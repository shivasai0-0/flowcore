import asyncio
import logging
import json
from datetime import datetime
from typing import List, Callable, Awaitable
from sqlalchemy.ext.asyncio import AsyncSession
from src.engine.events.event_models import WorkflowEvent
from src.engine.events.event_store import EventStore
from src.engine.events.subscribers import ALL_SUBSCRIBERS
from src.schemas.carry_unit import CarryUnit

logger = logging.getLogger("flowcore.event_bus")

class EventBus:
    def __init__(self):
        self.subscribers: List[Callable[[WorkflowEvent], Awaitable[None]]] = list(ALL_SUBSCRIBERS)

    def register(self, subscriber: Callable[[WorkflowEvent], Awaitable[None]]) -> None:
        self.subscribers.append(subscriber)

    async def publish(self, db_session: AsyncSession, event: WorkflowEvent) -> None:
        from src.database import db_session_context
        db_session_context.set(db_session)

        # 0. Validate event payload against EventRegistry
        from src.engine.registries.event_registry import EventRegistry
        EventRegistry.validate_payload(event.event_type, event.payload)

        # 1. Persist in Event Store
        await EventStore.save_event(db_session, event)
        logger.info(f"Emitted event: {event.event_type} for session {event.session_id}")

        # 2. Trigger active workflows portfolio subscribed to this event
        business_id = event.payload.get("business_id")
        customer_phone = event.payload.get("customer_phone") or event.payload.get("customer_id")
        
        # Resolve from session if missing
        if (not business_id or not customer_phone) and event.session_id and event.session_id != "event_trigger":
            from src.models import Session as SessionModel
            from sqlalchemy import select
            sess_res = await db_session.execute(select(SessionModel).where(SessionModel.id == event.session_id))
            session_rec = sess_res.scalar_one_or_none()
            if session_rec:
                if not business_id:
                    business_id = session_rec.business_id
                if not customer_phone:
                    customer_phone = session_rec.customer_phone
                logger.warning(f"Resolved from session: business_id={business_id}, customer_phone={customer_phone}")
            else:
                logger.warning(f"Could not find session {event.session_id} to resolve business/customer info.")

        logger.warning(f"EventBus publish: event_type={event.event_type}, business_id={business_id}, customer_phone={customer_phone}")

        # Persist in BusinessEvent and ConversationLog
        from src.models import BusinessEvent, ConversationLog
        if business_id:
            biz_event = BusinessEvent(
                business_id=business_id,
                event_type=event.event_type,
                entity_type=event.payload.get("entity_type", "session"),
                entity_id=event.payload.get("entity_id") or event.session_id or "unknown",
                payload_json=json.dumps(event.payload),
                created_at=datetime.utcnow()
            )
            db_session.add(biz_event)

            if event.event_type == "CUSTOMER_MESSAGE":
                direction = event.payload.get("direction", "INBOUND")
                sender = event.payload.get("sender") or customer_phone or "unknown"
                recipient = event.payload.get("recipient") or "SYSTEM"
                msg_text = event.payload.get("message_text") or ""
                msg_type = event.payload.get("message_type", "text")

                conv_log = ConversationLog(
                    business_id=business_id,
                    session_id=event.session_id if event.session_id != "event_trigger" else None,
                    direction=direction,
                    sender=sender,
                    recipient=recipient,
                    message_text=msg_text,
                    message_type=msg_type,
                    created_at=datetime.utcnow()
                )
                db_session.add(conv_log)
            
            await db_session.flush()

        if business_id and customer_phone:
            from src.models import WorkflowVersion, Session as SessionModel
            from sqlalchemy import select
            
            # Find active workflows for the business
            wv_query = select(WorkflowVersion).where(
                WorkflowVersion.business_id == business_id,
                WorkflowVersion.status == "ACTIVE"
            )
            wv_res = await db_session.execute(wv_query)
            active_versions = wv_res.scalars().all()
            logger.warning(f"Found {len(active_versions)} active workflows for business {business_id}")
            
            for wv in active_versions:
                try:
                    graph_dict = json.loads(wv.graph_json)
                except Exception:
                    continue
                
                trigger_event = graph_dict.get("trigger_event")
                trigger_events = graph_dict.get("trigger_events", [])
                if not isinstance(trigger_events, list):
                    trigger_events = [trigger_events]
                
                logger.warning(f"Checking workflow {wv.id}: trigger_event={trigger_event}, trigger_events={trigger_events}")
                
                if trigger_event == event.event_type or event.event_type in trigger_events:
                    logger.warning(f"Trigger matched event type: {event.event_type}. Spawning/unarchiving session...")
                    # Check for existing unarchived session for this customer, business and workflow version
                    sess_query = select(SessionModel).where(
                        SessionModel.business_id == business_id,
                        SessionModel.customer_phone == customer_phone,
                        SessionModel.workflow_version_id == wv.id,
                        SessionModel.is_archived == False
                    )
                    sess_res = await db_session.execute(sess_query)
                    existing_session = sess_res.scalar_one_or_none()
                    
                    if existing_session:
                        session_record = existing_session
                        carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))
                    else:
                        # Spawn new session
                        # Append the last 6 characters of the workflow version ID to avoid collisions
                        # when multiple workflows are active/triggered for the same customer in the same minute.
                        wv_suffix = wv.id.replace("-", "")[-6:]
                        session_id = f"sess_{datetime.utcnow().strftime('%Y%m%d%H%M')}_{customer_phone.replace('+', '')[-6:]}_{wv_suffix}"
                        carry_unit = CarryUnit(
                            session={
                                "session_id": session_id,
                                "customer_phone": customer_phone,
                                "business_id": business_id,
                                "workflow_version_id": wv.id,
                                "session_started_at": datetime.utcnow().isoformat()
                            }
                        )
                        session_record = SessionModel(
                            id=session_id,
                            business_id=business_id,
                            customer_phone=customer_phone,
                            fsm_state="START",
                            current_node_id=None,
                            carry_unit_json=json.dumps(carry_unit.model_dump()),
                            workflow_version_id=wv.id,
                            is_archived=False,
                            locked_until=None,
                            last_active_at=datetime.utcnow()
                        )
                        db_session.add(session_record)
                        await db_session.flush()
                    
                    # Merge event payload into the carry unit
                    try:
                        carry_unit = carry_unit.merge_patch(event.payload)
                        session_record.carry_unit_json = json.dumps(carry_unit.model_dump())
                        db_session.add(session_record)
                        await db_session.flush()
                    except Exception as e:
                        logger.error(f"Failed to merge event payload into carry unit: {str(e)}")
                    
                    # Run traversal dispatch step
                    from src.engine.traversal import GraphTraversalEngine
                    try:
                        await GraphTraversalEngine.dispatch_step(
                            db_session=db_session,
                            session_record=session_record,
                            user_input=event.event_type
                        )
                    except Exception as e:
                        logger.exception(f"Failed to dispatch step for triggered session {session_record.id}: {str(e)}")

        # 3. Invoke subscribers concurrently using asyncio.gather
        tasks = []
        for sub in self.subscribers:
            tasks.append(sub(event))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res, sub in zip(results, self.subscribers):
                if isinstance(res, Exception):
                    logger.error(f"Subscriber {sub.__name__} raised exception: {str(res)}", exc_info=res)

# Singleton instance
event_bus = EventBus()
