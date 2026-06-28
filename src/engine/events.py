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
            record = EventStoreRecord(
                session_id=session_id,
                event_type=event_type,
                payload_json=json.dumps(payload),
                emitted_at=datetime.utcnow()
            )
            db_session.add(record)
            await db_session.flush()
            logger.info(f"Orchestration Event Emitted: type='{event_type}' session_id='{session_id}' payload={payload}")
        except Exception as e:
            logger.error(f"Failed to emit event type='{event_type}' for session_id='{session_id}': {str(e)}")
