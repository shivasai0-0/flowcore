from fastapi import APIRouter, HTTPException, status
from src.modules.registry import ModuleRegistry
from src.schemas.contract import ModuleContract
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/modules", tags=["Modules"])

@router.get("", response_model=ApiResponse[list[ModuleContract]])
async def list_modules():
    """Returns all registered modules and their typed contracts."""
    modules = ModuleRegistry.list_all()
    data = [m.contract for m in modules]
    return ApiResponse(success=True, data=data)

@router.get("/{name}", response_model=ApiResponse[ModuleContract])
async def get_module(name: str):
    """Retrieves contract metadata for a single module name."""
    if not ModuleRegistry.exists(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{name}' is not registered in the system."
        )
    data = ModuleRegistry.get(name).contract
    return ApiResponse(success=True, data=data)
