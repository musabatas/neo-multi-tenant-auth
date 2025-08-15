"""
Permission decorators for function-level authorization.

Provides decorators for protecting functions and methods with permission checks.
"""
import functools
from typing import List, Optional, Callable, Any
from loguru import logger

from ...domain.value_objects.user_context import UserContext
from ...domain.value_objects.tenant_context import TenantContext
from ...application.services.permission_service import PermissionService
from ...application.services.role_service import RoleService


class PermissionError(Exception):
    """Exception raised when permission check fails."""
    
    def __init__(self, message: str, required_permission: str, user_id: str):
        self.message = message
        self.required_permission = required_permission
        self.user_id = user_id
        super().__init__(message)


def permission_required(
    permission: str,
    tenant_scoped: bool = True,
    cache_ttl: int = 300
):
    """
    Decorator to require a specific permission for function execution.
    
    Args:
        permission: Permission code required (e.g., "users:read")
        tenant_scoped: Whether permission is tenant-scoped
        cache_ttl: Cache TTL for permission check results
    
    Usage:
        @permission_required("users:read")
        async def get_user(user_id: str, context: UserContext):
            return await user_service.get_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Extract contexts from function arguments
            user_context = _extract_user_context(args, kwargs)
            tenant_context = _extract_tenant_context(args, kwargs) if tenant_scoped else None
            
            if not user_context:
                raise PermissionError(
                    "No user context found in function arguments",
                    permission,
                    "unknown"
                )
            
            # Get permission service (would be injected via DI in real implementation)
            permission_service = _get_permission_service()
            
            # Check permission
            result = await permission_service.check_permission(
                user_context, 
                permission, 
                tenant_context
            )
            
            if not result.granted:
                logger.warning(
                    f"Permission denied for user {user_context.user_id}: {permission}",
                    extra={
                        "user_id": user_context.user_id,
                        "permission": permission,
                        "tenant_id": tenant_context.tenant_id if tenant_context else None,
                        "function": func.__name__
                    }
                )
                raise PermissionError(
                    f"Permission denied: {permission}",
                    permission,
                    user_context.user_id
                )
            
            logger.debug(
                f"Permission granted for user {user_context.user_id}: {permission}",
                extra={
                    "user_id": user_context.user_id,
                    "permission": permission,
                    "from_cache": result.from_cache,
                    "function": func.__name__
                }
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def role_required(
    role_code: str,
    tenant_scoped: bool = True
):
    """
    Decorator to require a specific role for function execution.
    
    Args:
        role_code: Role code required (e.g., "admin", "manager")
        tenant_scoped: Whether role is tenant-scoped
    
    Usage:
        @role_required("admin")
        async def delete_user(user_id: str, context: UserContext):
            return await user_service.delete_user(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            user_context = _extract_user_context(args, kwargs)
            tenant_context = _extract_tenant_context(args, kwargs) if tenant_scoped else None
            
            if not user_context:
                raise PermissionError(
                    "No user context found in function arguments",
                    f"role:{role_code}",
                    "unknown"
                )
            
            # Get role service
            role_service = _get_role_service()
            
            # Get user roles
            user_roles = await role_service.get_user_roles(user_context, tenant_context)
            
            # Check if user has required role
            has_role = any(role.code == role_code for role in user_roles)
            
            if not has_role:
                logger.warning(
                    f"Role denied for user {user_context.user_id}: {role_code}",
                    extra={
                        "user_id": user_context.user_id,
                        "required_role": role_code,
                        "user_roles": [role.code for role in user_roles],
                        "function": func.__name__
                    }
                )
                raise PermissionError(
                    f"Role required: {role_code}",
                    f"role:{role_code}",
                    user_context.user_id
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def superadmin_required():
    """
    Decorator to require superadmin access for function execution.
    
    Usage:
        @superadmin_required()
        async def reset_system(context: UserContext):
            return await system_service.reset()
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            user_context = _extract_user_context(args, kwargs)
            
            if not user_context:
                raise PermissionError(
                    "No user context found in function arguments",
                    "superadmin",
                    "unknown"
                )
            
            if not user_context.is_superadmin:
                logger.warning(
                    f"Superadmin access denied for user {user_context.user_id}",
                    extra={
                        "user_id": user_context.user_id,
                        "function": func.__name__
                    }
                )
                raise PermissionError(
                    "Superadmin access required",
                    "superadmin",
                    user_context.user_id
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def tenant_access_required(tenant_id: Optional[str] = None):
    """
    Decorator to require tenant access for function execution.
    
    Args:
        tenant_id: Specific tenant ID required (None for current tenant)
    
    Usage:
        @tenant_access_required()
        async def get_tenant_users(context: UserContext, tenant_context: TenantContext):
            return await user_service.get_tenant_users(tenant_context.tenant_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            user_context = _extract_user_context(args, kwargs)
            tenant_context = _extract_tenant_context(args, kwargs)
            
            if not user_context:
                raise PermissionError(
                    "No user context found in function arguments",
                    "tenant_access",
                    "unknown"
                )
            
            # Superadmin bypasses tenant restrictions
            if user_context.is_superadmin:
                return await func(*args, **kwargs)
            
            # Check tenant context
            if not tenant_context:
                raise PermissionError(
                    "Tenant context required",
                    "tenant_access",
                    user_context.user_id
                )
            
            # Check specific tenant if required
            required_tenant = tenant_id or tenant_context.tenant_id
            if not user_context.matches_context(required_tenant):
                logger.warning(
                    f"Tenant access denied for user {user_context.user_id} to tenant {required_tenant}",
                    extra={
                        "user_id": user_context.user_id,
                        "required_tenant": required_tenant,
                        "user_tenant": user_context.tenant_id,
                        "function": func.__name__
                    }
                )
                raise PermissionError(
                    f"No access to tenant {required_tenant}",
                    "tenant_access",
                    user_context.user_id
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def _extract_user_context(args: tuple, kwargs: dict) -> Optional[UserContext]:
    """Extract UserContext from function arguments."""
    # Check kwargs first
    for key, value in kwargs.items():
        if isinstance(value, UserContext):
            return value
        if key.lower() in ["user_context", "user", "context", "current_user"]:
            if isinstance(value, UserContext):
                return value
    
    # Check args
    for arg in args:
        if isinstance(arg, UserContext):
            return arg
    
    return None


def _extract_tenant_context(args: tuple, kwargs: dict) -> Optional[TenantContext]:
    """Extract TenantContext from function arguments."""
    # Check kwargs first
    for key, value in kwargs.items():
        if isinstance(value, TenantContext):
            return value
        if key.lower() in ["tenant_context", "tenant"]:
            if isinstance(value, TenantContext):
                return value
    
    # Check args
    for arg in args:
        if isinstance(arg, TenantContext):
            return arg
    
    return None


def _get_permission_service() -> PermissionService:
    """Get permission service instance (would be injected via DI)."""
    # This would be replaced with proper dependency injection
    raise NotImplementedError("Configure permission service via DI container")


def _get_role_service() -> RoleService:
    """Get role service instance (would be injected via DI)."""
    # This would be replaced with proper dependency injection
    raise NotImplementedError("Configure role service via DI container")