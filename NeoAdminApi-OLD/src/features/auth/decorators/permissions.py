"""
Permission decorators for endpoint protection.
"""
from typing import Optional, List, Union, Callable, Any
from functools import wraps
from fastapi import HTTPException, status
from loguru import logger


class RequirePermission:
    """
    Decorator class for declaring endpoint permission requirements.
    
    This decorator attaches permission metadata to endpoints for:
    1. Automatic permission discovery and sync
    2. Runtime permission validation
    3. OpenAPI documentation
    """
    
    def __init__(
        self,
        permission: Union[str, List[str]],
        scope: str = "platform",
        description: Optional[str] = None,
        is_dangerous: bool = False,
        requires_mfa: bool = False,
        requires_approval: bool = False,
        any_of: bool = False
    ):
        """
        Initialize permission requirement.
        
        Args:
            permission: Permission code(s) required (e.g., "users:read")
            scope: Permission scope level ("platform", "tenant", "user")
            description: Human-readable description
            is_dangerous: Whether this is a dangerous operation
            requires_mfa: Whether MFA is required
            requires_approval: Whether approval workflow is required
            any_of: If True, user needs ANY of the permissions; if False, needs ALL
        """
        self.permissions = [permission] if isinstance(permission, str) else permission
        self.scope = scope
        self.description = description
        self.is_dangerous = is_dangerous
        self.requires_mfa = requires_mfa
        self.requires_approval = requires_approval
        self.any_of = any_of
    
    def __call__(self, func: Callable) -> Callable:
        """
        Apply decorator to function.
        
        Attaches permission metadata for discovery and adds to OpenAPI.
        """
        # Store permission metadata on the function
        if not hasattr(func, '_permissions'):
            func._permissions = []
        
        # Add this permission requirement
        func._permissions.append({
            'permissions': self.permissions,
            'scope': self.scope,
            'description': self.description,
            'is_dangerous': self.is_dangerous,
            'requires_mfa': self.requires_mfa,
            'requires_approval': self.requires_approval,
            'any_of': self.any_of
        })
        
        # Add to function's docstring for OpenAPI
        if func.__doc__:
            permissions_doc = f"\n\nRequired Permissions: {', '.join(self.permissions)} (Scope: {self.scope})"
            func.__doc__ += permissions_doc
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Runtime validation is handled by adding the dependency
            # The actual validation happens via FastAPI dependency injection
            # when the endpoint is called
            return await func(*args, **kwargs)
        
        # Preserve the permission metadata
        wrapper._permissions = func._permissions
        
        return wrapper


def require_permission(
    permission: Union[str, List[str]],
    scope: str = "platform",
    description: Optional[str] = None,
    is_dangerous: bool = False,
    requires_mfa: bool = False,
    requires_approval: bool = False,
    any_of: bool = False
) -> Callable:
    """
    Functional decorator for declaring endpoint permissions.
    
    Usage:
        @require_permission("users:read")
        async def get_users():
            pass
        
        @require_permission(["users:read", "users:list"], any_of=True)
        async def view_users():
            pass
    
    Args:
        permission: Permission code(s) required
        scope: Permission scope level
        description: Human-readable description
        is_dangerous: Whether this is a dangerous operation
        requires_mfa: Whether MFA is required
        requires_approval: Whether approval workflow is required
        any_of: If True, user needs ANY of the permissions; if False, needs ALL
    
    Returns:
        Decorated function with permission metadata
    """
    decorator = RequirePermission(
        permission=permission,
        scope=scope,
        description=description,
        is_dangerous=is_dangerous,
        requires_mfa=requires_mfa,
        requires_approval=requires_approval,
        any_of=any_of
    )
    return decorator


class PermissionMetadata:
    """
    Helper class to extract permission metadata from decorated endpoints.
    """
    
    @staticmethod
    def extract(func: Callable) -> List[dict]:
        """
        Extract permission metadata from a function.
        
        Args:
            func: Function to extract metadata from
            
        Returns:
            List of permission requirements
        """
        if hasattr(func, '_permissions'):
            return func._permissions
        
        # Check if it's wrapped
        if hasattr(func, '__wrapped__'):
            return PermissionMetadata.extract(func.__wrapped__)
        
        return []
    
    @staticmethod
    def has_permissions(func: Callable) -> bool:
        """
        Check if function has permission requirements.
        
        Args:
            func: Function to check
            
        Returns:
            True if has permissions
        """
        return len(PermissionMetadata.extract(func)) > 0