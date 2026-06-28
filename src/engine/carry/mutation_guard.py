from typing import Any, Dict
from src.schemas.carry_unit import CarryUnit

class MutationGuard:
    @staticmethod
    def validate_patch(carry_unit: CarryUnit, patch: Dict[str, Any]) -> None:
        """
        Validates that applying the patch to the carry_unit model does not violate policies.
        Uses typed properties on CarryUnit for validation rules.
        """
        for ns_name, ns_val in patch.items():
            if not isinstance(ns_val, dict):
                continue

            if ns_name == "session":
                # Compare fields using typed session attribute
                for k, v in ns_val.items():
                    current_val = getattr(carry_unit.session, k, None)
                    if current_val is not None and current_val != v:
                        raise ValueError(
                            f"CarryUnit Invariant Violation: session namespace is immutable. "
                            f"Cannot change {k} from '{current_val}' to '{v}'."
                        )

            elif ns_name == "payment":
                for k, v in ns_val.items():
                    if k == "status":
                        if carry_unit.payment.status == "SUCCESS" and v != "SUCCESS":
                            raise ValueError("CarryUnit Invariant Violation: payment status is locked after SUCCESS.")
