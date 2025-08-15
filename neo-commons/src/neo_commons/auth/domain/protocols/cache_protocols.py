"""
Cache protocol interfaces for authorization domain.

Defines contracts for caching layer implementations.
"""
from typing import Protocol, runtime_checkable, List, Optional, Dict, Any, Set
from datetime import datetime
from ..entities.permission import Permission
from ..entities.role import Role
from ..entities.access_control import AccessControlEntry
from ..entities.session import Session
from ..value_objects.permission_check import PermissionResult


@runtime_checkable
class AuthCacheProtocol(Protocol):
    """Protocol for general authorization caching operations."""
    
    async def get(self, key: str, namespace: Optional[str] = None) -> Any:
        """Get cached value by key."""
        ...
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        namespace: Optional[str] = None
    ) -> None:
        """Set cached value with TTL."""
        ...
    
    async def delete(self, key: str, namespace: Optional[str] = None) -> bool:
        """Delete cached value."""
        ...
    
    async def exists(self, key: str, namespace: Optional[str] = None) -> bool:
        """Check if key exists in cache."""
        ...
    
    async def get_ttl(self, key: str, namespace: Optional[str] = None) -> Optional[int]:
        """Get remaining TTL for key."""
        ...
    
    async def set_add(
        self,
        key: str,
        value: str,
        ttl: int = 300,
        namespace: Optional[str] = None
    ) -> None:
        """Add value to a set."""
        ...
    
    async def set_members(
        self,
        key: str,
        namespace: Optional[str] = None
    ) -> Set[str]:
        """Get all members of a set."""
        ...
    
    async def set_remove(
        self,
        key: str,
        value: str,
        namespace: Optional[str] = None
    ) -> bool:
        """Remove value from set."""
        ...
    
    async def clear_namespace(self, namespace: str) -> int:
        """Clear all keys in namespace. Returns count of cleared keys."""
        ...
    
    async def get_namespace_keys(self, namespace: str) -> List[str]:
        """Get all keys in namespace."""
        ...


@runtime_checkable
class PermissionCacheProtocol(Protocol):
    """Protocol for permission-specific caching operations."""
    
    async def cache_user_permissions(
        self,
        user_id: str,
        permissions: List[Permission],
        tenant_id: Optional[str] = None,
        ttl: int = 300
    ) -> None:
        """Cache user permissions."""
        ...
    
    async def get_cached_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[List[Permission]]:
        """Get cached user permissions."""
        ...
    
    async def cache_user_roles(
        self,
        user_id: str,
        roles: List[Role],
        tenant_id: Optional[str] = None,
        ttl: int = 300
    ) -> None:
        """Cache user roles."""
        ...
    
    async def get_cached_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[List[Role]]:
        """Get cached user roles."""
        ...
    
    async def cache_permission_check_result(
        self,
        user_id: str,
        permission: str,
        result: bool,
        tenant_id: Optional[str] = None,
        ttl: int = 300
    ) -> None:
        """Cache permission check result."""
        ...
    
    async def get_cached_permission_check(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> Optional[bool]:
        """Get cached permission check result."""
        ...
    
    async def cache_permission_result(
        self,
        result: PermissionResult,
        ttl: int = 300
    ) -> None:
        """Cache complete permission result."""
        ...
    
    async def get_cached_permission_result(
        self,
        user_id: str,
        permissions: List[str],
        check_type: str,
        tenant_id: Optional[str] = None
    ) -> Optional[PermissionResult]:
        """Get cached permission result."""
        ...
    
    async def cache_access_control_entry(
        self,
        entry: AccessControlEntry,
        ttl: Optional[int] = None
    ) -> None:
        """Cache access control entry."""
        ...
    
    async def get_cached_access_control_entry(
        self,
        user_id: str,
        resource: str,
        tenant_id: Optional[str] = None
    ) -> Optional[AccessControlEntry]:
        """Get cached access control entry."""
        ...
    
    async def cache_session(
        self,
        session: Session,
        ttl: int = 3600
    ) -> None:
        """Cache session data."""
        ...
    
    async def get_cached_session(
        self,
        session_id: str
    ) -> Optional[Session]:
        """Get cached session."""
        ...
    
    async def invalidate_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """Invalidate all cached data for a user."""
        ...
    
    async def invalidate_tenant_cache(self, tenant_id: str) -> None:
        """Invalidate all cached data for a tenant."""
        ...
    
    async def invalidate_permission_cache(self, permission_code: str) -> None:
        """Invalidate caches related to a specific permission."""
        ...
    
    async def invalidate_role_cache(self, role_id: str) -> None:
        """Invalidate caches related to a specific role."""
        ...
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics (hit rate, size, etc.)."""
        ...
    
    async def warm_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """Pre-warm cache with user's permissions and roles."""
        ...