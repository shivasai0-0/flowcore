import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./flowcore.db"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DEBUG: bool = True

    # Development Workspace Switcher settings
    DEVELOPMENT_WORKSPACE_MODE: bool = False
    ACTIVE_DEV_WORKSPACE: Optional[str] = None

    # Ollama LLM Settings
    OLLAMA_MODEL: str = "qwen3:4b"
    OLLAMA_ENDPOINT: str = "http://localhost:11434"

    # External LLM Keys (fallback system values)
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None

    # Meta WhatsApp Cloud API — optional, only needed when running with real Meta integration
    META_PHONE_NUMBER_ID: Optional[str] = None
    META_WABA_ID: Optional[str] = None
    META_ACCESS_TOKEN: Optional[str] = None
    META_WEBHOOK_VERIFY_TOKEN: str = "flowcore_webhook_verify_2026"

    # n8n Orchestration Layer
    N8N_BASE_URL: str = "http://localhost:5678"

    # FlowCore Platform defaults
    FLOWCORE_BUSINESS_ID: Optional[str] = None

settings = Settings()

def sanitize_endpoint(url: Optional[str]) -> str:
    if not url or not isinstance(url, str) or url.strip() == "" or url.strip().lower() == "string":
        return settings.OLLAMA_ENDPOINT.rstrip("/")
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url

def sanitize_model(model_name: Optional[str]) -> str:
    if not model_name or not isinstance(model_name, str) or model_name.strip() == "" or model_name.strip().lower() == "string":
        return settings.OLLAMA_MODEL
    return model_name.strip()
