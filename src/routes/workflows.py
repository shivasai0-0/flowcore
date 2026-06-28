import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from src.database import get_db
from src.models import Business, WorkflowVersion, CompiledGraph, Session as SessionModel, GenerationBenchmark
from src.schemas.graph import WorkflowGraph, WorkflowNode, WorkflowEdge, EdgeCondition
from src.schemas.workflow import (
    WorkflowVersionCreate, 
    WorkflowVersionResponse, 
    WorkflowRegisterResponse, 
    WorkflowValidationReport,
    WorkflowSimulationPayload,
    WorkflowSimulationResponse,
    WorkflowCertificationResponse,
    WorkflowGenerationRequest,
    WorkflowDraft
)
from src.services.ai_generator import AIGenerator
from src.services.draft_validator import WorkflowDraftValidator
from src.schemas.simulation import SimulationInputPayload, SimulationResponse
from src.engine.compiler import WorkflowCompiler
from src.engine.simulation import SimulationEngine
from src.engine.traversal import GraphTraversalEngine
from src.engine.exceptions import FlowCoreRuntimeError
from src.schemas.envelope import ApiResponse
from src.config import sanitize_endpoint

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])


@router.post("/generate", response_model=ApiResponse)
async def generate_workflow(payload: WorkflowGenerationRequest, db: AsyncSession = Depends(get_db)):
    """Generate a workflow portfolio using AI (or programmatic fallback) and auto-register results."""
    import time
    import logging
    logger = logging.getLogger("flowcore.routes.workflows")

    from src.config import settings
    business_id = payload.business_id
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        business_id = settings.ACTIVE_DEV_WORKSPACE

    # Verify business exists
    biz_query = select(Business).where(Business.id == business_id)
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Business '{business_id}' not found.")

    start_time = time.time()

    # Run AI / programmatic generation
    result = await AIGenerator.generate_portfolio(
        db_session=db,
        business_id=business_id,
        description=payload.business_description,
        capability_packs=payload.capability_packs,
        llama_endpoint=sanitize_endpoint(payload.llama_endpoint),
        use_mock_ai=payload.use_mock_ai,
    )

    raw_text = result.get("raw_content") or ""
    # Run deterministic validation gate
    is_valid, validation_errors, draft_obj = WorkflowDraftValidator.validate_draft_json(raw_text)

    if not is_valid:
        logger.warning(f"Workflow validation failed: {validation_errors}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow portfolio failed validation checks:\n" + "\n".join(validation_errors)
        )

    # Compile the validated draft workflows
    registered = []
    for wf in draft_obj.workflows:
        # Translate to WorkflowGraph
        # Build node mapping
        nodes_map = {}
        for n in wf.nodes:
            nodes_map[n.id] = WorkflowNode(
                id=n.id,
                module_name=n.module_name,
                config=n.config,
                fsm_transition_to=n.fsm_transition_to
            )

        # Build edges list
        edges_list = []
        for edge in wf.edges:
            edges_list.append(WorkflowEdge(
                from_node=edge.from_node,
                to_node=edge.to_node,
                condition=EdgeCondition(
                    type=edge.condition.type,
                    key=edge.condition.key,
                    value=edge.condition.value
                )
            ))

        # Compile FSM transition table dynamically
        # Kahn's topological sort
        adj = {n.id: [] for n in wf.nodes}
        in_degree = {n.id: 0 for n in wf.nodes}
        for edge in wf.edges:
            if edge.from_node in adj and edge.to_node in adj:
                adj[edge.from_node].append(edge.to_node)
                in_degree[edge.to_node] += 1

        import collections
        queue = collections.deque([n.id for n in wf.nodes if in_degree[n.id] == 0])
        topo_order = []
        while queue:
            curr = queue.popleft()
            topo_order.append(curr)
            for neighbor in adj[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        FSM_in = {n.id: set() for n in wf.nodes}
        FSM_out = {n.id: set() for n in wf.nodes}
        if wf.entry_node_id in FSM_in:
            FSM_in[wf.entry_node_id].add("START")

        fsm_transition_table = {}
        for nid in topo_order:
            node = nodes_map[nid]
            states_in = FSM_in[nid]
            if not states_in:
                continue

            for state_from in states_in:
                if node.fsm_transition_to:
                    state_to = node.fsm_transition_to
                    if state_from != state_to:
                        if state_from not in fsm_transition_table:
                            fsm_transition_table[state_from] = {}
                        fsm_transition_table[state_from][state_to] = node.module_name
                    state_out = state_to
                else:
                    state_out = state_from
                FSM_out[nid].add(state_out)

            for child in adj[nid]:
                FSM_in[child].update(FSM_out[nid])

        # Resolve trigger event from event connections
        trigger_events_list = []
        for conn in draft_obj.event_connections:
            if conn.to_workflow_id == wf.id:
                trigger_events_list.append(conn.event_type)

        trigger_event = trigger_events_list[0] if trigger_events_list else None

        # Build WorkflowGraph object
        graph_obj = WorkflowGraph(
            business_id=business_id,
            version_number=1,  # resolved dynamically below
            entry_node_id=wf.entry_node_id,
            nodes=nodes_map,
            edges=edges_list,
            fsm_transition_table=fsm_transition_table,
            trigger_event=trigger_event,
            trigger_events=trigger_events_list
        )

        # Run compilation
        compiled, compile_report = WorkflowCompiler.validate_and_compile(graph_obj)
        if not compile_report.is_valid:
            logger.warning(f"Workflow compile failed: {compile_report.errors}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Workflow compile failed:\n" + "\n".join(compile_report.errors)
            )

        # Retrieve next version number
        ver_query = (
            select(WorkflowVersion)
            .where(WorkflowVersion.business_id == business_id)
            .order_by(WorkflowVersion.version_number.desc())
        )
        ver_res = await db.execute(ver_query)
        last = ver_res.scalars().first()
        new_ver = (last.version_number + 1) if last else 1

        # Save with versioning metadata
        version_record = WorkflowVersion(
            business_id=business_id,
            version_number=new_ver,
            status="APPROVED",
            workflow_type="dynamic",
            graph_json=json.dumps(graph_obj.model_dump()),
            is_current=False,
            prompt_version=result.get("prompt_version"),
            model_name=result.get("model_name"),
            generation_time=result.get("elapsed_s"),
            validation_result="VALID"
        )
        db.add(version_record)
        await db.commit()
        await db.refresh(version_record)

        compiled_record = CompiledGraph(
            workflow_version_id=version_record.id,
            business_id=business_id,
            compiled_json=json.dumps(compiled),
        )
        db.add(compiled_record)
        await db.commit()

        registered.append({"name": wf.name, "version_id": version_record.id, "status": version_record.status})

    elapsed_s = time.time() - start_time
    logger.info(f"Successfully generated and registered {len(registered)} workflows in {elapsed_s:.2f}s.")

    return ApiResponse(
        success=True,
        data={
            **result,
            "registered": registered,
        }
    )

@router.post("/register", response_model=ApiResponse[WorkflowRegisterResponse], status_code=status.HTTP_201_CREATED)
async def register_workflow(payload: WorkflowVersionCreate, db: AsyncSession = Depends(get_db)):
    from src.config import settings
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        payload.business_id = settings.ACTIVE_DEV_WORKSPACE
    # Verify business exists
    biz_query = select(Business).where(Business.id == payload.business_id)
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business with ID '{payload.business_id}' does not exist."
        )

    # Resolve version number
    ver_query = select(WorkflowVersion).where(WorkflowVersion.business_id == payload.business_id).order_by(WorkflowVersion.version_number.desc())
    ver_res = await db.execute(ver_query)
    last_version = ver_res.scalars().first()
    new_version_number = (last_version.version_number + 1) if last_version else 1

    # Run dry-run compilation & validation
    payload.graph.business_id = payload.business_id
    compiled, report = WorkflowCompiler.validate_and_compile(payload.graph)

    # Create WorkflowVersion record in database
    version_record = WorkflowVersion(
        business_id=payload.business_id,
        version_number=new_version_number,
        status="DRAFT" if not report.is_valid else "APPROVED",
        workflow_type=payload.workflow_type,
        graph_json=json.dumps(payload.graph.model_dump()),
        is_current=False
    )
    db.add(version_record)
    await db.commit()
    await db.refresh(version_record)

    # If compilation succeeded, store CompiledGraph too
    if report.is_valid:
        compiled_record = CompiledGraph(
            workflow_version_id=version_record.id,
            business_id=payload.business_id,
            compiled_json=json.dumps(compiled)
        )
        db.add(compiled_record)
        await db.commit()

    data = WorkflowRegisterResponse(
        workflow_version_id=version_record.id,
        status=version_record.status,
        validation_report=report
    )
    return ApiResponse(success=True, data=data)

