"""
Neo-Commons Auth Dependencies for FastAPI routes.

Protocol-based dependency injection using neo-commons auth infrastructure.
"""
from typing import Optional, List, Annotated, Dict, Any, Union
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from neo_commons.auth.services.compatibility import (
    AuthServiceWrapper, PermissionServiceWrapper, GuestAuthServiceWrapper
)
from neo_commons.auth.dependencies import (
    CurrentUser as NeoCurrentUser,
    CheckPermission as NeoCheckPermission,
    GuestOrAuthenticated as NeoGuestOrAuthenticated
)

from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError, ForbiddenError, RateLimitError
from src.features.auth.models.response import UserProfile
from .implementations import (
    NeoAdminTokenValidator,
    NeoAdminPermissionChecker,
    NeoAdminGuestAuthService,
    NeoAdminCacheService,
    NeoAdminAuthConfig
)


# Security scheme
security = HTTPBearer(
    description="JWT token from Keycloak",
    auto_error=False
)

# Optional security scheme for guest tokens
guest_security = HTTPBearer(
    description="Optional guest session token for tracking",
    auto_error=False
)


# ============================================================================
# SERVICE INSTANCES - Protocol Implementations
# ============================================================================

def get_token_validator() -> NeoAdminTokenValidator:
    """Get token validator instance."""
    return NeoAdminTokenValidator()

def get_permission_checker() -> NeoAdminPermissionChecker:
    """Get permission checker instance."""
    return NeoAdminPermissionChecker()

def get_guest_auth_service() -> NeoAdminGuestAuthService:
    """Get guest auth service instance."""
    return NeoAdminGuestAuthService()

def get_cache_service() -> NeoAdminCacheService:
    """Get cache service instance."""
    return NeoAdminCacheService()

def get_auth_config() -> NeoAdminAuthConfig:
    """Get auth config instance."""
    return NeoAdminAuthConfig()


# ============================================================================
# SERVICE WRAPPERS - Backward Compatibility
# ============================================================================

def get_auth_service_wrapper() -> AuthServiceWrapper:
    """Get auth service wrapper for backward compatibility."""
    return AuthServiceWrapper(
        token_validator=get_token_validator(),
        permission_checker=get_permission_checker(),
        auth_config=get_auth_config(),
        cache_service=get_cache_service()
    )

def get_permission_service_wrapper() -> PermissionServiceWrapper:
    """Get permission service wrapper for backward compatibility."""
    return PermissionServiceWrapper(
        permission_checker=get_permission_checker(),
        cache_service=get_cache_service(),
        auth_config=get_auth_config()
    )

def get_guest_service_wrapper() -> GuestAuthServiceWrapper:
    """Get guest auth service wrapper for backward compatibility."""
    return GuestAuthServiceWrapper(
        guest_service=get_guest_auth_service(),
        permission_checker=get_permission_checker(),
        token_validator=get_token_validator(),
        auth_config=get_auth_config()
    )


# ============================================================================
# NEO-COMMONS DEPENDENCY CLASSES
# ============================================================================

class CurrentUser:
    """Current authenticated user dependency using neo-commons."""
    
    def __init__(self, required: bool = True, permissions: Optional[List[str]] = None):
        self.required = required
        self.required_permissions = permissions or []
        # Will be configured during instantiation - see get_current_user/get_current_user_optional
        self.neo_current_user = None
    
    async def __call__(
        self,
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
    ) -> Optional[UserProfile]:
        """Validate token and return current user."""
        
        # Lazy initialization of neo-commons dependency
        if self.neo_current_user is None:
            self.neo_current_user = get_neo_current_user(
                required=self.required,
                permissions=self.required_permissions
            )
        
        try:
            # Delegate directly to neo-commons CurrentUser
            user_profile = await self.neo_current_user(credentials)
            return user_profile
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise


