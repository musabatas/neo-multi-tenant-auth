"""
Migrated Authentication dependencies for FastAPI routes.

Gradual migration to neo-commons while maintaining backward compatibility.
"""
from typing import Optional, List, Annotated, Dict, Any, Union
from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError, ForbiddenError, RateLimitError
from src.features.auth.models.response import UserProfile

# Import protocol implementations
from .implementations import (
    NeoAdminTokenValidator,
    NeoAdminPermissionChecker,
    NeoAdminGuestAuthService,
    NeoAdminCacheService,
    NeoAdminAuthConfig
)

# Import existing services for gradual migration
from .services.auth_service import AuthService
from .services.permission_service import PermissionService
from .services.guest_auth_service import get_guest_auth_service, GuestAuthService


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
# PROTOCOL IMPLEMENTATION FACTORIES
# ============================================================================

def get_token_validator() -> NeoAdminTokenValidator:
    """Get token validator instance."""
    return NeoAdminTokenValidator()

def get_permission_checker() -> NeoAdminPermissionChecker:
    """Get permission checker instance.""" 
    return NeoAdminPermissionChecker()

def get_cache_service() -> NeoAdminCacheService:
    """Get cache service instance."""
    return NeoAdminCacheService()

def get_auth_config() -> NeoAdminAuthConfig:
    """Get auth config instance."""
    return NeoAdminAuthConfig()


# ============================================================================
# BACKWARD COMPATIBLE DEPENDENCIES - ORIGINAL IMPLEMENTATION
# ============================================================================

class CurrentUser:
    """Current authenticated user dependency - ORIGINAL IMPLEMENTATION."""
    
    def __init__(self, required: bool = True, permissions: Optional[List[str]] = None):
        self.required = required
        self.required_permissions = permissions or []
    
    async def __call__(
        self,
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
    ) -> Optional[UserProfile]:
        """Validate token and return current user."""
        
        # If no credentials and not required, return None
        if not credentials:
            if not self.required:
                return None
            raise UnauthorizedError("Authentication required")
        
        # Use existing AuthService for compatibility
        auth_service = AuthService()
        
        try:
            # Get current user using existing service
            user_profile = await auth_service.get_current_user(
                access_token=credentials.credentials,
                use_cache=True
            )
            
            # Check permissions if required
            if self.required_permissions:
                user_permissions = [p.get('code', f"{p.get('resource')}:{p.get('action')}") 
                                  if isinstance(p, dict) else str(p) 
                                  for p in user_profile.permissions]
                
                missing_permissions = set(self.required_permissions) - set(user_permissions)
                
                if missing_permissions:
                    raise ForbiddenError(
                        f"Missing required permissions: {', '.join(missing_permissions)}",
                        required_permission=", ".join(missing_permissions)
                    )
            
            return user_profile
            
        except UnauthorizedError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise UnauthorizedError("Invalid or expired token")