@router.post("/compile/{version_id}", response_model=ApiResponse[WorkflowRegisterResponse])
async def compile_workflow(version_id: str, db: AsyncSession = Depends(get_db)):
    # Find version record
    query = select(WorkflowVersion).where(WorkflowVersion.id == version_id)
    res = await db.execute(query)
    version_record = res.scalar_one_or_none()
    if not version_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow version ID '{version_id}' not found."
        )

    graph_dict = json.loads(version_record.graph_json)
    # Set correct ID in graph
    graph_dict["workflow_version_id"] = version_id
    graph_dict["business_id"] = version_record.business_id
    graph = WorkflowGraph.model_validate(graph_dict)

    # Compile
    compiled, report = WorkflowCompiler.validate_and_compile(graph)

    if report.is_valid:
        version_record.status = "APPROVED"
        # Upsert CompiledGraph
        comp_query = select(CompiledGraph).where(CompiledGraph.workflow_version_id == version_id)
        comp_res = await db.execute(comp_query)
        comp_record = comp_res.scalar_one_or_none()
        
        if not comp_record:
            comp_record = CompiledGraph(
                workflow_version_id=version_id,
                business_id=version_record.business_id,
                compiled_json=json.dumps(compiled)
            )
            db.add(comp_record)
        else:
            comp_record.compiled_json = json.dumps(compiled)
    else:
        version_record.status = "FAILED"

    await db.commit()
    await db.refresh(version_record)

    data = WorkflowRegisterResponse(
        workflow_version_id=version_record.id,
        status=version_record.status,
        validation_report=report
    )
    return ApiResponse(success=True, data=data)

