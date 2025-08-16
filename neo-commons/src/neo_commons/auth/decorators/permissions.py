"""
Permission Decorators Implementation

Protocol-compliant permission decorators implementing auth security patterns with:
- Declarative permission requirements for FastAPI endpoints
- Automatic permission discovery and metadata collection
- OpenAPI documentation integration
- Multi-scope permission support (platform/tenant/user)
- Advanced security features (MFA, approval workflows, danger flags)
- Runtime validation coordination with dependency injection
"""

from typing import Optional, List, Union, Callable, Any
from functools import wraps
from loguru import logger


class RequirePermission:
    """
    Decorator class for declaring endpoint permission requirements.
    
    This decorator attaches permission metadata to endpoints for:
    1. Automatic permission discovery and sync
    2. Runtime permission validation (via dependency injection)
    3. OpenAPI documentation enhancement
    4. Security audit and compliance tracking
    
    Features:
    - Multi-permission support with AND/OR logic
    - Scope-based permissions (platform/tenant/user)
    - Security enhancement flags (MFA, approval, danger)
    - Metadata preservation through function wrapping
    - OpenAPI documentation integration
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
        Initialize permission requirement decorator.
        
        Args:
            permission: Permission code(s) required (e.g., "users:read", ["users:read", "users:list"])
            scope: Permission scope level ("platform", "tenant", "user")
            description: Human-readable description for documentation
            is_dangerous: Whether this is a dangerous operation requiring extra confirmation
            requires_mfa: Whether MFA is required for this operation
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
        The actual runtime validation is handled by FastAPI dependency injection.
        
        Args:
            func: Function to decorate
            
        Returns:
            Decorated function with permission metadata
        """
        # Store permission metadata on the function (matching source)
        if not hasattr(func, '_permissions'):
            func._permissions = []
        
        # Add this permission requirement (matching source)
        func._permissions.append({
            'permissions': self.permissions,
            'scope': self.scope,
            'description': self.description,
            'is_dangerous': self.is_dangerous,
            'requires_mfa': self.requires_mfa,
            'requires_approval': self.requires_approval,
            'any_of': self.any_of
        })
        
        # Add to function's docstring for OpenAPI (matching source)
        if func.__doc__:
            permissions_doc = f"\n\nRequired Permissions: {', '.join(self.permissions)} (Scope: {self.scope})"
            func.__doc__ += permissions_doc
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Runtime validation is handled by adding the dependency (matching source)
            # The actual validation happens via FastAPI dependency injection
            # when the endpoint is called
            return await func(*args, **kwargs)
        
        # Preserve the permission metadata (matching source)
        wrapper._permissions = func._permissions
        
        logger.debug(f"Applied permission requirements to {func.__name__}: {self.permissions}")
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
    
    Convenience function for creating permission decorators without class instantiation.
    
    Usage Examples:
        @require_permission("users:read")
        async def get_users():
            pass
        
        @require_permission(["users:read", "users:list"], any_of=True)
        async def view_users():
            pass
        
        @require_permission("admin:delete", scope="platform", is_dangerous=True, requires_mfa=True)
        async def delete_everything():
            pass
    
    Args:
        permission: Permission code(s) required
        scope: Permission scope level ("platform", "tenant", "user")
        description: Human-readable description for documentation
        is_dangerous: Whether this is a dangerous operation
        requires_mfa: Whether MFA is required
        requires_approval: Whether approval workflow is required
        any_of: If True, user needs ANY of the permissions; if False, needs ALL
    
    Returns:
        Decorator function with specified permission requirements
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
    
    Used by permission discovery systems to scan endpoints and build
    permission registries for dynamic permission management.
    """
    
    @staticmethod
    def extract(func: Callable) -> List[dict]:
        """
        Extract permission metadata from a function.
        
        Handles both direct decoration and wrapped functions to ensure
        metadata is preserved through multiple decorator layers.
        
        Args:
            func: Function to extract metadata from
            
        Returns:
            List of permission requirement dictionaries
        """
        if hasattr(func, '_permissions'):
            return func._permissions
        
        # Check if it's wrapped (matching source)
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
            True if function has permission requirements
        """
        return len(PermissionMetadata.extract(func)) > 0
    
    @staticmethod
    def get_all_permissions(func: Callable) -> List[str]:
        """
        Get all permission codes required by a function.
        
        Args:
            func: Function to analyze
            
        Returns:
            Flattened list of all permission codes
        """
        metadata = PermissionMetadata.extract(func)
        all_permissions = []
        
        for perm_meta in metadata:
            all_permissions.extend(perm_meta.get('permissions', []))
        
        return list(set(all_permissions))  # Remove duplicates
    
    @staticmethod
    def get_dangerous_operations(func: Callable) -> List[dict]:
        """
        Get dangerous operations metadata from a function.
        
        Args:
            func: Function to analyze
            
        Returns:
            List of dangerous operation metadata
        """
        metadata = PermissionMetadata.extract(func)
        return [meta for meta in metadata if meta.get('is_dangerous', False)]
    
    @staticmethod
    def requires_mfa(func: Callable) -> bool:
        """
        Check if function requires MFA.
        
        Args:
            func: Function to check
            
        Returns:
            True if any permission requirement needs MFA
        """
        metadata = PermissionMetadata.extract(func)
        return any(meta.get('requires_mfa', False) for meta in metadata)
    
    @staticmethod
    def requires_approval(func: Callable) -> bool:
        """
        Check if function requires approval workflow.
        
        Args:
            func: Function to check
            
        Returns:
            True if any permission requirement needs approval
        """
        metadata = PermissionMetadata.extract(func)
        return any(meta.get('requires_approval', False) for meta in metadata)
    
    @staticmethod
    def get_scopes(func: Callable) -> List[str]:
        """
        Get all permission scopes used by a function.
        
        Args:
            func: Function to analyze
            
        Returns:
            List of unique scopes
        """
        metadata = PermissionMetadata.extract(func)
        scopes = [meta.get('scope', 'platform') for meta in metadata]
        return list(set(scopes))
    
    @staticmethod
    def to_openapi_security(func: Callable) -> List[dict]:
        """
        Convert permission metadata to OpenAPI security requirements.
        
        Args:
            func: Function to analyze
            
        Returns:
            OpenAPI-compatible security requirements
        """
        metadata = PermissionMetadata.extract(func)
        security_requirements = []
        
        for meta in metadata:
            permissions = meta.get('permissions', [])
            scope = meta.get('scope', 'platform')
            
            # Create OpenAPI security requirement
            security_requirements.append({
                "OAuth2": permissions,
                "scope": scope,
                "description": meta.get('description', f"Requires {', '.join(permissions)}")
            })
        
        return security_requirements