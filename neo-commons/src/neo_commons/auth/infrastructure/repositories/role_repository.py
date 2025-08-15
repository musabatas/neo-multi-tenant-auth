"""
Role repository implementation using AsyncPG for high-performance database operations.

Handles role management, assignment, and hierarchy with direct SQL for optimal performance.
"""
from typing import List, Optional, Dict, Any
import asyncpg
from loguru import logger

from ...domain.entities.role import Role, RoleLevel, RoleAssignment
from ...domain.entities.permission import Permission, PermissionScope
from ...domain.protocols.repository_protocols import RoleRepositoryProtocol


class RoleRepository(RoleRepositoryProtocol):
    """
    AsyncPG implementation of role repository for sub-millisecond performance.
    
    Uses direct SQL queries with prepared statements for optimal performance.
    """

    def __init__(self, db_pool: asyncpg.Pool, tenant_schema: str = "tenant_template", admin_schema: str = "admin"):
        """
        Initialize role repository with configurable schemas.
        
        Args:
            db_pool: AsyncPG connection pool
            tenant_schema: Schema name for tenant-scoped tables (default: tenant_template)
            admin_schema: Schema name for admin/platform tables (default: admin)
        """
        self._db_pool = db_pool
        self.tenant_schema = tenant_schema
        self.admin_schema = admin_schema

    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None
    ) -> List[Role]:
        """Get all roles assigned to a user with their permissions."""
        async with self._db_pool.acquire() as conn:
            if tenant_id:
                # Tenant-scoped roles
                query = f"""
                    SELECT DISTINCT
                        r.id, r.code, r.name, r.description, r.role_level,
                        r.tenant_id, r.is_active, r.created_at,
                        p.id as perm_id, p.code as perm_code, p.resource, 
                        p.action, p.scope_level
                    FROM {self.tenant_schema}.roles r
                    INNER JOIN {self.tenant_schema}.user_roles ur ON r.id = ur.role_id
                    LEFT JOIN {self.tenant_schema}.role_permissions rp ON r.id = rp.role_id
                    LEFT JOIN {self.tenant_schema}.permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = $1 
                        AND ur.tenant_id = $2 
                        AND ur.is_active = true
                        AND ur.revoked_at IS NULL
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                        AND r.is_active = true
                    ORDER BY r.role_level DESC, r.code
                """
                rows = await conn.fetch(query, user_id, tenant_id)
            else:
                # Platform-level roles
                query = f"""
                    SELECT DISTINCT
                        r.id, r.code, r.name, r.description, r.role_level,
                        r.tenant_id, r.is_active, r.created_at,
                        p.id as perm_id, p.code as perm_code, p.resource,
                        p.action, p.scope_level
                    FROM {self.admin_schema}.platform_roles r
                    INNER JOIN {self.admin_schema}.platform_user_roles ur ON r.id = ur.role_id
                    LEFT JOIN {self.admin_schema}.platform_role_permissions rp ON r.id = rp.role_id
                    LEFT JOIN {self.admin_schema}.platform_permissions p ON rp.permission_id = p.id
                    WHERE ur.user_id = $1 
                        AND ur.is_active = true
                        AND ur.revoked_at IS NULL
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                        AND r.is_active = true
                    ORDER BY r.role_level DESC, r.code
                """
                rows = await conn.fetch(query, user_id)

        # Convert rows to Role objects
        roles_dict = {}
        for row in rows:
            role_id = row['id']
            
            if role_id not in roles_dict:
                roles_dict[role_id] = Role(
                    id=role_id,
                    code=row['code'],
                    name=row['name'],
                    description=row['description'],
                    role_level=RoleLevel(row['role_level']),
                    tenant_id=row['tenant_id'],
                    is_active=row['is_active'],
                    created_at=row['created_at'],
                    permissions=[]
                )
            
            # Add permission if exists
            if row['perm_id']:
                permission = Permission(
                    id=row['perm_id'],
                    code=row['perm_code'],
                    resource=row['resource'],
                    action=row['action'],
                    scope_level=PermissionScope(row['scope_level'])
                )
                roles_dict[role_id].permissions.append(permission)

        return list(roles_dict.values())

    async def assign_role(
        self,
        user_id: str,
        role_code: str,
        assigned_by_user_id: str,
        tenant_id: Optional[str] = None,
        expiry_date: Optional[str] = None
    ) -> RoleAssignment:
        """Assign a role to a user."""
        async with self._db_pool.acquire() as conn:
            async with conn.transaction():
                if tenant_id:
                    # Get role ID for tenant scope
                    role_query = """
                        SELECT id FROM {self.tenant_schema}.$1 
                        WHERE code = $1 AND tenant_id = $2 AND is_active = true
                    """
                    role_row = await conn.fetchrow(role_query, role_code, tenant_id)
                    
                    if not role_row:
                        raise ValueError(f"Role {role_code} not found in tenant {tenant_id}")
                    
                    # Insert assignment
                    assignment_query = """
                        INSERT INTO {self.tenant_schema}.$1 
                        (user_id, role_id, tenant_id, assigned_by_user_id, expires_at)
                        VALUES ($1, $2, $3, $4, $5)
                        RETURNING id, created_at
                    """
                    result = await conn.fetchrow(
                        assignment_query, 
                        user_id, role_row['id'], tenant_id, assigned_by_user_id, expiry_date
                    )
                else:
                    # Platform-level role assignment
                    role_query = """
                        SELECT id FROM {self.admin_schema}.$1 
                        WHERE code = $1 AND is_active = true
                    """
                    role_row = await conn.fetchrow(role_query, role_code)
                    
                    if not role_row:
                        raise ValueError(f"Platform role {role_code} not found")
                    
                    assignment_query = """
                        INSERT INTO {self.admin_schema}.$1 
                        (user_id, role_id, assigned_by_user_id, expires_at)
                        VALUES ($1, $2, $3, $4)
                        RETURNING id, created_at
                    """
                    result = await conn.fetchrow(
                        assignment_query, 
                        user_id, role_row['id'], assigned_by_user_id, expiry_date
                    )

        assignment = RoleAssignment(
            id=result['id'],
            user_id=user_id,
            role_id=role_row['id'],
            role_code=role_code,
            tenant_id=tenant_id,
            assigned_by_user_id=assigned_by_user_id,
            created_at=result['created_at'],
            expires_at=expiry_date
        )

        logger.info(
            f"Role {role_code} assigned to user {user_id}",
            extra={
                "user_id": user_id,
                "role_code": role_code,
                "assigned_by": assigned_by_user_id,
                "tenant_id": tenant_id,
                "assignment_id": assignment.id
            }
        )

        return assignment

    async def revoke_role(
        self,
        user_id: str,
        role_code: str,
        revoked_by_user_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Revoke a role from a user."""
        async with self._db_pool.acquire() as conn:
            if tenant_id:
                query = """
                    UPDATE {self.tenant_schema}.$1 
                    SET is_active = false, revoked_at = NOW(), revoked_by_user_id = $4
                    WHERE user_id = $1 
                        AND role_id = (
                            SELECT id FROM {self.tenant_schema}.$1 
                            WHERE code = $2 AND tenant_id = $3 AND is_active = true
                        )
                        AND tenant_id = $3
                        AND is_active = true
                """
                result = await conn.execute(query, user_id, role_code, tenant_id, revoked_by_user_id)
            else:
                query = """
                    UPDATE {self.admin_schema}.$1 
                    SET is_active = false, revoked_at = NOW(), revoked_by_user_id = $3
                    WHERE user_id = $1 
                        AND role_id = (
                            SELECT id FROM {self.admin_schema}.$1 
                            WHERE code = $2 AND is_active = true
                        )
                        AND is_active = true
                """
                result = await conn.execute(query, user_id, role_code, revoked_by_user_id)

        success = result == "UPDATE 1"
        
        if success:
            logger.info(
                f"Role {role_code} revoked from user {user_id}",
                extra={
                    "user_id": user_id,
                    "role_code": role_code,
                    "revoked_by": revoked_by_user_id,
                    "tenant_id": tenant_id
                }
            )

        return success

    async def get_role_by_code(
        self,
        role_code: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Role]:
        """Get role by code."""
        async with self._db_pool.acquire() as conn:
            if tenant_id:
                query = """
                    SELECT r.id, r.code, r.name, r.description, r.role_level,
                           r.tenant_id, r.is_active, r.created_at,
                           p.id as perm_id, p.code as perm_code, p.resource,
                           p.action, p.scope_level
                    FROM {self.tenant_schema}.$1 r
                    LEFT JOIN {self.tenant_schema}.$1 rp ON r.id = rp.role_id
                    LEFT JOIN {self.tenant_schema}.$1 p ON rp.permission_id = p.id
                    WHERE r.code = $1 AND r.tenant_id = $2 AND r.is_active = true
                """
                rows = await conn.fetch(query, role_code, tenant_id)
            else:
                query = """
                    SELECT r.id, r.code, r.name, r.description, r.role_level,
                           r.tenant_id, r.is_active, r.created_at,
                           p.id as perm_id, p.code as perm_code, p.resource,
                           p.action, p.scope_level
                    FROM {self.admin_schema}.$1 r
                    LEFT JOIN {self.admin_schema}.$1 rp ON r.id = rp.role_id
                    LEFT JOIN {self.admin_schema}.$1 p ON rp.permission_id = p.id
                    WHERE r.code = $1 AND r.is_active = true
                """
                rows = await conn.fetch(query, role_code)

        if not rows:
            return None

        # Build role with permissions
        first_row = rows[0]
        permissions = []
        
        for row in rows:
            if row['perm_id']:
                permission = Permission(
                    id=row['perm_id'],
                    code=row['perm_code'],
                    resource=row['resource'],
                    action=row['action'],
                    scope_level=PermissionScope(row['scope_level'])
                )
                permissions.append(permission)

        return Role(
            id=first_row['id'],
            code=first_row['code'],
            name=first_row['name'],
            description=first_row['description'],
            role_level=RoleLevel(first_row['role_level']),
            tenant_id=first_row['tenant_id'],
            permissions=permissions
        )

    async def get_role_hierarchy(
        self,
        role_code: str,
        tenant_id: Optional[str] = None
    ) -> List[Role]:
        """Get role hierarchy (role and all parent roles)."""
        # For now, return single role
        # This would be expanded to handle role inheritance if needed
        role = await self.get_role_by_code(role_code, tenant_id)
        return [role] if role else []