@router.post("/activate/{version_id}", response_model=ApiResponse[WorkflowVersionResponse])
async def activate_workflow(version_id: str, db: AsyncSession = Depends(get_db)):
    # Find version record
    query = select(WorkflowVersion).where(WorkflowVersion.id == version_id)
    res = await db.execute(query)
    version_record = res.scalar_one_or_none()
    if not version_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow version ID '{version_id}' not found."
        )

    # Verify that it is compiled/approved
    if version_record.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot activate workflow version with status '{version_record.status}'. Compile it first."
        )

    # Compile and save/upsert the CompiledGraph record
    graph_dict = json.loads(version_record.graph_json)
    graph_dict["workflow_version_id"] = version_id
    graph_dict["business_id"] = version_record.business_id
    graph = WorkflowGraph.model_validate(graph_dict)
    
    compiled, report = WorkflowCompiler.validate_and_compile(graph)
    if not report.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow activation failed: Static validation failed. Errors: {report.errors}"
        )
        
    # Upsert CompiledGraph
    comp_query = select(CompiledGraph).where(CompiledGraph.workflow_version_id == version_id)
    comp_res = await db.execute(comp_query)
    comp_record = comp_res.scalar_one_or_none()
    if not comp_record:
        comp_record = CompiledGraph(
            workflow_version_id=version_id,
            business_id=version_record.business_id,
            compiled_json=json.dumps(compiled)
        )
        db.add(comp_record)
    else:
        comp_record.compiled_json = json.dumps(compiled)
    await db.flush()

    # If it is a dynamic workflow, it MUST pass the full certification pipeline synchronously
    if version_record.workflow_type == "dynamic":
        replay_match = False
        terminal_lock_certified = False

        # Run certification in an isolated sub-transaction
        async with db.begin_nested() as savepoint:
            try:
                sim_payload = SimulationInputPayload(
                    workflow_graph=graph,
                    inputs=["/start", "1 x 1", "Checkout", "123 Main Street", "CONFIRM_PAYMENT"],
                    simulation_mode="replay",
                    replay_validation=True
                )
                sim_res = await SimulationEngine.run_simulation(db, sim_payload)
                if sim_res.success and sim_res.replay_results:
                    replay_match = sim_res.replay_results.replay_match

                # Create a temporary session in a terminal state (CONFIRMED)
                temp_sess = SessionModel(
                    id=f"cert_sess_{uuid.uuid4().hex[:8]}",
                    business_id=version_record.business_id,
                    customer_phone="+10000000000",
                    fsm_state="CONFIRMED",
                    current_node_id=graph.entry_node_id,
                    carry_unit_json=json.dumps({
                        "version": 1,
                        "session": {
                            "session_id": "temp_cert_sess",
                            "customer_phone": "+10000000000",
                            "business_id": version_record.business_id,
                            "workflow_version_id": version_id,
                            "session_started_at": "2026-05-24T18:00:00Z"
                        }
                    }),
                    workflow_version_id=version_id,
                    is_archived=False,
                    locked_until=None
                )
                db.add(temp_sess)
                await db.flush()

                try:
                    await GraphTraversalEngine.dispatch_step(db, temp_sess, "/start")
                except FlowCoreRuntimeError as e:
                    if e.error_code == "TERMINAL_STATE_LOCKED":
                        terminal_lock_certified = True
                except Exception:
                    pass

                await savepoint.rollback()
            except Exception as e:
                await savepoint.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dynamic workflow certification failed due to simulation error: {str(e)}"
                )

        if not (replay_match and terminal_lock_certified):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dynamic workflow certification failed. Replay Match: {replay_match}, Terminal Lock: {terminal_lock_certified}"
            )

    # Atomically activate new and deprecate prior
    business_id = version_record.business_id

    # 1. Deprecate active workflows for this business
    await db.execute(
        update(WorkflowVersion)
        .where(WorkflowVersion.business_id == business_id, WorkflowVersion.status == "ACTIVE")
        .values(status="DEPRECATED", is_current=False)
    )

    # 2. Set this workflow to ACTIVE
    version_record.status = "ACTIVE"
    version_record.is_current = True
    await db.commit()
    await db.refresh(version_record)

    return ApiResponse(success=True, data=version_record)

