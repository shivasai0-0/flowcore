import pytest
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from src.main import app
from src.database import Base, get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.models import Business, WorkflowVersion, Session as SessionModel, CompiledGraph
from src.engine.compiler.static_validator import StaticValidator
from src.schemas.graph import WorkflowGraph
from src.schemas.simulation import SimulationInputPayload

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
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)

@pytest.mark.asyncio
async def test_dead_end_node_static_validation():
    """
    Verifies that the static validator detects a leaf node that doesn't transition to a terminal
    state and doesn't expect user input as a static dead-end.
    """
    graph_data = {
        "business_id": "biz_dead_end_123",
        "version_number": 1,
        "entry_node_id": "node_menu",
        "nodes": {
            "node_menu": {
                "id": "node_menu",
                "module_name": "show_menu",
                "fsm_transition_to": "MENU"
            },
            "node_dead": {
                "id": "node_dead",
                "module_name": "calculate_total", # Doesn't expect user input, FSM CHECKOUT, no outgoing edges!
                "fsm_transition_to": "CHECKOUT"
            }
        },
        "edges": [
            {"from_node": "node_menu", "to_node": "node_dead"}
        ],
        "fsm_transition_table": {
            "START": {"MENU": "show_menu"},
            "MENU": {"CHECKOUT": "calculate_total"}
        }
    }
    
    graph = WorkflowGraph.model_validate(graph_data)
    is_valid, errors, _, _, _, _, _ = StaticValidator.validate(graph)
    assert is_valid is False
    assert any("Dead-end node detected" in err for err in errors)

@pytest.mark.asyncio
async def test_dynamic_workflow_activation_certification():
    """
    Verifies that registering a dynamic workflow and trying to activate it runs the synchronous
    certification check and rejects if it fails validation/simulation.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Dynamic Cert Biz", "whatsapp_number": "+12223334444"
        })
        business_id = biz_res.json()["data"]["id"]

        # 1. Register a valid workflow as dynamic
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "workflow_type": "dynamic",
            "graph": graph
        })
        assert reg_res.status_code == 201
        version_id = reg_res.json()["data"]["workflow_version_id"]

        # 2. Try to activate without compilation (should reject due to not APPROVED)
        async with TestSessionLocal() as db:
            wv = await db.get(WorkflowVersion, version_id)
            wv.status = "DRAFT"
            await db.commit()

        act_res = await ac.post(f"/api/v1/workflows/activate/{version_id}")
        assert act_res.status_code == 400

        # Compile first
        comp_res = await ac.post(f"/api/v1/workflows/compile/{version_id}")
        assert comp_res.status_code == 200

        # Now activate - since it's valid and passes all certification checks, it should succeed
        act_res2 = await ac.post(f"/api/v1/workflows/activate/{version_id}")
        assert act_res2.status_code == 200
        assert act_res2.json()["data"]["status"] == "ACTIVE"

@pytest.mark.asyncio
async def test_business_settings_branding_delivery_payment():
    """
    Verifies that the business settings, branding, delivery settings, and payment config
    endpoints correctly update the Business settings_json.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "MultiTenant Biz", "whatsapp_number": "+15555555555"
        })
        business_id = biz_res.json()["data"]["id"]

        # Update Branding
        branding_payload = {"branding": {"logo_url": "http://logo.com", "primary_color": "#ff0000"}}
        brand_res = await ac.put(f"/api/v1/businesses/{business_id}/branding", json=branding_payload)
        assert brand_res.status_code == 200
        settings = json.loads(brand_res.json()["data"]["settings_json"])
        assert settings["branding"]["primary_color"] == "#ff0000"

        # Update Delivery Settings
        delivery_payload = {"delivery_settings": {"base_fare": 5.0, "provider": "courier_express"}}
        deliv_res = await ac.put(f"/api/v1/businesses/{business_id}/delivery", json=delivery_payload)
        assert deliv_res.status_code == 200
        settings = json.loads(deliv_res.json()["data"]["settings_json"])
        assert settings["delivery"]["base_fare"] == 5.0

        # Update Payment Config
        payment_payload = {"payment_config": {"gateway": "stripe", "currency": "USD"}}
        pay_res = await ac.put(f"/api/v1/businesses/{business_id}/payment", json=payment_payload)
        assert pay_res.status_code == 200
        settings = json.loads(pay_res.json()["data"]["settings_json"])
        assert settings["payment"]["gateway"] == "stripe"
        assert settings["branding"]["primary_color"] == "#ff0000"  # Previous settings preserved!

@pytest.mark.asyncio
async def test_session_unlock_endpoint():
    """
    Verifies that the PUT /unlock/{session_id} route resets the session lock.
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business and active workflow
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Unlock Biz", "whatsapp_number": "+16666666667"
        })
        business_id = biz_res.json()["data"]["id"]

        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        reg_res = await ac.post("/api/v1/workflows/register", json={
            "business_id": business_id,
            "graph": graph
        })
        version_id = reg_res.json()["data"]["workflow_version_id"]
        await ac.post(f"/api/v1/workflows/compile/{version_id}")
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": business_id, "customer_phone": "+19998881234"
        })
        session_id = sess_res.json()["data"]["id"]

        # Manually lock the session via DB
        async with TestSessionLocal() as session:
            from datetime import datetime, timedelta
            sess_record = await session.get(SessionModel, session_id)
            sess_record.locked_until = datetime.utcnow() + timedelta(seconds=10)
            await session.commit()

        # Try dispatching input, it should fail since locked
        disp_res = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})
        assert disp_res.status_code == 400
        assert "locked" in disp_res.json()["error"]["message"].lower()

        # Unlock the session
        unlock_res = await ac.put(f"/api/v1/sessions/unlock/{session_id}")
        assert unlock_res.status_code == 200

        # Dispatch should succeed now
        disp_res2 = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={"user_input": "/start"})
        assert disp_res2.status_code == 200
        assert disp_res2.json()["data"]["fsm_state_after"] == "MENU"
