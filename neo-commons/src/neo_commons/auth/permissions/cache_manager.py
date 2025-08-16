"""
Permission Cache Manager for Neo-Commons

Provides intelligent permission caching with tenant isolation, wildcard matching,
cache warming strategies, and automatic invalidation.
"""
from typing import Optional, Dict, Any, List, Set
from loguru import logger

from ...cache.protocols import TenantAwareCacheProtocol
from .protocols import (
    PermissionCacheProtocol, 
    PermissionDataSourceProtocol,
    WildcardMatcherProtocol
)
from .matcher import DefaultWildcardMatcher


class PermissionCacheManager:
    """
    Abstract base class for permission cache managers.
    
    Provides the interface and common functionality for permission caching
    implementations. Subclasses should implement the data source integration.
    """
    
    def __init__(
        self,
        cache_service: TenantAwareCacheProtocol,
        wildcard_matcher: Optional[WildcardMatcherProtocol] = None
    ):
        """
        Initialize permission cache manager.
        
        Args:
            cache_service: Cache service for storing permission data
            wildcard_matcher: Optional wildcard permission matcher
        """
        self.cache = cache_service
        self.matcher = wildcard_matcher or DefaultWildcardMatcher()
        
        # Cache configuration
        self.PERMISSION_CACHE_TTL = 600  # 10 minutes
        self.ROLE_CACHE_TTL = 900        # 15 minutes
        self.SUMMARY_CACHE_TTL = 300     # 5 minutes
        
        # Cache key patterns
        self.USER_PERMS_KEY = "perms:user:{user_id}"
        self.USER_TENANT_PERMS_KEY = "perms:user:{user_id}:tenant:{tenant_id}"
        self.USER_ROLES_KEY = "roles:user:{user_id}"
        self.USER_TENANT_ROLES_KEY = "roles:user:{user_id}:tenant:{tenant_id}"
        self.PERM_SUMMARY_KEY = "perms:summary:{user_id}"
        self.TENANT_PERM_SUMMARY_KEY = "perms:summary:{user_id}:tenant:{tenant_id}"
        self.ROLE_USERS_KEY = "role:users:{role_id}"
        self.TENANT_ROLE_USERS_KEY = "role:users:{role_id}:tenant:{tenant_id}"
        
        logger.info("Initialized PermissionCacheManager")


