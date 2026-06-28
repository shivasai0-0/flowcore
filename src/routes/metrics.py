from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database import get_db
from src.models import ExecutionMetric
from src.schemas.envelope import ApiResponse

router = APIRouter(prefix="/api/v1/metrics", tags=["Observability & Telemetry"])

@router.get("/{session_id}", response_model=ApiResponse[dict])
async def get_session_metrics(session_id: str, db: AsyncSession = Depends(get_db)):
    """Computes and retrieves traversal execution metrics for a specific session."""
    query = select(ExecutionMetric).where(ExecutionMetric.session_id == session_id).order_by(ExecutionMetric.timestamp.asc())
    res = await db.execute(query)
    metrics = res.scalars().all()

    if not metrics:
        data = {
            "session_id": session_id,
            "total_execution_steps": 0,
            "error_count": 0,
            "average_latency_ms": 0.0,
            "max_latency_ms": 0,
            "steps": []
        }
        return ApiResponse(success=True, data=data)

    total_steps = len(metrics)
    error_count = sum(1 for m in metrics if m.is_error)
    avg_latency = sum(m.latency_ms for m in metrics) / total_steps
    max_latency = max(m.latency_ms for m in metrics)

    steps_data = [
        {
            "node_id": m.node_id,
            "module_name": m.module_name,
            "latency_ms": m.latency_ms,
            "is_error": m.is_error,
            "retry_count": m.retry_count,
            "timestamp": m.timestamp
        }
        for m in metrics
    ]

    data = {
        "session_id": session_id,
        "total_execution_steps": total_steps,
        "error_count": error_count,
        "average_latency_ms": avg_latency,
        "max_latency_ms": max_latency,
        "steps": steps_data
    }
    return ApiResponse(success=True, data=data)
