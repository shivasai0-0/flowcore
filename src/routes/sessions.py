import json
import asyncio
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.database import get_db
from src.models import Session as SessionModel, WorkflowVersion, Business, ExecutionLog, ExecutionSnapshot
from src.schemas.session import SessionCreate, SessionResponse, DispatchPayload, DispatchResponse, ReplayResponse
from src.schemas.carry_unit import CarryUnit
from src.engine.traversal import GraphTraversalEngine
from src.engine.exceptions import FlowCoreRuntimeError
from src.engine.simulation import ReplayEngine
from src.engine.side_effects import ExternalOperationRegistry, ConcurrentOperationError
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/sessions", tags=["Sessions"])

# Background task for side effects execution
async def run_side_effect(op_key: str, se: dict, session_id: str):
    from src.database import AsyncSessionLocal
    async with AsyncSessionLocal() as local_db:
        try:
            # Simulate side-effect latency/external API call
            await asyncio.sleep(0.01)
            await ExternalOperationRegistry.commit_success(
                local_db, op_key, {"status": "SUCCESS", "executed_at": datetime.utcnow().isoformat()}
            )
            await local_db.commit()
        except Exception as e:
            await ExternalOperationRegistry.commit_failure(local_db, op_key)
            await local_db.commit()

@router.post("", response_model=ApiResponse[SessionResponse], status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    # Verify business exists
    biz_query = select(Business).where(Business.id == payload.business_id)
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business with ID '{payload.business_id}' does not exist."
        )

    # Find the current active workflow version for the business (INV-03)
    wf_query = select(WorkflowVersion).where(
        WorkflowVersion.business_id == payload.business_id,
        WorkflowVersion.status == "ACTIVE",
        WorkflowVersion.is_current == True
    )
    wf_res = await db.execute(wf_query)
    active_workflow = wf_res.scalar_one_or_none()
    if not active_workflow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business has no active workflow version. Cannot start session."
        )

    session_id = f"sess_{datetime.utcnow().strftime('%Y%m%d%H%M')}_{payload.customer_phone.replace('+', '')[-6:]}"
    
    # Initialize namespaced carry unit with seeded parameters
    carry_unit = CarryUnit(
        session={
            "session_id": session_id,
            "customer_phone": payload.customer_phone,
            "business_id": payload.business_id,
            "workflow_version_id": active_workflow.id,
            "session_started_at": datetime.utcnow().isoformat()
        }
    )

    session_record = SessionModel(
        id=session_id,
        business_id=payload.business_id,
        customer_phone=payload.customer_phone,
        fsm_state="START",
        current_node_id=None,
        carry_unit_json=json.dumps(carry_unit.model_dump()),
        workflow_version_id=active_workflow.id,
        is_archived=False,
        locked_until=None,
        last_active_at=datetime.utcnow()
    )

    db.add(session_record)
    await db.commit()
    await db.refresh(session_record)

    # Return mapped response
    return ApiResponse(
        success=True,
        data=SessionResponse(
            id=session_record.id,
            business_id=session_record.business_id,
            customer_phone=session_record.customer_phone,
            fsm_state=session_record.fsm_state,
            current_node_id=session_record.current_node_id,
            carry_unit=carry_unit,
            workflow_version_id=session_record.workflow_version_id,
            updated_at=session_record.updated_at
        )
    )

@router.post("/dispatch/{session_id}", response_model=ApiResponse[DispatchResponse])
async def dispatch_event(session_id: str, payload: DispatchPayload, db: AsyncSession = Depends(get_db)):
    # Load session record
    query = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(query)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )

    try:
        response = await GraphTraversalEngine.dispatch_step(
            db_session=db,
            session_record=session_record,
            user_input=payload.user_input
        )
        
        # Check or register side effects
        runnable_side_effects = []
        for se in response.side_effects:
            op_key = f"{session_id}:{se['node_id']}:{se['side_effect']}"
            try:
                status_code, cached = await ExternalOperationRegistry.check_or_register(db, session_id, op_key)
                if status_code in ("REGISTERED", "RETRY"):
                    runnable_side_effects.append((op_key, se))
            except ConcurrentOperationError:
                pass

        await db.commit()
        
        # Execute runnable side effects post-commit in background tasks
        for op_key, se in runnable_side_effects:
            asyncio.create_task(run_side_effect(op_key, se, session_id))

        return ApiResponse(success=True, data=response)
        
    except FlowCoreRuntimeError as e:
        # Rethrow FlowCoreRuntimeError to be caught by global handler
        raise e

