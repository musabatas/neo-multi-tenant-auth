"""
Authentication Dependencies Implementation for Neo-Commons

Protocol-compliant FastAPI dependencies for authentication and authorization with:
- Token validation using protocol-based token validators
- Permission checking against database with caching
- User extraction from JWT tokens with Keycloak integration
- Multi-tenant permission scoping with context awareness
- Configurable validation strategies (local/introspection/dual)
"""

from typing import Optional, List, Annotated, Dict, Any, Union
from fastapi import Depends, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    ValidationStrategy
)
from ..keycloak.protocols import TokenValidatorProtocol
from ..permissions.protocols import PermissionCheckerProtocol


# Security scheme for FastAPI
security = HTTPBearer(
    description="JWT token from Keycloak",
    auto_error=False
)


class UserProfile:
    """User profile extracted from token."""
    
    def __init__(
        self,
        id: str,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None
    ):
        self.id = id
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.display_name = display_name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name
        }


class CurrentUser:
    """
    Current authenticated user dependency with protocol-based validation.
    
    Features:
    - Protocol-based token validation for service independence
    - Configurable permission requirements
    - Optional authentication support
    - Token claim extraction and user profile creation
    - Performance optimization with validation strategies
    """
    
    def __init__(
        self,
        token_validator: TokenValidatorProtocol,
        auth_config: AuthConfigProtocol,
        required: bool = True,
        permissions: Optional[List[str]] = None
    ):
        """
        Initialize current user dependency.
        
        Args:
            token_validator: Token validation service
            auth_config: Authentication configuration
            required: Whether authentication is required
            permissions: Required permissions for access
        """
        self.token_validator = token_validator
        self.auth_config = auth_config
        self.required = required
        self.required_permissions = permissions or []
    
    async def __call__(
        self,
        credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)]
    ) -> Optional[UserProfile]:
        """
        Validate token and return current user.
        
        Args:
            credentials: Bearer token credentials
            
        Returns:
            User profile if authenticated, None if optional and not provided
            
        Raises:
            AuthenticationError: Invalid token or authentication required
            AuthorizationError: Missing required permissions
        """
        # If no credentials and not required, return None
        if not credentials:
            if not self.required:
                return None
            raise AuthenticationError("Authentication required")
        
        # Validate token using protocol-based validator
        try:
            token_data = await self.token_validator.validate_token(
                credentials.credentials,
                realm=self.auth_config.default_realm,
                strategy=ValidationStrategy.LOCAL,  # Use local validation to avoid introspection errors
                critical=False
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
                    raise AuthorizationError(
                        f"Missing required permissions: {', '.join(missing_permissions)}",
                        required_permission=", ".join(missing_permissions)
                    )
            
            return user
            
        except AuthenticationError:
            raise
        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError("Invalid or expired token")
    
    def _extract_permissions(self, token_data: dict) -> List[str]:
        """
        Extract permissions from token claims.
        
        Args:
            token_data: Decoded token data
            
        Returns:
            List of permission codes
        """
        permissions = []
        
        # Check resource access
        resource_access = token_data.get("resource_access", {})
        if hasattr(self.auth_config, 'admin_client_id') and self.auth_config.admin_client_id in resource_access:
            client_access = resource_access[self.auth_config.admin_client_id]
            permissions.extend(client_access.get("roles", []))
        
        # Check realm roles
        realm_access = token_data.get("realm_access", {})
        permissions.extend(realm_access.get("roles", []))
        
        # Check scope
        scope = token_data.get("scope", "")
        if scope:
            permissions.extend(scope.split(" "))
        
        return list(set(permissions))  # Remove duplicates


class CheckPermission:
    """
    Database-based permission checking dependency.
    
    This validates permissions against the database, not just Keycloak roles.
    Uses protocol-based services for multi-tenant permission checking.
    
    Features:
    - Database permission validation with caching
    - Multi-tenant permission scoping
    - ANY/ALL permission logic
    - Superadmin bypass functionality
    - Performance optimization with cached user data
    """
    
    def __init__(
        self,
        permission_checker: PermissionCheckerProtocol,
        token_validator: TokenValidatorProtocol,
        auth_config: AuthConfigProtocol,
        permissions: List[str],
        scope: str = "platform",
        any_of: bool = False,
        tenant_id: Optional[str] = None
    ):
        """
        Initialize permission checker dependency.
        
        Args:
            permission_checker: Permission validation service
            token_validator: Token validation service
            auth_config: Authentication configuration
            permissions: Required permission codes
            scope: Permission scope (platform/tenant/user)
            any_of: If True, requires ANY permission; if False, requires ALL
            tenant_id: Tenant context for tenant-scoped permissions
        """
        self.permission_checker = permission_checker
        self.token_validator = token_validator
        self.auth_config = auth_config
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
        
        Args:
            credentials: Bearer token credentials
            request: FastAPI request object
            
        Returns:
            User information if permission check passes
            
        Raises:
            AuthenticationError: Invalid authentication
            AuthorizationError: User lacks required permissions
        """
        # Check if credentials are provided
        if not credentials:
            raise AuthenticationError("Authentication required")
        
        # Validate token and get user info
        try:
            token_data = await self.token_validator.validate_token(
                credentials.credentials,
                realm=self.auth_config.default_realm,
                strategy=ValidationStrategy.LOCAL,
                critical=False
            )
            
            user_id = token_data.get("sub", "")
            if not user_id:
                raise AuthenticationError("Invalid token: missing user ID")
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise AuthenticationError("Invalid authentication credentials")
        
        # Check permissions using protocol-based permission checker
        try:
            # Get user permissions with caching
            has_permission = await self.permission_checker.check_permission(
                user_id=user_id,
                permissions=self.permissions,
                scope=self.scope,
                tenant_id=self.tenant_id,
                any_of=self.any_of
            )
            
            if not has_permission:
                logger.warning(
                    f"Permission denied for user {user_id}: "
                    f"required={self.permissions}, scope={self.scope}"
                )
                raise AuthorizationError(
                    f"Insufficient permissions. Required: {', '.join(self.permissions)}"
                )
            
            logger.debug(
                f"Permission granted for user {user_id}: "
                f"permissions={self.permissions}, scope={self.scope}"
            )
            
            # Try to get platform user ID if we have a resolver
            platform_user_id = user_id  # Default to Keycloak ID
            if hasattr(self.permission_checker, '_resolve_user_id'):
                resolved_id = await self.permission_checker._resolve_user_id(user_id)
                if resolved_id:
                    platform_user_id = resolved_id
            
            # Return user data with both IDs
            return {
                "id": platform_user_id,  # Platform user ID for database operations
                "keycloak_id": user_id,  # Original Keycloak ID
                "username": token_data.get("preferred_username", ""),
                "email": token_data.get("email", ""),
                "permissions": self.permissions,
                "scope": self.scope,
                "tenant_id": self.tenant_id
            }
            
        except AuthorizationError:
            raise
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            raise AuthorizationError("Permission check failed")


class TokenData:
    """
    Token data dependency for accessing raw token claims.
    
    Provides access to raw JWT token data for custom permission logic
    or additional claim extraction.
    """
    
    def __init__(
        self,
        token_validator: TokenValidatorProtocol,
        auth_config: AuthConfigProtocol
    ):
        """
        Initialize token data dependency.
        
        Args:
            token_validator: Token validation service
            auth_config: Authentication configuration
        """
        self.token_validator = token_validator
        self.auth_config = auth_config
    
    async def __call__(
        self,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
    ) -> dict:
        """
        Get raw token data.
        
        Args:
            credentials: Bearer token credentials
            
        Returns:
            Raw token claims dictionary
            
        Raises:
            AuthenticationError: Invalid token
        """
        try:
            return await self.token_validator.validate_token(
                credentials.credentials,
                realm=self.auth_config.default_realm,
                strategy=ValidationStrategy.LOCAL,
                critical=False
            )
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise AuthenticationError("Invalid or expired token")


# Factory functions for creating configured dependencies
def create_current_user(
    token_validator: TokenValidatorProtocol,
    auth_config: AuthConfigProtocol,
    required: bool = True,
    permissions: Optional[List[str]] = None
) -> CurrentUser:
    """Create configured CurrentUser dependency."""
    return CurrentUser(token_validator, auth_config, required, permissions)


def create_permission_checker(
    permission_checker: PermissionCheckerProtocol,
    token_validator: TokenValidatorProtocol,
    auth_config: AuthConfigProtocol,
    permissions: List[str],
    scope: str = "platform",
    any_of: bool = False,
    tenant_id: Optional[str] = None
) -> CheckPermission:
    """Create configured CheckPermission dependency."""
    return CheckPermission(
        permission_checker, token_validator, auth_config,
        permissions, scope, any_of, tenant_id
    )


def create_token_data(
    token_validator: TokenValidatorProtocol,
    auth_config: AuthConfigProtocol
) -> TokenData:
    """Create configured TokenData dependency."""
    return TokenData(token_validator, auth_config)


def require_permissions(*permissions: str):
    """
    Create a dependency that requires specific permissions.
    
    Args:
        *permissions: Permission codes required
        
    Returns:
        Function that creates configured CurrentUser dependency
    """
    def create_dependency(
        token_validator: TokenValidatorProtocol,
        auth_config: AuthConfigProtocol
    ):
        return CurrentUser(token_validator, auth_config, True, list(permissions))
    
    return create_dependency


async def get_user_permissions(
    token_data: Annotated[dict, Depends(lambda: None)]  # Placeholder dependency
) -> List[str]:
    """
    Get current user's permissions from token.
    
    Args:
        token_data: Token claims data
        
    Returns:
        List of permission codes
    """
    if not token_data:
        return []
    
    permissions = []
    
    # Extract from realm access
    realm_access = token_data.get("realm_access", {})
    permissions.extend(realm_access.get("roles", []))
    
    # Extract from scope
    scope = token_data.get("scope", "")
    if scope:
        permissions.extend(scope.split(" "))
    
    return list(set(permissions))


async def get_user_roles(
    token_data: Annotated[dict, Depends(lambda: None)]  # Placeholder dependency
) -> List[str]:
    """
    Get current user's roles from token.
    
    Args:
        token_data: Token claims data
        
    Returns:
        List of role names
    """
    if not token_data:
        return []
    
    roles = []
    
    # Extract realm roles
    realm_access = token_data.get("realm_access", {})
    roles.extend(realm_access.get("roles", []))
    
    return list(set(roles))


__all__ = [
    "UserProfile",
    "CurrentUser",
    "CheckPermission",
    "TokenData",
    "create_current_user",
    "create_permission_checker",
    "create_token_data",
    "require_permissions",
    "get_user_permissions",
    "get_user_roles",
    "security",
]