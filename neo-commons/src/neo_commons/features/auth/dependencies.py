"""FastAPI authentication dependencies."""

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...core.exceptions.auth import AuthenticationError, AuthorizationError, InvalidTokenError
from ...core.value_objects.identifiers import PermissionCode, RealmId, RoleCode, TenantId
from .entities.auth_context import AuthContext
from .entities.protocols import (
    AuthServiceProtocol,
    JWTValidatorProtocol,
    RealmManagerProtocol,
    TokenServiceProtocol,
    UserMapperProtocol,
)

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


class AuthDependencyError(HTTPException):
    """Base exception for authentication dependencies."""
    
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(status_code=status_code, detail=detail)


class AuthDependencies:
    """FastAPI authentication dependencies factory."""
    
    def __init__(
        self,
        auth_service: AuthServiceProtocol,
        jwt_validator: JWTValidatorProtocol,
        token_service: TokenServiceProtocol,
        user_mapper: UserMapperProtocol,
        realm_manager: RealmManagerProtocol,
    ):
        """Initialize auth dependencies."""
        self.auth_service = auth_service
        self.jwt_validator = jwt_validator
        self.token_service = token_service
        self.user_mapper = user_mapper
        self.realm_manager = realm_manager
    
    async def get_current_user(
        self,
        request: Request,
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ) -> AuthContext:
        """Get current authenticated user from JWT token."""
        try:
            # Extract tenant from request (could be from subdomain, header, or path)
            tenant_id = await self._extract_tenant_id(request)
            
            # Get realm configuration for tenant
            realm_config = await self.realm_manager.get_realm_config(tenant_id)
            realm_id = realm_config.realm_id
            
            # Validate token and get auth context
            auth_context = await self.token_service.validate_and_cache_token(
                credentials.credentials, realm_id
            )
            
            # Ensure tenant matches
            if auth_context.tenant_id != tenant_id:
                logger.warning(
                    f"Token tenant {auth_context.tenant_id.value} doesn't match "
                    f"request tenant {tenant_id.value}"
                )
                raise AuthDependencyError("Invalid token for this tenant")
            
            logger.debug(f"Authenticated user {auth_context.user_id.value}")
            return auth_context
        
        except InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise AuthDependencyError(f"Invalid token: {e}")
        
        except AuthenticationError as e:
            logger.warning(f"Authentication failed: {e}")
            raise AuthDependencyError(f"Authentication failed: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected authentication error: {e}")
            raise AuthDependencyError("Authentication failed")
    
    async def get_optional_user(
        self,
        request: Request,
        credentials: Annotated[
            Optional[HTTPAuthorizationCredentials], 
            Depends(HTTPBearer(auto_error=False))
        ],
    ) -> Optional[AuthContext]:
        """Get current user if token is provided (optional authentication)."""
        if not credentials:
            return None
        
        try:
            return await self.get_current_user(request, credentials)
        
        except AuthDependencyError:
            # Return None for optional authentication
            return None
    
    def require_permission(self, permission: str | PermissionCode):
        """Require specific permission."""
        perm_code = permission if isinstance(permission, PermissionCode) else PermissionCode(permission)
        
        async def dependency(
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            if not current_user.has_permission(perm_code):
                logger.warning(
                    f"User {current_user.user_id.value} lacks permission: {perm_code.value}"
                )
                raise AuthDependencyError(
                    f"Permission required: {perm_code.value}",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return current_user
        
        return dependency
    
    def require_any_permission(self, permissions: list[str | PermissionCode]):
        """Require any of the specified permissions."""
        perm_codes = [
            perm if isinstance(perm, PermissionCode) else PermissionCode(perm)
            for perm in permissions
        ]
        
        async def dependency(
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            if not current_user.has_any_permission(perm_codes):
                perm_names = [perm.value for perm in perm_codes]
                logger.warning(
                    f"User {current_user.user_id.value} lacks any permission from: {perm_names}"
                )
                raise AuthDependencyError(
                    f"One of these permissions required: {', '.join(perm_names)}",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return current_user
        
        return dependency
    
    def require_all_permissions(self, permissions: list[str | PermissionCode]):
        """Require all of the specified permissions."""
        perm_codes = [
            perm if isinstance(perm, PermissionCode) else PermissionCode(perm)
            for perm in permissions
        ]
        
        async def dependency(
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            if not current_user.has_all_permissions(perm_codes):
                perm_names = [perm.value for perm in perm_codes]
                logger.warning(
                    f"User {current_user.user_id.value} lacks required permissions: {perm_names}"
                )
                raise AuthDependencyError(
                    f"All permissions required: {', '.join(perm_names)}",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return current_user
        
        return dependency
    
    def require_role(self, role: str | RoleCode):
        """Require specific role."""
        role_code = role if isinstance(role, RoleCode) else RoleCode(role)
        
        async def dependency(
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            if not current_user.has_role(role_code):
                logger.warning(
                    f"User {current_user.user_id.value} lacks role: {role_code.value}"
                )
                raise AuthDependencyError(
                    f"Role required: {role_code.value}",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return current_user
        
        return dependency
    
    def require_any_role(self, roles: list[str | RoleCode]):
        """Require any of the specified roles."""
        role_codes = [
            role if isinstance(role, RoleCode) else RoleCode(role)
            for role in roles
        ]
        
        async def dependency(
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            if not current_user.has_any_role(role_codes):
                role_names = [role.value for role in role_codes]
                logger.warning(
                    f"User {current_user.user_id.value} lacks any role from: {role_names}"
                )
                raise AuthDependencyError(
                    f"One of these roles required: {', '.join(role_names)}",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return current_user
        
        return dependency
    
    def require_tenant_admin(self):
        """Require tenant admin role."""
        async def dependency(
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            admin_roles = [RoleCode("tenant_admin"), RoleCode("admin"), RoleCode("super_admin")]
            
            if not current_user.has_any_role(admin_roles):
                logger.warning(
                    f"User {current_user.user_id.value} lacks tenant admin privileges"
                )
                raise AuthDependencyError(
                    "Tenant admin privileges required",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return current_user
        
        return dependency
    
    def require_platform_admin(self):
        """Require platform admin role."""
        async def dependency(
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            admin_roles = [RoleCode("platform_admin"), RoleCode("super_admin")]
            
            if not current_user.has_any_role(admin_roles):
                logger.warning(
                    f"User {current_user.user_id.value} lacks platform admin privileges"
                )
                raise AuthDependencyError(
                    "Platform admin privileges required",
                    status_code=status.HTTP_403_FORBIDDEN
                )
            return current_user
        
        return dependency
    
    def require_fresh_token(self, max_age_seconds: int = 300):
        """Require a fresh token (recently issued)."""
        async def dependency(
            request: Request,
            credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
            current_user: Annotated[AuthContext, Depends(self.get_current_user)]
        ) -> AuthContext:
            # Check token freshness
            is_fresh = await self.token_service.validate_token_freshness(
                credentials.credentials, max_age_seconds
            )
            
            if not is_fresh:
                logger.warning(
                    f"Stale token used by user {current_user.user_id.value}"
                )
                raise AuthDependencyError(
                    "Fresh authentication required for this operation",
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            return current_user
        
        return dependency
    
    async def _extract_tenant_id(self, request: Request) -> TenantId:
        """Extract tenant ID from request."""
        # Strategy 1: Check custom header
        tenant_header = request.headers.get("x-tenant-id")
        if tenant_header:
            return TenantId(tenant_header)
        
        # Strategy 2: Check subdomain
        host = request.headers.get("host", "")
        if "." in host:
            subdomain = host.split(".")[0]
            if subdomain and subdomain != "api" and subdomain != "www":
                return TenantId(subdomain)
        
        # Strategy 3: Check path parameter
        path_parts = request.url.path.split("/")
        if len(path_parts) >= 3 and path_parts[1] == "tenant":
            return TenantId(path_parts[2])
        
        # Strategy 4: Check query parameter
        tenant_query = request.query_params.get("tenant_id")
        if tenant_query:
            return TenantId(tenant_query)
        
        # Default: Raise error if no tenant found
        logger.error("No tenant ID found in request")
        raise AuthDependencyError(
            "Tenant identification required",
            status_code=status.HTTP_400_BAD_REQUEST
        )


# Convenience functions for global auth dependencies
_auth_dependencies: Optional[AuthDependencies] = None


def init_auth_dependencies(
    auth_service: AuthServiceProtocol,
    jwt_validator: JWTValidatorProtocol,
    token_service: TokenServiceProtocol,
    user_mapper: UserMapperProtocol,
    realm_manager: RealmManagerProtocol,
) -> AuthDependencies:
    """Initialize global auth dependencies."""
    global _auth_dependencies
    _auth_dependencies = AuthDependencies(
        auth_service=auth_service,
        jwt_validator=jwt_validator,
        token_service=token_service,
        user_mapper=user_mapper,
        realm_manager=realm_manager,
    )
    return _auth_dependencies


def get_auth_dependencies() -> AuthDependencies:
    """Get global auth dependencies."""
    if not _auth_dependencies:
        raise RuntimeError(
            "Auth dependencies not initialized. Call init_auth_dependencies() first."
        )
    return _auth_dependencies


# Convenience dependency functions

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> AuthContext:
    """Get current authenticated user (global dependency)."""
    deps = get_auth_dependencies()
    return await deps.get_current_user(request, credentials)


async def get_optional_user(
    request: Request,
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], 
        Depends(HTTPBearer(auto_error=False))
    ],
) -> Optional[AuthContext]:
    """Get current user if token provided (global dependency)."""
    deps = get_auth_dependencies()
    return await deps.get_optional_user(request, credentials)


def require_permission(permission: str | PermissionCode):
    """Require specific permission (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_permission(permission)


def require_any_permission(permissions: list[str | PermissionCode]):
    """Require any of the specified permissions (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_any_permission(permissions)


def require_all_permissions(permissions: list[str | PermissionCode]):
    """Require all of the specified permissions (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_all_permissions(permissions)


def require_role(role: str | RoleCode):
    """Require specific role (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_role(role)


def require_any_role(roles: list[str | RoleCode]):
    """Require any of the specified roles (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_any_role(roles)


def require_tenant_admin():
    """Require tenant admin role (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_tenant_admin()


def require_platform_admin():
    """Require platform admin role (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_platform_admin()


def require_fresh_token(max_age_seconds: int = 300):
    """Require fresh token (global dependency)."""
    deps = get_auth_dependencies()
    return deps.require_fresh_token(max_age_seconds)