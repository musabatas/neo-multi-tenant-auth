"""
Permission Checker for Neo-Commons

Provides intelligent permission checking with tenant isolation, wildcard matching,
cache integration, and performance optimization.
"""
from typing import Optional, Dict, Any, List, Set
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    CacheKeyProviderProtocol,
    AuthenticationError,
    AuthorizationError,
    UserNotFoundError,
)
from .protocols import (
    PermissionCheckerProtocol,
    PermissionDataSourceProtocol,
    WildcardMatcherProtocol,
    PermissionCacheProtocol
)


class DefaultPermissionChecker:
    """
    Default implementation of permission checker.
    
    Provides comprehensive permission checking with tenant isolation,
    wildcard matching, intelligent caching, and performance optimization.
    """
    
    def __init__(
        self,
        cache_service: PermissionCacheProtocol,
        data_source: PermissionDataSourceProtocol,
        wildcard_matcher: WildcardMatcherProtocol,
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize permission checker.
        
        Args:
            cache_service: Cache service for storing permission data
            data_source: Data source for loading permission data
            wildcard_matcher: Wildcard permission matcher
            config: Optional configuration
        """
        self.cache = cache_service
        self.data_source = data_source
        self.matcher = wildcard_matcher
        self.config = config
        
        # Cache configuration
        self.PERMISSION_CACHE_TTL = 600  # 10 minutes
        self.ROLE_CACHE_TTL = 900        # 15 minutes
        self.SUMMARY_CACHE_TTL = 300     # 5 minutes
        
        logger.info("Initialized DefaultPermissionChecker")
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_id: User UUID
            permission: Permission name (e.g., "users:read")
            tenant_id: Optional tenant context
            
        Returns:
            True if user has the permission
            
        Raises:
            UserNotFoundError: If user doesn't exist
            AuthenticationError: If user authentication fails
        """
        try:
            # Get cached permissions
            permissions = await self.get_user_permissions(user_id, tenant_id)
            
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
            
        except Exception as e:
            logger.error(f"Permission check failed for user {user_id}: {e}")
            if "not found" in str(e).lower():
                raise UserNotFoundError(f"User {user_id} not found")
            raise AuthenticationError(f"Permission check failed: {str(e)}")
    
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
        
        try:
            # Get user permissions once
            user_permissions = await self.get_user_permissions(user_id, tenant_id)
            
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
            
        except Exception as e:
            logger.error(f"Batch permission check failed for user {user_id}: {e}")
            if "not found" in str(e).lower():
                raise UserNotFoundError(f"User {user_id} not found")
            raise AuthenticationError(f"Batch permission check failed: {str(e)}")
    
    async def get_user_permissions(
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
        # Try cache first
        cached = await self.cache.get_user_permissions(user_id, tenant_id)
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} permissions")
            return cached
        
        # Load from data source
        permissions = await self.data_source.get_user_permissions(user_id, tenant_id)
        
        # Cache the result
        if permissions:
            await self.cache.set_user_permissions(
                user_id,
                permissions,
                tenant_id=tenant_id,
                ttl=self.PERMISSION_CACHE_TTL
            )
            logger.debug(f"Cached {len(permissions)} permissions for user {user_id}")
        
        return permissions
    
    async def get_user_roles(
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
        # Try cache first
        cached = await self.cache.get_user_roles(user_id, tenant_id)
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} roles")
            return cached
        
        # Load from data source
        roles = await self.data_source.get_user_roles(user_id, tenant_id)
        
        # Cache the result
        if roles:
            await self.cache.set_user_roles(
                user_id,
                roles,
                tenant_id=tenant_id,
                ttl=self.ROLE_CACHE_TTL
            )
            logger.debug(f"Cached {len(roles)} roles for user {user_id}")
        
        return roles
    
    async def get_user_permission_summary(
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
        # Try cache first
        cached = await self.cache.get_user_permission_summary(user_id, tenant_id)
        
        if cached:
            logger.debug(f"Cache hit for user {user_id} permission summary")
            return cached
        
        # Load from data source
        summary = await self.data_source.get_user_permission_summary(user_id, tenant_id)
        
        # Cache the result
        if summary:
            await self.cache.set_user_permission_summary(
                user_id,
                summary,
                tenant_id=tenant_id,
                ttl=self.SUMMARY_CACHE_TTL
            )
            logger.debug(f"Cached permission summary for user {user_id}")
        
        return summary
    
    async def has_any_permission(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has any of the specified permissions.
        
        Args:
            user_id: User UUID
            permissions: List of permissions to check
            tenant_id: Optional tenant context
            
        Returns:
            True if user has at least one permission
        """
        return await self.batch_check_permissions(
            user_id=user_id,
            permissions=permissions,
            tenant_id=tenant_id,
            require_all=False
        )
    
    async def has_all_permissions(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has all of the specified permissions.
        
        Args:
            user_id: User UUID
            permissions: List of permissions to check
            tenant_id: Optional tenant context
            
        Returns:
            True if user has all permissions
        """
        return await self.batch_check_permissions(
            user_id=user_id,
            permissions=permissions,
            tenant_id=tenant_id,
            require_all=True
        )
    
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
        await self.cache.invalidate_user_cache(user_id, tenant_id)
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
        await self.get_user_permissions(user_id, tenant_id)
        
        # Load and cache roles
        await self.get_user_roles(user_id, tenant_id)
        
        # Load and cache permission summary
        await self.get_user_permission_summary(user_id, tenant_id)
        
        logger.info(f"Warmed permission cache for user {user_id}")
    
    async def check_resource_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission for specific resource and action.
        
        Args:
            user_id: User UUID
            resource: Resource name (e.g., "users", "organizations")
            action: Action name (e.g., "read", "write", "delete")
            tenant_id: Optional tenant context
            
        Returns:
            True if user has the permission
        """
        permission = f"{resource}:{action}"
        return await self.check_permission(user_id, permission, tenant_id)


__all__ = [
    "DefaultPermissionChecker",
]