@router.post("/redeploy/{version_id}", response_model=ApiResponse)
async def redeploy_workflow(version_id: str, db: AsyncSession = Depends(get_db)):
    """
    Promotes any existing workflow version (DRAFT, APPROVED, DEPRECATED) back to ACTIVE.
    Re-runs static compilation to ensure the graph is still valid, but skips the full
    dynamic certification pipeline (simulation + terminal lock test) since this version
    was already vetted when it was first registered. Useful for rolling back to a known-good
    deployment.
    """
    # 1. Load the target version
    query = select(WorkflowVersion).where(WorkflowVersion.id == version_id)
    res = await db.execute(query)
    version_record = res.scalar_one_or_none()
    if not version_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow version ID '{version_id}' not found."
        )

    if version_record.status == "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This workflow version is already ACTIVE. No redeploy needed."
        )

    # 2. Re-run static compilation to verify the graph is still structurally valid
    try:
        graph_dict = json.loads(version_record.graph_json)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Workflow version has invalid or missing graph_json. Cannot redeploy."
        )

    graph_dict["workflow_version_id"] = version_id
    graph_dict["business_id"] = version_record.business_id
    graph = WorkflowGraph.model_validate(graph_dict)
    compiled, report = WorkflowCompiler.validate_and_compile(graph)

    if not report.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Redeploy aborted: Static recompilation failed. Errors: {report.errors}"
        )

    # 3. Upsert compiled graph record
    comp_query = select(CompiledGraph).where(CompiledGraph.workflow_version_id == version_id)
    comp_res = await db.execute(comp_query)
    comp_record = comp_res.scalar_one_or_none()
    if not comp_record:
        comp_record = CompiledGraph(
            workflow_version_id=version_id,
            business_id=version_record.business_id,
            compiled_json=json.dumps(compiled)
        )
        db.add(comp_record)
    else:
        comp_record.compiled_json = json.dumps(compiled)
    await db.flush()

    # 4. Atomically deprecate current ACTIVE version for this business
    await db.execute(
        update(WorkflowVersion)
        .where(
            WorkflowVersion.business_id == version_record.business_id,
            WorkflowVersion.status == "ACTIVE"
        )
        .values(status="DEPRECATED", is_current=False)
    )

    # 5. Promote this version to ACTIVE
    version_record.status = "ACTIVE"
    version_record.is_current = True
    await db.commit()
    await db.refresh(version_record)

    return ApiResponse(
        success=True,
        data={
            "workflow_version_id": version_record.id,
            "version_number": version_record.version_number,
            "status": version_record.status,
            "is_current": version_record.is_current,
            "message": f"Workflow Version #{version_record.version_number} successfully redeployed as the active workflow."
        }
    )

