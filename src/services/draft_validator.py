import json
import collections
from typing import Dict, Any, List, Tuple, Optional, Set
from pydantic import ValidationError

from src.schemas.workflow import WorkflowDraft
from src.modules.registry import ModuleRegistry

class WorkflowDraftValidator:
    @staticmethod
    def validate_draft_json(raw_text: str) -> Tuple[bool, List[str], Optional[WorkflowDraft]]:
        """
        Parses raw JSON string checking for duplicate keys and validates it against the WorkflowDraft schema
        and internal consistency rules.
        
        Returns:
            is_valid (bool)
            errors (List[str])
            parsed_draft (Optional[WorkflowDraft])
        """
        errors = []

        # 1. Valid JSON structure and duplicate keys check
        def check_duplicate_keys(pairs):
            seen = set()
            for key, value in pairs:
                if key in seen:
                    raise ValueError(f"Duplicate key in JSON: {key}")
                seen.add(key)
            return dict(pairs)

        try:
            parsed_dict = json.loads(raw_text, object_pairs_hook=check_duplicate_keys)
        except json.JSONDecodeError as de:
            return False, [f"JSON Syntax Error: {str(de)}"], None
        except ValueError as ve:
            return False, [f"JSON Validation Error: {str(ve)}"], None

        # 2. Pydantic schema validation
        try:
            draft = WorkflowDraft.model_validate(parsed_dict)
        except ValidationError as val_err:
            for error in val_err.errors():
                loc = " -> ".join(str(l) for l in error["loc"])
                errors.append(f"Schema Error at '{loc}': {error['msg']}")
            return False, errors, None

        # 3. Duplicate workflow IDs
        workflow_ids = [w.id for w in draft.workflows]
        seen_wfs = set()
        for w_id in workflow_ids:
            if w_id in seen_wfs:
                errors.append(f"Duplicate workflow ID '{w_id}' found in draft.")
            seen_wfs.add(w_id)

        # Map to verify event connections later
        all_wf_ids = set(workflow_ids)

        valid_fsm_states = {"START", "MENU", "CART", "CHECKOUT", "PAYMENT", "CONFIRMED", "CANCELLED", "ERROR"}

        # Validate each workflow
        for wf in draft.workflows:
            # 4. Duplicate node IDs within workflow
            node_ids = [n.id for n in wf.nodes]
            seen_nodes = set()
            for n_id in node_ids:
                if n_id in seen_nodes:
                    errors.append(f"Duplicate node ID '{n_id}' found in workflow '{wf.id}'.")
                seen_nodes.add(n_id)
            
            node_map = {n.id: n for n in wf.nodes}

            # 5. Valid entry node
            if not wf.entry_node_id:
                errors.append(f"Validation Error: Entry node ID is not set in workflow '{wf.id}'.")
            elif wf.entry_node_id not in node_map:
                errors.append(f"Validation Error: Entry node ID '{wf.entry_node_id}' does not exist in workflow '{wf.id}' nodes.")

            # 6. Valid capability names and FSM states
            for node in wf.nodes:
                if not ModuleRegistry.exists(node.module_name):
                    errors.append(f"Validation Error: Node '{node.id}' in workflow '{wf.id}' uses unregistered module '{node.module_name}'.")
                
                if node.fsm_transition_to and node.fsm_transition_to not in valid_fsm_states:
                    errors.append(
                        f"FSM State Error: Node '{node.id}' in workflow '{wf.id}' transitions to invalid FSM state '{node.fsm_transition_to}'."
                    )

            # 7. Valid edge references
            adj = {n_id: [] for n_id in node_map}
            in_degree = {n_id: 0 for n_id in node_map}
            out_degree = {n_id: 0 for n_id in node_map}

            for edge in wf.edges:
                if edge.from_node not in node_map:
                    errors.append(f"Edge Error: Source node '{edge.from_node}' in workflow '{wf.id}' does not exist.")
                if edge.to_node not in node_map:
                    errors.append(f"Edge Error: Target node '{edge.to_node}' in workflow '{wf.id}' does not exist.")
                
                if edge.from_node in node_map and edge.to_node in node_map:
                    adj[edge.from_node].append(edge.to_node)
                    in_degree[edge.to_node] += 1
                    out_degree[edge.from_node] += 1

            # 8. Reachable nodes
            if wf.entry_node_id in node_map:
                visited = set()
                queue = collections.deque([wf.entry_node_id])
                visited.add(wf.entry_node_id)
                while queue:
                    curr = queue.popleft()
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                
                unreachable = [n_id for n_id in node_map if n_id not in visited]
                for u in unreachable:
                    errors.append(f"Validation Error: Node '{u}' in workflow '{wf.id}' is unreachable from entry node '{wf.entry_node_id}'.")

            # 9. No orphan nodes
            if len(wf.nodes) > 1:
                for n_id in node_map:
                    if in_degree[n_id] == 0 and out_degree[n_id] == 0:
                        errors.append(f"Validation Error: Orphan node '{n_id}' detected in workflow '{wf.id}' (has no incoming or outgoing edges).")

        # 10. Valid event references
        for conn in draft.event_connections:
            if not conn.event_type:
                errors.append("Event Connection Error: event_type cannot be empty.")
            if conn.from_workflow_id not in all_wf_ids:
                errors.append(f"Event Connection Error: from_workflow_id '{conn.from_workflow_id}' does not exist.")
            if conn.to_workflow_id not in all_wf_ids:
                errors.append(f"Event Connection Error: to_workflow_id '{conn.to_workflow_id}' does not exist.")

        is_valid = len(errors) == 0
        return is_valid, errors, (draft if is_valid else None)