class CheckPermission:
    """
    Dependency class for checking database-based permissions - ORIGINAL IMPLEMENTATION.
    
    This actually validates permissions against the database, not just Keycloak roles.
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
        # Check if credentials are provided
        if not credentials:
            raise UnauthorizedError("Authentication required")
        
        # Get current user from token - this uses cache and loads from database
        auth_service = AuthService()
        user = await auth_service.get_current_user(
            access_token=credentials.credentials,
            use_cache=True
        )
        
        if not user:
            raise UnauthorizedError("Invalid authentication credentials")
        
        # Superadmin bypass - they have all permissions
        if user.get('is_superadmin'):
            logger.debug(f"Superadmin {user['id']} bypasses permission check")
            return user
        
        # Get user's permissions from the cached user data
        user_permissions_raw = user.get('permissions', [])
        
        # Handle both old string format and new object format
        user_permission_codes = []
        if user_permissions_raw and isinstance(user_permissions_raw[0], dict):
            # New format: list of permission objects
            user_permission_codes = [p.get('code', f"{p.get('resource')}:{p.get('action')}") for p in user_permissions_raw]
        else:
            # Old format: list of strings (for backward compatibility)
            user_permission_codes = user_permissions_raw
        
        # Check if user has required permissions
        has_permission = False
        
        if self.any_of:
            # User needs ANY of the permissions
            for perm in self.permissions:
                if perm in user_permission_codes or f"{perm.split(':')[0]}:*" in user_permission_codes:
                    has_permission = True
                    break
        else:
            # User needs ALL permissions
            has_permission = True
            for perm in self.permissions:
                if perm not in user_permission_codes and f"{perm.split(':')[0]}:*" not in user_permission_codes:
                    has_permission = False
                    break
        
        if not has_permission:
            logger.warning(
                f"Permission denied for user {user['id']}: "
                f"required={self.permissions}, user_has={user_permission_codes[:5]}..."  # Show first 5 perms
            )
            raise ForbiddenError(
                f"Insufficient permissions. Required: {', '.join(self.permissions)}"
            )
        
        logger.debug(
            f"Permission granted for user {user['id']}: "
            f"permissions={self.permissions}"
        )
        return user


class TokenData:
    """Token data dependency for accessing raw token claims - ORIGINAL IMPLEMENTATION."""
    
    async def __call__(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
    ) -> dict:
        """Get raw token data."""
        try:
            # Use existing token manager for validation
            from src.integrations.keycloak.token_manager import get_token_manager, ValidationStrategy
            
            token_manager = get_token_manager()
            return await token_manager.validate_token(
                credentials.credentials,
                realm=settings.keycloak_admin_realm,
                strategy=ValidationStrategy.LOCAL
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise UnauthorizedError("Invalid or expired token")


class GuestOrAuthenticated:
    """
    Dependency that allows both authenticated users and guest access - ORIGINAL IMPLEMENTATION.
    
    Provides session tracking for guests while maintaining full functionality
    for authenticated users.
    """
    
    def __init__(self, required_permissions: Optional[list] = None):
        """
        Initialize guest/authenticated dependency.
        
        Args:
            required_permissions: Permissions required for authenticated access
        """
        self.required_permissions = required_permissions or []
    
    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(guest_security),
        x_guest_session: Optional[str] = Header(None, description="Guest session token"),
        guest_service: GuestAuthService = Depends(get_guest_auth_service)
    ) -> Dict[str, Any]:
        """
        Validate either authenticated user or create guest session.
        
        Returns:
            User data (authenticated) or guest session data
        """
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        referrer = request.headers.get("referer")
        
        # Try authenticated access first
        if credentials and credentials.credentials:
            try:
                # Use existing authentication system
                auth_check = CheckPermission(self.required_permissions, scope="platform")
                user_data = await auth_check(credentials, request)
                
                # Add user type marker
                user_data["user_type"] = "authenticated"
                user_data["session_type"] = "keycloak"
                
                logger.debug(f"Authenticated user {user_data['id']} accessing reference data")
                return user_data
                
            except Exception as e:
                logger.debug(f"Authentication failed, falling back to guest: {e}")
                # Fall through to guest access
        
        # Handle guest access
        try:
            # Get or create guest session
            guest_token = x_guest_session or (credentials.credentials if credentials else None)
            
            session_data = await guest_service.get_or_create_guest_session(
                session_token=guest_token,
                ip_address=client_ip,
                user_agent=user_agent,
                referrer=referrer
            )
            
            # Format session token for response
            if not guest_token or not guest_token.startswith("guest_"):
                session_data["new_session_token"] = f"{session_data['session_id']}:{session_data['session_token']}"
            
            logger.debug(f"Guest session {session_data['session_id']} accessing reference data")
            return session_data
            
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded for IP {client_ip}: {e}")
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
    """Dependency to extract guest session information - ORIGINAL IMPLEMENTATION."""
    
    async def __call__(
        self,
        x_guest_session: Optional[str] = Header(None),
        guest_service: GuestAuthService = Depends(get_guest_auth_service)
    ) -> Optional[Dict[str, Any]]:
        """Get guest session stats if session token provided."""
        if not x_guest_session:
            return None
        
        try:
            return await guest_service.get_session_stats(x_guest_session)
        except Exception as e:
            logger.debug(f"Failed to get guest session stats: {e}")
            return None


# ============================================================================
# DEPENDENCY INSTANCES 
# ============================================================================

# Current user dependencies
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
    """Get current user's permissions."""
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
    """Get current user's roles."""
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


# ============================================================================
# NEO-COMMONS EXPERIMENTAL DEPENDENCIES (Future Use)
# ============================================================================

# These are available for testing and future migration
# but not used by default to maintain stability

def get_neo_current_user(required: bool = True, permissions: Optional[List[str]] = None):
    """
    Get neo-commons based CurrentUser dependency (experimental).
    
    This is available for testing but not used by default.
    """
    from .dependencies_neo import CurrentUser as NeoCurrentUser
    return NeoCurrentUser(required=required, permissions=permissions)

def get_neo_check_permission(permissions: List[str], scope: str = "platform", any_of: bool = False):
    """
    Get neo-commons based CheckPermission dependency (experimental).
    
    This is available for testing but not used by default.
    """
    from .dependencies_neo import CheckPermission as NeoCheckPermission
    return NeoCheckPermission(permissions=permissions, scope=scope, any_of=any_of)