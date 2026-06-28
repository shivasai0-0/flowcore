import json
import time
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Business, WorkflowVersion, CompiledGraph, Session as SessionModel, ExecutionLog, ExecutionSnapshot, ExecutionMetric
from src.schemas.graph import WorkflowGraph
from src.schemas.workflow import WorkflowValidationReport
from src.schemas.carry_unit import CarryUnit
from src.schemas.session import ReplayResponse, ReplayStep
from src.schemas.simulation import (
    SimulationInputPayload, 
    SimulationResponse, 
    SimulationStepDetail, 
    SimulationReplaySummary
)
from src.engine.compiler import WorkflowCompiler
from src.engine.traversal import GraphTraversalEngine, TraversalError
from src.modules.registry import ModuleRegistry

logger = logging.getLogger("flowcore.simulation")

class ReplayVerifier:
    @staticmethod
    async def verify_replay(
        db_session: AsyncSession,
        session_record: SessionModel,
        executed_steps: List[SimulationStepDetail],
        workflow_version_id: str,
        business_id: str,
        initial_fsm: str,
        initial_carry_json: str,
        initial_node_id: Optional[str]
    ) -> SimulationReplaySummary:
        """
        Runs a dry-run replay step-by-step using the same inputs to verify consistency of FSM, nodes, and carry.
        """
        replay_session = SessionModel(
            id=f"replay_sess_{uuid.uuid4().hex[:8]}",
            business_id=business_id,
            customer_phone="+10000000000",
            fsm_state=initial_fsm,
            current_node_id=initial_node_id,
            carry_unit_json=initial_carry_json,
            workflow_version_id=workflow_version_id
        )
        db_session.add(replay_session)
        await db_session.flush()
        
        replay_match = True
        divergence_step = None
        mismatch_reason = None
        
        for step_idx, step_detail in enumerate(executed_steps):
            if step_detail.error:
                # If the step originally had a validation error, replay it to ensure it also errors out
                try:
                    rep_disp = await GraphTraversalEngine.dispatch_step(
                        db_session=db_session,
                        session_record=replay_session,
                        user_input=step_detail.input_received,
                        max_depth=10
                    )
                    replay_match = False
                    mismatch_reason = f"Step {step_idx + 1} expected an error but succeeded."
                    divergence_step = step_idx + 1
                    break
                except Exception as e:
                    # Expected error occurred; FSM and carry should not change
                    continue

            try:
                rep_disp = await GraphTraversalEngine.dispatch_step(
                    db_session=db_session,
                    session_record=replay_session,
                    user_input=step_detail.input_received,
                    max_depth=10
                )
                
                # 1. Verify executed nodes
                if rep_disp.executed_nodes != step_detail.executed_nodes:
                    replay_match = False
                    mismatch_reason = f"Executed nodes mismatch. Expected: {step_detail.executed_nodes}, got: {rep_disp.executed_nodes}"
                    divergence_step = step_idx + 1
                    break
                
                # 2. Verify FSM progression
                if replay_session.fsm_state != step_detail.fsm_state_after:
                    replay_match = False
                    mismatch_reason = f"FSM state mismatch. Expected: {step_detail.fsm_state_after}, got: {replay_session.fsm_state}"
                    divergence_step = step_idx + 1
                    break
                    
                # 3. Verify carry unit order total
                rep_carry = json.loads(replay_session.carry_unit_json)
                expected_carry = step_detail.carry_unit_snapshot
                if rep_carry.get("order", {}).get("total") != expected_carry.get("order", {}).get("total"):
                    replay_match = False
                    mismatch_reason = f"Carry unit order total mismatch. Expected: {expected_carry.get('order', {}).get('total')}, got: {rep_carry.get('order', {}).get('total')}"
                    divergence_step = step_idx + 1
                    break
                    
            except Exception as e:
                replay_match = False
                mismatch_reason = f"Replay execution failed with error: {str(e)}"
                divergence_step = step_idx + 1
                break
                
        return SimulationReplaySummary(
            replay_match=replay_match,
            divergence_step=divergence_step,
            mismatch_reason=mismatch_reason
        )


