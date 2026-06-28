import logging
from src.engine.events.event_models import WorkflowEvent
from src.services.event_handlers import (
    handle_customer_message,
    handle_customer_booking,
    handle_customer_order,
    handle_approval_granted,
    handle_sla_tracking
)

logger = logging.getLogger("flowcore.events")

async def notify_customer_on_payment(event: WorkflowEvent) -> None:
    if event.event_type == "PAYMENT_CONFIRMED":
        logger.info(f"[Subscriber: Notification] Customer notified for payment of session {event.session_id}")

async def update_analytics_on_order(event: WorkflowEvent) -> None:
    if event.event_type == "ORDER_CREATED":
        logger.info(f"[Subscriber: Analytics] Order metrics updated for session {event.session_id}")

ALL_SUBSCRIBERS = [
    notify_customer_on_payment,
    update_analytics_on_order,
    handle_customer_message,
    handle_customer_booking,
    handle_customer_order,
    handle_approval_granted,
    handle_sla_tracking
]
