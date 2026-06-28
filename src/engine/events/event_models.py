from datetime import datetime
from typing import Any, Dict
from pydantic import BaseModel, Field
import uuid

class WorkflowEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    emitted_at: datetime = Field(default_factory=datetime.utcnow)
