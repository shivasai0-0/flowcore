import json
import datetime
import logging
from typing import Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import src.database
from src.engine.events.event_models import WorkflowEvent
from src.models import (
    Task, Employee, CustomerOwnership, SLAConfig, SLATracking,
    AggregatedMetrics, Approval, Session as SessionModel, ConversationLog
)
from src.services.assignment_engine import AssignmentEngine
from src.services.notification_center import NotificationCenter

logger = logging.getLogger("flowcore.event_handlers")

@asynccontextmanager
async def db_context():
    from src.database import db_session_context
    db = db_session_context.get()
    if db is not None:
        yield db, False
    else:
        async with src.database.AsyncSessionLocal() as session:
            yield session, True

async def handle_customer_message(event: WorkflowEvent) -> None:
    """
    Subscribes to CUSTOMER_MESSAGE. Performs intent detection and emits subsequent lifecycle events.
    """
    if event.event_type != "CUSTOMER_MESSAGE":
        return

    payload = event.payload
    msg_text = payload.get("message_text", "").lower().strip()
    business_id = payload.get("business_id")
    customer_phone = payload.get("sender") or payload.get("customer_phone")
    session_id = event.session_id

    if not business_id or not customer_phone:
        return

    # Mock intent detection
    detected_event = None
    entity_type = "session"
    entity_id = session_id

    if any(keyword in msg_text for keyword in ["book", "appointment", "schedule"]):
        detected_event = "CUSTOMER_BOOKING"
        entity_type = "appointment"
    elif any(keyword in msg_text for keyword in ["order", "buy", "purchase"]):
        detected_event = "CUSTOMER_ORDER"
        entity_type = "order"
    elif any(keyword in msg_text for keyword in ["cancel", "stop"]):
        detected_event = "CUSTOMER_CANCELLATION"
    elif any(keyword in msg_text for keyword in ["reschedule", "change"]):
        detected_event = "CUSTOMER_RESCHEDULE"
    elif any(keyword in msg_text for keyword in ["escalate", "help", "manager"]):
        detected_event = "CUSTOMER_ESCALATION"

    if detected_event:
        # Publish the detected event to the event bus
        # To avoid circular imports, import event_bus here
        from src.engine.events.event_bus import event_bus
        async with db_context() as (db, should_commit):
            new_event = WorkflowEvent(
                session_id=session_id,
                event_type=detected_event,
                payload={
                    "business_id": business_id,
                    "customer_phone": customer_phone,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "message_text": msg_text
                }
            )
            await event_bus.publish(db, new_event)
            if should_commit:
                await db.commit()

async def handle_customer_booking(event: WorkflowEvent) -> None:
    """
    Subscribes to CUSTOMER_BOOKING and APPOINTMENT_CREATED.
    Creates tasks, runs capacity-based staffing assignment, and dispatches notification.
    """
    if event.event_type not in ["CUSTOMER_BOOKING", "APPOINTMENT_CREATED"]:
        return

    payload = event.payload
    business_id = payload.get("business_id")
    customer_phone = payload.get("customer_phone")
    session_id = event.session_id

    if not business_id:
        return

    async with db_context() as (db, should_commit):
        # 1. Run assignment engine
        assigned_emp = await AssignmentEngine.assign_task_to_employee(
            db=db,
            business_id=business_id,
            due_time=datetime.datetime.utcnow() + datetime.timedelta(hours=2),
            customer_phone=customer_phone
        )

        assigned_emp_id = assigned_emp.id if assigned_emp else None

        # 2. Create Task
        task = Task(
            business_id=business_id,
            session_id=session_id if session_id != "event_trigger" else None,
            title=f"Booking Appointment for {customer_phone or 'Customer'}",
            description=f"Automated booking fulfillment task. Incoming message: {payload.get('message_text', '')}",
            priority="MEDIUM",
            assigned_employee_id=assigned_emp_id,
            due_time=datetime.datetime.utcnow() + datetime.timedelta(hours=2),
            status="PENDING"
        )
        db.add(task)
        await db.flush()

        # 3. Create Customer Ownership mapping if employee is assigned and does not exist
        if assigned_emp_id and customer_phone:
            exist_query = select(CustomerOwnership).where(
                CustomerOwnership.business_id == business_id,
                CustomerOwnership.customer_phone == customer_phone
            )
            exist_res = await db.execute(exist_query)
            if not exist_res.scalar_one_or_none():
                ownership = CustomerOwnership(
                    business_id=business_id,
                    customer_phone=customer_phone,
                    assigned_employee_id=assigned_emp_id
                )
                db.add(ownership)

        # 4. Dispatch notification
        msg = f"New task assigned: Booking Appointment for {customer_phone}. Task ID: {task.id}"
        await NotificationCenter.send_notification(
            db=db,
            business_id=business_id,
            employee_id=assigned_emp_id,
            source="TASK_ASSIGNED",
            message=msg
        )

        if should_commit:
            await db.commit()

