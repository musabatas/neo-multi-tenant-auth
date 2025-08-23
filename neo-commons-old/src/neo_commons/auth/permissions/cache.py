"""
Permission Cache for Neo-Commons

Provides intelligent permission caching with tenant isolation, cache warming 
strategies, and automatic invalidation.
"""
from typing import Optional, Dict, Any, List, Set
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    CacheKeyProviderProtocol,
)
from .protocols import PermissionCacheProtocol


class DefaultPermissionCache:
    """
    Default implementation of permission cache.
    
    Provides comprehensive permission caching with tenant isolation,
    intelligent cache key management, and performance optimization.
    """
    
    def __init__(
        self,
        cache_service,  # TenantAwareCacheProtocol - avoiding import for now
        cache_key_provider: Optional[CacheKeyProviderProtocol] = None,
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize permission cache.
        
        Args:
            cache_service: Cache service for storing permission data
            cache_key_provider: Optional cache key provider
            config: Optional configuration
        """
        self.cache = cache_service
        self.key_provider = cache_key_provider
        self.config = config
        
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
        
        logger.info("Initialized DefaultPermissionCache")
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached permissions for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details or None if not cached
        """
        # Build cache key
        if tenant_id:
            cache_key = self.USER_TENANT_PERMS_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.USER_PERMS_KEY.format(user_id=user_id)
        
        # Try cache
        cached = await self.cache.get(
            cache_key,
            tenant_id=tenant_id
        )
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} permissions")
        
        return cached
    
    async def set_user_permissions(
        self,
        user_id: str,
        permissions: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache permissions for a user.
        
        Args:
            user_id: User UUID
            permissions: List of permission details
            tenant_id: Optional tenant context
            ttl: Optional time-to-live override
        """
        # Build cache key
        if tenant_id:
            cache_key = self.USER_TENANT_PERMS_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.USER_PERMS_KEY.format(user_id=user_id)
        
        # Cache the result
        await self.cache.set(
            cache_key,
            permissions,
            ttl=ttl or self.PERMISSION_CACHE_TTL,
            tenant_id=tenant_id
        )
        logger.debug(f"Cached {len(permissions)} permissions for user {user_id}")
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached roles for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of role assignments or None if not cached
        """
        # Build cache key
        if tenant_id:
            cache_key = self.USER_TENANT_ROLES_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.USER_ROLES_KEY.format(user_id=user_id)
        
        # Try cache
        cached = await self.cache.get(
            cache_key,
            tenant_id=tenant_id
        )
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} roles")
        
        return cached
    
    async def set_user_roles(
        self,
        user_id: str,
        roles: List[Dict[str, Any]],
        tenant_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache roles for a user.
        
        Args:
            user_id: User UUID
            roles: List of role assignments
            tenant_id: Optional tenant context
            ttl: Optional time-to-live override
        """
        # Build cache key
        if tenant_id:
            cache_key = self.USER_TENANT_ROLES_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.USER_ROLES_KEY.format(user_id=user_id)
        
        # Cache the result
        await self.cache.set(
            cache_key,
            roles,
            ttl=ttl or self.ROLE_CACHE_TTL,
            tenant_id=tenant_id
        )
        logger.debug(f"Cached {len(roles)} roles for user {user_id}")
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Set[str]]]:
        """
        Get cached permission summary for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            Dict mapping resource to set of actions or None if not cached
        """
        # Build cache key
        if tenant_id:
            cache_key = self.TENANT_PERM_SUMMARY_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.PERM_SUMMARY_KEY.format(user_id=user_id)
        
        # Try cache
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
    
    async def set_user_permission_summary(
        self,
        user_id: str,
        summary: Dict[str, Set[str]],
        tenant_id: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Cache permission summary for a user.
        
        Args:
            user_id: User UUID
            summary: Dict mapping resource to set of actions
            tenant_id: Optional tenant context
            ttl: Optional time-to-live override
        """
        # Build cache key
        if tenant_id:
            cache_key = self.TENANT_PERM_SUMMARY_KEY.format(
                user_id=user_id,
                tenant_id=tenant_id
            )
        else:
            cache_key = self.PERM_SUMMARY_KEY.format(user_id=user_id)
        
        # Cache the result (convert sets to lists for JSON serialization)
        cache_data = {}
        for resource, actions in summary.items():
            cache_data[resource] = list(actions) if isinstance(actions, set) else actions
        
        await self.cache.set(
            cache_key,
            cache_data,
            ttl=ttl or self.SUMMARY_CACHE_TTL,
            tenant_id=tenant_id
        )
        logger.debug(f"Cached permission summary for user {user_id}")
    
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
            if hasattr(self.cache, 'clear_pattern'):
                await self.cache.clear_pattern(pattern, tenant_id=tenant_id)
            else:
                logger.warning(f"Cache service doesn't support pattern clearing for {pattern}")
        
        logger.info(f"Cleared all permission cache data for tenant {tenant_id}")
    
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
        stats = {
            "cache_service": type(self.cache).__name__,
            "tenant_id": tenant_id,
            "ttl_config": {
                "permissions": self.PERMISSION_CACHE_TTL,
                "roles": self.ROLE_CACHE_TTL,
                "summary": self.SUMMARY_CACHE_TTL
            }
        }
        
        # Add cache-specific stats if available
        if hasattr(self.cache, 'get_stats'):
            try:
                cache_stats = await self.cache.get_stats(tenant_id=tenant_id)
                stats["cache_stats"] = cache_stats
            except Exception as e:
                logger.debug(f"Could not get cache stats: {e}")
        
        return stats
    
    async def warm_cache_for_user(
        self,
        user_id: str,
        permissions: Optional[List[Dict[str, Any]]] = None,
        roles: Optional[List[Dict[str, Any]]] = None,
        summary: Optional[Dict[str, Set[str]]] = None,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Warm cache for a user with provided data.
        
        Args:
            user_id: User UUID
            permissions: Optional permissions to cache
            roles: Optional roles to cache
            summary: Optional permission summary to cache
            tenant_id: Optional tenant context
        """
        if permissions:
            await self.set_user_permissions(user_id, permissions, tenant_id)
        
        if roles:
            await self.set_user_roles(user_id, roles, tenant_id)
        
        if summary:
            await self.set_user_permission_summary(user_id, summary, tenant_id)
        
        logger.info(f"Warmed cache for user {user_id}")
    
    def _build_cache_key(
        self,
        template: str,
        **kwargs
    ) -> str:
        """
        Build cache key from template and parameters.
        
        Args:
            template: Cache key template
            **kwargs: Template parameters
            
        Returns:
            Formatted cache key
        """
        if self.key_provider:
            return self.key_provider.build_key(template, **kwargs)
        return template.format(**kwargs)


# Legacy compatibility class
class PermissionCacheManager(DefaultPermissionCache):
    """
    Legacy compatibility class for permission cache manager.
    
    This class maintains backward compatibility with the old cache manager
    interface while using the new implementation.
    """
    
    def __init__(
        self,
        cache_service,
        wildcard_matcher=None
    ):
        """
        Initialize with legacy interface.
        
        Args:
            cache_service: Cache service
            wildcard_matcher: Wildcard matcher (ignored for now)
        """
        super().__init__(cache_service)
        self.matcher = wildcard_matcher
        logger.info("Initialized PermissionCacheManager (legacy compatibility)")


__all__ = [
    "DefaultPermissionCache",
    "PermissionCacheManager",  # Legacy compatibility
]