class DefaultPermissionCacheManager(PermissionCacheManager):
    """
    Default implementation of permission cache manager.
    
    Provides comprehensive permission caching with tenant isolation,
    wildcard matching, and intelligent cache warming strategies.
    """
    
    def __init__(
        self,
        cache_service: TenantAwareCacheProtocol,
        data_source: PermissionDataSourceProtocol,
        wildcard_matcher: Optional[WildcardMatcherProtocol] = None
    ):
        """
        Initialize default permission cache manager.
        
        Args:
            cache_service: Cache service for storing permission data
            data_source: Data source for loading permission data
            wildcard_matcher: Optional wildcard permission matcher
        """
        super().__init__(cache_service, wildcard_matcher)
        self.data_source = data_source
        logger.info("Initialized DefaultPermissionCacheManager with data source")
    
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
        # Get cached permissions
        permissions = await self.get_user_permissions_cached(user_id, tenant_id)
        
        # Convert to permission strings and check with wildcard matching
        permission_strings = []
        for perm in permissions:
            if isinstance(perm, dict):
                # Handle structured permission data
                resource = perm.get('resource', '')
                action = perm.get('action', '')
                if resource and action:
                    permission_strings.append(f"{resource}:{action}")
            elif isinstance(perm, str):
                # Handle simple permission strings
                permission_strings.append(perm)
        
        # Check if any granted permission matches the required permission
        for granted in permission_strings:
            if self.matcher.matches_permission(permission, granted):
                logger.debug(f"Permission granted: {permission} via {granted}")
                return True
        
        logger.debug(f"Permission denied: {permission} for user {user_id}")
        return False
    
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
        # Build cache key
        if tenant_id:
            cache_key = self.USER_TENANT_PERMS_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.USER_PERMS_KEY.format(user_id=user_id)
        
        # Try cache first
        cached = await self.cache.get(
            cache_key,
            tenant_id=tenant_id
        )
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} permissions")
            return cached
        
        # Load from data source
        permissions = await self.data_source.get_user_permissions(user_id, tenant_id)
        
        # Cache the result
        if permissions:
            await self.cache.set(
                cache_key,
                permissions,
                ttl=self.PERMISSION_CACHE_TTL,
                tenant_id=tenant_id
            )
            logger.debug(f"Cached {len(permissions)} permissions for user {user_id}")
        
        return permissions
    
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
        # Build cache key
        if tenant_id:
            cache_key = self.USER_TENANT_ROLES_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.USER_ROLES_KEY.format(user_id=user_id)
        
        # Try cache first
        cached = await self.cache.get(
            cache_key,
            tenant_id=tenant_id
        )
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} roles")
            return cached
        
        # Load from data source
        roles = await self.data_source.get_user_roles(user_id, tenant_id)
        
        # Cache the result
        if roles:
            await self.cache.set(
                cache_key,
                roles,
                ttl=self.ROLE_CACHE_TTL,
                tenant_id=tenant_id
            )
            logger.debug(f"Cached {len(roles)} roles for user {user_id}")
        
        return roles
    
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
        # Build cache key
        if tenant_id:
            cache_key = self.TENANT_PERM_SUMMARY_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.PERM_SUMMARY_KEY.format(user_id=user_id)
        
        # Try cache first
        cached = await self.cache.get(
            cache_key,
            tenant_id=tenant_id
        )
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} permission summary")
            # Convert sets back from list format if needed
            if isinstance(cached, dict):
                for resource, actions in cached.items():
                    if isinstance(actions, list):
                        cached[resource] = set(actions)
            return cached
        
        # Load from data source
        summary = await self.data_source.get_user_permission_summary(user_id, tenant_id)
        
        # Cache the result (convert sets to lists for JSON serialization)
        if summary:
            cache_data = {}
            for resource, actions in summary.items():
                cache_data[resource] = list(actions) if isinstance(actions, set) else actions
            
            await self.cache.set(
                cache_key,
                cache_data,
                ttl=self.SUMMARY_CACHE_TTL,
                tenant_id=tenant_id
            )
            logger.debug(f"Cached permission summary for user {user_id}")
        
        return summary
    
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
        # Base cache keys
        keys_to_delete = [
            self.USER_PERMS_KEY.format(user_id=user_id),
            self.USER_ROLES_KEY.format(user_id=user_id),
            self.PERM_SUMMARY_KEY.format(user_id=user_id)
        ]
        
        # Add tenant-specific keys if tenant provided
        if tenant_id:
            keys_to_delete.extend([
                self.USER_TENANT_PERMS_KEY.format(user_id=user_id, tenant_id=tenant_id),
                self.USER_TENANT_ROLES_KEY.format(user_id=user_id, tenant_id=tenant_id),
                self.TENANT_PERM_SUMMARY_KEY.format(user_id=user_id, tenant_id=tenant_id)
            ])
        
        # Delete all keys
        for key in keys_to_delete:
            await self.cache.delete(key, tenant_id=tenant_id)
        
        logger.info(f"Invalidated permission cache for user {user_id}")
    
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
        # Load and cache permissions
        await self.get_user_permissions_cached(user_id, tenant_id)
        
        # Load and cache roles
        await self.get_user_roles_cached(user_id, tenant_id)
        
        # Load and cache permission summary
        await self.get_user_permission_summary_cached(user_id, tenant_id)
        
        logger.info(f"Warmed permission cache for user {user_id}")
    
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
        # Get list of users with this role
        user_ids = await self.data_source.get_users_with_role(role_id, tenant_id)
        
        # Invalidate cache for each user
        for user_id in user_ids:
            await self.invalidate_user_cache(user_id, tenant_id)
        
        # Clear role-specific cache keys
        role_cache_keys = [
            self.ROLE_USERS_KEY.format(role_id=role_id)
        ]
        
        if tenant_id:
            role_cache_keys.append(
                self.TENANT_ROLE_USERS_KEY.format(role_id=role_id, tenant_id=tenant_id)
            )
        
        for key in role_cache_keys:
            await self.cache.delete(key, tenant_id=tenant_id)
        
        logger.info(f"Invalidated role cache for role {role_id}")
    
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
        # Get list of users with this role
        user_ids = await self.data_source.get_users_with_role(role_id, tenant_id)
        
        # Warm cache for each user
        for user_id in user_ids:
            await self.warm_user_cache(user_id, tenant_id)
        
        logger.info(f"Warmed role cache for role {role_id} ({len(user_ids)} users)")
    
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
        # This would require cache service to provide stats
        # For now, return basic info
        return {
            "cache_service": type(self.cache).__name__,
            "tenant_id": tenant_id,
            "ttl_config": {
                "permissions": self.PERMISSION_CACHE_TTL,
                "roles": self.ROLE_CACHE_TTL,
                "summary": self.SUMMARY_CACHE_TTL
            }
        }
    
    async def clear_all_cache(
        self,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Clear all permission-related cache data.
        
        Args:
            tenant_id: Optional tenant context
        """
        # Use pattern-based clearing if cache supports it
        patterns = [
            "perms:*",
            "roles:*",
            "role:users:*"
        ]
        
        for pattern in patterns:
            await self.cache.clear_pattern(pattern, tenant_id=tenant_id)
        
        logger.info(f"Cleared all permission cache data for tenant {tenant_id}")
    
    async def batch_check_permissions(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        require_all: bool = True
    ) -> bool:
        """
        Check multiple permissions in a single operation.
        
        Args:
            user_id: User UUID
            permissions: List of permissions to check
            tenant_id: Optional tenant context
            require_all: If True, all permissions must be satisfied
            
        Returns:
            True if permissions are satisfied based on require_all flag
        """
        if not permissions:
            return True
        
        # Get user permissions once
        user_permissions = await self.get_user_permissions_cached(user_id, tenant_id)
        
        # Convert to permission strings
        permission_strings = []
        for perm in user_permissions:
            if isinstance(perm, dict):
                resource = perm.get('resource', '')
                action = perm.get('action', '')
                if resource and action:
                    permission_strings.append(f"{resource}:{action}")
            elif isinstance(perm, str):
                permission_strings.append(perm)
        
        # Use wildcard matcher for batch checking
        return self.matcher.check_permissions_list(
            required_permissions=permissions,
            granted_permissions=permission_strings,
            require_all=require_all
        )