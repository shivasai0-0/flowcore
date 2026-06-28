import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.database import get_db
from src.models import Business, EventStoreRecord
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/events", tags=["Events"])

@router.get("", response_model=ApiResponse)
async def list_events(
    business_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    # Resolve business
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            return ApiResponse(success=True, data=[])
        business_id = business.id

    query = select(EventStoreRecord).where(
        EventStoreRecord.business_id == business_id
    ).order_by(desc(EventStoreRecord.emitted_at)).limit(limit).offset(offset)

    res = await db.execute(query)
    records = res.scalars().all()

    data = []
    for r in records:
        try:
            payload = json.loads(r.payload_json)
        except Exception:
            payload = {}
        data.append({
            "id": r.id,
            "session_id": r.session_id,
            "business_id": r.business_id,
            "workflow_version_id": r.workflow_version_id,
            "customer_id": r.customer_id,
            "event_type": r.event_type,
            "payload": payload,
            "emitted_at": r.emitted_at.isoformat()
        })

    return ApiResponse(success=True, data=data)

@router.get("/live", response_model=ApiResponse)
async def list_live_events(
    business_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    # Return the latest 25 events
    return await list_events(business_id=business_id, limit=25, offset=0, db=db)
