import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.main import app
from src.database import Base, get_db
from src.models import Business, WorkflowVersion, Session as SessionModel, ExecutionLog, ExecutionSnapshot
from src.schemas.carry_unit import CarryUnit

# Set up isolated in-memory testing database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

import pytest_asyncio

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Initializes schema on in-memory db before each test."""
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)

@pytest.mark.asyncio
async def test_concurrency_locking():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Locking Biz",
            "whatsapp_number": "+19991112222"
        })
        business_id = biz_res.json()["data"]["id"]

        # Register workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": business_id,
            "customer_phone": "+19991112222"
        })
        session_id = sess_res.json()["data"]["id"]

        # Lock the session manually by updating database
        async with TestSessionLocal() as db:
            query = select(SessionModel).where(SessionModel.id == session_id)
            res = await db.execute(query)
            session_record = res.scalar_one()
            session_record.locked_until = datetime.utcnow() + timedelta(seconds=30)
            await db.commit()

        # Dispatch should throw SESSION_LOCKED
        dispatch_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "/start"
        })
        assert dispatch_res.status_code == 400
        res_data = dispatch_res.json()
        assert res_data["success"] is False
        assert res_data["error"]["error_code"] == "SESSION_LOCKED"

@pytest.mark.asyncio
async def test_terminal_state_lockout():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Terminal Biz",
            "whatsapp_number": "+19991113333"
        })
        business_id = biz_res.json()["data"]["id"]

        # Register workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": business_id,
            "customer_phone": "+19991113333"
        })
        session_id = sess_res.json()["data"]["id"]

        # Run through the entire traversal to CONFIRMED state
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "1 x 1"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "Checkout"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "123 Cherry Lane"})
        confirm_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "CONFIRM_PAYMENT"})
        
        assert confirm_res.status_code == 200
        assert confirm_res.json()["data"]["fsm_state_after"] == "CONFIRMED"

        # Subsequent dispatch should fail with TERMINAL_STATE_LOCKED
        blocked_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})
        assert blocked_res.status_code == 400
        assert blocked_res.json()["error"]["error_code"] == "TERMINAL_STATE_LOCKED"

@pytest.mark.asyncio
async def test_payment_idempotency_enforcement():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Idempotency Biz",
            "whatsapp_number": "+19991114444"
        })
        business_id = biz_res.json()["data"]["id"]

        # Register workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": business_id,
            "customer_phone": "+19991114444"
        })
        session_id = sess_res.json()["data"]["id"]

        # Get to PAYMENT state
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "1 x 1"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "Checkout"})
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "123 Cherry Lane"})

        # First confirm payment succeeds
        p1 = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "CONFIRM_PAYMENT"})
        assert p1.status_code == 200
        assert p1.json()["data"]["fsm_state_after"] == "CONFIRMED"

        # Force session FSM state back to PAYMENT and try payment confirm again.
        # This will test ConfirmPaymentModule execution logic with carry status already SUCCESS.
        async with TestSessionLocal() as db:
            query = select(SessionModel).where(SessionModel.id == session_id)
            res = await db.execute(query)
            session_record = res.scalar_one()
            session_record.fsm_state = "PAYMENT"
            session_record.current_node_id = "node_payment"
            
            # Delete execution log for node_confirm to bypass idempotency check
            from sqlalchemy import delete
            await db.execute(delete(ExecutionLog).where(
                ExecutionLog.session_id == session_id,
                ExecutionLog.node_id == "node_confirm"
            ))
            await db.commit()

        p2 = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "CONFIRM_PAYMENT"})
        assert p2.status_code == 400
        assert p2.json()["error"]["error_code"] == "PAYMENT_ALREADY_COMPLETED"

@pytest.mark.asyncio
async def test_input_normalization_and_catalog():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business and configure its catalog settings (menu items)
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Normalization Biz",
            "whatsapp_number": "+19991115555"
        })
        business_id = biz_res.json()["data"]["id"]

        # Update business catalog configuration
        catalog_payload = {
            "catalog": {
                "items": [
                    {"id": "1", "name": "Margherita Pizza", "price": 12.00, "synonyms": ["pizza", "margherita"]},
                    {"id": "2", "name": "French Fries", "price": 4.50, "synonyms": ["fries", "chips"]}
                ]
            }
        }
        cat_res = await ac.put(f"/api/v1/businesses/{business_id}/catalog", json=catalog_payload)
        assert cat_res.status_code == 200

        # Register workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": business_id,
            "customer_phone": "+19991115555"
        })
        session_id = sess_res.json()["data"]["id"]

        # Dispatch to MENU state
        await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})

        # Dispatch cart input with strict format: <item_index_or_name> x <quantity>
        # "1 x 2" means item #1 (Margherita Pizza), quantity 2
        cart_dispatch = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "1 x 2"
        })
        assert cart_dispatch.status_code == 200
        res_data = cart_dispatch.json()["data"]
        items = res_data["carry_unit"]["order"]["items"]
        assert len(items) == 1
        assert items[0]["item_id"] == "1"
        assert items[0]["quantity"] == 2
        assert res_data["carry_unit"]["order"]["total"] == 24.00

        # Test invalid inputs
        # Move back to MENU FSM state to test other inputs
        async with TestSessionLocal() as db:
            query = select(SessionModel).where(SessionModel.id == session_id)
            res = await db.execute(query)
            session_record = res.scalar_one()
            session_record.fsm_state = "MENU"
            session_record.current_node_id = "node_cart"
            await db.commit()

        # Malformed syntax input (First invalid input - no 'x' separator)
        bad_syntax_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "margherita pizza"
        })
        assert bad_syntax_res.status_code == 200
        data1 = bad_syntax_res.json()["data"]
        assert "❌" in data1["messages_sent"][0]
        assert data1["carry_unit"]["metadata"]["data"]["invalid_input_count"] == 1

        # Unknown product (Second invalid input - 'sushi' is not in the menu)
        unknown_prod_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "sushi x 1"
        })
        assert unknown_prod_res.status_code == 200
        data2 = unknown_prod_res.json()["data"]
        assert "⚠️" in data2["messages_sent"][0]
        assert data2["carry_unit"]["metadata"]["data"]["invalid_input_count"] == 2

        # Invalid quantity (Third invalid input - cancels session)
        bad_qty_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "pizza x 0"
        })
        assert bad_qty_res.status_code == 200
        data3 = bad_qty_res.json()["data"]
        assert "🚫" in data3["messages_sent"][0]
        assert data3["fsm_state_after"] == "CANCELLED"

@pytest.mark.asyncio
async def test_session_lifecycle_and_timeouts():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Lifecycle Biz",
            "whatsapp_number": "+19991116666"
        })
        business_id = biz_res.json()["data"]["id"]

        # Register workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": business_id,
            "customer_phone": "+19991116666"
        })
        session_id = sess_res.json()["data"]["id"]

        # Test Inspect session
        inspect_res = await ac.get(f"/api/v1/sessions/inspect/{session_id}")
        assert inspect_res.status_code == 200
        assert inspect_res.json()["data"]["session_id"] == session_id
        assert inspect_res.json()["data"]["is_archived"] is False

        # Test Archive session
        archive_res = await ac.post(f"/api/v1/sessions/archive/{session_id}")
        assert archive_res.status_code == 200
        assert archive_res.json()["data"]["id"] == session_id
        
        # Verify archived status in inspect
        inspect_res2 = await ac.get(f"/api/v1/sessions/inspect/{session_id}")
        assert inspect_res2.json()["data"]["is_archived"] is True

        # Traversal on archived session fails
        dispatch_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "/start"
        })
        assert dispatch_res.status_code == 400
        assert dispatch_res.json()["error"]["error_code"] == "SESSION_ARCHIVED"

        # Recover session
        recover_res = await ac.post(f"/api/v1/sessions/recover/{session_id}")
        assert recover_res.status_code == 200
        
        inspect_res3 = await ac.get(f"/api/v1/sessions/inspect/{session_id}")
        assert inspect_res3.json()["data"]["is_archived"] is False

        # Timeout Check
        # Set session last_active_at to 40 minutes ago
        async with TestSessionLocal() as db:
            query = select(SessionModel).where(SessionModel.id == session_id)
            res = await db.execute(query)
            session_record = res.scalar_one()
            session_record.last_active_at = datetime.utcnow() - timedelta(minutes=40)
            await db.commit()

        # Run timeout checker route
        timeout_res = await ac.post("/api/v1/sessions/timeout?timeout_minutes=30")
        assert timeout_res.status_code == 200
        assert session_id in timeout_res.json()["data"]

        # Verify session is now archived and CANCELLED
        inspect_res4 = await ac.get(f"/api/v1/sessions/inspect/{session_id}")
        assert inspect_res4.json()["data"]["is_archived"] is True
        assert inspect_res4.json()["data"]["fsm_state"] == "CANCELLED"

@pytest.mark.asyncio
async def test_workflow_certification():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Certification Biz",
            "whatsapp_number": "+19991117777"
        })
        business_id = biz_res.json()["data"]["id"]

        # Register workflow
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]

        # Call certification endpoint
        cert_res = await ac.post(f"/api/v1/workflows/certify/{version_id}")
        assert cert_res.status_code == 200
        cert_data = cert_res.json()["data"]
        
        assert cert_data["workflow_version_id"] == version_id
        assert cert_data["static_validation"]["is_valid"] is True
        assert cert_data["replay_determinism_certified"] is True
        assert cert_data["idempotency_certified"] is True
        assert cert_data["terminal_state_lock_certified"] is True
