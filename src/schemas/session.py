from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.schemas.carry_unit import CarryUnit

class SessionCreate(BaseModel):
    business_id: str
    customer_phone: str

class SessionResponse(BaseModel):
    id: str
    business_id: str
    customer_phone: str
    fsm_state: str
    current_node_id: Optional[str] = None
    carry_unit: CarryUnit
    workflow_version_id: str
    updated_at: datetime

    class Config:
        from_attributes = True

class DispatchPayload(BaseModel):
    user_input: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UiAction(BaseModel):
    label: str
    action: str

class FormField(BaseModel):
    name: str
    type: str
    label: str
    required: bool = True
    options: Optional[List[str]] = None

class FormDefinition(BaseModel):
    type: str = "form"
    title: str
    fields: List[FormField] = Field(default_factory=list)

class UiObject(BaseModel):
    text: str = ""
    actions: List[UiAction] = Field(default_factory=list)
    form: Optional[FormDefinition] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DispatchResponse(BaseModel):
    session_id: str
    fsm_state_before: str
    fsm_state_after: str
    executed_nodes: List[str]
    carry_unit: CarryUnit
    messages_sent: List[str]
    ui: Optional[UiObject] = None
    available_actions: Optional[List[str]] = None
    side_effects: List[Dict[str, Any]] = Field(default_factory=dict)
    edge_logs: List[str] = Field(default_factory=list)
    routing_trace: List[str] = Field(default_factory=list)

class ReplayStep(BaseModel):
    node_id: str
    module_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    fsm_state_before: str
    fsm_state_after: str
    executed_at: datetime
    latency_ms: Optional[int] = None
    routing_decision: Optional[str] = None
    carry_diff: Optional[Dict[str, Any]] = None
    fsm_transition: Optional[str] = None
    side_effects: List[str] = Field(default_factory=list)
    edge_logs: List[str] = Field(default_factory=list)

class ReplayResponse(BaseModel):
    session_id: str
    trace: List[ReplayStep]
    final_carry_unit: CarryUnit
    final_fsm_state: str
