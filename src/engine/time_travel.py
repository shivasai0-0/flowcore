from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import Session as SessionModel, ExecutionSnapshot, ExecutionJournal, ExecutionLog

class SnapshotNotFoundError(ValueError):
    """Raised when the specified snapshot does not exist or belong to the session."""
    pass

class TimeTravelEngine:
    @staticmethod
    async def rollback_session_to_snapshot(
        db_session: AsyncSession,
        session_id: str,
        snapshot_id: str
    ) -> SessionModel:
        """
        Reverts the session state (FSM state, carry unit, current node) to a specific snapshot point.
        Truncates downstream journals, execution logs, and snapshots created after this snapshot timestamp.
        """
        # 1. Load the snapshot
        snap_query = select(ExecutionSnapshot).where(
            ExecutionSnapshot.id == snapshot_id,
            ExecutionSnapshot.session_id == session_id
        )
        snap_res = await db_session.execute(snap_query)
        snapshot = snap_res.scalar_one_or_none()

        if not snapshot:
            raise SnapshotNotFoundError(f"Snapshot with ID '{snapshot_id}' not found for session '{session_id}'.")

        # 2. Load the session
        sess_query = select(SessionModel).where(SessionModel.id == session_id)
        sess_res = await db_session.execute(sess_query)
        session_record = sess_res.scalar_one_or_none()
        if not session_record:
            raise ValueError(f"Session with ID '{session_id}' not found.")

        snapshot_time = snapshot.timestamp

        # 3. Truncate downstream records created strictly after the snapshot timestamp
        # Truncate execution logs
        log_delete_query = delete(ExecutionLog).where(
            ExecutionLog.session_id == session_id,
            ExecutionLog.executed_at > snapshot_time
        )
        await db_session.execute(log_delete_query)

        # Truncate execution journals
        journal_delete_query = delete(ExecutionJournal).where(
            ExecutionJournal.session_id == session_id,
            ExecutionJournal.timestamp > snapshot_time
        )
        await db_session.execute(journal_delete_query)

        # Truncate execution snapshots
        snap_delete_query = delete(ExecutionSnapshot).where(
            ExecutionSnapshot.session_id == session_id,
            ExecutionSnapshot.timestamp > snapshot_time
        )
        await db_session.execute(snap_delete_query)

        # 4. Revert session state
        session_record.fsm_state = snapshot.fsm_state
        session_record.current_node_id = snapshot.node_id
        session_record.carry_unit_json = snapshot.carry_unit_json

        await db_session.flush()
        return session_record
