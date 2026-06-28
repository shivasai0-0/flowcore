import json
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models import Business as BusinessModel
from src.config import settings

class WhatsAppConfigService:
    @staticmethod
    async def get_whatsapp_config(db: AsyncSession, business_id: str) -> Dict[str, Any]:
        """
        Retrieves the WhatsApp configuration for the given business.
        Checks:
        1. settings_json["whatsapp"] keys ("phone_number_id", "access_token")
        2. Direct Business columns (meta_phone_number_id) as fallback
        3. Environment variables (settings.META_PHONE_NUMBER_ID / settings.META_ACCESS_TOKEN) as fallback (for e216b183-8c91-4a56-b819-50ebfb3f8a45)
        """
        # 1. Verify business exists
        query = select(BusinessModel).where(BusinessModel.id == business_id)
        res = await db.execute(query)
        business = res.scalar_one_or_none()
        if not business:
            return {"success": False, "error_code": "BUSINESS_NOT_FOUND"}

        # 2. Extract settings from settings_json
        whatsapp_settings = {}
        if business.settings_json:
            try:
                settings_dict = json.loads(business.settings_json)
                whatsapp_settings = settings_dict.get("whatsapp", {})
            except Exception:
                whatsapp_settings = {}

        phone_number_id = whatsapp_settings.get("phone_number_id") or whatsapp_settings.get("whatsapp_phone_number_id")
        access_token = whatsapp_settings.get("access_token") or whatsapp_settings.get("whatsapp_access_token")

        # 3. Direct column fallback
        if not phone_number_id:
            phone_number_id = business.meta_phone_number_id

        # 4. Env file / Settings fallback (specifically for the MVP business e216b183-8c91-4a56-b819-50ebfb3f8a45)
        # Note: Do not hardcode actual credential values.
        if business_id == "e216b183-8c91-4a56-b819-50ebfb3f8a45":
            if not phone_number_id:
                phone_number_id = settings.META_PHONE_NUMBER_ID
            if not access_token:
                access_token = settings.META_ACCESS_TOKEN

        # 5. Validation
        if not phone_number_id or not access_token:
            return {"success": False, "error_code": "WHATSAPP_CONFIG_MISSING"}

        return {
            "success": True,
            "phone_number_id": phone_number_id,
            "access_token": access_token
        }
