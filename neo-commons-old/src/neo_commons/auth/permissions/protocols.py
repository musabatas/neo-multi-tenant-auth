"""
Permission Management Protocols for Neo-Commons

Protocol definitions for permission validation, registry management,
caching, and wildcard matching in multi-tenant environments.
"""
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable, Set
from ..core import PermissionScope


@runtime_checkable
class PermissionValidatorProtocol(Protocol):
    """Protocol for permission checking with tenant context."""
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None,
        scope: PermissionScope = PermissionScope.PLATFORM
    ) -> bool:
        """Check if user has specific permission."""
        ...
    
    async def check_any_permission(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        scope: PermissionScope = PermissionScope.PLATFORM
    ) -> bool:
        """Check if user has any of the specified permissions."""
        ...
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        scope: Optional[PermissionScope] = None
    ) -> List[Dict[str, Any]]:
        """Get all permissions for user."""
        ...


@runtime_checkable
class PermissionRegistryProtocol(Protocol):
    """Protocol for permission registry and definitions."""
    
    async def validate_permission(self, permission_code: str) -> bool:
        """Validate if a permission code exists in the registry."""
        ...
    
    async def get_permission(self, permission_code: str) -> Optional[Any]:
        """Get permission definition by code."""
        ...
    
    async def get_permissions_by_scope(self, scope: str) -> List[Any]:
        """Get all permissions for a specific scope."""
        ...
    
    async def get_dangerous_permissions(self) -> List[Any]:
        """Get all permissions marked as dangerous."""
        ...
    
    async def get_mfa_required_permissions(self) -> List[Any]:
        """Get all permissions requiring MFA."""
        ...
    
    async def get_approval_required_permissions(self) -> List[Any]:
        """Get all permissions requiring approval."""
        ...
    
    async def expand_permission_group(self, group_name: str) -> List[str]:
        """Expand a permission group to individual permission codes."""
        ...
    
    async def check_permission_security(self, permission_code: str) -> Dict[str, Any]:
        """Check security requirements for a permission."""
        ...
    
    async def list_all_permissions(self) -> List[Any]:
        """Get all registered permissions."""
        ...
    
    async def list_permission_codes(self) -> List[str]:
        """Get all registered permission codes."""
        ...
    
    async def get_resource_permissions(self, resource: str) -> List[Any]:
        """Get all permissions for a specific resource."""
        ...
    
    async def register_dynamic_permission(self, permission: Any) -> bool:
        """Register a dynamic permission at runtime."""
        ...
    
    async def get_permissions_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the permission registry."""
        ...


@runtime_checkable
class PermissionDecoratorProtocol(Protocol):
    """Protocol for permission decorators with metadata extraction."""
    
    def create_permission_decorator(
        self,
        permission: Union[str, List[str]],
        scope: PermissionScope = PermissionScope.PLATFORM,
        any_of: bool = False
    ) -> Any:
        """Create permission decorator with specified requirements."""
        ...


@runtime_checkable
class PermissionCheckerProtocol(Protocol):
    """Protocol for comprehensive permission checking with caching."""
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission."""
        ...
    
    async def check_permissions(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        require_all: bool = True
    ) -> bool:
        """Check if user has required permissions."""
        ...
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get all permissions for a user."""
        ...
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all roles for a user."""
        ...
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """Get a summary of user permissions grouped by resource."""
        ...
    
    async def has_wildcard_permission(
        self,
        user_id: str,
        resource: str,
        action: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has wildcard permission for resource/action."""
        ...


@runtime_checkable
class PermissionCacheProtocol(Protocol):
    """Protocol for permission caching with TTL and invalidation."""
    
    async def get_cached_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[List[str]]:
        """Get cached permissions for user."""
        ...
    
    async def set_cached_permissions(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        ttl: int = 300
    ) -> None:
        """Cache permissions for user with TTL."""
        ...
    
    async def get_cached_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get cached roles for user."""
        ...
    
    async def set_cached_roles(
        self,
        user_id: str,
        roles: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        ttl: int = 300
    ) -> None:
        """Cache roles for user with TTL."""
        ...
    
    async def get_cached_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Set[str]]]:
        """Get cached permission summary for user."""
        ...
    
    async def set_cached_permission_summary(
        self,
        user_id: str,
        summary: Dict[str, Set[str]],
        tenant_id: Optional[str] = None,
        ttl: int = 300
    ) -> None:
        """Cache permission summary for user with TTL."""
        ...
    
    async def invalidate_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """Invalidate cached permissions for user."""
        ...
    
    async def invalidate_role_permissions(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """Invalidate cached permissions for role."""
        ...
    
    async def invalidate_tenant_permissions(
        self,
        tenant_id: str
    ) -> None:
        """Invalidate all cached permissions for tenant."""
        ...
    
    async def clear_all_permission_cache(self) -> None:
        """Clear all permission-related cache entries."""
        ...


@runtime_checkable
class PermissionDataSourceProtocol(Protocol):
    """Protocol for permission data source operations."""
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user permissions from data source."""
        ...
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user roles from data source."""
        ...
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """Get a summary of user permissions grouped by resource."""
        ...
    
    async def get_users_with_role(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get all user IDs that have a specific role."""
        ...
    
    async def validate_user_exists(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Validate that a user exists in the data source."""
        ...


@runtime_checkable
class WildcardMatcherProtocol(Protocol):
    """Protocol for wildcard permission matching."""
    
    def matches_permission(
        self,
        required_permission: str,
        granted_permission: str
    ) -> bool:
        """Check if granted permission matches required permission."""
        ...
    
    def expand_wildcard_permissions(
        self,
        permissions: List[str]
    ) -> Set[str]:
        """Expand wildcard permissions to include all variations."""
        ...
    
    def get_resource_from_permission(
        self,
        permission: str
    ) -> Optional[str]:
        """Extract resource name from permission string."""
        ...
    
    def get_action_from_permission(
        self,
        permission: str
    ) -> Optional[str]:
        """Extract action from permission string."""
        ...
    
    def check_permissions_list(
        self,
        required_permissions: List[str],
        granted_permissions: List[str],
        require_all: bool = True
    ) -> bool:
        """Check if granted permissions satisfy required permissions."""
        ...
    
    def group_permissions_by_resource(
        self,
        permissions: List[str]
    ) -> Dict[str, Set[str]]:
        """Group permissions by resource."""
        ...
    
    def has_wildcard_permission(
        self,
        permissions: List[str],
        resource: str,
        action: Optional[str] = None
    ) -> bool:
        """Check if permissions list contains a wildcard that would grant access."""
        ...
    
    def get_effective_permissions(
        self,
        granted_permissions: List[str],
        all_possible_permissions: List[str]
    ) -> Set[str]:
        """Get all effective permissions based on granted permissions with wildcards."""
        ...
    
    def normalize_permission(self, permission: str) -> Optional[str]:
        """Normalize permission string format."""
        ...
    
    def is_wildcard_permission(self, permission: str) -> bool:
        """Check if permission contains wildcards."""
        ...


__all__ = [
    "PermissionValidatorProtocol",
    "PermissionRegistryProtocol", 
    "PermissionDecoratorProtocol",
    "PermissionCheckerProtocol",
    "PermissionCacheProtocol",
    "PermissionDataSourceProtocol",
    "WildcardMatcherProtocol",
]