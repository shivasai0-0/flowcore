from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.schemas.graph import WorkflowGraph
from src.schemas.carry_unit import CarryUnit

class WorkflowVersionCreate(BaseModel):
    business_id: str
    graph: WorkflowGraph
    workflow_type: str = "static"

class WorkflowVersionResponse(BaseModel):
    id: str
    business_id: str
    version_number: int
    status: str
    workflow_type: str
    is_current: bool
    created_at: datetime
    graph_json: str

    class Config:
        from_attributes = True

class WorkflowValidationReport(BaseModel):
    is_valid: bool
    errors: List[str]
    cycle_detected: bool
    connectivity_check: bool
    fsm_check: bool
    contracts_check: bool

class WorkflowRegisterResponse(BaseModel):
    workflow_version_id: str
    status: str
    validation_report: WorkflowValidationReport

class WorkflowSimulationPayload(BaseModel):
    business_id: str
    graph: WorkflowGraph
    simulated_inputs: List[str]

class WorkflowSimulationStep(BaseModel):
    step_number: int
    input_received: str
    node_id: str
    module_name: str
    carry_unit: CarryUnit
    fsm_state: str
    messages_sent: List[str]

class WorkflowSimulationResponse(BaseModel):
    success: bool
    steps: List[WorkflowSimulationStep]
    validation_report: WorkflowValidationReport
    error: Optional[str] = None

class WorkflowCertificationResponse(BaseModel):
    workflow_version_id: str
    static_validation: WorkflowValidationReport
    replay_determinism_certified: bool
    idempotency_certified: bool
    terminal_state_lock_certified: bool

class WorkflowGenerationRequest(BaseModel):
    business_id: str
    business_description: str
    capability_packs: List[str] = []
    llama_endpoint: Optional[str] = "http://localhost:11434"
    use_mock_ai: bool = True

class DraftNode(BaseModel):
    id: str
    module_name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    fsm_transition_to: Optional[str] = None

class DraftEdgeCondition(BaseModel):
    type: str  # always, input_equals, input_in, carry_equals, carry_greater_than
    key: Optional[str] = None
    value: Optional[Any] = None

class DraftEdge(BaseModel):
    from_node: str
    to_node: str
    condition: DraftEdgeCondition = Field(default_factory=lambda: DraftEdgeCondition(type="always"))

class DraftWorkflow(BaseModel):
    id: str
    name: str
    entry_node_id: str
    nodes: List[DraftNode]
    edges: List[DraftEdge] = Field(default_factory=list)

class DraftEventConnection(BaseModel):
    from_workflow_id: str
    to_workflow_id: str
    event_type: str

class WorkflowDraft(BaseModel):
    business_type: str
    workflows: List[DraftWorkflow]
    event_connections: List[DraftEventConnection] = Field(default_factory=list)



