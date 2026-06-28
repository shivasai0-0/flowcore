from typing import Dict, List, Type
from src.modules.base import BaseModule

class ModuleRegistry:
    _registry: Dict[str, BaseModule] = {}

    @classmethod
    def register(cls, module_class: Type[BaseModule]) -> None:
        instance = module_class()
        cls._registry[instance.contract.module_name] = instance

    @classmethod
    def get(cls, name: str) -> BaseModule:
        module = cls._registry.get(name)
        if not module:
            raise KeyError(f"Module '{name}' is not registered in the Module Registry.")
        return module

    @classmethod
    def exists(cls, name: str) -> bool:
        return name in cls._registry

    @classmethod
    def list_all(cls) -> List[BaseModule]:
        return list(cls._registry.values())
