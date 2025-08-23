"""FastAPI dependency injection helpers for middleware and authentication.

Provides dependency functions for extracting user context, tenant information,
request context, and enforcing permissions/roles in FastAPI route handlers.
"""

from typing import Optional, List, Union, Callable, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ...core.value_objects import UserId, TenantId, PermissionCode, RoleCode
from ...core.shared.context import RequestContext
from ...core.exceptions import AuthenticationError, AuthorizationError, PermissionDeniedError
from ...features.permissions.services import PermissionService
from ...features.users.services import UserService
from ...features.tenants.services import TenantService

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)


# Basic Context Dependencies

def get_request_context(request: Request) -> Optional[RequestContext]:
    """Get request context from middleware."""
    return getattr(request.state, 'user_context', None)


def get_current_user(request: Request) -> Optional[UserId]:
    """Get current authenticated user ID."""
    user_context = getattr(request.state, 'user_context', None)
    if user_context and user_context.user_id:
        return user_context.user_id
    return None


def get_current_tenant(request: Request) -> Optional[TenantId]:
    """Get current tenant ID from context."""
    # Try user context first
    user_context = getattr(request.state, 'user_context', None)
    if user_context and user_context.tenant_id:
        return user_context.tenant_id
    
    # Fallback to tenant context
    tenant_context = getattr(request.state, 'tenant_context', None)
    if tenant_context and tenant_context.get('tenant_id'):
        return TenantId(tenant_context['tenant_id'])
    
    return None


def get_tenant_context(request: Request) -> Optional[dict]:
    """Get full tenant context from middleware."""
    return getattr(request.state, 'tenant_context', None)


# Required Context Dependencies

def require_authentication(request: Request) -> UserId:
    """Require authenticated user, raise 401 if not authenticated."""
    user_id = get_current_user(request)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user_id


def require_tenant_context(request: Request) -> TenantId:
    """Require tenant context, raise 400 if not available."""
    tenant_id = get_current_tenant(request)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context required"
        )
    return tenant_id


def require_authenticated_tenant(request: Request) -> tuple[UserId, TenantId]:
    """Require both authentication and tenant context."""
    user_id = require_authentication(request)
    tenant_id = require_tenant_context(request)
    return user_id, tenant_id


# Permission-Based Dependencies

def require_permission(permission: Union[str, PermissionCode]):
    """Create a dependency that requires a specific permission.
    
    Usage:
        @router.get("/users")
        async def list_users(
            current_user: UserId = Depends(require_permission("users:list"))
        ):
            # Only users with 'users:list' permission can access this
            pass
    """
    if isinstance(permission, str):
        permission = PermissionCode(permission)
    
    async def _check_permission(
        request: Request,
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserId:
        user_id = require_authentication(request)
        tenant_id = get_current_tenant(request)
        
        try:
            has_permission = await permission_service.check_permission(
                user_id=user_id,
                permission=permission,
                tenant_id=tenant_id
            )
            
            if not has_permission:
                raise PermissionDeniedError(f"Permission required: {permission}")
            
            return user_id
        
        except PermissionDeniedError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )
    
    return _check_permission


def require_any_permission(permissions: List[Union[str, PermissionCode]]):
    """Create a dependency that requires any of the specified permissions.
    
    Usage:
        @router.get("/data")
        async def get_data(
            current_user: UserId = Depends(require_any_permission(["data:read", "admin:full"]))
        ):
            # User needs either 'data:read' OR 'admin:full' permission
            pass
    """
    permission_codes = [
        PermissionCode(p) if isinstance(p, str) else p 
        for p in permissions
    ]
    
    async def _check_any_permission(
        request: Request,
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserId:
        user_id = require_authentication(request)
        tenant_id = get_current_tenant(request)
        
        try:
            for permission in permission_codes:
                has_permission = await permission_service.check_permission(
                    user_id=user_id,
                    permission=permission,
                    tenant_id=tenant_id
                )
                
                if has_permission:
                    return user_id
            
            # No permissions matched
            raise PermissionDeniedError(f"One of these permissions required: {[str(p) for p in permission_codes]}")
        
        except PermissionDeniedError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {[str(p) for p in permission_codes]}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )
    
    return _check_any_permission


def require_all_permissions(permissions: List[Union[str, PermissionCode]]):
    """Create a dependency that requires all specified permissions.
    
    Usage:
        @router.delete("/admin/users/{user_id}")
        async def delete_user(
            current_user: UserId = Depends(require_all_permissions(["users:delete", "admin:users"]))
        ):
            # User needs BOTH 'users:delete' AND 'admin:users' permissions
            pass
    """
    permission_codes = [
        PermissionCode(p) if isinstance(p, str) else p 
        for p in permissions
    ]
    
    async def _check_all_permissions(
        request: Request,
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserId:
        user_id = require_authentication(request)
        tenant_id = get_current_tenant(request)
        
        try:
            for permission in permission_codes:
                has_permission = await permission_service.check_permission(
                    user_id=user_id,
                    permission=permission,
                    tenant_id=tenant_id
                )
                
                if not has_permission:
                    raise PermissionDeniedError(f"All permissions required: {[str(p) for p in permission_codes]}")
            
            return user_id
        
        except PermissionDeniedError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"All permissions required: {[str(p) for p in permission_codes]}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission check failed"
            )
    
    return _check_all_permissions


# Role-Based Dependencies

