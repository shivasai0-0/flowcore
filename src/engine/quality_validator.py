"""
FlowCore Workflow Quality Validator — Business Logic Layer.

This validator runs AFTER the structural FSM/schema validator passes.
It enforces business-domain-specific ordering and completeness rules.

Usage:
    report = WorkflowQualityValidator.validate(graph_dict, category)
    if not report["passed"]:
        for v in report["violations"]:
            print(v["rule"], v["hint"])
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("flowcore.quality_validator")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _module_order(nodes: Dict[str, Any], edges: List[Dict[str, Any]]) -> List[str]:
    """
    Topological walk of edges; returns an ordered list of module_names as they
    would execute for a customer going through the happy path (always / any_input edges).
    Cycles are broken after 100 steps.
    """
    # Build adjacency: node_id → list of successors on non-conditional edges
    adj: Dict[str, List[str]] = {}
    for edge in edges:
        src = edge.get("from_node", "")
        dst = edge.get("to_node", "")
        ctype = edge.get("condition", {}).get("type", "always")
        # Include input_equals — these are confirmation steps still on the happy path
        if ctype in ("always", "any_input", "input_equals"):
            adj.setdefault(src, []).append(dst)

    # Find entry node (node_id not appearing as a dst)
    all_dsts = {e.get("to_node") for e in edges}
    entry_candidates = [nid for nid in nodes if nid not in all_dsts]
    start = entry_candidates[0] if entry_candidates else (list(nodes.keys())[0] if nodes else None)
    if not start:
        return []

    ordered_modules: List[str] = []
    visited: set = set()
    queue = [start]
    steps = 0
    while queue and steps < 100:
        steps += 1
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        node = nodes.get(nid, {})
        mod = node.get("module_name")
        if mod:
            ordered_modules.append(mod)
        for succ in adj.get(nid, []):
            if succ not in visited:
                queue.append(succ)
    return ordered_modules


def _module_set(nodes: Dict[str, Any]) -> set:
    return {n.get("module_name") for n in nodes.values() if n.get("module_name")}


def _idx(ordered: List[str], module: str) -> int:
    """Returns first position of module in ordered list, or -1."""
    try:
        return ordered.index(module)
    except ValueError:
        return -1


def _make_violation(rule: str, severity: str, hint: str) -> Dict[str, str]:
    return {"rule": rule, "severity": severity, "hint": hint}


# ---------------------------------------------------------------------------
# Category rule sets
# ---------------------------------------------------------------------------

RESTAURANT_REQUIRED_MODULES = [
    "show_menu", "collect_cart", "calculate_total",
    "create_order", "create_payment", "confirm_payment",
    "collect_address", "create_delivery", "notify_customer",
]

RESTAURANT_ORDER_RULES = [
    # (earlier_module, later_module, rule_name)
    ("collect_cart",     "calculate_total", "cart_before_total"),
    ("calculate_total",  "create_order",    "total_before_order"),
    ("create_order",     "create_payment",  "order_before_payment"),
    ("create_payment",   "confirm_payment", "payment_before_confirm"),
    ("confirm_payment",  "collect_address", "confirm_before_address"),
    ("collect_address",  "create_delivery", "address_before_delivery"),
    ("create_delivery",  "notify_customer", "delivery_before_notify"),
]

HOSPITAL_REQUIRED_MODULES = [
    "show_menu", "collect_cart", "create_order",
    "create_payment", "confirm_payment", "notify_customer",
]

HOSPITAL_ORDER_RULES = [
    ("collect_cart",    "create_order",     "selection_before_order"),
    ("create_order",    "create_payment",   "order_before_payment"),
    ("create_payment",  "confirm_payment",  "payment_before_confirm"),
    ("confirm_payment", "notify_customer",  "confirm_before_notify"),
]

EDUCATION_REQUIRED_MODULES = [
    "show_menu", "collect_cart", "create_order",
    "create_payment", "confirm_payment", "notify_customer",
]

EDUCATION_ORDER_RULES = [
    ("collect_cart",    "create_order",     "selection_before_registration"),
    ("create_order",    "create_payment",   "registration_before_fee_payment"),
    ("create_payment",  "confirm_payment",  "fee_before_confirm"),
    ("confirm_payment", "notify_customer",  "confirm_before_notify"),
]

REALESTATE_REQUIRED_MODULES = [
    "show_menu", "collect_cart", "create_order", "notify_customer",
]

REALESTATE_ORDER_RULES = [
    ("collect_cart",  "create_order",    "selection_before_lead_capture"),
    ("create_order",  "notify_customer", "lead_capture_before_followup"),
]

# Generic booking (Salon, Gym, Hotel, Travel, …)
BOOKING_REQUIRED_MODULES = [
    "show_menu", "collect_cart", "create_order",
    "create_payment", "confirm_payment", "notify_customer",
]

BOOKING_ORDER_RULES = [
    ("collect_cart",    "create_order",     "selection_before_booking"),
    ("create_order",    "create_payment",   "booking_before_payment"),
    ("create_payment",  "confirm_payment",  "payment_before_confirm"),
    ("confirm_payment", "notify_customer",  "confirm_before_notify"),
]


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------

class WorkflowQualityValidator:
    """
    Validates business-logic quality of a single workflow graph dict.

    Parameters
    ----------
    graph    : dict — workflow graph (nodes, edges, fsm_transition_table, …)
    category : str — lowercase FlowCore category constant (e.g. "restaurant")

    Returns
    -------
    dict with keys:
        passed      : bool
        category    : str
        violations  : list[dict]   — each has rule, severity, hint
        warnings    : list[str]
        module_order: list[str]    — happy-path module execution order
    """

    @staticmethod
    def validate(graph: Dict[str, Any], category: str) -> Dict[str, Any]:
        nodes  = graph.get("nodes", {})
        edges  = graph.get("edges", [])
        mods   = _module_set(nodes)
        ordered = _module_order(nodes, edges)

        violations: List[Dict[str, str]] = []
        warnings:   List[str]            = []

        # -----------------------------------------------------------------
        # Dispatch to category-specific rules
        # -----------------------------------------------------------------
        if category == "restaurant":
            violations += WorkflowQualityValidator._check_required(
                mods, RESTAURANT_REQUIRED_MODULES, category)
            violations += WorkflowQualityValidator._check_order(
                ordered, RESTAURANT_ORDER_RULES, category)

        elif category in ("hospital", "clinic"):
            violations += WorkflowQualityValidator._check_required(
                mods, HOSPITAL_REQUIRED_MODULES, category)
            violations += WorkflowQualityValidator._check_order(
                ordered, HOSPITAL_ORDER_RULES, category)

        elif category == "education":
            violations += WorkflowQualityValidator._check_required(
                mods, EDUCATION_REQUIRED_MODULES, category)
            violations += WorkflowQualityValidator._check_order(
                ordered, EDUCATION_ORDER_RULES, category)

        elif category == "realestate":
            violations += WorkflowQualityValidator._check_required(
                mods, REALESTATE_REQUIRED_MODULES, category)
            violations += WorkflowQualityValidator._check_order(
                ordered, REALESTATE_ORDER_RULES, category)

        elif category in ("salon", "gym", "hotel", "travel", "supermarket"):
            violations += WorkflowQualityValidator._check_required(
                mods, BOOKING_REQUIRED_MODULES, category)
            violations += WorkflowQualityValidator._check_order(
                ordered, BOOKING_ORDER_RULES, category)

        elif category in ("ecommerce", "pharmacy"):
            # Same as restaurant but delivery is optional for pharmacy
            required = RESTAURANT_REQUIRED_MODULES.copy()
            if category == "pharmacy":
                required = [m for m in required
                            if m not in ("collect_address", "create_delivery")]
            violations += WorkflowQualityValidator._check_required(mods, required, category)
            violations += WorkflowQualityValidator._check_order(
                ordered, RESTAURANT_ORDER_RULES, category)

        else:
            # servicebusiness / unknown — only check that show_menu and notify_customer exist
            for mod in ("show_menu", "notify_customer"):
                if mod not in mods:
                    violations.append(_make_violation(
                        f"missing_module_{mod}",
                        "warning",
                        f"'{mod}' is recommended in all workflows."
                    ))
            warnings.append(f"No specific quality rules defined for category '{category}'. Basic checks applied.")

        # -----------------------------------------------------------------
        # Universal rules — apply to every category
        # -----------------------------------------------------------------
        # Leaf nodes should reach CONFIRMED, CANCELLED, or ERROR
        terminal_states = {"CONFIRMED", "CANCELLED", "ERROR"}
        for nid, node in nodes.items():
            has_outgoing = any(e.get("from_node") == nid for e in edges)
            if not has_outgoing:
                fsm_to = node.get("fsm_transition_to", "")
                expects_input = node.get("config", {}).get("expects_user_input", False)
                if fsm_to not in terminal_states and not expects_input:
                    violations.append(_make_violation(
                        f"dead_end_non_terminal_{nid}",
                        "error",
                        f"Node '{nid}' is a leaf but its fsm_transition_to='{fsm_to}' is not a "
                        f"terminal state. Add 'expects_user_input: true' or transition to "
                        f"CONFIRMED/CANCELLED/ERROR."
                    ))

        passed = all(v["severity"] != "error" for v in violations)

        logger.info(
            f"[QualityValidator] category='{category}' passed={passed} "
            f"violations={len(violations)} warnings={len(warnings)}"
        )

        return {
            "passed":       passed,
            "category":     category,
            "violations":   violations,
            "warnings":     warnings,
            "module_order": ordered,
        }

    # -----------------------------------------------------------------
    # Rule checkers
    # -----------------------------------------------------------------

    @staticmethod
    def _check_required(
        present_mods: set,
        required: List[str],
        category: str
    ) -> List[Dict[str, str]]:
        violations = []
        for mod in required:
            if mod not in present_mods:
                violations.append(_make_violation(
                    f"{category}_missing_{mod}",
                    "error",
                    f"Module '{mod}' is required for {category} workflows but is missing."
                ))
        return violations

    @staticmethod
    def _check_order(
        ordered: List[str],
        rules: List[tuple],
        category: str
    ) -> List[Dict[str, str]]:
        violations = []
        for earlier, later, rule_name in rules:
            idx_e = _idx(ordered, earlier)
            idx_l = _idx(ordered, later)
            if idx_e == -1 or idx_l == -1:
                continue  # Module missing — caught by _check_required
            if idx_e >= idx_l:
                violations.append(_make_violation(
                    f"{category}_{rule_name}_ordering_error",
                    "error",
                    f"'{earlier}' must execute before '{later}' in the happy path. "
                    f"Current order has '{earlier}' at position {idx_e} "
                    f"and '{later}' at position {idx_l}."
                ))
        return violations