class SimulationEngine:
    @staticmethod
    async def run_simulation(
        db_session: AsyncSession,
        payload: SimulationInputPayload
    ) -> SimulationResponse:
        """
        Runs an input-driven workflow simulation and stress-testing verification.
        Supports strict, tolerant, and replay validation modes.
        Operates entirely inside a database savepoint rollback transaction to prevent side effects.
        """
        time_overall_start = time.time()
        
        # 0. Backward compatibility translation
        if not payload.workflow_graph and payload.graph:
            payload.workflow_graph = payload.graph
        if not payload.inputs and payload.simulated_inputs:
            payload.inputs = payload.simulated_inputs
            
        # 1. Validation phase (if graph is provided)
        validation_report = None
        compiled_graph_dict = None
        business_id = None
        workflow_version_id = None
        
        if payload.workflow_graph:
            compiled, report = WorkflowCompiler.validate_and_compile(payload.workflow_graph)
            validation_report = report
            if not report.is_valid and payload.strict_validation:
                return SimulationResponse(
                    success=False,
                    test_name="FlowCore Simulation",
                    simulation_mode=payload.simulation_mode,
                    runtime_errors=["Workflow graph validation failed."],
                    validation_report=report,
                    execution_timings={"overall_latency_ms": int((time.time() - time_overall_start) * 1000)}
                )
            compiled_graph_dict = compiled
            business_id = payload.workflow_graph.business_id
        
        executed_steps: List[SimulationStepDetail] = []
        executed_nodes: List[str] = []
        fsm_progression: List[str] = []
        runtime_errors: List[str] = []
        
        # Start isolated savepoint transaction
        async with db_session.begin_nested() as savepoint:
            try:
                # 2. Resolve or create session
                session_record = None
                
                if payload.session_id:
                    # Load existing session
                    sess_query = select(SessionModel).where(SessionModel.id == payload.session_id)
                    sess_res = await db_session.execute(sess_query)
                    session_record = sess_res.scalar_one_or_none()
                    if not session_record:
                        raise ValueError(f"Session ID '{payload.session_id}' not found.")
                    business_id = session_record.business_id
                    workflow_version_id = session_record.workflow_version_id
                    
                    # Fetch compiled graph for this session
                    cg_query = select(CompiledGraph).where(CompiledGraph.workflow_version_id == workflow_version_id)
                    cg_res = await db_session.execute(cg_query)
                    cg_record = cg_res.scalar_one_or_none()
                    if cg_record:
                        compiled_graph_dict = json.loads(cg_record.compiled_json)
                else:
                    # Create temporary session for dry-run simulation
                    if not business_id:
                        business_id = payload.business_id or "sim_biz_123"
                        
                    # Create temporary active workflow version
                    temp_version = WorkflowVersion(
                        business_id=business_id,
                        version_number=9999,
                        status="ACTIVE",
                        graph_json=json.dumps(payload.workflow_graph.model_dump()) if payload.workflow_graph else "{}",
                        is_current=False
                    )
                    db_session.add(temp_version)
                    await db_session.flush()
                    workflow_version_id = temp_version.id
                    
                    # Store compiled graph
                    if not compiled_graph_dict and payload.workflow_graph:
                        compiled_graph_dict = {
                            "workflow_version_id": temp_version.id,
                            "business_id": business_id,
                            "version_number": 9999,
                            "entry_node_id": payload.workflow_graph.entry_node_id,
                            "nodes": {nid: n.model_dump() for nid, n in payload.workflow_graph.nodes.items()},
                            "edges": [e.model_dump() for e in payload.workflow_graph.edges],
                            "fsm_transition_table": payload.workflow_graph.fsm_transition_table
                        }
                    
                    if compiled_graph_dict:
                        temp_compiled = CompiledGraph(
                            workflow_version_id=temp_version.id,
                            business_id=business_id,
                            compiled_json=json.dumps(compiled_graph_dict)
                        )
                        db_session.add(temp_compiled)
                        await db_session.flush()
                    
                    # Create temporary session
                    initial_carry_unit = CarryUnit(
                        session={
                            "session_id": f"sim_sess_{uuid.uuid4().hex[:8]}",
                            "customer_phone": "+10000000000",
                            "business_id": business_id,
                            "workflow_version_id": temp_version.id,
                            "session_started_at": datetime.utcnow().isoformat()
                        }
                    )
                    
                    session_record = SessionModel(
                        id=initial_carry_unit.session.session_id,
                        business_id=business_id,
                        customer_phone="+10000000000",
                        fsm_state="START",
                        current_node_id=None,
                        carry_unit_json=json.dumps(initial_carry_unit.model_dump()),
                        workflow_version_id=temp_version.id
                    )
                    db_session.add(session_record)
                    await db_session.flush()
                
                # Keep copy of initial FSM and Carry Unit state for replay comparison
                initial_fsm = session_record.fsm_state
                initial_carry_json = session_record.carry_unit_json
                initial_node_id = session_record.current_node_id
                
                # Load compiled ExecutableGraph for module name mapping
                from src.engine.compiler.executable_graph import ExecutableGraph
                executable = ExecutableGraph(compiled_graph_dict) if compiled_graph_dict else None
                
                # 3. Traversal Execution loop
                step_limit = min(payload.max_steps, len(payload.inputs))
                for step_idx in range(step_limit):
                    if session_record.fsm_state in {"CONFIRMED", "CANCELLED"}:
                        break
                    user_input = payload.inputs[step_idx]
                    fsm_before = session_record.fsm_state
                    carry_before = json.loads(session_record.carry_unit_json)
                    node_id_before = session_record.current_node_id
                    
                    time_step_start = time.time()
                    step_error = None
                    dispatch_res = None
                    
                    # Create step savepoint to rollback on failure in tolerant mode
                    step_savepoint = await db_session.begin_nested()
                    try:
                        dispatch_res = await GraphTraversalEngine.dispatch_step(
                            db_session=db_session,
                            session_record=session_record,
                            user_input=user_input,
                            max_depth=10
                        )
                        
                        # Validate FSM progression
                        fsm_after = session_record.fsm_state
                        
                        # Check if step successfully processed/transitioned (or if it halted/fallback)
                        if not dispatch_res.executed_nodes and payload.strict_validation:
                            raise TraversalError("Input failed to resolve any transition edges.")
                        
                        # Commit step savepoint
                        await step_savepoint.commit()
                        await db_session.refresh(session_record)
                        
                    except Exception as e:
                        # Rollback step changes
                        await step_savepoint.rollback()
                        await db_session.refresh(session_record)
                        step_error = str(e)
                        from src.engine.exceptions import FlowCoreRuntimeError
                        if isinstance(e, FlowCoreRuntimeError) and e.error_code == "UNRESOLVED_ROUTING":
                            step_error = "Input failed to resolve any transition edges. " + step_error
                        dispatch_res = None
                        runtime_errors.append(f"Step {step_idx + 1} Error: {step_error}")
                        
                        if payload.simulation_mode == "strict":
                            # Stop immediately on strict mode error
                            executed_steps.append(
                                SimulationStepDetail(
                                    step_number=step_idx + 1,
                                    input_received=user_input,
                                    fsm_state_before=fsm_before,
                                    fsm_state_after=fsm_before,
                                    latency_ms=int((time.time() - time_step_start) * 1000),
                                    error=step_error
                                )
                            )
                            break
                    
                    # Record step detail
                    if dispatch_res:
                        latency = int((time.time() - time_step_start) * 1000)
                        
                        # Determine condition routing decisions
                        routing_decision = None
                        if dispatch_res.executed_nodes:
                            routing_decision = {
                                "from_node": node_id_before,
                                "transitioned_to": dispatch_res.executed_nodes[0]
                            }
                            executed_nodes.extend(dispatch_res.executed_nodes)
                            fsm_progression.append(session_record.fsm_state)
                            
                        last_node_id = dispatch_res.executed_nodes[-1] if dispatch_res.executed_nodes else None
                        last_module_name = None
                        if last_node_id and executable:
                            node_obj = executable.get_node(last_node_id)
                            if node_obj:
                                last_module_name = node_obj.module_name
 
                        # Compute carry diff
                        def compute_diff(before: dict, after: dict) -> dict:
                            diff = {}
                            for k, v in after.items():
                                if before.get(k) != v:
                                    if isinstance(v, dict) and isinstance(before.get(k), dict):
                                        sub_diff = compute_diff(before[k], v)
                                        if sub_diff:
                                            diff[k] = sub_diff
                                    else:
                                        diff[k] = v
                            return diff
                            
                        step_snapshot = json.loads(session_record.carry_unit_json)
                        carry_diff = compute_diff(carry_before, step_snapshot)
                        
                        executed_steps.append(
                            SimulationStepDetail(
                                step_number=step_idx + 1,
                                input_received=user_input,
                                node_id=session_record.current_node_id,
                                module_name=last_module_name,
                                carry_unit_snapshot=step_snapshot,
                                carry_unit=CarryUnit.model_validate(step_snapshot),
                                fsm_state_before=fsm_before,
                                fsm_state_after=session_record.fsm_state,
                                fsm_state=session_record.fsm_state,
                                messages_sent=dispatch_res.messages_sent,
                                executed_nodes=dispatch_res.executed_nodes,
                                routing_decision=routing_decision,
                                latency_ms=latency,
                                carry_diff=carry_diff,
                                fsm_transition=fsm_before if fsm_before == session_record.fsm_state else fsm_before,
                                side_effects=[se["side_effect"] for se in dispatch_res.side_effects],
                                edge_logs=dispatch_res.edge_logs
                            )
                        )
                    else:
                        # Error step recorded in tolerant mode
                        executed_steps.append(
                            SimulationStepDetail(
                                step_number=step_idx + 1,
                                input_received=user_input,
                                fsm_state_before=fsm_before,
                                fsm_state_after=fsm_before,
                                fsm_state=fsm_before,
                                latency_ms=int((time.time() - time_step_start) * 1000),
                                error=step_error
                            )
                        )
                
                # 4. Optional Replay Validation checks
                replay_summary = None
                if (payload.replay_validation or payload.simulation_mode == "replay") and not runtime_errors:
                    replay_summary = await ReplayVerifier.verify_replay(
                        db_session=db_session,
                        session_record=session_record,
                        executed_steps=executed_steps,
                        workflow_version_id=workflow_version_id,
                        business_id=business_id,
                        initial_fsm=initial_fsm,
                        initial_carry_json=initial_carry_json,
                        initial_node_id=initial_node_id
                    )
                
                # Rollback everything to keep the DB state clean and side-effect free
                await savepoint.rollback()
                
                # Compute success
                success = (len(runtime_errors) == 0)
                
                return SimulationResponse(
                    success=success,
                    test_name="FlowCore Simulation",
                    simulation_mode=payload.simulation_mode,
                    executed_steps=executed_steps,
                    executed_nodes=executed_nodes,
                    fsm_progression=fsm_progression,
                    runtime_errors=runtime_errors,
                    replay_results=replay_summary,
                    validation_report=validation_report,
                    execution_timings={"overall_latency_ms": int((time.time() - time_overall_start) * 1000)},
                    steps=executed_steps,
                    error=runtime_errors[0] if runtime_errors else None
                )
                
            except Exception as e:
                await savepoint.rollback()
                raise e

    @staticmethod
    async def simulate_workflow(
        db_session: AsyncSession,
        business_id: str,
        graph: WorkflowGraph,
        simulated_inputs: List[str]
    ) -> Any:
        """
        Deprecated. Kept temporarily for backward compatibility with old unit tests.
        Delegates to modern run_simulation implementation.
        """
        payload = SimulationInputPayload(
            workflow_graph=graph,
            inputs=simulated_inputs,
            simulation_mode="tolerant"
        )
        res = await SimulationEngine.run_simulation(db_session, payload)
        
        # Convert to old WorkflowSimulationResponse schema structure
        from src.schemas.workflow import WorkflowSimulationResponse, WorkflowSimulationStep
        steps = []
        for step in res.executed_steps:
            if not step.error:
                steps.append(
                    WorkflowSimulationStep(
                        step_number=step.step_number,
                        input_received=step.input_received,
                        node_id=step.node_id or "",
                        module_name=step.module_name or "",
                        carry_unit=CarryUnit.model_validate(step.carry_unit_snapshot),
                        fsm_state=step.fsm_state_after,
                        messages_sent=step.messages_sent
                    )
                )
        return WorkflowSimulationResponse(
            success=res.success,
            steps=steps,
            validation_report=res.validation_report or WorkflowValidationReport(
                is_valid=True, errors=[], cycle_detected=False, connectivity_check=True, fsm_check=True, contracts_check=True
            ),
            error=res.runtime_errors[0] if res.runtime_errors else None
        )


