from src.engine.events.event_models import WorkflowEvent
from src.engine.events.event_bus import event_bus
import json
import logging
from datetime import datetime
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("flowcore.events")

class EventDispatcher:
    @staticmethod
    async def emit(
        db_session: AsyncSession,
        session_id: str,
        event_type: str,
        payload: Dict[str, Any]
    ) -> None:
        """
        Emits an internal orchestration event by persisting it to the database event_store table.
        This enables external system integrations (like N8N, webhooks, WhatsApp, logistics, payments).
        """
        from src.models import EventStoreRecord
        
        try:
            from src.engine.events.event_models import WorkflowEvent
            from src.engine.events.event_bus import event_bus
            
            # Construct WorkflowEvent
            event = WorkflowEvent(
                session_id=session_id,
                event_type=event_type,
                payload=payload
            )
            await event_bus.publish(db_session, event)
            logger.info(f"Orchestration Event Emitted: type='{event_type}' session_id='{session_id}' payload={payload}")
        except Exception as e:
            logger.error(f"Failed to emit event type='{event_type}' for session_id='{session_id}': {str(e)}")

__all__ = ["WorkflowEvent", "event_bus", "EventDispatcher"]
