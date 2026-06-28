from typing import Any, Dict, List, Optional
from src.schemas.graph import WorkflowNode, WorkflowEdge

class ExecutableGraph:
    def __init__(self, compiled_dict: Dict[str, Any]):
        self.workflow_version_id = compiled_dict.get("workflow_version_id")
        self.business_id = compiled_dict.get("business_id")
        self.version_number = compiled_dict.get("version_number")
        self.entry_node_id = compiled_dict.get("entry_node_id")
        self.topological_order = compiled_dict.get("topological_order", [])
        self.nodes = compiled_dict.get("nodes", {})
        self.edges = compiled_dict.get("edges", [])
        self.fsm_transition_table = compiled_dict.get("fsm_transition_table", {})

        # Precompute lookup tables mapping to Pydantic objects for O(1) runtime lookups
        self.node_lookup = {
            nid: WorkflowNode.model_validate(node) 
            for nid, node in self.nodes.items()
        }
        self.edge_lookup = {nid: [] for nid in self.nodes}
        for edge in self.edges:
            from_node = edge.get("from_node")
            if from_node in self.edge_lookup:
                self.edge_lookup[from_node].append(WorkflowEdge.model_validate(edge))

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        return self.node_lookup.get(node_id)

    def get_outgoing_edges(self, node_id: str) -> List[WorkflowEdge]:
        return self.edge_lookup.get(node_id, [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_version_id": self.workflow_version_id,
            "business_id": self.business_id,
            "version_number": self.version_number,
            "entry_node_id": self.entry_node_id,
            "topological_order": self.topological_order,
            "nodes": self.nodes,
            "edges": self.edges,
            "fsm_transition_table": self.fsm_transition_table
        }
