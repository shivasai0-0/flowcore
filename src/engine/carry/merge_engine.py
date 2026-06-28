from typing import Any, Dict
from src.schemas.carry_unit import CarryUnit
from src.engine.carry.mutation_guard import MutationGuard

class CarryUnitMergeEngine:
    @staticmethod
    def merge_patch(carry_unit: CarryUnit, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Monotonically merges a dictionary patch into the CarryUnit model while enforcing invariants.
        Operates on typed validations and returns the merged dictionary ready for Pydantic instantiation.
        """
        # 1. Enforce validation guards using typed properties
        MutationGuard.validate_patch(carry_unit, patch)

        # 2. Extract dict and perform merge
        current_data = carry_unit.model_dump()
        
        merged = {}
        for k, v in current_data.items():
            if isinstance(v, dict):
                merged[k] = dict(v)
            elif isinstance(v, list):
                merged[k] = list(v)
            else:
                merged[k] = v

        merged["version"] = current_data.get("version", 1) + 1

        for ns_name, ns_val in patch.items():
            if not isinstance(ns_val, dict):
                continue
            if ns_name not in merged:
                continue

            if isinstance(merged[ns_name], dict):
                merged[ns_name] = dict(merged[ns_name])
            current_ns = merged[ns_name]

            if ns_name == "order":
                for k, v in ns_val.items():
                    if k == "items":
                        if "items" not in current_ns:
                            current_ns["items"] = []
                        else:
                            current_ns["items"] = list(current_ns["items"])
                        current_ns["items"].extend(v)
                    elif k == "total":
                        current_ns["total"] = float(v)
                    else:
                        current_ns[k] = v

            elif ns_name == "workflow":
                for k, v in ns_val.items():
                    if k == "execution_trace":
                        if "execution_trace" not in current_ns:
                            current_ns["execution_trace"] = []
                        else:
                            current_ns["execution_trace"] = list(current_ns["execution_trace"])
                        current_ns["execution_trace"].extend(v)
                    else:
                        current_ns[k] = v
            else:
                for k, v in ns_val.items():
                    if isinstance(v, dict) and isinstance(current_ns.get(k), dict):
                        current_ns[k] = dict(current_ns[k])
                        current_ns[k].update(v)
                    else:
                        current_ns[k] = v

        return merged
