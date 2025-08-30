"""Session invalidation command."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, List
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import SessionId, RealmIdentifier
from ...core.entities import AuthSession
from ...core.events import SessionExpired
from ...core.exceptions import SessionInvalid, AuthenticationFailed


@dataclass
class InvalidateSessionRequest:
    """Request to invalidate sessions."""
    
    # Target information
    user_id: UserId
    tenant_id: Optional[TenantId] = None
    session_id: Optional[SessionId] = None
    
    # Invalidation scope
    invalidate_all_sessions: bool = False
    invalidate_related_sessions: bool = True
    
    # Invalidation context
    invalidation_reason: str = "user_request"  # user_request, security, expiration, admin_action
    invalidation_type: str = "manual"  # manual, automatic, security
    
    # Security context
    forced_invalidation: bool = False
    security_incident: bool = False


@dataclass
class InvalidateSessionResponse:
    """Response from session invalidation."""
    
    user_id: UserId
    sessions_invalidated: int
    tokens_invalidated: int
    cache_cleared: bool
    events_published: List[SessionExpired]


@runtime_checkable
class SessionProvider(Protocol):
    """Protocol for session operations."""
    
    async def get_user_sessions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        active_only: bool = True
    ) -> List[AuthSession]:
        """Get user sessions."""
        ...
    
    async def get_session(
        self,
        session_id: SessionId,
        user_id: Optional[UserId] = None
    ) -> Optional[AuthSession]:
        """Get specific session."""
        ...
    
    async def invalidate_session(
        self,
        session_id: SessionId,
        reason: str = "user_request"
    ) -> bool:
        """Invalidate specific session."""
        ...
    
    async def invalidate_user_sessions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        exclude_session: Optional[SessionId] = None
    ) -> int:
        """Invalidate all user sessions and return count."""
        ...


@runtime_checkable
class TokenInvalidator(Protocol):
    """Protocol for token invalidation operations."""
    
    async def invalidate_session_tokens(
        self,
        session_id: SessionId,
        user_id: UserId
    ) -> int:
        """Invalidate tokens associated with session."""
        ...


@runtime_checkable
class CacheCleaner(Protocol):
    """Protocol for cache cleanup operations."""
    
    async def clear_session_cache(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        session_id: Optional[SessionId] = None
    ) -> bool:
        """Clear session-related cache data."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishing."""
    
    async def publish(self, event: SessionExpired) -> None:
        """Publish session expired event."""
        ...


class InvalidateSession:
    """Command to invalidate sessions following maximum separation principle.
    
    Handles ONLY session invalidation workflow orchestration.
    Does not handle session storage, token management, or cache implementation.
    """
    
    def __init__(
        self,
        session_provider: SessionProvider,
        token_invalidator: TokenInvalidator,
        cache_cleaner: CacheCleaner,
        event_publisher: EventPublisher
    ):
        """Initialize command with protocol dependencies."""
        self._session_provider = session_provider
        self._token_invalidator = token_invalidator
        self._cache_cleaner = cache_cleaner
        self._event_publisher = event_publisher
    
    async def execute(self, request: InvalidateSessionRequest) -> InvalidateSessionResponse:
        """Execute session invalidation command.
        
        Args:
            request: Session invalidation request with scope and options
            
        Returns:
            Session invalidation response with statistics
            
        Raises:
            SessionInvalid: When session is not found or already invalid
            AuthenticationFailed: When invalidation fails for critical reasons
        """
        try:
            sessions_to_invalidate: List[AuthSession] = []
            
            # Step 1: Determine sessions to invalidate
            if request.session_id and not request.invalidate_all_sessions:
                # Invalidate specific session
                session = await self._session_provider.get_session(
                    session_id=request.session_id,
                    user_id=request.user_id
                )
                if session:
                    sessions_to_invalidate.append(session)
                elif not request.forced_invalidation:
                    raise SessionInvalid(
                        "Session not found or already invalid",
                        session_id=str(request.session_id.value),
                        user_id=str(request.user_id.value)
                    )
            else:
                # Invalidate all user sessions
                user_sessions = await self._session_provider.get_user_sessions(
                    user_id=request.user_id,
                    tenant_id=request.tenant_id,
                    active_only=True
                )
                sessions_to_invalidate.extend(user_sessions)
            
            # Step 2: Invalidate sessions and collect statistics
            sessions_invalidated = 0
            tokens_invalidated = 0
            events_published: List[SessionExpired] = []
            
            for session in sessions_to_invalidate:
                try:
                    # Invalidate the session
                    success = await self._session_provider.invalidate_session(
                        session_id=session.session_id,
                        reason=request.invalidation_reason
                    )
                    
                    if success:
                        sessions_invalidated += 1
                        
                        # Invalidate associated tokens
                        session_tokens = await self._token_invalidator.invalidate_session_tokens(
                            session_id=session.session_id,
                            user_id=request.user_id
                        )
                        tokens_invalidated += session_tokens
                        
                        # Create session expired event
                        event = self._create_session_expired_event(session, request)
                        events_published.append(event)
                        
                        # Publish event
                        await self._event_publisher.publish(event)
                        
                except Exception as e:
                    # Log error but continue with other sessions
                    # For security operations, partial success is acceptable
                    pass
            
            # Step 3: Clear cache
            cache_cleared = await self._cache_cleaner.clear_session_cache(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                session_id=request.session_id
            )
            
            # Step 4: Return invalidation response
            return InvalidateSessionResponse(
                user_id=request.user_id,
                sessions_invalidated=sessions_invalidated,
                tokens_invalidated=tokens_invalidated,
                cache_cleared=cache_cleared,
                events_published=events_published
            )
            
        except SessionInvalid:
            # Re-raise session-specific exceptions as-is
            raise
        except Exception as e:
            # Wrap other exceptions in authentication failure
            raise AuthenticationFailed(
                "Session invalidation process failed",
                reason="invalidation_error",
                context={
                    "user_id": str(request.user_id.value),
                    "session_id": str(request.session_id.value) if request.session_id else None,
                    "invalidation_reason": request.invalidation_reason,
                    "error": str(e)
                }
            ) from e
    
    def _create_session_expired_event(
        self, 
        session: AuthSession, 
        request: InvalidateSessionRequest
    ) -> SessionExpired:
        """Create session expired event for invalidated session.
        
        Args:
            session: Session being invalidated
            request: Invalidation request
            
        Returns:
            Session expired event
        """
        # Calculate session duration
        session_duration = None
        if session.created_at:
            duration = datetime.now(timezone.utc) - session.created_at
            session_duration = int(duration.total_seconds())
        
        # Calculate idle duration
        idle_duration = None
        if session.last_activity_at:
            idle_time = datetime.now(timezone.utc) - session.last_activity_at
            idle_duration = int(idle_time.total_seconds())
        
        # Determine expiration type
        expiration_type = "manual" if request.invalidation_type == "manual" else "security"
        if request.security_incident or request.forced_invalidation:
            expiration_type = "security"
        
        return SessionExpired(
            user_id=session.user_id,
            tenant_id=session.tenant_id,
            session_id=session.session_id,
            expiration_reason=request.invalidation_reason,
            expiration_type=expiration_type,
            session_created_at=session.created_at,
            session_last_activity_at=session.last_activity_at,
            session_duration_seconds=session_duration,
            idle_duration_seconds=idle_duration,
            tokens_invalidated=True,
            cache_cleared=True,
            event_timestamp=datetime.now(timezone.utc)
        )