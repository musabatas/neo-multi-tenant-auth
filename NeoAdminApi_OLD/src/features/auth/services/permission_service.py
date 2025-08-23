"""
Permission service with intelligent caching and validation.
Now fully integrated with neo-commons for enhanced caching and wildcard matching.
"""
from typing import Optional, Dict, Any, List, Set, Union
from enum import Enum
from loguru import logger

from src.common.config.settings import settings
from src.common.exceptions.base import UnauthorizedError
# Use neo-commons for everything
from neo_commons.auth import create_auth_service, create_permission_cache_manager
from neo_commons.cache import CacheManager, TenantAwareCacheService
from ..repositories.auth_repository import AuthRepository
from ..implementations.permission_data_source import NeoAdminPermissionDataSource


class PermissionScope(Enum):
    """Permission scope levels."""
    PLATFORM = "platform"  # Platform-wide permissions
    TENANT = "tenant"      # Tenant-scoped permissions
    USER = "user"          # User-level permissions


class PermissionService:
    """
    High-performance permission service with intelligent caching.
    
    Features:
    - Multi-level permission checking (platform/tenant/user)
    - Intelligent caching with namespace separation via neo-commons
    - Advanced wildcard permission support (users:* matches users:read)
    - Role hierarchy resolution
    - Sub-millisecond permission checks
    - Automatic cache warming and invalidation
    """
    
    def __init__(self):
        """Initialize permission service with neo-commons integration."""
        # Import auth config locally to avoid circular imports
        from ..implementations import NeoAdminAuthConfig
        
        # Use neo-commons auth service for token operations
        auth_config = NeoAdminAuthConfig()
        self.auth_service = create_auth_service(auth_config=auth_config)
        
        # Create neo-commons permission cache manager with proper config
        from ..repositories.permission_repository import PermissionRepository
        from src.common.cache.client import get_cache
        
        # Use NeoAdminApi's configured cache manager
        cache_manager = get_cache()
        cache_service = TenantAwareCacheService(cache_manager)
        data_source = NeoAdminPermissionDataSource(PermissionRepository())
        
        self.cache_manager = create_permission_cache_manager(
            cache_service=cache_service,
            data_source=data_source
        )
        
        # Keep auth repo for user validation
        self.auth_repo = AuthRepository()
        
        logger.info("Initialized PermissionService with neo-commons integration")
    
    async def check_permission(
        self,
        user_id: str,
        permissions: Any,  # Can be a single permission string or a list
        scope: str = "platform",
        tenant_id: Optional[str] = None,
        any_of: bool = False
    ) -> bool:
        """
        Check if user has specific permission(s).
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            permissions: Permission name(s) - can be string or list
            scope: Permission scope (platform/tenant/user)
            tenant_id: Optional tenant context
            any_of: If True and permissions is a list, check ANY; if False, check ALL
            
        Returns:
            True if user has the permission(s)
            
        Raises:
            ForbiddenError: User lacks the required permission
        """
        # Handle both single permission string and list of permissions
        if isinstance(permissions, str):
            permission_list = [permissions]
        elif isinstance(permissions, list):
            permission_list = permissions
        else:
            permission_list = [str(permissions)]
        
        # Resolve user ID (handle both Keycloak ID and platform ID)
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            from src.common.exceptions.base import ForbiddenError
            raise ForbiddenError("User not found")
        
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(platform_user_id)
        if is_superadmin:
            logger.debug(f"Superadmin {platform_user_id} bypasses permission check")
            return True
        
        # Check if user is active
        is_active = await self.auth_repo.is_user_active(platform_user_id)
        if not is_active:
            from src.common.exceptions.base import ForbiddenError
            raise ForbiddenError("User account is not active")
        
        # If tenant specified, verify user has access to tenant
        if tenant_id:
            tenant_access = await self.auth_repo.check_tenant_access(platform_user_id, tenant_id)
            if not tenant_access:
                logger.warning(f"User {platform_user_id} lacks access to tenant {tenant_id}")
                from src.common.exceptions.base import ForbiddenError
                raise ForbiddenError("No access to specified tenant")
        
        # Check permissions based on any_of flag
        if any_of:
            # Check if user has ANY of the permissions
            for permission in permission_list:
                has_perm = await self.cache_manager.check_permission_cached(
                    user_id=platform_user_id,
                    permission=permission,
                    tenant_id=tenant_id
                )
                if has_perm:
                    return True
            
            # None of the permissions matched
            logger.warning(
                f"Permission denied: user={platform_user_id}, permissions={permission_list}, tenant={tenant_id}"
            )
            from src.common.exceptions.base import ForbiddenError
            raise ForbiddenError(f"Permission denied: requires any of {permission_list}")
        else:
            # Check if user has ALL of the permissions
            for permission in permission_list:
                has_perm = await self.cache_manager.check_permission_cached(
                    user_id=platform_user_id,
                    permission=permission,
                    tenant_id=tenant_id
                )
                if not has_perm:
                    logger.warning(
                        f"Permission denied: user={platform_user_id}, missing permission={permission}, tenant={tenant_id}"
                    )
                    from src.common.exceptions.base import ForbiddenError
                    raise ForbiddenError(f"Permission denied: {permission}")
            
            return True
    
    async def check_any_permission(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has any of the specified permissions.
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            permissions: List of permission names
            tenant_id: Optional tenant context
            
        Returns:
            True if user has at least one permission
        """
        # Resolve user ID
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            return False
        
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(platform_user_id)
        if is_superadmin:
            return True
        
        # Use neo-commons batch permission checking with any_of=True
        return await self.cache_manager.batch_check_permissions(
            user_id=platform_user_id,
            permissions=permissions,
            tenant_id=tenant_id,
            require_all=False  # any_of behavior
        )
    
    async def check_all_permissions(
        self,
        user_id: str,
        permissions: List[str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has all of the specified permissions.
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            permissions: List of permission names
            tenant_id: Optional tenant context
            
        Returns:
            True if user has all permissions
        """
        # Resolve user ID
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            return False
        
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(platform_user_id)
        if is_superadmin:
            return True
        
        # Use neo-commons batch permission checking with require_all=True
        return await self.cache_manager.batch_check_permissions(
            user_id=platform_user_id,
            permissions=permissions,
            tenant_id=tenant_id,
            require_all=True
        )
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details
        """
        # Resolve user ID
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            return []
        
        return await self.cache_manager.get_user_permissions_cached(
            user_id=platform_user_id,
            tenant_id=tenant_id
        )
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all roles for a user.
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            tenant_id: Optional tenant context
            
        Returns:
            List of role assignments
        """
        # Resolve user ID
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            return []
        
        return await self.cache_manager.get_user_roles_cached(
            user_id=platform_user_id,
            tenant_id=tenant_id
        )
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """
        Get a summary of user permissions grouped by resource.
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            tenant_id: Optional tenant context
            
        Returns:
            Dict mapping resource to set of actions
        """
        # Resolve user ID
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            return {}
        
        return await self.cache_manager.get_user_permission_summary_cached(
            user_id=platform_user_id,
            tenant_id=tenant_id
        )
    
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
        token_claims = await self.auth_service.token_validator.validate_token(
            token=access_token,
            realm=settings.keycloak_admin_realm
        )
        
        # Get Keycloak user ID from token
        keycloak_user_id = token_claims.get('sub')
        if not keycloak_user_id:
            raise UnauthorizedError("Invalid token claims")
        
        logger.debug(f"Token validation: Keycloak user ID = {keycloak_user_id}")
        
        # Get auth repository to resolve user ID
        auth_repo = AuthRepository()
        
        # Map Keycloak user ID to platform user ID
        user = await auth_repo.get_user_by_external_id(
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
            user_id=platform_user_id,
            permissions=required_permission,
            scope="platform",
            tenant_id=tenant_id,
            any_of=False
        )
        
        return user
    
    async def invalidate_user_permissions_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Invalidate cached permissions for a user.
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            tenant_id: Optional tenant to clear specific cache
        """
        # Resolve user ID
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            return
        
        await self.cache_manager.invalidate_user_cache(
            user_id=platform_user_id,
            tenant_id=tenant_id
        )
    
    async def warm_permission_cache(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Warm the permission cache for a user (useful after login).
        
        Args:
            user_id: User UUID (can be Keycloak ID or platform ID)
            tenant_id: Optional tenant context
        """
        # Resolve user ID
        platform_user_id = await self._resolve_user_id(user_id)
        if not platform_user_id:
            return
        
        await self.cache_manager.warm_user_cache(
            user_id=platform_user_id,
            tenant_id=tenant_id
        )
    
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
        await self.cache_manager.invalidate_role_cache(
            role_id=role_id,
            tenant_id=tenant_id
        )
    
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
        await self.cache_manager.warm_role_cache(
            role_id=role_id,
            tenant_id=tenant_id
        )
    
    # Pass-through methods that don't involve caching
    async def get_role_permissions(
        self,
        role_id: str
    ) -> List[Dict[str, Any]]:
        """Get all permissions for a specific role."""
        from ..repositories.permission_repository import PermissionRepository
        permission_repo = PermissionRepository()
        return await permission_repo.get_role_permissions(role_id)
    
    async def get_all_permissions(
        self,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all available permissions in the system."""
        from ..repositories.permission_repository import PermissionRepository
        permission_repo = PermissionRepository()
        return await permission_repo.get_all_permissions(active_only)
    
    async def get_permission_resources(self) -> List[str]:
        """Get all unique permission resources."""
        from ..repositories.permission_repository import PermissionRepository
        permission_repo = PermissionRepository()
        return await permission_repo.get_permission_resources()
    
    async def _resolve_user_id(self, user_id: str) -> Optional[str]:
        """
        Resolve user ID to platform user ID.
        
        Handles both Keycloak IDs and platform IDs.
        
        Args:
            user_id: User ID (can be Keycloak ID or platform ID)
            
        Returns:
            Platform user ID or None if not found
        """
        try:
            # First check if it's already a platform user ID
            user = await self.auth_repo.get_user_by_id(user_id)
            if user:
                logger.debug(f"User ID {user_id} is already a platform user ID")
                return user_id
        except Exception:
            # Not a platform user ID, try to resolve from Keycloak ID
            pass
        
        try:
            # Try to resolve as Keycloak ID
            user = await self.auth_repo.get_user_by_external_id(
                provider="keycloak",
                external_id=user_id
            )
            if user:
                platform_id = user.get('id')
                logger.debug(f"Resolved Keycloak ID {user_id} to platform ID {platform_id}")
                return platform_id
        except Exception as e:
            logger.error(f"Failed to resolve user ID {user_id}: {e}")
        
        logger.warning(f"Could not resolve user ID: {user_id}")
        return None