async def handle_customer_order(event: WorkflowEvent) -> None:
    """
    Subscribes to CUSTOMER_ORDER and ORDER_PLACED.
    Fulfills delivery, assigns employee, and updates metrics store.
    """
    if event.event_type not in ["CUSTOMER_ORDER", "ORDER_PLACED"]:
        return

    payload = event.payload
    business_id = payload.get("business_id")
    customer_phone = payload.get("customer_phone")
    session_id = event.session_id

    if not business_id:
        return

    async with db_context() as (db, should_commit):
        # 1. Assign employee
        assigned_emp = await AssignmentEngine.assign_task_to_employee(
            db=db,
            business_id=business_id,
            customer_phone=customer_phone
        )
        assigned_emp_id = assigned_emp.id if assigned_emp else None

        # 2. Create fulfillment task
        task = Task(
            business_id=business_id,
            session_id=session_id if session_id != "event_trigger" else None,
            title=f"Order Fulfillment for {customer_phone or 'Customer'}",
            description="Process order delivery and payments.",
            priority="HIGH",
            assigned_employee_id=assigned_emp_id,
            due_time=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            status="PENDING"
        )
        db.add(task)
        await db.flush()

        # 3. Update Metrics Store incrementally
        today = datetime.datetime.utcnow().date()
        start_of_day = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)

        metric_query = select(AggregatedMetrics).where(
            AggregatedMetrics.business_id == business_id,
            AggregatedMetrics.date == start_of_day
        )
        metric_res = await db.execute(metric_query)
        metric = metric_res.scalar_one_or_none()

        if not metric:
            metric = AggregatedMetrics(
                business_id=business_id,
                date=start_of_day,
                appointments_count=0,
                tasks_pending=1,
                tasks_completed=0,
                active_employees=1,
                revenue=50.0,  # Mock transaction revenue
                csat_score=5.0
            )
            db.add(metric)
        else:
            metric.tasks_pending += 1
            metric.revenue += 50.0
            db.add(metric)

        # 4. Dispatch notification
        msg = f"New order fulfillment task assigned. Task ID: {task.id}"
        await NotificationCenter.send_notification(
            db=db,
            business_id=business_id,
            employee_id=assigned_emp_id,
            source="TASK_ASSIGNED",
            message=msg
        )

        if should_commit:
            await db.commit()

async def handle_approval_granted(event: WorkflowEvent) -> None:
    """
    Subscribes to APPROVAL_GRANTED or similar event.
    Resumes session traversal, releases locks, and notifies employee.
    """
    if event.event_type not in ["APPROVAL_GRANTED", "APPROVAL_APPROVE"]:
        return

    payload = event.payload
    approval_id = payload.get("approval_id")
    business_id = payload.get("business_id")

    if not approval_id:
        return

    async with db_context() as (db, should_commit):
        # Find approval
        app_query = select(Approval).where(Approval.id == approval_id)
        app_res = await db.execute(app_query)
        approval = app_res.scalar_one_or_none()

        if not approval or approval.status not in ["PENDING", "APPROVED"]:
            return

        was_pending = (approval.status == "PENDING")

        if was_pending:
            # Update approval status
            approval.status = "APPROVED"
            approval.resolved_at = datetime.datetime.utcnow()
            approval.action_taken = "Approve"
            approval.resolved_by = payload.get("resolved_by", "Manager")
            db.add(approval)

        # If it was a whatsapp command execution approval, complete the task
        if approval.request_type == "whatsapp_command_execution":
            details = json.loads(approval.details_json)
            task_id = details.get("task_id")
            emp_id = details.get("employee_id")

            task_query = select(Task).where(Task.id == task_id)
            task_res = await db.execute(task_query)
            task = task_res.scalar_one_or_none()

            if task and task.status != "COMPLETED":
                task.status = "COMPLETED"
                task.completed_at = datetime.datetime.utcnow()
                db.add(task)

                # Send success notification
                await NotificationCenter.send_notification(
                    db=db,
                    business_id=business_id or approval.business_id,
                    employee_id=emp_id,
                    source="APPROVAL_GRANTED",
                    message=f"Your request to complete task '{task.title}' has been APPROVED by manager."
                )
        elif was_pending:
            # Resume traversal on session
            sess_query = select(SessionModel).where(SessionModel.id == approval.session_id)
            sess_res = await db.execute(sess_query)
            session_rec = sess_res.scalar_one_or_none()

            if session_rec:
                # Release locked_until
                session_rec.locked_until = None
                db.add(session_rec)
                await db.flush()

                # Dispatch step traversal
                from src.engine.traversal import GraphTraversalEngine
                try:
                    await GraphTraversalEngine.dispatch_step(
                        db_session=db,
                        session_record=session_rec,
                        user_input="APPROVED"
                    )
                except Exception as e:
                    logger.exception(f"Failed to resume session traversal: {str(e)}")

        if should_commit:
            await db.commit()

async def handle_sla_tracking(event: WorkflowEvent) -> None:
    """
    Subscribes to events that require SLA tracking (CUSTOMER_BOOKING, CUSTOMER_ORDER, etc.).
    Creates an SLATracking record.
    """
    trigger_events = ["CUSTOMER_BOOKING", "CUSTOMER_ORDER", "APPOINTMENT_CREATED", "ORDER_PLACED"]
    if event.event_type not in trigger_events:
        return

    payload = event.payload
    business_id = payload.get("business_id")
    entity_id = payload.get("entity_id") or event.session_id
    entity_type = payload.get("entity_type", "task")

    if not business_id:
        return

    async with db_context() as (db, should_commit):
        # Fetch SLA Config for this event type
        cfg_query = select(SLAConfig).where(
            SLAConfig.business_id == business_id,
            SLAConfig.trigger_event == event.event_type
        )
        cfg_res = await db.execute(cfg_query)
        cfg = cfg_res.scalar_one_or_none()

        breach_threshold = 30
        if cfg:
            breach_threshold = cfg.breach_threshold_minutes

        now = datetime.datetime.utcnow()
        target_time = now + datetime.timedelta(minutes=breach_threshold)

        sla = SLATracking(
            business_id=business_id,
            entity_type=entity_type,
            entity_id=entity_id,
            sla_status="SLA_MET",
            target_time=target_time,
            created_at=now
        )
        db.add(sla)
        if should_commit:
            await db.commit()
