from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class ApiErrorDetail(BaseModel):
    error_code: str
    message: str

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ApiErrorDetail] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
