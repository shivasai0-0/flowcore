import json
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.main import app
from src.database import Base, get_db
from src.models import Business, WorkflowVersion, CompiledGraph
from src.services.ai_generator import AIGenerator

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
async def test_category_detection():
    # Test keyword matching for business description category detection
    assert AIGenerator.detect_category("we serve yummy pizza and burger", []) == "restaurant"
    assert AIGenerator.detect_category("patient doctor consultation", []) == "clinic"
    assert AIGenerator.detect_category("hair cuts and spa styling", []) == "salon"
    assert AIGenerator.detect_category("grocery hypermarket mart items", []) == "supermarket"
    assert AIGenerator.detect_category("courses enrollment student class", []) == "education"
    assert AIGenerator.detect_category("property view tour apartment", []) == "realestate"

@pytest.mark.asyncio
async def test_fast_mode_generation_all_categories():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Template Tester Shop",
            "whatsapp_number": "+10001112222"
        })
        assert biz_res.status_code in {200, 201}
        biz_data = biz_res.json()["data"]
        biz_id = biz_data["id"]

        # 1. Restaurant template check
        res_restaurant = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "A delicious pizza diner.",
            "capability_packs": ["restaurant"],
            "use_mock_ai": True
        })
        assert res_restaurant.status_code == 200
        data = res_restaurant.json()["data"]
        assert data["success"] is True
        assert data["method"] == "programmatic"
        assert data["category"] == "restaurant"
        assert len(data["workflows"]) == 3
        assert "Ordering Workflow" in data["workflows"]

        # 2. Hospital template check
        res_hospital = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "City health clinic.",
            "capability_packs": ["hospital"],
            "use_mock_ai": True
        })
        assert res_hospital.status_code == 200
        data = res_hospital.json()["data"]
        assert data["category"] == "hospital"
        assert "Appointment Workflow" in data["workflows"]

        # 3. Salon template check
        res_salon = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "Elite styles haircuts.",
            "capability_packs": ["salon"],
            "use_mock_ai": True
        })
        assert res_salon.status_code == 200
        data = res_salon.json()["data"]
        assert data["category"] == "salon"
        assert "Booking Workflow" in data["workflows"]

        # 4. Supermarket template check
        res_supermarket = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "Fresh Mart groceries store.",
            "capability_packs": ["supermarket"],
            "use_mock_ai": True
        })
        assert res_supermarket.status_code == 200
        data = res_supermarket.json()["data"]
        assert data["category"] == "supermarket"
        assert "Ordering Workflow" in data["workflows"]

        # 5. Education template check
        res_education = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "Apex learn Academy courses.",
            "capability_packs": ["education"],
            "use_mock_ai": True
        })
        assert res_education.status_code == 200
        data = res_education.json()["data"]
        assert data["category"] == "education"
        assert "Enrollment Workflow" in data["workflows"]

        # 6. Real Estate template check
        res_real_estate = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "Properties rental real estate.",
            "capability_packs": ["real_estate"],
            "use_mock_ai": True
        })
        assert res_real_estate.status_code == 200
        data = res_real_estate.json()["data"]
        assert data["category"] == "realestate"
        assert "Lead Management Workflow" in data["workflows"]
        assert "Viewing Workflow" in data["workflows"]

@pytest.mark.asyncio
async def test_generate_validation_failure_rejection(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock
    
    # We will mock the post request in httpx.AsyncClient to return an invalid workflow graph
    # e.g., missing entry_node_id or invalid module names or invalid FSM states
    invalid_portfolio = {
        "Invalid Workflow": {
            "entry_node_id": "nonexistent_node",
            "trigger_event": None,
            "nodes": {
                "node_1": {
                    "id": "node_1",
                    "module_name": "unregistered_module_name",
                    "config": {},
                    "fsm_transition_to": "INVALID_STATE"
                }
            },
            "edges": [],
            "fsm_transition_table": {}
        }
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": json.dumps(invalid_portfolio)
        }
    }
    
    import httpx
    original_post = httpx.AsyncClient.post
    
    async def mock_post(self, url, *args, **kwargs):
        if "api/chat" in str(url):
            return mock_response
        return await original_post(self, url, *args, **kwargs)
        
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Validation Failure Tester",
            "whatsapp_number": "+19998887777"
        })
        assert biz_res.status_code in {200, 201}
        biz_id = biz_res.json()["data"]["id"]

        # Call generate in AI Mode (use_mock_ai=False)
        res = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "Mock business for failure test",
            "capability_packs": ["restaurant"],
            "use_mock_ai": False
        })
        
        # Verify it rejected the invalid portfolio and returned HTTP 400
        assert res.status_code == 400
        res_json = res.json()
        assert res_json["success"] is False
        assert "Workflow portfolio failed validation checks" in res_json["error"]["message"]
