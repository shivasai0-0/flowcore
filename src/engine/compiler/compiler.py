from typing import Any, Dict, Tuple
from src.schemas.graph import WorkflowGraph
from src.schemas.workflow import WorkflowValidationReport
from src.engine.compiler.static_validator import StaticValidator
from src.engine.compiler.graph_optimizer import GraphOptimizer
from src.engine.compiler.executable_graph import ExecutableGraph

class GraphCompilationError(ValueError):
    """Raised when workflow graph compilation fails validation checks."""
    pass

class WorkflowCompiler:
    @staticmethod
    def validate_and_compile(graph: WorkflowGraph) -> Tuple[Dict[str, Any], WorkflowValidationReport]:
        """
        Validates the raw WorkflowGraph against structural, FSM, and contract rules.
        If valid, runs optimization steps and returns the compiled dictionary.
        """
        is_valid, errors, topo_order, cycle_detected, connectivity_check, fsm_check, contracts_check = StaticValidator.validate(graph)

        report = WorkflowValidationReport(
            is_valid=is_valid,
            errors=errors,
            cycle_detected=cycle_detected,
            connectivity_check=connectivity_check,
            fsm_check=fsm_check,
            contracts_check=contracts_check
        )

        compiled_dict = {}
        if is_valid:
            # Construct standard compiled structure
            table = graph.fsm_transition_table if graph.fsm_transition_table else {}
            compiled_dict = {
                "workflow_version_id": graph.workflow_version_id,
                "business_id": graph.business_id,
                "version_number": graph.version_number,
                "entry_node_id": graph.entry_node_id,
                "topological_order": topo_order,
                "nodes": {nid: node.model_dump() for nid, node in graph.nodes.items()},
                "edges": [edge.model_dump() for edge in graph.edges],
                "fsm_transition_table": table
            }

            # Run optimizer steps
            compiled_dict = GraphOptimizer.optimize(compiled_dict)

        return compiled_dict, report
