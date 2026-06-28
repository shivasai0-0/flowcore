import uuid
import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.database import get_db
from src.models import Business, EventStoreRecord
from src.engine.events import EventDispatcher
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])

class ReportGenerateRequest(BaseModel):
    business_id: Optional[str] = None
    report_type: str = Field(..., description="e.g. Doctor Appointment Schedule, Daily Orders Report, Today's Appointments, Member Attendance")

class ReportSendRequest(BaseModel):
    recipient_phone: str = Field(..., min_length=1)
    report_content: str = Field(..., min_length=1)

BUSINESS_REPORT_TYPES = {
    "restaurant": ["Daily Orders Report"],
    "ecommerce": ["Daily Orders Report"],
    "hospital": ["Doctor Appointment Schedule"],
    "clinic": ["Doctor Appointment Schedule"],
    "salon": ["Today's Appointments"],
    "beauty": ["Today's Appointments"],
    "gym": ["Member Attendance"],
    "athletics": ["Member Attendance"]
}

@router.get("/history", response_model=ApiResponse)
async def get_report_history(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            return ApiResponse(success=True, data=[])
        business_id = business.id
    else:
        biz_query = select(Business).where(Business.id == business_id)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()

    if not business:
        return ApiResponse(success=True, data=[])

    query = select(EventStoreRecord).where(
        EventStoreRecord.business_id == business_id,
        EventStoreRecord.event_type == "REPORT_GENERATED"
    ).order_by(desc(EventStoreRecord.emitted_at))
    res = await db.execute(query)
    records = res.scalars().all()

    biz_type = (business.business_type or "restaurant").lower()
    allowed_types = BUSINESS_REPORT_TYPES.get(biz_type, ["Daily Summary Report"])

    data = []
    for r in records:
        try:
            payload = json.loads(r.payload_json)
        except Exception:
            payload = {}
        
        rep_type = payload.get("report_type")
        if rep_type in allowed_types:
            data.append({
                "id": r.id,
                "business_id": r.business_id,
                "report_type": rep_type,
                "content": payload.get("content"),
                "generated_at": r.emitted_at.isoformat()
            })

    return ApiResponse(success=True, data=data)

@router.post("/generate", response_model=ApiResponse)
async def generate_report(payload: ReportGenerateRequest, db: AsyncSession = Depends(get_db)):
    business_id = payload.business_id
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No business registered.")
        business_id = business.id
    else:
        biz_query = select(Business).where(Business.id == business_id)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")

    report_id = f"rpt_{uuid.uuid4().hex[:8]}"
    report_type = payload.report_type

    # Validate report type against business type
    biz_type = (business.business_type or "restaurant").lower()
    allowed_types = BUSINESS_REPORT_TYPES.get(biz_type, ["Daily Summary Report"])
    if report_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Report type '{report_type}' is not allowed for business type '{biz_type}'."
        )

    # Generate content based on type
    if "doctor" in report_type.lower() or "appointment" in report_type.lower():
        content = (
            f"Good Morning Doctor\n\n"
            f"Appointments for today:\n"
            f"10:00 John Doe\n"
            f"10:30 Alex Carter\n"
            f"11:00 Sarah Connor\n"
            f"11:30 Michael Scott"
        )
    elif "orders" in report_type.lower() or "daily" in report_type.lower():
        content = (
            f"Daily Orders Report Summary:\n"
            f"Total Orders: 38\n"
            f"Gross Revenue: $789.20\n"
            f"Average Order: $20.77\n"
            f"Status: COMPLETED"
        )
    elif "attendance" in report_type.lower() or "member" in report_type.lower():
        content = (
            f"Member Attendance Report:\n"
            f"Total check-ins: 84\n"
            f"Peak hours: 06:00 - 09:00 (42 check-ins)\n"
            f"New Memberships: 3"
        )
    else:
        content = f"Summary Report for {report_type}:\nAll systems nominal.\nCompleted executions: 147"

    # Emit event to persist in EventStore
    await EventDispatcher.emit(
        db, "system", "REPORT_GENERATED",
        {"report_type": report_type, "content": content, "report_id": report_id, "business_id": business_id}
    )
    await db.commit()

    return ApiResponse(
        success=True,
        data={
            "id": report_id,
            "business_id": business_id,
            "report_type": report_type,
            "content": content,
            "generated_at": datetime.utcnow().isoformat()
        }
    )

@router.post("/send-whatsapp", response_model=ApiResponse)
async def send_whatsapp_report(
    payload: ReportSendRequest,
    x_flowcore_business_id: Optional[str] = Header(None, alias="X-FlowCore-Business-Id"),
    x_business_id: Optional[str] = Header(None, alias="X-Business-Id"),
    db: AsyncSession = Depends(get_db)
):
    # Retrieve business_id
    business_id = x_flowcore_business_id or x_business_id
    from src.config import settings
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        business_id = settings.ACTIVE_DEV_WORKSPACE
        
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if business:
            business_id = business.id

    report_content = payload.report_content
    if business_id:
        from src.services.dev_workspace import apply_dev_workspace_branding
        report_content = await apply_dev_workspace_branding(db, business_id, report_content)

    # Simulate sending message
    from src.services.provider_adapters import NotificationAdapter
    await NotificationAdapter.send_notification("WhatsApp", payload.recipient_phone, report_content)
    
    # Emit event
    await EventDispatcher.emit(
        db, "system", "REPORT_DELIVERED",
        {"recipient": payload.recipient_phone, "content": report_content}
    )
    await db.commit()

    return ApiResponse(
        success=True,
        data={
            "delivered": True,
            "recipient": payload.recipient_phone,
            "delivered_at": datetime.utcnow().isoformat()
        }
    )
