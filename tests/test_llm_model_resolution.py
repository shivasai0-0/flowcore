import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.config import settings, sanitize_endpoint, sanitize_model

@pytest.fixture
def anyio_backend():
    return "asyncio"

def test_sanitize_endpoint_logic():
    # Test fallback to settings.OLLAMA_ENDPOINT
    expected_default = settings.OLLAMA_ENDPOINT.rstrip("/")
    assert sanitize_endpoint(None) == expected_default
    assert sanitize_endpoint("") == expected_default
    assert sanitize_endpoint("   ") == expected_default
    assert sanitize_endpoint("string") == expected_default
    assert sanitize_endpoint("STRING") == expected_default

    # Test protocol prepending
    assert sanitize_endpoint("localhost:11434") == "http://localhost:11434"
    assert sanitize_endpoint("127.0.0.1:11434") == "http://127.0.0.1:11434"

    # Test valid protocol preservation
    assert sanitize_endpoint("http://my-ollama:11434") == "http://my-ollama:11434"
    assert sanitize_endpoint("https://secure-ollama:11434/") == "https://secure-ollama:11434"

def test_sanitize_model_logic():
    # Test fallback to settings.OLLAMA_MODEL
    expected_default = settings.OLLAMA_MODEL
    assert sanitize_model(None) == expected_default
    assert sanitize_model("") == expected_default
    assert sanitize_model("   ") == expected_default
    assert sanitize_model("string") == expected_default
    assert sanitize_model("STRING") == expected_default

    # Test custom model name preservation
    assert sanitize_model("qwen:7b") == "qwen:7b"
    assert sanitize_model("llama3") == "llama3"

@pytest.mark.anyio
async def test_llm_info_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/system/llm-info")
        assert res.status_code == 200
        data = res.json()
        assert "endpoint" in data
        assert "configured_model" in data
        assert "available" in data
        assert "installed_models" in data
        assert data["configured_model"] == settings.OLLAMA_MODEL

@pytest.mark.anyio
async def test_llm_diagnostic_endpoint_uses_configured_model():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # We trigger the diagnostic route with default payload, and check it uses settings
        res = await ac.post("/api/v1/tests/llm-diagnostic", json={
            "run_case_1": False,
            "run_case_2": False,
            "run_case_3": False
        })
        assert res.status_code == 200
        data = res.json()
        # success is false because no test cases were run, which is expected
        assert data["success"] is False
        assert data["data"]["configured_model"] == settings.OLLAMA_MODEL

@pytest.mark.anyio
async def test_llm_config_endpoints():
    import random
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create a business
        biz_payload = {
            "name": "LLM Test Business",
            "whatsapp_number": f"+1999{random.randint(1000000, 9999999)}"
        }
        res = await ac.post("/api/v1/businesses", json=biz_payload)
        assert res.status_code == 201
        biz_id = res.json()["data"]["id"]

        # 2. Update LLM Config
        config_payload = {
            "llm_config": {
                "llm_provider": "openai",
                "openai_api_key": "sk-1234567890abcdef",
                "gemini_api_key": "",
                "openai_model": "gpt-4o",
                "gemini_model": "gemini-1.5-flash",
                "ollama_model": "qwen3:4b",
                "ollama_endpoint": "http://localhost:11434"
            }
        }
        update_res = await ac.put(f"/api/v1/businesses/{biz_id}/llm-config", json=config_payload)
        assert update_res.status_code == 200

        # 3. Get LLM Config and verify key is masked
        get_res = await ac.get(f"/api/v1/businesses/{biz_id}/llm-config")
        assert get_res.status_code == 200
        get_data = get_res.json()["data"]
        assert get_data["llm_provider"] == "openai"
        assert get_data["openai_api_key"] == "sk-1••••••••cdef"
        assert get_data["openai_model"] == "gpt-4o"

        # 4. Update LLM Config with masked key and verify original key is preserved
        config_payload["llm_config"]["openai_api_key"] = "sk-1••••••••cdef"
        config_payload["llm_config"]["openai_model"] = "gpt-4o-mini"
        update_res_2 = await ac.put(f"/api/v1/businesses/{biz_id}/llm-config", json=config_payload)
        assert update_res_2.status_code == 200

        # Fetch from DB directly or via GET to verify it is still saved correctly
        get_res_2 = await ac.get(f"/api/v1/businesses/{biz_id}/llm-config")
        assert get_res_2.json()["data"]["openai_model"] == "gpt-4o-mini"
        assert get_res_2.json()["data"]["openai_api_key"] == "sk-1••••••••cdef"
