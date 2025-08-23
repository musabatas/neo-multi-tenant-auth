"""
Repository for role-related database operations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import logging
import json
import asyncpg

from neo_commons.repositories.base import BaseRepository
from neo_commons.database.utils import process_database_record
from neo_commons.models.pagination import PaginationParams
from src.common.database.connection_provider import neo_admin_connection_provider
from src.common.exceptions.base import NotFoundError, ConflictError
from src.features.roles.models.domain import (
    PlatformRole, PlatformPermission, RolePermission,
    UserRoleAssignment, TenantUserRoleAssignment,
    PlatformRoleLevel, PermissionScopeLevel
)

logger = logging.getLogger(__name__)


class RoleRepository(BaseRepository[Dict[str, Any]]):
    """Repository for platform roles."""
    
    def __init__(self, schema: str = "admin"):
        """Initialize role repository with configurable schema.
        
        Args:
            schema: Database schema to use (default: admin)
        """
        super().__init__(
            table_name="platform_roles", 
            default_schema=schema,
            connection_provider=neo_admin_connection_provider
        )
    
    async def get_by_id(self, role_id: int) -> Optional[PlatformRole]:
        """Get role by ID."""
        db = await self.get_connection()
        query = f"""
            SELECT * FROM {self.get_current_schema()}.{self.table_name}
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        row = await db.fetchrow(query, role_id)
        if not row:
            return None
        
        return self._row_to_role(row)
    
    async def get_by_code(self, code: str) -> Optional[PlatformRole]:
        """Get role by code."""
        db = await self.get_connection()
        query = f"""
            SELECT * FROM {self.get_current_schema()}.{self.table_name}
            WHERE code = $1 AND deleted_at IS NULL
        """
        
        row = await db.fetchrow(query, code)
        if not row:
            return None
        
        return self._row_to_role(row)
    
    async def list_roles(
        self,
        filters: Dict[str, Any],
        pagination: PaginationParams
    ) -> tuple[List[PlatformRole], int]:
        """List roles with filters and pagination."""
        db = await self.get_connection()
        
        # Build WHERE clause
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters.get("code"):
            param_count += 1
            where_conditions.append(f"code ILIKE ${param_count}")
            params.append(f"%{filters['code']}%")
        
        if filters.get("name"):
            param_count += 1
            where_conditions.append(f"name ILIKE ${param_count}")
            params.append(f"%{filters['name']}%")
        
        if filters.get("role_level"):
            param_count += 1
            where_conditions.append(f"role_level = ${param_count}")
            params.append(filters["role_level"])
        
        if filters.get("is_system") is not None:
            param_count += 1
            where_conditions.append(f"is_system = ${param_count}")
            params.append(filters["is_system"])
        
        if filters.get("is_default") is not None:
            param_count += 1
            where_conditions.append(f"is_default = ${param_count}")
            params.append(filters["is_default"])
        
        if filters.get("tenant_scoped") is not None:
            param_count += 1
            where_conditions.append(f"tenant_scoped = ${param_count}")
            params.append(filters["tenant_scoped"])
        
        if filters.get("min_priority") is not None:
            param_count += 1
            where_conditions.append(f"priority >= ${param_count}")
            params.append(filters["min_priority"])
        
        if filters.get("max_priority") is not None:
            param_count += 1
            where_conditions.append(f"priority <= ${param_count}")
            params.append(filters["max_priority"])
        
        where_clause = " AND ".join(where_conditions)
        
        # Count query
        count_query = f"""
            SELECT COUNT(*) FROM {self.get_current_schema()}.{self.table_name}
            WHERE {where_clause}
        """
        total_count = await db.fetchval(count_query, *params)
        
        # List query with pagination
        offset = (pagination.page - 1) * pagination.page_size
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        
        list_query = f"""
            SELECT r.*,
                   (SELECT COUNT(*) FROM {self.get_current_schema()}.role_permissions WHERE role_id = r.id) as permission_count,
                   (SELECT COUNT(*) FROM {self.get_current_schema()}.platform_user_roles WHERE role_id = r.id AND is_active = true) as user_count
            FROM {self.get_current_schema()}.{self.table_name} r
            WHERE {where_clause}
            ORDER BY priority DESC, name ASC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        params.extend([pagination.page_size, offset])
        rows = await db.fetch(list_query, *params)
        
        roles = [self._row_to_role(row) for row in rows]
        
        return roles, total_count
    
    async def create(self, role_data: Dict[str, Any]) -> PlatformRole:
        """Create a new role."""
        db = await self.get_connection()
        
        # Check if code already exists
        existing = await self.get_by_code(role_data["code"])
        if existing:
            raise ConflictError(
                message=f"Role with code '{role_data['code']}' already exists",
                conflicting_field="code",
                conflicting_value=role_data["code"]
            )
        
        query = f"""
            INSERT INTO {self.get_current_schema()}.{self.table_name} (
                code, name, display_name, description,
                role_level, priority, is_system, is_default,
                max_assignees, tenant_scoped, requires_approval,
                role_config, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
            )
            RETURNING *
        """
        
        row = await db.fetchrow(
            query,
            role_data["code"],
            role_data["name"],
            role_data.get("display_name"),
            role_data.get("description"),
            role_data.get("role_level", "platform"),
            role_data.get("priority", 100),
            role_data.get("is_system", False),
            role_data.get("is_default", False),
            role_data.get("max_assignees"),
            role_data.get("tenant_scoped", False),
            role_data.get("requires_approval", False),
            json.dumps(role_data.get("role_config", {})),
            json.dumps(role_data.get("metadata", {}))
        )
        
        return self._row_to_role(row)
    
    async def update(self, role_id: int, updates: Dict[str, Any]) -> Optional[PlatformRole]:
        """Update a role."""
        db = await self.get_connection()
        
        # Build update query dynamically
        set_clauses = []
        params = []
        param_count = 0
        
        # Map of field names to their types
        json_fields = {"role_config", "metadata"}
        
        for field, value in updates.items():
            if value is not None:
                param_count += 1
                set_clauses.append(f"{field} = ${param_count}")
                
                if field in json_fields:
                    params.append(json.dumps(value))
                else:
                    params.append(value)
        
        if not set_clauses:
            # Nothing to update
            return await self.get_by_id(role_id)
        
        param_count += 1
        query = f"""
            UPDATE {self.get_current_schema()}.{self.table_name}
            SET {', '.join(set_clauses)}
            WHERE id = ${param_count} AND deleted_at IS NULL
            RETURNING *
        """
        
        params.append(role_id)
        row = await db.fetchrow(query, *params)
        
        if not row:
            return None
        
        return self._row_to_role(row)
    
    async def delete(self, role_id: int) -> bool:
        """Soft delete a role."""
        db = await self.get_connection()
        query = f"""
            UPDATE {self.get_current_schema()}.{self.table_name}
            SET deleted_at = NOW()
            WHERE id = $1 AND deleted_at IS NULL
            RETURNING id
        """
        
        result = await db.fetchval(query, role_id)
        return result is not None
    
    async def get_role_permissions(self, role_id: int) -> List[PlatformPermission]:
        """Get all permissions for a role."""
        db = await self.get_connection()
        query = """
            SELECT p.*
            FROM admin.platform_permissions p
            JOIN admin.role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = $1 AND p.deleted_at IS NULL
            ORDER BY p.resource, p.action
        """
        
        rows = await db.fetch(query, role_id)
        return [self._row_to_permission(row) for row in rows]
    
    async def update_role_permissions(
        self,
        role_id: int,
        permission_ids: List[int],
        replace: bool = False
    ) -> List[PlatformPermission]:
        """Update role permissions."""
        
        db = await self.get_connection()
        
        async with db.transaction():
            if replace:
                # Remove all existing permissions
                await db.execute(
                    "DELETE FROM admin.role_permissions WHERE role_id = $1",
                    role_id
                )
            
            # Add new permissions
            if permission_ids:
                # Build bulk insert
                values = [(role_id, perm_id) for perm_id in permission_ids]
                await db.executemany(
                    """
                    INSERT INTO admin.role_permissions (role_id, permission_id)
                    VALUES ($1, $2)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                    """,
                    values
                )
        
        # Return updated permissions
        return await self.get_role_permissions(role_id)
    
    async def assign_role_to_user(
        self,
        user_id: UUID,
        role_id: int,
        granted_by: Optional[UUID] = None,
        granted_reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        tenant_id: Optional[UUID] = None
    ) -> UserRoleAssignment:
        """Assign a role to a user."""
        
        db = await self.get_connection()
        
        if tenant_id:
            # Tenant-specific assignment
            query = """
                INSERT INTO admin.tenant_user_roles (
                    tenant_id, user_id, role_id, granted_by,
                    granted_reason, expires_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (tenant_id, user_id, role_id) 
                DO UPDATE SET
                    granted_by = EXCLUDED.granted_by,
                    granted_reason = EXCLUDED.granted_reason,
                    granted_at = NOW(),
                    expires_at = EXCLUDED.expires_at,
                    is_active = true
                RETURNING *
            """
            row = await db.fetchrow(
                query, tenant_id, user_id, role_id,
                granted_by, granted_reason, expires_at
            )
        else:
            # Platform-level assignment
            query = """
                INSERT INTO admin.platform_user_roles (
                    user_id, role_id, granted_by,
                    granted_reason, expires_at
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, role_id)
                DO UPDATE SET
                    granted_by = EXCLUDED.granted_by,
                    granted_reason = EXCLUDED.granted_reason,
                    granted_at = NOW(),
                    expires_at = EXCLUDED.expires_at,
                    is_active = true
                RETURNING *
            """
            row = await db.fetchrow(
                query, user_id, role_id,
                granted_by, granted_reason, expires_at
            )
        
        return self._row_to_assignment(row)
    
    async def remove_role_from_user(
        self,
        user_id: UUID,
        role_id: int,
        tenant_id: Optional[UUID] = None
    ) -> bool:
        """Remove a role from a user."""
        
        db = await self.get_connection()
        
        if tenant_id:
            query = """
                UPDATE admin.tenant_user_roles
                SET is_active = false
                WHERE tenant_id = $1 AND user_id = $2 AND role_id = $3
                RETURNING user_id
            """
            result = await db.fetchval(query, tenant_id, user_id, role_id)
        else:
            query = """
                UPDATE admin.platform_user_roles
                SET is_active = false
                WHERE user_id = $1 AND role_id = $2
                RETURNING user_id
            """
            result = await db.fetchval(query, user_id, role_id)
        
        return result is not None
    
    async def get_user_role_assignments(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        include_inactive: bool = False
    ) -> List[UserRoleAssignment]:
        """Get all role assignments for a user."""
        
        db = await self.get_connection()
        active_filter = "" if include_inactive else "AND ur.is_active = true"
        
        if tenant_id:
            query = f"""
                SELECT ur.*, r.code as role_code, r.name as role_name
                FROM admin.tenant_user_roles ur
                JOIN admin.platform_roles r ON ur.role_id = r.id
                WHERE ur.tenant_id = $1 AND ur.user_id = $2 {active_filter}
                ORDER BY r.priority DESC
            """
            rows = await db.fetch(query, tenant_id, user_id)
        else:
            query = f"""
                SELECT ur.*, r.code as role_code, r.name as role_name
                FROM admin.platform_user_roles ur
                JOIN admin.platform_roles r ON ur.role_id = r.id
                WHERE ur.user_id = $1 {active_filter}
                ORDER BY r.priority DESC
            """
            rows = await db.fetch(query, user_id)
        
        return [self._row_to_assignment(row) for row in rows]
    
    def _row_to_role(self, row: asyncpg.Record) -> PlatformRole:
        """Convert database row to PlatformRole."""
        data = dict(row)
        
        # Handle JSONB fields
        if isinstance(data.get("role_config"), str):
            data["role_config"] = json.loads(data["role_config"])
        if isinstance(data.get("metadata"), str):
            data["metadata"] = json.loads(data["metadata"])
        
        # Handle enum fields
        if data.get("role_level") and hasattr(data["role_level"], "value"):
            data["role_level"] = data["role_level"].value
        
        # Include counts if available
        if "permission_count" in data:
            data["permission_count"] = data["permission_count"]
        if "user_count" in data:
            data["user_count"] = data["user_count"]
        
        return PlatformRole(**data)
    
    def _row_to_permission(self, row: asyncpg.Record) -> PlatformPermission:
        """Convert database row to PlatformPermission."""
        data = dict(row)
        
        # Handle JSONB fields
        if isinstance(data.get("permissions_config"), str):
            data["permissions_config"] = json.loads(data["permissions_config"])
        
        # Handle enum fields
        if data.get("scope_level") and hasattr(data["scope_level"], "value"):
            data["scope_level"] = data["scope_level"].value
        
        return PlatformPermission(**data)
    
    def _row_to_assignment(self, row: asyncpg.Record) -> UserRoleAssignment:
        """Convert database row to UserRoleAssignment."""
        data = dict(row)
        
        # Convert UUID fields to string if needed
        for field in ["user_id", "granted_by", "tenant_id"]:
            if field in data and data[field]:
                data[field] = str(data[field])
        
        # Remove extra fields not in model
        data.pop("role_code", None)
        data.pop("role_name", None)
        
        return UserRoleAssignment(**data)