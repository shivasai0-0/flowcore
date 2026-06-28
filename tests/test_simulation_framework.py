import pytest
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.main import app
from src.database import Base, get_db

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
async def test_simulation_strict_mode_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Simulation Biz", "whatsapp_number": "+18888888888"
        })
        business_id = biz_res.json()["data"]["id"]

        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        # Post simulation payload (format: <item_index> x <quantity>)
        sim_payload = {
            "workflow_graph": graph,
            "inputs": ["/start", "1 x 2", "Checkout", "123 Main Street", "CONFIRM_PAYMENT"],
            "simulation_mode": "strict"
        }
        res = await ac.post("/api/v1/workflows/simulate", json=sim_payload)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["success"] is True
        assert len(data["executed_steps"]) == 5
        assert data["executed_steps"][0]["fsm_state_after"] == "MENU"
        assert data["executed_steps"][1]["fsm_state_after"] == "CART"
        assert data["executed_steps"][2]["fsm_state_after"] == "CHECKOUT"
        assert data["executed_steps"][3]["fsm_state_after"] == "PAYMENT"
        assert data["executed_steps"][4]["fsm_state_after"] == "CONFIRMED"
        
        # Verify carry unit snapshot has Margherita Pizza (id '1', qty 2)
        items = data["executed_steps"][1]["carry_unit_snapshot"]["order"]["items"]
        assert len(items) == 1
        assert items[0]["item_id"] == "1"
        assert items[0]["quantity"] == 2

@pytest.mark.asyncio
async def test_simulation_strict_mode_failure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Simulation Biz 2", "whatsapp_number": "+18888888889"
        })
        business_id = biz_res.json()["data"]["id"]

        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        # Post simulation payload with invalid step 4 input ("INVALID" instead of "CONFIRM_PAYMENT")
        sim_payload = {
            "workflow_graph": graph,
            "inputs": ["/start", "1 x 2", "Checkout", "123 Main Street", "INVALID"],
            "simulation_mode": "strict"
        }
        res = await ac.post("/api/v1/workflows/simulate", json=sim_payload)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["success"] is False
        assert len(data["executed_steps"]) == 5
        assert data["executed_steps"][4]["error"] is not None
        assert len(data["runtime_errors"]) == 1

@pytest.mark.asyncio
async def test_simulation_tolerant_mode_recovery():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Simulation Biz 3", "whatsapp_number": "+18888888890"
        })
        business_id = biz_res.json()["data"]["id"]

        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        # Post simulation payload with tolerant mode.
        sim_payload = {
            "workflow_graph": graph,
            "inputs": ["/start", "1 x 2", "Checkout", "123 Main Street", "INVALID", "CONFIRM_PAYMENT"],
            "simulation_mode": "tolerant"
        }
        res = await ac.post("/api/v1/workflows/simulate", json=sim_payload)
        assert res.status_code == 200
        data = res.json()["data"]
        
        # In tolerant mode, success is False because there is a runtime error
        assert data["success"] is False
        assert len(data["executed_steps"]) == 6
        
        # Step 5 failed (index 4)
        assert data["executed_steps"][4]["error"] is not None
        
        # Step 6 succeeded and recovered to CONFIRMED (index 5)
        assert data["executed_steps"][5]["error"] is None
        assert data["executed_steps"][5]["fsm_state_after"] == "CONFIRMED"
        assert len(data["runtime_errors"]) == 1

@pytest.mark.asyncio
async def test_simulation_replay_mode():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Simulation Biz 4", "whatsapp_number": "+18888888891"
        })
        business_id = biz_res.json()["data"]["id"]

        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)
        graph["business_id"] = business_id

        # Run replay simulation mode
        sim_payload = {
            "workflow_graph": graph,
            "inputs": ["/start", "1 x 2", "Checkout", "123 Main Street", "CONFIRM_PAYMENT"],
            "simulation_mode": "replay",
            "replay_validation": True
        }
        res = await ac.post("/api/v1/workflows/simulate", json=sim_payload)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["success"] is True
        assert data["replay_results"] is not None
        assert data["replay_results"]["replay_match"] is True
        assert data["replay_results"]["divergence_step"] is None
        assert data["replay_results"]["mismatch_reason"] is None

@pytest.mark.asyncio
async def test_dynamic_diagnostic_test_routes():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Load sample workflow graph to post
        with open("examples/restaurant_workflow.json", "r") as f:
            graph = json.load(f)

        # 1. Test /api/v1/tests/businesses dynamically
        biz_payload = {
            "name": "Dynamic Diagnostic Biz",
            "whatsapp_number": "+19999999999"
        }
        biz_test_res = await ac.post("/api/v1/tests/businesses", json=biz_payload)
        assert biz_test_res.status_code == 200
        biz_test_data = biz_test_res.json()["data"]
        assert biz_test_data["success"] is True
        assert any(r["response"].get("data", {}).get("name") == "Dynamic Diagnostic Biz" for r in biz_test_data["results"] if isinstance(r.get("response"), dict))

        # 2. Test /api/v1/tests/workflows dynamically (format: item_index x quantity)
        wf_payload = {
            "workflow_graph": graph,
            "inputs": ["/start", "1 x 1", "Checkout", "888 Broadway", "CONFIRM_PAYMENT"]
        }
        wf_test_res = await ac.post("/api/v1/tests/workflows", json=wf_payload)
        assert wf_test_res.status_code == 200
        wf_test_data = wf_test_res.json()["data"]
        assert wf_test_data["success"] is True

        # 3. Test /api/v1/tests/sessions dynamically (with customer turn simulation)
        sess_payload = {
            "workflow_graph": graph,
            "inputs": ["/start", "3 x 1", "Checkout", "888 Broadway", "CONFIRM_PAYMENT"]
        }
        sess_test_res = await ac.post("/api/v1/tests/sessions", json=sess_payload)
        assert sess_test_res.status_code == 200
        sess_test_data = sess_test_res.json()["data"]
        assert sess_test_data["success"] is True
        # Verify French Fries was ordered in the dynamically simulated session
        replay_step = next(r for r in sess_test_data["results"] if r.get("step") == "Verify Session Replay Trace")
        final_carry = replay_step["response"]["data"]["final_carry_unit"]
        assert len(final_carry["order"]["items"]) == 1
        assert final_carry["order"]["items"][0]["item_id"] == "3" # Fries ID is '3'

