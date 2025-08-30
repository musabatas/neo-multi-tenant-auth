"""Token refresh command."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable
from ....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import AccessToken, RefreshToken, SessionId, TokenClaims
from ...core.entities import TokenMetadata
from ...core.events import TokenRefreshed
from ...core.exceptions import TokenExpired, InvalidSignature, AuthenticationFailed


@dataclass
class RefreshTokenRequest:
    """Request to refresh an access token."""
    
    refresh_token: RefreshToken
    user_id: Optional[UserId] = None  # May be extracted from token
    tenant_id: Optional[TenantId] = None
    session_id: Optional[SessionId] = None
    
    # Refresh context
    refresh_reason: str = "token_expired"  # token_expired, proactive_refresh, user_request
    refresh_method: str = "automatic"  # automatic, manual, background
    
    # Security context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    validate_ip_match: bool = False


@dataclass
class RefreshTokenResponse:
    """Response from token refresh."""
    
    new_access_token: AccessToken
    new_refresh_token: Optional[RefreshToken] = None  # May rotate refresh token
    token_metadata: TokenMetadata
    user_id: UserId
    event: TokenRefreshed


@runtime_checkable
class TokenRefresher(Protocol):
    """Protocol for token refresh operations."""
    
    async def refresh_token(
        self, 
        refresh_token: RefreshToken,
        validate_ip: bool = False,
        ip_address: Optional[str] = None
    ) -> tuple[AccessToken, Optional[RefreshToken], TokenClaims]:
        """Refresh tokens and return new tokens with claims."""
        ...


@runtime_checkable
class TokenMetadataProvider(Protocol):
    """Protocol for token metadata operations."""
    
    async def create_token_metadata(
        self,
        access_token: AccessToken,
        refresh_token: Optional[RefreshToken],
        token_claims: TokenClaims,
        user_id: UserId,
        session_id: Optional[SessionId] = None
    ) -> TokenMetadata:
        """Create token metadata from refresh operation."""
        ...


@runtime_checkable
class SecurityValidator(Protocol):
    """Protocol for security validation operations."""
    
    async def validate_refresh_security(
        self,
        refresh_token: RefreshToken,
        user_id: UserId,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> float:
        """Validate refresh security and return risk score."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishing."""
    
    async def publish(self, event: TokenRefreshed) -> None:
        """Publish token refreshed event."""
        ...


class RefreshTokenCommand:
    """Command to refresh tokens following maximum separation principle.
    
    Handles ONLY token refresh workflow orchestration.
    Does not handle token generation, validation, or storage.
    """
    
    def __init__(
        self,
        token_refresher: TokenRefresher,
        token_metadata_provider: TokenMetadataProvider,
        security_validator: SecurityValidator,
        event_publisher: EventPublisher
    ):
        """Initialize command with protocol dependencies."""
        self._token_refresher = token_refresher
        self._token_metadata_provider = token_metadata_provider
        self._security_validator = security_validator
        self._event_publisher = event_publisher
    
    async def execute(self, request: RefreshTokenRequest) -> RefreshTokenResponse:
        """Execute token refresh command.
        
        Args:
            request: Token refresh request with refresh token and context
            
        Returns:
            Token refresh response with new tokens
            
        Raises:
            TokenExpired: When refresh token is expired
            InvalidSignature: When refresh token signature is invalid
            AuthenticationFailed: When refresh fails for other reasons
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Step 1: Refresh tokens
            new_access_token, new_refresh_token, token_claims = (
                await self._token_refresher.refresh_token(
                    refresh_token=request.refresh_token,
                    validate_ip=request.validate_ip_match,
                    ip_address=request.ip_address
                )
            )
            
            # Step 2: Extract user ID from token claims if not provided
            user_id = request.user_id
            if not user_id:
                subject = token_claims.subject
                if not subject:
                    raise AuthenticationFailed(
                        "No user identifier in refresh token",
                        reason="missing_subject",
                        context={"refresh_token": str(request.refresh_token.value)[:20] + "..."}
                    )
                user_id = UserId(subject)
            
            # Step 3: Validate security context
            risk_score = await self._security_validator.validate_refresh_security(
                refresh_token=request.refresh_token,
                user_id=user_id,
                ip_address=request.ip_address,
                user_agent=request.user_agent
            )
            
            # Step 4: Create token metadata
            token_metadata = await self._token_metadata_provider.create_token_metadata(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_claims=token_claims,
                user_id=user_id,
                session_id=request.session_id
            )
            
            # Step 5: Calculate refresh duration
            end_time = datetime.now(timezone.utc)
            refresh_duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Step 6: Create token refresh event
            event = TokenRefreshed(
                user_id=user_id,
                tenant_id=request.tenant_id,
                session_id=request.session_id,
                old_access_token=None,  # Don't store old token for security
                new_access_token=new_access_token,
                refresh_token=new_refresh_token or request.refresh_token,
                old_token_expires_at=None,  # Could be extracted from old token
                new_token_expires_at=token_claims.expiration,
                refresh_token_expires_at=None,  # Could be extracted if available
                refresh_reason=request.refresh_reason,
                refresh_method=request.refresh_method,
                ip_address=request.ip_address,
                user_agent=request.user_agent,
                risk_score=risk_score,
                refresh_duration_ms=refresh_duration_ms,
                cache_hit=False,  # Refresh is always a fresh operation
                event_timestamp=end_time
            )
            
            # Step 7: Publish token refreshed event
            await self._event_publisher.publish(event)
            
            # Step 8: Return refresh response
            return RefreshTokenResponse(
                new_access_token=new_access_token,
                new_refresh_token=new_refresh_token,
                token_metadata=token_metadata,
                user_id=user_id,
                event=event
            )
            
        except (TokenExpired, InvalidSignature):
            # Re-raise token-specific exceptions as-is
            raise
        except Exception as e:
            # Wrap other exceptions in authentication failure
            raise AuthenticationFailed(
                "Token refresh process failed",
                reason="refresh_error",
                context={
                    "refresh_token": str(request.refresh_token.value)[:20] + "...",
                    "user_id": str(request.user_id.value) if request.user_id else None,
                    "error": str(e)
                }
            ) from e
    
    def _determine_cache_hit(
        self, 
        refresh_duration_ms: int, 
        risk_score: float
    ) -> bool:
        """Determine if refresh was likely served from cache.
        
        Args:
            refresh_duration_ms: Refresh duration in milliseconds
            risk_score: Security risk score
            
        Returns:
            True if likely served from cache
        """
        # Fast refresh with low risk score suggests cache hit
        return refresh_duration_ms < 50 and risk_score < 0.2