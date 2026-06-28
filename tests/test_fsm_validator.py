import pytest
from src.engine.compiler.static_validator import StaticValidator
from src.schemas.graph import WorkflowGraph, WorkflowNode, WorkflowEdge, EdgeCondition

@pytest.mark.unit
def test_validator_legal_shared_semantic_state():
    """
    Verifies that multiple nodes can share or operate inside the same FSM semantic state
    (e.g., node_order and node_ask_address all operating inside CHECKOUT)
    without forcing FSM transition table duplication.
    """
    # Define a valid graph with shared states matching current module contracts:
    # calculate_total: allowed in CART, transitions to CART_REVIEW
    # create_order: allowed in CART_REVIEW, transitions to CHECKOUT
    # collect_address: allowed in CHECKOUT, transitions to ADDRESS
    # create_payment: allowed in ADDRESS, transitions to PAYMENT
    graph_data = {
        "business_id": "biz_test_fsm_123",
        "version_number": 1,
        "entry_node_id": "node_menu",
        "nodes": {
            "node_menu": {
                "id": "node_menu",
                "module_name": "show_menu",
                "fsm_transition_to": "MENU"
            },
            "node_cart": {
                "id": "node_cart",
                "module_name": "collect_cart",
                "fsm_transition_to": "CART"
            },
            "node_total": {
                "id": "node_total",
                "module_name": "calculate_total",
                "fsm_transition_to": "CART_REVIEW"
            },
            "node_order": {
                "id": "node_order",
                "module_name": "create_order",
                "fsm_transition_to": "CHECKOUT"
            },
            # Multiple nodes sharing CHECKOUT state
            "node_ask_address": {
                "id": "node_ask_address",
                "module_name": "send_message",
                "fsm_transition_to": None
            },
            "node_address": {
                "id": "node_address",
                "module_name": "collect_address",
                "fsm_transition_to": "ADDRESS"
            },
            "node_payment": {
                "id": "node_payment",
                "module_name": "create_payment",
                "fsm_transition_to": "PAYMENT"
            },
            "node_confirm": {
                "id": "node_confirm",
                "module_name": "confirm_payment",
                "fsm_transition_to": "CONFIRMED"
            }
        },
        "edges": [
            {"from_node": "node_menu", "to_node": "node_cart"},
            {"from_node": "node_cart", "to_node": "node_total"},
            {"from_node": "node_total", "to_node": "node_order"},
            {"from_node": "node_order", "to_node": "node_ask_address"},
            {"from_node": "node_ask_address", "to_node": "node_address"},
            {"from_node": "node_address", "to_node": "node_payment"},
            {"from_node": "node_payment", "to_node": "node_confirm"}
        ],
        "fsm_transition_table": {
            "START": {"MENU": "show_menu"},
            "MENU": {"CART": "collect_cart"},
            "CART": {"CART_REVIEW": "calculate_total"},
            "CART_REVIEW": {"CHECKOUT": "create_order"},
            "CHECKOUT": {"ADDRESS": "collect_address"},
            "ADDRESS": {"PAYMENT": "create_payment"},
            "PAYMENT": {"CONFIRMED": "confirm_payment"}
        }
    }
    
    graph = WorkflowGraph.model_validate(graph_data)
    is_valid, errors, _, _, _, fsm_check, _ = StaticValidator.validate(graph)
    assert is_valid is True, f"Validation failed with errors: {errors}"
    assert fsm_check is True

