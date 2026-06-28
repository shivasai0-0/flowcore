from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class EdgeCondition(BaseModel):
    type: str  # always, input_equals, input_in, carry_equals, carry_greater_than
    key: Optional[str] = None  # for carry_equals / carry_greater_than, e.g., "order.total"
    value: Optional[Any] = None  # value to check against

class WorkflowEdge(BaseModel):
    from_node: str
    to_node: str
    condition: EdgeCondition = Field(default_factory=lambda: EdgeCondition(type="always"))

class WorkflowNode(BaseModel):
    id: str
    module_name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    fsm_transition_to: Optional[str] = None
    edges: Optional[List[Dict[str, Any]]] = None

class WorkflowGraph(BaseModel):
    workflow_version_id: Optional[str] = None
    business_id: str
    version_number: int
    entry_node_id: str
    nodes: Dict[str, WorkflowNode]
    edges: List[WorkflowEdge] = Field(default_factory=list)
    fsm_transition_table: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="fsm_state_from -> { fsm_state_to: module_name_trigger }"
    )
    trigger_event: Optional[str] = None
    trigger_events: List[str] = Field(default_factory=list)
