"""
PermissionChecker implementation for NeoAdminApi.

Protocol-compliant wrapper around existing permission services for neo-commons integration.
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from neo_commons.auth.protocols import PermissionCheckerProtocol
from src.features.auth.services.permission_service import PermissionService
from src.common.exceptions.base import ForbiddenError, UnauthorizedError


class NeoAdminPermissionChecker:
    """
    PermissionChecker implementation for NeoAdminApi.
    
    Protocol-compliant wrapper around existing PermissionService.
    """
    
    def __init__(self):
        self.permission_service = PermissionService()
        # Import here to avoid circular dependency
        from ..repositories.auth_repository import AuthRepository
        self.auth_repo = AuthRepository()
    
    async def _resolve_user_id(self, user_id: str) -> str:
        """
        Resolve user ID - map Keycloak user ID to platform user ID if needed.
        
        Args:
            user_id: User ID (could be Keycloak or platform user ID)
            
        Returns:
            Platform user ID
        """
        try:
            # First, check if this is already a platform user ID
            platform_user = await self.auth_repo.get_user_by_id(user_id)
            if platform_user:
                logger.debug(f"User ID {user_id} is already a platform user ID")
                return user_id
        except Exception:
            # Not a platform user ID, try mapping from Keycloak ID
            pass
        
        try:
            # Try to map from Keycloak user ID to platform user ID
            logger.debug(f"Attempting to map Keycloak user ID {user_id} to platform user ID")
            platform_user = await self.auth_repo.get_user_by_external_id(
                provider="keycloak",
                external_id=user_id
            )
            if platform_user:
                platform_user_id = platform_user['id']
                logger.debug(f"Mapped Keycloak user ID {user_id} to platform user ID {platform_user_id}")
                return platform_user_id
            else:
                logger.warning(f"No platform user found for Keycloak user ID {user_id}")
                return user_id  # Return original ID as fallback
        except Exception as e:
            logger.warning(f"Failed to map user ID {user_id}: {e}")
            return user_id  # Return original ID as fallback

    async def check_permission(
        self,
        user_id: str,
        permissions: List[str],
        scope: str = "platform",
        tenant_id: Optional[str] = None,
        any_of: bool = False
    ) -> bool:
        """
        Check if user has required permissions.
        
        Args:
            user_id: User ID to check permissions for (Keycloak or platform user ID)
            permissions: List of permission codes to check
            scope: Permission scope (platform/tenant/user)
            tenant_id: Optional tenant context
            any_of: If True, requires ANY permission; if False, requires ALL
            
        Returns:
            True if user has required permissions
        """
        try:
            # Resolve user ID (map Keycloak ID to platform ID if needed)
            platform_user_id = await self._resolve_user_id(user_id)
            
            # Convert single permission to list if needed
            permission_list = permissions if isinstance(permissions, list) else [permissions]
            
            if any_of:
                # Check if user has ANY of the permissions
                for permission in permission_list:
                    has_permission = await self.permission_service.check_permission(
                        user_id=platform_user_id,
                        permission=permission,
                        tenant_id=tenant_id
                    )
                    if has_permission:
                        logger.debug(f"User {platform_user_id} has permission {permission} (ANY mode)")
                        return True
                
                logger.debug(f"User {platform_user_id} missing ALL permissions {permission_list} (ANY mode)")
                return False
            else:
                # Check if user has ALL permissions
                for permission in permission_list:
                    has_permission = await self.permission_service.check_permission(
                        user_id=platform_user_id,
                        permission=permission,
                        tenant_id=tenant_id
                    )
                    if not has_permission:
                        logger.debug(f"User {platform_user_id} missing permission {permission} (ALL mode)")
                        return False
                
                logger.debug(f"User {platform_user_id} has ALL permissions {permission_list}")
                return True
                
        except Exception as e:
            logger.error(f"Permission check failed for user {user_id}: {e}")
            return False
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        scope: str = "platform"
    ) -> List[str]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User ID (Keycloak or platform user ID)
            tenant_id: Optional tenant context
            scope: Permission scope
            
        Returns:
            List of permission codes
        """
        try:
            # Resolve user ID (map Keycloak ID to platform ID if needed)
            platform_user_id = await self._resolve_user_id(user_id)
            
            permissions = await self.permission_service.get_user_permissions(
                user_id=platform_user_id,
                tenant_id=tenant_id,
                scope=scope
            )
            
            # Extract permission codes
            permission_codes = []
            for perm in permissions:
                if isinstance(perm, dict):
                    # Handle both formats: {"code": "..."} and {"resource": "...", "action": "..."}
                    if "code" in perm:
                        permission_codes.append(perm["code"])
                    elif "resource" in perm and "action" in perm:
                        permission_codes.append(f"{perm['resource']}:{perm['action']}")
                elif isinstance(perm, str):
                    permission_codes.append(perm)
            
            return permission_codes
            
        except Exception as e:
            logger.error(f"Failed to get permissions for user {user_id}: {e}")
            return []
    
    async def invalidate_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> None:
        """
        Invalidate cached permissions for a user.
        
        Args:
            user_id: User ID (Keycloak or platform user ID)
            tenant_id: Optional tenant context
        """
        try:
            # Resolve user ID (map Keycloak ID to platform ID if needed)
            platform_user_id = await self._resolve_user_id(user_id)
            
            await self.permission_service.invalidate_user_cache(platform_user_id, tenant_id)
            logger.debug(f"Invalidated permission cache for user {platform_user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to invalidate permissions cache for user {user_id}: {e}")