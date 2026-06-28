import json
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.database import get_db
from src.models import Business, GenerationJob, WorkflowVersion
from src.services.ai_generator import AIGenerator
from src.schemas.envelope import ApiResponse
from src.config import sanitize_endpoint

router = APIRouter(prefix="/api/v1/generation-jobs", tags=["Generation Jobs"])

class GenerationJobCreateRequest(BaseModel):
    business_id: Optional[str] = None
    business_description: str = Field(..., min_length=1)
    capability_packs: List[str] = Field(default_factory=list)
    llama_endpoint: Optional[str] = "http://localhost:11434"
    use_mock_ai: Optional[bool] = True

@router.get("", response_model=ApiResponse)
async def list_generation_jobs(business_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            return ApiResponse(success=True, data=[])
        business_id = business.id

    query = select(GenerationJob).where(GenerationJob.business_id == business_id).order_by(desc(GenerationJob.created_at))
    res = await db.execute(query)
    jobs = res.scalars().all()

    data = []
    for j in jobs:
        try:
            packs = json.loads(j.input_packs_json)
        except Exception:
            packs = []
        data.append({
            "id": j.id,
            "business_id": j.business_id,
            "status": j.status,
            "progress": j.progress,
            "input_description": j.input_description,
            "input_packs": packs,
            "llama_endpoint": j.llama_endpoint,
            "method": j.method,
            "category": j.category,
            "error": j.error,
            "created_at": j.created_at.isoformat(),
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "completed_at": j.completed_at.isoformat() if j.completed_at else None
        })

    return ApiResponse(success=True, data=data)

@router.post("", response_model=ApiResponse)
async def trigger_generation_job(payload: GenerationJobCreateRequest, db: AsyncSession = Depends(get_db)):
    business_id = payload.business_id
    if not business_id:
        biz_query = select(Business).limit(1)
        biz_res = await db.execute(biz_query)
        business = biz_res.scalar_one_or_none()
        if not business:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No business registered.")
        business_id = business.id

    # 1. Create Job record in PENDING / RUNNING state
    sanitized_url = sanitize_endpoint(payload.llama_endpoint)
    job = GenerationJob(
        business_id=business_id,
        status="running",
        progress=25,
        input_description=payload.business_description,
        input_packs_json=json.dumps(payload.capability_packs),
        llama_endpoint=sanitized_url,
        started_at=datetime.utcnow()
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 2. Execute AI generator synchronously
    try:
        # Simulate step validating (status updates)
        job.status = "validating"
        job.progress = 60
        await db.commit()

        res = await AIGenerator.generate_portfolio(
            db_session=db,
            business_id=business_id,
            description=payload.business_description,
            capability_packs=payload.capability_packs,
            llama_endpoint=sanitized_url,
            use_mock_ai=payload.use_mock_ai
        )

        if res.get("success"):
            # Auto-register each generated workflow via register endpoint internally
            wf_entries = Object_entries = list((res.get("workflows") or {}).items())
            for name, graph in wf_entries:
                try:
                    # Register workflow version in DB
                    from src.schemas.graph import WorkflowGraph
                    from src.engine.compiler import WorkflowCompiler
                    graph_obj = WorkflowGraph.model_validate(graph)
                    graph_obj.business_id = business_id
                    compiled, report = WorkflowCompiler.validate_and_compile(graph_obj)
                    
                    # Fetch next version number
                    ver_query = select(WorkflowVersion).where(WorkflowVersion.business_id == business_id).order_by(WorkflowVersion.version_number.desc())
                    ver_res = await db.execute(ver_query)
                    last_version = ver_res.scalars().first()
                    new_version_number = (last_version.version_number + 1) if last_version else 1
                    
                    version_record = WorkflowVersion(
                        business_id=business_id,
                        version_number=new_version_number,
                        status="DRAFT" if not report.is_valid else "APPROVED",
                        workflow_type="dynamic",
                        graph_json=json.dumps(graph_obj.model_dump()),
                        is_current=False
                    )
                    db.add(version_record)
                    await db.commit()
                except Exception:
                    pass

            job.status = "completed"
            job.progress = 100
            job.category = res.get("category")
            job.method = res.get("method")
            job.result_json = json.dumps(res)
            job.completed_at = datetime.utcnow()
            await db.commit()
        else:
            job.status = "failed"
            job.progress = 100
            job.error = res.get("error") or "Unknown generation failure"
            job.completed_at = datetime.utcnow()
            await db.commit()

    except Exception as e:
        job.status = "failed"
        job.progress = 100
        job.error = str(e)
        job.completed_at = datetime.utcnow()
        await db.commit()

    return ApiResponse(
        success=job.status == "completed",
        data={
            "job_id": job.id,
            "status": job.status,
            "progress": job.progress,
            "category": job.category,
            "method": job.method,
            "error": job.error
        }
    )
