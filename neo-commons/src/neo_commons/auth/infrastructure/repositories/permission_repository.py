"""
Permission repository implementation using AsyncPG.

Migrated from NeoAdminApi with Clean Architecture patterns.
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from ...domain.entities.permission import Permission, PermissionScope, PermissionGroup
from ...domain.protocols.repository_protocols import PermissionRepositoryProtocol


class PermissionRepository:
    """
    AsyncPG implementation of permission repository.
    
    Handles efficient permission queries for multi-level RBAC.
    Migrated from NeoAdminApi/src/features/auth/repositories/permission_repository.py
    """
    
    def __init__(self, database_manager, tenant_schema: str = "tenant_template", admin_schema: str = "admin"):
        """
        Initialize with database connection manager and configurable schemas.
        
        Args:
            database_manager: Database connection manager
            tenant_schema: Schema name for tenant-scoped tables (default: tenant_template)
            admin_schema: Schema name for admin/platform tables (default: admin)
        """
        self.db = database_manager
        self.tenant_schema = tenant_schema
        self.admin_schema = admin_schema
    
    async def get_permission_by_id(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID."""
        query = f"""
            SELECT 
                id, code, resource, action, scope_level, description,
                is_dangerous, requires_mfa, requires_approval,
                permissions_config, (deleted_at IS NULL) as is_active,
                created_at, updated_at
            FROM {self.admin_schema}.platform_permissions
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        record = await self.db.fetchrow(query, permission_id)
        if not record:
            return None
        
        return self._record_to_permission(record)
    
    async def get_permission_by_code(self, code: str) -> Optional[Permission]:
        """Get permission by code (e.g., 'users:read')."""
        query = f"""
            SELECT 
                id, code, resource, action, scope_level, description,
                is_dangerous, requires_mfa, requires_approval,
                permissions_config, (deleted_at IS NULL) as is_active,
                created_at, updated_at
            FROM {self.admin_schema}.platform_permissions
            WHERE code = $1 AND deleted_at IS NULL
        """
        
        record = await self.db.fetchrow(query, code)
        if not record:
            return None
        
        return self._record_to_permission(record)
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        include_role_permissions: bool = True,
        include_direct_permissions: bool = True
    ) -> List[Permission]:
        """Get all permissions for a user in given context."""
        permissions = []
        
        # Get platform permissions
        platform_perms = await self.get_platform_user_permissions(user_id)
        permissions.extend(platform_perms)
        
        # Get tenant permissions if tenant_id provided
        if tenant_id:
            tenant_perms = await self.get_tenant_user_permissions(user_id, tenant_id)
            permissions.extend(tenant_perms)
        
        # Deduplicate by permission ID
        unique_perms = {}
        for perm in permissions:
            unique_perms[perm.id] = perm
        
        return list(unique_perms.values())
    
    async def get_platform_user_permissions(self, user_id: str) -> List[Permission]:
        """Get platform-level permissions for user."""
        permissions = []
        
        # Get permissions from platform roles
        role_perms = await self._get_platform_role_based_permissions(user_id)
        permissions.extend(role_perms)
        
        # Get direct platform permissions
        direct_perms = await self._get_platform_direct_permissions(user_id)
        permissions.extend(direct_perms)
        
        # Deduplicate by ID while keeping highest priority source
        unique_perms = {}
        for perm in permissions:
            perm_id = perm.id
            if perm_id not in unique_perms:
                unique_perms[perm_id] = perm
        
        return list(unique_perms.values())
    
    async def get_tenant_user_permissions(self, user_id: str, tenant_id: str) -> List[Permission]:
        """Get tenant-level permissions for user."""
        permissions = []
        
        # Get permissions from tenant roles
        role_perms = await self._get_tenant_role_based_permissions(user_id, tenant_id)
        permissions.extend(role_perms)
        
        # Get direct tenant permissions
        direct_perms = await self._get_tenant_direct_permissions(user_id, tenant_id)
        permissions.extend(direct_perms)
        
        # Deduplicate by ID while keeping highest priority source
        unique_perms = {}
        for perm in permissions:
            perm_id = perm.id
            if perm_id not in unique_perms:
                unique_perms[perm_id] = perm
        
        return list(unique_perms.values())
    
    async def check_permission(
        self,
        user_id: str,
        permission_code: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has a specific permission."""
        # Check wildcard permission first (e.g., "users:*" covers "users:read")
        resource = permission_code.split(':')[0] if ':' in permission_code else permission_code
        wildcard_permission = f"{resource}:*"
        
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM (
                    -- Permissions from platform roles
                    SELECT p.code as name
                    FROM {self.admin_schema}.$1 ur
                    JOIN {self.admin_schema}.$1 r ON r.id = ur.role_id
                    JOIN {self.admin_schema}.$1 rp ON rp.role_id = r.id
                    JOIN {self.admin_schema}.$1 p ON p.id = rp.permission_id
                    WHERE ur.user_id = $1
                        AND ur.is_active = true
                        AND r.deleted_at IS NULL
                        AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                        AND (p.code = $2 OR p.code = $3)
        """
        
        params = [user_id, permission_code, wildcard_permission]
        
        if tenant_id:
            query += """
                    UNION
                    -- Permissions from tenant roles
                    SELECT p.code as name
                    FROM {self.admin_schema}.$1 ur
                    JOIN {self.admin_schema}.$1 r ON r.id = ur.role_id
                    JOIN {self.admin_schema}.$1 rp ON rp.role_id = r.id
                    JOIN {self.admin_schema}.$1 p ON p.id = rp.permission_id
                    WHERE ur.user_id = $1 AND ur.tenant_id = $4
                        AND ur.is_active = true
                        AND r.deleted_at IS NULL
                        AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                        AND (p.code = $2 OR p.code = $3)
            """
            params.append(tenant_id)
        
        query += """
                    UNION
                    -- Direct platform permissions
                    SELECT p.code as name
                    FROM {self.admin_schema}.$1 up
                    JOIN {self.admin_schema}.$1 p ON p.id = up.permission_id
                    WHERE up.user_id = $1
                        AND up.is_active = true
                        AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                        AND (p.code = $2 OR p.code = $3)
        """
        
        if tenant_id:
            query += """
                    UNION
                    -- Direct tenant permissions
                    SELECT p.code as name
                    FROM {self.admin_schema}.$1 up
                    JOIN {self.admin_schema}.$1 p ON p.id = up.permission_id
                    WHERE up.user_id = $1 AND up.tenant_id = $4
                        AND up.is_active = true
                        AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                        AND (p.code = $2 OR p.code = $3)
            """
        
        query += """
                ) AS all_permissions
            )
        """
        
        result = await self.db.fetchval(query, *params)
        return bool(result)
    
    async def get_all_permissions(self) -> List[Permission]:
        """Get all available permissions."""
        query = f"""
            SELECT 
                id, code, resource, action, scope_level, description,
                is_dangerous, requires_mfa, requires_approval,
                permissions_config, (deleted_at IS NULL) as is_active,
                created_at, updated_at
            FROM {self.admin_schema}.platform_permissions
            WHERE deleted_at IS NULL
            ORDER BY resource, action
        """
        
        records = await self.db.fetch(query)
        return [self._record_to_permission(record) for record in records]
    
    async def get_permission_resources(self) -> List[str]:
        """Get all unique resource types from permissions."""
        query = f"""
            SELECT DISTINCT resource 
            FROM {self.admin_schema}.platform_permissions
            WHERE deleted_at IS NULL
            ORDER BY resource
        """
        
        records = await self.db.fetch(query)
        return [record['resource'] for record in records]
    
    async def get_permission_group_by_id(self, group_id: str) -> Optional[PermissionGroup]:
        """Get permission group by ID."""
        # This would need to be implemented based on your permission group schema
        # For now, return None as groups might not be implemented yet
        return None
    
    async def get_permission_groups(self, active_only: bool = True) -> List[PermissionGroup]:
        """Get all permission groups."""
        # This would need to be implemented based on your permission group schema
        return []
    
    async def _get_platform_role_based_permissions(self, user_id: str) -> List[Permission]:
        """Get platform permissions granted through platform roles."""
        query = f"""
            SELECT DISTINCT
                p.id,
                p.code,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                p.created_at,
                p.updated_at
            FROM {self.admin_schema}.platform_user_roles ur
            JOIN {self.admin_schema}.platform_roles r ON r.id = ur.role_id
            JOIN {self.admin_schema}.role_permissions rp ON rp.role_id = r.id
            JOIN {self.admin_schema}.platform_permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = $1
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND p.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'platform'
        """
        
        records = await self.db.fetch(query, user_id)
        return [self._record_to_permission(record) for record in records]
    
    async def _get_tenant_role_based_permissions(self, user_id: str, tenant_id: str) -> List[Permission]:
        """Get tenant permissions granted through tenant roles."""
        query = f"""
            SELECT DISTINCT
                p.id,
                p.code,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                p.created_at,
                p.updated_at
            FROM {self.admin_schema}.tenant_user_roles ur
            JOIN {self.admin_schema}.platform_roles r ON r.id = ur.role_id
            JOIN {self.admin_schema}.role_permissions rp ON rp.role_id = r.id
            JOIN {self.admin_schema}.platform_permissions p ON p.id = rp.permission_id
            WHERE ur.user_id = $1
                AND ur.tenant_id = $2
                AND ur.is_active = true
                AND r.deleted_at IS NULL
                AND p.deleted_at IS NULL
                AND (ur.expires_at IS NULL OR ur.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level IN ('tenant', 'multi_tenant')
        """
        
        records = await self.db.fetch(query, user_id, tenant_id)
        return [self._record_to_permission(record) for record in records]
    
    async def _get_platform_direct_permissions(self, user_id: str) -> List[Permission]:
        """Get platform permissions granted directly to user."""
        query = f"""
            SELECT DISTINCT
                p.id,
                p.code,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                p.created_at,
                p.updated_at
            FROM {self.admin_schema}.platform_user_permissions up
            JOIN {self.admin_schema}.platform_permissions p ON p.id = up.permission_id
            WHERE up.user_id = $1
                AND up.is_active = true
                AND p.deleted_at IS NULL
                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level = 'platform'
        """
        
        records = await self.db.fetch(query, user_id)
        return [self._record_to_permission(record) for record in records]
    
    async def _get_tenant_direct_permissions(self, user_id: str, tenant_id: str) -> List[Permission]:
        """Get tenant permissions granted directly to user."""
        query = f"""
            SELECT DISTINCT
                p.id,
                p.code,
                p.resource,
                p.action,
                p.scope_level,
                p.description,
                p.is_dangerous,
                p.requires_mfa,
                p.requires_approval,
                p.permissions_config,
                (p.deleted_at IS NULL) as is_active,
                p.created_at,
                p.updated_at
            FROM {self.admin_schema}.tenant_user_permissions up
            JOIN {self.admin_schema}.platform_permissions p ON p.id = up.permission_id
            WHERE up.user_id = $1
                AND up.tenant_id = $2
                AND up.is_active = true
                AND p.deleted_at IS NULL
                AND (up.expires_at IS NULL OR up.expires_at > CURRENT_TIMESTAMP)
                AND p.scope_level IN ('tenant', 'multi_tenant')
        """
        
        records = await self.db.fetch(query, user_id, tenant_id)
        return [self._record_to_permission(record) for record in records]
    
    def _record_to_permission(self, record: Dict[str, Any]) -> Permission:
        """Convert database record to Permission entity."""
        return Permission(
            id=str(record["id"]),
            code=record["code"],
            resource=record["resource"],
            action=record["action"],
            scope_level=PermissionScope(record["scope_level"]),
            description=record.get("description"),
            is_dangerous=record.get("is_dangerous", False),
            requires_mfa=record.get("requires_mfa", False),
            requires_approval=record.get("requires_approval", False),
            config=record.get("permissions_config", {}),
            is_active=record.get("is_active", True),
            created_at=record.get("created_at"),
            updated_at=record.get("updated_at")
        )