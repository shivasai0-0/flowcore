from typing import Any
from src.engine.carry.path_resolver import resolve_path

class CarryUnitResolver:
    @staticmethod
    def get_field(carry_unit: Any, path: str) -> Any:
        """Resolves field value from a CarryUnit instance using path resolver."""
        return resolve_path(carry_unit, path)
