import json
import uuid
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from src.database import get_db
from src.models import Business, Employee, EmployeeAvailability
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/workers", tags=["Workers"])

class WorkerCreateRequest(BaseModel):
    business_id: Optional[str] = None
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None
    role: str = Field(..., min_length=1)
    specialization: Optional[str] = "General"
    availability: Optional[Dict[str, List[str]]] = None
    capacity: Optional[int] = 15

class WorkerUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    specialization: Optional[str] = None
    availability: Optional[Dict[str, List[str]]] = None
    capacity: Optional[int] = None

@router.get("", response_model=ApiResponse)
async def list_workers(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            return ApiResponse(success=True, data=[])
        business_id = business.id

    query = select(Employee).where(Employee.business_id == business_id).order_by(Employee.name)
    res = await db.execute(query)
    workers = res.scalars().all()

    data = []
    for w in workers:
        # Fetch availability from EmployeeAvailability table
        avail_res = await db.execute(
            select(EmployeeAvailability).where(EmployeeAvailability.employee_id == w.id)
        )
        avail_records = avail_res.scalars().all()
        avail = {}
        for rec in avail_records:
            avail[rec.day_of_week] = [rec.start_time, rec.end_time]

        data.append({
            "id": w.id,
            "business_id": w.business_id,
            "name": w.name,
            "phone": w.phone,
            "role": w.role,
            "specialization": w.specialization,
            "availability": avail,
            "capacity": w.capacity,
            "created_at": w.created_at.isoformat()
        })

    return ApiResponse(success=True, data=data)

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_worker(payload: WorkerCreateRequest, db: AsyncSession = Depends(get_db)):
    business_id = payload.business_id
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No business registered.")
        business_id = business.id

    # If phone is not provided, generate a unique random one for compatibility with legacy tests
    phone = payload.phone or f"+1555{uuid.uuid4().hex[:10]}"

    w = Employee(
        business_id=business_id,
        name=payload.name,
        phone=phone,
        role=payload.role.lower(),
        specialization=payload.specialization or "General",
        capacity=payload.capacity or 15,
        status="ACTIVE",
        login_enabled=True
    )
    db.add(w)
    await db.flush()

    avail = payload.availability or {}
    for day, times in avail.items():
        if len(times) >= 2:
            ea = EmployeeAvailability(
                employee_id=w.id,
                day_of_week=day,
                start_time=times[0],
                end_time=times[1]
            )
            db.add(ea)

    await db.commit()
    await db.refresh(w)

    return ApiResponse(
        success=True,
        data={
            "id": w.id,
            "business_id": w.business_id,
            "name": w.name,
            "phone": w.phone,
            "role": w.role,
            "specialization": w.specialization,
            "availability": avail,
            "capacity": w.capacity,
            "created_at": w.created_at.isoformat()
        }
    )

@router.put("/{worker_id}", response_model=ApiResponse)
async def update_worker(worker_id: str, payload: WorkerUpdateRequest, db: AsyncSession = Depends(get_db)):
    query = select(Employee).where(Employee.id == worker_id)
    res = await db.execute(query)
    w = res.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found.")

    if payload.name is not None:
        w.name = payload.name
    if payload.role is not None:
        w.role = payload.role.lower()
    if payload.specialization is not None:
        w.specialization = payload.specialization
    if payload.capacity is not None:
        w.capacity = payload.capacity

    if payload.availability is not None:
        # Delete old availabilities and insert new ones
        await db.execute(delete(EmployeeAvailability).where(EmployeeAvailability.employee_id == worker_id))
        for day, times in payload.availability.items():
            if len(times) >= 2:
                ea = EmployeeAvailability(
                    employee_id=worker_id,
                    day_of_week=day,
                    start_time=times[0],
                    end_time=times[1]
                )
                db.add(ea)

    await db.commit()
    await db.refresh(w)

    # Fetch fresh availability
    avail_res = await db.execute(
        select(EmployeeAvailability).where(EmployeeAvailability.employee_id == w.id)
    )
    avail_records = avail_res.scalars().all()
    avail = {}
    for rec in avail_records:
        avail[rec.day_of_week] = [rec.start_time, rec.end_time]

    return ApiResponse(
        success=True,
        data={
            "id": w.id,
            "business_id": w.business_id,
            "name": w.name,
            "phone": w.phone,
            "role": w.role,
            "specialization": w.specialization,
            "availability": avail,
            "capacity": w.capacity,
            "created_at": w.created_at.isoformat()
        }
    )

@router.delete("/{worker_id}", response_model=ApiResponse)
async def delete_worker(worker_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Employee).where(Employee.id == worker_id)
    res = await db.execute(query)
    w = res.scalar_one_or_none()
    if not w:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found.")

    await db.delete(w)
    await db.commit()

    return ApiResponse(success=True, data={"id": worker_id, "deleted": True})
