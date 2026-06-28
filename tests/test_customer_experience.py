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
    ExecutionSnapshot, ExecutionLog
)

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
async def test_dynamic_menu_and_custom_experience_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a business with a custom business catalog settings (business agnostic check)
        custom_catalog = {
            "title": "Elite Salon & Spa",
            "items": [
                {"id": "haircut", "name": "Classic Haircut", "price": 25.00},
                {"id": "massage", "name": "Therapeutic Massage", "price": 60.00}
            ]
        }
        
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Elite Salon",
            "whatsapp_number": "+19991112222"
        })
        biz_data = biz_res.json()["data"]
        biz_id = biz_data["id"]

        # Update the business catalog in db
        async with TestSessionLocal() as db:
            query = select(Business).where(Business.id == biz_id)
            res = await db.execute(query)
            business = res.scalar_one()
            business.catalog_json = json.dumps(custom_catalog)
            await db.commit()

        # Register workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = biz_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": biz_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]

        # Activate workflow
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+19991112222"
        })
        session_id = sess_res.json()["data"]["id"]

        # 2. Test dynamic menu rendering (Part 7 & Part 1)
        dispatch_start = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "/start"
        })
        assert dispatch_start.status_code == 200
        start_data = dispatch_start.json()["data"]
        
        # Verify custom catalog formatted menu is returned
        assert "ELITE SALON" in start_data["messages_sent"][0]
        assert "Classic Haircut" in start_data["messages_sent"][0]
        assert "$25.00" in start_data["messages_sent"][0]
        assert "Therapeutic Massage" in start_data["messages_sent"][0]
        assert "$60.00" in start_data["messages_sent"][0]

        # 3. Test universal error policy retries (Part 3)
        # First invalid input (does not match cart format 'N x M')
        dispatch_err1 = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "invalid_item_name_here"
        })
        assert dispatch_err1.status_code == 200
        err1_data = dispatch_err1.json()["data"]
        assert "❌ Invalid item selection." in err1_data["messages_sent"][0]
        assert err1_data["carry_unit"]["metadata"]["data"]["invalid_input_count"] == 1

        # Second invalid input
        dispatch_err2 = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "still_invalid_input"
        })
        assert dispatch_err2.status_code == 200
        err2_data = dispatch_err2.json()["data"]
        assert "⚠️ We're still unable to process your response." in err2_data["messages_sent"][0]
        assert err2_data["carry_unit"]["metadata"]["data"]["invalid_input_count"] == 2

        # Third invalid input (terminates session)
        dispatch_err3 = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "final_failed_input"
        })
        assert dispatch_err3.status_code == 200
        err3_data = dispatch_err3.json()["data"]
        assert "🚫 We couldn't understand your request after multiple attempts." in err3_data["messages_sent"][0]
        assert err3_data["fsm_state_after"] == "CANCELLED"
        
        # Verify active session is cleared (Part 3)
        active_res = await ac.get(f"/api/v1/sessions/active?business_id={biz_id}&customer_phone=%2B19991112222")
        assert active_res.status_code == 404

        # 4. Test FSM-Aware actions at payment (Part 2)
        # Create a new session
        sess_res2 = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+19991113333"
        })
        session_id2 = sess_res2.json()["data"]["id"]

        # Run start
        await ac.post(f"/api/v1/sessions/dispatch/{session_id2}", json={"user_input": "/start"})
        
        # Add item (Classic Haircut x 1)
        cart_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id2}", json={
            "user_input": "haircut x 1"
        })
        assert cart_res.status_code == 200
        assert "Classic Haircut x1" in cart_res.json()["data"]["messages_sent"][0]

        # Checkout
        checkout_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id2}", json={
            "user_input": "Checkout"
        })
        assert checkout_res.status_code == 200
        assert checkout_res.json()["data"]["fsm_state_after"] == "CHECKOUT"

        # Provide address
        addr_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id2}", json={
            "user_input": "123 Beauty Lane"
        })
        assert addr_res.status_code == 200
        addr_data = addr_res.json()["data"]
        assert addr_data["fsm_state_after"] == "PAYMENT"
        
        # Verify dynamic form definition in collect address output (Part 6)
        assert addr_data["ui"]["form"] is not None
        assert addr_data["ui"]["form"]["title"] == "Delivery Details"
        assert addr_data["ui"]["form"]["fields"][0]["name"] == "address"

        # Verify operational actions for PAYMENT state (Part 2)
        actions = addr_data["ui"]["actions"]
        actions_list = [a["action"] for a in actions]
        assert "RETRY_PAYMENT" in actions_list
        assert "CANCEL_ORDER" in actions_list
        assert "CONTACT_SUPPORT" in actions_list

        # Test "Contact Support" intercept action (Part 5)
        support_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id2}", json={
            "user_input": "Contact Support"
        })
        assert support_res.status_code == 200
        support_data = support_res.json()["data"]
        assert "Our support team will contact you shortly." in support_data["messages_sent"][0]
        assert support_data["fsm_state_after"] == "PAYMENT"  # Stays in same state

        # Confirm Payment -> moves to CONFIRMED state
        confirm_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id2}", json={
            "user_input": "CONFIRM_PAYMENT"
        })
        assert confirm_res.status_code == 200
        confirm_data = confirm_res.json()["data"]
        assert confirm_data["fsm_state_after"] == "CONFIRMED"

        # Verify actions for CONFIRMED state (DELIVERY_ACTIVE)
        # Because in the restaurant workflow, node_confirm automatically cascades to node_delivery, 
        # which sets logistics delivery_id and status to ASSIGNED.
        assert confirm_data["carry_unit"]["logistics"]["delivery_id"] is not None
        actions2 = confirm_data["ui"]["actions"]
        actions_list2 = [a["action"] for a in actions2]
        assert "TRACK_DELIVERY" in actions_list2
        assert "CONTACT_SUPPORT" in actions_list2
        assert "VIEW_ORDER" not in actions_list2  # Should only show Track Delivery when delivery active

        # REGRESSION AUDIT VERIFICATIONS (Bug 2, Bug 3)
        # A. Verify that active session lookup does not exclude CONFIRMED sessions
        active_lookup_res = await ac.get(f"/api/v1/sessions/active?business_id={biz_id}&customer_phone=%2B19991113333")
        assert active_lookup_res.status_code == 200
        assert active_lookup_res.json()["data"]["session_id"] == session_id2

        # B. Verify Track Delivery dispatch preserves session and displays correct status
        track_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id2}", json={
            "user_input": "TRACK_DELIVERY"
        })
        assert track_res.status_code == 200
        track_data = track_res.json()["data"]
        assert "Delivery Tracking" in track_data["messages_sent"][0]
        assert track_data["fsm_state_after"] == "CONFIRMED"

        # C. Verify Retry Payment executes without crash and displays new payment link
        # Create a new session
        sess_res3 = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+19991115555"
        })
        session_id3 = sess_res3.json()["data"]["id"]
        await ac.post(f"/api/v1/sessions/dispatch/{session_id3}", json={"user_input": "/start"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id3}", json={"user_input": "haircut x 1"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id3}", json={"user_input": "Checkout"})
        addr_res3 = await ac.post(f"/api/v1/sessions/dispatch/{session_id3}", json={"user_input": "123 Beauty Lane"})
        assert addr_res3.json()["data"]["fsm_state_after"] == "PAYMENT"

        # Dispatch RETRY_PAYMENT
        retry_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id3}", json={
            "user_input": "RETRY_PAYMENT"
        })
        assert retry_res.status_code == 200
        retry_data = retry_res.json()["data"]
        assert "Payment Required" in retry_data["messages_sent"][0]
        assert "pay.flowcore.io/link/" in retry_data["messages_sent"][0]
        assert retry_data["fsm_state_after"] == "PAYMENT"


