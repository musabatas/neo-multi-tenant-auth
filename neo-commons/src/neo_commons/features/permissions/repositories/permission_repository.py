"""AsyncPG-based permission repository implementation.

Concrete implementation of PermissionRepository protocol using AsyncPG
for high-performance database operations with dynamic schema support.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
import logging

from ....core.exceptions import DatabaseError
from ....config.constants import PermissionScope
from ..entities import Permission, PermissionCode, PermissionRepository


logger = logging.getLogger(__name__)


class AsyncPGPermissionRepository:
    """AsyncPG implementation of PermissionRepository protocol."""
    
    def __init__(self, connection_manager):
        """Initialize with connection manager for dynamic schema support."""
        self.connection_manager = connection_manager
    
    async def _get_connection(self, schema: str = "admin") -> asyncpg.Connection:
        """Get database connection for specified schema."""
        return await self.connection_manager.get_connection(schema)
    
    def _build_permission_from_row(self, row: asyncpg.Record) -> Permission:
        """Build Permission entity from database row."""
        return Permission(
            id=row['id'],
            code=PermissionCode(row['code']),
            description=row['description'],
            resource=row['resource'],
            action=row['action'],
            scope_level=PermissionScope(row['scope_level']),
            is_dangerous=row['is_dangerous'],
            requires_mfa=row['requires_mfa'],
            requires_approval=row['requires_approval'],
            permission_config=row['permission_config'] or {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            deleted_at=row['deleted_at']
        )
    
    async def get_by_id(self, permission_id: int, schema: str = "admin") -> Optional[Permission]:
        """Get permission by ID from specified schema."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, description, resource, action, scope_level,
                       is_dangerous, requires_mfa, requires_approval, permission_config,
                       created_at, updated_at, deleted_at
                FROM {schema}.permissions
                WHERE id = $1 AND deleted_at IS NULL
            """
            
            row = await conn.fetchrow(query, permission_id)
            return self._build_permission_from_row(row) if row else None
            
        except Exception as e:
            logger.error(f"Failed to get permission by id {permission_id} from {schema}: {e}")
            raise DatabaseError(f"Failed to retrieve permission: {e}")
    
    async def get_by_code(self, code: PermissionCode, schema: str = "admin") -> Optional[Permission]:
        """Get permission by code from specified schema."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, description, resource, action, scope_level,
                       is_dangerous, requires_mfa, requires_approval, permission_config,
                       created_at, updated_at, deleted_at
                FROM {schema}.permissions
                WHERE code = $1 AND deleted_at IS NULL
            """
            
            row = await conn.fetchrow(query, code.value)
            return self._build_permission_from_row(row) if row else None
            
        except Exception as e:
            logger.error(f"Failed to get permission by code {code} from {schema}: {e}")
            raise DatabaseError(f"Failed to retrieve permission: {e}")
    
    async def get_by_codes(self, codes: List[PermissionCode], schema: str = "admin") -> List[Permission]:
        """Get multiple permissions by codes from specified schema."""
        if not codes:
            return []
        
        try:
            conn = await self._get_connection(schema)
            code_values = [code.value for code in codes]
            
            query = f"""
                SELECT id, code, description, resource, action, scope_level,
                       is_dangerous, requires_mfa, requires_approval, permission_config,
                       created_at, updated_at, deleted_at
                FROM {schema}.permissions
                WHERE code = ANY($1) AND deleted_at IS NULL
                ORDER BY code
            """
            
            rows = await conn.fetch(query, code_values)
            return [self._build_permission_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to get permissions by codes from {schema}: {e}")
            raise DatabaseError(f"Failed to retrieve permissions: {e}")
    
    async def list_all(
        self,
        schema: str = "admin",
        include_deleted: bool = False,
        resource_filter: Optional[str] = None,
        scope_filter: Optional[str] = None
    ) -> List[Permission]:
        """List all permissions with optional filters."""
        try:
            conn = await self._get_connection(schema)
            
            conditions = []
            params = []
            param_count = 0
            
            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            
            if resource_filter:
                param_count += 1
                conditions.append(f"resource = ${param_count}")
                params.append(resource_filter)
            
            if scope_filter:
                param_count += 1
                conditions.append(f"scope_level = ${param_count}")
                params.append(scope_filter)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            query = f"""
                SELECT id, code, description, resource, action, scope_level,
                       is_dangerous, requires_mfa, requires_approval, permission_config,
                       created_at, updated_at, deleted_at
                FROM {schema}.permissions
                {where_clause}
                ORDER BY resource, action
            """
            
            rows = await conn.fetch(query, *params)
            return [self._build_permission_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list permissions from {schema}: {e}")
            raise DatabaseError(f"Failed to list permissions: {e}")
    
    async def list_by_resource(self, resource: str, schema: str = "admin") -> List[Permission]:
        """List all permissions for a specific resource."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, description, resource, action, scope_level,
                       is_dangerous, requires_mfa, requires_approval, permission_config,
                       created_at, updated_at, deleted_at
                FROM {schema}.permissions
                WHERE resource = $1 AND deleted_at IS NULL
                ORDER BY action
            """
            
            rows = await conn.fetch(query, resource)
            return [self._build_permission_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list permissions by resource {resource} from {schema}: {e}")
            raise DatabaseError(f"Failed to list permissions: {e}")
    
    async def list_dangerous(self, schema: str = "admin") -> List[Permission]:
        """List all dangerous permissions requiring extra security."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                SELECT id, code, description, resource, action, scope_level,
                       is_dangerous, requires_mfa, requires_approval, permission_config,
                       created_at, updated_at, deleted_at
                FROM {schema}.permissions
                WHERE is_dangerous = true AND deleted_at IS NULL
                ORDER BY resource, action
            """
            
            rows = await conn.fetch(query)
            return [self._build_permission_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list dangerous permissions from {schema}: {e}")
            raise DatabaseError(f"Failed to list dangerous permissions: {e}")
    
    async def create(self, permission: Permission, schema: str = "admin") -> Permission:
        """Create a new permission in specified schema."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                INSERT INTO {schema}.permissions (
                    code, description, resource, action, scope_level,
                    is_dangerous, requires_mfa, requires_approval, permission_config,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW()
                )
                RETURNING id, created_at, updated_at
            """
            
            row = await conn.fetchrow(
                query,
                permission.code.value,
                permission.description,
                permission.resource,
                permission.action,
                permission.scope_level.value,
                permission.is_dangerous,
                permission.requires_mfa,
                permission.requires_approval,
                permission.permission_config
            )
            
            # Return updated permission with ID and timestamps
            return Permission(
                id=row['id'],
                code=permission.code,
                description=permission.description,
                resource=permission.resource,
                action=permission.action,
                scope_level=permission.scope_level,
                is_dangerous=permission.is_dangerous,
                requires_mfa=permission.requires_mfa,
                requires_approval=permission.requires_approval,
                permission_config=permission.permission_config,
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                deleted_at=None
            )
            
        except asyncpg.UniqueViolationError:
            raise DatabaseError(f"Permission with code {permission.code.value} already exists")
        except Exception as e:
            logger.error(f"Failed to create permission {permission.code.value} in {schema}: {e}")
            raise DatabaseError(f"Failed to create permission: {e}")
    
    async def update(self, permission: Permission, schema: str = "admin") -> Permission:
        """Update an existing permission in specified schema."""
        if not permission.id:
            raise DatabaseError("Cannot update permission without ID")
        
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                UPDATE {schema}.permissions
                SET description = $2,
                    scope_level = $3,
                    is_dangerous = $4,
                    requires_mfa = $5,
                    requires_approval = $6,
                    permission_config = $7,
                    updated_at = NOW()
                WHERE id = $1 AND deleted_at IS NULL
                RETURNING updated_at
            """
            
            row = await conn.fetchrow(
                query,
                permission.id,
                permission.description,
                permission.scope_level.value,
                permission.is_dangerous,
                permission.requires_mfa,
                permission.requires_approval,
                permission.permission_config
            )
            
            if not row:
                raise DatabaseError(f"Permission with ID {permission.id} not found or already deleted")
            
            # Return updated permission
            return Permission(
                id=permission.id,
                code=permission.code,
                description=permission.description,
                resource=permission.resource,
                action=permission.action,
                scope_level=permission.scope_level,
                is_dangerous=permission.is_dangerous,
                requires_mfa=permission.requires_mfa,
                requires_approval=permission.requires_approval,
                permission_config=permission.permission_config,
                created_at=permission.created_at,
                updated_at=row['updated_at'],
                deleted_at=permission.deleted_at
            )
            
        except Exception as e:
            logger.error(f"Failed to update permission {permission.id} in {schema}: {e}")
            raise DatabaseError(f"Failed to update permission: {e}")
    
    async def delete(self, permission_id: int, schema: str = "admin") -> bool:
        """Soft delete a permission by setting deleted_at."""
        try:
            conn = await self._get_connection(schema)
            
            query = f"""
                UPDATE {schema}.permissions
                SET deleted_at = NOW(), updated_at = NOW()
                WHERE id = $1 AND deleted_at IS NULL
            """
            
            result = await conn.execute(query, permission_id)
            return result.split()[-1] == "1"  # Check if one row was affected
            
        except Exception as e:
            logger.error(f"Failed to delete permission {permission_id} from {schema}: {e}")
            raise DatabaseError(f"Failed to delete permission: {e}")
    
    async def search(
        self,
        query: str,
        schema: str = "admin",
        limit: int = 100,
        offset: int = 0
    ) -> List[Permission]:
        """Search permissions by description or code."""
        try:
            conn = await self._get_connection(schema)
            
            # Use full-text search on description and pattern matching on code
            search_query = f"""
                SELECT id, code, description, resource, action, scope_level,
                       is_dangerous, requires_mfa, requires_approval, permission_config,
                       created_at, updated_at, deleted_at
                FROM {schema}.permissions
                WHERE deleted_at IS NULL
                  AND (
                    code ILIKE $1
                    OR description ILIKE $1
                    OR resource ILIKE $1
                    OR action ILIKE $1
                  )
                ORDER BY 
                  CASE WHEN code ILIKE $1 THEN 1 ELSE 2 END,
                  code
                LIMIT $2 OFFSET $3
            """
            
            search_pattern = f"%{query}%"
            rows = await conn.fetch(search_query, search_pattern, limit, offset)
            return [self._build_permission_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to search permissions in {schema}: {e}")
            raise DatabaseError(f"Failed to search permissions: {e}")