class ReplayEngine:
    @staticmethod
    async def get_session_replay(
        db_session: AsyncSession,
        session_id: str
    ) -> ReplayResponse:
        """
        Loads the chronological execution trace logs of a session and formats them.
        Useful for auditability, reproducing bug states, and compliance.
        """
        # Load session
        session_query = select(SessionModel).where(SessionModel.id == session_id)
        res = await db_session.execute(session_query)
        session_record = res.scalar_one_or_none()
        if not session_record:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        # Load execution logs chronologically
        logs_query = select(ExecutionLog).where(ExecutionLog.session_id == session_id).order_by(ExecutionLog.executed_at.asc())
        logs_res = await db_session.execute(logs_query)
        log_records = logs_res.scalars().all()

        # Load execution metrics chronologically to match latency
        metrics_query = select(ExecutionMetric).where(ExecutionMetric.session_id == session_id).order_by(ExecutionMetric.timestamp.asc())
        metrics_res = await db_session.execute(metrics_query)
        metrics_records = list(metrics_res.scalars().all())

        # Match metrics to logs chronologically by node_id
        node_metrics = {}
        for m in metrics_records:
            node_metrics.setdefault(m.node_id, []).append(m.latency_ms)

        # Load execution snapshots to calculate carry_diff
        snapshots_query = select(ExecutionSnapshot).where(ExecutionSnapshot.session_id == session_id).order_by(ExecutionSnapshot.timestamp.asc())
        snapshots_res = await db_session.execute(snapshots_query)
        snapshot_records = list(snapshots_res.scalars().all())

        # Match snapshots to logs chronologically by node_id
        node_snapshots = {}
        for s in snapshot_records:
            node_snapshots.setdefault(s.node_id, []).append(s.carry_unit_json)

        # Helper to compute carry diff
        def compute_diff(before: dict, after: dict) -> dict:
            diff = {}
            for k, v in after.items():
                if before.get(k) != v:
                    if isinstance(v, dict) and isinstance(before.get(k), dict):
                        sub_diff = compute_diff(before[k], v)
                        if sub_diff:
                            diff[k] = sub_diff
                    else:
                        diff[k] = v
            return diff

        # We also need the initial carry unit state to calculate diff for the first step
        final_carry = json.loads(session_record.carry_unit_json)
        last_carry = {"session": final_carry.get("session", {})}

        replay_steps = []
        for log in log_records:
            inputs = json.loads(log.inputs_json)
            outputs = json.loads(log.outputs_json)
            
            # Fetch latency
            latency = None
            if log.node_id in node_metrics and node_metrics[log.node_id]:
                latency = node_metrics[log.node_id].pop(0)

            # Fetch carry diff
            carry_diff = None
            if log.node_id in node_snapshots and node_snapshots[log.node_id]:
                snap_json_str = node_snapshots[log.node_id].pop(0)
                current_carry = json.loads(snap_json_str)
                carry_diff = compute_diff(last_carry, current_carry)
                last_carry = current_carry
            else:
                carry_diff = {}

            # FSM transition string
            fsm_trans = f"{log.fsm_state_before} -> {log.fsm_state_after}" if log.fsm_state_before != log.fsm_state_after else log.fsm_state_before

            # Fetch side effects from outputs/registry
            side_effects_list = []
            if ModuleRegistry.exists(log.module_name):
                module = ModuleRegistry.get(log.module_name)
                if module.contract.side_effects:
                    side_effects_list = list(module.contract.side_effects)

            # Routing decision: if there's a next log, the routing decision is that node's ID
            routing_dec = None
            log_idx = list(log_records).index(log)
            if log_idx + 1 < len(log_records):
                routing_dec = log_records[log_idx + 1].node_id

            replay_steps.append(
                ReplayStep(
                    node_id=log.node_id,
                    module_name=log.module_name,
                    inputs=inputs,
                    outputs=outputs,
                    fsm_state_before=log.fsm_state_before,
                    fsm_state_after=log.fsm_state_after,
                    executed_at=log.executed_at,
                    latency_ms=latency,
                    routing_decision=routing_dec,
                    carry_diff=carry_diff,
                    fsm_transition=fsm_trans,
                    side_effects=side_effects_list,
                    edge_logs=[]
                )
            )

        carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))

        return ReplayResponse(
            session_id=session_id,
            trace=replay_steps,
            final_carry_unit=carry_unit,
            final_fsm_state=session_record.fsm_state
        )
