import json
import logging
from typing import List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import WorkflowVersion

logger = logging.getLogger("flowcore.workflow_registry")

class WorkflowRegistry:
    @staticmethod
    async def get_portfolio(db_session: AsyncSession, business_id: str) -> List[Dict[str, Any]]:
        """
        Queries active database workflow versions for a business to build its active portfolio.
        Returns a list of metadata dictionaries containing active workflow profiles.
        """
        query = select(WorkflowVersion).where(
            WorkflowVersion.business_id == business_id,
            WorkflowVersion.status == "ACTIVE"
        )
        res = await db_session.execute(query)
        active_versions = res.scalars().all()
        
        portfolio = []
        for wv in active_versions:
            try:
                graph = json.loads(wv.graph_json)
                portfolio.append({
                    "workflow_version_id": wv.id,
                    "workflow_type": wv.workflow_type,
                    "version_number": wv.version_number,
                    "entry_node_id": graph.get("entry_node_id"),
                    "name": graph.get("name", f"workflow_v{wv.version_number}"),
                    "nodes_count": len(graph.get("nodes", {})),
                    "is_current": wv.is_current
                })
            except Exception as e:
                logger.error(f"Failed to parse active workflow graph for portfolio version {wv.id}: {str(e)}")
                
        return portfolio
