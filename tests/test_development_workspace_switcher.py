import pytest
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from src.main import app
from src.database import Base, get_db
from src.models import Business as BusinessModel
from src.config import settings
from src.services.dev_workspace import apply_dev_workspace_branding

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

@pytest_asyncio.fixture(autouse=True)
async def restore_dev_workspace_settings():
    # Save original settings
    orig_mode = settings.DEVELOPMENT_WORKSPACE_MODE
    orig_active = settings.ACTIVE_DEV_WORKSPACE
    yield
    # Restore original settings after test
    settings.DEVELOPMENT_WORKSPACE_MODE = orig_mode
    settings.ACTIVE_DEV_WORKSPACE = orig_active

@pytest.mark.asyncio
async def test_list_businesses():
    settings.DEVELOPMENT_WORKSPACE_MODE = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create test businesses
        await ac.post("/api/v1/businesses", json={
            "name": "Pizza Planet",
            "whatsapp_number": "+111"
        })
        await ac.post("/api/v1/businesses", json={
            "name": "City Hospital",
            "whatsapp_number": "+222"
        })

        res = await ac.get("/api/v1/businesses")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert len(data["data"]) == 2
        names = [b["name"] for b in data["data"]]
        assert "Pizza Planet" in names
        assert "City Hospital" in names
        for item in data["data"]:
            assert "id" in item
            assert "name" in item
            assert "business_type" in item

@pytest.mark.asyncio
async def test_set_active_dev_workspace():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_res = await ac.post("/api/v1/businesses", json={
            "name": "Pizza Planet",
            "whatsapp_number": "+111"
        })
        biz_id = create_res.json()["data"]["id"]

        # Call active dev workspace endpoint
        res = await ac.post(f"/api/v1/businesses/active-dev-workspace/{biz_id}")
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert settings.ACTIVE_DEV_WORKSPACE == biz_id

        # Non-existent business should return 404
        bad_res = await ac.post("/api/v1/businesses/active-dev-workspace/does-not-exist")
        assert bad_res.status_code == 404

@pytest.mark.asyncio
async def test_meta_phone_id_routing_dev_mode():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create test business 1
        create_res_1 = await ac.post("/api/v1/businesses", json={
            "name": "Pizza Planet",
            "whatsapp_number": "+111"
        })
        biz_1 = create_res_1.json()["data"]

        # Create test business 2
        create_res_2 = await ac.post("/api/v1/businesses", json={
            "name": "City Hospital",
            "whatsapp_number": "+222"
        })
        biz_2 = create_res_2.json()["data"]

        # Set up Meta Phone Number ID manually for business 1
        async with TestSessionLocal() as session:
            db_biz = await session.get(BusinessModel, biz_1["id"])
            db_biz.meta_phone_number_id = "phone-id-1"
            await session.commit()

        # In dev workspace mode, set business 2 active
        settings.DEVELOPMENT_WORKSPACE_MODE = True
        settings.ACTIVE_DEV_WORKSPACE = biz_2["id"]

        # Query by-phone-id/phone-id-1
        # It should return business 2 (City Hospital) instead of business 1 (Pizza Planet)
        res = await ac.get("/api/v1/businesses/by-phone-id/phone-id-1")
        assert res.status_code == 200
        assert res.json()["data"]["id"] == biz_2["id"]
        assert res.json()["data"]["name"] == "City Hospital"

        # Disable dev mode: should query correctly
        settings.DEVELOPMENT_WORKSPACE_MODE = False
        res = await ac.get("/api/v1/businesses/by-phone-id/phone-id-1")
        assert res.status_code == 200
        assert res.json()["data"]["id"] == biz_1["id"]
        assert res.json()["data"]["name"] == "Pizza Planet"

@pytest.mark.asyncio
async def test_dev_workspace_branding_helper():
    async with TestSessionLocal() as session:
        # Create business
        biz = BusinessModel(
            name="Pizza Planet",
            whatsapp_number="+111"
        )
        session.add(biz)
        await session.commit()
        await session.refresh(biz)

        # Mode Disabled
        settings.DEVELOPMENT_WORKSPACE_MODE = False
        res = await apply_dev_workspace_branding(session, biz.id, "Hello Customer")
        assert res == "Hello Customer"

        # Mode Enabled
        settings.DEVELOPMENT_WORKSPACE_MODE = True
        res = await apply_dev_workspace_branding(session, biz.id, "Hello Customer")
        assert res == "[Pizza Planet] Hello Customer"

@pytest.mark.asyncio
async def test_report_branding_in_dev_mode():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business
        create_res = await ac.post("/api/v1/businesses", json={
            "name": "Pizza Planet",
            "whatsapp_number": "+111"
        })
        biz_id = create_res.json()["data"]["id"]

        # Enable Dev Mode
        settings.DEVELOPMENT_WORKSPACE_MODE = True
        settings.ACTIVE_DEV_WORKSPACE = biz_id

        # Send report via endpoint (which calls send_whatsapp_report)
        res = await ac.post("/api/v1/reports/send-whatsapp", json={
            "recipient_phone": "+99999999",
            "report_content": "This is a report"
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

        # Let's verify that the event generated has the branded content
        async with TestSessionLocal() as session:
            from src.models import EventStoreRecord
            # Query REPORT_DELIVERED event
            q = select(EventStoreRecord).where(EventStoreRecord.event_type == "REPORT_DELIVERED")
            db_res = await session.execute(q)
            evt = db_res.scalar_one_or_none()
            assert evt is not None
            payload = json.loads(evt.payload_json)
            assert "[Pizza Planet] This is a report" in payload["content"]

@pytest.mark.asyncio
async def test_dashboard_overview_and_tasks_dev_mode_override():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create business 1
        create_res_1 = await ac.post("/api/v1/businesses", json={
            "name": "Pizza Planet",
            "whatsapp_number": "+111"
        })
        biz_1_id = create_res_1.json()["data"]["id"]

        # Create business 2
        create_res_2 = await ac.post("/api/v1/businesses", json={
            "name": "City Hospital",
            "whatsapp_number": "+222"
        })
        biz_2_id = create_res_2.json()["data"]["id"]

        # Enable Dev Mode and activate business 2
        settings.DEVELOPMENT_WORKSPACE_MODE = True
        settings.ACTIVE_DEV_WORKSPACE = biz_2_id

        # 1. Query dashboard overview for business 1
        # It should override to business 2's ID
        res = await ac.get(f"/api/v1/dashboard/overview?business_id={biz_1_id}")
        assert res.status_code == 200
        assert res.json()["success"] is True
        assert res.json()["data"]["business_id"] == biz_2_id
        assert res.json()["data"]["business_name"] == "City Hospital"

        # 2. Query list tasks for business 1
        # It should override to business 2
        res_tasks = await ac.get(f"/api/v1/tasks?business_id={biz_1_id}")
        assert res_tasks.status_code == 200
        assert res_tasks.json()["success"] is True
        # Since business 2 has no tasks, it should return empty list
        assert len(res_tasks.json()["data"]) == 0