@router.get("/replay/{session_id}", response_model=ApiResponse[ReplayResponse])
async def replay_session(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        response = await ReplayEngine.get_session_replay(db, session_id)
        return ApiResponse(success=True, data=response)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/logs/{session_id}")
async def get_session_logs(session_id: str, db: AsyncSession = Depends(get_db)):
    query = select(ExecutionLog).where(ExecutionLog.session_id == session_id).order_by(ExecutionLog.executed_at.asc())
    res = await db.execute(query)
    logs = res.scalars().all()
    
    # Return formatted list in ApiResponse envelope
    return ApiResponse(
        success=True,
        data=[
            {
                "id": log.id,
                "session_id": log.session_id,
                "node_id": log.node_id,
                "module_name": log.module_name,
                "inputs": json.loads(log.inputs_json),
                "outputs": json.loads(log.outputs_json),
                "fsm_state_before": log.fsm_state_before,
                "fsm_state_after": log.fsm_state_after,
                "executed_at": log.executed_at
            } for log in logs
        ]
    )

# UPGRADED LIFECYCLE APIS
@router.post("/resume/{session_id}", response_model=ApiResponse[SessionResponse])
async def resume_session(session_id: str, db: AsyncSession = Depends(get_db)):
    query = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(query)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    session_record.is_archived = False
    session_record.locked_until = None
    session_record.last_active_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session_record)
    
    carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))
    return ApiResponse(
        success=True,
        data=SessionResponse(
            id=session_record.id,
            business_id=session_record.business_id,
            customer_phone=session_record.customer_phone,
            fsm_state=session_record.fsm_state,
            current_node_id=session_record.current_node_id,
            carry_unit=carry_unit,
            workflow_version_id=session_record.workflow_version_id,
            updated_at=session_record.updated_at
        )
    )

@router.get("/active", response_model=ApiResponse[dict])
async def get_active_session(business_id: str, customer_phone: str, db: AsyncSession = Depends(get_db)):
    """
    Dynamic session resolver for n8n orchestration.
    Finds the most recent non-archived session for a given (business_id, customer_phone) pair.
    Returns 404 if no active session exists — n8n should then call POST /sessions to create one.
    This removes the need for n8n to reconstruct or store time-based session IDs.
    """
    from sqlalchemy import desc
    query = (
        select(SessionModel)
        .where(
            SessionModel.business_id == business_id,
            SessionModel.customer_phone == customer_phone,
            SessionModel.is_archived == False,
            SessionModel.fsm_state.notin_(["CANCELLED"])
        )
        .order_by(desc(SessionModel.last_active_at))
        .limit(1)
    )
    res = await db.execute(query)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found for this customer. Create a new session."
        )
    carry_unit = json.loads(session_record.carry_unit_json)
    return ApiResponse(success=True, data={
        "session_id": session_record.id,
        "business_id": session_record.business_id,
        "customer_phone": session_record.customer_phone,
        "fsm_state": session_record.fsm_state,
        "current_node_id": session_record.current_node_id,
        "carry_unit": carry_unit,
        "last_active_at": session_record.last_active_at.isoformat()
    })

@router.get("/inspect/{session_id}", response_model=ApiResponse[dict])

