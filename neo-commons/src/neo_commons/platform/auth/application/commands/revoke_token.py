"""Token revocation command."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable, List
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import AccessToken, RefreshToken, SessionId, RealmIdentifier
from ...core.exceptions import AuthenticationFailed, InvalidSignature


@dataclass
class RevokeTokenRequest:
    """Request to revoke tokens."""
    
    # Token information (at least one required)
    access_token: Optional[AccessToken] = None
    refresh_token: Optional[RefreshToken] = None
    
    # Target information (may be extracted from tokens)
    user_id: Optional[UserId] = None
    tenant_id: Optional[TenantId] = None
    session_id: Optional[SessionId] = None
    
    # Revocation context
    revocation_reason: str = "user_request"  # user_request, security, admin_action, expiration
    revoke_all_user_tokens: bool = False
    revoke_all_sessions: bool = False
    
    # Security context
    revoked_by_admin: bool = False
    security_incident: bool = False


@dataclass
class RevokeTokenResponse:
    """Response from token revocation."""
    
    user_id: UserId
    tokens_revoked: int
    sessions_affected: int
    revocation_successful: bool
    revocation_timestamp: datetime


@runtime_checkable
class TokenIntrospector(Protocol):
    """Protocol for token introspection operations."""
    
    async def introspect_token(
        self, 
        token: AccessToken | RefreshToken
    ) -> dict:
        """Introspect token to extract user and session information."""
        ...


@runtime_checkable
class TokenRevoker(Protocol):
    """Protocol for token revocation operations."""
    
    async def revoke_token(
        self,
        token: AccessToken | RefreshToken,
        reason: str = "user_request"
    ) -> bool:
        """Revoke a specific token."""
        ...
    
    async def revoke_user_tokens(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        reason: str = "user_request"
    ) -> int:
        """Revoke all tokens for a user."""
        ...


@runtime_checkable
class SessionRevoker(Protocol):
    """Protocol for session revocation operations."""
    
    async def revoke_sessions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        session_id: Optional[SessionId] = None,
        revoke_all: bool = False
    ) -> int:
        """Revoke sessions and return count of affected sessions."""
        ...


@runtime_checkable
class CacheInvalidator(Protocol):
    """Protocol for cache invalidation operations."""
    
    async def invalidate_token_cache(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> bool:
        """Invalidate token cache for a user."""
        ...


class RevokeToken:
    """Command to revoke tokens following maximum separation principle.
    
    Handles ONLY token revocation workflow orchestration.
    Does not handle token validation, storage, or cache implementation.
    """
    
    def __init__(
        self,
        token_introspector: TokenIntrospector,
        token_revoker: TokenRevoker,
        session_revoker: SessionRevoker,
        cache_invalidator: CacheInvalidator
    ):
        """Initialize command with protocol dependencies."""
        self._token_introspector = token_introspector
        self._token_revoker = token_revoker
        self._session_revoker = session_revoker
        self._cache_invalidator = cache_invalidator
    
    async def execute(self, request: RevokeTokenRequest) -> RevokeTokenResponse:
        """Execute token revocation command.
        
        Args:
            request: Token revocation request with tokens and options
            
        Returns:
            Token revocation response with statistics
            
        Raises:
            AuthenticationFailed: When revocation fails for critical reasons
        """
        revocation_timestamp = datetime.now(timezone.utc)
        
        try:
            # Step 1: Determine user ID if not provided
            user_id = request.user_id
            if not user_id:
                user_id = await self._extract_user_id_from_tokens(request)
                if not user_id:
                    raise AuthenticationFailed(
                        "Cannot revoke tokens: no user identifier available",
                        reason="missing_user_id",
                        context={"revocation_reason": request.revocation_reason}
                    )
            
            # Step 2: Revoke tokens based on request scope
            tokens_revoked = 0
            
            if request.revoke_all_user_tokens:
                # Revoke all user tokens
                tokens_revoked = await self._token_revoker.revoke_user_tokens(
                    user_id=user_id,
                    tenant_id=request.tenant_id,
                    reason=request.revocation_reason
                )
            else:
                # Revoke specific tokens
                if request.access_token:
                    success = await self._token_revoker.revoke_token(
                        token=request.access_token,
                        reason=request.revocation_reason
                    )
                    if success:
                        tokens_revoked += 1
                
                if request.refresh_token:
                    success = await self._token_revoker.revoke_token(
                        token=request.refresh_token,
                        reason=request.revocation_reason
                    )
                    if success:
                        tokens_revoked += 1
            
            # Step 3: Revoke sessions if requested
            sessions_affected = 0
            if request.revoke_all_sessions:
                sessions_affected = await self._session_revoker.revoke_sessions(
                    user_id=user_id,
                    tenant_id=request.tenant_id,
                    session_id=request.session_id,
                    revoke_all=True
                )
            elif request.session_id:
                sessions_affected = await self._session_revoker.revoke_sessions(
                    user_id=user_id,
                    tenant_id=request.tenant_id,
                    session_id=request.session_id,
                    revoke_all=False
                )
            
            # Step 4: Invalidate token cache
            cache_invalidated = await self._cache_invalidator.invalidate_token_cache(
                user_id=user_id,
                tenant_id=request.tenant_id
            )
            
            # Step 5: Determine success
            revocation_successful = (
                tokens_revoked > 0 or 
                sessions_affected > 0 or 
                cache_invalidated
            )
            
            # Step 6: Return revocation response
            return RevokeTokenResponse(
                user_id=user_id,
                tokens_revoked=tokens_revoked,
                sessions_affected=sessions_affected,
                revocation_successful=revocation_successful,
                revocation_timestamp=revocation_timestamp
            )
            
        except Exception as e:
            # For security operations like revocation, we generally want to succeed
            # even if some operations fail, but log the failures
            
            raise AuthenticationFailed(
                "Token revocation process failed",
                reason="revocation_error",
                context={
                    "user_id": str(user_id.value) if user_id else None,
                    "revocation_reason": request.revocation_reason,
                    "error": str(e)
                }
            ) from e
    
    async def _extract_user_id_from_tokens(self, request: RevokeTokenRequest) -> Optional[UserId]:
        """Extract user ID from provided tokens.
        
        Args:
            request: Revocation request with tokens
            
        Returns:
            User ID if extractable, None otherwise
        """
        # Try access token first
        if request.access_token:
            try:
                token_info = await self._token_introspector.introspect_token(request.access_token)
                subject = token_info.get('sub') or token_info.get('user_id')
                if subject:
                    return UserId(subject)
            except Exception:
                pass  # Try next token
        
        # Try refresh token
        if request.refresh_token:
            try:
                token_info = await self._token_introspector.introspect_token(request.refresh_token)
                subject = token_info.get('sub') or token_info.get('user_id')
                if subject:
                    return UserId(subject)
            except Exception:
                pass  # Unable to extract
        
        return None