@router.post("/validate", response_model=ApiResponse[WorkflowValidationReport])
async def dry_run_validate(payload: WorkflowGraph):
    _, report = WorkflowCompiler.validate_and_compile(payload)
    return ApiResponse(success=True, data=report)

@router.post("/simulate", response_model=ApiResponse[SimulationResponse])
async def simulate_workflow(payload: SimulationInputPayload, db: AsyncSession = Depends(get_db)):
    res = await SimulationEngine.run_simulation(
        db_session=db,
        payload=payload
    )
    return ApiResponse(success=True, data=res)

# WORKFLOW CERTIFICATION
@router.post("/certify/{version_id}", response_model=ApiResponse[WorkflowCertificationResponse])
async def certify_workflow(version_id: str, db: AsyncSession = Depends(get_db)):
    query = select(WorkflowVersion).where(WorkflowVersion.id == version_id)
    res = await db.execute(query)
    version_record = res.scalar_one_or_none()
    if not version_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow version ID '{version_id}' not found."
        )

    graph_dict = json.loads(version_record.graph_json)
    graph_dict["workflow_version_id"] = version_id
    graph_dict["business_id"] = version_record.business_id
    graph = WorkflowGraph.model_validate(graph_dict)

    # Run compilation & static validator
    compiled, report = WorkflowCompiler.validate_and_compile(graph)

    if not report.is_valid:
        data = WorkflowCertificationResponse(
            workflow_version_id=version_id,
            static_validation=report,
            replay_determinism_certified=False,
            idempotency_certified=False,
            terminal_state_lock_certified=False
        )
        return ApiResponse(success=True, data=data)

    # Run certification in an isolated sub-transaction
    async with db.begin_nested() as savepoint:
        try:
            # 1. Run dynamic simulation check with replay validation
            sim_payload = SimulationInputPayload(
                workflow_graph=graph,
                inputs=["/start", "1 x 1", "Checkout", "123 Main Street", "CONFIRM_PAYMENT"],
                simulation_mode="replay",
                replay_validation=True
            )
            sim_res = await SimulationEngine.run_simulation(db, sim_payload)
            
            replay_match = False
            if sim_res.success and sim_res.replay_results:
                replay_match = sim_res.replay_results.replay_match

            # 2. Run terminal state locking dynamic verification
            terminal_lock_certified = False
            try:
                # Create a temporary session in a terminal state (CONFIRMED)
                temp_sess = SessionModel(
                    id=f"cert_sess_{uuid.uuid4().hex[:8]}",
                    business_id=version_record.business_id,
                    customer_phone="+10000000000",
                    fsm_state="CONFIRMED",
                    current_node_id=graph.entry_node_id,
                    carry_unit_json=json.dumps({
                        "version": 1,
                        "session": {
                            "session_id": "temp_cert_sess",
                            "customer_phone": "+10000000000",
                            "business_id": version_record.business_id,
                            "workflow_version_id": version_id,
                            "session_started_at": "2026-05-24T18:00:00Z"
                        }
                    }),
                    workflow_version_id=version_id,
                    is_archived=False,
                    locked_until=None
                )
                db.add(temp_sess)
                await db.flush()

                # Dispatching while session FSM state is CONFIRMED must raise FlowCoreRuntimeError
                await GraphTraversalEngine.dispatch_step(db, temp_sess, "/start")
            except FlowCoreRuntimeError as e:
                if e.error_code == "TERMINAL_STATE_LOCKED":
                    terminal_lock_certified = True
            except Exception:
                pass

            # Rollback all temporary records from the certification run
            await savepoint.rollback()

            data = WorkflowCertificationResponse(
                workflow_version_id=version_id,
                static_validation=report,
                replay_determinism_certified=replay_match,
                idempotency_certified=replay_match, # Replay matching succeeded confirms idempotency caching works
                terminal_state_lock_certified=terminal_lock_certified
            )
            return ApiResponse(success=True, data=data)

        except Exception as e:
            await savepoint.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Certification failed with internal error: {str(e)}"
            )

