import datetime
import logging
from typing import Optional, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import (
    ReportSchedule, Task, Employee, AggregatedMetrics,
    EmployeePerformance
)
from src.services.notification_center import NotificationCenter

logger = logging.getLogger("flowcore.reporting_engine")

class ReportingEngine:
    @staticmethod
    async def compile_and_dispatch_due_reports(db: AsyncSession) -> int:
        now = datetime.datetime.utcnow()
        # Find schedules where next_run_at is in the past
        query = select(ReportSchedule).where(ReportSchedule.next_run_at <= now)
        res = await db.execute(query)
        schedules = res.scalars().all()

        count = 0
        for sched in schedules:
            try:
                # Compile report based on frequency and role
                report_text = await ReportingEngine._compile_report(db, sched)
                if not report_text:
                    continue

                # Resolve recipient employee ID
                recipient_emp_id = sched.recipient_id
                if not recipient_emp_id and sched.recipient_role in ["OWNER", "MANAGER"]:
                    # Find the owner/manager employee of this business
                    owner_query = select(Employee).where(
                        Employee.business_id == sched.business_id,
                        Employee.role == sched.recipient_role.lower(),
                        Employee.status == "ACTIVE"
                    ).limit(1)
                    owner_res = await db.execute(owner_query)
                    owner = owner_res.scalar_one_or_none()
                    if owner:
                        recipient_emp_id = owner.id

                # Dispatch report
                await NotificationCenter.send_notification(
                    db=db,
                    business_id=sched.business_id,
                    employee_id=recipient_emp_id,
                    source="REPORT_GENERATED",
                    message=report_text
                )

                # Update next run time
                if sched.frequency.upper() == "DAILY":
                    sched.next_run_at += datetime.timedelta(days=1)
                elif sched.frequency.upper() == "WEEKLY":
                    sched.next_run_at += datetime.timedelta(weeks=1)
                else:  # MONTHLY
                    sched.next_run_at += datetime.timedelta(days=30)

                db.add(sched)
                count += 1
            except Exception as e:
                logger.error(f"Error compiling report schedule {sched.id}: {str(e)}")

        if count > 0:
            await db.commit()

        return count

    @staticmethod
    async def _compile_report(db: AsyncSession, sched: ReportSchedule) -> Optional[str]:
        # Define timeframe
        now = datetime.datetime.utcnow()
        if sched.frequency.upper() == "DAILY":
            timeframe_start = now - datetime.timedelta(days=1)
            timeframe_name = "Daily"
        elif sched.frequency.upper() == "WEEKLY":
            timeframe_start = now - datetime.timedelta(weeks=1)
            timeframe_name = "Weekly"
        else:
            timeframe_start = now - datetime.timedelta(days=30)
            timeframe_name = "Monthly"

        # Owner / Manager report
        if sched.recipient_role.upper() in ["OWNER", "MANAGER"]:
            # Query active tasks count
            pending_query = select(func.count(Task.id)).where(
                Task.business_id == sched.business_id,
                Task.status.in_(["PENDING", "ACCEPTED", "IN_PROGRESS"])
            )
            pending_res = await db.execute(pending_query)
            pending_count = pending_res.scalar() or 0

            # Query completed tasks count in timeframe
            completed_query = select(func.count(Task.id)).where(
                Task.business_id == sched.business_id,
                Task.status == "COMPLETED",
                Task.completed_at >= timeframe_start
            )
            completed_res = await db.execute(completed_query)
            completed_count = completed_res.scalar() or 0

            # Query active employees
            emp_query = select(func.count(Employee.id)).where(
                Employee.business_id == sched.business_id,
                Employee.status == "ACTIVE"
            )
            emp_res = await db.execute(emp_query)
            active_emps = emp_res.scalar() or 0

            # Est revenue based on completed tasks
            revenue = completed_count * 50.0

            return (
                f"=== {timeframe_name} Business Report for {sched.recipient_role} ===\n"
                f"- Active Employees: {active_emps}\n"
                f"- Tasks Pending: {pending_count}\n"
                f"- Tasks Completed in timeframe: {completed_count}\n"
                f"- Estimated Revenue: ${revenue:.2f}\n"
                f"- Average CSAT Score: 5.0"
            )

        # Employee report
        elif sched.recipient_id:
            emp_query = select(Employee).where(Employee.id == sched.recipient_id)
            emp_res = await db.execute(emp_query)
            emp = emp_res.scalar_one_or_none()

            if not emp:
                return None

            # Tasks completed
            completed_query = select(func.count(Task.id)).where(
                Task.assigned_employee_id == emp.id,
                Task.status == "COMPLETED",
                Task.completed_at >= timeframe_start
            )
            completed_res = await db.execute(completed_query)
            completed_count = completed_res.scalar() or 0

            # Tasks pending
            pending_query = select(func.count(Task.id)).where(
                Task.assigned_employee_id == emp.id,
                Task.status.in_(["PENDING", "ACCEPTED", "IN_PROGRESS"])
            )
            pending_res = await db.execute(pending_query)
            pending_count = pending_res.scalar() or 0

            # Performance rating
            perf_query = select(EmployeePerformance).where(EmployeePerformance.employee_id == emp.id)
            perf_res = await db.execute(perf_query)
            perf = perf_res.scalar_one_or_none()
            rating = perf.rating if perf else 5.0

            return (
                f"=== {timeframe_name} Performance Report for {emp.name} ===\n"
                f"- Tasks Assigned (Pending): {pending_count}\n"
                f"- Tasks Completed in timeframe: {completed_count}\n"
                f"- Current Rating: {rating:.1f}/5.0"
            )

        return None
