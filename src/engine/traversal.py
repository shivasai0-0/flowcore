import json
import logging
import time
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger("flowcore.traversal")
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.models import (
    Session as SessionModel, ExecutionLog, CompiledGraph, WorkflowVersion,
    ExecutionSnapshot, ExecutionJournal, ExecutionMetric, Business
)
from src.schemas.carry_unit import CarryUnit
from src.schemas.graph import EdgeCondition, WorkflowNode, WorkflowEdge
from src.schemas.session import DispatchResponse, UiObject, UiAction, FormDefinition
from src.fsm.engine import FSMEngine, InvalidTransitionError
from src.modules.registry import ModuleRegistry
from src.modules.base import get_carry_unit_field, ModuleOutput
from src.engine.compiler.executable_graph import ExecutableGraph
from src.engine.conditions import evaluate_condition
from src.engine.exceptions import FlowCoreRuntimeError, IllegalTransitionError
from src.engine.events import EventDispatcher


class TraversalError(ValueError):
    """Raised when traversal encountered a structural or FSM error."""
    pass

# Lock registry to serialize requests per session_id
_session_locks: Dict[str, asyncio.Lock] = {}

# Tenacity-based retry wrapper for transient module errors
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type(Exception),
    reraise=True
)
async def execute_module_with_retry(module: Any, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
    return await module.execute(carry_unit, config, user_input)

async def write_journal(
    db_session: AsyncSession,
    session_id: str,
    node_id: str,
    event_type: str,
    payload: Dict[str, Any]
) -> None:
    """Writes a write-ahead journal event to the database execution_journals table."""
    journal = ExecutionJournal(
        session_id=session_id,
        node_id=node_id,
        event_type=event_type,
        payload_json=json.dumps(payload),
        timestamp=datetime.utcnow()
    )
    db_session.add(journal)
    await db_session.flush()

def get_operational_actions(fsm_state: str, carry_unit: CarryUnit = None) -> List[UiAction]:
    actions = []
    if fsm_state in ("CART", "CART_REVIEW"):
        if carry_unit and carry_unit.order and carry_unit.order.items:
            actions.append(UiAction(label="Add More Items", action="ADD_MORE_ITEMS"))
            actions.append(UiAction(label="Checkout", action="CHECKOUT"))
            actions.append(UiAction(label="Cancel Order", action="CANCEL_ORDER"))
    elif fsm_state == "PAYMENT":
        if not carry_unit or carry_unit.payment.status != "SUCCESS":
            actions.append(UiAction(label="Retry Payment", action="RETRY_PAYMENT"))
            actions.append(UiAction(label="Cancel Order", action="CANCEL_ORDER"))
    elif fsm_state == "CONFIRMED":
        if carry_unit and carry_unit.logistics and (carry_unit.logistics.delivery_id or carry_unit.logistics.status == "ASSIGNED"):
            actions.append(UiAction(label="Track Delivery", action="TRACK_DELIVERY"))
        else:
            actions.append(UiAction(label="View Order", action="VIEW_ORDER"))
    
    actions.append(UiAction(label="Contact Support", action="CONTACT_SUPPORT"))
    return actions

def get_state_guidance(fsm_state: str, carry_unit: CarryUnit = None) -> str:
    if fsm_state in ("MENU", "BROWSING"):
        return "\n\nReply using:\n1 x 2\n2 x 1"
    elif fsm_state == "CART":
        if carry_unit and carry_unit.order and carry_unit.order.items:
            return ""
        return "\n\nReply using:\n1 x 2\n2 x 1"
    elif fsm_state == "CART_REVIEW":
        return ""
    elif fsm_state == "PAYMENT":
        return "\n\nReply PAY after completing payment.\nOr select Cancel Order."
    elif fsm_state == "CONFIRMED":
        if carry_unit and carry_unit.logistics and (carry_unit.logistics.delivery_id or carry_unit.logistics.status == "ASSIGNED"):
            return "\n\nYour order is on the way.\nUse Track Delivery for updates."
        else:
            return "\n\nYour order has been confirmed."
    elif fsm_state == "CHECKOUT":
        return "\n\nPlease reply with your delivery address."
    elif fsm_state == "START":
        return "\n\nReply with 'MENU' to get started."
    return ""

def get_valid_options_text(fsm_state: str, carry_unit: CarryUnit = None) -> str:
    if fsm_state in ("CART", "CART_REVIEW"):
        if carry_unit and carry_unit.order and carry_unit.order.items:
            return "\n\nValid options:\n- Select Checkout\n- Select Add More Items\n- Select Cancel Order\n- Select Contact Support"
        else:
            return "\n\nValid options:\n- Reply with item numbers/names and quantities (e.g., '1 x 2')\n- Select Contact Support"
    elif fsm_state in ("MENU", "BROWSING"):
        return "\n\nValid options:\n- Reply with item numbers/names and quantities (e.g., '1 x 2')\n- Select Contact Support"
    elif fsm_state == "PAYMENT":
        return "\n\nValid options:\n- Reply 'PAY'\n- Select Cancel Order\n- Select Contact Support"
    elif fsm_state == "CHECKOUT":
        return "\n\nValid options:\n- Reply with your delivery address\n- Select Contact Support"
    elif fsm_state == "CONFIRMED":
        if carry_unit and carry_unit.logistics and (carry_unit.logistics.delivery_id or carry_unit.logistics.status == "ASSIGNED"):
            return "\n\nValid options:\n- Select Track Delivery\n- Select Contact Support"
        else:
            return "\n\nValid options:\n- Select View Order\n- Select Contact Support"
    return ""

class GraphTraversalEngine:
    @staticmethod
    async def dispatch_step(
        db_session: AsyncSession,
        session_record: SessionModel,
        user_input: str,
        max_depth: int = 10
    ) -> DispatchResponse:
        """
        Executes a single user interaction turn.
        Traverses the graph from the current node by matching edge conditions,
        running module executors inside transaction boundaries with WAL logs,
        updating FSM states, merging carry units, and writing execution snapshots.
        """
        from src.database import db_session_context
        db_session_context.set(db_session)

        session_id = session_record.id
        
        # 1. Session-level Concurrency Locks serialization
        if session_id not in _session_locks:
            _session_locks[session_id] = asyncio.Lock()
        
        async with _session_locks[session_id]:
            # Capture session record attributes before any rollback can occur to avoid MissingGreenlet errors.
            business_id = session_record.business_id
            customer_phone = session_record.customer_phone
            current_node_id_before = session_record.current_node_id
            carry_unit_json_before = session_record.carry_unit_json

            # Load Business settings and catalog
            biz_query = select(Business).where(Business.id == business_id)
            biz_res = await db_session.execute(biz_query)
            business_rec = biz_res.scalar_one_or_none()
            catalog = json.loads(business_rec.catalog_json) if (business_rec and business_rec.catalog_json) else {}
            settings = json.loads(business_rec.settings_json) if (business_rec and business_rec.settings_json) else {}
            biz_type = business_rec.business_type if business_rec else "restaurant"
            branding = json.loads(business_rec.branding_json) if (business_rec and business_rec.branding_json) else {}
            providers = json.loads(business_rec.providers_json) if (business_rec and business_rec.providers_json) else {}

            # Load or initialize SharedCustomerContext
            from src.models import SharedCustomerContext
            context_query = select(SharedCustomerContext).where(
                SharedCustomerContext.customer_id == customer_phone,
                SharedCustomerContext.business_id == business_id
            )
            context_res = await db_session.execute(context_query)
            shared_context = context_res.scalar_one_or_none()
            if not shared_context:
                shared_context = SharedCustomerContext(
                    customer_id=customer_phone,
                    business_id=business_id,
                    active_orders_json="[]",
                    active_bookings_json="[]",
                    support_tickets_json="[]",
                    loyalty_points=0,
                    business_data_json="{}"
                )
                db_session.add(shared_context)
                await db_session.flush()

            shared_context_data = {
                "loyalty_points": shared_context.loyalty_points,
                "active_orders": json.loads(shared_context.active_orders_json),
                "active_bookings": json.loads(shared_context.active_bookings_json),
                "support_tickets": json.loads(shared_context.support_tickets_json),
                "business_data": json.loads(shared_context.business_data_json)
            }

            now = datetime.utcnow()
            if session_record.is_archived:
                raise FlowCoreRuntimeError(
                    error_code="SESSION_ARCHIVED",
                    message="Session is archived and cannot process events.",
                    session_id=session_id,
                    node_id=session_record.current_node_id,
                    current_fsm_state=session_record.fsm_state
                )
            if session_record.locked_until and session_record.locked_until > now:
                raise FlowCoreRuntimeError(
                    error_code="SESSION_LOCKED",
                    message="Session is currently locked due to another concurrent process.",
                    session_id=session_id,
                    node_id=session_record.current_node_id,
                    current_fsm_state=session_record.fsm_state
                )

            # Deserialize carry unit early for global intercepts
            carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))
            carry_unit.customer.shared_context = shared_context_data
            fsm_state_before = session_record.fsm_state
            current_fsm_state = session_record.fsm_state

            # Check if there is an active pending approval for this session
            from src.models import Approval
            app_query = select(Approval).where(Approval.session_id == session_id, Approval.status == "PENDING")
            app_res = await db_session.execute(app_query)
            pending_app = app_res.scalars().first()
            if pending_app:
                msg = "⏳ Your request is pending approval from our staff. Please wait."
                return DispatchResponse(
                    session_id=session_id,
                    fsm_state_before=fsm_state_before,
                    fsm_state_after=current_fsm_state,
                    executed_nodes=[],
                    carry_unit=carry_unit,
                    messages_sent=[msg],
                    ui=UiObject(
                        text=msg,
                        actions=[],
                        metadata={}
                    ),
                    available_actions=[],
                    side_effects=[],
                    edge_logs=[],
                    routing_trace=[]
                )

            # CHECK GLOBAL INTERCEPTS BEFORE TERMINAL STATE LOCK (UX Requirement)
            # 1. Contact Support
            if user_input.strip().upper() == "CONTACT_SUPPORT" or user_input.strip().lower() == "contact support":
                msg = "Our support team will contact you shortly."
                session_record.locked_until = None
                await db_session.flush()
                return DispatchResponse(
                    session_id=session_id,
                    fsm_state_before=fsm_state_before,
                    fsm_state_after=current_fsm_state,
                    executed_nodes=[],
                    carry_unit=carry_unit,
                    messages_sent=[msg],
                    ui=UiObject(
                        text=msg,
                        actions=[UiAction(label=a.label, action=a.action) for a in get_operational_actions(current_fsm_state, carry_unit)],
                        metadata={}
                    ),
                    available_actions=[a.label for a in get_operational_actions(current_fsm_state, carry_unit)],
                    side_effects=[],
                    edge_logs=[],
                    routing_trace=[]
                )

            # 2. Track Delivery (CONFIRMED state only)
            if user_input.strip().upper() in {"TRACK_DELIVERY", "TRACK DELIVERY"} and current_fsm_state == "CONFIRMED":
                status_str = "UNASSIGNED"
                delivery_id_str = "N/A"
                if carry_unit.logistics:
                    status_str = carry_unit.logistics.status or "ASSIGNED"
                    delivery_id_str = carry_unit.logistics.delivery_id or "N/A"
                msg = f"🚚 Delivery Tracking\n\nStatus: {status_str.upper()}\nDelivery ID: {delivery_id_str}"
                session_record.locked_until = None
                await db_session.flush()
                return DispatchResponse(
                    session_id=session_id,
                    fsm_state_before=fsm_state_before,
                    fsm_state_after=current_fsm_state,
                    executed_nodes=[],
                    carry_unit=carry_unit,
                    messages_sent=[msg],
                    ui=UiObject(
                        text=msg,
                        actions=[UiAction(label=a.label, action=a.action) for a in get_operational_actions(current_fsm_state, carry_unit)],
                        metadata={}
                    ),
                    available_actions=[a.label for a in get_operational_actions(current_fsm_state, carry_unit)],
                    side_effects=[],
                    edge_logs=[],
                    routing_trace=[]
                )

            # 3. View Order (CONFIRMED state only)
            if user_input.strip().upper() in {"VIEW_ORDER", "VIEW ORDER"} and current_fsm_state == "CONFIRMED":
                item_lines = []
                total_val = 0.0
                if carry_unit.order:
                    total_val = carry_unit.order.total or 0.0
                    menu_prices = {
                        "1": "Margherita Pizza",
                        "2": "Veggie Burger",
                        "3": "French Fries",
                        "4": "Soft Drink"
                    }
                    if catalog and isinstance(catalog, dict) and "items" in catalog:
                        for item in catalog["items"]:
                            menu_prices[str(item.get("id"))] = item.get("name")
                    for item in carry_unit.order.items:
                        item_name = menu_prices.get(str(item.item_id), f"Item {item.item_id}")
                        item_lines.append(f"{item_name} x{item.quantity}")
                items_str = "\n".join(item_lines) if item_lines else "No items found."
                msg = f"📝 Confirmed Order Summary\n\n{items_str}\n\nTotal Paid: ${total_val:.2f}"
                session_record.locked_until = None
                await db_session.flush()
                return DispatchResponse(
                    session_id=session_id,
                    fsm_state_before=fsm_state_before,
                    fsm_state_after=current_fsm_state,
                    executed_nodes=[],
                    carry_unit=carry_unit,
                    messages_sent=[msg],
                    ui=UiObject(
                        text=msg,
                        actions=[UiAction(label=a.label, action=a.action) for a in get_operational_actions(current_fsm_state, carry_unit)],
                        metadata={}
                    ),
                    available_actions=[a.label for a in get_operational_actions(current_fsm_state, carry_unit)],
                    side_effects=[],
                    edge_logs=[],
                    routing_trace=[]
                )

            # Now enforce terminal state lock for all other inputs
            if session_record.fsm_state in {"CONFIRMED", "CANCELLED"}:
                raise FlowCoreRuntimeError(
                    error_code="TERMINAL_STATE_LOCKED",
                    message=f"Session is in terminal state '{session_record.fsm_state}' and cannot process further events.",
                    session_id=session_id,
                    node_id=session_record.current_node_id,
                    current_fsm_state=session_record.fsm_state
                )

            # Set lock in db
            session_record.locked_until = now + timedelta(seconds=10)
            session_record.last_active_at = now
            db_session.add(session_record)
            await db_session.flush()

            # Create step savepoint to rollback on failure
            step_savepoint = await db_session.begin_nested()
            try:
                # Load compiled graph
                query = select(CompiledGraph).where(CompiledGraph.workflow_version_id == session_record.workflow_version_id)
                res = await db_session.execute(query)
                compiled_graph_record = res.scalar_one_or_none()
                if not compiled_graph_record:
                    raise FlowCoreRuntimeError(
                        error_code="COMPILED_GRAPH_NOT_FOUND",
                        message=f"Compiled graph not found for workflow version ID '{session_record.workflow_version_id}'.",
                        session_id=session_id,
                        node_id=session_record.current_node_id,
                        current_fsm_state=session_record.fsm_state
                    )

                graph_dict = json.loads(compiled_graph_record.compiled_json)
                
                # Enforce Business Isolation Invariant (INV-06)
                if session_record.business_id != graph_dict["business_id"]:
                    raise FlowCoreRuntimeError(
                        error_code="BUSINESS_ISOLATION_VIOLATION",
                        message="Business Isolation Violation: Session business_id does not match workflow business_id.",
                        session_id=session_id,
                        node_id=session_record.current_node_id,
                        current_fsm_state=session_record.fsm_state
                    )

                # Load compiled ExecutableGraph
                executable = ExecutableGraph(graph_dict)

                # Load compiled ExecutableGraph (carry_unit and FSM states are already loaded early)

                # Check for "Add More Items" input
                if user_input.strip().upper() in {"ADD_MORE_ITEMS", "ADD MORE ITEMS"}:
                    session_record.current_node_id = None
                    session_record.fsm_state = "START"
                    user_input = "/start"
                    current_fsm_state = "START"
                    fsm_state_before = "START"

                # Check for "Cancel Order" input
                if user_input.strip().upper() in {"CANCEL_ORDER", "CANCEL ORDER"}:
                    msg = "❌ Order Cancelled\n\nYour order has been cancelled. If you want to start a new order, reply with MENU."
                    session_record.fsm_state = "CANCELLED"
                    session_record.is_archived = True
                    session_record.current_node_id = None
                    session_record.locked_until = None
                    session_record.carry_unit_json = json.dumps(carry_unit.model_dump())
                    await db_session.flush()
                    return DispatchResponse(
                        session_id=session_id,
                        fsm_state_before=fsm_state_before,
                        fsm_state_after="CANCELLED",
                        executed_nodes=[],
                        carry_unit=carry_unit,
                        messages_sent=[msg],
                        ui=UiObject(
                            text=msg,
                            actions=[UiAction(label="Start New Order", action="START_NEW_ORDER")],
                            metadata={}
                        ),
                        available_actions=["Start New Order"],
                        side_effects=[],
                        edge_logs=[],
                        routing_trace=[]
                    )

                # Initialize or reset invalid input count based on FSM state change
                metadata_data = carry_unit.metadata.data or {}
                invalid_count = metadata_data.get("invalid_input_count", 0)
                invalid_state = metadata_data.get("invalid_input_state", current_fsm_state)
                
                if invalid_state != current_fsm_state:
                    invalid_count = 0
                    invalid_state = current_fsm_state

                logger.info(f"--- [Session Dispatch] ID: {session_id} | Input: '{user_input}' | FSM: {fsm_state_before} | Node: {session_record.current_node_id} ---")

                executed_nodes = []
                messages_sent = []
                pending_side_effects = []
                edge_logs = []
                routing_trace = []
                final_text_list = []
                final_actions = []
                final_form = None
                final_metadata = {}

                try:
                    # Find next node based on current pointer
                    current_node_id = session_record.current_node_id

                    # Global action intercepts to bypass standard conditional edge routing
                    bypass_routing = False
                    clean_input = user_input.strip().upper()
                    if clean_input in {"VIEW_CART", "VIEW CART", "CALCULATE_TOTAL", "CALCULATE TOTAL"} and current_fsm_state in {"CART", "CART_REVIEW"}:
                        calc_node_id = None
                        for nid, node_obj in executable.node_lookup.items():
                            if node_obj.module_name == "calculate_total":
                                calc_node_id = nid
                                break
                        if calc_node_id:
                            session_record.current_node_id = calc_node_id
                            current_node_id = calc_node_id
                            bypass_routing = True

                    if clean_input in {"RETRY_PAYMENT", "RETRY PAYMENT"} and current_fsm_state == "PAYMENT":
                        pay_node_id = None
                        for nid, node_obj in executable.node_lookup.items():
                            if node_obj.module_name == "create_payment":
                                pay_node_id = nid
                                break
                        if pay_node_id:
                            session_record.current_node_id = pay_node_id
                            current_node_id = pay_node_id
                            bypass_routing = True

                    node_to_execute = None
                    if bypass_routing:
                        node_to_execute = current_node_id
                    elif not current_node_id:
                        # First tick: start at entry node
                        node_to_execute = executable.entry_node_id
                    else:
                        outgoing_edges = executable.get_outgoing_edges(current_node_id)
                        
                        # Check if it has any outgoing USER edges (non-always edges)
                        has_user_edges = any(edge.condition.type != "always" for edge in outgoing_edges)
                        
                        if has_user_edges:
                            next_node_id = None
                            for edge in outgoing_edges:
                                if edge.condition.type != "always":
                                    try:
                                        matched = evaluate_condition(edge.condition, user_input, carry_unit)
                                        edge_logs.append(f"Node {current_node_id}: Checked edge to {edge.to_node} [type={edge.condition.type}, key={edge.condition.key}, value={edge.condition.value}] -> matched={matched}")
                                    except Exception as e:
                                        edge_logs.append(f"Node {current_node_id}: Checked edge to {edge.to_node} [type={edge.condition.type}] -> error={str(e)}")
                                        raise
                                    if matched:
                                        next_node_id = edge.to_node
                                        routing_trace.append(f"{edge.from_node} -> {edge.to_node} (condition match)")
                                        break
                            
                            # Fallback 'always' edge
                            if not next_node_id:
                                for edge in outgoing_edges:
                                    if edge.condition.type == "always":
                                        next_node_id = edge.to_node
                                        edge_logs.append(f"Node {current_node_id}: Checked edge to {edge.to_node} [type=always] -> matched=True")
                                        routing_trace.append(f"{edge.from_node} -> {edge.to_node} (always fallback)")
                                        break
                                        
                            if not next_node_id:
                                raise FlowCoreRuntimeError(
                                    error_code="UNRESOLVED_ROUTING",
                                    message=f"Unresolved routing from node '{current_node_id}': no condition edges matched input '{user_input}'.",
                                    session_id=session_id,
                                    node_id=current_node_id,
                                    current_fsm_state=current_fsm_state
                                )
                            node_to_execute = next_node_id
                        else:
                            node_to_execute = current_node_id

                    current_node_id = node_to_execute
                    depth = 0
                    bypass_cache = bypass_routing

                    while current_node_id:
                        if depth >= max_depth:
                            raise FlowCoreRuntimeError(
                                error_code="STALLED_EXECUTION",
                                message="Traversal loop or stalled execution detected. Max execution depth exceeded.",
                                session_id=session_id,
                                node_id=current_node_id,
                                current_fsm_state=current_fsm_state
                            )

                        depth += 1
                        node = executable.get_node(current_node_id)
                        if not node:
                            raise FlowCoreRuntimeError(
                                error_code="NODE_NOT_FOUND",
                                message=f"Node '{current_node_id}' not found in executable plan.",
                                session_id=session_id,
                                node_id=current_node_id,
                                current_fsm_state=current_fsm_state
                            )

                        module = ModuleRegistry.get(node.module_name)
                        logger.info(f" -> Traversing node '{current_node_id}' [module: '{node.module_name}']")

                        # Reset only actions in the cascade step to prevent button pollution (stay under WhatsApp 3-button limit)
                        # but preserve form and metadata so they are not lost.
                        final_actions = []

                        time_start = time.time()
                        is_error = False

                        try:
                            async with db_session.begin_nested() as node_savepoint:
                                await write_journal(
                                    db_session, session_id, current_node_id, "BEGIN_NODE",
                                    {"user_input": user_input, "config": node.config}
                                )

                                if current_fsm_state not in module.contract.allowed_fsm_states:
                                    if "*" not in module.contract.allowed_fsm_states:
                                        raise IllegalTransitionError(
                                            message=f"FSM Engine Violation: Module '{node.module_name}' is not allowed in state '{current_fsm_state}'.",
                                            session_id=session_id,
                                            node_id=current_node_id,
                                            current_fsm_state=current_fsm_state
                                        )

                                if node.fsm_transition_to:
                                    try:
                                        FSMEngine.transition(
                                            current_state=current_fsm_state,
                                            target_state=node.fsm_transition_to,
                                            module_name=node.module_name,
                                            custom_transition_table=executable.fsm_transition_table
                                        )
                                    except InvalidTransitionError as e:
                                        raise IllegalTransitionError(
                                            message=f"FSM State Transition Failure: {str(e)}",
                                            session_id=session_id,
                                            node_id=current_node_id,
                                            current_fsm_state=current_fsm_state
                                        )

                                module.validate_inputs(carry_unit)

                                cached_output = None
                                if not module.contract.is_idempotent and not bypass_cache:
                                    log_query = select(ExecutionLog).where(
                                        ExecutionLog.session_id == session_id,
                                        ExecutionLog.node_id == current_node_id
                                    )
                                    log_res = await db_session.execute(log_query)
                                    prior_log = log_res.scalar_one_or_none()
                                    if prior_log:
                                        cached_output = json.loads(prior_log.outputs_json)
                                
                                bypass_cache = False
                                node_config = dict(node.config or {})
                                node_config["_node_id"] = current_node_id
                                node_config["_business_catalog"] = catalog
                                node_config["_business_settings"] = settings
                                node_config["_business_type"] = biz_type
                                node_config["_business_branding"] = branding
                                node_config["_business_providers"] = providers

                                if cached_output is not None:
                                    logger.info(f"    INV-08: Retrieved cached execution for non-idempotent module '{node.module_name}' on node '{current_node_id}'")
                                    outputs = cached_output
                                    messages = []
                                    res = None
                                else:
                                    try:
                                        res = await asyncio.wait_for(
                                            execute_module_with_retry(module, carry_unit, node_config, user_input),
                                            timeout=5.0
                                        )
                                        outputs = res.outputs
                                        messages = res.messages
                                        logger.info(f"    Executed module '{node.module_name}' successfully.")
                                    except asyncio.TimeoutError:
                                        logger.error(f"    Module execution TIMEOUT on node '{current_node_id}'")
                                        raise FlowCoreRuntimeError(
                                            error_code="MODULE_TIMEOUT",
                                            message="Module execution timed out after 5.0 seconds.",
                                            session_id=session_id,
                                            node_id=current_node_id,
                                            current_fsm_state=current_fsm_state
                                        )
                                    except Exception as e:
                                        logger.error(f"    Module execution error on node '{current_node_id}': {str(e)}")
                                        raise

                                await write_journal(
                                    db_session, session_id, current_node_id, "MODULE_EXECUTED",
                                    {"outputs": list(outputs.keys()), "messages": messages}
                                )

                                module.validate_outputs(outputs)
                                fsm_state_node_before = current_fsm_state

                                try:
                                    carry_unit = carry_unit.merge_patch(outputs)
                                    serialized_carry = json.dumps(carry_unit.model_dump())
                                    if len(serialized_carry) > 51200:
                                        raise FlowCoreRuntimeError(
                                            error_code="PAYLOAD_BUDGET_EXCEEDED",
                                            message="Carry Unit Payload Budget Exceeded: CarryUnit serialized size is greater than 50KB.",
                                            session_id=session_id,
                                            node_id=current_node_id,
                                            current_fsm_state=current_fsm_state
                                        )
                                except ValueError as e:
                                    raise FlowCoreRuntimeError(
                                        error_code="CARRY_MUTATION_ERROR",
                                        message=f"Carry Unit Merge Violation: {str(e)}",
                                        session_id=session_id,
                                        node_id=current_node_id,
                                        current_fsm_state=current_fsm_state
                                    )

                                if node.fsm_transition_to:
                                    try:
                                        current_fsm_state = FSMEngine.transition(
                                            current_state=current_fsm_state,
                                            target_state=node.fsm_transition_to,
                                            module_name=node.module_name,
                                            custom_transition_table=executable.fsm_transition_table
                                        )
                                        logger.info(f"    FSM Transition: {fsm_state_node_before} -> {current_fsm_state}")
                                        
                                        await write_journal(
                                            db_session, session_id, current_node_id, "FSM_TRANSITION",
                                            {"fsm_state_before": fsm_state_node_before, "fsm_state_after": current_fsm_state}
                                        )
                                        
                                        await EventDispatcher.emit(
                                            db_session, session_id, "FSM_TRANSITIONED",
                                            {
                                                "fsm_state_before": fsm_state_node_before,
                                                "fsm_state_after": current_fsm_state,
                                                "node_id": current_node_id,
                                                "module_name": node.module_name
                                            }
                                        )
                                    except InvalidTransitionError as e:
                                        raise IllegalTransitionError(
                                            message=f"FSM State Transition Failure: {str(e)}",
                                            session_id=session_id,
                                            node_id=current_node_id,
                                            current_fsm_state=current_fsm_state
                                        )

                                log = ExecutionLog(
                                    session_id=session_id,
                                    business_id=session_record.business_id,
                                    node_id=current_node_id,
                                    module_name=node.module_name,
                                    inputs_json=json.dumps({"user_input": user_input, "config": node.config}),
                                    outputs_json=json.dumps(outputs),
                                    fsm_state_before=fsm_state_node_before,
                                    fsm_state_after=current_fsm_state
                                )
                                db_session.add(log)

                                snapshot = ExecutionSnapshot(
                                    session_id=session_id,
                                    node_id=current_node_id,
                                    carry_unit_json=json.dumps(carry_unit.model_dump()),
                                    fsm_state=current_fsm_state
                                )
                                db_session.add(snapshot)
                                await db_session.flush()

                                await write_journal(
                                    db_session, session_id, current_node_id, "SNAPSHOT_WRITTEN",
                                    {"carry_unit_version": carry_unit.version}
                                )

                                await write_journal(
                                    db_session, session_id, current_node_id, "NODE_COMMITTED", {}
                                )

                                executed_nodes.append(current_node_id)
                                messages_sent.extend(messages)
                                
                                if res and getattr(res, "ui", None):
                                    ui_data = res.ui
                                    if ui_data.get("text"):
                                        final_text_list.append(ui_data["text"])
                                    if ui_data.get("actions"):
                                        final_actions.extend(ui_data["actions"])
                                    if ui_data.get("form"):
                                        final_form = ui_data["form"]
                                    elif ui_data.get("metadata", {}).get("form"):
                                        final_form = ui_data["metadata"]["form"]
                                    if ui_data.get("metadata"):
                                        final_metadata.update(ui_data["metadata"])
                                else:
                                    if messages:
                                        final_text_list.extend(messages)

                                if node.module_name == "confirm_payment" and outputs.get("payment", {}).get("status") == "SUCCESS":
                                    await EventDispatcher.emit(
                                        db_session, session_id, "PAYMENT_SUCCESS",
                                        {"transaction_id": carry_unit.payment.transaction_id, "total": carry_unit.order.total}
                                    )
                                elif node.module_name == "create_payment" and outputs.get("payment", {}).get("transaction_id"):
                                    p_out = outputs.get("payment")
                                    await EventDispatcher.emit(
                                        db_session, session_id, "PAYMENT_CREATED",
                                        {"transaction_id": p_out.get("transaction_id"), "payment_url": p_out.get("payment_url"), "total": carry_unit.order.total}
                                    )
                                elif node.module_name == "create_order" and outputs.get("order", {}).get("status") == "PLACED":
                                    await EventDispatcher.emit(
                                        db_session, session_id, "ORDER_PLACED",
                                        {"total": carry_unit.order.total, "items_count": len(carry_unit.order.items)}
                                    )
                                elif node.module_name == "create_delivery" and outputs.get("logistics", {}).get("status") == "ASSIGNED":
                                    await EventDispatcher.emit(
                                        db_session, session_id, "DELIVERY_ASSIGNED",
                                        {"delivery_id": outputs.get("logistics", {}).get("delivery_id")}
                                    )
                                
                                if res and getattr(res, "side_effects", None):
                                    for se in res.side_effects:
                                        pending_side_effects.append({
                                            "node_id": current_node_id,
                                            "module_name": node.module_name,
                                            "side_effect": se.get("type", ""),
                                            "type": se.get("type", ""),
                                            "payload": se.get("payload", {})
                                        })
                                elif module.contract.side_effects:
                                    for se in module.contract.side_effects:
                                        pending_side_effects.append({
                                            "node_id": current_node_id,
                                            "module_name": node.module_name,
                                            "side_effect": se,
                                            "type": se,
                                            "payload": {}
                                        })

                        except Exception as e:
                            is_error = True
                            logger.error(f"    Transaction rollback executed for node '{current_node_id}': {str(e)}")

                            is_gating_error = False
                            if isinstance(e, FlowCoreRuntimeError):
                                if e.error_code in {
                                    "INVALID_TRANSITION",
                                    "INVALID_CART_INPUT",
                                    "INVALID_QUANTITY",
                                    "UNKNOWN_PRODUCT",
                                    "TERMINAL_STATE_LOCKED",
                                    "SESSION_ARCHIVED",
                                    "SESSION_LOCKED",
                                    "UNRESOLVED_ROUTING",
                                    "INVALID_ADDRESS",
                                    "PAYMENT_ALREADY_COMPLETED"
                                }:
                                    is_gating_error = True

                            if is_gating_error:
                                raise e

                            session_record.fsm_state = "ERROR"
                            session_record.current_node_id = current_node_id
                            
                            if isinstance(e, FlowCoreRuntimeError):
                                err_code = e.error_code
                                err_msg = e.message
                            else:
                                err_code = "NODE_EXECUTION_FAILED"
                                err_msg = str(e)

                            trace_entry = {
                                "node_id": current_node_id,
                                "module_name": node.module_name,
                                "timestamp": datetime.utcnow().isoformat(),
                                "fsm_state_before": current_fsm_state,
                                "fsm_state_after": "ERROR",
                                "routing_decision": None,
                                "latency_ms": int((time.time() - time_start) * 1000),
                                "error": err_msg
                            }
                            carry_unit = carry_unit.merge_patch({
                                "workflow": {
                                    "execution_trace": [json.dumps(trace_entry)]
                                }
                            })

                            await write_journal(
                                db_session, session_id, current_node_id, "NODE_FAILED",
                                {"error": err_msg}
                            )

                            fail_log = ExecutionLog(
                                session_id=session_id,
                                business_id=session_record.business_id,
                                node_id=current_node_id,
                                module_name=node.module_name,
                                inputs_json=json.dumps({"user_input": user_input, "config": node.config}),
                                outputs_json=json.dumps({"error": err_msg}),
                                fsm_state_before=current_fsm_state,
                                fsm_state_after="ERROR"
                            )
                            db_session.add(fail_log)
                            
                            session_record.carry_unit_json = json.dumps(carry_unit.model_dump())
                            
                            latency_ms = int((time.time() - time_start) * 1000)
                            metric = ExecutionMetric(
                                session_id=session_id,
                                node_id=current_node_id,
                                module_name=node.module_name,
                                latency_ms=latency_ms,
                                is_error=True,
                                retry_count=0
                            )
                            db_session.add(metric)
                            await db_session.flush()

                            await db_session.commit()

                            if isinstance(e, FlowCoreRuntimeError):
                                raise e
                            else:
                                raise FlowCoreRuntimeError(
                                    error_code=err_code,
                                    message=err_msg,
                                    session_id=session_id,
                                    node_id=current_node_id,
                                    current_fsm_state=current_fsm_state
                                )

                        latency_ms = int((time.time() - time_start) * 1000)
                        metric = ExecutionMetric(
                            session_id=session_id,
                            node_id=current_node_id,
                            module_name=node.module_name,
                            latency_ms=latency_ms,
                            is_error=False,
                            retry_count=0
                        )
                        db_session.add(metric)
                        await db_session.flush()

                        outgoing = executable.get_outgoing_edges(current_node_id)
                        next_target_node_id = None
                        for edge in outgoing:
                            if edge.condition.type == "always":
                                next_target_node_id = edge.to_node
                                edge_logs.append(f"Node {current_node_id}: Checked edge to {edge.to_node} [type=always] -> matched=True")
                                routing_trace.append(f"Cascade: {edge.from_node} -> {edge.to_node}")
                                break
                        
                        if len(outgoing) == 0 and current_fsm_state not in {"CONFIRMED", "CANCELLED"}:
                            raise FlowCoreRuntimeError(
                                error_code="DEAD_END_NODE",
                                message=f"Dead-end node detected: Node '{current_node_id}' has no outgoing edges and FSM state '{current_fsm_state}' is not terminal.",
                                session_id=session_id,
                                node_id=current_node_id,
                                current_fsm_state=current_fsm_state
                            )

                        trace_entry = {
                            "node_id": current_node_id,
                            "module_name": node.module_name,
                            "timestamp": datetime.utcnow().isoformat(),
                            "fsm_state_before": fsm_state_node_before,
                            "fsm_state_after": current_fsm_state,
                            "routing_decision": next_target_node_id,
                            "latency_ms": latency_ms,
                            "error": None
                        }
                        carry_unit = carry_unit.merge_patch({
                            "workflow": {
                                "execution_trace": [json.dumps(trace_entry)]
                            }
                        })

                        if next_target_node_id:
                            target_node_obj = executable.get_node(next_target_node_id)
                            is_user_input = False
                            if target_node_obj:
                                target_module = ModuleRegistry.get(target_node_obj.module_name)
                                is_user_input = getattr(target_module.contract, "expects_user_input", False)

                            if is_user_input:
                                logger.info(f"    Always transition to user-input node '{next_target_node_id}'. Halting traversal.")
                                current_node_id = next_target_node_id
                                break
                            else:
                                logger.info(f"    Cascade: Automatically traversing 'always' edge to node '{next_target_node_id}'")
                                current_node_id = next_target_node_id
                        else:
                            break                    # Traversal succeeded! Reset the invalid input count (RESET RULES)
                    carry_unit.metadata.data["invalid_input_count"] = 0
                    carry_unit.metadata.data["invalid_input_state"] = current_fsm_state
                    
                    # Persist final session updates
                    session_record.fsm_state = current_fsm_state
                    session_record.current_node_id = current_node_id
                    session_record.carry_unit_json = json.dumps(carry_unit.model_dump())

                    logger.info(f"--- [Dispatch Complete] Final FSM: {current_fsm_state} | Final Node: {session_record.current_node_id} | Carry Unit Ver: {carry_unit.version} | Messages Sent: {messages_sent} ---\n")

                    # Apply state-specific guidance (PART 4)
                    guidance = get_state_guidance(current_fsm_state, carry_unit)
                    if guidance:
                        guidance_clean = guidance.strip()
                        already_present = False
                        for msg in final_text_list:
                            if guidance_clean in msg:
                                already_present = True
                                break
                        if not already_present:
                            final_text_list.append(guidance_clean)
                            if messages_sent and guidance_clean not in messages_sent[-1]:
                                messages_sent[-1] += guidance
                            
                    # Merge FSM-aware actions (PART 2)
                    fsm_actions = get_operational_actions(current_fsm_state, carry_unit)
                    for fa in fsm_actions:
                        if not any(a.get("action") == fa.action for a in final_actions):
                            final_actions.append({"label": fa.label, "action": fa.action})

                    final_ui = None
                    if final_text_list or final_actions or final_form:
                        text_content = "\n\n".join(final_text_list).strip()
                        final_ui = UiObject(
                            text=text_content,
                            actions=[UiAction(label=a.get("label", ""), action=a.get("action", "")) for a in final_actions],
                            form=final_form,
                            metadata=final_metadata
                        )

                    # Ensure FSM state and current node are aligned (Runtime Safety Invariant)
                    if current_node_id:
                        curr_node_obj = executable.get_node(current_node_id)
                        if curr_node_obj:
                            curr_module = ModuleRegistry.get(curr_node_obj.module_name)
                            if curr_module and current_fsm_state not in curr_module.contract.allowed_fsm_states:
                                if "*" not in curr_module.contract.allowed_fsm_states:
                                    raise IllegalTransitionError(
                                        message=f"FSM Legality Alignment Violation: Halted at node '{current_node_id}' running module '{curr_node_obj.module_name}' which is not allowed in FSM state '{current_fsm_state}'.",
                                        session_id=session_id,
                                        node_id=current_node_id,
                                        current_fsm_state=current_fsm_state
                                    )

                    # Save SharedCustomerContext updates
                    if carry_unit.customer.shared_context:
                        sc = carry_unit.customer.shared_context
                        shared_context.loyalty_points = sc.get("loyalty_points", 0)
                        if "active_orders" in sc:
                            shared_context.active_orders_json = json.dumps(sc["active_orders"])
                        if "active_bookings" in sc:
                            shared_context.active_bookings_json = json.dumps(sc["active_bookings"])
                        if "support_tickets" in sc:
                            shared_context.support_tickets_json = json.dumps(sc["support_tickets"])
                        if "business_data" in sc:
                            shared_context.business_data_json = json.dumps(sc["business_data"])
                        db_session.add(shared_context)
                        await db_session.flush()

                    # Commit successful step savepoint
                    await step_savepoint.commit()

                    from src.services.dev_workspace import apply_dev_workspace_branding
                    branded_messages = []
                    for msg in messages_sent:
                        branded_messages.append(await apply_dev_workspace_branding(db_session, business_id, msg))
                    messages_sent = branded_messages
                    if final_ui and final_ui.text:
                        final_ui.text = await apply_dev_workspace_branding(db_session, business_id, final_ui.text)

                    return DispatchResponse(
                        session_id=session_id,
                        fsm_state_before=fsm_state_before,
                        fsm_state_after=current_fsm_state,
                        executed_nodes=executed_nodes,
                        carry_unit=carry_unit,
                        messages_sent=messages_sent,
                        ui=final_ui,
                        available_actions=[a.get("label", "") for a in final_actions] if final_actions else [],
                        side_effects=pending_side_effects,
                        edge_logs=edge_logs,
                        routing_trace=routing_trace
                    )

                except Exception as e:
                    # Rollback step changes
                    await step_savepoint.rollback()

                    # Check for FSM legality violation
                    is_fsm_error = False
                    if isinstance(e, (IllegalTransitionError, InvalidTransitionError)):
                        is_fsm_error = True
                    elif isinstance(e, FlowCoreRuntimeError) and e.error_code == "INVALID_TRANSITION":
                        is_fsm_error = True

                    if is_fsm_error:
                        logger.error(f"FSM Legality Violation: {str(e)}")

                        # Return customer-friendly message
                        msg = "We encountered an issue processing your request.\n\nPlease try again or restart your order."

                        # Log technical error internally in ExecutionLog
                        error_log = ExecutionLog(
                            session_id=session_id,
                            business_id=business_id,
                            node_id=current_node_id_before or "unresolved",
                            module_name="fsm_legality_handler",
                            inputs_json=json.dumps({"user_input": user_input}),
                            outputs_json=json.dumps({"error": str(e)}),
                            fsm_state_before=fsm_state_before,
                            fsm_state_after=fsm_state_before
                        )
                        db_session.add(error_log)

                        # Session state remains at fsm_state_before / current_node_id from before the turn
                        session_record.fsm_state = fsm_state_before
                        session_record.carry_unit_json = carry_unit_json_before
                        await db_session.flush()

                        from src.services.dev_workspace import apply_dev_workspace_branding
                        branded_msg = await apply_dev_workspace_branding(db_session, business_id, msg)

                        return DispatchResponse(
                            session_id=session_id,
                            fsm_state_before=fsm_state_before,
                            fsm_state_after=fsm_state_before,
                            executed_nodes=[],
                            carry_unit=carry_unit,
                            messages_sent=[branded_msg],
                            ui=UiObject(
                                text=branded_msg,
                                actions=[UiAction(label=a.label, action=a.action) for a in get_operational_actions(fsm_state_before, carry_unit)],
                                metadata={}
                            ),
                            available_actions=[a.label for a in get_operational_actions(fsm_state_before, carry_unit)],
                            side_effects=[],
                            edge_logs=edge_logs,
                            routing_trace=routing_trace
                        )

                    # Catch and process customer input verification errors (PART 3)
                    is_input_error = False
                    if isinstance(e, FlowCoreRuntimeError) and e.error_code in {
                        "UNRESOLVED_ROUTING", "INVALID_CART_INPUT", "INVALID_QUANTITY", "UNKNOWN_PRODUCT", "INVALID_ADDRESS"
                    }:
                        is_input_error = True
                    elif isinstance(e, (ValueError, TypeError)):
                        is_input_error = True
                        
                    if is_input_error:
                        invalid_count += 1
                        carry_unit.metadata.data["invalid_input_count"] = invalid_count
                        carry_unit.metadata.data["invalid_input_state"] = current_fsm_state
                        
                        fsm_state_after = current_fsm_state
                        
                        if invalid_count == 1:
                            err_code = getattr(e, "error_code", None)
                            if err_code in {"INVALID_CART_INPUT", "INVALID_QUANTITY", "UNKNOWN_PRODUCT"}:
                                msg = "❌ Invalid item selection.\n\nPlease use the format:\n\n1 x 2\n2 x 1\n\nor\n\n1 x 2, 2 x 1"
                            elif err_code == "INVALID_ADDRESS":
                                msg = "📍 Please enter a valid delivery address.\n\nExample:\n\nHouse No 4-56\nNear Bus Stand\nKamareddy"
                            else:
                                msg = "❌ I couldn't understand that.\n\nPlease follow the instructions shown above."
                                options_text = get_valid_options_text(current_fsm_state, carry_unit)
                                if options_text:
                                    msg += options_text
                        elif invalid_count == 2:
                            msg = "⚠️ We're still unable to process your response.\n\nPlease carefully follow the instructions provided."
                        else:
                            msg = "🚫 We couldn't understand your request after multiple attempts.\n\nThis session has been closed.\n\nPlease start a new conversation to continue."
                            session_record.is_archived = True
                            session_record.fsm_state = "CANCELLED"
                            fsm_state_after = "CANCELLED"
                            carry_unit.metadata.data["invalid_input_count"] = 0
                            
                        session_record.carry_unit_json = json.dumps(carry_unit.model_dump())
                        
                        # Preserve replay history & logs (PART 3 requirement)
                        error_log = ExecutionLog(
                            session_id=session_id,
                            business_id=business_id,
                            node_id=current_node_id_before or "unresolved",
                            module_name="invalid_input_handler",
                            inputs_json=json.dumps({"user_input": user_input}),
                            outputs_json=json.dumps({"error": str(e), "invalid_input_count": invalid_count}),
                            fsm_state_before=fsm_state_before,
                            fsm_state_after=fsm_state_after
                        )
                        db_session.add(error_log)
                        
                        snapshot = ExecutionSnapshot(
                            session_id=session_id,
                            node_id=current_node_id_before or "unresolved",
                            carry_unit_json=json.dumps(carry_unit.model_dump()),
                            fsm_state=fsm_state_after
                        )
                        db_session.add(snapshot)
                        await db_session.flush()
                        
                        session_record.locked_until = None
                        await db_session.flush()
                        
                        from src.services.dev_workspace import apply_dev_workspace_branding
                        branded_msg = await apply_dev_workspace_branding(db_session, business_id, msg)

                        return DispatchResponse(
                            session_id=session_id,
                            fsm_state_before=fsm_state_before,
                            fsm_state_after=fsm_state_after,
                            executed_nodes=[],
                            carry_unit=carry_unit,
                            messages_sent=[branded_msg],
                            ui=UiObject(
                                text=branded_msg,
                                actions=[UiAction(label=a.label, action=a.action) for a in get_operational_actions(fsm_state_after, carry_unit)],
                                metadata={}
                            ),
                            available_actions=[a.label for a in get_operational_actions(fsm_state_after, carry_unit)],
                            side_effects=[],
                            edge_logs=edge_logs,
                            routing_trace=routing_trace
                        )
                    else:
                        raise e

            except Exception as outer_e:
                raise outer_e
            finally:
                session_record.locked_until = None
                await db_session.flush()
