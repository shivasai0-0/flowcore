import datetime
from typing import List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import (
    AggregatedMetrics, Task, Employee, BusinessEvent, AuditEvent
)

class MetricsStore:
    @staticmethod
    async def update_daily_metrics(db: AsyncSession, business_id: str) -> AggregatedMetrics:
        today = datetime.datetime.utcnow().date()
        start_of_day = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
        end_of_day = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)

        # 1. Query metrics counts
        # Pending tasks
        pending_res = await db.execute(
            select(func.count(Task.id)).where(
                Task.business_id == business_id,
                Task.status.in_(["PENDING", "ACCEPTED", "IN_PROGRESS"])
            )
        )
        pending_count = pending_res.scalar() or 0

        # Completed tasks today
        completed_res = await db.execute(
            select(func.count(Task.id)).where(
                Task.business_id == business_id,
                Task.status == "COMPLETED",
                Task.completed_at >= start_of_day,
                Task.completed_at <= end_of_day
            )
        )
        completed_count = completed_res.scalar() or 0

        # Active employees
        emp_res = await db.execute(
            select(func.count(Employee.id)).where(
                Employee.business_id == business_id,
                Employee.status == "ACTIVE"
            )
        )
        active_emps = emp_res.scalar() or 0

        # Appointments count (bookings) today
        appt_res = await db.execute(
            select(func.count(BusinessEvent.id)).where(
                BusinessEvent.business_id == business_id,
                BusinessEvent.event_type.in_(["CUSTOMER_BOOKING", "APPOINTMENT_CREATED"]),
                BusinessEvent.created_at >= start_of_day,
                BusinessEvent.created_at <= end_of_day
            )
        )
        appointments_count = appt_res.scalar() or 0

        # Revenue (e.g. $50 per completed task)
        revenue = float(completed_count * 50.0)

        # 2. Get or create AggregatedMetrics record
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
                appointments_count=appointments_count,
                tasks_pending=pending_count,
                tasks_completed=completed_count,
                active_employees=active_emps,
                revenue=revenue,
                csat_score=5.0
            )
            db.add(metric)
        else:
            metric.appointments_count = appointments_count
            metric.tasks_pending = pending_count
            metric.tasks_completed = completed_count
            metric.active_employees = active_emps
            metric.revenue = revenue
            db.add(metric)

        await db.flush()
        return metric

    @staticmethod
    async def get_operations_timeline(db: AsyncSession, business_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        # Fetch business events
        be_query = select(BusinessEvent).where(
            BusinessEvent.business_id == business_id
        ).order_by(BusinessEvent.created_at.desc()).limit(limit)
        be_res = await db.execute(be_query)
        business_events = be_res.scalars().all()

        # Fetch audit events
        ae_query = select(AuditEvent).where(
            AuditEvent.business_id == business_id
        ).order_by(AuditEvent.timestamp.desc()).limit(limit)
        ae_res = await db.execute(ae_query)
        audit_events = ae_res.scalars().all()

        timeline = []

        # Format business events
        for be in business_events:
            timeline.append({
                "id": be.id,
                "type": "BUSINESS_EVENT",
                "event_type": be.event_type,
                "entity_type": be.entity_type,
                "entity_id": be.entity_id,
                "timestamp": be.created_at.isoformat(),
                "description": f"Event '{be.event_type}' emitted on {be.entity_type} {be.entity_id}",
                "payload": json.loads(be.payload_json) if be.payload_json else {}
            })

        # Format audit events
        for ae in audit_events:
            timeline.append({
                "id": ae.id,
                "type": "AUDIT_EVENT",
                "event_type": ae.action,
                "entity_type": ae.entity_type,
                "entity_id": ae.entity_id,
                "timestamp": ae.timestamp.isoformat(),
                "description": f"Action '{ae.action}' executed by Actor '{ae.actor_id or 'System'}' on {ae.entity_type}",
                "payload": {
                    "actor_id": ae.actor_id,
                    "old_value": json.loads(ae.old_value_json) if ae.old_value_json else {},
                    "new_value": json.loads(ae.new_value_json) if ae.new_value_json else {}
                }
            })

        # Sort timeline descending by timestamp string (or parse/sort, but ISO strings sort perfectly)
        timeline.sort(key=lambda x: x["timestamp"], reverse=True)
        return timeline[:limit]
