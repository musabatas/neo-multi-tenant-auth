"""
Permission service with intelligent caching and validation.
Now fully integrated with neo-commons for enhanced caching and wildcard matching.
"""
from typing import Optional, Dict, Any, List, Set
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
        # Use neo-commons auth service for token operations
        self.auth_service = create_auth_service()
        
        # Create neo-commons permission cache manager directly
        from ..repositories.permission_repository import PermissionRepository
        cache_manager = CacheManager()
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
            from src.common.exceptions.base import ForbiddenError
            raise ForbiddenError("User account is not active")
        
        # If tenant specified, verify user has access to tenant
        if tenant_id:
            tenant_access = await self.auth_repo.check_tenant_access(user_id, tenant_id)
            if not tenant_access:
                logger.warning(f"User {user_id} lacks access to tenant {tenant_id}")
                from src.common.exceptions.base import ForbiddenError
                raise ForbiddenError("No access to specified tenant")
        
        # Use neo-commons cache manager for permission checking
        has_perm = await self.cache_manager.check_permission_cached(
            user_id=user_id,
            permission=permission,
            tenant_id=tenant_id
        )
        
        if not has_perm:
            logger.warning(
                f"Permission denied: user={user_id}, permission={permission}, tenant={tenant_id}"
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
            user_id: User UUID
            permissions: List of permission names
            tenant_id: Optional tenant context
            
        Returns:
            True if user has at least one permission
        """
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(user_id)
        if is_superadmin:
            return True
        
        # Use neo-commons batch permission checking with any_of=True
        return await self.cache_manager.batch_check_permissions(
            user_id=user_id,
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
            user_id: User UUID
            permissions: List of permission names
            tenant_id: Optional tenant context
            
        Returns:
            True if user has all permissions
        """
        # Superadmin bypass
        is_superadmin = await self.auth_repo.is_user_superadmin(user_id)
        if is_superadmin:
            return True
        
        # Use neo-commons batch permission checking with require_all=True
        return await self.cache_manager.batch_check_permissions(
            user_id=user_id,
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
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of permission details
        """
        return await self.cache_manager.get_user_permissions_cached(
            user_id=user_id,
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
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            List of role assignments
        """
        return await self.cache_manager.get_user_roles_cached(
            user_id=user_id,
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
            user_id: User UUID
            tenant_id: Optional tenant context
            
        Returns:
            Dict mapping resource to set of actions
        """
        return await self.cache_manager.get_user_permission_summary_cached(
            user_id=user_id,
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
            platform_user_id,
            required_permission,
            tenant_id
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
            user_id: User UUID
            tenant_id: Optional tenant to clear specific cache
        """
        await self.cache_manager.invalidate_user_cache(
            user_id=user_id,
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
            user_id: User UUID
            tenant_id: Optional tenant context
        """
        await self.cache_manager.warm_user_cache(
            user_id=user_id,
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