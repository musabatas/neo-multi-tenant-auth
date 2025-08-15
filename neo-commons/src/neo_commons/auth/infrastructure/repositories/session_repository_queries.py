"""
Session repository SQL queries and utilities.

Provides SQL queries and helper functions for session management.
"""
from typing import Dict, Any
from ...domain.entities.session import Session, SessionStatus


class SessionQueries:
    """SQL queries for session operations with configurable schemas."""
    
    def __init__(self, admin_schema: str = "admin"):
        """
        Initialize session queries with configurable schema.
        
        Args:
            admin_schema: Schema name for admin/platform tables (default: admin)
        """
        self.admin_schema = admin_schema
    
    @property
    def STORE_SESSION(self) -> str:
        return f"""
            INSERT INTO {self.admin_schema}.user_sessions 
            (id, user_id, tenant_id, status, created_at, expires_at, ip_address, user_agent, metadata)
            VALUES ($1, $2, $3, $4, NOW(), to_timestamp($5), $6, $7, $8)
            ON CONFLICT (id) 
            DO UPDATE SET 
                status = EXCLUDED.status,
                expires_at = EXCLUDED.expires_at,
                ip_address = EXCLUDED.ip_address,
                user_agent = EXCLUDED.user_agent,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """
    
    @property
    def GET_SESSION(self) -> str:
        return f"""
            SELECT id, user_id, tenant_id, status, created_at, expires_at,
                   ip_address, user_agent, metadata, updated_at
            FROM {self.admin_schema}.user_sessions
            WHERE id = $1 AND user_id = $2
        """
    
    @property
    def UPDATE_SESSION_STATUS(self) -> str:
        return f"""
            UPDATE {self.admin_schema}.user_sessions 
            SET status = $3, updated_at = NOW()
            WHERE id = $1 AND user_id = $2
        """
    
    @property
    def GET_SESSION_BY_ID(self) -> str:
        return f"""
            SELECT id, user_id, tenant_id, status, created_at, expires_at,
                   ip_address, user_agent, metadata, updated_at
            FROM {self.admin_schema}.user_sessions
            WHERE id = $1
        """
    
    @property
    def GET_USER_SESSIONS(self) -> str:
        return f"""
            SELECT id, user_id, tenant_id, status, created_at, expires_at,
                   ip_address, user_agent, metadata, updated_at
            FROM {self.admin_schema}.user_sessions
            WHERE user_id = $1 AND status = 'active'
            ORDER BY created_at DESC
        """
    
    @property
    def GET_ACTIVE_SESSIONS(self) -> str:
        return f"""
            SELECT id, user_id, tenant_id, status, created_at, expires_at,
                   ip_address, user_agent, metadata, updated_at
            FROM {self.admin_schema}.user_sessions
            WHERE status = 'active' AND expires_at > NOW()
            ORDER BY created_at DESC
        """
    
    @property
    def EXPIRE_SESSION(self) -> str:
        return f"""
            UPDATE {self.admin_schema}.user_sessions 
            SET status = 'expired', updated_at = NOW()
            WHERE id = $1
        """
    
    @property
    def INVALIDATE_SESSION(self) -> str:
        return f"""
            UPDATE {self.admin_schema}.user_sessions 
            SET status = 'invalidated', updated_at = NOW()
            WHERE id = $1
        """
    
    @property
    def REVOKE_SESSION(self) -> str:
        return f"""
            UPDATE {self.admin_schema}.user_sessions 
            SET status = 'revoked', updated_at = NOW()
            WHERE id = $1
        """
    
    @property
    def CLEANUP_EXPIRED_SESSIONS(self) -> str:
        return f"""
            UPDATE {self.admin_schema}.user_sessions 
            SET status = 'expired', updated_at = NOW()
            WHERE expires_at <= NOW() AND status = 'active'
        """
    
    @property
    def DELETE_OLD_SESSIONS(self) -> str:
        return f"""
            DELETE FROM {self.admin_schema}.user_sessions 
            WHERE updated_at < NOW() - INTERVAL '90 days'
        """
    
    @property
    def EXTEND_SESSION(self) -> str:
        return f"""
            UPDATE {self.admin_schema}.user_sessions 
            SET expires_at = to_timestamp($2), updated_at = NOW()
            WHERE id = $1 AND status = 'active'
        """
    
    @property
    def GET_SESSIONS_BY_CRITERIA(self) -> str:
        return f"""
            SELECT id, user_id, tenant_id, status, created_at, expires_at,
                   ip_address, user_agent, metadata, updated_at
            FROM {self.admin_schema}.user_sessions
            WHERE ($1::text IS NULL OR user_id = $1)
              AND ($2::text IS NULL OR tenant_id = $2)
              AND ($3::text IS NULL OR status = $3)
              AND ($4::timestamp IS NULL OR created_at >= $4)
              AND ($5::timestamp IS NULL OR created_at <= $5)
            ORDER BY created_at DESC
        """


class SessionUtils:
    """Utility functions for session management."""
    
    @staticmethod
    def session_to_params(session: Session) -> tuple:
        """Convert session entity to database parameters."""
        return (
            session.id,
            session.user_id,
            session.tenant_id,
            session.status.value,
            session.expires_at,
            session.ip_address,
            session.user_agent,
            session.metadata
        )
    
    @staticmethod
    def row_to_session(row: Dict[str, Any]) -> Session:
        """Convert database row to session entity."""
        return Session(
            id=row['id'],
            user_id=row['user_id'],
            tenant_id=row['tenant_id'],
            status=SessionStatus(row['status']),
            created_at=row['created_at'].timestamp() if row['created_at'] else None,
            expires_at=row['expires_at'].timestamp() if row['expires_at'] else None,
            ip_address=row['ip_address'],
            user_agent=row['user_agent'],
            metadata=row['metadata'] or {}
        )
    
    @staticmethod
    def extract_update_count(result: str) -> int:
        """Extract count from UPDATE result string."""
        return int(result.split()[-1]) if result.startswith("UPDATE") else 0