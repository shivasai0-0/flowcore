from collections import deque
from typing import Any, Dict, List, Set, Tuple
from src.modules.registry import ModuleRegistry
from src.schemas.graph import WorkflowGraph
from src.fsm.engine import FSMEngine

class StaticValidator:
    @staticmethod
    def validate(graph: WorkflowGraph) -> Tuple[bool, List[str], List[str], bool, bool, bool, bool]:
        """
        Statically validates a WorkflowGraph.
        Returns:
            is_valid (bool)
            errors (List[str])
            topological_order (List[str])
            cycle_detected (bool)
            connectivity_check (bool)
            fsm_check (bool)
            contracts_check (bool)
        """
        errors = []
        cycle_detected = False
        connectivity_check = True
        fsm_check = True
        contracts_check = True

        # Fallback node-centric to edge-centric translation
        from src.schemas.graph import WorkflowEdge, EdgeCondition
        flat_edges = list(graph.edges) if graph.edges else []
        for nid, node in graph.nodes.items():
            if getattr(node, "edges", None):
                for edge_data in node.edges:
                    to_node = edge_data.get("to_node")
                    cond_data = edge_data.get("condition", {"type": "always"})
                    cond = EdgeCondition.model_validate(cond_data)
                    # Avoid duplicate edge addition
                    if not any(e.from_node == nid and e.to_node == to_node for e in flat_edges):
                        flat_edges.append(WorkflowEdge(
                            from_node=nid,
                            to_node=to_node,
                            condition=cond
                        ))
        graph.edges = flat_edges

        # 1. Validate Entry Node
        if not graph.entry_node_id:
            errors.append("Validation Error: Entry node ID is not set.")
        elif graph.entry_node_id not in graph.nodes:
            errors.append(f"Validation Error: Entry node ID '{graph.entry_node_id}' does not exist in graph nodes.")

        # 2. Validate Edge References
        for edge in graph.edges:
            if edge.from_node not in graph.nodes:
                errors.append(f"Validation Error: Edge source node '{edge.from_node}' does not exist.")
            if edge.to_node not in graph.nodes:
                errors.append(f"Validation Error: Edge target node '{edge.to_node}' does not exist.")

        # Return early if base references are broken
        if errors:
            return False, errors, [], False, False, False, False

        # 3. Cycle Detection & Topological Sort (Kahn's Algorithm)
        adj: Dict[str, List[str]] = {nid: [] for nid in graph.nodes}
        in_degree: Dict[str, int] = {nid: 0 for nid in graph.nodes}
        for edge in graph.edges:
            adj[edge.from_node].append(edge.to_node)
            in_degree[edge.to_node] += 1

        queue = deque([nid for nid in graph.nodes if in_degree[nid] == 0])
        topo_order = []
        while queue:
            curr = queue.popleft()
            topo_order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(topo_order) < len(graph.nodes):
            cycle_detected = True
            errors.append("Validation Error: Cycle detected in graph. Workflow must be an acyclic graph (DAG).")
            connectivity_check = False

        # 4. Reachability Check (BFS from Entry Node)
        visited = set()
        if graph.entry_node_id in graph.nodes:
            q = deque([graph.entry_node_id])
            visited.add(graph.entry_node_id)
            while q:
                curr = q.popleft()
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        q.append(neighbor)

            unreachable_nodes = set(graph.nodes.keys()) - visited
            if unreachable_nodes:
                connectivity_check = False
                errors.append(f"Validation Error: Unreachable nodes detected: {list(unreachable_nodes)}")

        # 5. Module existence check
        for nid, node in graph.nodes.items():
            if not ModuleRegistry.exists(node.module_name):
                errors.append(f"Validation Error: Node '{nid}' uses unregistered module '{node.module_name}'.")

        # 6. FSM Compatibility Check
        table = graph.fsm_transition_table if graph.fsm_transition_table else FSMEngine.DEFAULT_TRANSITION_TABLE
        for state_from, transitions in table.items():
            for state_to, trigger_module in transitions.items():
                if not ModuleRegistry.exists(trigger_module):
                    fsm_check = False
                    errors.append(
                        f"FSM Compatibility Error: Transition '{state_from} -> {state_to}' "
                        f"refers to unregistered triggering module '{trigger_module}'."
                    )

        # FSM State existence
        valid_states = {"START", "MENU", "CART", "CHECKOUT", "PAYMENT", "CONFIRMED", "CANCELLED", "ERROR"}
        for state_from, transitions in table.items():
            valid_states.add(state_from)
            for state_to in transitions.keys():
                valid_states.add(state_to)

        # FSM reachability check in the transition table
        reached = {"START"}
        state_queue = deque(["START"])
        while state_queue:
            curr_state = state_queue.popleft()
            for target_state in table.get(curr_state, {}).keys():
                if target_state not in reached:
                    reached.add(target_state)
                    state_queue.append(target_state)

        all_table_states = set(table.keys())
        for transitions in table.values():
            all_table_states.update(transitions.keys())

        unreachable_states = all_table_states - reached
        if unreachable_states:
            fsm_check = False
            errors.append(f"FSM Compatibility Error: Unreachable states in FSM transition table: {list(unreachable_states)}")

        # Propagation of FSM states along the workflow graph DAG
        if not cycle_detected:
            FSM_in: Dict[str, Set[str]] = {nid: set() for nid in graph.nodes}
            FSM_out: Dict[str, Set[str]] = {nid: set() for nid in graph.nodes}

            if graph.entry_node_id in FSM_in:
                FSM_in[graph.entry_node_id].add("START")

            for nid in topo_order:
                node = graph.nodes[nid]
                if not ModuleRegistry.exists(node.module_name):
                    continue
                module = ModuleRegistry.get(node.module_name)

                # Skip nodes that are unreachable from the entry node
                if not FSM_in[nid]:
                    continue

                for state_in in FSM_in[nid]:
                    # A. Check if the FSM state matches allowed_fsm_states of the module contract
                    if state_in not in module.contract.allowed_fsm_states and "*" not in module.contract.allowed_fsm_states:
                        fsm_check = False
                        errors.append(
                            f"FSM Compatibility Error: Node '{nid}' running module '{node.module_name}' "
                            f"is executed in FSM state '{state_in}', which is not allowed by the module contract."
                        )

                    # B. Determine target state
                    if node.fsm_transition_to:
                        state_out = node.fsm_transition_to
                        
                        # Verify target state exists
                        if state_out not in valid_states:
                            fsm_check = False
                            errors.append(
                                f"FSM Compatibility Error: Node '{nid}' transitions to unregistered "
                                f"FSM state '{state_out}'."
                            )

                        # Validate FSM State transition rules if FSM state changes
                        if state_in != state_out:
                            if state_in in FSMEngine.TERMINAL_STATES:
                                fsm_check = False
                                errors.append(
                                    f"FSM Compatibility Error: Node '{nid}' attempts transition from "
                                    f"terminal state '{state_in}' to '{state_out}'."
                                )
                            else:
                                transitions = table.get(state_in, {})
                                allowed_trigger = transitions.get(state_out)

                                if not allowed_trigger:
                                    fsm_check = False
                                    errors.append(
                                        f"FSM Compatibility Error: Illegal transition from state '{state_in}' "
                                        f"to '{state_out}' via module '{node.module_name}' at node '{nid}' (no transition defined)."
                                    )
                                elif allowed_trigger != node.module_name:
                                    fsm_check = False
                                    errors.append(
                                        f"FSM Compatibility Error: Illegal transition from state '{state_in}' "
                                        f"to '{state_out}' via module '{node.module_name}' at node '{nid}'. "
                                        f"Expected triggering module is '{allowed_trigger}'."
                                    )
                    else:
                        state_out = state_in

                    FSM_out[nid].add(state_out)

                # Propagate FSM_out to child nodes
                for child in adj[nid]:
                    FSM_in[child].update(FSM_out[nid])

            # 6b. Dead-end node detection (non-terminal leaf nodes that do not expect user input)
            for nid in visited:
                node = graph.nodes[nid]
                if len(adj[nid]) == 0:  # Leaf node
                    node_states = FSM_out.get(nid, set())
                    non_terminal_states = [s for s in node_states if s not in {"CONFIRMED", "CANCELLED"}]
                    if non_terminal_states:
                        if ModuleRegistry.exists(node.module_name):
                            module = ModuleRegistry.get(node.module_name)
                            expects_input = getattr(module.contract, "expects_user_input", False)
                            if not expects_input:
                                errors.append(
                                    f"Validation Error: Dead-end node detected: Node '{nid}' has no outgoing edges, "
                                    f"transitions to non-terminal state(s) {non_terminal_states}, and does not expect user input."
                                )

        # 7. Static Contract Dependency Satisfaction
        if not cycle_detected and connectivity_check:
            initial_fields = {
                "session.session_id",
                "session.customer_phone",
                "session.business_id",
                "session.workflow_version_id",
                "session.session_started_at"
            }
            available_fields: Dict[str, Set[str]] = {nid: set(initial_fields) for nid in graph.nodes}

            for nid in topo_order:
                node = graph.nodes[nid]
                if not ModuleRegistry.exists(node.module_name):
                    continue
                module = ModuleRegistry.get(node.module_name)

                missing_requires = []
                for req_field, req_type in module.contract.requires.items():
                    if req_field not in available_fields[nid]:
                        missing_requires.append(req_field)
                
                if missing_requires:
                    contracts_check = False
                    errors.append(
                        f"Contract Compatibility Error: Node '{nid}' [module: {node.module_name}] "
                        f"missing required inputs: {missing_requires}."
                    )

                produced_by_node = set(module.contract.produces.keys())
                fields_after_exec = available_fields[nid] | produced_by_node

                for child in adj[nid]:
                    available_fields[child] = available_fields[child] | fields_after_exec

        # 8. Terminal States reachability check
        terminal_reachable = False
        for nid in visited:
            node = graph.nodes[nid]
            if node.fsm_transition_to in FSMEngine.TERMINAL_STATES or len(adj[nid]) == 0:
                terminal_reachable = True
                break
        
        if not terminal_reachable:
            errors.append("Validation Error: Graph has no paths leading to a terminal state (CONFIRMED, CANCELLED) or leaf node.")

        # 9. Action Registry and Routability Enforcements
        from src.engine.actions import REGISTERED_ACTIONS, get_action_for_input

        # 9a. Validate that all actions emitted by nodes/modules are registered
        for nid, node in graph.nodes.items():
            if ModuleRegistry.exists(node.module_name):
                module_cls = ModuleRegistry.get(node.module_name)
                emitted = getattr(module_cls, "emitted_actions", [])
                for act in emitted:
                    if act not in REGISTERED_ACTIONS:
                        errors.append(f"Action Validation Error: Node '{nid}' module '{node.module_name}' emits unregistered action '{act}'.")

        # 9b. Validate that all graph routes/edge conditions only reference registered actions
        for edge in graph.edges:
            if edge.condition.type in ("input_equals", "input_in"):
                cond_vals = edge.condition.value if isinstance(edge.condition.value, list) else [edge.condition.value]
                for val in cond_vals:
                    if val is not None:
                        act = get_action_for_input(str(val))
                        if not act:
                            errors.append(f"Action Validation Error: Edge from '{edge.from_node}' to '{edge.to_node}' condition checks unregistered action/input '{val}'.")

        # 9c. Validate that FSM transitions only reference registered actions where target state matches FSM transitions
        # Also check that every emitted action is routable (has an outgoing edge or global intercept)
        if not cycle_detected:
            global_actions = {
                "CONTACT_SUPPORT", "ADD_MORE_ITEMS", "CANCEL_ORDER",
                "VIEW_CART", "CALCULATE_TOTAL", "RETRY_PAYMENT",
                "TRACK_DELIVERY", "VIEW_ORDER"
            }
            ACTION_TARGET_STATES = {
                "CHECKOUT": {"CHECKOUT"},
                "CONFIRM_PAYMENT": {"CONFIRMED"},
                "RETRY_PAYMENT": {"PAYMENT"},
                "VIEW_CART": {"CART", "CART_REVIEW"},
                "TRACK_DELIVERY": {"CONFIRMED"},
                "VIEW_ORDER": {"CONFIRMED"},
                "CALCULATE_TOTAL": {"CART_REVIEW"},
                "ADD_MORE_ITEMS": {"MENU", "BROWSING"},
                "CANCEL_ORDER": {"CANCELLED"},
            }
            for nid in visited:
                node = graph.nodes[nid]
                # A node is only halting if it doesn't automatically cascade via an always edge
                has_always_edge = any(edge_obj.condition.type == "always" for edge_obj in graph.edges if edge_obj.from_node == nid)
                if has_always_edge:
                    continue
                if not ModuleRegistry.exists(node.module_name):
                    continue
                module_cls = ModuleRegistry.get(node.module_name)
                node_states = FSM_out.get(nid, set())
                
                for state in node_states:
                    # Skip action routability checks if the FSM state is terminal (CONFIRMED, CANCELLED)
                    if state in {"CONFIRMED", "CANCELLED"}:
                        continue
                        
                    # Gather all actions emitted in this state at this node
                    emitted_in_state = set()
                    # 1. From get_operational_actions
                    from src.engine.traversal import get_operational_actions
                    for act_obj in get_operational_actions(state, None):
                        emitted_in_state.add(act_obj.action)
                    # 2. From module's emitted actions
                    emitted_in_state.update(getattr(module_cls, "emitted_actions", []))

                    # Check each emitted action
                    for act in emitted_in_state:
                        if act in global_actions:
                            # Globally intercepted, so always routable
                            continue
                        
                        # Only enforce routability for actions whose target FSM states are actually declared in valid_states
                        target_states = ACTION_TARGET_STATES.get(act, set())
                        if target_states and not (target_states & valid_states):
                            continue

                        # Verify an edge exists from nid matching this action
                        edge_found = False
                        for child in adj[nid]:
                            # Find edge(s) from nid to child
                            for edge_obj in graph.edges:
                                if edge_obj.from_node == nid and edge_obj.to_node == child:
                                    if edge_obj.condition.type == "always":
                                        edge_found = True
                                        break
                                    elif edge_obj.condition.type in ("input_equals", "input_in"):
                                        vals = edge_obj.condition.value if isinstance(edge_obj.condition.value, list) else [edge_obj.condition.value]
                                        for v in vals:
                                            if get_action_for_input(str(v)) == act:
                                                edge_found = True
                                                break
                                    if edge_found:
                                        break
                            if edge_found:
                                break
                        
                        if not edge_found:
                            errors.append(f"Action Validation Error: Emitted action '{act}' in state '{state}' at node '{nid}' has no matching graph route/edge.")

        is_valid = len(errors) == 0
        return is_valid, errors, topo_order, cycle_detected, connectivity_check, fsm_check, contracts_check


