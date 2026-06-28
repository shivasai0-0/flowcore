import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.models import Business

logger = logging.getLogger("flowcore.dev_workspace")

async def apply_dev_workspace_branding(db: AsyncSession, business_id: str, message: str) -> str:
    """
    If DEVELOPMENT_WORKSPACE_MODE is enabled, prefixes the message with the business name.
    Example: "[Pizza Planet]\n\nYour order has been confirmed."
    """
    if not settings.DEVELOPMENT_WORKSPACE_MODE:
        return message

    try:
        # Fetch business name
        query = select(Business).where(Business.id == business_id)
        res = await db.execute(query)
        business = res.scalar_one_or_none()
        if business:
            return f"[{business.name}] {message}"
    except Exception as e:
        logger.error(f"Failed to apply dev workspace branding: {str(e)}")
        
    return message
