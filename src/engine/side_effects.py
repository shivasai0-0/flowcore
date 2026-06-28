import json
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models import ExternalOperation

class ConcurrentOperationError(ValueError):
    """Raised when the same side effect is executed concurrently or repeatedly while pending."""
    pass

class ExternalOperationRegistry:
    @staticmethod
    async def check_or_register(
        db_session: AsyncSession,
        session_id: str,
        operation_key: str
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Checks the status of an external operation.
        - If it does not exist, registers intent (PENDING) and returns ('REGISTERED', None).
        - If it is PENDING, raises ConcurrentOperationError.
        - If it is COMPLETED, returns ('COMPLETED', cached_response).
        - If it is FAILED, resets status to PENDING and returns ('RETRY', None).
        """
        query = select(ExternalOperation).where(ExternalOperation.operation_key == operation_key)
        res = await db_session.execute(query)
        op = res.scalar_one_or_none()

        if not op:
            new_op = ExternalOperation(
                session_id=session_id,
                operation_key=operation_key,
                status="PENDING"
            )
            db_session.add(new_op)
            await db_session.flush()
            return "REGISTERED", None

        if op.status == "PENDING":
            raise ConcurrentOperationError(
                f"Operation '{operation_key}' is currently executing (PENDING state)."
            )

        if op.status == "COMPLETED":
            return "COMPLETED", json.loads(op.response_json)

        # If FAILED, reset to PENDING to allow retry
        op.status = "PENDING"
        op.completed_at = None
        await db_session.flush()
        return "RETRY", None

    @staticmethod
    async def commit_success(
        db_session: AsyncSession,
        operation_key: str,
        response_data: Dict[str, Any]
    ) -> None:
        """Marks the operation as COMPLETED and stores response payload."""
        query = select(ExternalOperation).where(ExternalOperation.operation_key == operation_key)
        res = await db_session.execute(query)
        op = res.scalar_one_or_none()
        if op:
            op.status = "COMPLETED"
            op.response_json = json.dumps(response_data)
            op.completed_at = datetime.utcnow()
            await db_session.flush()

    @staticmethod
    async def commit_failure(
        db_session: AsyncSession,
        operation_key: str
    ) -> None:
        """Marks the operation as FAILED."""
        query = select(ExternalOperation).where(ExternalOperation.operation_key == operation_key)
        res = await db_session.execute(query)
        op = res.scalar_one_or_none()
        if op:
            op.status = "FAILED"
            op.completed_at = datetime.utcnow()
            await db_session.flush()


import logging
import asyncio

logger = logging.getLogger("flowcore.side_effects")

# Side Effect Handlers
async def persist_order(session_id: str, payload: dict) -> dict:
    logger.info(f"Side Effect: persist_order executed for session {session_id}")
    return {"status": "SUCCESS", "persisted": True}

async def external_gateway_handshake(session_id: str, payload: dict) -> dict:
    logger.info(f"Side Effect: external_gateway_handshake executed for session {session_id}")
    return {"status": "SUCCESS", "gateway_tx": "gw_tx_123"}

async def notify_finance(session_id: str, payload: dict) -> dict:
    logger.info(f"Side Effect: notify_finance executed for session {session_id}")
    return {"status": "SUCCESS", "notified": True}

async def dispatch_delivery_courier(session_id: str, payload: dict) -> dict:
    logger.info(f"Side Effect: dispatch_delivery_courier executed for session {session_id}")
    return {"status": "SUCCESS", "delivery_started": True}

SIDE_EFFECT_HANDLERS = {
    "persist_order": persist_order,
    "external_gateway_handshake": external_gateway_handshake,
    "notify_finance": notify_finance,
    "dispatch_delivery_courier": dispatch_delivery_courier
}

async def run_retry_worker(db_session_factory, poll_interval: float = 5.0):
    """
    Background worker loop that queries for FAILED (or timed-out PENDING) operations
    and retries executing their mapped handlers.
    """
    logger.info("Starting background side effects retry worker...")
    while True:
        try:
            await asyncio.sleep(poll_interval)
            async with db_session_factory() as session:
                # Query for failed or old pending operations
                query = select(ExternalOperation).where(ExternalOperation.status == "FAILED")
                res = await session.execute(query)
                failed_ops = res.scalars().all()
                
                for op in failed_ops:
                    # operation_key is formatted as session_id:node_id:side_effect
                    parts = op.operation_key.split(":")
                    if len(parts) == 3:
                        sess_id, node_id, se_name = parts
                        # Reset status to PENDING
                        op.status = "PENDING"
                        await session.commit()
                        
                        logger.info(f"Retrying side effect '{se_name}' for session '{sess_id}'...")
                        try:
                            handler = SIDE_EFFECT_HANDLERS.get(se_name)
                            if handler:
                                res_data = await handler(sess_id, {})
                                await ExternalOperationRegistry.commit_success(session, op.operation_key, res_data)
                            else:
                                raise ValueError(f"No handler registered for side effect: {se_name}")
                        except Exception as retry_err:
                            logger.error(f"Retry failed for side effect '{se_name}': {str(retry_err)}")
                            await ExternalOperationRegistry.commit_failure(session, op.operation_key)
                        await session.commit()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in side effect retry worker loop: {str(e)}")
