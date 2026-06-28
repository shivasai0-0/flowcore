import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.database import Base, get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture
def anyio_backend():
    return "asyncio"

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@pytest.fixture(autouse=True)
async def setup_test_db():
    app.dependency_overrides[get_db] = override_get_db
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    app.dependency_overrides.pop(get_db, None)

@pytest.mark.anyio
async def test_run_benchmarks_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Run benchmarks in Fast Mode
        res = await ac.post("/api/v1/workflows/benchmarks/run?use_mock_ai=true")
        assert res.status_code == 200
        res_json = res.json()
        assert res_json["success"] is True
        
        runs = res_json["data"]
        assert len(runs) == 10
        
        # Verify all 10 benchmarks generated and passed validation
        for run in runs:
            assert run["is_valid"] is True, f"Benchmark {run['business_type']} validation failed with errors: {run['validation_errors']}"
            assert len(run["validation_errors"]) == 0
            assert run["raw_output"] != ""

@pytest.mark.anyio
async def test_get_benchmarks_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First check that benchmarks list is empty
        res = await ac.get("/api/v1/workflows/benchmarks")
        assert res.status_code == 200
        assert len(res.json()["data"]) == 0
        
        # Run benchmarks
        run_res = await ac.post("/api/v1/workflows/benchmarks/run?use_mock_ai=true")
        assert run_res.status_code == 200
        
        # Check benchmarks list contains 10 records
        list_res = await ac.get("/api/v1/workflows/benchmarks")
        assert list_res.status_code == 200
        assert len(list_res.json()["data"]) == 10