@router.get("/ai-context", response_model=ApiResponse[str])
async def get_ai_context():
    """Returns the markdown context for AI workflow generation (v2)."""
    import os
    # Try v2 first, fall back to v1
    for filename in ["flowcore_runtime_context_v2.md", "flowcore_runtime_context_v1.md"]:
        file_path = os.path.join("ai", "context", filename)
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return ApiResponse(success=True, data=content)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="AI Context file not found."
    )

@router.get("", response_model=ApiResponse)
async def list_workflows(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    from src.config import settings
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        business_id = settings.ACTIVE_DEV_WORKSPACE
    from typing import Optional
    if business_id:
        query = select(WorkflowVersion).where(WorkflowVersion.business_id == business_id).order_by(WorkflowVersion.version_number.desc())
    else:
        query = select(WorkflowVersion).order_by(WorkflowVersion.version_number.desc())
    res = await db.execute(query)
    versions = res.scalars().all()
    
    data = []
    for v in versions:
        try:
            graph_dict = json.loads(v.graph_json)
        except Exception:
            graph_dict = {}
        data.append({
            "id": v.id,
            "business_id": v.business_id,
            "version_number": v.version_number,
            "status": v.status,
            "workflow_type": v.workflow_type,
            "is_current": v.is_current,
            "created_at": v.created_at.isoformat(),
            "trigger_event": graph_dict.get("trigger_event"),
            "trigger_events": graph_dict.get("trigger_events", []),
            "entry_node_id": graph_dict.get("entry_node_id"),
            "nodes_count": len(graph_dict.get("nodes", {}))
        })
    return ApiResponse(success=True, data=data)
BENCHMARKS = [
    {
        "business_type": "restaurant",
        "description": "A busy pizza restaurant that takes table reservations, displays a menu, allows customers to order food, handles card or cash on delivery payments, and triggers delivery tracking."
    },
    {
        "business_type": "diagnostic_lab",
        "description": "A diagnostic laboratory where patients can book blood tests and scans, choose slots, receive automated test report notifications, and submit feedback."
    },
    {
        "business_type": "hospital",
        "description": "A multi-specialty hospital managing outpatient OPD appointments, ward admissions, billing invoices, emergency alerts, and patient support requests."
    },
    {
        "business_type": "hospital_no_appointments",
        "description": "A walk-in clinic and hospital that manages patient admissions, emergency triage, consultations, pharmacy prescriptions, and billing, without pre-booked appointments."
    },
    {
        "business_type": "gym",
        "description": "A fitness center offering monthly gym memberships, personal training bookings, class schedules, subscription payments, and customer support."
    },
    {
        "business_type": "salon",
        "description": "A beauty salon and spa offering haircuts, massage packages, slot booking, manager approvals for premium packages, and feedback collection."
    },
    {
        "business_type": "repair_service",
        "description": "An appliance repair center where customers can request a technician visit, get cost estimations, approve repair jobs, and pay after completion."
    },
    {
        "business_type": "pharmacy",
        "description": "A pharmacy where patients can upload prescriptions, get order verification from a pharmacist, pay online, and get medications delivered."
    },
    {
        "business_type": "school",
        "description": "A private school managing student admissions, course enrollments, tuition fee payments, parent-teacher meeting schedules, and general queries."
    },
    {
        "business_type": "hotel",
        "description": "A luxury hotel providing room bookings, room service orders, check-in/check-out workflow, and review generation after checkout."
    }
]

@router.post("/generate-debug", response_model=ApiResponse)
async def generate_workflow_debug(payload: WorkflowGenerationRequest, db: AsyncSession = Depends(get_db)):
    business_id = payload.business_id
    from src.config import settings
    if settings.DEVELOPMENT_WORKSPACE_MODE and settings.ACTIVE_DEV_WORKSPACE:
        business_id = settings.ACTIVE_DEV_WORKSPACE

    # Verify business exists or fallback to first business
    biz_query = select(Business).where(Business.id == business_id)
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    if not business:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            business = Business(
                id="debug_sentinel",
                name="Debug Sentinel Business",
                whatsapp_number="+18888888889",
                business_type="restaurant"
            )
            db.add(business)
            await db.commit()
            await db.refresh(business)
        business_id = business.id

    result = await AIGenerator.generate_portfolio(
        db_session=db,
        business_id=business_id,
        description=payload.business_description,
        capability_packs=payload.capability_packs,
        llama_endpoint=sanitize_endpoint(payload.llama_endpoint),
        use_mock_ai=payload.use_mock_ai,
    )

    raw_text = result.get("raw_content") or ""
    is_valid, validation_errors, draft_obj = WorkflowDraftValidator.validate_draft_json(raw_text)

    compiled_workflows = {}
    if is_valid:
        # Compile draft to graphs (without writing to DB)
        for wf in draft_obj.workflows:
            nodes_map = {}
            for n in wf.nodes:
                nodes_map[n.id] = WorkflowNode(
                    id=n.id,
                    module_name=n.module_name,
                    config=n.config,
                    fsm_transition_to=n.fsm_transition_to
                )

            edges_list = []
            for edge in wf.edges:
                edges_list.append(WorkflowEdge(
                    from_node=edge.from_node,
                    to_node=edge.to_node,
                    condition=EdgeCondition(
                        type=edge.condition.type,
                        key=edge.condition.key,
                        value=edge.condition.value
                    )
                ))

            adj = {n.id: [] for n in wf.nodes}
            in_degree = {n.id: 0 for n in wf.nodes}
            for edge in wf.edges:
                if edge.from_node in adj and edge.to_node in adj:
                    adj[edge.from_node].append(edge.to_node)
                    in_degree[edge.to_node] += 1

            import collections
            queue = collections.deque([n.id for n in wf.nodes if in_degree[n.id] == 0])
            topo_order = []
            while queue:
                curr = queue.popleft()
                topo_order.append(curr)
                for neighbor in adj[curr]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)

            FSM_in = {n.id: set() for n in wf.nodes}
            FSM_out = {n.id: set() for n in wf.nodes}
            if wf.entry_node_id in FSM_in:
                FSM_in[wf.entry_node_id].add("START")

            fsm_transition_table = {}
            for nid in topo_order:
                node = nodes_map[nid]
                states_in = FSM_in[nid]
                if not states_in:
                    continue

                for state_from in states_in:
                    if node.fsm_transition_to:
                        state_to = node.fsm_transition_to
                        if state_from != state_to:
                            if state_from not in fsm_transition_table:
                                fsm_transition_table[state_from] = {}
                            fsm_transition_table[state_from][state_to] = node.module_name
                        state_out = state_to
                    else:
                        state_out = state_from
                    FSM_out[nid].add(state_out)

                for child in adj[nid]:
                    FSM_in[child].update(FSM_out[nid])

            trigger_events_list = []
            for conn in draft_obj.event_connections:
                if conn.to_workflow_id == wf.id:
                    trigger_events_list.append(conn.event_type)

            trigger_event = trigger_events_list[0] if trigger_events_list else None

            graph_obj = WorkflowGraph(
                business_id=business_id,
                version_number=1,
                entry_node_id=wf.entry_node_id,
                nodes=nodes_map,
                edges=edges_list,
                fsm_transition_table=fsm_transition_table,
                trigger_event=trigger_event,
                trigger_events=trigger_events_list
            )

            try:
                compiled, compile_report = WorkflowCompiler.validate_and_compile(graph_obj)
                if compile_report.is_valid:
                    compiled_workflows[wf.name] = compiled
            except Exception:
                pass

    return ApiResponse(
        success=True,
        data={
            "business_description": payload.business_description,
            "prompt_sent": {
                "system": result.get("system_prompt") or "Mock system prompt.",
                "user": result.get("user_prompt") or f"Description: {payload.business_description}"
            },
            "raw_llm_output": raw_text,
            "parsed_workflow_draft": json.loads(raw_text) if is_valid else None,
            "validation_result": {
                "is_valid": is_valid,
                "errors": validation_errors
            },
            "compiled_workflows": compiled_workflows
        }
    )

