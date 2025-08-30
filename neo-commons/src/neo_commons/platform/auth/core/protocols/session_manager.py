"""Session management protocol contract."""

from datetime import datetime
from typing import Protocol, runtime_checkable, Optional, Dict, Any
from ....core.value_objects.identifiers import UserId
from ..value_objects import SessionId


@runtime_checkable
class SessionManager(Protocol):
    """Protocol for session lifecycle management.
    
    Defines ONLY the contract for session operations.
    Implementations handle specific session storage (Redis, database, memory, etc.).
    """
    
    async def create_session(
        self,
        user_id: UserId,
        session_data: Dict[str, Any],
        expires_at: Optional[datetime] = None
    ) -> SessionId:
        """Create a new user session.
        
        Args:
            user_id: User identifier for the session
            session_data: Session data to store
            expires_at: Optional expiration timestamp
            
        Returns:
            Generated session identifier
            
        Raises:
            SessionInvalid: If session cannot be created
        """
        ...
    
    async def get_session(self, session_id: SessionId) -> Dict[str, Any]:
        """Retrieve session data.
        
        Args:
            session_id: Session identifier to retrieve
            
        Returns:
            Session data dictionary
            
        Raises:
            SessionInvalid: If session is invalid or expired
        """
        ...
    
    async def update_session(
        self,
        session_id: SessionId,
        session_data: Dict[str, Any],
        extend_expiry: bool = True
    ) -> None:
        """Update session data.
        
        Args:
            session_id: Session identifier to update
            session_data: New session data
            extend_expiry: Whether to extend session expiration
            
        Raises:
            SessionInvalid: If session is invalid or expired
        """
        ...
    
    async def invalidate_session(self, session_id: SessionId) -> None:
        """Invalidate a specific session.
        
        Args:
            session_id: Session identifier to invalidate
            
        Raises:
            SessionInvalid: If session is already invalid
        """
        ...
    
    async def invalidate_user_sessions(self, user_id: UserId) -> int:
        """Invalidate all sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of sessions invalidated
        """
        ...
    
    async def is_session_valid(self, session_id: SessionId) -> bool:
        """Check if session is valid without retrieving data.
        
        Args:
            session_id: Session identifier to check
            
        Returns:
            True if session is valid, False otherwise
        """
        ...
    
    async def refresh_session(
        self,
        session_id: SessionId,
        extend_by_seconds: Optional[int] = None
    ) -> datetime:
        """Refresh session expiration.
        
        Args:
            session_id: Session identifier to refresh
            extend_by_seconds: Seconds to extend (uses default if None)
            
        Returns:
            New expiration timestamp
            
        Raises:
            SessionInvalid: If session is invalid
        """
        ...
    
    async def get_session_metadata(self, session_id: SessionId) -> Dict[str, Any]:
        """Get session metadata without full data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session metadata (created_at, expires_at, user_id, etc.)
            
        Raises:
            SessionInvalid: If session is invalid
        """
        ...
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        ...