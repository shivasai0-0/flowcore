import json
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models import Business
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/business", tags=["Business"])

class BusinessConfigUpdateRequest(BaseModel):
    business_id: Optional[str] = None
    name: Optional[str] = None
    business_type: Optional[str] = None
    logo_url: Optional[str] = None
    theme_color: Optional[str] = None
    welcome_message: Optional[str] = None

class CatalogItemRequest(BaseModel):
    business_id: Optional[str] = None
    id: Optional[str] = None
    name: str
    price: float
    category: Optional[str] = "default"
    description: Optional[str] = ""
    image_url: Optional[str] = ""

@router.get("/config", response_model=ApiResponse)
async def get_business_config(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
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
        branding = json.loads(business.branding_json or "{}")
    except Exception:
        branding = {}

    return ApiResponse(
        success=True,
        data={
            "id": business.id,
            "name": business.name,
            "whatsapp_number": business.whatsapp_number,
            "business_type": business.business_type,
            "branding": {
                "logo_url": branding.get("logo_url", ""),
                "theme_color": branding.get("theme_color", "#22C55E"),
                "welcome_message": branding.get("welcome_message", "")
            }
        }
    )

@router.put("/config", response_model=ApiResponse)
async def update_business_config(payload: BusinessConfigUpdateRequest, db: AsyncSession = Depends(get_db)):
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

    if payload.name:
        business.name = payload.name
    if payload.business_type:
        business.business_type = payload.business_type.lower()

    try:
        branding = json.loads(business.branding_json or "{}")
    except Exception:
        branding = {}

    if payload.logo_url is not None:
        branding["logo_url"] = payload.logo_url
    if payload.theme_color is not None:
        branding["theme_color"] = payload.theme_color
    if payload.welcome_message is not None:
        branding["welcome_message"] = payload.welcome_message

    business.branding_json = json.dumps(branding)

    await db.commit()
    await db.refresh(business)

    return ApiResponse(
        success=True,
        data={
            "id": business.id,
            "name": business.name,
            "business_type": business.business_type,
            "branding": branding
        }
    )

@router.get("/catalog", response_model=ApiResponse)
async def get_catalog(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
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
        catalog = json.loads(business.catalog_json or "{}")
    except Exception:
        catalog = {}

    # Standardize catalog format: ensure it has an "items" list
    if "items" not in catalog:
        if isinstance(catalog, list):
            catalog = {"items": catalog}
        elif isinstance(catalog, dict) and catalog:
            # Maybe it's a dict mapping id -> item
            items = []
            for k, v in catalog.items():
                if isinstance(v, dict):
                    item = dict(v)
                    item["id"] = item.get("id") or item.get("item_id") or k
                    items.append(item)
                else:
                    items.append({"id": k, "name": k, "price": float(v)})
            catalog = {"items": items}
        else:
            catalog = {"items": []}

    return ApiResponse(success=True, data=catalog.get("items", []))

@router.post("/catalog/item", response_model=ApiResponse)
async def create_catalog_item(payload: CatalogItemRequest, db: AsyncSession = Depends(get_db)):
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

    try:
        catalog = json.loads(business.catalog_json or "{}")
    except Exception:
        catalog = {}

    if "items" not in catalog:
        catalog["items"] = []

    item_id = payload.id or f"item_{uuid.uuid4().hex[:8]}"
    new_item = {
        "id": item_id,
        "name": payload.name,
        "price": payload.price,
        "category": payload.category,
        "description": payload.description,
        "image_url": payload.image_url
    }

    catalog["items"].append(new_item)
    business.catalog_json = json.dumps(catalog)

    await db.commit()
    await db.refresh(business)

    return ApiResponse(success=True, data=new_item)

@router.put("/catalog/item/{item_id}", response_model=ApiResponse)
async def update_catalog_item(item_id: str, payload: CatalogItemRequest, db: AsyncSession = Depends(get_db)):
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

    try:
        catalog = json.loads(business.catalog_json or "{}")
    except Exception:
        catalog = {}

    if "items" not in catalog:
        catalog["items"] = []

    item_found = False
    updated_item = None
    for item in catalog["items"]:
        if item.get("id") == item_id or item.get("item_id") == item_id:
            item["name"] = payload.name
            item["price"] = payload.price
            item["category"] = payload.category
            item["description"] = payload.description
            item["image_url"] = payload.image_url
            item_found = True
            updated_item = item
            break

    if not item_found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog item with ID '{item_id}' not found."
        )

    business.catalog_json = json.dumps(catalog)
    await db.commit()
    await db.refresh(business)

    return ApiResponse(success=True, data=updated_item)

@router.delete("/catalog/item/{item_id}", response_model=ApiResponse)
async def delete_catalog_item(item_id: str, business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
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
        catalog = json.loads(business.catalog_json or "{}")
    except Exception:
        catalog = {}

    if "items" not in catalog:
        catalog["items"] = []

    original_len = len(catalog["items"])
    catalog["items"] = [item for item in catalog["items"] if item.get("id") != item_id and item.get("item_id") != item_id]

    if len(catalog["items"]) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Catalog item with ID '{item_id}' not found."
        )

    business.catalog_json = json.dumps(catalog)
    await db.commit()
    await db.refresh(business)

    return ApiResponse(success=True, data={"id": item_id, "deleted": True})
