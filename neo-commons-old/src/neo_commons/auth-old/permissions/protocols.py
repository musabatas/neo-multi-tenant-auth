"""
Permission Cache Protocol for Neo-Commons

Defines the interface for permission caching implementations that provide
intelligent caching, invalidation, and warming strategies for permission data.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List, Set
from enum import Enum


class PermissionScope(Enum):
    """Permission scope levels for multi-tenant systems."""
    PLATFORM = "platform"  # Platform-wide permissions
    TENANT = "tenant"      # Tenant-scoped permissions
    USER = "user"          # User-level permissions


@runtime_checkable
class PermissionCacheProtocol(Protocol):
    """
    Protocol for permission caching implementations.
    
    Provides intelligent caching strategies for permission data including
    user permissions, roles, and permission summaries with tenant isolation.
    """
    
    async def check_permission_cached(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission using cached data.
        
        Args:
            user_id: User UUID
            permission: Permission name (e.g., "users:read")
            tenant_id: Optional tenant context
            
        Returns:
            True if user has the permission
        """
        ...
    
    async def get_user_permissions_cached(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user with caching.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details
        """
        ...
    
    async def get_user_roles_cached(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all roles for a user with caching.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of role assignments
        """
        ...
    
    async def get_user_permission_summary_cached(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """
        Get a summary of user permissions grouped by resource with caching.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            Dict mapping resource to set of actions
        """
        ...
    
    async def invalidate_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Invalidate all cached data for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant to clear specific cache
        """
        ...
    
    async def warm_user_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Warm the cache for a user by pre-loading permission data.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
        """
        ...
    
    async def invalidate_role_cache(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Invalidate cache for all users with a specific role.
        
        Args:
            role_id: Role UUID
            tenant_id: Optional tenant context
        """
        ...
    
    async def warm_role_cache(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Warm cache for all users with a specific role.
        
        Args:
            role_id: Role UUID
            tenant_id: Optional tenant context
        """
        ...
    
    async def get_cache_stats(
        self,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get cache statistics and metrics.
        
        Args:
            tenant_id: Optional tenant context
            
        Returns:
            Dict with cache statistics
        """
        ...
    
    async def clear_all_cache(
        self,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Clear all permission-related cache data.
        
        Args:
            tenant_id: Optional tenant context
        """
        ...


@runtime_checkable  
class PermissionDataSourceProtocol(Protocol):
    """
    Protocol for permission data sources.
    
    Defines the interface for loading permission data from databases
    or other storage systems.
    """
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission in data source."""
        ...
    
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
        """Get user permission summary from data source."""
        ...
    
    async def get_users_with_role(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get list of user IDs with specific role."""
        ...


@runtime_checkable
class WildcardMatcherProtocol(Protocol):
    """
    Protocol for wildcard permission matching.
    
    Provides pattern matching for permission strings including
    wildcard support (e.g., "users:*" matches "users:read").
    """
    
    def matches_permission(
        self,
        required_permission: str,
        granted_permission: str
    ) -> bool:
        """
        Check if granted permission matches required permission.
        
        Args:
            required_permission: Permission being checked
            granted_permission: Permission that was granted
            
        Returns:
            True if granted permission satisfies required permission
        """
        ...
    
    def expand_wildcard_permissions(
        self,
        permissions: List[str]
    ) -> Set[str]:
        """
        Expand wildcard permissions to include all possible matches.
        
        Args:
            permissions: List of permission strings (may include wildcards)
            
        Returns:
            Set of expanded permission strings
        """
        ...
    
    def get_resource_from_permission(
        self,
        permission: str
    ) -> Optional[str]:
        """
        Extract resource name from permission string.
        
        Args:
            permission: Permission string (e.g., "users:read")
            
        Returns:
            Resource name (e.g., "users") or None if invalid format
        """
        ...
    
    def get_action_from_permission(
        self,
        permission: str
    ) -> Optional[str]:
        """
        Extract action from permission string.
        
        Args:
            permission: Permission string (e.g., "users:read")
            
        Returns:
            Action name (e.g., "read") or None if invalid format
        """
        ...