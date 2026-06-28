import asyncio
import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.main import app
from src.database import Base, get_db
from src.models import (
    Business, WorkflowVersion, Session as SessionModel, 
    ExecutionSnapshot, ExecutionLog, SharedCustomerContext, EventStoreRecord
)
from src.engine.registries.capability_registry import CapabilityRegistry
from src.engine.registries.event_registry import EventRegistry
from src.engine.registries.provider_registry import ProviderRegistry
from src.engine.events.event_bus import event_bus, WorkflowEvent
from src.schemas.graph import WorkflowGraph, WorkflowNode, WorkflowEdge, EdgeCondition
from src.engine.compiler import WorkflowCompiler

# Isolated in-memory testing database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)

@pytest.mark.asyncio
async def test_registry_operations():
    # 1. CapabilityRegistry retrieve capability specs by version
    spec = CapabilityRegistry.get("show_catalog", "1.0")
    assert spec is not None
    assert spec["module_name"] == "show_catalog"
    assert spec["category"] == "Core"
    
    # Invalid specs
    assert CapabilityRegistry.get("show_catalog", "2.0") is None
    assert CapabilityRegistry.get("non_existent_module") is None

    # 2. EventRegistry Validate event payloads
    assert EventRegistry.validate_payload("ORDER_CREATED", {"order_id": "123", "total": 45.50})
    with pytest.raises(ValueError):
        EventRegistry.validate_payload("ORDER_CREATED", {"order_id": "123"})
        
    # Unregistered event type warns/skips and returns True
    assert EventRegistry.validate_payload("SOME_CUSTOM_EVENT", {"any": "thing"})

    # 3. ProviderRegistry configuration lookups
    categories = ProviderRegistry.get_categories()
    assert "payment" in categories
    assert "delivery" in categories
    assert "notification" in categories
    
    providers = ProviderRegistry.get_providers_in_category("payment")
    assert "COD" in providers
    assert "Razorpay" in providers
    
    req_config = ProviderRegistry.get_required_config("payment", "Razorpay")
    assert "key_id" in req_config
    assert "key_secret" in req_config
    
    assert ProviderRegistry.validate_provider_config("payment", "Razorpay", {"key_id": "1", "key_secret": "2"})
    with pytest.raises(ValueError):
        ProviderRegistry.validate_provider_config("payment", "Razorpay", {"key_id": "1"})

@pytest.mark.asyncio
async def test_decoupled_providers():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business with decoupled provider configurations
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Decoupled Biz",
            "whatsapp_number": "+19992223333"
        })
        biz_data = biz_res.json()["data"]
        biz_id = biz_data["id"]

        # Update the business catalog, type, and providers configuration in database
        providers_config = {
            "payment_provider": "Stripe",
            "delivery_provider": "Shadowfax",
            "notification_provider": "SMS"
        }
        async with TestSessionLocal() as db:
            query = select(Business).where(Business.id == biz_id)
            res = await db.execute(query)
            business = res.scalar_one()
            business.providers_json = json.dumps(providers_config)
            await db.commit()

        # Register standard restaurant workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = biz_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": biz_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+19992223333"
        })
        session_id = sess_res.json()["data"]["id"]

        # 1. Dispatch /start
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})
        # 2. Add Margherita Pizza
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "1 x 1"})
        # 3. Checkout
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "Checkout"})
        # 4. Provide address -> should transition to PAYMENT, rendering Stripe payment provider!
        payment_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "123 Beauty Lane"})
        payment_data = payment_res.json()["data"]
        # messages_sent contains:
        # [0] "Delivery Address Confirmed" (from collect_address node)
        # [1] "Payment Required (Stripe)" (from create_payment node)
        assert "Payment Required (Stripe)" in payment_data["messages_sent"][1]
        assert "checkout.stripe.com" in payment_data["messages_sent"][1]

        # 5. Confirm Payment -> should trigger shadowfax delivery & SMS notification!
        confirm_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "CONFIRM_PAYMENT"})
        confirm_data = confirm_res.json()["data"]
        # messages_sent contains:
        # [0] "Payment Received" (from confirm_payment node)
        # [1] "Delivery Partner Assigned (Shadowfax)" (from create_delivery node)
        # [2] "We'll notify you via SMS" (from notify_customer node)
        assert "Delivery Partner Assigned (Shadowfax)" in confirm_data["messages_sent"][1]
        assert "We'll notify you via SMS" in confirm_data["messages_sent"][2]

