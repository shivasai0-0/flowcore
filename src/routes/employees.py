import json
import uuid
import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.database import get_db
from src.models import Employee, Business, Department, AuditEvent, EmployeePerformance
from src.schemas.envelope import ApiResponse
from src.services.auth import (
    PermissionChecker, get_current_user_context, hash_password, generate_salt
)

router = APIRouter(prefix="/api/v1/employees", tags=["Employees"])

class EmployeeCreateRequest(BaseModel):
    business_id: Optional[str] = None
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    role: str = Field("worker", description="owner, manager, worker, viewer")
    department_id: Optional[str] = None
    skills: Optional[str] = None
    specialization: Optional[str] = "General"
    capacity: Optional[int] = 15

class EmployeeUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[str] = None
    skills: Optional[str] = None
    specialization: Optional[str] = None
    capacity: Optional[int] = None
    status: Optional[str] = None

@router.get("", response_model=ApiResponse)
async def list_employees(
    business_id: Optional[str] = None, 
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(get_current_user_context)
):
    # Enforce active business scope
    active_biz_id = user_context.get("business_id")
    if not active_biz_id:
        raise HTTPException(status_code=400, detail="Active business not set.")

    query = select(Employee).where(Employee.business_id == active_biz_id).order_by(Employee.name)
    res = await db.execute(query)
    employees = res.scalars().all()

    data = []
    for emp in employees:
        data.append({
            "id": emp.id,
            "business_id": emp.business_id,
            "department_id": emp.department_id,
            "name": emp.name,
            "phone": emp.phone,
            "role": emp.role,
            "status": emp.status,
            "login_enabled": emp.login_enabled,
            "specialization": emp.specialization,
            "capacity": emp.capacity,
            "created_at": emp.created_at.isoformat()
        })

    return ApiResponse(success=True, data=data)

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreateRequest, 
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")
    
    # Check if number already registered
    exist_query = select(Employee).where(Employee.phone == payload.phone)
    exist_res = await db.execute(exist_query)
    if exist_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee with phone number '{payload.phone}' already registered."
        )

    # Check if department exists if provided
    if payload.department_id:
        dept_query = select(Department).where(Department.id == payload.department_id)
        dept_res = await db.execute(dept_query)
        if not dept_res.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Department not found.")

    salt = generate_salt()
    temp_pass = f"temp_{uuid.uuid4().hex[:6]}"
    hashed = hash_password(temp_pass, salt)

    emp = Employee(
        business_id=active_biz_id,
        department_id=payload.department_id,
        name=payload.name,
        phone=payload.phone,
        role=payload.role.lower(),
        status="ACTIVE",
        login_enabled=True,
        password_hash=hashed,
        salt=salt,
        force_password_change=True,
        specialization=payload.specialization or "General",
        capacity=payload.capacity or 15,
        created_by=actor_id
    )
    db.add(emp)
    await db.flush()

    # Create dummy performance record
    perf = EmployeePerformance(
        employee_id=emp.id,
        rating=5.0,
        tasks_completed=0
    )
    db.add(perf)
    await db.flush()

    # Log audit event
    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="EMPLOYEE_CREATED",
        entity_type="employee",
        entity_id=emp.id,
        new_value_json=json.dumps({"name": emp.name, "phone": emp.phone, "role": emp.role})
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(
        success=True,
        data={
            "employee": {
                "id": emp.id,
                "business_id": emp.business_id,
                "department_id": emp.department_id,
                "name": emp.name,
                "phone": emp.phone,
                "role": emp.role,
                "status": emp.status,
                "specialization": emp.specialization,
                "capacity": emp.capacity
            },
            "temporary_password": temp_pass
        }
    )