def require_role(role: Union[str, RoleCode]):
    """Create a dependency that requires a specific role.
    
    Usage:
        @router.get("/admin/settings")
        async def get_admin_settings(
            current_user: UserId = Depends(require_role("admin"))
        ):
            # Only users with 'admin' role can access this
            pass
    """
    if isinstance(role, str):
        role = RoleCode(role)
    
    async def _check_role(
        request: Request,
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserId:
        user_id = require_authentication(request)
        tenant_id = get_current_tenant(request)
        
        try:
            has_role = await permission_service.check_user_role(
                user_id=user_id,
                role=role,
                tenant_id=tenant_id
            )
            
            if not has_role:
                raise AuthorizationError(f"Role required: {role}")
            
            return user_id
        
        except AuthorizationError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role check failed"
            )
    
    return _check_role


def require_any_role(roles: List[Union[str, RoleCode]]):
    """Create a dependency that requires any of the specified roles.
    
    Usage:
        @router.get("/management")
        async def management_page(
            current_user: UserId = Depends(require_any_role(["admin", "manager"]))
        ):
            # User needs either 'admin' OR 'manager' role
            pass
    """
    role_codes = [
        RoleCode(r) if isinstance(r, str) else r 
        for r in roles
    ]
    
    async def _check_any_role(
        request: Request,
        permission_service: PermissionService = Depends(get_permission_service)
    ) -> UserId:
        user_id = require_authentication(request)
        tenant_id = get_current_tenant(request)
        
        try:
            for role in role_codes:
                has_role = await permission_service.check_user_role(
                    user_id=user_id,
                    role=role,
                    tenant_id=tenant_id
                )
                
                if has_role:
                    return user_id
            
            # No roles matched
            raise AuthorizationError(f"One of these roles required: {[str(r) for r in role_codes]}")
        
        except AuthorizationError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {[str(r) for r in role_codes]}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Role check failed"
            )
    
    return _check_any_role


# Optional Authentication Dependencies

def get_optional_user(request: Request) -> Optional[UserId]:
    """Get current user ID if authenticated, None otherwise.
    
    Usage:
        @router.get("/public-data")
        async def get_public_data(
            current_user: Optional[UserId] = Depends(get_optional_user)
        ):
            # Endpoint accessible to both authenticated and anonymous users
            if current_user:
                # Return personalized data
                pass
            else:
                # Return public data
                pass
    """
    return get_current_user(request)


def get_optional_tenant(request: Request) -> Optional[TenantId]:
    """Get current tenant ID if available, None otherwise."""
    return get_current_tenant(request)


# Service Dependencies (to be implemented by the application)

def get_permission_service() -> PermissionService:
    """Get permission service instance.
    
    This should be implemented by the application to provide the actual
    PermissionService instance, typically from a dependency injection container.
    """
    raise NotImplementedError(
        "get_permission_service must be implemented by the application"
    )


def get_user_service() -> UserService:
    """Get user service instance.
    
    This should be implemented by the application to provide the actual
    UserService instance, typically from a dependency injection container.
    """
    raise NotImplementedError(
        "get_user_service must be implemented by the application"
    )


def get_tenant_service() -> TenantService:
    """Get tenant service instance.
    
    This should be implemented by the application to provide the actual
    TenantService instance, typically from a dependency injection container.
    """
    raise NotImplementedError(
        "get_tenant_service must be implemented by the application"
    )


# Utility Dependencies

def get_request_id(request: Request) -> Optional[str]:
    """Get request ID from request state."""
    return getattr(request.state, 'request_id', None)


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers first
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to client host
    if hasattr(request, "client") and request.client:
        return request.client.host
    
    return "unknown"


def get_user_agent(request: Request) -> Optional[str]:
    """Get user agent from request headers."""
    return request.headers.get("User-Agent")


# Pagination Dependencies

def get_pagination(
    page: int = 1,
    limit: int = 20,
    max_limit: int = 100
) -> tuple[int, int, int]:
    """Get pagination parameters with validation.
    
    Returns:
        tuple: (page, limit, offset)
    
    Usage:
        @router.get("/users")
        async def list_users(
            pagination: tuple[int, int, int] = Depends(get_pagination)
        ):
            page, limit, offset = pagination
            # Use pagination parameters
            pass
    """
    # Validate and constrain parameters
    page = max(1, page)
    limit = min(max(1, limit), max_limit)
    offset = (page - 1) * limit
    
    return page, limit, offset


# Advanced Permission Dependencies

def require_resource_permission(resource_type: str, action: str):
    """Create a dependency for resource-specific permissions.
    
    Usage:
        @router.get("/projects/{project_id}")
        async def get_project(
            project_id: str,
            current_user: UserId = Depends(require_resource_permission("project", "read"))
        ):
            # Check for project:read permission
            pass
    """
    permission = PermissionCode(f"{resource_type}:{action}")
    return require_permission(permission)


def require_tenant_admin(request: Request) -> UserId:
    """Require tenant admin role for tenant-specific operations.
    
    Usage:
        @router.post("/tenant/settings")
        async def update_tenant_settings(
            current_user: UserId = Depends(require_tenant_admin)
        ):
            # Only tenant admins can modify tenant settings
            pass
    """
    return require_role("tenant_admin")(request)


def require_platform_admin(request: Request) -> UserId:
    """Require platform admin role for platform-wide operations.
    
    Usage:
        @router.get("/admin/system-status")
        async def get_system_status(
            current_user: UserId = Depends(require_platform_admin)
        ):
            # Only platform admins can access system status
            pass
    """
    return require_role("platform_admin")(request)