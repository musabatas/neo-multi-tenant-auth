"""
FastAPI authentication and authorization dependencies.

Provides dependency injection for authorization services and context.
"""
from typing import List, Optional, Callable, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...domain.value_objects.user_context import UserContext
from ...domain.value_objects.tenant_context import TenantContext
from ...application.services.permission_service import PermissionService
from ...application.services.role_service import RoleService
from ...application.services.token_validation_service import TokenValidationService
from ...infrastructure.repositories.permission_repository import PermissionRepository
from ...infrastructure.repositories.role_repository import RoleRepository
from ...infrastructure.cache.redis_permission_cache import RedisPermissionCache


# Security scheme
security = HTTPBearer()


# Service dependencies (would be configured via DI container)
def get_permission_repository() -> PermissionRepository:
    """Get permission repository instance."""
    # This would be configured via dependency injection container
    # For now, return a placeholder
    raise NotImplementedError("Configure permission repository via DI container")


def get_role_repository() -> RoleRepository:
    """Get role repository instance."""
    raise NotImplementedError("Configure role repository via DI container")


def get_permission_cache() -> RedisPermissionCache:
    """Get permission cache instance."""
    raise NotImplementedError("Configure permission cache via DI container")


def get_token_validation_service() -> TokenValidationService:
    """Get token validation service."""
    raise NotImplementedError("Configure token validation service via DI container")


def get_permission_service(
    repository: PermissionRepository = Depends(get_permission_repository),
    cache: RedisPermissionCache = Depends(get_permission_cache)
) -> PermissionService:
    """Get permission service with dependencies injected."""
    return PermissionService(repository, cache)


def get_role_service(
    repository: RoleRepository = Depends(get_role_repository),
    cache: RedisPermissionCache = Depends(get_permission_cache)
) -> RoleService:
    """Get role service with dependencies injected."""
    return RoleService(repository, cache)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    token_service: TokenValidationService = Depends(get_token_validation_service)
) -> UserContext:
    """
    Extract and validate current user from JWT token.
    
    Returns UserContext for authorization decisions.
    """
    try:
        # Extract tenant ID from request (could be from path, query, or header)
        tenant_id = _extract_tenant_id_from_request(request)
        
        # Get IP and User-Agent for security context
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        # Validate token and extract user context
        user_context = await token_service.extract_user_context(
            token=credentials.credentials,
            tenant_id=tenant_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return user_context
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def get_user_context(
    user: UserContext = Depends(get_current_user)
) -> UserContext:
    """Get user context (alias for get_current_user)."""
    return user


async def get_tenant_context(
    request: Request,
    user: UserContext = Depends(get_current_user)
) -> Optional[TenantContext]:
    """
    Extract tenant context from request.
    
    Returns None for platform-level operations.
    """
    tenant_id = _extract_tenant_id_from_request(request)
    if not tenant_id:
        return None
    
    # This would typically load tenant details from database
    # For now, create minimal context
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug=f"tenant-{tenant_id}",
        tenant_name=f"Tenant {tenant_id}",
        organization_id=f"org-{tenant_id}"
    )


def require_permission(permission: str) -> Callable:
    """
    Dependency factory for requiring a specific permission.
    
    Usage:
        @app.get("/users", dependencies=[Depends(require_permission("users:read"))])
    """
    async def permission_dependency(
        user: UserContext = Depends(get_current_user),
        tenant: Optional[TenantContext] = Depends(get_tenant_context),
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserContext:
        
        result = await permission_service.check_permission(user, permission, tenant)
        
        if not result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )
        
        return user
    
    return permission_dependency


def require_any_permission(permissions: List[str]) -> Callable:
    """
    Dependency factory for requiring any of the specified permissions.
    
    Usage:
        @app.get("/admin", dependencies=[Depends(require_any_permission(["admin:read", "superadmin:*"]))])
    """
    async def permission_dependency(
        user: UserContext = Depends(get_current_user),
        tenant: Optional[TenantContext] = Depends(get_tenant_context),
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserContext:
        
        result = await permission_service.has_any_permission(user, permissions, tenant)
        
        if not result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires any of {permissions}"
            )
        
        return user
    
    return permission_dependency


def require_all_permissions(permissions: List[str]) -> Callable:
    """
    Dependency factory for requiring all of the specified permissions.
    
    Usage:
        @app.delete("/users/{id}", dependencies=[Depends(require_all_permissions(["users:delete", "admin:write"]))])
    """
    async def permission_dependency(
        user: UserContext = Depends(get_current_user),
        tenant: Optional[TenantContext] = Depends(get_tenant_context),
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserContext:
        
        result = await permission_service.has_all_permissions(user, permissions, tenant)
        
        if not result.granted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires all of {permissions}"
            )
        
        return user
    
    return permission_dependency


def require_superadmin() -> Callable:
    """
    Dependency for requiring superadmin access.
    
    Usage:
        @app.post("/system/config", dependencies=[Depends(require_superadmin())])
    """
    async def superadmin_dependency(
        user: UserContext = Depends(get_current_user)
    ) -> UserContext:
        
        if not user.is_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Superadmin access required"
            )
        
        return user
    
    return superadmin_dependency


def require_tenant_access(required_tenant_id: Optional[str] = None) -> Callable:
    """
    Dependency for requiring tenant access.
    
    Args:
        required_tenant_id: Specific tenant ID required (None for any tenant access)
    
    Usage:
        @app.get("/tenants/{tenant_id}/users", dependencies=[Depends(require_tenant_access())])
    """
    async def tenant_dependency(
        user: UserContext = Depends(get_current_user),
        tenant: Optional[TenantContext] = Depends(get_tenant_context)
    ) -> UserContext:
        
        # Superadmin bypasses tenant restrictions
        if user.is_superadmin:
            return user
        
        # Check if user has tenant context
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant access required"
            )
        
        # Check specific tenant if required
        if required_tenant_id and tenant.tenant_id != required_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to tenant {required_tenant_id} required"
            )
        
        # Check if user has access to this tenant
        if not user.matches_context(tenant.tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to specified tenant"
            )
        
        return user
    
    return tenant_dependency


def _extract_tenant_id_from_request(request: Request) -> Optional[str]:
    """
    Extract tenant ID from request.
    
    Checks multiple sources:
    1. Path parameter: /tenants/{tenant_id}/...
    2. Query parameter: ?tenant_id=...
    3. Header: X-Tenant-ID
    """
    # Check path parameters
    if "tenant_id" in request.path_params:
        return request.path_params["tenant_id"]
    
    # Check query parameters
    if "tenant_id" in request.query_params:
        return request.query_params["tenant_id"]
    
    # Check headers
    return request.headers.get("X-Tenant-ID")