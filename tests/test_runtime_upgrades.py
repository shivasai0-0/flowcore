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
    ExecutionSnapshot, ExecutionJournal, ExternalOperation, 
    ExecutionMetric, EventStoreRecord
)
from src.engine.compiler.static_validator import StaticValidator
from src.engine.compiler.graph_optimizer import GraphOptimizer
from src.engine.side_effects import ExternalOperationRegistry, ConcurrentOperationError

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

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Initializes schema on in-memory db and registers dependency override before each test."""
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)

@pytest.mark.asyncio
async def test_compiler_optimizer():
    # Verify optimizer prunes unreachable nodes
    compiled_data = {
        "entry_node_id": "node_1",
        "nodes": {
            "node_1": {"id": "node_1"},
            "node_2": {"id": "node_2"},
            "node_dead": {"id": "node_dead"}
        },
        "edges": [
            {"from_node": "node_1", "to_node": "node_2"}
        ],
        "topological_order": ["node_1", "node_dead", "node_2"]
    }
    optimized = GraphOptimizer.optimize(compiled_data)
    assert "node_dead" not in optimized["nodes"]
    assert "node_1" in optimized["nodes"]
    assert "node_2" in optimized["nodes"]
    assert optimized["topological_order"] == ["node_1", "node_2"]

@pytest.mark.asyncio
async def test_exactly_once_side_effects():
    async with TestSessionLocal() as session:
        session_id = "test_sess_exactly_once"
        op_key = "test_op_123"

        # 1. Register intent
        status, cached = await ExternalOperationRegistry.check_or_register(session, session_id, op_key)
        assert status == "REGISTERED"
        assert cached is None

        # 2. Concurrent registry should raise error
        with pytest.raises(ConcurrentOperationError):
            await ExternalOperationRegistry.check_or_register(session, session_id, op_key)

        # 3. Commit success
        await ExternalOperationRegistry.commit_success(session, op_key, {"success": True, "tx": "abc"})

        # 4. Subsequent check returns cached response
        status, cached = await ExternalOperationRegistry.check_or_register(session, session_id, op_key)
        assert status == "COMPLETED"
        assert cached == {"success": True, "tx": "abc"}

@pytest.mark.asyncio
async def test_full_runtime_journaling_and_snapshots():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Upgrade Pizza",
            "whatsapp_number": "+17770000000"
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

        # Activate
        await ac.post(f"/api/v1/workflows/activate/{version_id}")

        # Start Session
        sess_res = await ac.post("/api/v1/sessions", json={
            "business_id": biz_id,
            "customer_phone": "+17770000000"
        })
        session_id = sess_res.json()["data"]["id"]

        # Run traversal dispatch step
        dispatch = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "/start"
        })
        assert dispatch.status_code == 200

        # Query Database manually for Snapshots and Journals
        async with TestSessionLocal() as db:
            # Check execution snapshots exist
            snaps_query = select(ExecutionSnapshot).where(ExecutionSnapshot.session_id == session_id)
            snaps_res = await db.execute(snaps_query)
            snapshots = snaps_res.scalars().all()
            assert len(snapshots) > 0
            
            # Check execution journals exist with correct order
            journals_query = select(ExecutionJournal).where(ExecutionJournal.session_id == session_id).order_by(ExecutionJournal.timestamp.asc())
            journals_res = await db.execute(journals_query)
            journals = journals_res.scalars().all()
            assert len(journals) > 0
            
            event_types = [j.event_type for j in journals]
            assert "BEGIN_NODE" in event_types
            assert "SNAPSHOT_WRITTEN" in event_types
            assert "NODE_COMMITTED" in event_types

            # Verify metrics were stored
            metrics_query = select(ExecutionMetric).where(ExecutionMetric.session_id == session_id)
            metrics_res = await db.execute(metrics_query)
            metrics = metrics_res.scalars().all()
            assert len(metrics) > 0
            assert metrics[0].latency_ms >= 0

        # Test Rollback Time Travel endpoint
        snapshots_res = await ac.get(f"/api/v1/sessions/{session_id}/snapshots")
        assert snapshots_res.status_code == 200
        snap_list = snapshots_res.json()["data"]
        assert len(snap_list) > 0
        first_snap_id = snap_list[0]["id"]

        # Dispatch Turn 2: Select item to transition to CART
        dispatch_cart = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "1 x 1"
        })
        assert dispatch_cart.status_code == 200

        # Dispatch Turn 2b: Checkout
        dispatch_checkout = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "Checkout"
        })
        assert dispatch_checkout.status_code == 200

        # Send another input to move state forward
        dispatch2 = await ac.post(f"/api/v1/sessions/dispatch/{session_id}", json={
            "user_input": "123 Cherry Lane"
        })
        assert dispatch2.status_code == 200
        assert dispatch2.json()["data"]["fsm_state_after"] == "PAYMENT"

        # Rollback session to the first snapshot point (which was in MENU state)
        rollback_res = await ac.post(f"/api/v1/sessions/{session_id}/rollback/{first_snap_id}")
        assert rollback_res.status_code == 200
        assert rollback_res.json()["data"]["fsm_state"] == "MENU"

        # Verify that downstream journals and snapshots were truncated after rollback
        async with TestSessionLocal() as db:
            snaps_after = await db.execute(select(ExecutionSnapshot).where(ExecutionSnapshot.session_id == session_id))
            assert len(snaps_after.scalars().all()) == 1

        # Check API Metrics endpoint
        metrics_api = await ac.get(f"/api/v1/metrics/{session_id}")
        assert metrics_api.status_code == 200
        metrics_data = metrics_api.json()["data"]
        assert metrics_data["total_execution_steps"] > 0
        assert "average_latency_ms" in metrics_data

@pytest.mark.asyncio
async def test_condition_operators():
    from src.engine.conditions import evaluate_condition, EdgeCondition
    from src.schemas.carry_unit import CarryUnit

    carry = CarryUnit(
        session={
            "session_id": "sess_cond",
            "customer_phone": "+19998887777",
            "business_id": "biz_123",
            "workflow_version_id": "wf_123",
            "session_started_at": "2026-05-24T18:00:00Z"
        },
        order={"total": 25.00}
    )

    # Test always
    assert evaluate_condition(EdgeCondition(type="always"), "hello", carry) is True

    # Test any_input
    assert evaluate_condition(EdgeCondition(type="any_input"), "hello", carry) is True
    assert evaluate_condition(EdgeCondition(type="any_input"), " ", carry) is False

    # Test input_equals
    assert evaluate_condition(EdgeCondition(type="input_equals", value="yes"), "YES", carry) is True
    assert evaluate_condition(EdgeCondition(type="input_equals", value="yes"), "no", carry) is False

    # Test input_in
    assert evaluate_condition(EdgeCondition(type="input_in", value=["a", "b"]), "B", carry) is True
    assert evaluate_condition(EdgeCondition(type="input_in", value=["a", "b"]), "c", carry) is False

    # Test carry_equals
    assert evaluate_condition(EdgeCondition(type="carry_equals", key="order.total", value="25.0"), "", carry) is True
    assert evaluate_condition(EdgeCondition(type="carry_equals", key="order.total", value="10.0"), "", carry) is False

    # Test carry_greater_than
    assert evaluate_condition(EdgeCondition(type="carry_greater_than", key="order.total", value="20"), "", carry) is True
    assert evaluate_condition(EdgeCondition(type="carry_greater_than", key="order.total", value="30"), "", carry) is False