async def inspect_session(session_id: str, db: AsyncSession = Depends(get_db)):
    query = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(query)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    # Get execution logs count
    log_query = select(ExecutionLog).where(ExecutionLog.session_id == session_id)
    log_res = await db.execute(log_query)
    logs_count = len(log_res.scalars().all())
    
    # Get snapshots count
    snap_query = select(ExecutionSnapshot).where(ExecutionSnapshot.session_id == session_id)
    snap_res = await db.execute(snap_query)
    snapshots_count = len(snap_res.scalars().all())
    
    carry_unit = json.loads(session_record.carry_unit_json)
    
    data = {
        "session_id": session_record.id,
        "business_id": session_record.business_id,
        "customer_phone": session_record.customer_phone,
        "fsm_state": session_record.fsm_state,
        "current_node_id": session_record.current_node_id,
        "carry_unit": carry_unit,
        "is_archived": session_record.is_archived,
        "locked_until": session_record.locked_until.isoformat() if session_record.locked_until else None,
        "last_active_at": session_record.last_active_at.isoformat(),
        "logs_count": logs_count,
        "snapshots_count": snapshots_count
    }
    return ApiResponse(success=True, data=data)

@router.post("/archive/{session_id}", response_model=ApiResponse[SessionResponse])
async def archive_session(session_id: str, db: AsyncSession = Depends(get_db)):
    query = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(query)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    session_record.is_archived = True
    await db.commit()
    await db.refresh(session_record)
    
    carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))
    return ApiResponse(
        success=True,
        data=SessionResponse(
            id=session_record.id,
            business_id=session_record.business_id,
            customer_phone=session_record.customer_phone,
            fsm_state=session_record.fsm_state,
            current_node_id=session_record.current_node_id,
            carry_unit=carry_unit,
            workflow_version_id=session_record.workflow_version_id,
            updated_at=session_record.updated_at
        )
    )

@router.post("/recover/{session_id}", response_model=ApiResponse[SessionResponse])
async def recover_session(session_id: str, db: AsyncSession = Depends(get_db)):
    query = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(query)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Session not found.")
    
    session_record.is_archived = False
    await db.commit()
    await db.refresh(session_record)
    
    carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))
    return ApiResponse(
        success=True,
        data=SessionResponse(
            id=session_record.id,
            business_id=session_record.business_id,
            customer_phone=session_record.customer_phone,
            fsm_state=session_record.fsm_state,
            current_node_id=session_record.current_node_id,
            carry_unit=carry_unit,
            workflow_version_id=session_record.workflow_version_id,
            updated_at=session_record.updated_at
        )
    )

@router.post("/timeout", response_model=ApiResponse[list[str]])
async def check_session_timeouts(timeout_minutes: int = 30, db: AsyncSession = Depends(get_db)):
    threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
    
    # Select all active non-archived sessions that are older than threshold
    query = select(SessionModel).where(
        SessionModel.is_archived == False,
        SessionModel.last_active_at < threshold
    )
    res = await db.execute(query)
    expired_sessions = res.scalars().all()
    
    timed_out_ids = []
    for s in expired_sessions:
        s.is_archived = True
        s.fsm_state = "CANCELLED"
        timed_out_ids.append(s.id)
        
    await db.commit()
    return ApiResponse(success=True, data=timed_out_ids)

@router.put("/unlock/{session_id}", response_model=ApiResponse[SessionResponse])
async def unlock_session(session_id: str, db: AsyncSession = Depends(get_db)):
    query = select(SessionModel).where(SessionModel.id == session_id)
    res = await db.execute(query)
    session_record = res.scalar_one_or_none()
    if not session_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found."
        )
    
    session_record.locked_until = None
    await db.commit()
    await db.refresh(session_record)
    
    carry_unit = CarryUnit.model_validate(json.loads(session_record.carry_unit_json))
    
    return ApiResponse(
        success=True,
        data=SessionResponse(
            id=session_record.id,
            business_id=session_record.business_id,
            customer_phone=session_record.customer_phone,
            fsm_state=session_record.fsm_state,
            current_node_id=session_record.current_node_id,
            carry_unit=carry_unit,
            workflow_version_id=session_record.workflow_version_id,
            updated_at=session_record.updated_at
        )
    )
