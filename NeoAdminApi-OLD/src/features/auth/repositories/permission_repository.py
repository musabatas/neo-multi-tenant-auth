"""
Permission repository for multi-level RBAC (Platform + Tenant).
Handles efficient permission queries and role resolution with proper separation.
"""
from typing import List, Dict, Any, Optional, Set
from uuid import UUID
from loguru import logger

from src.common.database.connection import get_database
from src.common.database.utils import process_database_record
from src.common.utils.datetime import utc_now


class PermissionRepository:
    """
    Efficient permission queries for multi-level RBAC (Platform + Tenant).
    
    Features:
    - Platform-level permissions (system/platform scope)
    - Tenant-level permissions (tenant scope) 
    - Optimized permission aggregation
    - Role hierarchy resolution with level enforcement
    - Time-based access validation
    - Proper separation of platform vs tenant concerns
    """
    
    def __init__(self):
        """Initialize repository with database connection."""
        self.db = get_database()
    
    async def get_platform_user_roles(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get platform-level roles assigned to a user.
        
        Args:
            user_id: User UUID
            active_only: Only return active roles
            
        Returns:
            List of platform role assignments with role details
        """
        query = """
            SELECT 
                ur.user_id,
                ur.role_id,
                ur.granted_by,
                ur.granted_at,
                ur.expires_at,
                ur.is_active as assignment_is_active,
                r.id as role_id,
                r.code as role_code,
                r.name as role_name,
                r.display_name as role_display_name,
                r.description as role_description,
                r.role_level as role_level,
                r.priority as role_priority,
                r.role_config as role_config,
                r.is_system as role_is_system,
                (r.deleted_at IS NULL) as role_is_active,
                0 as permissions_count
            FROM admin.platform_user_roles ur
            JOIN admin.platform_roles r ON r.id = ur.role_id
            WHERE ur.user_id = $1
        """
        
        params = [user_id]
        
        if active_only:
            query += """
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
            """
        
        query += " ORDER BY r.priority DESC, r.name"
        
        results = await self.db.fetch(query, *params)
        
        return [
            process_database_record(
                record,
                uuid_fields=['user_id', 'role_id', 'granted_by'],
                jsonb_fields=['role_config']
            )
            for record in results
        ]

    async def get_tenant_user_roles(
        self,
        user_id: str,
        tenant_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get tenant-level roles assigned to a user within a specific tenant.
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            active_only: Only return active roles
            
        Returns:
            List of tenant role assignments with role details
        """
        query = """
            SELECT 
                ur.user_id,
                ur.role_id,
                ur.tenant_id,
                ur.granted_by,
                ur.granted_at,
                ur.expires_at,
                ur.is_active as assignment_is_active,
                r.id as role_id,
                r.name as role_name,
                r.display_name as role_display_name,
                r.description as role_description,
                r.role_level as role_level,
                r.priority as role_priority,
                r.role_config as role_config,
                r.is_system as role_is_system,
                (r.deleted_at IS NULL) as role_is_active,
                0 as permissions_count
            FROM admin.tenant_user_roles ur
            JOIN admin.platform_roles r ON r.id = ur.role_id
            WHERE ur.user_id = $1 AND ur.tenant_id = $2
        """
        
        params = [user_id, tenant_id]
        
        if active_only:
            query += """
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
            """
        
        query += " ORDER BY r.priority DESC, r.name"
        
        results = await self.db.fetch(query, *params)
        
        return [
            process_database_record(
                record,
                uuid_fields=['user_id', 'role_id', 'tenant_id', 'granted_by']
            )
            for record in results
        ]
    
    async def get_platform_user_permissions(
        self,
        user_id: str,
        include_role_permissions: bool = True,
        include_direct_permissions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get platform-level permissions for a user (from roles and direct assignments).
        
        Args:
            user_id: User UUID
            include_role_permissions: Include permissions from roles
            include_direct_permissions: Include directly assigned permissions
            
        Returns:
            List of platform permissions with metadata
        """
        permissions = []
        
        # Get permissions from platform roles
        if include_role_permissions:
            role_perms = await self._get_platform_role_based_permissions(user_id)
            permissions.extend(role_perms)
        
        # Get direct platform permissions
        if include_direct_permissions:
            direct_perms = await self._get_platform_direct_permissions(user_id)
            permissions.extend(direct_perms)
        
        # Deduplicate permissions by ID while keeping the highest priority source
        unique_perms = {}
        for perm in permissions:
            perm_id = perm["id"]
            if perm_id not in unique_perms or perm.get("priority", 0) > unique_perms[perm_id].get("priority", 0):
                unique_perms[perm_id] = perm
        
        return list(unique_perms.values())
    
    async def get_tenant_user_permissions(
        self,
        user_id: str,
        tenant_id: str,
        include_role_permissions: bool = True,
        include_direct_permissions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get tenant-level permissions for a user within a specific tenant.
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            include_role_permissions: Include permissions from roles
            include_direct_permissions: Include directly assigned permissions
            
        Returns:
            List of tenant permissions with metadata
        """
        permissions = []
        
        # Get permissions from tenant roles
        if include_role_permissions:
            role_perms = await self._get_tenant_role_based_permissions(user_id, tenant_id)
            permissions.extend(role_perms)
        
        # Get direct tenant permissions
        if include_direct_permissions:
            direct_perms = await self._get_tenant_direct_permissions(user_id, tenant_id)
            permissions.extend(direct_perms)
        
        # Deduplicate permissions by ID while keeping the highest priority source
        unique_perms = {}
        for perm in permissions:
            perm_id = perm["id"]
            if perm_id not in unique_perms or perm.get("priority", 0) > unique_perms[perm_id].get("priority", 0):
                unique_perms[perm_id] = perm
        
        return list(unique_perms.values())
    
    async def _get_platform_role_based_permissions(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get platform permissions granted through platform roles.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of permissions from platform roles
        """
        query = """
            SELECT DISTINCT
                p.id,
                p.code as name,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                'platform_role' as source_type,
                r.name as source_name,
                r.priority as priority
            FROM admin.platform_user_roles ur
            JOIN admin.platform_roles r ON r.id = ur.role_id
            JOIN admin.role_permissions rp ON rp.role_id = r.id
            JOIN admin.platform_permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = $1
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND p.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'platform'
        """
        
        results = await self.db.fetch(query, user_id)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
    async def _get_tenant_role_based_permissions(
        self,
        user_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get tenant permissions granted through tenant roles.
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            
        Returns:
            List of permissions from tenant roles
        """
        query = """
            SELECT DISTINCT
                p.id,
                p.code as name,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                'tenant_role' as source_type,
                r.name as source_name,
                r.priority as priority
            FROM admin.tenant_user_roles ur
            JOIN admin.platform_roles r ON r.id = ur.role_id
            JOIN admin.role_permissions rp ON rp.role_id = r.id
            JOIN admin.platform_permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = $1 AND ur.tenant_id = $2
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND p.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'tenant'
        """
        
        results = await self.db.fetch(query, user_id, tenant_id)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
    async def _get_platform_direct_permissions(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get platform permissions directly assigned to a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of direct platform permissions
        """
        query = """
            SELECT 
                p.id,
                p.code as name,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                'platform_direct' as source_type,
                'Direct Assignment' as source_name,
                1000 as priority,
                up.granted_by,
                up.granted_at,
                up.expires_at
            FROM admin.platform_user_permissions up
            JOIN admin.platform_permissions p ON p.id = up.permission_id
            WHERE up.user_id = $1
                AND up.is_active = true
                AND up.is_granted = true
                AND p.deleted_at IS NULL
                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'platform'
        """
        
        results = await self.db.fetch(query, user_id)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id', 'granted_by'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
    async def _get_tenant_direct_permissions(
        self,
        user_id: str,
        tenant_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get tenant permissions directly assigned to a user within a tenant.
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            
        Returns:
            List of direct tenant permissions
        """
        query = """
            SELECT 
                p.id,
                p.code as name,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                'tenant_direct' as source_type,
                'Direct Assignment' as source_name,
                1000 as priority,
                up.granted_by,
                up.granted_at,
                up.expires_at,
                up.tenant_id
            FROM admin.tenant_user_permissions up
            JOIN admin.platform_permissions p ON p.id = up.permission_id
            WHERE up.user_id = $1 AND up.tenant_id = $2
                AND up.is_active = true
                AND up.is_granted = true
                AND p.deleted_at IS NULL
                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'tenant'
        """
        
        results = await self.db.fetch(query, user_id, tenant_id)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id', 'granted_by', 'tenant_id'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
    async def check_permission(
        self,
        user_id: str,
        permission_name: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has a specific permission.
        
        Args:
            user_id: User UUID
            permission_name: Permission name (e.g., "users:read")
            tenant_id: Optional tenant scope
            
        Returns:
            True if user has the permission
        """
        # Check wildcard permission first (e.g., "users:*" covers "users:read")
        resource = permission_name.split(':')[0] if ':' in permission_name else permission_name
        wildcard_permission = f"{resource}:*"
        
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM (
                    -- Permissions from roles
                    SELECT p.code as name
                    FROM admin.platform_user_roles ur
                    JOIN admin.platform_roles r ON r.id = ur.role_id
                    JOIN admin.role_permissions rp ON rp.role_id = r.id
                    JOIN admin.platform_permissions p ON p.id = rp.permission_id
                    WHERE ur.user_id = $1
                        AND ur.is_active = true
                        AND r.deleted_at IS NULL
                                        AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                        AND (p.code = $2 OR p.code = $3)
        """
        
        params = [user_id, permission_name, wildcard_permission]
        
        if tenant_id:
            query += " AND (ur.tenant_id = $4 OR ur.tenant_id IS NULL)"
            params.append(tenant_id)
        
        query += """
                    UNION
                    -- Direct permissions
                    SELECT p.code as name
                    FROM admin.platform_user_permissions up
                    JOIN admin.platform_permissions p ON p.id = up.permission_id
                    WHERE up.user_id = $1
                        AND up.is_active = true
                                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                        AND (p.code = $2 OR p.code = $3)
        """
        
        if tenant_id:
            query += " AND (up.tenant_id = $4 OR up.tenant_id IS NULL)"
        
        query += """
                ) AS all_permissions
            )
        """
        
        result = await self.db.fetchval(query, *params)
        return bool(result)
    
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
        query = """
            SELECT 
                p.id,
                p.code as name,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                true as is_active,
                NULL as granted_by,
                now() as granted_at
            FROM admin.role_permissions rp
            JOIN admin.platform_permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = $1
            ORDER BY p.resource, p.action
        """
        
        results = await self.db.fetch(query, role_id)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id', 'granted_by'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
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
        query = """
            SELECT 
                id,
                code,
                resource,
                action,
                scope_level,
                description,
                is_dangerous,
                requires_mfa,
                requires_approval,
                created_at,
                updated_at
            FROM admin.platform_permissions
        """
        
        if active_only:
            query += " WHERE deleted_at IS NULL"
        
        query += " ORDER BY resource, action"
        
        results = await self.db.fetch(query)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
    async def get_permission_resources(self) -> List[str]:
        """
        Get all unique permission resources.
        
        Returns:
            List of resource names
        """
        query = """
            SELECT DISTINCT resource
            FROM admin.platform_permissions
            WHERE deleted_at IS NULL
            ORDER BY resource
        """
        
        results = await self.db.fetch(query)
        return [record["resource"] for record in results]
    
    # Backward compatibility and convenience methods
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all roles for a user (backward compatibility).
        Combines platform and tenant roles.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant scope for tenant roles
            active_only: Only return active roles
            
        Returns:
            List of all user roles with level indicators
        """
        roles = []
        
        # Get platform roles
        platform_roles = await self.get_platform_user_roles(user_id, active_only)
        for role in platform_roles:
            role['level'] = 'platform'
            role['tenant_id'] = None
        roles.extend(platform_roles)
        
        # Get tenant roles if tenant_id provided
        if tenant_id:
            tenant_roles = await self.get_tenant_user_roles(user_id, tenant_id, active_only)
            for role in tenant_roles:
                role['level'] = 'tenant'
            roles.extend(tenant_roles)
        
        return roles
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        include_role_permissions: bool = True,
        include_direct_permissions: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user (backward compatibility).
        Combines platform and tenant permissions.
        
        Args:
            user_id: User UUID
            tenant_id: Optional tenant scope for tenant permissions
            include_role_permissions: Include permissions from roles
            include_direct_permissions: Include directly assigned permissions
            
        Returns:
            List of all user permissions with level indicators
        """
        permissions = []
        
        # Get platform permissions
        platform_perms = await self.get_platform_user_permissions(
            user_id, include_role_permissions, include_direct_permissions
        )
        for perm in platform_perms:
            perm['level'] = 'platform'
        permissions.extend(platform_perms)
        
        # Get tenant permissions if tenant_id provided
        if tenant_id:
            tenant_perms = await self.get_tenant_user_permissions(
                user_id, tenant_id, include_role_permissions, include_direct_permissions
            )
            for perm in tenant_perms:
                perm['level'] = 'tenant'
            permissions.extend(tenant_perms)
        
        return permissions
    
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
            permissions: List of permission names
            tenant_id: Optional tenant scope
            
        Returns:
            True if user has at least one permission
        """
        for permission in permissions:
            if await self.check_permission(user_id, permission, tenant_id):
                return True
        return False
    
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
            permissions: List of permission names
            tenant_id: Optional tenant scope
            
        Returns:
            True if user has all permissions
        """
        for permission in permissions:
            if not await self.check_permission(user_id, permission, tenant_id):
                return False
        return True