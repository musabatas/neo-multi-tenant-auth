"""
Permission management protocols.

Protocol definitions for permission validation, registry management,
caching, and wildcard matching in multi-tenant environments.
"""

from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable
from .base import PermissionScope


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
    
    def get_platform_permissions(self) -> List[Dict[str, Any]]:
        """Get all platform-level permissions."""
        ...
    
    def get_tenant_permissions(self) -> List[Dict[str, Any]]:
        """Get all tenant-level permissions."""
        ...
    
    def find_permission(self, code: str) -> Optional[Dict[str, Any]]:
        """Find permission by code."""
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
        permissions: List[str],
        scope: str = "platform",
        tenant_id: Optional[str] = None,
        any_of: bool = False
    ) -> bool:
        """Check if user has required permissions."""
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
    
    async def invalidate_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """Invalidate cached permissions for user."""
        ...


@runtime_checkable
class PermissionDataSourceProtocol(Protocol):
    """Protocol for permission data source operations."""
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get user permissions from data source."""
        ...
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get user roles from data source."""
        ...


@runtime_checkable
class WildcardMatcherProtocol(Protocol):
    """Protocol for wildcard permission matching."""
    
    def matches(self, pattern: str, permission: str) -> bool:
        """Check if permission matches wildcard pattern."""
        ...
    
    def expand_wildcards(self, patterns: List[str], available: List[str]) -> List[str]:
        """Expand wildcard patterns against available permissions."""
        ...