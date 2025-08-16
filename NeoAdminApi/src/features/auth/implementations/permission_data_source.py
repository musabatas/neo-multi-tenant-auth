"""
Permission Data Source Implementation for Neo-Commons Integration

Implements PermissionDataSourceProtocol to bridge NeoAdminApi's permission
repositories with neo-commons PermissionCacheManager.
"""
from typing import Optional, Dict, Any, List, Set
from loguru import logger

from neo_commons.auth.protocols import PermissionDataSourceProtocol
from ..repositories.permission_repository import PermissionRepository


class NeoAdminPermissionDataSource:
    """
    Implementation of PermissionDataSourceProtocol for NeoAdminApi.
    
    Bridges the existing permission repository with neo-commons cache manager.
    """
    
    def __init__(self, permission_repo: Optional[PermissionRepository] = None):
        """
        Initialize the permission data source.
        
        Args:
            permission_repo: Optional permission repository instance
        """
        self.permission_repo = permission_repo or PermissionRepository()
        logger.debug("Initialized NeoAdminPermissionDataSource")
    
    async def check_permission(
        self,
        user_id: str,
        permission: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has permission in data source."""
        try:
            return await self.permission_repo.check_permission(
                user_id=user_id,
                permission=permission,
                tenant_id=tenant_id
            )
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user permissions from data source."""
        try:
            return await self.permission_repo.get_user_permissions(
                user_id=user_id,
                tenant_id=tenant_id
            )
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return []
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user roles from data source."""
        try:
            return await self.permission_repo.get_user_roles(
                user_id=user_id,
                tenant_id=tenant_id
            )
        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return []
    
    async def get_user_permission_summary(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Set[str]]:
        """Get user permission summary from data source."""
        try:
            summary = await self.permission_repo.get_user_permission_summary(
                user_id=user_id,
                tenant_id=tenant_id
            )
            
            # Ensure values are sets
            if isinstance(summary, dict):
                result = {}
                for resource, actions in summary.items():
                    if isinstance(actions, list):
                        result[resource] = set(actions)
                    elif isinstance(actions, set):
                        result[resource] = actions
                    else:
                        result[resource] = {str(actions)}
                return result
            
            return summary or {}
            
        except Exception as e:
            logger.error(f"Failed to get user permission summary: {e}")
            return {}
    
    async def get_users_with_role(
        self,
        role_id: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get list of user IDs with specific role."""
        try:
            if hasattr(self.permission_repo, 'get_users_with_role'):
                return await self.permission_repo.get_users_with_role(
                    role_id=role_id,
                    tenant_id=tenant_id
                )
            else:
                logger.warning("get_users_with_role not implemented in repository")
                return []
                
        except Exception as e:
            logger.error(f"Failed to get users with role: {e}")
            return []