@router.put("/{employee_id}", response_model=ApiResponse)
async def update_employee(
    employee_id: str,
    payload: EmployeeUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")

    query = select(Employee).where(Employee.id == employee_id, Employee.business_id == active_biz_id)
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    old_vals = {"name": emp.name, "role": emp.role, "status": emp.status, "department_id": emp.department_id}

    if payload.name is not None:
        emp.name = payload.name
    if payload.role is not None:
        emp.role = payload.role.lower()
    if payload.department_id is not None:
        if payload.department_id:
            dept_query = select(Department).where(Department.id == payload.department_id)
            dept_res = await db.execute(dept_query)
            if not dept_res.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Department not found.")
        emp.department_id = payload.department_id
    if payload.specialization is not None:
        emp.specialization = payload.specialization
    if payload.capacity is not None:
        emp.capacity = payload.capacity
    if payload.status is not None:
        emp.status = payload.status

    db.add(emp)

    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="EMPLOYEE_UPDATED",
        entity_type="employee",
        entity_id=emp.id,
        old_value_json=json.dumps(old_vals),
        new_value_json=json.dumps({"name": emp.name, "role": emp.role, "status": emp.status, "department_id": emp.department_id})
    )
    db.add(audit)
    await db.commit()
    await db.refresh(emp)

    return ApiResponse(
        success=True,
        data={
            "id": emp.id,
            "name": emp.name,
            "role": emp.role,
            "status": emp.status,
            "department_id": emp.department_id,
            "specialization": emp.specialization,
            "capacity": emp.capacity
        }
    )

@router.delete("/{employee_id}", response_model=ApiResponse)
async def delete_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")

    query = select(Employee).where(Employee.id == employee_id, Employee.business_id == active_biz_id)
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    old_name = emp.name
    await db.delete(emp)

    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="EMPLOYEE_DELETED",
        entity_type="employee",
        entity_id=employee_id,
        old_value_json=json.dumps({"name": old_name})
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(success=True, data={"id": employee_id, "deleted": True})

# Credentials Actions
@router.post("/{employee_id}/credentials/reset-password", response_model=ApiResponse)
async def reset_password(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")

    query = select(Employee).where(Employee.id == employee_id, Employee.business_id == active_biz_id)
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    salt = generate_salt()
    temp_pass = f"temp_{uuid.uuid4().hex[:6]}"
    hashed = hash_password(temp_pass, salt)

    emp.salt = salt
    emp.password_hash = hashed
    emp.force_password_change = True
    db.add(emp)

    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="CREDENTIALS_PASSWORD_RESET",
        entity_type="employee",
        entity_id=employee_id
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(success=True, data={"id": employee_id, "temporary_password": temp_pass})

@router.post("/{employee_id}/credentials/disable-login", response_model=ApiResponse)
async def disable_login(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")

    query = select(Employee).where(Employee.id == employee_id, Employee.business_id == active_biz_id)
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp.login_enabled = False
    db.add(emp)

    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="CREDENTIALS_LOGIN_DISABLED",
        entity_type="employee",
        entity_id=employee_id
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(success=True, data={"id": employee_id, "login_enabled": False})

@router.post("/{employee_id}/credentials/enable-login", response_model=ApiResponse)
async def enable_login(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")

    query = select(Employee).where(Employee.id == employee_id, Employee.business_id == active_biz_id)
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp.login_enabled = True
    db.add(emp)

    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="CREDENTIALS_LOGIN_ENABLED",
        entity_type="employee",
        entity_id=employee_id
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(success=True, data={"id": employee_id, "login_enabled": True})

@router.post("/{employee_id}/credentials/suspend", response_model=ApiResponse)
async def suspend_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")

    query = select(Employee).where(Employee.id == employee_id, Employee.business_id == active_biz_id)
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp.status = "SUSPENDED"
    emp.login_enabled = False
    db.add(emp)

    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="CREDENTIALS_EMPLOYEE_SUSPENDED",
        entity_type="employee",
        entity_id=employee_id
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(success=True, data={"id": employee_id, "status": "SUSPENDED", "login_enabled": False})

@router.post("/{employee_id}/credentials/force-password-change", response_model=ApiResponse)
async def force_password_change(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    user_context: dict = Depends(PermissionChecker(["owner", "manager"]))
):
    active_biz_id = user_context.get("business_id")
    actor_id = user_context.get("employee_id")

    query = select(Employee).where(Employee.id == employee_id, Employee.business_id == active_biz_id)
    res = await db.execute(query)
    emp = res.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found.")

    emp.force_password_change = True
    db.add(emp)

    audit = AuditEvent(
        business_id=active_biz_id,
        actor_id=actor_id,
        action="CREDENTIALS_FORCE_PASSWORD_CHANGE",
        entity_type="employee",
        entity_id=employee_id
    )
    db.add(audit)
    await db.commit()

    return ApiResponse(success=True, data={"id": employee_id, "force_password_change": True})
