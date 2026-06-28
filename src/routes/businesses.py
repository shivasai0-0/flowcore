import json
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models import Business as BusinessModel, WorkflowVersion
from src.schemas.business import (
    BusinessCreate, BusinessResponse, SettingsUpdate, CatalogUpdate, WhatsappUpdate,
    BrandingUpdate, DeliverySettingsUpdate, PaymentConfigUpdate, MetaPhoneNumberIdUpdate,
    BusinessListItem, LLMConfigUpdate
)
from src.schemas.envelope import ApiResponse
from src.schemas.workflow import WorkflowVersionResponse
from src.services.whatsapp_config import WhatsAppConfigService

router = APIRouter(prefix="/api/v1/businesses", tags=["Businesses"])

@router.post("", response_model=ApiResponse[BusinessResponse], status_code=status.HTTP_201_CREATED)
async def create_business(payload: BusinessCreate, db: AsyncSession = Depends(get_db)):
    # Check if number already registered
    query = select(BusinessModel).where(BusinessModel.whatsapp_number == payload.whatsapp_number)
    res = await db.execute(query)
    existing = res.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Business with WhatsApp number '{payload.whatsapp_number}' already registered."
        )

    business = BusinessModel(
        name=payload.name,
        whatsapp_number=payload.whatsapp_number,
        settings_json="{}",
        catalog_json="{}"
    )
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.get("", response_model=ApiResponse[list[BusinessListItem]])
async def list_all_businesses(db: AsyncSession = Depends(get_db)):
    from src.config import settings
    query = select(BusinessModel)
    res = await db.execute(query)
    businesses = res.scalars().all()

    if settings.DEVELOPMENT_WORKSPACE_MODE:
        target_ids = {
            "e216b183-8c91-4a56-b819-50ebfb3f8a45",
            "hospital-business-id",
            "salon-business-id",
            "supermarket-business-id",
            "education-business-id",
            "real-estate-business-id"
        }
        filtered = [b for b in businesses if b.id in target_ids]
        missing_ids = target_ids - {b.id for b in filtered}
        
        if missing_ids:
            default_bizs = [
                BusinessModel(id="e216b183-8c91-4a56-b819-50ebfb3f8a45", name="Pizza Planet", whatsapp_number="+919652778472", business_type="restaurant", meta_phone_number_id="10928374928"),
                BusinessModel(id="hospital-business-id", name="City General Hospital", whatsapp_number="+919652778473", business_type="hospital", meta_phone_number_id="10928374929"),
                BusinessModel(id="salon-business-id", name="Luxe Salon & Spa", whatsapp_number="+919652778474", business_type="salon", meta_phone_number_id="10928374930"),
                BusinessModel(id="supermarket-business-id", name="FreshMart Supermarket", whatsapp_number="+919652778475", business_type="supermarket", meta_phone_number_id="10928374931"),
                BusinessModel(id="education-business-id", name="Apex Academy", whatsapp_number="+919652778476", business_type="education", meta_phone_number_id="10928374932"),
                BusinessModel(id="real-estate-business-id", name="Elite Realty", whatsapp_number="+919652778477", business_type="real_estate", meta_phone_number_id="10928374933")
            ]
            added = False
            for b in default_bizs:
                if b.id in missing_ids:
                    # Double check if any duplicate phone number
                    exist_query = select(BusinessModel).where(BusinessModel.whatsapp_number == b.whatsapp_number)
                    exist_res = await db.execute(exist_query)
                    if not exist_res.scalar_one_or_none():
                        db.add(b)
                        filtered.append(b)
                        added = True
            if added:
                await db.commit()
                res = await db.execute(query)
                businesses = res.scalars().all()
                filtered = [b for b in businesses if b.id in target_ids]
        
        return ApiResponse(success=True, data=filtered)

    return ApiResponse(success=True, data=businesses)

