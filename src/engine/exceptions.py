from typing import Optional

class FlowCoreRuntimeError(Exception):
    """
    Standardized exception class representing runtime failures, transition gating rejections,
    immutability errors, or semantic violations in the FlowCore kernel.
    """
    def __init__(
        self,
        error_code: str,
        message: str,
        session_id: str,
        node_id: Optional[str] = None,
        current_fsm_state: str = "START"
    ):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.session_id = session_id
        self.node_id = node_id
        self.current_fsm_state = current_fsm_state

class IllegalTransitionError(FlowCoreRuntimeError):
    """Raised when an illegal FSM state transition is requested."""
    def __init__(
        self,
        message: str,
        session_id: str,
        node_id: Optional[str] = None,
        current_fsm_state: str = "START"
    ):
        super().__init__(
            error_code="INVALID_TRANSITION",
            message=message,
            session_id=session_id,
            node_id=node_id,
            current_fsm_state=current_fsm_state
        )
