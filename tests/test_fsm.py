import pytest
from src.fsm.engine import FSMEngine, InvalidTransitionError

# Mock scoped workflow FSM transition table
TEST_TABLE = {
    "START": {
        "MENU": "show_menu"
    },
    "MENU": {
        "BROWSING": "collect_cart",
        "CANCELLED": "collect_cart"
    },
    "BROWSING": {
        "CART": "collect_cart"
    },
    "CONFIRMED": {
        "START": "show_menu"
    }
}

def test_fsm_legal_transitions():
    # START -> MENU via show_menu
    state = FSMEngine.transition("START", "MENU", "show_menu", TEST_TABLE)
    assert state == "MENU"

    # MENU -> BROWSING via collect_cart
    state = FSMEngine.transition("MENU", "BROWSING", "collect_cart", TEST_TABLE)
    assert state == "BROWSING"

def test_fsm_illegal_transition():
    # Trigger name mismatch
    with pytest.raises(InvalidTransitionError) as exc_info:
        FSMEngine.transition("START", "MENU", "collect_cart", TEST_TABLE)
    assert "Illegal transition" in str(exc_info.value)

    # Transition to undeclared state
    with pytest.raises(InvalidTransitionError) as exc_info:
        FSMEngine.transition("START", "BROWSING", "show_menu", TEST_TABLE)
    assert "No transition defined" in str(exc_info.value)

def test_fsm_terminal_state_lock():
    # Attempting to transition from CONFIRMED should fail
    with pytest.raises(InvalidTransitionError) as exc_info:
        FSMEngine.transition("CONFIRMED", "START", "show_menu", TEST_TABLE)
    assert "Cannot transition from terminal state" in str(exc_info.value)
