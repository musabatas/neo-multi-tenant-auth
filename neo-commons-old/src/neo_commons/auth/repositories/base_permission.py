"""
Permission repository for multi-level RBAC (Platform + Tenant).
Handles efficient permission queries and role resolution with proper separation.
"""
from typing import List, Dict, Any, Optional, Set
from uuid import UUID
from loguru import logger

from ...repositories.base import BaseRepository
from ...utils.datetime import utc_now
from ...database.utils import process_database_record


class BasePermissionRepository(BaseRepository[Dict[str, Any]]):
    """
    Efficient permission queries for multi-level RBAC (Platform + Tenant) with dynamic schema configuration.
    
    Features:
    - Platform-level permissions (system/platform scope)
    - Tenant-level permissions (tenant scope) 
    - Optimized permission aggregation
    - Role hierarchy resolution with level enforcement
    - Time-based access validation
    - Proper separation of platform vs tenant concerns
    
    FIXED: Eliminated hardcoded 'admin' schema references for dynamic configuration.
    """
    
    def __init__(self, connection_provider, schema_name: str = "admin"):
        """
        Initialize repository with BaseRepository and configurable schema.
        
        Args:
            connection_provider: Database connection provider
            schema_name: Database schema to use (default: admin)
        """
        super().__init__(
            table_name="platform_permissions", 
            connection_provider=connection_provider,
            default_schema=schema_name
        )
        self.db = connection_provider
        self.schema_name = schema_name
    
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
        query = f"""
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
            FROM {self.get_current_schema()}.platform_user_roles ur
            JOIN {self.get_current_schema()}.platform_roles r ON r.id = ur.role_id
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
        
        db = await self.get_connection()
        results = await db.fetch(query, *params)
        
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
        query = f"""
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
            FROM {self.get_current_schema()}.tenant_user_roles ur
            JOIN {self.get_current_schema()}.platform_roles r ON r.id = ur.role_id
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
        
        db = await self.get_connection()
        results = await db.fetch(query, *params)
        
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
        if not include_role_permissions and not include_direct_permissions:
            return []
        
        # Build optimized UNION query to combine both permission sources in a single database call
        union_parts = []
        params = [user_id]
        param_idx = 1
        
        if include_role_permissions:
            union_parts.append(f"""
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
                FROM {self.get_current_schema()}.platform_user_roles ur
                JOIN {self.get_current_schema()}.platform_roles r ON r.id = ur.role_id
                JOIN {self.get_current_schema()}.role_permissions rp ON rp.role_id = r.id
                JOIN {self.get_current_schema()}.platform_permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = ${param_idx}
                    AND ur.is_active = true
                    AND r.deleted_at IS NULL
                    AND p.deleted_at IS NULL
                    AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                    AND p.scope_level = 'platform'
            """)
        
        if include_direct_permissions:
            param_idx += 1
            params.append(user_id)
            union_parts.append(f"""
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
                    100 as priority
                FROM {self.get_current_schema()}.platform_user_permissions up
                JOIN {self.get_current_schema()}.platform_permissions p ON p.id = up.permission_id
                WHERE up.user_id = ${param_idx}
                    AND up.is_active = true
                    AND p.deleted_at IS NULL
                    AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                    AND p.scope_level = 'platform'
            """)
        
        # Combine with UNION ALL and handle deduplication with window functions for better performance
        query = f"""
            WITH combined_permissions AS (
                {' UNION ALL '.join(union_parts)}
            ),
            ranked_permissions AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY id ORDER BY priority DESC, source_type) as rn
                FROM combined_permissions
            )
            SELECT id, name, resource, action, scope_level, description, is_dangerous,
                   requires_mfa, requires_approval, permissions_config, is_active,
                   source_type, source_name, priority
            FROM ranked_permissions 
            WHERE rn = 1
            ORDER BY priority DESC, name
        """
        
        db = await self.get_connection()
        results = await db.fetch(query, *params)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
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
        if not include_role_permissions and not include_direct_permissions:
            return []
        
        # Build optimized UNION query to combine both permission sources in a single database call
        union_parts = []
        params = [user_id, tenant_id]
        param_idx = 2
        
        if include_role_permissions:
            union_parts.append(f"""
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
                FROM {self.get_current_schema()}.tenant_user_roles ur
                JOIN {self.get_current_schema()}.platform_roles r ON r.id = ur.role_id
                JOIN {self.get_current_schema()}.role_permissions rp ON rp.role_id = r.id
                JOIN {self.get_current_schema()}.platform_permissions p ON p.id = rp.permission_id
                WHERE ur.user_id = $1 AND ur.tenant_id = $2
                    AND ur.is_active = true
                    AND r.deleted_at IS NULL
                    AND p.deleted_at IS NULL
                    AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                    AND p.scope_level = 'tenant'
            """)
        
        if include_direct_permissions:
            param_idx += 2  # Skip user_id, tenant_id already used
            params.extend([user_id, tenant_id])
            union_parts.append(f"""
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
                    100 as priority
                FROM {self.get_current_schema()}.tenant_user_permissions up
                JOIN {self.get_current_schema()}.platform_permissions p ON p.id = up.permission_id
                WHERE up.user_id = ${param_idx-1} AND up.tenant_id = ${param_idx}
                    AND up.is_active = true
                    AND p.deleted_at IS NULL
                    AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                    AND p.scope_level = 'tenant'
            """)
        
        # Combine with UNION ALL and handle deduplication with window functions for better performance
        query = f"""
            WITH combined_permissions AS (
                {' UNION ALL '.join(union_parts)}
            ),
            ranked_permissions AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY id ORDER BY priority DESC, source_type) as rn
                FROM combined_permissions
            )
            SELECT id, name, resource, action, scope_level, description, is_dangerous,
                   requires_mfa, requires_approval, permissions_config, is_active,
                   source_type, source_name, priority
            FROM ranked_permissions 
            WHERE rn = 1
            ORDER BY priority DESC, name
        """
        
        db = await self.get_connection()
        results = await db.fetch(query, *params)
        
        return [
            process_database_record(
                record,
                uuid_fields=['id'],
                jsonb_fields=['permissions_config']
            )
            for record in results
        ]
    
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
        query = f"""
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
            FROM {self.get_current_schema()}.platform_user_roles ur
            JOIN {self.get_current_schema()}.platform_roles r ON r.id = ur.role_id
            JOIN {self.get_current_schema()}.role_permissions rp ON rp.role_id = r.id
            JOIN {self.get_current_schema()}.platform_permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = $1
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND p.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'platform'
        """
        
        db = await self.get_connection()
        results = await db.fetch(query, user_id)
        
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
        query = f"""
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
            FROM {self.get_current_schema()}.tenant_user_roles ur
            JOIN {self.get_current_schema()}.platform_roles r ON r.id = ur.role_id
            JOIN {self.get_current_schema()}.role_permissions rp ON rp.role_id = r.id
            JOIN {self.get_current_schema()}.platform_permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = $1 AND ur.tenant_id = $2
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND p.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'tenant'
        """
        
        db = await self.get_connection()
        results = await db.fetch(query, user_id, tenant_id)
        
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
        query = f"""
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
            FROM {self.get_current_schema()}.platform_user_permissions up
            JOIN {self.get_current_schema()}.platform_permissions p ON p.id = up.permission_id
            WHERE up.user_id = $1
                AND up.is_active = true
                AND up.is_granted = true
                AND p.deleted_at IS NULL
                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'platform'
        """
        
        db = await self.get_connection()
        results = await db.fetch(query, user_id)
        
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
        query = f"""
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
            FROM {self.get_current_schema()}.tenant_user_permissions up
            JOIN {self.get_current_schema()}.platform_permissions p ON p.id = up.permission_id
            WHERE up.user_id = $1 AND up.tenant_id = $2
                AND up.is_active = true
                AND up.is_granted = true
                AND p.deleted_at IS NULL
                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'tenant'
        """
        
        db = await self.get_connection()
        results = await db.fetch(query, user_id, tenant_id)
        
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
        
        query = f"""
            SELECT EXISTS (
                SELECT 1
                FROM (
                    -- Permissions from roles
                    SELECT p.code as name
                    FROM {self.get_current_schema()}.platform_user_roles ur
                    JOIN {self.get_current_schema()}.platform_roles r ON r.id = ur.role_id
                    JOIN {self.get_current_schema()}.role_permissions rp ON rp.role_id = r.id
                    JOIN {self.get_current_schema()}.platform_permissions p ON p.id = rp.permission_id
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
                    FROM {self.get_current_schema()}.platform_user_permissions up
                    JOIN {self.get_current_schema()}.platform_permissions p ON p.id = up.permission_id
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
        
        db = await self.get_connection()
        result = await db.fetchval(query, *params)
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
        query = f"""
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
            FROM {self.get_current_schema()}.role_permissions rp
            JOIN {self.get_current_schema()}.platform_permissions p ON p.id = rp.permission_id
            WHERE rp.role_id = $1
            ORDER BY p.resource, p.action
        """
        
        db = await self.get_connection()
        results = await db.fetch(query, role_id)
        
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
        query = f"""
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
            FROM {self.get_current_schema()}.platform_permissions
        """
        
        if active_only:
            query += " WHERE deleted_at IS NULL"
        
        query += " ORDER BY resource, action"
        
        db = await self.get_connection()
        results = await db.fetch(query)
        
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
        query = f"""
            SELECT DISTINCT resource
            FROM {self.get_current_schema()}.platform_permissions
            WHERE deleted_at IS NULL
            ORDER BY resource
        """
        
        db = await self.get_connection()
        results = await db.fetch(query)
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