@pytest.mark.asyncio
async def test_fsm_legality_recovery_handling():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Recovery Biz",
            "whatsapp_number": "+19991118888"
        })
        biz_data = biz_res.json()["data"]
        biz_id = biz_data["id"]

        # Register workflow
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
            "customer_phone": "+19991118888"
        })
        session_id = sess_res.json()["data"]["id"]

        # Force session FSM state to CART and current node to node_address (illegal state)
        async with TestSessionLocal() as db:
            query = select(SessionModel).where(SessionModel.id == session_id)
            res = await db.execute(query)
            session_record = res.scalar_one()
            session_record.fsm_state = "CART"
            session_record.current_node_id = "node_address"
            await db.commit()

        # Dispatch should not fail with 500/runtime error but recover with friendly message
        dispatch_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "123 Beauty Lane"
        })
        assert dispatch_res.status_code == 200
        res_data = dispatch_res.json()
        assert res_data["success"] is True
        msg = res_data["data"]["messages_sent"][0]
        assert "We encountered an issue processing your request." in msg
        assert "Please try again or restart your order." in msg

        # DB session state should remain rolled back to the state before the failed turn
        async with TestSessionLocal() as db:
            query = select(SessionModel).where(SessionModel.id == session_id)
            res = await db.execute(query)
            sess_record = res.scalar_one()
            assert sess_record.fsm_state == "CART"
            assert sess_record.current_node_id == "node_address"
