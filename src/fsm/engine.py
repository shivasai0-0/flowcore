from typing import Dict

class InvalidTransitionError(Exception):
    """Raised when an illegal FSM state transition is requested."""
    pass

IllegalTransitionError = InvalidTransitionError

class FSMEngine:
    # Default Restaurant Domain FSM transition table:
    # state_from -> { state_to: triggering_module_name }
    DEFAULT_TRANSITION_TABLE: Dict[str, Dict[str, str]] = {
        "START": {
            "MENU": "show_menu"
        },
        "MENU": {
            "BROWSING": "collect_cart",
            "CANCELLED": "collect_cart" # Or mock module
        },
        "BROWSING": {
            "CART": "collect_cart"
        },
        "CART": {
            "CHECKOUT": "calculate_total",
            "MENU": "show_menu",
            "CANCELLED": "collect_cart"
        },
        "CHECKOUT": {
            "PAYMENT": "create_payment",
            "CART": "collect_cart"
        },
        "PAYMENT": {
            "CONFIRMED": "confirm_payment",
            "CHECKOUT": "calculate_total"
        },
        "CONFIRMED": {
            "START": "show_menu"
        },
        "CANCELLED": {
            "START": "show_menu"
        },
        "ERROR": {
            "START": "show_menu"
        }
    }

    TERMINAL_STATES = {"CONFIRMED", "CANCELLED"}

    @classmethod
    def transition(
        cls,
        current_state: str,
        target_state: str,
        module_name: str,
        custom_transition_table: Dict[str, Dict[str, str]] = None
    ) -> str:
        """
        Transitions the state machine from current_state to target_state.
        Validates the transition against the transition table.
        - Only permitted transitions are allowed.
        - Terminal states cannot transition further (must raise exception).
        """
        if current_state == target_state:
            return current_state

        # Enforce terminal state lock: terminal states cannot transition
        if current_state in cls.TERMINAL_STATES:
            raise InvalidTransitionError(
                f"FSM Engine Violation: Cannot transition from terminal state '{current_state}' to '{target_state}'."
            )

        if not custom_transition_table:
            raise ValueError(
                "FSM Engine Violation: Workflow FSM transitions require a workflow-scoped transition table. "
                "Global fallback FSM table is deprecated."
            )
        table = custom_transition_table

        transitions = table.get(current_state, {})
        allowed_trigger = transitions.get(target_state)

        if not allowed_trigger:
            raise InvalidTransitionError(
                f"FSM Engine Violation: No transition defined from '{current_state}' to '{target_state}'."
            )

        # Trigger module name must match
        if allowed_trigger != module_name:
            raise InvalidTransitionError(
                f"FSM Engine Violation: Illegal transition from '{current_state}' to '{target_state}' via module '{module_name}'. "
                f"Required triggering module is '{allowed_trigger}'."
            )

        return target_state
