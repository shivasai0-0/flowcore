from typing import Any, Dict

def check_session_policy(current_ns: Dict[str, Any], patch_ns: Dict[str, Any]) -> None:
    # Session is immutable. Compare keys
    for k, v in patch_ns.items():
        if k in current_ns and current_ns[k] != v:
            raise ValueError(
                f"CarryUnit Invariant Violation: session namespace is immutable. "
                f"Cannot change {k} from '{current_ns[k]}' to '{v}'."
            )

def check_payment_policy(current_ns: Dict[str, Any], patch_ns: Dict[str, Any]) -> None:
    for k, v in patch_ns.items():
        if k == "status":
            if current_ns.get("status") == "SUCCESS" and v != "SUCCESS":
                raise ValueError("CarryUnit Invariant Violation: payment status is locked after SUCCESS.")
