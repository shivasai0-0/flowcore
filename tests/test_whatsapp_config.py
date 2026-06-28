import pytest
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.main import app
from src.database import Base, get_db
from src.models import Business as BusinessModel
from src.config import settings

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
async def test_whatsapp_config_business_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/businesses/non_existent_id/whatsapp-config")
        assert res.status_code == 404
        data = res.json()
        assert data["success"] is False
        assert data["error"]["error_code"] == "BUSINESS_NOT_FOUND"

@pytest.mark.asyncio
async def test_whatsapp_config_missing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business
        create_res = await ac.post("/api/v1/businesses", json={
            "name": "No Config Shop",
            "whatsapp_number": "+12345678"
        })
        business_id = create_res.json()["data"]["id"]

        res = await ac.get(f"/api/v1/businesses/{business_id}/whatsapp-config")
        assert res.status_code == 400
        data = res.json()
        assert data["success"] is False
        assert data["error"]["error_code"] == "WHATSAPP_CONFIG_MISSING"

@pytest.mark.asyncio
async def test_whatsapp_config_success_from_settings():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create a business
        create_res = await ac.post("/api/v1/businesses", json={
            "name": "Config Shop",
            "whatsapp_number": "+123456789"
        })
        business_id = create_res.json()["data"]["id"]

        # Update settings with whatsapp credentials
        update_res = await ac.put(f"/api/v1/businesses/{business_id}/settings", json={
            "settings": {
                "whatsapp": {
                    "phone_number_id": "999888777",
                    "access_token": "EAA_test_token"
                }
            }
        })
        assert update_res.status_code == 200

        # Retrieve config
        res = await ac.get(f"/api/v1/businesses/{business_id}/whatsapp-config")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["phone_number_id"] == "999888777"
        assert data["data"]["access_token"] == "EAA_test_token"

@pytest.mark.asyncio
async def test_whatsapp_config_success_from_env_fallback():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Temporarily mock env config settings
        original_phone = settings.META_PHONE_NUMBER_ID
        original_token = settings.META_ACCESS_TOKEN
        settings.META_PHONE_NUMBER_ID = "1142214872306990"
        settings.META_ACCESS_TOKEN = "EAAecwqLXXng..."

        try:
            # Create a business using the specific MVP ID
            async with TestSessionLocal() as session:
                async with session.begin():
                    biz = BusinessModel(
                        id="e216b183-8c91-4a56-b819-50ebfb3f8a45",
                        name="MVP Restaurant",
                        whatsapp_number="+15555555"
                    )
                    session.add(biz)

            # Retrieve config (should fallback to settings.META_PHONE_NUMBER_ID/META_ACCESS_TOKEN)
            res = await ac.get("/api/v1/businesses/e216b183-8c91-4a56-b819-50ebfb3f8a45/whatsapp-config")
            assert res.status_code == 200
            data = res.json()
            assert data["success"] is True
            assert data["data"]["phone_number_id"] == "1142214872306990"
            assert data["data"]["access_token"] == "EAAecwqLXXng..."

        finally:
            settings.META_PHONE_NUMBER_ID = original_phone
            settings.META_ACCESS_TOKEN = original_token
