from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator

class SessionNamespace(BaseModel):
    session_id: str
    customer_phone: str
    business_id: str
    workflow_version_id: str
    session_started_at: str

class CustomerNamespace(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    shared_context: Optional[Dict[str, Any]] = None

class OrderItem(BaseModel):
    item_id: str
    quantity: int
    price: float

class OrderNamespace(BaseModel):
    items: List[OrderItem] = Field(default_factory=list)
    total: float = 0.0
    status: str = "PENDING"  # PENDING, PLACED, CANCELLED

class PaymentNamespace(BaseModel):
    payment_url: Optional[str] = None
    transaction_id: Optional[str] = None
    status: str = "PENDING"  # PENDING, SUCCESS, FAILED

class WorkflowNamespace(BaseModel):
    execution_trace: List[str] = Field(default_factory=list)

class LogisticsNamespace(BaseModel):
    delivery_id: Optional[str] = None
    address: Optional[str] = None
    status: Optional[str] = None

class AnalyticsNamespace(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)

class MetadataNamespace(BaseModel):
    data: Dict[str, Any] = Field(default_factory=dict)

class CarryUnit(BaseModel):
    version: int = 1
    session: SessionNamespace
    customer: CustomerNamespace = Field(default_factory=CustomerNamespace)
    order: OrderNamespace = Field(default_factory=OrderNamespace)
    payment: PaymentNamespace = Field(default_factory=PaymentNamespace)
    workflow: WorkflowNamespace = Field(default_factory=WorkflowNamespace)
    logistics: LogisticsNamespace = Field(default_factory=LogisticsNamespace)
    analytics: AnalyticsNamespace = Field(default_factory=AnalyticsNamespace)
    metadata: MetadataNamespace = Field(default_factory=MetadataNamespace)

    def merge_patch(self, patch: Dict[str, Any]) -> "CarryUnit":
        """
        Monotonically merges a dictionary patch into the carry unit while enforcing invariants.
        Delegates validation and merging to CarryUnitMergeEngine.
        """
        from src.engine.carry.merge_engine import CarryUnitMergeEngine
        merged_data = CarryUnitMergeEngine.merge_patch(self, patch)
        return CarryUnit.model_validate(merged_data)
