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
            user_id: User ID to check permissions for
            permissions: List of permission codes to check
            scope: Permission scope (platform/tenant/user)
            tenant_id: Optional tenant context
            any_of: If True, requires ANY permission; if False, requires ALL
            
        Returns:
            True if user has required permissions
        """
        try:
            # Convert single permission to list if needed
            permission_list = permissions if isinstance(permissions, list) else [permissions]
            
            if any_of:
                # Check if user has ANY of the permissions
                for permission in permission_list:
                    has_permission = await self.permission_service.check_permission(
                        user_id=user_id,
                        permission_code=permission,
                        tenant_id=tenant_id,
                        scope=scope
                    )
                    if has_permission:
                        logger.debug(f"User {user_id} has permission {permission} (ANY mode)")
                        return True
                
                logger.debug(f"User {user_id} missing ALL permissions {permission_list} (ANY mode)")
                return False
            else:
                # Check if user has ALL permissions
                for permission in permission_list:
                    has_permission = await self.permission_service.check_permission(
                        user_id=user_id,
                        permission_code=permission,
                        tenant_id=tenant_id,
                        scope=scope
                    )
                    if not has_permission:
                        logger.debug(f"User {user_id} missing permission {permission} (ALL mode)")
                        return False
                
                logger.debug(f"User {user_id} has ALL permissions {permission_list}")
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
            user_id: User ID
            tenant_id: Optional tenant context
            scope: Permission scope
            
        Returns:
            List of permission codes
        """
        try:
            permissions = await self.permission_service.get_user_permissions(
                user_id=user_id,
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
            user_id: User ID
            tenant_id: Optional tenant context
        """
        try:
            await self.permission_service.invalidate_user_cache(user_id, tenant_id)
            logger.debug(f"Invalidated permission cache for user {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to invalidate permissions cache for user {user_id}: {e}")