@router.post("/active-dev-workspace/{business_id}", response_model=ApiResponse)
async def set_active_dev_workspace(business_id: str, db: AsyncSession = Depends(get_db)):
    from src.config import settings
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business with ID '{business_id}' not found."
        )
    settings.ACTIVE_DEV_WORKSPACE = business_id
    return ApiResponse(success=True, data={"active_dev_workspace": business_id})

@router.get("/by-phone-id/{meta_phone_number_id}", response_model=ApiResponse[BusinessResponse])
async def get_business_by_meta_phone_id(meta_phone_number_id: str, db: AsyncSession = Depends(get_db)):
    """
    Dynamic business resolver for n8n orchestration.
    Given a Meta Cloud API Phone Number ID, returns the matching FlowCore business.
    This is how n8n identifies which business owns an incoming WhatsApp webhook
    without hardcoding any business IDs in the workflow.
    """
    from src.config import settings
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        query = select(BusinessModel).where(BusinessModel.id == settings.ACTIVE_DEV_WORKSPACE)
        res = await db.execute(query)
        business = res.scalar_one_or_none()
        if business:
            return ApiResponse(success=True, data=business)

    query = select(BusinessModel).where(BusinessModel.meta_phone_number_id == meta_phone_number_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No business registered with Meta Phone Number ID '{meta_phone_number_id}'."
        )
    return ApiResponse(success=True, data=business)

@router.get("/{business_id}", response_model=ApiResponse[BusinessResponse])
async def get_business(business_id: str, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business with ID '{business_id}' not found."
        )
    return ApiResponse(success=True, data=business)

