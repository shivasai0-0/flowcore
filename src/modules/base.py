from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from src.schemas.carry_unit import CarryUnit
from src.schemas.contract import ModuleContract

class ModuleOutput(BaseModel):
    outputs: Dict[str, Any]
    messages: List[str] = []
    ui: Optional[Dict[str, Any]] = None
    side_effects: List[Dict[str, Any]] = []

def get_carry_unit_field(carry_unit: CarryUnit, path: str) -> Any:
    """Helper to traverse namespaced attributes in the CarryUnit."""
    parts = path.split(".")
    obj = carry_unit
    for p in parts:
        if hasattr(obj, p):
            obj = getattr(obj, p)
        elif isinstance(obj, dict) and p in obj:
            obj = obj[p]
        else:
            return None
    return obj

def check_type(val: Any, type_str: str) -> bool:
    """Validates that a value matches the declared string type."""
    if val is None:
        return False
    if type_str == "str":
        return isinstance(val, str)
    if type_str == "float":
        return isinstance(val, (int, float))
    if type_str == "int":
        return isinstance(val, int)
    if type_str == "bool":
        return isinstance(val, bool)
    if type_str == "list":
        return isinstance(val, list)
    if type_str == "dict":
        return isinstance(val, dict)
    return True

class BaseModule(ABC):
    contract: ModuleContract

    def validate_inputs(self, carry_unit: CarryUnit) -> None:
        """Enforces that all fields declared in 'requires' exist in carry_unit with matching types."""
        for field, expected_type in self.contract.requires.items():
            val = get_carry_unit_field(carry_unit, field)
            if val is None:
                raise ValueError(
                    f"Contract Violation: Module '{self.contract.module_name}' requires field '{field}' which is missing in CarryUnit."
                )
            if not check_type(val, expected_type):
                raise TypeError(
                    f"Contract Type Violation: Module '{self.contract.module_name}' requires field '{field}' to be '{expected_type}', got '{type(val).__name__}'."
                )

    def validate_outputs(self, outputs: Dict[str, Any]) -> None:
        """Enforces that all outputs produced match the types declared in the contract's 'produces'."""
        for field, expected_type in self.contract.produces.items():
            # Check if output contains namespaced key directly or nested
            parts = field.split(".")
            val = outputs
            for p in parts:
                if isinstance(val, dict) and p in val:
                    val = val[p]
                else:
                    val = None
                    break
            
            if val is None:
                raise ValueError(
                    f"Contract Violation: Module '{self.contract.module_name}' failed to produce field '{field}'."
                )
            if not check_type(val, expected_type):
                raise TypeError(
                    f"Contract Type Violation: Module '{self.contract.module_name}' produced field '{field}' of type '{type(val).__name__}', expected '{expected_type}'."
                )

    @abstractmethod
    async def execute(self, carry_unit: CarryUnit, config: Dict[str, Any], user_input: str) -> ModuleOutput:
        """
        Executes module logic.
        Must return a ModuleOutput (outputs dict and messages list).
        """
        pass
