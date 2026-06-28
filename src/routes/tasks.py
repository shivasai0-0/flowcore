import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.database import get_db
from src.models import Business, Task, Worker
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

class TaskCreateRequest(BaseModel):
    business_id: Optional[str] = None
    session_id: Optional[str] = None
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    priority: Optional[str] = "MEDIUM"
    assigned_worker_id: Optional[str] = None
    due_time: Optional[datetime] = None

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    status: Optional[str] = None
    due_time: Optional[datetime] = None

@router.get("", response_model=ApiResponse)
async def list_tasks(
    business_id: Optional[str] = None,
    assigned_worker_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    from src.config import settings
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        business_id = settings.ACTIVE_DEV_WORKSPACE

    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            return ApiResponse(success=True, data=[])
        business_id = business.id

    query = select(Task).where(Task.business_id == business_id)
    if assigned_worker_id:
        query = query.where(Task.assigned_worker_id == assigned_worker_id)
    if status_filter:
        query = query.where(Task.status == status_filter.upper())
    
    query = query.order_by(desc(Task.created_at))
    res = await db.execute(query)
    tasks = res.scalars().all()

    # Load worker details for presentation
    worker_ids = [t.assigned_worker_id for t in tasks if t.assigned_worker_id]
    workers_dict = {}
    if worker_ids:
        w_query = select(Worker).where(Worker.id.in_(worker_ids))
        w_res = await db.execute(w_query)
        for w in w_res.scalars().all():
            workers_dict[w.id] = w.name

    data = []
    for t in tasks:
        data.append({
            "id": t.id,
            "business_id": t.business_id,
            "session_id": t.session_id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "assigned_worker_id": t.assigned_worker_id,
            "assigned_worker_name": workers_dict.get(t.assigned_worker_id, "Unassigned") if t.assigned_worker_id else "Unassigned",
            "due_time": t.due_time.isoformat() if t.due_time else None,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None
        })

    return ApiResponse(success=True, data=data)

@router.post("", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreateRequest, db: AsyncSession = Depends(get_db)):
    from src.config import settings
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        business_id = settings.ACTIVE_DEV_WORKSPACE

    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No business registered.")
        business_id = business.id

    if payload.assigned_worker_id:
        w_query = select(Worker).where(Worker.id == payload.assigned_worker_id)
        w_res = await db.execute(w_query)
        if not w_res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned worker not found.")

    t = Task(
        business_id=business_id,
        session_id=payload.session_id,
        title=payload.title,
        description=payload.description or "",
        priority=payload.priority.upper() if payload.priority else "MEDIUM",
        assigned_worker_id=payload.assigned_worker_id,
        due_time=payload.due_time,
        status="PENDING"
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)

    return ApiResponse(
        success=True,
        data={
            "id": t.id,
            "business_id": t.business_id,
            "session_id": t.session_id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "assigned_worker_id": t.assigned_worker_id,
            "due_time": t.due_time.isoformat() if t.due_time else None,
            "status": t.status,
            "created_at": t.created_at.isoformat()
        }
    )

@router.put("/{task_id}", response_model=ApiResponse)
async def update_task(task_id: str, payload: TaskUpdateRequest, db: AsyncSession = Depends(get_db)):
    query = select(Task).where(Task.id == task_id)
    res = await db.execute(query)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    if payload.title is not None:
        t.title = payload.title
    if payload.description is not None:
        t.description = payload.description
    if payload.priority is not None:
        t.priority = payload.priority.upper()
    if payload.due_time is not None:
        t.due_time = payload.due_time

    if payload.assigned_worker_id is not None:
        if payload.assigned_worker_id != "":
            w_query = select(Worker).where(Worker.id == payload.assigned_worker_id)
            w_res = await db.execute(w_query)
            if not w_res.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found.")
            t.assigned_worker_id = payload.assigned_worker_id
        else:
            t.assigned_worker_id = None

    if payload.status is not None:
        old_status = t.status
        new_status = payload.status.upper()
        t.status = new_status
        if new_status == "COMPLETED" and old_status != "COMPLETED":
            t.completed_at = datetime.utcnow()
        elif new_status != "COMPLETED":
            t.completed_at = None

    await db.commit()
    await db.refresh(t)

    return ApiResponse(
        success=True,
        data={
            "id": t.id,
            "business_id": t.business_id,
            "session_id": t.session_id,
            "title": t.title,
            "description": t.description,
            "priority": t.priority,
            "assigned_worker_id": t.assigned_worker_id,
            "due_time": t.due_time.isoformat() if t.due_time else None,
            "status": t.status,
            "created_at": t.created_at.isoformat(),
            "completed_at": t.completed_at.isoformat() if t.completed_at else None
        }
    )

@router.delete("/{task_id}", response_model=ApiResponse)
async def delete_task(task_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Task).where(Task.id == task_id)
    res = await db.execute(query)
    t = res.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

    await db.delete(t)
    await db.commit()

    return ApiResponse(success=True, data={"id": task_id, "deleted": True})
