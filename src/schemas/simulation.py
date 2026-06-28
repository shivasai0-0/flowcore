from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.schemas.graph import WorkflowGraph
from src.schemas.workflow import WorkflowValidationReport
from src.schemas.carry_unit import CarryUnit

class SimulationInputPayload(BaseModel):
    workflow_graph: Optional[WorkflowGraph] = Field(default=None, description="Graph for dry-run simulation")
    session_id: Optional[str] = Field(default=None, description="Existing session ID to simulate on")
    inputs: List[str] = Field(default_factory=list, description="Sequenced inputs to simulate")
    simulation_mode: str = Field(default="strict", description="Simulation mode: strict, tolerant, replay")
    strict_validation: bool = Field(default=True, description="Strict validation constraints")
    replay_validation: bool = Field(default=False, description="Run replay alignment checks")
    max_steps: int = Field(default=50, description="Max inputs traversal boundary limit")

    # Backward compatibility fields
    graph: Optional[WorkflowGraph] = Field(default=None, description="Graph for dry-run simulation (old)")
    simulated_inputs: Optional[List[str]] = Field(default=None, description="Sequenced inputs to simulate (old)")
    business_id: Optional[str] = Field(default=None, description="Business ID (old)")

class SimulationStepDetail(BaseModel):
    step_number: int
    input_received: str
    node_id: Optional[str] = None
    module_name: Optional[str] = None
    carry_unit_snapshot: Optional[Dict[str, Any]] = None
    fsm_state_before: str
    fsm_state_after: str
    messages_sent: List[str] = Field(default_factory=list)
    executed_nodes: List[str] = Field(default_factory=list)
    routing_decision: Optional[Dict[str, Any]] = None
    latency_ms: int
    error: Optional[str] = None
    carry_diff: Optional[Dict[str, Any]] = None
    fsm_transition: Optional[str] = None
    side_effects: List[str] = Field(default_factory=list)
    edge_logs: List[str] = Field(default_factory=list)

    # Backward compatibility fields (matching WorkflowSimulationStep)
    carry_unit: Optional[CarryUnit] = None
    fsm_state: Optional[str] = None

class SimulationReplaySummary(BaseModel):
    replay_match: bool
    divergence_step: Optional[int] = None
    mismatch_reason: Optional[str] = None

class SimulationResponse(BaseModel):
    success: bool
    test_name: str
    simulation_mode: str
    executed_steps: List[SimulationStepDetail] = Field(default_factory=list)
    executed_nodes: List[str] = Field(default_factory=list)
    fsm_progression: List[str] = Field(default_factory=list)
    runtime_errors: List[str] = Field(default_factory=list)
    replay_results: Optional[SimulationReplaySummary] = None
    validation_report: Optional[WorkflowValidationReport] = None
    execution_timings: Dict[str, Any] = Field(default_factory=dict)

    # Backward compatibility fields (matching WorkflowSimulationResponse)
    steps: List[SimulationStepDetail] = Field(default_factory=list)
    error: Optional[str] = None
