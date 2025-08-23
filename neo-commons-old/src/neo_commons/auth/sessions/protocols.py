"""
Session Management Protocols for Neo-Commons

Protocol definitions for session management operations including
guest authentication, session caching, and session lifecycle management.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class GuestAuthServiceProtocol(Protocol):
    """Protocol for guest authentication service."""
    
    async def create_guest_session(
        self,
        session_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new guest session."""
        ...
    
    async def get_guest_session(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get guest session by ID."""
        ...
    
    async def update_guest_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update guest session data."""
        ...
    
    async def delete_guest_session(
        self,
        session_id: str
    ) -> bool:
        """Delete guest session."""
        ...


@runtime_checkable
class SessionCacheServiceProtocol(Protocol):
    """Protocol for session-specific cache service operations."""
    
    async def get_session(
        self, 
        session_id: str, 
        session_type: str = "guest"
    ) -> Optional[Dict[str, Any]]:
        """Get session data by ID and type."""
        ...
    
    async def set_session(
        self, 
        session_id: str, 
        session_data: Dict[str, Any], 
        ttl: Optional[int] = None,
        session_type: str = "guest"
    ) -> None:
        """Store session data with TTL."""
        ...
    
    async def delete_session(
        self, 
        session_id: str, 
        session_type: str = "guest"
    ) -> None:
        """Delete session data."""
        ...
    
    async def extend_session_ttl(
        self, 
        session_id: str, 
        extension_seconds: int,
        session_type: str = "guest"
    ) -> bool:
        """Extend session TTL."""
        ...
    
    async def get_session_stats(self) -> Dict[str, Any]:
        """Get session cache statistics."""
        ...


@runtime_checkable
class SessionValidatorProtocol(Protocol):
    """Protocol for session validation operations."""
    
    async def validate_session(
        self,
        session_token: str,
        session_type: str = "guest"
    ) -> Optional[Dict[str, Any]]:
        """Validate session token and return session data if valid."""
        ...
    
    async def is_session_expired(
        self,
        session_data: Dict[str, Any]
    ) -> bool:
        """Check if session has expired."""
        ...
    
    async def refresh_session(
        self,
        session_token: str,
        extension_seconds: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Refresh session and extend expiration."""
        ...


@runtime_checkable
class SessionManagerProtocol(Protocol):
    """Protocol for high-level session management operations."""
    
    async def create_session(
        self,
        user_id: Optional[str] = None,
        session_type: str = "guest",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new session of specified type."""
        ...
    
    async def get_session_by_token(
        self,
        session_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get session by token regardless of type."""
        ...
    
    async def invalidate_session(
        self,
        session_token: str
    ) -> bool:
        """Invalidate a session by token."""
        ...
    
    async def invalidate_all_user_sessions(
        self,
        user_id: str
    ) -> int:
        """Invalidate all sessions for a user."""
        ...
    
    async def get_active_sessions(
        self,
        user_id: Optional[str] = None,
        session_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get active sessions with optional filtering."""
        ...


@runtime_checkable
class SessionAuditProtocol(Protocol):
    """Protocol for session audit and logging operations."""
    
    async def log_session_creation(
        self,
        session_id: str,
        user_id: Optional[str],
        session_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log session creation event."""
        ...
    
    async def log_session_activity(
        self,
        session_id: str,
        activity_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log session activity event."""
        ...
    
    async def log_session_termination(
        self,
        session_id: str,
        termination_reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log session termination event."""
        ...
    
    async def get_session_audit_trail(
        self,
        session_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get audit trail for a session."""
        ...


@runtime_checkable
class SessionCleanupProtocol(Protocol):
    """Protocol for session cleanup and maintenance operations."""
    
    async def cleanup_expired_sessions(
        self,
        session_type: Optional[str] = None
    ) -> int:
        """Clean up expired sessions."""
        ...
    
    async def cleanup_orphaned_sessions(
        self,
        session_type: Optional[str] = None
    ) -> int:
        """Clean up orphaned sessions (sessions without valid users)."""
        ...
    
    async def get_session_statistics(
        self,
        session_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get session usage statistics."""
        ...
    
    async def schedule_cleanup_task(
        self,
        interval_seconds: int = 3600
    ) -> bool:
        """Schedule periodic cleanup task."""
        ...


@runtime_checkable
class SessionSecurityProtocol(Protocol):
    """Protocol for session security operations."""
    
    async def validate_session_origin(
        self,
        session_token: str,
        ip_address: str,
        user_agent: Optional[str] = None
    ) -> bool:
        """Validate session request origin for security."""
        ...
    
    async def detect_session_hijacking(
        self,
        session_token: str,
        request_metadata: Dict[str, Any]
    ) -> bool:
        """Detect potential session hijacking attempts."""
        ...
    
    async def enforce_session_limits(
        self,
        user_id: str,
        session_type: str = "authenticated"
    ) -> bool:
        """Enforce concurrent session limits for users."""
        ...
    
    async def rotate_session_token(
        self,
        current_token: str
    ) -> Optional[str]:
        """Rotate session token for security."""
        ...


@runtime_checkable
class SessionMetricsProtocol(Protocol):
    """Protocol for session metrics and monitoring."""
    
    async def record_session_metric(
        self,
        metric_name: str,
        metric_value: float,
        session_type: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a session-related metric."""
        ...
    
    async def get_session_metrics(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        session_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get session metrics for a time period."""
        ...
    
    async def get_real_time_session_count(
        self,
        session_type: Optional[str] = None
    ) -> int:
        """Get current count of active sessions."""
        ...


__all__ = [
    "GuestAuthServiceProtocol",
    "SessionCacheServiceProtocol",
    "SessionValidatorProtocol",
    "SessionManagerProtocol",
    "SessionAuditProtocol",
    "SessionCleanupProtocol",
    "SessionSecurityProtocol",
    "SessionMetricsProtocol",
]