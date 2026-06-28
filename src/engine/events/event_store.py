import json
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import EventStoreRecord
from src.engine.events.event_models import WorkflowEvent

class EventStore:
    @staticmethod
    async def save_event(db_session: AsyncSession, event: WorkflowEvent) -> None:
        # Extract from payload
        biz_id = event.payload.get("business_id")
        wf_id = event.payload.get("workflow_version_id")
        cust_id = event.payload.get("customer_id") or event.payload.get("customer_phone")
        
        record = EventStoreRecord(
            id=event.id,
            session_id=event.session_id or "event_trigger",
            business_id=biz_id,
            workflow_version_id=wf_id,
            customer_id=cust_id,
            event_type=event.event_type,
            payload_json=json.dumps(event.payload),
            emitted_at=event.emitted_at
        )
        db_session.add(record)
