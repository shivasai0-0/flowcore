import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models import Business
from src.engine.registries.provider_registry import ProviderRegistry, PROVIDER_METADATA
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/providers", tags=["Providers"])

class ProvidersUpdateRequest(BaseModel):
    business_id: Optional[str] = None
    providers: Dict[str, str]  # e.g., {"payment_provider": "Stripe", "delivery_provider": "Shadowfax", "notification_provider": "SMS"}
    config: Optional[Dict[str, Dict[str, Any]]] = None  # e.g., {"Stripe": {"api_key": "..."}}

@router.get("", response_model=ApiResponse)
async def get_providers(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    # 1. Resolve business
    if business_id:
        biz_query = select(Business).where(Business.id == business_id)
    else:
        biz_query = select(Business).limit(1)
        
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

    try:
        current_providers = json.loads(business.providers_json or "{}")
    except Exception:
        current_providers = {}

    try:
        current_settings = json.loads(business.settings_json or "{}")
    except Exception:
        current_settings = {}

    return ApiResponse(
        success=True,
        data={
            "business_id": business.id,
            "current_providers": current_providers,
            "current_settings": current_settings,
            "available_providers": PROVIDER_METADATA
        }
    )

@router.put("", response_model=ApiResponse)
async def update_providers(payload: ProvidersUpdateRequest, db: AsyncSession = Depends(get_db)):
    # 1. Resolve business
    business_id = payload.business_id
    if business_id:
        biz_query = select(Business).where(Business.id == business_id)
    else:
        biz_query = select(Business).limit(1)
        
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

    # 2. Update providers_json
    business.providers_json = json.dumps(payload.providers)

    # 3. If credentials config is provided, store in settings_json under payments/delivery/notification credentials keys
    if payload.config:
        try:
            settings = json.loads(business.settings_json or "{}")
        except Exception:
            settings = {}
            
        for prov_name, prov_config in payload.config.items():
            # Validate configs against registry
            # Detect category
            category = None
            for cat, meta in PROVIDER_METADATA.items():
                if prov_name in meta["providers"]:
                    category = cat
                    break
            
            if category:
                try:
                    ProviderRegistry.validate_provider_config(category, prov_name, prov_config)
                except ValueError as val_err:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Validation error for provider '{prov_name}': {str(val_err)}"
                    )
                
                if "credentials" not in settings:
                    settings["credentials"] = {}
                settings["credentials"][prov_name] = prov_config
        
        business.settings_json = json.dumps(settings)

    await db.commit()
    await db.refresh(business)

    try:
        updated_providers = json.loads(business.providers_json)
    except Exception:
        updated_providers = {}
        
    try:
        updated_settings = json.loads(business.settings_json)
    except Exception:
        updated_settings = {}

    return ApiResponse(
        success=True,
        data={
            "business_id": business.id,
            "current_providers": updated_providers,
            "current_settings": updated_settings
        }
    )
