import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import get_db
from src.models import ExecutionSnapshot
from src.schemas.session import SessionResponse
from src.schemas.carry_unit import CarryUnit
from src.engine.time_travel import TimeTravelEngine, SnapshotNotFoundError
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["Snapshots & Time Travel"])

@router.get("/{session_id}/snapshots", response_model=ApiResponse[list[dict]])
async def list_snapshots(session_id: str, db: AsyncSession = Depends(get_db)):
    """Lists snapshots saved for a specific session ordered chronologically."""
    query = select(ExecutionSnapshot).where(ExecutionSnapshot.session_id == session_id).order_by(ExecutionSnapshot.timestamp.asc())
    res = await db.execute(query)
    records = res.scalars().all()
    
    data = [
        {
            "id": r.id,
            "session_id": r.session_id,
            "node_id": r.node_id,
            "fsm_state": r.fsm_state,
            "carry_unit": json.loads(r.carry_unit_json),
            "timestamp": r.timestamp
        }
        for r in records
    ]
    return ApiResponse(success=True, data=data)

@router.post("/{session_id}/rollback/{snapshot_id}", response_model=ApiResponse[SessionResponse])
async def rollback_session(session_id: str, snapshot_id: str, db: AsyncSession = Depends(get_db)):
    """Reverts session state back to the specified snapshot timestamp and commits."""
    try:
        session_record = await TimeTravelEngine.rollback_session_to_snapshot(db, session_id, snapshot_id)
        await db.commit()
        
        carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))
        data = SessionResponse(
            id=session_record.id,
            business_id=session_record.business_id,
            customer_phone=session_record.customer_phone,
            fsm_state=session_record.fsm_state,
            current_node_id=session_record.current_node_id,
            carry_unit=carry_unit,
            workflow_version_id=session_record.workflow_version_id,
            updated_at=session_record.updated_at
        )
        return ApiResponse(success=True, data=data)
    except SnapshotNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
