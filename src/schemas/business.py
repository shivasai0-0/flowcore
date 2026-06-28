from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class BusinessCreate(BaseModel):
    name: str
    whatsapp_number: str
    meta_phone_number_id: Optional[str] = None  # Meta Cloud API Phone Number ID

class BusinessResponse(BaseModel):
    id: str
    name: str
    whatsapp_number: str
    meta_phone_number_id: Optional[str] = None
    settings_json: str
    catalog_json: str
    created_at: datetime

    class Config:
        from_attributes = True

class SettingsUpdate(BaseModel):
    settings: dict

class CatalogUpdate(BaseModel):
    catalog: dict

class WhatsappUpdate(BaseModel):
    whatsapp_number: str
    meta_phone_number_id: Optional[str] = None  # Optionally update Meta Phone Number ID at same time

class MetaPhoneNumberIdUpdate(BaseModel):
    meta_phone_number_id: str  # Register or update the Meta-assigned Phone Number ID

class BrandingUpdate(BaseModel):
    branding: dict

class DeliverySettingsUpdate(BaseModel):
    delivery_settings: dict

class PaymentConfigUpdate(BaseModel):
    payment_config: dict

class BusinessListItem(BaseModel):
    id: str
    name: str
    business_type: str

    class Config:
        from_attributes = True

class LLMConfig(BaseModel):
    llm_provider: str = "ollama"  # "ollama" | "gemini" | "openai"
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_model: Optional[str] = "gpt-4o-mini"
    gemini_model: Optional[str] = "gemini-1.5-flash"
    ollama_model: Optional[str] = "qwen3:4b"
    ollama_endpoint: Optional[str] = "http://localhost:11434"

class LLMConfigUpdate(BaseModel):
    llm_config: LLMConfig

