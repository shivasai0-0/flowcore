import pytest
import pytest_asyncio
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from src.main import app
from src.database import get_db, Base
from src.models import Business, Session as SessionModel, EventStoreRecord, WorkflowVersion
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

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
async def test_dashboard_overview():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Test Dashboard Biz",
            "whatsapp_number": "+19999999999"
        })
        assert biz_res.status_code == 201
        biz_data = biz_res.json()["data"]
        biz_id = biz_data["id"]

        # 2. Query empty dashboard overview
        dash_res = await ac.get(f"/api/v1/dashboard/overview?business_id={biz_id}")
        assert dash_res.status_code == 200
        dash_data = dash_res.json()["data"]
        assert dash_data["business_name"] == "Test Dashboard Biz"
        assert dash_data["kpis"]["orders"] == 0
        assert dash_data["kpis"]["revenue"] == 0.0

@pytest.mark.asyncio
async def test_catalog_crud():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Catalog Biz",
            "whatsapp_number": "+18888888888"
        })
        biz_id = biz_res.json()["data"]["id"]

        # 1. Get empty catalog
        cat_res = await ac.get(f"/api/v1/business/catalog?business_id={biz_id}")
        assert cat_res.status_code == 200
        assert cat_res.json()["data"] == []

        # 2. Add an item
        add_res = await ac.post("/api/v1/business/catalog/item", json={
            "business_id": biz_id,
            "id": "pizza_01",
            "name": "Pepperoni Pizza",
            "price": 14.99,
            "category": "Pizza"
        })
        assert add_res.status_code == 200
        assert add_res.json()["data"]["id"] == "pizza_01"

        # 3. List catalog items
        cat_res2 = await ac.get(f"/api/v1/business/catalog?business_id={biz_id}")
        assert len(cat_res2.json()["data"]) == 1
        assert cat_res2.json()["data"][0]["name"] == "Pepperoni Pizza"

        # 4. Edit item
        edit_res = await ac.put(f"/api/v1/business/catalog/item/pizza_01", json={
            "business_id": biz_id,
            "name": "Pepperoni Pizza Classic",
            "price": 15.99
        })
        assert edit_res.status_code == 200
        assert edit_res.json()["data"]["price"] == 15.99

        # 5. Delete item
        del_res = await ac.delete(f"/api/v1/business/catalog/item/pizza_01?business_id={biz_id}")
        assert del_res.status_code == 200
        assert del_res.json()["data"]["deleted"] is True

        cat_res3 = await ac.get(f"/api/v1/business/catalog?business_id={biz_id}")
        assert len(cat_res3.json()["data"]) == 0

@pytest.mark.asyncio
async def test_providers_config():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "Providers Biz",
            "whatsapp_number": "+17777777777"
        })
        biz_id = biz_res.json()["data"]["id"]

        # 1. Get providers
        prov_res = await ac.get(f"/api/v1/providers?business_id={biz_id}")
        assert prov_res.status_code == 200
        data = prov_res.json()["data"]
        assert "available_providers" in data

        # 2. Update providers
        up_res = await ac.put("/api/v1/providers", json={
            "business_id": biz_id,
            "providers": {
                "payment_provider": "Stripe",
                "delivery_provider": "Shadowfax",
                "notification_provider": "SMS"
            },
            "config": {
                "Stripe": {
                    "secret_key": "sk_test_123",
                    "webhook_secret": "whsec_123"
                }
            }
        })
        assert up_res.status_code == 200
        assert up_res.json()["data"]["current_providers"]["payment_provider"] == "Stripe"

@pytest.mark.asyncio
async def test_ai_generator():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business
        biz_res = await ac.post("/api/v1/businesses", json={
            "name": "AI Gen Biz",
            "whatsapp_number": "+16666666666"
        })
        biz_id = biz_res.json()["data"]["id"]

        # Generate portfolio
        gen_res = await ac.post("/api/v1/workflows/generate", json={
            "business_id": biz_id,
            "business_description": "We are a food shop selling Margherita Pizza for $12",
            "capability_packs": ["Restaurant"],
            "use_mock_ai": True
        })
        assert gen_res.status_code == 200
        data = gen_res.json()["data"]
        assert data["success"] is True
        assert data["category"] == "restaurant"
        assert "Ordering Workflow" in data["workflows"]
