"""User permission service for RBAC integration."""

import logging
from typing import Dict, Any, List, Optional
from uuid import UUID

from ....core.value_objects import UserId, TenantId
from ...permissions.repositories.permission_checker import AsyncPGPermissionChecker

logger = logging.getLogger(__name__)


class UserPermissionService:
    """Service for integrating user permissions with authentication."""
    
    def __init__(self, database_service, permission_cache=None):
        """Initialize with database service and optional cache."""
        self.database_service = database_service
        self.permission_checker = AsyncPGPermissionChecker(database_service, permission_cache)
    
    async def get_user_auth_context(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> Dict[str, Any]:
        """Get complete user authentication context including roles and permissions."""
        try:
            # Get user permissions and roles (permissions now come from detailed query)
            
            roles = await self.permission_checker.get_user_roles(
                user_id, tenant_id
            )
            
            # Get detailed permission information
            permission_details = await self.permission_checker.get_user_permissions_with_details(
                user_id, tenant_id
            )
            
            # Format roles for response
            role_data = []
            for role in roles:
                role_data.append({
                    'id': role.id,
                    'code': role.code.value,
                    'name': role.name,
                    'display_name': role.display_name,
                    'role_level': role.role_level.value,
                    'is_system': role.is_system,
                    'scope_type': role.scope_type,
                    'priority': role.priority
                })
            
            # Categorize permissions by resource with full metadata
            permissions_by_resource = {}
            dangerous_permissions = []
            mfa_required_permissions = []
            approval_required_permissions = []
            
            for perm_detail in permission_details.get('permissions', []):
                resource = perm_detail['resource']
                if resource not in permissions_by_resource:
                    permissions_by_resource[resource] = []
                
                perm_info = {
                    'code': perm_detail['code'],
                    'resource': perm_detail['resource'],
                    'action': perm_detail['action'],
                    'scope_level': perm_detail['scope_level'],
                    'is_dangerous': perm_detail['is_dangerous'],
                    'requires_mfa': perm_detail['requires_mfa'],
                    'requires_approval': perm_detail['requires_approval'],
                    'permission_config': perm_detail['permission_config']
                }
                
                permissions_by_resource[resource].append(perm_info)
                
                # Track special permission categories
                if perm_detail['is_dangerous']:
                    dangerous_permissions.append(perm_detail['code'])
                if perm_detail['requires_mfa']:
                    mfa_required_permissions.append(perm_detail['code'])
                if perm_detail['requires_approval']:
                    approval_required_permissions.append(perm_detail['code'])
            
            # Flatten permissions from by_resource into a simple list
            flattened_permissions = []
            for resource_permissions in permissions_by_resource.values():
                flattened_permissions.extend(resource_permissions)
            
            return {
                'user_id': user_id.value,
                'tenant_id': tenant_id.value if tenant_id else None,
                'schema': 'admin' if tenant_id is None else f'tenant_{tenant_id.value}',
                'permissions': flattened_permissions,  # Direct list of permission objects
                'roles': {
                    'list': role_data,
                    'total_count': len(role_data),
                    'codes': [role.code.value for role in roles]
                },
                'rbac_loaded_at': None  # Will be set when loaded
            }
            
        except Exception as e:
            logger.error(f"Failed to get auth context for user {user_id.value}: {e}")
            return {
                'user_id': user_id.value,
                'tenant_id': tenant_id.value if tenant_id else None,
                'schema': 'admin' if tenant_id is None else f'tenant_{tenant_id.value}',
                'permissions': {'codes': [], 'total_count': 0, 'by_resource': {}, 'dangerous': []},
                'roles': {'list': [], 'total_count': 0, 'codes': []},
                'error': str(e)
            }
    
    async def has_permission(
        self,
        user_id: UserId,
        permission_code: str,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has specific permission."""
        return await self.permission_checker.has_permission(
            user_id, permission_code, tenant_id, scope_id
        )
    
    async def has_any_permission(
        self,
        user_id: UserId,
        permission_codes: List[str],
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has any of the specified permissions."""
        return await self.permission_checker.has_any_permission(
            user_id, permission_codes, tenant_id, scope_id
        )
    
    async def has_role(
        self,
        user_id: UserId,
        role_code: str,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has specific role."""
        try:
            roles = await self.permission_checker.get_user_roles(
                user_id, tenant_id, scope_id
            )
            return any(role.code.value == role_code for role in roles)
        except Exception as e:
            logger.error(f"Failed to check role {role_code} for user {user_id.value}: {e}")
            return False
    
    async def get_user_summary(self, user_id: UserId, tenant_id: Optional[TenantId] = None) -> Dict[str, Any]:
        """Get summary of user's permissions and roles for display."""
        auth_context = await self.get_user_auth_context(user_id, tenant_id)
        
        return {
            'user_id': user_id.value,
            'tenant_id': tenant_id.value if tenant_id else None,
            'permissions_count': auth_context['permissions']['total_count'],
            'roles_count': auth_context['roles']['total_count'],
            'has_dangerous_permissions': len(auth_context['permissions']['dangerous']) > 0,
            'resources': list(auth_context['permissions']['by_resource'].keys()),
            'role_names': [role['name'] for role in auth_context['roles']['list']],
            'highest_role_level': self._get_highest_role_level(auth_context['roles']['list'])
        }
    
    def _get_highest_role_level(self, roles: List[Dict[str, Any]]) -> Optional[str]:
        """Get the highest role level from user's roles."""
        if not roles:
            return None
        
        # Role level hierarchy (higher number = higher privilege)
        level_priority = {
            'platform': 5,
            'admin': 4,
            'manager': 3,
            'member': 2,
            'guest': 1
        }
        
        highest_priority = 0
        highest_level = None
        
        for role in roles:
            role_level = role.get('role_level', 'member')
            priority = level_priority.get(role_level, 0)
            if priority > highest_priority:
                highest_priority = priority
                highest_level = role_level
        
        return highest_level