from typing import Any, Dict, Set

class GraphOptimizer:
    @staticmethod
    def optimize(compiled_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimizes the compiled graph dictionary by:
        1. Pruning dead (unreachable) nodes.
        2. Filtering edges that reference pruned nodes.
        """
        entry_node_id = compiled_dict.get("entry_node_id")
        nodes = compiled_dict.get("nodes", {})
        edges = compiled_dict.get("edges", [])

        if not entry_node_id or entry_node_id not in nodes:
            return compiled_dict

        # Simple reachability search to identify reachable nodes
        adj = {nid: [] for nid in nodes}
        for edge in edges:
            from_node = edge.get("from_node")
            to_node = edge.get("to_node")
            if from_node in adj:
                adj[from_node].append(to_node)

        visited: Set[str] = set()
        queue = [entry_node_id]
        visited.add(entry_node_id)
        
        while queue:
            curr = queue.pop(0)
            for neighbor in adj.get(curr, []):
                if neighbor not in visited and neighbor in nodes:
                    visited.add(neighbor)
                    queue.append(neighbor)

        # Prune nodes not in visited
        pruned_nodes = {nid: nval for nid, nval in nodes.items() if nid in visited}
        pruned_edges = [
            edge for edge in edges
            if edge.get("from_node") in visited and edge.get("to_node") in visited
        ]

        # Re-compute topological order on pruned nodes
        topo_order = compiled_dict.get("topological_order", [])
        pruned_topo = [nid for nid in topo_order if nid in visited]

        optimized_dict = dict(compiled_dict)
        optimized_dict["nodes"] = pruned_nodes
        optimized_dict["edges"] = pruned_edges
        optimized_dict["topological_order"] = pruned_topo

        return optimized_dict