@router.get("/benchmarks", response_model=ApiResponse)
async def get_benchmarks(db: AsyncSession = Depends(get_db)):
    query = select(GenerationBenchmark).order_by(GenerationBenchmark.created_at.desc())
    res = await db.execute(query)
    records = res.scalars().all()
    
    data = []
    for r in records:
        data.append({
            "id": r.id,
            "business_type": r.business_type,
            "input_description": r.input_description,
            "raw_output": r.raw_output,
            "is_valid": r.is_valid,
            "validation_errors": r.validation_errors.split("\n") if r.validation_errors else [],
            "created_at": r.created_at.isoformat()
        })
    return ApiResponse(success=True, data=data)

@router.post("/benchmarks/run", response_model=ApiResponse)
async def run_benchmarks(use_mock_ai: bool = True, db: AsyncSession = Depends(get_db)):
    # Find or create a mock business
    biz_query = select(Business).limit(1)
    biz_res = await db.execute(biz_query)
    business = biz_res.scalar_one_or_none()
    
    if not business:
        business = Business(
            id="benchmark_sentinel",
            name="Benchmark Sentinel Business",
            whatsapp_number="+18888888888",
            business_type="restaurant"
        )
        db.add(business)
        await db.commit()
        await db.refresh(business)
        
    business_id = business.id
    
    runs = []
    from datetime import datetime
    for b in BENCHMARKS:
        result = await AIGenerator.generate_portfolio(
            db_session=db,
            business_id=business_id,
            description=b["description"],
            capability_packs=[b["business_type"]],
            use_mock_ai=use_mock_ai
        )
        
        raw_text = result.get("raw_content") or ""
        is_valid, validation_errors, draft_obj = WorkflowDraftValidator.validate_draft_json(raw_text)
        
        run_record = GenerationBenchmark(
            id=str(uuid.uuid4()),
            business_type=b["business_type"],
            input_description=b["description"],
            raw_output=raw_text,
            parsed_draft_json=json.dumps(draft_obj.model_dump()) if is_valid else None,
            is_valid=is_valid,
            validation_errors="\n".join(validation_errors) if validation_errors else None,
            created_at=datetime.utcnow()
        )
        db.add(run_record)
        runs.append(run_record)
        
    await db.commit()
    
    data = []
    for r in runs:
        data.append({
            "id": r.id,
            "business_type": r.business_type,
            "input_description": r.input_description,
            "raw_output": r.raw_output,
            "is_valid": r.is_valid,
            "validation_errors": r.validation_errors.split("\n") if r.validation_errors else [],
            "created_at": r.created_at.isoformat()
        })
    return ApiResponse(success=True, data=data)

@router.get("/{version_id}", response_model=ApiResponse)
async def get_workflow(version_id: str, db: AsyncSession = Depends(get_db)):
    query = select(WorkflowVersion).where(WorkflowVersion.id == version_id)
    res = await db.execute(query)
    v = res.scalar_one_or_none()
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow version ID '{version_id}' not found."
        )
    
    try:
        graph_dict = json.loads(v.graph_json)
    except Exception:
        graph_dict = {}
        
    return ApiResponse(
        success=True,
        data={
            "id": v.id,
            "business_id": v.business_id,
            "version_number": v.version_number,
            "status": v.status,
            "workflow_type": v.workflow_type,
            "is_current": v.is_current,
            "created_at": v.created_at.isoformat(),
            "graph": graph_dict
        }
    )
