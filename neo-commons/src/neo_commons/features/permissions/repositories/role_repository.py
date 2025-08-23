"""AsyncPG-based role repository implementation.

Concrete implementation of RoleRepository protocol using AsyncPG
for high-performance database operations with dynamic schema support.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import asyncpg
import json
import logging

from ....core.exceptions import DatabaseError
from ....config.constants import RoleLevel
from ..entities import Role, RoleCode, Permission, PermissionCode, RoleRepository


logger = logging.getLogger(__name__)


class AsyncPGRoleRepository:
    """AsyncPG implementation of RoleRepository protocol."""
    
    def __init__(self, connection_manager):
        """Initialize with connection manager for dynamic schema support."""
        self.connection_manager = connection_manager
    
    async def _get_connection(self, schema: str = "admin") -> asyncpg.Connection:
        """Get database connection for specified schema."""
        return await self.connection_manager.get_connection(schema)
    
    def _build_role_from_row(self, row: asyncpg.Record) -> Role:
        """Build Role entity from database row."""
        return Role(
            id=row['id'],
            code=RoleCode(row['code']),
            name=row['name'],
            description=row['description'],
            display_name=row['display_name'],
            role_level=RoleLevel(row['role_level']),
            is_system=row['is_system'],
            is_default=row['is_default'],
            requires_approval=row['requires_approval'],
            scope_type=row['scope_type'],
            priority=row['priority'],
            max_assignees=row['max_assignees'],
            auto_expire_days=row['auto_expire_days'],
            role_config=row['role_config'] or {},
            metadata=row['metadata'] or {},
            populated_permissions=row['populated_permissions'] or {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            deleted_at=row['deleted_at']
        )
    
    async def get_by_id(self, role_id: int, schema: str = "admin") -> Optional[Role]:
        """Get role by ID from specified schema."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, name, description, display_name, role_level,
                       is_system, is_default, requires_approval, scope_type,
                       priority, max_assignees, auto_expire_days,
                       role_config, metadata, populated_permissions,
                       created_at, updated_at, deleted_at
                FROM {schema}.roles
                WHERE id = $1 AND deleted_at IS NULL
            """
            
            row = await conn.fetchrow(query, role_id)
            return self._build_role_from_row(row) if row else None
            
        except Exception as e:
            logger.error(f"Failed to get role by id {role_id} from {schema}: {e}")
            raise DatabaseError(f"Failed to retrieve role: {e}")
    
    async def get_by_code(self, code: RoleCode, schema: str = "admin") -> Optional[Role]:
        """Get role by code from specified schema."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, name, description, display_name, role_level,
                       is_system, is_default, requires_approval, scope_type,
                       priority, max_assignees, auto_expire_days,
                       role_config, metadata, populated_permissions,
                       created_at, updated_at, deleted_at
                FROM {schema}.roles
                WHERE code = $1 AND deleted_at IS NULL
            """
            
            row = await conn.fetchrow(query, code.value)
            return self._build_role_from_row(row) if row else None
            
        except Exception as e:
            logger.error(f"Failed to get role by code {code} from {schema}: {e}")
            raise DatabaseError(f"Failed to retrieve role: {e}")
    
    async def get_by_codes(self, codes: List[RoleCode], schema: str = "admin") -> List[Role]:
        """Get multiple roles by codes from specified schema."""
        if not codes:
            return []
        
        try:
            conn = await self._get_connection(schema)
            code_values = [code.value for code in codes]
            
            query = f"""
                SELECT id, code, name, description, display_name, role_level,
                       is_system, is_default, requires_approval, scope_type,
                       priority, max_assignees, auto_expire_days,
                       role_config, metadata, populated_permissions,
                       created_at, updated_at, deleted_at
                FROM {schema}.roles
                WHERE code = ANY($1) AND deleted_at IS NULL
                ORDER BY priority DESC, code
            """
            
            rows = await conn.fetch(query, code_values)
            return [self._build_role_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get roles by codes from {schema}: {e}")
            raise DatabaseError(f"Failed to retrieve roles: {e}")
    
    async def list_all(
        self,
        schema: str = "admin",
        include_deleted: bool = False,
        level_filter: Optional[str] = None,
        scope_filter: Optional[str] = None
    ) -> List[Role]:
        """List all roles with optional filters."""
        try:
            conn = await self._get_connection(schema)
            
            conditions = []
            params = []
            param_count = 0
            
            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            
            if level_filter:
                param_count += 1
                conditions.append(f"role_level = ${param_count}")
                params.append(level_filter)
            
            if scope_filter:
                param_count += 1
                conditions.append(f"scope_type = ${param_count}")
                params.append(scope_filter)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
                SELECT id, code, name, description, display_name, role_level,
                       is_system, is_default, requires_approval, scope_type,
                       priority, max_assignees, auto_expire_days,
                       role_config, metadata, populated_permissions,
                       created_at, updated_at, deleted_at
                FROM {schema}.roles
                {where_clause}
                ORDER BY priority DESC, code
            """
            
            rows = await conn.fetch(query, *params)
            return [self._build_role_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list roles from {schema}: {e}")
            raise DatabaseError(f"Failed to list roles: {e}")
    
    async def list_by_level(self, role_level: str, schema: str = "admin") -> List[Role]:
        """List all roles at a specific hierarchical level."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, name, description, display_name, role_level,
                       is_system, is_default, requires_approval, scope_type,
                       priority, max_assignees, auto_expire_days,
                       role_config, metadata, populated_permissions,
                       created_at, updated_at, deleted_at
                FROM {schema}.roles
                WHERE role_level = $1 AND deleted_at IS NULL
                ORDER BY priority DESC, code
            """
            
            rows = await conn.fetch(query, role_level)
            return [self._build_role_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list roles by level {role_level} from {schema}: {e}")
            raise DatabaseError(f"Failed to list roles: {e}")
    
    async def list_default_roles(self, schema: str = "admin") -> List[Role]:
        """List all default roles that are auto-assigned."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, name, description, display_name, role_level,
                       is_system, is_default, requires_approval, scope_type,
                       priority, max_assignees, auto_expire_days,
                       role_config, metadata, populated_permissions,
                       created_at, updated_at, deleted_at
                FROM {schema}.roles
                WHERE is_default = true AND deleted_at IS NULL
                ORDER BY priority DESC, code
            """
            
            rows = await conn.fetch(query)
            return [self._build_role_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list default roles from {schema}: {e}")
            raise DatabaseError(f"Failed to list default roles: {e}")
    
    async def list_system_roles(self, schema: str = "admin") -> List[Role]:
        """List all system roles."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, name, description, display_name, role_level,
                       is_system, is_default, requires_approval, scope_type,
                       priority, max_assignees, auto_expire_days,
                       role_config, metadata, populated_permissions,
                       created_at, updated_at, deleted_at
                FROM {schema}.roles
                WHERE is_system = true AND deleted_at IS NULL
                ORDER BY priority DESC, code
            """
            
            rows = await conn.fetch(query)
            return [self._build_role_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list system roles from {schema}: {e}")
            raise DatabaseError(f"Failed to list system roles: {e}")
    
    async def get_with_permissions(self, role_id: int, schema: str = "admin") -> Optional[Role]:
        """Get role with all its permissions loaded."""
        try:
            conn = await self._get_connection(schema)
            
            # Get role with all permission details
            query = f"""
                SELECT 
                    r.id, r.code, r.name, r.description, r.display_name, r.role_level,
                    r.is_system, r.is_default, r.requires_approval, r.scope_type,
                    r.priority, r.max_assignees, r.auto_expire_days,
                    r.role_config, r.metadata, r.populated_permissions,
                    r.created_at, r.updated_at, r.deleted_at,
                    p.id as perm_id, p.code as perm_code, p.description as perm_description,
                    p.resource, p.action, p.scope_level, p.is_dangerous,
                    p.requires_mfa, p.requires_approval as perm_requires_approval,
                    p.permission_config
                FROM {schema}.roles r
                LEFT JOIN {schema}.role_permissions rp ON r.id = rp.role_id
                LEFT JOIN {schema}.permissions p ON rp.permission_id = p.id AND p.deleted_at IS NULL
                WHERE r.id = $1 AND r.deleted_at IS NULL
                ORDER BY p.code
            """
            
            rows = await conn.fetch(query, role_id)
            if not rows:
                return None
            
            # Build role from first row
            role = self._build_role_from_row(rows[0])
            
            # Add permissions if any exist
            for row in rows:
                if row['perm_id']:
                    permission = Permission(
                        id=row['perm_id'],
                        code=PermissionCode(row['perm_code']),
                        description=row['perm_description'],
                        resource=row['resource'],
                        action=row['action'],
                        scope_level=row['scope_level'],
                        is_dangerous=row['is_dangerous'],
                        requires_mfa=row['requires_mfa'],
                        requires_approval=row['perm_requires_approval'],
                        permission_config=row['permission_config'] or {}
                    )
                    role.add_permission(permission)
            
            return role
            
        except Exception as e:
            logger.error(f"Failed to get role with permissions {role_id} from {schema}: {e}")
            raise DatabaseError(f"Failed to retrieve role with permissions: {e}")
    
    async def create(self, role: Role, schema: str = "admin") -> Role:
        """Create a new role in specified schema."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                INSERT INTO {schema}.roles (
                    code, name, description, display_name, role_level,
                    is_system, is_default, requires_approval, scope_type,
                    priority, max_assignees, auto_expire_days,
                    role_config, metadata, populated_permissions,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                    NOW(), NOW()
                )
                RETURNING id, created_at, updated_at
            """
            
            row = await conn.fetchrow(
                query,
                role.code.value,
                role.name,
                role.description,
                role.display_name,
                role.role_level.value,
                role.is_system,
                role.is_default,
                role.requires_approval,
                role.scope_type,
                role.priority,
                role.max_assignees,
                role.auto_expire_days,
                role.role_config,
                role.metadata,
                role.populated_permissions
            )
            
            # Return updated role with ID and timestamps
            return Role(
                id=row['id'],
                code=role.code,
                name=role.name,
                description=role.description,
                display_name=role.display_name,
                role_level=role.role_level,
                is_system=role.is_system,
                is_default=role.is_default,
                requires_approval=role.requires_approval,
                scope_type=role.scope_type,
                priority=role.priority,
                max_assignees=role.max_assignees,
                auto_expire_days=role.auto_expire_days,
                role_config=role.role_config,
                metadata=role.metadata,
                populated_permissions=role.populated_permissions,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                deleted_at=None
            )
            
        except asyncpg.UniqueViolationError:
            raise DatabaseError(f"Role with code {role.code.value} already exists")
        except Exception as e:
            logger.error(f"Failed to create role {role.code.value} in {schema}: {e}")
            raise DatabaseError(f"Failed to create role: {e}")
    
    async def update(self, role: Role, schema: str = "admin") -> Role:
        """Update an existing role in specified schema."""
        if not role.id:
            raise DatabaseError("Cannot update role without ID")
        
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                UPDATE {schema}.roles
                SET name = $2,
                    description = $3,
                    display_name = $4,
                    requires_approval = $5,
                    scope_type = $6,
                    priority = $7,
                    max_assignees = $8,
                    auto_expire_days = $9,
                    role_config = $10,
                    metadata = $11,
                    updated_at = NOW()
                WHERE id = $1 AND deleted_at IS NULL
                RETURNING updated_at
            """
            
            row = await conn.fetchrow(
                query,
                role.id,
                role.name,
                role.description,
                role.display_name,
                role.requires_approval,
                role.scope_type,
                role.priority,
                role.max_assignees,
                role.auto_expire_days,
                role.role_config,
                role.metadata
            )
            
            if not row:
                raise DatabaseError(f"Role with ID {role.id} not found or already deleted")
            
            # Return updated role
            return Role(
                id=role.id,
                code=role.code,
                name=role.name,
                description=role.description,
                display_name=role.display_name,
                role_level=role.role_level,
                is_system=role.is_system,
                is_default=role.is_default,
                requires_approval=role.requires_approval,
                scope_type=role.scope_type,
                priority=role.priority,
                max_assignees=role.max_assignees,
                auto_expire_days=role.auto_expire_days,
                role_config=role.role_config,
                metadata=role.metadata,
                populated_permissions=role.populated_permissions,
                created_at=role.created_at,
                updated_at=row['updated_at'],
                deleted_at=role.deleted_at
            )
            
        except Exception as e:
            logger.error(f"Failed to update role {role.id} in {schema}: {e}")
            raise DatabaseError(f"Failed to update role: {e}")
    
    async def delete(self, role_id: int, schema: str = "admin") -> bool:
        """Soft delete a role by setting deleted_at."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                UPDATE {schema}.roles
                SET deleted_at = NOW(), updated_at = NOW()
                WHERE id = $1 AND deleted_at IS NULL
            """
            
            result = await conn.execute(query, role_id)
            return result.split()[-1] == "1"  # Check if one row was affected
            
        except Exception as e:
            logger.error(f"Failed to delete role {role_id} from {schema}: {e}")
            raise DatabaseError(f"Failed to delete role: {e}")
    
    async def add_permission(
        self,
        role_id: int,
        permission_id: int,
        granted_by: Optional[UUID] = None,
        granted_reason: Optional[str] = None,
        schema: str = "admin"
    ) -> bool:
        """Add a permission to a role."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                INSERT INTO {schema}.role_permissions (
                    role_id, permission_id, granted_at, granted_by, granted_reason
                ) VALUES ($1, $2, NOW(), $3, $4)
                ON CONFLICT (role_id, permission_id) DO NOTHING
            """
            
            result = await conn.execute(query, role_id, permission_id, granted_by, granted_reason)
            return result.split()[-1] == "1"  # Check if one row was inserted
            
        except Exception as e:
            logger.error(f"Failed to add permission {permission_id} to role {role_id} in {schema}: {e}")
            raise DatabaseError(f"Failed to add permission to role: {e}")
    
    async def remove_permission(self, role_id: int, permission_id: int, schema: str = "admin") -> bool:
        """Remove a permission from a role."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                DELETE FROM {schema}.role_permissions
                WHERE role_id = $1 AND permission_id = $2
            """
            
            result = await conn.execute(query, role_id, permission_id)
            return result.split()[-1] == "1"  # Check if one row was deleted
            
        except Exception as e:
            logger.error(f"Failed to remove permission {permission_id} from role {role_id} in {schema}: {e}")
            raise DatabaseError(f"Failed to remove permission from role: {e}")
    
    async def update_permissions_cache(self, role_id: int, schema: str = "admin") -> bool:
        """Update the populated_permissions JSONB cache for a role."""
        try:
            conn = await self._get_connection(schema)
            
            # Get all permissions for the role
            permissions_query = f"""
                SELECT p.code, p.description, p.resource, p.action, p.scope_level,
                       p.is_dangerous, p.requires_mfa, p.requires_approval, p.permission_config
                FROM {schema}.permissions p
                JOIN {schema}.role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = $1 AND p.deleted_at IS NULL
            """
            
            rows = await conn.fetch(permissions_query, role_id)
            
            # Build permissions cache
            permissions_cache = {}
            for row in rows:
                permissions_cache[row['code']] = {
                    'description': row['description'],
                    'resource': row['resource'],
                    'action': row['action'],
                    'scope_level': row['scope_level'],
                    'is_dangerous': row['is_dangerous'],
                    'requires_mfa': row['requires_mfa'],
                    'requires_approval': row['requires_approval'],
                    'permission_config': row['permission_config'] or {}
                }
            
            # Update role's populated_permissions cache
            update_query = f"""
                UPDATE {schema}.roles
                SET populated_permissions = $2, updated_at = NOW()
                WHERE id = $1
            """
            
            result = await conn.execute(update_query, role_id, json.dumps(permissions_cache))
            return result.split()[-1] == "1"  # Check if one row was updated
            
        except Exception as e:
            logger.error(f"Failed to update permissions cache for role {role_id} in {schema}: {e}")
            raise DatabaseError(f"Failed to update permissions cache: {e}")