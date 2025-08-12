"""
Authentication dependencies for FastAPI routes.
"""
from typing import Optional, List, Annotated, Dict, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from src.integrations.keycloak.token_manager import get_token_manager, ValidationStrategy
from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError, ForbiddenError
from src.features.auth.models.response import UserProfile
from .services.auth_service import AuthService
from .services.permission_service import PermissionService


# Security scheme
security = HTTPBearer(
    description="JWT token from Keycloak",
    auto_error=False
)


class CurrentUser:
    """Current authenticated user dependency."""
    
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
        
        # Validate token using Token Manager
        try:
            token_manager = get_token_manager()
            token_data = await token_manager.validate_token(
                credentials.credentials,
                realm=settings.keycloak_admin_realm,
                critical=False,  # Use dual validation for better performance
                strategy=ValidationStrategy.DUAL
            )
            
            # Extract user information from token
            user = UserProfile(
                id=token_data.get("sub", ""),
                username=token_data.get("preferred_username", ""),
                email=token_data.get("email", ""),
                first_name=token_data.get("given_name"),
                last_name=token_data.get("family_name"),
                display_name=token_data.get("name")
            )
            
            # Check permissions if required
            if self.required_permissions:
                user_permissions = self._extract_permissions(token_data)
                missing_permissions = set(self.required_permissions) - set(user_permissions)
                
                if missing_permissions:
                    raise ForbiddenError(
                        f"Missing required permissions: {', '.join(missing_permissions)}",
                        required_permission=", ".join(missing_permissions)
                    )
            
            return user
            
        except UnauthorizedError:
            raise
        except ForbiddenError:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise UnauthorizedError("Invalid or expired token")
    
    def _extract_permissions(self, token_data: dict) -> List[str]:
        """Extract permissions from token claims."""
        permissions = []
        
        # Check resource access
        resource_access = token_data.get("resource_access", {})
        if settings.keycloak_admin_client_id in resource_access:
            client_access = resource_access[settings.keycloak_admin_client_id]
            permissions.extend(client_access.get("roles", []))
        
        # Check realm roles
        realm_access = token_data.get("realm_access", {})
        permissions.extend(realm_access.get("roles", []))
        
        # Check scope
        scope = token_data.get("scope", "")
        if scope:
            permissions.extend(scope.split(" "))
        
        return list(set(permissions))  # Remove duplicates


# Dependency instances
get_current_user = CurrentUser(required=True)
get_current_user_optional = CurrentUser(required=False)


def require_permissions(*permissions: str):
    """Create a dependency that requires specific permissions."""
    return CurrentUser(required=True, permissions=list(permissions))


# Common permission dependencies
require_admin = require_permissions("admin", "platform_admin")
require_superadmin = require_permissions("superadmin")


class CheckPermission:
    """
    Dependency class for checking database-based permissions.
    
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
        
        # Get current user from token - this uses cache
        auth_service = AuthService()
        user = await auth_service.get_current_user(credentials.credentials, use_cache=True)
        
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
    """Token data dependency for accessing raw token claims."""
    
    async def __call__(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
    ) -> dict:
        """Get raw token data."""
        try:
            token_manager = get_token_manager()
            return await token_manager.validate_token(
                credentials.credentials,
                realm=settings.keycloak_admin_realm,
                critical=False,
                strategy=ValidationStrategy.DUAL
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise UnauthorizedError("Invalid or expired token")


get_token_data = TokenData()


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