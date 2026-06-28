import datetime
from typing import Optional, List
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import (
    Employee, EmployeeAvailability, EmployeeCalendarAvailability,
    CustomerOwnership, Task
)

class AssignmentEngine:
    @staticmethod
    async def assign_task_to_employee(
        db: AsyncSession,
        business_id: str,
        department_id: Optional[str] = None,
        specialization: Optional[str] = None,
        due_time: Optional[datetime.datetime] = None,
        customer_phone: Optional[str] = None
    ) -> Optional[Employee]:
        if not due_time:
            due_time = datetime.datetime.utcnow()

        # 1. Retrieve active employees in the business
        query = select(Employee).where(
            Employee.business_id == business_id,
            Employee.status == "ACTIVE"
        )
        if department_id:
            query = query.where(Employee.department_id == department_id)
        if specialization and specialization.lower() != "general":
            query = query.where(Employee.specialization == specialization)

        res = await db.execute(query)
        candidates = res.scalars().all()

        if not candidates:
            # If no matches with specialization, fallback to general employees in the department/business
            query = select(Employee).where(
                Employee.business_id == business_id,
                Employee.status == "ACTIVE"
            )
            if department_id:
                query = query.where(Employee.department_id == department_id)
            res = await db.execute(query)
            candidates = res.scalars().all()

        if not candidates:
            return None

        due_date = due_time.date()
        start_of_day = datetime.datetime(due_date.year, due_date.month, due_date.day, 0, 0, 0)
        end_of_day = datetime.datetime(due_date.year, due_date.month, due_date.day, 23, 59, 59)
        due_time_str = due_time.strftime("%H:%M")
        weekday = due_time.strftime("%A")

        available_candidates = []
        candidate_workloads = {}

        for emp in candidates:
            # A. Calendar availability check (overrides first)
            override_query = select(EmployeeCalendarAvailability).where(
                EmployeeCalendarAvailability.employee_id == emp.id,
                EmployeeCalendarAvailability.date >= start_of_day,
                EmployeeCalendarAvailability.date <= end_of_day
            )
            override_res = await db.execute(override_query)
            override = override_res.scalar_one_or_none()

            is_available = False
            if override is not None:
                if override.is_available:
                    # Check times if specified
                    if override.start_time and override.end_time:
                        if override.start_time <= due_time_str <= override.end_time:
                            is_available = True
                    else:
                        is_available = True
                else:
                    is_available = False
            else:
                # Fallback to standard weekday availability
                std_query = select(EmployeeAvailability).where(
                    EmployeeAvailability.employee_id == emp.id,
                    EmployeeAvailability.day_of_week == weekday
                )
                std_res = await db.execute(std_query)
                std_avail = std_res.scalar_one_or_none()

                if std_avail is not None:
                    if std_avail.start_time <= due_time_str <= std_avail.end_time:
                        is_available = True
                else:
                    # If there are no weekday availability constraints defined in DB at all,
                    # assume available by default.
                    all_std_res = await db.execute(
                        select(func.count(EmployeeAvailability.id)).where(EmployeeAvailability.employee_id == emp.id)
                    )
                    has_any_rules = all_std_res.scalar() or 0
                    if has_any_rules == 0:
                        is_available = True

            if not is_available:
                continue

            # B. Capacity Check
            # Count active tasks assigned to employee
            task_count_query = select(func.count(Task.id)).where(
                Task.assigned_employee_id == emp.id,
                Task.status.in_(["PENDING", "ACCEPTED", "IN_PROGRESS"])
            )
            task_count_res = await db.execute(task_count_query)
            active_tasks = task_count_res.scalar() or 0

            if active_tasks >= emp.capacity:
                continue

            available_candidates.append(emp)
            candidate_workloads[emp.id] = active_tasks

        if not available_candidates:
            return None

        # C. Customer Ownership Check
        if customer_phone:
            owner_query = select(CustomerOwnership).where(
                CustomerOwnership.business_id == business_id,
                CustomerOwnership.customer_phone == customer_phone
            )
            owner_res = await db.execute(owner_query)
            ownership = owner_res.scalar_one_or_none()
            if ownership:
                # Check if the owned employee is in the available candidates list
                owned_emp = next((e for e in available_candidates if e.id == ownership.assigned_employee_id), None)
                if owned_emp:
                    return owned_emp

        # D. Workload Check (Select candidate with lowest workload)
        best_candidate_id = min(candidate_workloads, key=candidate_workloads.get)
        best_emp = next(e for e in available_candidates if e.id == best_candidate_id)
        return best_emp
