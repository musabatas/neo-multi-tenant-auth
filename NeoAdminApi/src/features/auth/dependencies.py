"""
Simplified Neo-Commons Auth Dependencies for FastAPI routes.

Uses neo-commons auth services directly without unnecessary wrappers.
"""
from typing import List, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from loguru import logger

# Import neo-commons directly
from neo_commons.auth import create_auth_service, create_permission_cache_manager
from neo_commons.auth.dependencies import (
    create_reference_data_access,
    create_guest_session_info
)
from neo_commons.auth.services.guest import create_guest_auth_service
from neo_commons.cache import CacheManager, TenantAwareCacheService

from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError, ForbiddenError
from .implementations import NeoAdminAuthConfig
from .services.permission_service import PermissionService

# Security scheme
security = HTTPBearer(
    description="JWT token from Keycloak",
    auto_error=False
)

# ============================================================================
# DIRECT NEO-COMMONS INTEGRATION
# ============================================================================

def get_auth_service():
    """Get neo-commons auth service directly."""
    return create_auth_service(auth_config=NeoAdminAuthConfig())

def get_permission_service() -> PermissionService:
    """Get permission service with neo-commons integration."""
    return PermissionService()

def get_guest_auth_service():
    """Get guest authentication service with cache integration."""
    # Create cache service for guest auth
    from src.common.cache.client import get_cache
    from neo_commons.cache.implementations import TenantAwareCacheService
    
    cache_manager = get_cache()
    cache_service = TenantAwareCacheService(cache_manager)
    
    return create_guest_auth_service(cache_service=cache_service)

# ============================================================================
# GUEST AUTHENTICATION DEPENDENCIES
# ============================================================================

def _create_guest_dependencies():
    """Create configured guest authentication dependencies."""
    auth_service = get_auth_service()
    permission_service = get_permission_service()
    guest_service = get_guest_auth_service()
    auth_config = NeoAdminAuthConfig()
    
    # Create the dependencies using neo-commons factories
    reference_data_access = create_reference_data_access(
        guest_service=guest_service,
        permission_checker=permission_service,
        token_validator=auth_service.token_validator,
        auth_config=auth_config
    )
    
    guest_session_info = create_guest_session_info(guest_service)
    
    return reference_data_access, guest_session_info

# Create the dependency instances
get_reference_data_access, get_guest_session_info = _create_guest_dependencies()

# ============================================================================
# FASTAPI DEPENDENCIES
# ============================================================================

async def get_current_user(
    credentials: HTTPBearer = Depends(security)
) -> Dict[str, Any]:
    """
    Get current authenticated user.
    
    Returns:
        User information from token validation
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        auth_service = get_auth_service()
        token_claims = await auth_service.token_validator.validate_token(
            token=credentials.credentials,
            realm=settings.keycloak_admin_realm
        )
        
        # Get platform user info via permission service (includes ID mapping)
        permission_service = get_permission_service()
        user = await permission_service.validate_token_permissions(
            access_token=credentials.credentials,
            required_permission="platform:access"  # Basic platform access
        )
        
        return user
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

async def get_current_user_optional(
    credentials: HTTPBearer = Depends(security)
) -> Dict[str, Any] | None:
    """
    Get current user if authenticated, None otherwise.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

class CheckPermission:
    """
    Permission checking dependency.
    
    Usage:
        @router.get("/users")
        async def list_users(
            current_user: dict = Depends(CheckPermission(["users:list"]))
        ):
            return await user_service.list_users()
    """
    
    def __init__(self, permissions: List[str], any_of: bool = False, scope: str = "platform"):
        self.permissions = permissions
        self.any_of = any_of
        self.scope = scope  # For backward compatibility, not used in logic yet
    
    async def __call__(
        self,
        credentials: HTTPBearer = Depends(security)
    ) -> Dict[str, Any]:
        """Check permissions and return user if authorized."""
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        try:
            permission_service = get_permission_service()
            
            # Validate token and check permissions in one operation
            user = await permission_service.validate_token_permissions(
                access_token=credentials.credentials,
                required_permission=self.permissions[0] if self.permissions else "platform:access"
            )
            
            # For multiple permissions, check additional ones
            if len(self.permissions) > 1:
                if self.any_of:
                    # Check if user has ANY of the permissions
                    has_permission = await permission_service.check_any_permission(
                        user_id=user['id'],
                        permissions=self.permissions
                    )
                else:
                    # Check if user has ALL permissions
                    has_permission = await permission_service.check_all_permissions(
                        user_id=user['id'],
                        permissions=self.permissions
                    )
                
                if not has_permission:
                    raise ForbiddenError(f"Required permissions: {', '.join(self.permissions)}")
            
            return user
            
        except (UnauthorizedError, ForbiddenError):
            raise
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )

# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def require_permission(permission: str):
    """Convenience function for single permission check."""
    return CheckPermission([permission])

def require_any_permission(*permissions: str):
    """Convenience function for any-of permission check."""
    return CheckPermission(list(permissions), any_of=True)

def require_all_permissions(*permissions: str):
    """Convenience function for all-of permission check."""
    return CheckPermission(list(permissions), any_of=False)

# ============================================================================
# EXPORTS - Make functions available for import from other modules
# ============================================================================

__all__ = [
    # Core dependencies
    "get_current_user",
    "get_current_user_optional", 
    "CheckPermission",
    "security",
    
    # Guest authentication (from neo-commons)
    "get_reference_data_access",
    "get_guest_session_info",
    
    # Convenience functions
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    
    # Services
    "get_auth_service",
    "get_permission_service"
]