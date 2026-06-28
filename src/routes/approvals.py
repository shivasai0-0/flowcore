import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.database import get_db
from src.models import Business, Approval, Session as SessionModel
from src.engine.traversal import GraphTraversalEngine
from src.engine.events import EventDispatcher
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/approvals", tags=["Approvals"])

class ApprovalActionRequest(BaseModel):
    action: str = Field(..., description="Action to take: APPROVE, REJECT, MODIFY, ESCALATE")
    resolved_by: Optional[str] = "Owner"
    notes: Optional[str] = ""

@router.get("", response_model=ApiResponse)
async def list_approvals(
    business_id: Optional[str] = None,
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

    query = select(Approval).where(Approval.business_id == business_id)
    if status_filter:
        query = query.where(Approval.status == status_filter.upper())
    
    query = query.order_by(desc(Approval.created_at))
    res = await db.execute(query)
    approvals = res.scalars().all()

    data = []
    for a in approvals:
        try:
            details = json.loads(a.details_json)
        except Exception:
            details = {}
        data.append({
            "id": a.id,
            "business_id": a.business_id,
            "session_id": a.session_id,
            "node_id": a.node_id,
            "request_type": a.request_type,
            "details": details,
            "status": a.status,
            "created_at": a.created_at.isoformat(),
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "action_taken": a.action_taken,
            "resolved_by": a.resolved_by
        })

    return ApiResponse(success=True, data=data)

@router.post("/{approval_id}/action", response_model=ApiResponse)
async def action_approval(
    approval_id: str,
    payload: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db)
):
    query = select(Approval).where(Approval.id == approval_id)
    res = await db.execute(query)
    approval = res.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")

    if approval.status != "PENDING":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Approval request already resolved with status '{approval.status}'.")

    action = payload.action.upper()
    if action not in {"APPROVE", "REJECT", "MODIFY", "ESCALATE"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid approval action '{action}'.")

    # Update Approval Record
    approval.status = "APPROVED" if action == "APPROVE" else "REJECTED" if action == "REJECT" else "ESCALATED" if action == "ESCALATE" else "MODIFIED"
    approval.action_taken = action
    approval.resolved_at = datetime.utcnow()
    approval.resolved_by = payload.resolved_by or "Owner"
    
    # Save the updated approval state early so dispatch_step does not hit the pending approval intercept lock.
    await db.commit()

    # Emit appropriate FlowCore event
    event_type = f"APPROVAL_{action}"
    await EventDispatcher.emit(
        db, approval.session_id, event_type,
        {
            "approval_id": approval.id,
            "node_id": approval.node_id,
            "resolved_by": approval.resolved_by,
            "notes": payload.notes
        }
    )

    # Resume traverser by dispatching step with action as input
    sess_query = select(SessionModel).where(SessionModel.id == approval.session_id)
    sess_res = await db.execute(sess_query)
    session = sess_res.scalar_one_or_none()
    
    dispatch_res = None
    if session:
        # Unlock locked_until if it was set
        session.locked_until = None
        await db.flush()
        
        # Dispatch traversal step using the action verb as user input to route the FSM edges
        dispatch_res = await GraphTraversalEngine.dispatch_step(db, session, action)

    # Always commit to save event subscriber updates (e.g. task completion)
    await db.commit()

    return ApiResponse(
        success=True,
        data={
            "approval_id": approval.id,
            "status": approval.status,
            "action_taken": approval.action_taken,
            "dispatch_response": {
                "fsm_state_after": dispatch_res.fsm_state_after,
                "messages_sent": dispatch_res.messages_sent
            } if dispatch_res else None
        }
    )
