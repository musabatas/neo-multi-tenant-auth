"""
Permission service with intelligent caching and validation.
Handles complex permission checks with team and tenant scoping.
"""
from typing import Optional, Dict, Any, List, Set
from enum import Enum
from loguru import logger

from src.common.cache.client import get_cache
from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError, ForbiddenError
# Use neo-commons for token management
from neo_commons.auth import create_auth_service
from ..repositories.permission_repository import PermissionRepository
from ..repositories.auth_repository import AuthRepository


class PermissionScope(Enum):
    """Permission scope levels."""
    PLATFORM = "platform"  # Platform-wide permissions
    TENANT = "tenant"      # Tenant-scoped permissions
    USER = "user"          # User-level permissions


class PermissionService:
    """
    High-performance permission service with caching.
    
    Features:
    - Multi-level permission checking (platform/tenant/user)
    - Intelligent caching with namespace separation
    - Wildcard permission support
    - Role hierarchy resolution
    - Time-based access validation
    """
    
    def __init__(self):
        """Initialize permission service."""
        self.permission_repo = PermissionRepository()
        self.auth_repo = AuthRepository()
        self.cache = get_cache()
        # Use neo-commons auth service for token operations
        self.auth_service = create_auth_service()
        
        # Cache configuration
        self.PERMISSION_CACHE_TTL = 600  # 10 minutes
        self.ROLE_CACHE_TTL = 900        # 15 minutes
        self.SUMMARY_CACHE_TTL = 300     # 5 minutes
        
        # Cache key patterns
        self.USER_PERMS_KEY = "platform:perms:user:{user_id}"
        self.USER_TENANT_PERMS_KEY = "platform:perms:user:{user_id}:tenant:{tenant_id}"
        self.USER_ROLES_KEY = "platform:roles:user:{user_id}"
        self.USER_TENANT_ROLES_KEY = "platform:roles:user:{user_id}:tenant:{tenant_id}"
        self.PERM_SUMMARY_KEY = "platform:perms:summary:{user_id}"
        self.TENANT_PERM_SUMMARY_KEY = "platform:perms:summary:{user_id}:tenant:{tenant_id}"
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None,
        use_cache: bool = True
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_id: User UUID
            permission: Permission name (e.g., "users:read")
            tenant_id: Optional tenant context
            use_cache: Whether to use cached permissions
            
        Returns:
            True if user has the permission
            
        Raises:
            ForbiddenError: User lacks the required permission
        """
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(user_id)
        if is_superadmin:
            logger.debug(f"Superadmin {user_id} bypasses permission check")
            return True
        
        # Check if user is active
        is_active = await self.auth_repo.is_user_active(user_id)
        if not is_active:
            raise ForbiddenError("User account is not active")
        
        # If tenant specified, verify user has access to tenant
        if tenant_id:
            tenant_access = await self.auth_repo.check_tenant_access(user_id, tenant_id)
            if not tenant_access:
                logger.warning(f"User {user_id} lacks access to tenant {tenant_id}")
                raise ForbiddenError("No access to specified tenant")
        
        # Check permission (with caching if enabled)
        if use_cache:
            has_perm = await self._check_permission_cached(user_id, permission, tenant_id)
        else:
            has_perm = await self.permission_repo.check_permission(user_id, permission, tenant_id)
        
        if not has_perm:
            logger.warning(
                f"Permission denied: user={user_id}, permission={permission}, tenant={tenant_id}"
            )
            raise ForbiddenError(f"Permission denied: {permission}")
        
        return True
    
    async def check_any_permission(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        use_cache: bool = True
    ) -> bool:
        """
        Check if user has any of the specified permissions.
        
        Args:
            user_id: User UUID
            permissions: List of permission names
            tenant_id: Optional tenant context
            use_cache: Whether to use cached permissions
            
        Returns:
            True if user has at least one permission
        """
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(user_id)
        if is_superadmin:
            return True
        
        # Check each permission
        for permission in permissions:
            try:
                if use_cache:
                    has_perm = await self._check_permission_cached(user_id, permission, tenant_id)
                else:
                    has_perm = await self.permission_repo.check_permission(user_id, permission, tenant_id)
                
                if has_perm:
                    return True
            except Exception:
                continue
        
        return False
    
    async def check_all_permissions(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None,
        use_cache: bool = True
    ) -> bool:
        """
        Check if user has all of the specified permissions.
        
        Args:
            user_id: User UUID
            permissions: List of permission names
            tenant_id: Optional tenant context
            use_cache: Whether to use cached permissions
            
        Returns:
            True if user has all permissions
        """
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(user_id)
        if is_superadmin:
            return True
        
        # Check all permissions
        for permission in permissions:
            if use_cache:
                has_perm = await self._check_permission_cached(user_id, permission, tenant_id)
            else:
                has_perm = await self.permission_repo.check_permission(user_id, permission, tenant_id)
            
            if not has_perm:
                return False
        
        return True
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            use_cache: Whether to use cached permissions
            
        Returns:
            List of permission details
        """
        if use_cache:
            # Try cache first
            if tenant_id:
                cache_key = self.USER_TENANT_PERMS_KEY.format(
                    user_id=user_id,
                    tenant_id=tenant_id
                )
            else:
                cache_key = self.USER_PERMS_KEY.format(user_id=user_id)
            
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for user {user_id} permissions")
                return cached
        
        # Load from database
        permissions = await self.permission_repo.get_user_permissions(user_id, tenant_id)
        
        # Cache the result
        if use_cache and permissions:
            await self.cache.set(cache_key, permissions, ttl=self.PERMISSION_CACHE_TTL)
        
        return permissions
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all roles for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            use_cache: Whether to use cached roles
            
        Returns:
            List of role assignments
        """
        if use_cache:
            # Try cache first
            if tenant_id:
                cache_key = self.USER_TENANT_ROLES_KEY.format(
                    user_id=user_id,
                    tenant_id=tenant_id
                )
            else:
                cache_key = self.USER_ROLES_KEY.format(user_id=user_id)
            
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for user {user_id} roles")
                return cached
        
        # Load from database
        roles = await self.permission_repo.get_user_roles(user_id, tenant_id)
        
        # Cache the result
        if use_cache and roles:
            await self.cache.set(cache_key, roles, ttl=self.ROLE_CACHE_TTL)
        
        return roles
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Set[str]]:
        """
        Get a summary of user permissions grouped by resource.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
            use_cache: Whether to use cached summary
            
        Returns:
            Dict mapping resource to set of actions
        """
        if use_cache:
            # Try cache first
            if tenant_id:
                cache_key = self.TENANT_PERM_SUMMARY_KEY.format(
                    user_id=user_id,
                    tenant_id=tenant_id
                )
            else:
                cache_key = self.PERM_SUMMARY_KEY.format(user_id=user_id)
            
            cached = await self.cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for user {user_id} permission summary")
                return cached
        
        # Get summary from repository
        summary = await self.permission_repo.get_user_permission_summary(user_id, tenant_id)
        
        # Cache the result
        if use_cache and summary:
            await self.cache.set(cache_key, summary, ttl=self.SUMMARY_CACHE_TTL)
        
        return summary
    
    async def validate_token_permissions(
        self,
        access_token: str,
        required_permission: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate token and check permission in one operation.
        
        Args:
            access_token: JWT access token
            required_permission: Permission to check
            tenant_id: Optional tenant context
            
        Returns:
            User info if permission granted
            
        Raises:
            UnauthorizedError: Invalid token
            ForbiddenError: Lacks permission
        """
        # Validate token using neo-commons auth service
        token_claims = await self.auth_service.validate_token(
            access_token,
            realm=settings.keycloak_admin_realm
        )
        
        # Get Keycloak user ID from token
        keycloak_user_id = token_claims.get('sub')
        if not keycloak_user_id:
            raise UnauthorizedError("Invalid token claims")
        
        logger.debug(f"Token validation: Keycloak user ID = {keycloak_user_id}")
        
        # Map Keycloak user ID to platform user ID
        user = await self.auth_repo.get_user_by_external_id(
            provider="keycloak",
            external_id=keycloak_user_id
        )
        
        if not user:
            logger.error(f"Platform user not found for Keycloak ID: {keycloak_user_id}")
            raise UnauthorizedError("User not found in platform database")
        
        platform_user_id = user['id']
        logger.debug(f"Mapped to platform user ID: {platform_user_id}")
        
        # Check permission using platform user ID
        await self.check_permission(
            platform_user_id,
            required_permission,
            tenant_id,
            use_cache=True
        )
        
        return user
    
    async def invalidate_user_permissions_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ):
        """
        Invalidate cached permissions for a user.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant to clear specific cache
        """
        # Clear permission caches
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
        else:
            # Clear all tenant-specific caches for this user
            # This would require pattern matching in Redis
            pass
        
        # Delete all keys
        for key in keys_to_delete:
            await self.cache.delete(key)
        
        logger.info(f"Invalidated permission cache for user {user_id}")
    
    async def warm_permission_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ):
        """
        Warm the permission cache for a user (useful after login).
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant context
        """
        # Load and cache permissions
        await self.get_user_permissions(user_id, tenant_id, use_cache=True)
        
        # Load and cache roles
        await self.get_user_roles(user_id, tenant_id, use_cache=True)
        
        # Load and cache permission summary
        await self.get_user_permission_summary(user_id, tenant_id, use_cache=True)
        
        logger.info(f"Warmed permission cache for user {user_id}")
    
    async def _check_permission_cached(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check permission with caching.
        
        Args:
            user_id: User UUID
            permission: Permission name
            tenant_id: Optional tenant context
            
        Returns:
            True if user has permission
        """
        # Get cached permissions
        permissions = await self.get_user_permissions(user_id, tenant_id, use_cache=True)
        
        # Extract permission names
        permission_names = set()
        for perm in permissions:
            perm_name = f"{perm['resource']}:{perm['action']}"
            permission_names.add(perm_name)
            
            # Add wildcard permissions
            if perm['action'] == '*':
                permission_names.add(f"{perm['resource']}:*")
        
        # Check exact match
        if permission in permission_names:
            return True
        
        # Check wildcard match (e.g., "users:*" matches "users:read")
        if ':' in permission:
            resource = permission.split(':')[0]
            wildcard = f"{resource}:*"
            if wildcard in permission_names:
                return True
        
        return False
    
    async def get_role_permissions(
        self,
        role_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a specific role.
        
        Args:
            role_id: Role UUID
            
        Returns:
            List of permissions assigned to the role
        """
        return await self.permission_repo.get_role_permissions(role_id)
    
    async def get_all_permissions(
        self,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all available permissions in the system.
        
        Args:
            active_only: Only return active permissions
            
        Returns:
            List of all permissions
        """
        return await self.permission_repo.get_all_permissions(active_only)
    
    async def get_permission_resources(self) -> List[str]:
        """
        Get all unique permission resources.
        
        Returns:
            List of resource names
        """
        return await self.permission_repo.get_permission_resources()