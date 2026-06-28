from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class RetryConfig(BaseModel):
    max_retries: int = 3
    backoff_strategy: str = "exponential"  # linear, exponential
    idempotency_key_fields: List[str] = Field(default_factory=list)

class ModuleContract(BaseModel):
    module_name: str
    display_name: str
    version: str = "1.0.0"
    domain: str = "*"
    requires: Dict[str, str] = Field(
        default_factory=dict, 
        description="Keys mapped to expected types, e.g., {'order.total': 'float'}"
    )
    produces: Dict[str, str] = Field(
        default_factory=dict, 
        description="Keys mapped to produced types, e.g., {'payment.url': 'str'}"
    )
    allowed_fsm_states: List[str] = Field(default_factory=list)
    side_effects: List[str] = Field(default_factory=list)
    is_idempotent: bool = True
    expects_user_input: bool = False
    retry_config: RetryConfig = Field(default_factory=RetryConfig)
