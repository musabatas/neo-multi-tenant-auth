"""User authentication command."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol, runtime_checkable
from ....core.value_objects.identifiers import UserId, TenantId, PermissionCode, RoleCode
from ...core.value_objects import AccessToken, RefreshToken, RealmIdentifier, SessionId
from ...core.entities import UserContext, AuthSession
from ...core.events import UserAuthenticated
from ...core.exceptions import AuthenticationFailed


@dataclass
class AuthenticateUserRequest:
    """Request to authenticate a user."""
    
    username: str
    password: str
    realm_id: RealmIdentifier
    tenant_id: Optional[TenantId] = None
    
    # Authentication context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[dict] = None
    
    # Security options
    require_mfa: bool = False
    remember_me: bool = False


@dataclass 
class AuthenticateUserResponse:
    """Response from user authentication."""
    
    user_context: UserContext
    auth_session: AuthSession
    access_token: AccessToken
    refresh_token: RefreshToken
    event: UserAuthenticated


@runtime_checkable
class KeycloakAuthenticator(Protocol):
    """Protocol for Keycloak authentication operations."""
    
    async def authenticate(
        self, 
        username: str, 
        password: str, 
        realm_id: RealmIdentifier
    ) -> tuple[AccessToken, RefreshToken, dict]:
        """Authenticate user with Keycloak and return tokens and user info."""
        ...


@runtime_checkable  
class UserContextProvider(Protocol):
    """Protocol for user context operations."""
    
    async def create_user_context(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId],
        realm_id: RealmIdentifier,
        user_info: dict
    ) -> UserContext:
        """Create user context from authentication data."""
        ...


@runtime_checkable
class SessionProvider(Protocol):
    """Protocol for session management operations."""
    
    async def create_session(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId],
        realm_id: RealmIdentifier,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Optional[dict] = None
    ) -> AuthSession:
        """Create new authentication session."""
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """Protocol for event publishing."""
    
    async def publish(self, event: UserAuthenticated) -> None:
        """Publish authentication event."""
        ...


class AuthenticateUser:
    """Command to authenticate user following maximum separation principle.
    
    Handles ONLY user authentication workflow orchestration.
    Does not handle token validation, session management, or user loading.
    """
    
    def __init__(
        self,
        keycloak_authenticator: KeycloakAuthenticator,
        user_context_provider: UserContextProvider,
        session_provider: SessionProvider,
        event_publisher: EventPublisher
    ):
        """Initialize command with protocol dependencies."""
        self._keycloak_authenticator = keycloak_authenticator
        self._user_context_provider = user_context_provider
        self._session_provider = session_provider
        self._event_publisher = event_publisher
    
    async def execute(self, request: AuthenticateUserRequest) -> AuthenticateUserResponse:
        """Execute user authentication command.
        
        Args:
            request: Authentication request with credentials and context
            
        Returns:
            Authentication response with user context and session
            
        Raises:
            AuthenticationFailed: When authentication fails for any reason
        """
        try:
            # Step 1: Authenticate with Keycloak
            access_token, refresh_token, user_info = await self._keycloak_authenticator.authenticate(
                username=request.username,
                password=request.password,
                realm_id=request.realm_id
            )
            
            # Extract user ID from user info
            user_id = UserId(user_info.get('sub') or user_info.get('user_id'))
            if not user_id:
                raise AuthenticationFailed(
                    "Invalid user information from authentication provider",
                    reason="missing_user_id",
                    context={"username": request.username, "realm": str(request.realm_id.value)}
                )
            
            # Step 2: Create user context
            user_context = await self._user_context_provider.create_user_context(
                user_id=user_id,
                tenant_id=request.tenant_id,
                realm_id=request.realm_id,
                user_info=user_info
            )
            
            # Step 3: Create authentication session
            auth_session = await self._session_provider.create_session(
                user_id=user_id,
                tenant_id=request.tenant_id,
                realm_id=request.realm_id,
                ip_address=request.ip_address,
                user_agent=request.user_agent,
                device_info=request.device_info or {}
            )
            
            # Step 4: Calculate risk score
            risk_score = self._calculate_risk_score(request, user_context, auth_session)
            
            # Step 5: Create authentication event
            event = UserAuthenticated(
                user_id=user_id,
                tenant_id=request.tenant_id,
                realm_id=request.realm_id,
                session_id=auth_session.session_id,
                authentication_method="password",
                mfa_verified=request.require_mfa,
                email=user_context.email,
                username=user_context.username,
                display_name=user_context.display_name,
                ip_address=request.ip_address,
                user_agent=request.user_agent,
                device_info=request.device_info or {},
                risk_score=risk_score,
                event_timestamp=datetime.now(timezone.utc)
            )
            
            # Step 6: Publish authentication event
            await self._event_publisher.publish(event)
            
            # Step 7: Return authentication response
            return AuthenticateUserResponse(
                user_context=user_context,
                auth_session=auth_session,
                access_token=access_token,
                refresh_token=refresh_token,
                event=event
            )
            
        except AuthenticationFailed:
            # Re-raise authentication failures as-is
            raise
        except Exception as e:
            # Wrap other exceptions in authentication failure
            raise AuthenticationFailed(
                "Authentication process failed",
                reason="authentication_error",
                context={
                    "username": request.username,
                    "realm": str(request.realm_id.value),
                    "error": str(e)
                }
            ) from e
    
    def _calculate_risk_score(
        self, 
        request: AuthenticateUserRequest,
        user_context: UserContext,
        auth_session: AuthSession
    ) -> float:
        """Calculate authentication risk score.
        
        Args:
            request: Authentication request
            user_context: User context
            auth_session: Authentication session
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        base_score = 0.0
        
        # New user risk
        if not user_context.last_login_at:
            base_score += 0.2
        
        # No IP address risk
        if not request.ip_address:
            base_score += 0.1
        
        # System user risk (elevated privileges)
        if user_context.is_system_user:
            base_score += 0.1
        
        # Admin user risk
        if user_context.is_admin:
            base_score += 0.1
        
        # High permission count risk
        if user_context.permission_count > 50:
            base_score += 0.1
        
        # Remember me risk (longer session)
        if request.remember_me:
            base_score += 0.05
        
        return min(1.0, base_score)