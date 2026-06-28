import logging
import json
import httpx
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config import settings
from src.database import get_db
from src.models import Business as BusinessModel

logger = logging.getLogger("flowcore.system_route")

router = APIRouter(prefix="/api/v1/system", tags=["System Info & Health"])

@router.get("/llm-info", status_code=status.HTTP_200_OK)
async def get_llm_info(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """
    GET /api/v1/system/llm-info
    Exposes configured LLM model, its endpoint, availability, and installed models.
    Supports dynamic provider resolving if business_id is specified.
    """
    llm_provider = "ollama"
    configured_model = settings.OLLAMA_MODEL
    endpoint = settings.OLLAMA_ENDPOINT.rstrip("/")
    available = False
    installed_models = []
    
    # Resolve per-business configuration
    if business_id:
        query = select(BusinessModel).where(BusinessModel.id == business_id)
        res = await db.execute(query)
        business = res.scalar_one_or_none()
        if business:
            try:
                biz_settings = json.loads(business.settings_json or "{}")
                llm_config = biz_settings.get("llm_config", {})
                llm_provider = llm_config.get("llm_provider", "ollama")
                if llm_provider == "gemini":
                    configured_model = llm_config.get("gemini_model") or "gemini-1.5-flash"
                    endpoint = "https://generativelanguage.googleapis.com"
                elif llm_provider == "openai":
                    configured_model = llm_config.get("openai_model") or "gpt-4o-mini"
                    endpoint = "https://api.openai.com"
                else:
                    configured_model = llm_config.get("ollama_model") or settings.OLLAMA_MODEL
                    endpoint = (llm_config.get("ollama_endpoint") or settings.OLLAMA_ENDPOINT).rstrip("/")
            except Exception:
                pass

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if llm_provider == "openai":
                api_key = settings.OPENAI_API_KEY
                if business_id and 'llm_config' in locals():
                    api_key = llm_config.get("openai_api_key") or api_key
                if api_key:
                    resp = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"}
                    )
                    if resp.status_code == 200:
                        available = True
                        data = resp.json()
                        installed_models = [m["id"] for m in data.get("data", []) if "gpt" in m["id"].lower()]
            elif llm_provider == "gemini":
                api_key = settings.GEMINI_API_KEY
                if business_id and 'llm_config' in locals():
                    api_key = llm_config.get("gemini_api_key") or api_key
                if api_key:
                    resp = await client.get(
                        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
                    )
                    if resp.status_code == 200:
                        available = True
                        data = resp.json()
                        installed_models = [m["name"].split("/")[-1] for m in data.get("models", []) if "gemini" in m["name"].lower()]
            else: # ollama
                resp = await client.get(f"{endpoint}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    installed_models = [m["name"] for m in data.get("models", [])]
                    available = any(
                        m == configured_model or (":" not in configured_model and m.split(":")[0] == configured_model)
                        for m in installed_models
                    )
    except Exception as e:
        logger.warning(f"Failed to query LLM endpoint ({llm_provider}) at {endpoint}: {str(e)}")

    return {
        "provider": llm_provider,
        "endpoint": endpoint,
        "configured_model": configured_model,
        "available": available,
        "installed_models": installed_models
    }