class CheckPermission:
    """
    Dependency class for checking database-based permissions using neo-commons.
    """
    
    def __init__(
        self,
        permissions: List[str],
        scope: str = "platform",
        any_of: bool = False,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize permission checker.
        
        Args:
            permissions: Required permission codes
            scope: Permission scope (platform/tenant)
            any_of: If True, requires ANY permission; if False, requires ALL
            tenant_id: Tenant context for tenant-scoped permissions
        """
        self.permissions = permissions if isinstance(permissions, list) else [permissions]
        self.scope = scope
        self.any_of = any_of
        self.tenant_id = tenant_id
        
        # Will be configured during instantiation
        self.neo_check_permission = None
    
    async def __call__(
        self,
        credentials: HTTPAuthorizationCredentials = Depends(security),
        request: Request = None
    ) -> Dict[str, Any]:
        """
        Check if user has required permissions and return user info.
        
        Returns:
            User information if permission check passes
            
        Raises:
            ForbiddenError: User lacks required permissions
        """
        # Lazy initialization of neo-commons dependency
        if self.neo_check_permission is None:
            self.neo_check_permission = get_neo_check_permission(
                permissions=self.permissions,
                require_all=not self.any_of,
                tenant_id=self.tenant_id
            )
        
        try:
            # Delegate directly to neo-commons CheckPermission
            user_data = await self.neo_check_permission(credentials, request)
            return user_data
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            raise


class TokenData:
    """Token data dependency for accessing raw token claims using neo-commons."""
    
    def __init__(self):
        # Use shared protocol implementations
        self.token_validator = _token_validator
        self.auth_config = _auth_config
    
    async def __call__(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
    ) -> dict:
        """Get raw token data."""
        try:
            # Validate token using neo-commons protocol
            validation_result = await self.token_validator.validate_token(
                token=credentials.credentials,
                realm=self.auth_config.default_realm,
                strategy=self.auth_config.token_validation_strategy
            )
            
            # Return raw claims for compatibility
            return validation_result.raw_claims
            
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise UnauthorizedError("Invalid or expired token")


class GuestOrAuthenticated:
    """
    Dependency that allows both authenticated users and guest access using neo-commons.
    """
    
    def __init__(self, required_permissions: Optional[list] = None):
        """
        Initialize guest/authenticated dependency.
        
        Args:
            required_permissions: Permissions required for authenticated access
        """
        self.required_permissions = required_permissions or []
        
        # Will be configured during instantiation
        self.neo_guest_or_auth = None
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(guest_security),
        x_guest_session: Optional[str] = Header(None, description="Guest session token")
    ) -> Dict[str, Any]:
        """
        Validate either authenticated user or create guest session.
        
        Returns:
            User data (authenticated) or guest session data
        """
        # Lazy initialization of neo-commons dependency
        if self.neo_guest_or_auth is None:
            self.neo_guest_or_auth = get_neo_guest_or_authenticated()
        
        try:
            # Extract client information
            client_ip = self._get_client_ip(request)
            user_agent = request.headers.get("user-agent")
            referrer = request.headers.get("referer")
            
            # Use neo-commons GuestOrAuthenticated dependency
            result = await self.neo_guest_or_auth(
                token=credentials.credentials if credentials else None,
                guest_token=x_guest_session,
                ip_address=client_ip,
                user_agent=user_agent,
                metadata={"referrer": referrer}
            )
            
            # Format result for NeoAdminApi compatibility
            if result.get("user_type") == "authenticated":
                # Authenticated user - format as expected
                return {
                    "user_type": "authenticated",
                    "session_type": "keycloak",
                    "id": result.get("user_id"),
                    "email": result.get("email"),
                    "username": result.get("username"),
                    "permissions": result.get("permissions", []),
                    "roles": result.get("roles", []),
                    "tenants": result.get("tenants", [])
                }
            else:
                # Guest session - format as expected
                guest_data = {
                    "user_type": "guest",
                    "session_type": "guest",
                    "session_id": result.get("session_id"),
                    "session_token": result.get("session_token"),
                    "permissions": result.get("permissions", ["reference_data:read"]),
                    "rate_limit": result.get("rate_limit", {}),
                    "request_count": result.get("request_count", 0),
                    "created_at": result.get("created_at"),
                    "expires_at": result.get("expires_at")
                }
                
                # Add new session token if created
                if result.get("new_session_token"):
                    guest_data["new_session_token"] = result["new_session_token"]
                
                return guest_data
                
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for IP {self._get_client_ip(request)}: {e}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(e),
                headers={"Retry-After": "3600"}  # 1 hour
            )
        except Exception as e:
            logger.error(f"Guest authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to create guest session"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check X-Forwarded-For header (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header (nginx)
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


class GuestSessionInfo:
    """Dependency to extract guest session information using neo-commons."""
    
    def __init__(self):
        # Use shared protocol implementation
        self.guest_service = _guest_auth_service
    
    async def __call__(
        self,
        x_guest_session: Optional[str] = Header(None)
    ) -> Optional[Dict[str, Any]]:
        """Get guest session stats if session token provided."""
        if not x_guest_session:
            return None
        
        try:
            return await self.guest_service.get_session_stats(x_guest_session)
        except Exception as e:
            logger.debug(f"Failed to get guest session stats: {e}")
            return None


# ============================================================================
# DEPENDENCY INSTANCES
# ============================================================================

# Protocol implementations - configured once and reused
_token_validator = get_token_validator()
_permission_checker = get_permission_checker()
_auth_config = get_auth_config()
_cache_service = get_cache_service()
_guest_auth_service = get_guest_auth_service()

# Neo-commons dependency factories
def get_neo_current_user(required: bool = True, permissions: Optional[List[str]] = None) -> NeoCurrentUser:
    """Create configured neo-commons CurrentUser dependency."""
    return NeoCurrentUser(
        token_validator=_token_validator,
        auth_config=_auth_config,
        required=required,
        permissions=permissions
    )

def get_neo_check_permission(
    permissions: List[str],
    require_all: bool = True,
    tenant_id: Optional[str] = None
) -> NeoCheckPermission:
    """Create configured neo-commons CheckPermission dependency."""
    return NeoCheckPermission(
        permission_checker=_permission_checker,
        token_validator=_token_validator,
        auth_config=_auth_config,
        permissions=permissions,
        any_of=not require_all,  # Convert require_all to any_of (inverted logic)
        tenant_id=tenant_id
    )

def get_neo_guest_or_authenticated() -> NeoGuestOrAuthenticated:
    """Create configured neo-commons GuestOrAuthenticated dependency."""
    return NeoGuestOrAuthenticated(
        guest_service=_guest_auth_service,
        permission_checker=_permission_checker,
        token_validator=_token_validator,
        auth_config=_auth_config
    )

# NeoAdminApi dependency instances with protocol implementations
get_current_user = CurrentUser(required=True)
get_current_user_optional = CurrentUser(required=False)

# Token data dependency
get_token_data = TokenData()

# Guest session info dependency
get_guest_session_info = GuestSessionInfo()

# Common guest/authenticated access for reference data
get_reference_data_access = GuestOrAuthenticated(required_permissions=["reference_data:read"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def require_permissions(*permissions: str):
    """Create a dependency that requires specific permissions."""
    return CurrentUser(required=True, permissions=list(permissions))

def create_guest_or_authenticated(required_permissions: Optional[list] = None):
    """
    Create a guest/authenticated dependency with specific permissions.
    
    Args:
        required_permissions: Permissions required for authenticated users
        
    Returns:
        Configured dependency instance
    """
    return GuestOrAuthenticated(required_permissions)


# ============================================================================
# PERMISSION FUNCTIONS
# ============================================================================

async def get_user_permissions(
    token_data: Annotated[dict, Depends(get_token_data)]
) -> List[str]:
    """Get current user's permissions from token."""
    permissions = []
    
    # Extract from resource access
    resource_access = token_data.get("resource_access", {})
    if settings.keycloak_admin_client_id in resource_access:
        client_access = resource_access[settings.keycloak_admin_client_id]
        permissions.extend(client_access.get("roles", []))
    
    # Extract from realm access
    realm_access = token_data.get("realm_access", {})
    permissions.extend(realm_access.get("roles", []))
    
    # Extract from scope
    scope = token_data.get("scope", "")
    if scope:
        permissions.extend(scope.split(" "))
    
    return list(set(permissions))


async def get_user_roles(
    token_data: Annotated[dict, Depends(get_token_data)]
) -> List[str]:
    """Get current user's roles from token."""
    roles = []
    
    # Extract realm roles
    realm_access = token_data.get("realm_access", {})
    roles.extend(realm_access.get("roles", []))
    
    # Extract client roles
    resource_access = token_data.get("resource_access", {})
    if settings.keycloak_admin_client_id in resource_access:
        client_access = resource_access[settings.keycloak_admin_client_id]
        roles.extend(client_access.get("roles", []))
    
    return list(set(roles))


# ============================================================================
# COMMON PERMISSION DEPENDENCIES
# ============================================================================

# Common permission dependencies
require_admin = require_permissions("admin", "platform_admin")
require_superadmin = require_permissions("superadmin")