@pytest.mark.unit
def test_validator_invalid_transition():
    """
    Verifies that a transition not configured in the FSM transition table is rejected.
    Here, node_cart attempts to transition directly from MENU to CHECKOUT.
    """
    graph_data = {
        "business_id": "biz_test_fsm_123",
        "version_number": 1,
        "entry_node_id": "node_menu",
        "nodes": {
            "node_menu": {
                "id": "node_menu",
                "module_name": "show_menu",
                "fsm_transition_to": "MENU"
            },
            "node_cart": {
                "id": "node_cart",
                "module_name": "collect_cart",
                "fsm_transition_to": "CHECKOUT"  # Illegal transition! MENU -> CHECKOUT is not in transition table.
            }
        },
        "edges": [
            {"from_node": "node_menu", "to_node": "node_cart"}
        ],
        "fsm_transition_table": {
            "START": {"MENU": "show_menu"},
            "MENU": {"CART": "collect_cart"},
            "CART": {"CHECKOUT": "calculate_total"}
        }
    }
    
    graph = WorkflowGraph.model_validate(graph_data)
    is_valid, errors, _, _, _, fsm_check, _ = StaticValidator.validate(graph)
    assert is_valid is False
    assert fsm_check is False
    assert any("no transition defined" in err or "Illegal transition" in err for err in errors)

@pytest.mark.unit
def test_validator_terminal_state_rejection():
    """
    Verifies that transitioning from a terminal state to any other state is rejected.
    """
    graph_data = {
        "business_id": "biz_test_fsm_123",
        "version_number": 1,
        "entry_node_id": "node_menu",
        "nodes": {
            "node_menu": {
                "id": "node_menu",
                "module_name": "show_menu",
                "fsm_transition_to": "CONFIRMED"  # Transitions to terminal state CONFIRMED
            },
            "node_cart": {
                "id": "node_cart",
                "module_name": "collect_cart",
                "fsm_transition_to": "CART"  # Illegal transition from terminal state CONFIRMED to CART!
            }
        },
        "edges": [
            {"from_node": "node_menu", "to_node": "node_cart"}
        ],
        "fsm_transition_table": {
            "START": {"CONFIRMED": "show_menu"},
            "CONFIRMED": {"CART": "collect_cart"}
        }
    }
    
    graph = WorkflowGraph.model_validate(graph_data)
    is_valid, errors, _, _, _, fsm_check, _ = StaticValidator.validate(graph)
    assert is_valid is False
    assert fsm_check is False
    assert any("attempts transition from terminal state" in err for err in errors)

@pytest.mark.unit
def test_validator_unreachable_fsm_state():
    """
    Verifies that FSM transition tables containing unreachable states are rejected.
    """
    graph_data = {
        "business_id": "biz_test_fsm_123",
        "version_number": 1,
        "entry_node_id": "node_menu",
        "nodes": {
            "node_menu": {
                "id": "node_menu",
                "module_name": "show_menu",
                "fsm_transition_to": "MENU"
            }
        },
        "edges": [],
        "fsm_transition_table": {
            "START": {"MENU": "show_menu"},
            # ABANDONED is completely unreachable from START
            "ABANDONED": {"CART": "collect_cart"}
        }
    }
    
    graph = WorkflowGraph.model_validate(graph_data)
    is_valid, errors, _, _, _, fsm_check, _ = StaticValidator.validate(graph)
    assert is_valid is False
    assert fsm_check is False
    assert any("Unreachable states in FSM transition table" in err for err in errors)

@pytest.mark.unit
def test_validator_unregistered_fsm_state_in_node():
    """
    Verifies that a node attempting to transition to a completely unregistered FSM state fails validation.
    """
    graph_data = {
        "business_id": "biz_test_fsm_123",
        "version_number": 1,
        "entry_node_id": "node_menu",
        "nodes": {
            "node_menu": {
                "id": "node_menu",
                "module_name": "show_menu",
                "fsm_transition_to": "SUPER_UNKNOWN_STATE"  # State does not exist anywhere!
            }
        },
        "edges": [],
        "fsm_transition_table": {
            "START": {"MENU": "show_menu"}
        }
    }
    
    graph = WorkflowGraph.model_validate(graph_data)
    is_valid, errors, _, _, _, fsm_check, _ = StaticValidator.validate(graph)
    assert is_valid is False
    assert fsm_check is False
    assert any("transitions to unregistered FSM state" in err for err in errors)