@pytest.mark.asyncio
async def test_event_triggers_and_bus():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Event Trigger Biz",
            "whatsapp_number": "+19993334444"
        })
        biz_data = biz_res.json()["data"]
        biz_id = biz_data["id"]

        # Register standard ordering workflow (Workflow 1)
        with open("examples/restaurant_workflow.json", "r") as f:
            graph_order = json.load(f)
        graph_order["business_id"] = biz_id

        reg_order = await ac.post("/api/v1/workflows/register", json={
            "business_id": biz_id,
            "graph": graph_order
        })
        order_version_id = reg_order.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{order_version_id}")

        # Register feedback workflow (Workflow 2) triggered on DELIVERY_ASSIGNED
        feedback_graph = {
            "business_id": biz_id,
            "version_number": 1,
            "entry_node_id": "feedback_start",
            "trigger_event": "DELIVERY_ASSIGNED",  # Subscribed event trigger
            "nodes": {
                "feedback_start": {
                    "id": "feedback_start",
                    "module_name": "send_message",
                    "config": {
                        "text": "How was your delivery? Reply with score 1 to 5."
                    },
                    "fsm_transition_to": "CONFIRMED"
                }
            },
            "edges": [],
            "fsm_transition_table": {
                "START": {
                    "CONFIRMED": "send_message"
                }
            }
        }

        reg_feedback = await ac.post("/api/v1/workflows/register", json={
            "business_id": biz_id,
            "graph": feedback_graph
        })
        feedback_version_id = reg_feedback.json()["data"]["workflow_version_id"]
        
        # Make the feedback workflow active in database!
        async with TestSessionLocal() as db:
            wv = await db.get(WorkflowVersion, feedback_version_id)
            wv.status = "ACTIVE"
            await db.commit()

        # Start ordering session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+19993334444"
        })
        order_session_id = sess_res.json()["data"]["id"]

        # Drive ordering session to delivery assignment
        await ac.post(f"/api/v1/sessions/dispatch/{order_session_id}", json={"user_input": "/start"})
        await ac.post(f"/api/v1/sessions/dispatch/{order_session_id}", json={"user_input": "1 x 1"})
        await ac.post(f"/api/v1/sessions/dispatch/{order_session_id}", json={"user_input": "Checkout"})
        await ac.post(f"/api/v1/sessions/dispatch/{order_session_id}", json={"user_input": "123 Pizza St"})
        
        # Confirming payment triggers DELIVERY_ASSIGNED event!
        # This event goes through EventBus, finds Feedback Workflow, creates Feedback Session, and dispatches!
        confirm_res = await ac.post(f"/api/v1/sessions/dispatch/{order_session_id}", json={"user_input": "CONFIRM_PAYMENT"})
        assert confirm_res.status_code == 200

        # Wait briefly for background execution
        await asyncio.sleep(0.5)

        # Check if feedback session was spawned and traversed automatically!
        async with TestSessionLocal() as db:
            query = select(SessionModel).where(
                SessionModel.business_id == biz_id,
                SessionModel.customer_phone == "+19993334444",
                SessionModel.workflow_version_id == feedback_version_id
            )
            res = await db.execute(query)
            feedback_session = res.scalar_one_or_none()
            assert feedback_session is not None
            assert feedback_session.fsm_state == "CONFIRMED"
            
            # Check execution log for feedback_start node
            log_query = select(ExecutionLog).where(
                ExecutionLog.session_id == feedback_session.id,
                ExecutionLog.node_id == "feedback_start"
            )
            log_res = await db.execute(log_query)
            log_rec = log_res.scalar_one_or_none()
            assert log_rec is not None
            assert log_rec.node_id == "feedback_start"

