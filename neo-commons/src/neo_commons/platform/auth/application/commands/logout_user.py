"""User logout command."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, List
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import SessionId, RefreshToken, RealmIdentifier
from ...core.events import UserLoggedOut
from ...core.exceptions import AuthenticationFailed


@dataclass
class LogoutUserRequest:
    """Request to logout a user."""
    
    user_id: UserId
    tenant_id: Optional[TenantId] = None
    session_id: Optional[SessionId] = None
    refresh_token: Optional[RefreshToken] = None
    
    # Logout context
    logout_reason: str = "user_initiated"  # user_initiated, expired, revoked, admin_action
    logout_method: str = "manual"  # manual, automatic, forced
    
    # Security context
    force_logout: bool = False
    invalidate_all_sessions: bool = False
    revoked_by_admin: bool = False


@dataclass
class LogoutUserResponse:
    """Response from user logout."""
    
    user_id: UserId
    sessions_invalidated: int
    tokens_revoked: int
    cache_cleared: bool
    event: UserLoggedOut


@runtime_checkable
class TokenRevoker(Protocol):
    """Protocol for token revocation operations."""
    
    async def revoke_user_tokens(
        self, 
        user_id: UserId, 
        tenant_id: Optional[TenantId] = None,
        refresh_token: Optional[RefreshToken] = None
    ) -> int:
        """Revoke all tokens for a user and return count of revoked tokens."""
        ...


@runtime_checkable
class SessionInvalidator(Protocol):
    """Protocol for session invalidation operations."""
    
    async def invalidate_user_sessions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        session_id: Optional[SessionId] = None,
        invalidate_all: bool = False
    ) -> tuple[int, Optional[datetime], Optional[int]]:
        """Invalidate user sessions and return (count, last_activity, duration_seconds)."""
        ...


@runtime_checkable
class CacheCleaner(Protocol):
    """Protocol for cache cleanup operations."""
    
    async def clear_user_cache(
        self, 
        user_id: UserId, 
        tenant_id: Optional[TenantId] = None
    ) -> bool:
        """Clear all cached data for a user."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishing."""
    
    async def publish(self, event: UserLoggedOut) -> None:
        """Publish logout event."""
        ...


class LogoutUser:
    """Command to logout user following maximum separation principle.
    
    Handles ONLY user logout workflow orchestration.
    Does not handle token validation, session loading, or cache implementation.
    """
    
    def __init__(
        self,
        token_revoker: TokenRevoker,
        session_invalidator: SessionInvalidator,
        cache_cleaner: CacheCleaner,
        event_publisher: EventPublisher
    ):
        """Initialize command with protocol dependencies."""
        self._token_revoker = token_revoker
        self._session_invalidator = session_invalidator
        self._cache_cleaner = cache_cleaner
        self._event_publisher = event_publisher
    
    async def execute(self, request: LogoutUserRequest) -> LogoutUserResponse:
        """Execute user logout command.
        
        Args:
            request: Logout request with user information and options
            
        Returns:
            Logout response with cleanup statistics
            
        Raises:
            AuthenticationFailed: When logout fails for critical reasons
        """
        try:
            # Step 1: Invalidate user sessions
            sessions_invalidated, last_activity_at, session_duration_seconds = (
                await self._session_invalidator.invalidate_user_sessions(
                    user_id=request.user_id,
                    tenant_id=request.tenant_id,
                    session_id=request.session_id,
                    invalidate_all=request.invalidate_all_sessions
                )
            )
            
            # Step 2: Revoke user tokens
            tokens_revoked = await self._token_revoker.revoke_user_tokens(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                refresh_token=request.refresh_token
            )
            
            # Step 3: Clear user cache
            cache_cleared = await self._cache_cleaner.clear_user_cache(
                user_id=request.user_id,
                tenant_id=request.tenant_id
            )
            
            # Step 4: Determine security context
            is_security_logout = self._is_security_logout(request)
            
            # Step 5: Create logout event
            event = UserLoggedOut(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                logout_reason=request.logout_reason,
                logout_method=request.logout_method,
                session_duration_seconds=session_duration_seconds,
                last_activity_at=last_activity_at,
                was_forced=request.force_logout,
                revoked_by_admin=request.revoked_by_admin,
                security_incident=is_security_logout,
                tokens_revoked=tokens_revoked > 0,
                cache_cleared=cache_cleared,
                sessions_invalidated=sessions_invalidated,
                event_timestamp=datetime.now(timezone.utc)
            )
            
            # Step 6: Publish logout event
            await self._event_publisher.publish(event)
            
            # Step 7: Return logout response
            return LogoutUserResponse(
                user_id=request.user_id,
                sessions_invalidated=sessions_invalidated,
                tokens_revoked=tokens_revoked,
                cache_cleared=cache_cleared,
                event=event
            )
            
        except Exception as e:
            # For logout, we generally don't want to fail completely
            # Log the error but continue with partial cleanup
            
            # Create a failure event for security monitoring
            event = UserLoggedOut(
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                logout_reason="logout_error",
                logout_method=request.logout_method,
                was_forced=request.force_logout,
                revoked_by_admin=request.revoked_by_admin,
                security_incident=True,
                tokens_revoked=False,
                cache_cleared=False,
                sessions_invalidated=0,
                event_timestamp=datetime.now(timezone.utc),
                metadata={"error": str(e)}
            )
            
            # Publish failure event (best effort)
            try:
                await self._event_publisher.publish(event)
            except:
                pass  # Don't fail on event publishing failure
            
            # Return partial response instead of failing
            return LogoutUserResponse(
                user_id=request.user_id,
                sessions_invalidated=0,
                tokens_revoked=0,
                cache_cleared=False,
                event=event
            )
    
    def _is_security_logout(self, request: LogoutUserRequest) -> bool:
        """Determine if logout is security-related.
        
        Args:
            request: Logout request
            
        Returns:
            True if logout is due to security reasons
        """
        return (
            request.force_logout or
            request.revoked_by_admin or
            request.logout_reason in [
                "security", "suspicious_activity", "breach", 
                "admin_action", "forced", "compliance"
            ]
        )