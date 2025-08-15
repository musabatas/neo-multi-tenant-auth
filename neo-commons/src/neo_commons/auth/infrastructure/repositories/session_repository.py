"""
Session repository implementation using AsyncPG for session management.

Handles session storage, validation, and cleanup with high performance.
"""
from typing import List, Optional, Dict, Any
import asyncpg
from loguru import logger

from ...domain.entities.session import Session, SessionStatus
from ...domain.protocols.repository_protocols import SessionRepositoryProtocol
from .session_repository_queries import SessionQueries, SessionUtils


class SessionRepository(SessionRepositoryProtocol):
    """
    AsyncPG implementation of session repository for sub-millisecond performance.
    
    Manages user sessions with direct SQL for optimal performance.
    """

    def __init__(self, db_pool: asyncpg.Pool, admin_schema: str = "admin"):
        """
        Initialize session repository with configurable schema.
        
        Args:
            db_pool: AsyncPG connection pool
            admin_schema: Schema name for admin/platform tables (default: admin)
        """
        self._db_pool = db_pool
        self.admin_schema = admin_schema
        self._queries = SessionQueries(admin_schema)
        self._utils = SessionUtils()

    async def store_session(self, session: Session) -> None:
        """Store or update a session."""
        async with self._db_pool.acquire() as conn:
            params = self._utils.session_to_params(session)
            await conn.execute(self._queries.STORE_SESSION, *params)

        logger.debug(
            f"Session stored: {session.id} for user {session.user_id}",
            extra={
                "session_id": session.id,
                "user_id": session.user_id,
                "tenant_id": session.tenant_id,
                "status": session.status.value,
                "expires_at": session.expires_at
            }
        )

    async def get_session(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[Session]:
        """Get a session by ID and user ID."""
        async with self._db_pool.acquire() as conn:
            row = await conn.fetchrow(self._queries.GET_SESSION, session_id, user_id)

        return self._utils.row_to_session(row) if row else None

    async def invalidate_session(
        self,
        session_id: str,
        user_id: str,
        invalidated_by: Optional[str] = None
    ) -> bool:
        """Invalidate a session."""
        async with self._db_pool.acquire() as conn:
            result = await conn.execute(
                self._queries.INVALIDATE_SESSION,
                session_id,
                user_id,
                SessionStatus.INVALIDATED.value,
                invalidated_by,
                SessionStatus.ACTIVE.value
            )

        success = result == "UPDATE 1"
        
        if success:
            logger.info(
                f"Session invalidated: {session_id} for user {user_id}",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "invalidated_by": invalidated_by
                }
            )

        return success

    async def get_user_sessions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Session]:
        """Get all sessions for a user."""
        async with self._db_pool.acquire() as conn:
            if active_only:
                if tenant_id:
                    rows = await conn.fetch(
                        self._queries.GET_USER_SESSIONS_ACTIVE_TENANT,
                        user_id, tenant_id, SessionStatus.ACTIVE.value
                    )
                else:
                    rows = await conn.fetch(
                        self._queries.GET_USER_SESSIONS_ACTIVE,
                        user_id, SessionStatus.ACTIVE.value
                    )
            else:
                if tenant_id:
                    rows = await conn.fetch(
                        self._queries.GET_USER_SESSIONS_ALL_TENANT,
                        user_id, tenant_id
                    )
                else:
                    rows = await conn.fetch(
                        self._queries.GET_USER_SESSIONS_ALL,
                        user_id
                    )

        sessions = [self._utils.row_to_session(row) for row in rows]

        logger.debug(
            f"Retrieved {len(sessions)} sessions for user {user_id}",
            extra={
                "user_id": user_id,
                "tenant_id": tenant_id,
                "active_only": active_only,
                "session_count": len(sessions)
            }
        )

        return sessions

    async def refresh_session(
        self,
        session_id: str,
        user_id: str,
        new_expires_at: Optional[int],
        new_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Refresh session expiry and metadata."""
        async with self._db_pool.acquire() as conn:
            if new_metadata:
                result = await conn.execute(
                    self._queries.REFRESH_SESSION_WITH_METADATA,
                    session_id,
                    user_id,
                    new_expires_at,
                    new_metadata,
                    SessionStatus.ACTIVE.value
                )
            else:
                result = await conn.execute(
                    self._queries.REFRESH_SESSION,
                    session_id,
                    user_id,
                    new_expires_at,
                    SessionStatus.ACTIVE.value
                )

        success = result == "UPDATE 1"
        
        if success:
            logger.debug(
                f"Session refreshed: {session_id} for user {user_id}",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "new_expires_at": new_expires_at
                }
            )

        return success

    async def cleanup_expired_sessions(self, expiry_hours: int = 24) -> int:
        """Clean up expired sessions."""
        async with self._db_pool.acquire() as conn:
            # Use string formatting for INTERVAL since it's not a parameter
            query = self._queries.CLEANUP_EXPIRED_SESSIONS % expiry_hours
            
            result = await conn.execute(
                query,
                SessionStatus.EXPIRED.value,
                SessionStatus.ACTIVE.value
            )

        count = self._utils.extract_update_count(result)
        
        if count > 0:
            logger.info(
                f"Marked {count} sessions as expired",
                extra={"expired_count": count, "expiry_hours": expiry_hours}
            )

        return count

    async def invalidate_user_sessions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        invalidated_by: Optional[str] = None,
        exclude_session_id: Optional[str] = None
    ) -> int:
        """Invalidate all sessions for a user."""
        async with self._db_pool.acquire() as conn:
            if tenant_id:
                if exclude_session_id:
                    result = await conn.execute(
                        self._queries.INVALIDATE_USER_SESSIONS_TENANT_EXCLUDE,
                        user_id,
                        tenant_id,
                        SessionStatus.INVALIDATED.value,
                        invalidated_by,
                        exclude_session_id,
                        SessionStatus.ACTIVE.value
                    )
                else:
                    result = await conn.execute(
                        self._queries.INVALIDATE_USER_SESSIONS_TENANT,
                        user_id,
                        tenant_id,
                        SessionStatus.INVALIDATED.value,
                        invalidated_by,
                        SessionStatus.ACTIVE.value
                    )
            else:
                if exclude_session_id:
                    result = await conn.execute(
                        self._queries.INVALIDATE_USER_SESSIONS_EXCLUDE,
                        user_id,
                        SessionStatus.INVALIDATED.value,
                        invalidated_by,
                        exclude_session_id,
                        SessionStatus.ACTIVE.value
                    )
                else:
                    result = await conn.execute(
                        self._queries.INVALIDATE_USER_SESSIONS,
                        user_id,
                        SessionStatus.INVALIDATED.value,
                        invalidated_by,
                        SessionStatus.ACTIVE.value
                    )

        count = self._utils.extract_update_count(result)
        
        if count > 0:
            logger.info(
                f"Invalidated {count} sessions for user {user_id}",
                extra={
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "invalidated_by": invalidated_by,
                    "exclude_session_id": exclude_session_id,
                    "invalidated_count": count
                }
            )

        return count

    async def get_session_statistics(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get session statistics."""
        async with self._db_pool.acquire() as conn:
            if tenant_id:
                rows = await conn.fetch(self._queries.GET_SESSION_STATS_TENANT, tenant_id)
            else:
                rows = await conn.fetch(self._queries.GET_SESSION_STATS)

        stats = {}
        for row in rows:
            status_name = SessionStatus(row['status']).name.lower()
            stats[status_name] = row['count']

        # Add totals
        stats['total'] = sum(stats.values())

        return stats