@pytest.mark.asyncio
async def test_shared_customer_context():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Loyalty Biz",
            "whatsapp_number": "+19994445555"
        })
        biz_id = biz_res.json()["data"]["id"]

        # Register standard ordering workflow (Workflow 1)
        with open("examples/restaurant_workflow.json", "r") as f:
            graph_order = json.load(f)
        graph_order["business_id"] = biz_id

        reg_order = await ac.post("/api/v1/workflows/register", json={
            "business_id": biz_id,
            "graph": graph_order
        })
        order_version_id = reg_order.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{order_version_id}")

        # Start first session to initialize SharedCustomerContext
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+19994445555"
        })
        session_id = sess_res.json()["data"]["id"]

        # Dispatch first step to initialize SharedCustomerContext in traversal
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})

        # Manually mutate loyalty points and verify updates are persisted
        async with TestSessionLocal() as db:
            context_query = select(SharedCustomerContext).where(
                SharedCustomerContext.customer_id == "+19994445555",
                SharedCustomerContext.business_id == biz_id
            )
            context_res = await db.execute(context_query)
            context_row = context_res.scalar_one_or_none()
            assert context_row is not None  # Initialized automatically on first dispatch or session creation check in traversal
            
            # Set initial loyalty points
            context_row.loyalty_points = 150
            await db.commit()

        # Dispatch step - traversal loads the shared context into carry unit!
        dispatch_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "1 x 1"})
        dispatch_data = dispatch_res.json()["data"]
        # Verify carry unit has loyalty points loaded under customer.shared_context
        assert dispatch_data["carry_unit"]["customer"]["shared_context"]["loyalty_points"] == 150

        # Dispatch next step that updates loyalty points
        async with TestSessionLocal() as db:
            context_query = select(SharedCustomerContext).where(
                SharedCustomerContext.customer_id == "+19994445555",
                SharedCustomerContext.business_id == biz_id
            )
            context_res = await db.execute(context_query)
            context_row = context_res.scalar_one()
            assert context_row.loyalty_points == 150

@pytest.mark.asyncio
async def test_node_centric_compilation_fallback():
    # Construct a valid node-centric workflow graph (flat edges list is empty/missing, nodes have nested edges)
    node_centric_graph_dict = {
        "business_id": "biz_node_centric_123",
        "version_number": 1,
        "entry_node_id": "node_a",
        "nodes": {
            "node_a": {
                "id": "node_a",
                "module_name": "show_menu",
                "config": {"text": "A"},
                "fsm_transition_to": "MENU",
                "edges": [
                    {
                        "to_node": "node_b",
                        "condition": {"type": "always"}
                    }
                ]
            },
            "node_b": {
                "id": "node_b",
                "module_name": "send_message",
                "config": {"text": "B"},
                "fsm_transition_to": "CONFIRMED",
                "edges": []
            }
        },
        "edges": [],
        "fsm_transition_table": {
            "START": {
                "MENU": "show_menu"
            },
            "MENU": {
                "CONFIRMED": "send_message"
            }
        }
    }
    
    graph = WorkflowGraph.model_validate(node_centric_graph_dict)
    
    # Run compiler validation and compilation
    compiled, report = WorkflowCompiler.validate_and_compile(graph)
    
    assert report.is_valid
    assert len(compiled["edges"]) == 1
    assert compiled["edges"][0]["from_node"] == "node_a"
    assert compiled["edges"][0]["to_node"] == "node_b"
    assert compiled["edges"][0]["condition"]["type"] == "always"
