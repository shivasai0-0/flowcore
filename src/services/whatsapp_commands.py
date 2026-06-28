import json
import datetime
from typing import Optional, List
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import (
    Employee, Task, Approval, EmployeeCalendarAvailability,
    EmployeeShift, ConversationLog
)

class WhatsAppCommandRouter:
    @staticmethod
    async def handle_incoming_text(
        db: AsyncSession,
        from_phone: str,
        text_message: str
    ) -> str:
        from src.config import settings
        from src.services.dev_workspace import apply_dev_workspace_branding

        # 1. Retrieve the employee by phone
        emp_query = select(Employee).where(
            Employee.phone == from_phone,
            Employee.status == "ACTIVE"
        )
        if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
            emp_query = emp_query.where(Employee.business_id == settings.ACTIVE_DEV_WORKSPACE)

        emp_res = await db.execute(emp_query)
        employee = emp_res.scalar_one_or_none()

        if not employee:
            return "Error: Phone number not registered as an active employee."

        # Log conversation inbound message
        log_rec = ConversationLog(
            business_id=employee.business_id,
            direction="INBOUND",
            sender=from_phone,
            recipient="SYSTEM",
            message_text=text_message,
            message_type="text"
        )
        db.add(log_rec)
        await db.flush()

        raw_response = await WhatsAppCommandRouter._handle_incoming_text_raw(db, employee, text_message)
        return await apply_dev_workspace_branding(db, employee.business_id, raw_response)

    @staticmethod
    async def _handle_incoming_text_raw(
        db: AsyncSession,
        employee: Employee,
        text_message: str
    ) -> str:
        # Parse command
        tokens = text_message.strip().split()
        if not tokens:
            return "Error: Empty message. Please send a valid command (e.g., TASKS, TODAY, START <task_id>, COMPLETE <task_id>)."

        cmd = tokens[0].upper()
        args = tokens[1:]

        try:
            if cmd == "START":
                if not args:
                    return "Error: Please specify task ID. Usage: START <task_id>"
                task_id = args[0]
                task_query = select(Task).where(
                    Task.id == task_id,
                    Task.business_id == employee.business_id
                )
                task_res = await db.execute(task_query)
                task = task_res.scalar_one_or_none()

                if not task:
                    return f"Error: Task with ID '{task_id}' not found."

                task.status = "IN_PROGRESS"
                db.add(task)
                await db.commit()
                return f"Task '{task.title}' is now IN_PROGRESS."

            elif cmd == "COMPLETE":
                if not args:
                    return "Error: Please specify task ID. Usage: COMPLETE <task_id>"
                task_id = args[0]
                task_query = select(Task).where(
                    Task.id == task_id,
                    Task.business_id == employee.business_id
                )
                task_res = await db.execute(task_query)
                task = task_res.scalar_one_or_none()

                if not task:
                    return f"Error: Task with ID '{task_id}' not found."

                # High-Risk command checks (e.g. critical priority, financial keywords)
                is_high_risk = False
                if task.priority == "CRITICAL":
                    is_high_risk = True
                else:
                    high_risk_keywords = ["financial", "payment", "refund", "close", "audit", "billing"]
                    if any(kw in task.title.lower() or kw in task.description.lower() for kw in high_risk_keywords):
                        is_high_risk = True

                if is_high_risk:
                    # Create Approval record instead of completing
                    approval = Approval(
                        business_id=employee.business_id,
                        session_id=task.session_id or "whatsapp_session",
                        node_id="whatsapp_command",
                        request_type="whatsapp_command_execution",
                        details_json=json.dumps({
                            "task_id": task.id,
                            "task_title": task.title,
                            "employee_id": employee.id,
                            "employee_name": employee.name,
                            "action": "COMPLETE"
                        }),
                        status="PENDING"
                    )
                    db.add(approval)
                    await db.commit()
                    return f"Completion of critical task '{task.title}' requires manager approval. Request submitted."
                else:
                    task.status = "COMPLETED"
                    task.completed_at = datetime.datetime.utcnow()
                    db.add(task)
                    await db.commit()
                    return f"Task '{task.title}' completed successfully."

            elif cmd == "TODAY":
                today = datetime.date.today()
                start_of_day = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
                end_of_day = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)

                tasks_query = select(Task).where(
                    Task.assigned_employee_id == employee.id,
                    Task.due_time >= start_of_day,
                    Task.due_time <= end_of_day,
                    Task.status != "COMPLETED",
                    Task.status != "CANCELLED"
                ).order_by(Task.due_time)

                tasks_res = await db.execute(tasks_query)
                tasks = tasks_res.scalars().all()

                if not tasks:
                    return "You have no pending tasks scheduled for today."

                lines = ["Your tasks for today:"]
                for t in tasks:
                    due = t.due_time.strftime("%H:%M") if t.due_time else "No time"
                    lines.append(f"- [{t.status}] {t.title} (Due: {due}) | ID: {t.id}")
                return "\n".join(lines)

            elif cmd == "TASKS":
                tasks_query = select(Task).where(
                    Task.assigned_employee_id == employee.id,
                    Task.status.in_(["PENDING", "ACCEPTED", "IN_PROGRESS"])
                ).order_by(Task.due_time)

                tasks_res = await db.execute(tasks_query)
                tasks = tasks_res.scalars().all()

                if not tasks:
                    return "You have no active pending tasks."

                lines = ["Your active tasks:"]
                for t in tasks:
                    due = t.due_time.strftime("%Y-%m-%d %H:%M") if t.due_time else "No time"
                    lines.append(f"- [{t.status}] {t.title} (Due: {due}) | ID: {t.id}")
                return "\n".join(lines)

            elif cmd == "AVAILABLE":
                today = datetime.date.today()
                start_of_day = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
                end_of_day = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)

                await db.execute(
                    delete(EmployeeCalendarAvailability).where(
                        EmployeeCalendarAvailability.employee_id == employee.id,
                        EmployeeCalendarAvailability.date >= start_of_day,
                        EmployeeCalendarAvailability.date <= end_of_day
                    )
                )

                override = EmployeeCalendarAvailability(
                    employee_id=employee.id,
                    date=start_of_day,
                    is_available=True,
                    reason="WhatsApp Command Available"
                )
                db.add(override)
                await db.commit()
                return "You are now marked as AVAILABLE for today."

            elif cmd == "UNAVAILABLE":
                today = datetime.date.today()
                start_of_day = datetime.datetime(today.year, today.month, today.day, 0, 0, 0)
                end_of_day = datetime.datetime(today.year, today.month, today.day, 23, 59, 59)

                await db.execute(
                    delete(EmployeeCalendarAvailability).where(
                        EmployeeCalendarAvailability.employee_id == employee.id,
                        EmployeeCalendarAvailability.date >= start_of_day,
                        EmployeeCalendarAvailability.date <= end_of_day
                    )
                )

                override = EmployeeCalendarAvailability(
                    employee_id=employee.id,
                    date=start_of_day,
                    is_available=False,
                    reason="WhatsApp Command Unavailable"
                )
                db.add(override)
                await db.commit()
                return "You are now marked as UNAVAILABLE for today."

            elif cmd == "SHIFT":
                now = datetime.datetime.utcnow()
                shift_query = select(EmployeeShift).where(
                    EmployeeShift.employee_id == employee.id,
                    EmployeeShift.end_time >= now
                ).order_by(EmployeeShift.start_time).limit(1)

                shift_res = await db.execute(shift_query)
                shift = shift_res.scalar_one_or_none()

                if not shift:
                    return "You have no upcoming shifts scheduled."

                start_str = shift.start_time.strftime("%Y-%m-%d %H:%M")
                end_str = shift.end_time.strftime("%H:%M")
                return f"Your next scheduled shift: {start_str} to {end_str} (Status: {shift.status})."

            else:
                return f"Unknown command '{cmd}'. Available commands: TASKS, TODAY, START <task_id>, COMPLETE <task_id>, AVAILABLE, UNAVAILABLE, SHIFT."

        except Exception as e:
            await db.rollback()
            return f"Error executing command: {str(e)}"