@router.put("/{business_id}/settings", response_model=ApiResponse[BusinessResponse])
async def update_settings(business_id: str, payload: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    business.settings_json = json.dumps(payload.settings)
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.put("/{business_id}/catalog", response_model=ApiResponse[BusinessResponse])
async def update_catalog(business_id: str, payload: CatalogUpdate, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    business.catalog_json = json.dumps(payload.catalog)
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.put("/{business_id}/whatsapp", response_model=ApiResponse[BusinessResponse])
async def update_whatsapp(business_id: str, payload: WhatsappUpdate, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    # Check if number already registered by another business
    exist_query = select(BusinessModel).where(
        BusinessModel.whatsapp_number == payload.whatsapp_number,
        BusinessModel.id != business_id
    )
    exist_res = await db.execute(exist_query)
    if exist_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="WhatsApp number already in use by another business.")
    business.whatsapp_number = payload.whatsapp_number
    if payload.meta_phone_number_id is not None:
        business.meta_phone_number_id = payload.meta_phone_number_id
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.put("/{business_id}/meta-phone-id", response_model=ApiResponse[BusinessResponse])
async def update_meta_phone_number_id(business_id: str, payload: MetaPhoneNumberIdUpdate, db: AsyncSession = Depends(get_db)):
    """
    Register or update the Meta Cloud API Phone Number ID for a business.
    Every business must call this once after setting up their Meta WhatsApp account.
    This is what enables dynamic webhook routing in n8n.
    """
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    # Check uniqueness — each Phone Number ID can only belong to one business
    conflict_query = select(BusinessModel).where(
        BusinessModel.meta_phone_number_id == payload.meta_phone_number_id,
        BusinessModel.id != business_id
    )
    conflict_res = await db.execute(conflict_query)
    if conflict_res.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Meta Phone Number ID '{payload.meta_phone_number_id}' is already registered to another business."
        )
    business.meta_phone_number_id = payload.meta_phone_number_id
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.get("/{business_id}/workflows", response_model=ApiResponse[list[WorkflowVersionResponse]])
async def get_business_workflows(business_id: str, db: AsyncSession = Depends(get_db)):
    query = select(WorkflowVersion).where(WorkflowVersion.business_id == business_id)
    res = await db.execute(query)
    workflows = res.scalars().all()
    return ApiResponse(success=True, data=workflows)

@router.post("/create", response_model=ApiResponse[BusinessResponse], status_code=status.HTTP_201_CREATED)
async def create_business_alias(payload: BusinessCreate, db: AsyncSession = Depends(get_db)):
    return await create_business(payload, db)

@router.put("/{business_id}/branding", response_model=ApiResponse[BusinessResponse])
async def update_branding(business_id: str, payload: BrandingUpdate, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    
    settings = json.loads(business.settings_json or "{}")
    settings["branding"] = payload.branding
    business.settings_json = json.dumps(settings)
    
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.put("/{business_id}/delivery", response_model=ApiResponse[BusinessResponse])
async def update_delivery(business_id: str, payload: DeliverySettingsUpdate, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    
    settings = json.loads(business.settings_json or "{}")
    settings["delivery"] = payload.delivery_settings
    business.settings_json = json.dumps(settings)
    
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.put("/{business_id}/payment", response_model=ApiResponse[BusinessResponse])
async def update_payment(business_id: str, payload: PaymentConfigUpdate, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    
    settings = json.loads(business.settings_json or "{}")
    settings["payment"] = payload.payment_config
    business.settings_json = json.dumps(settings)
    
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)

@router.get("/{business_id}/whatsapp-config")
async def get_whatsapp_config(business_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve WhatsApp credentials for the given business.
    Designed for consumption by n8n runtime to send messages dynamically.
    """
    res = await WhatsAppConfigService.get_whatsapp_config(db, business_id)
    if not res["success"]:
        error_code = res["error_code"]
        if error_code == "BUSINESS_NOT_FOUND":
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "error": {
                        "error_code": "BUSINESS_NOT_FOUND"
                    }
                }
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": {
                        "error_code": "WHATSAPP_CONFIG_MISSING"
                    }
                }
            )
            
    return ApiResponse(
        success=True,
        data={
            "phone_number_id": res["phone_number_id"],
            "access_token": res["access_token"]
        }
    )

@router.get("/{business_id}/llm-config", response_model=ApiResponse)
async def get_llm_config(business_id: str, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    
    settings_data = json.loads(business.settings_json or "{}")
    llm_config = settings_data.get("llm_config", {})
    
    def mask_key(k: Optional[str]) -> str:
        if not k:
            return ""
        if len(k) <= 8:
            return "••••••••"
        return f"{k[:4]}••••••••{k[-4:]}"
        
    return ApiResponse(
        success=True,
        data={
            "llm_provider": llm_config.get("llm_provider", "ollama"),
            "openai_api_key": mask_key(llm_config.get("openai_api_key")),
            "gemini_api_key": mask_key(llm_config.get("gemini_api_key")),
            "openai_model": llm_config.get("openai_model", "gpt-4o-mini"),
            "gemini_model": llm_config.get("gemini_model", "gemini-1.5-flash"),
            "ollama_model": llm_config.get("ollama_model", "qwen3:4b"),
            "ollama_endpoint": llm_config.get("ollama_endpoint", "http://localhost:11434")
        }
    )

@router.put("/{business_id}/llm-config", response_model=ApiResponse[BusinessResponse])
async def update_llm_config(business_id: str, payload: LLMConfigUpdate, db: AsyncSession = Depends(get_db)):
    query = select(BusinessModel).where(BusinessModel.id == business_id)
    res = await db.execute(query)
    business = res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found.")
    
    settings_data = json.loads(business.settings_json or "{}")
    existing_llm_config = settings_data.get("llm_config", {})
    
    new_config = payload.llm_config.model_dump()
    
    def should_preserve(val: Optional[str]) -> bool:
        if not val:
            return False
        return "••" in val or val.startswith("****") or val == "********"

    if should_preserve(new_config.get("openai_api_key")):
        new_config["openai_api_key"] = existing_llm_config.get("openai_api_key")
        
    if should_preserve(new_config.get("gemini_api_key")):
        new_config["gemini_api_key"] = existing_llm_config.get("gemini_api_key")
        
    settings_data["llm_config"] = new_config
    business.settings_json = json.dumps(settings_data)
    
    await db.commit()
    await db.refresh(business)
    return ApiResponse(success=True, data=business)
