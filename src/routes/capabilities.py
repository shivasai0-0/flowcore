from fastapi import APIRouter
from src.schemas.envelope import ApiResponse
from src.engine.registries.capability_registry import CapabilityRegistry, VALID_CATEGORIES
from src.engine.registries.event_registry import EVENT_SCHEMAS
from src.engine.registries.provider_registry import PROVIDER_METADATA

router = APIRouter(prefix="/api/v1/capabilities", tags=["Capabilities"])

@router.get("", response_model=ApiResponse)
async def list_capabilities():
    return ApiResponse(
        success=True,
        data=CapabilityRegistry.list_all()
    )

@router.get("/packs", response_model=ApiResponse)
async def list_packs():
    return ApiResponse(
        success=True,
        data=list(VALID_CATEGORIES)
    )

@router.get("/events", response_model=ApiResponse)
async def list_events():
    return ApiResponse(
        success=True,
        data=EVENT_SCHEMAS
    )

@router.get("/providers", response_model=ApiResponse)
async def list_providers():
    return ApiResponse(
        success=True,
        data=PROVIDER_METADATA
    )
