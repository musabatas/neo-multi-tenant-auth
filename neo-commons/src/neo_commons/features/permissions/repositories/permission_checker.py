"""Concrete PermissionChecker implementation using AsyncPG."""

import logging
from typing import List, Optional, Set, Dict, Any
from uuid import UUID

from ....core.value_objects import UserId, TenantId
from ..entities.protocols import PermissionChecker
from ..entities.role import Role
from ..entities.permission import PermissionCode

logger = logging.getLogger(__name__)


class AsyncPGPermissionChecker(PermissionChecker):
    """High-performance permission checker using AsyncPG with caching support."""
    
    def __init__(self, database_service, permission_cache=None):
        """Initialize permission checker with database service and optional cache."""
        self.database_service = database_service
        self.permission_cache = permission_cache
    
    def _validate_schema_name(self, schema_name: str) -> str:
        """Validate schema name to prevent SQL injection."""
        if schema_name == 'admin' or schema_name.startswith('tenant_'):
            return schema_name
        raise ValueError(f"Invalid schema name: {schema_name}")
    
    async def has_permission(
        self,
        user_id: UserId,
        permission_code: str,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has a specific permission in given scope."""
        try:
            # Determine schema based on tenant_id
            schema = "admin" if tenant_id is None else f"tenant_{tenant_id.value}"
            safe_schema = self._validate_schema_name(schema)
            
            # Check cache first if available
            if self.permission_cache:
                cached_permissions = await self.permission_cache.get_user_permissions(
                    user_id.value, 
                    tenant_id.value if tenant_id else None,
                    scope_id
                )
                if cached_permissions is not None:
                    return permission_code in cached_permissions
            
            # Query database for permission
            user_permissions = await self.get_user_permissions(
                user_id, tenant_id, scope_id
            )
            
            # Cache result if cache is available
            if self.permission_cache:
                await self.permission_cache.set_user_permissions(
                    user_id.value,
                    user_permissions,
                    tenant_id.value if tenant_id else None,
                    scope_id,
                    ttl=300  # 5 minutes
                )
            
            return permission_code in user_permissions
            
        except Exception as e:
            logger.error(f"Failed to check permission {permission_code} for user {user_id.value}: {e}")
            return False
    
    async def has_any_permission(
        self,
        user_id: UserId,
        permission_codes: List[str],
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has any of the specified permissions."""
        if not permission_codes:
            return False
            
        user_permissions = await self.get_user_permissions(user_id, tenant_id, scope_id)
        return any(code in user_permissions for code in permission_codes)
    
    async def has_all_permissions(
        self,
        user_id: UserId,
        permission_codes: List[str],
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has all of the specified permissions."""
        if not permission_codes:
            return True
            
        user_permissions = await self.get_user_permissions(user_id, tenant_id, scope_id)
        return all(code in user_permissions for code in permission_codes)
    
    async def get_user_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> Set[str]:
        """Get all permission codes for a user in given scope."""
        try:
            # Determine schema and connection
            schema = "admin" if tenant_id is None else f"tenant_{tenant_id.value}"
            safe_schema = self._validate_schema_name(schema)
            connection_name = "admin" if schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                # Build the comprehensive permission query
                query = f"""
                WITH user_role_permissions AS (
                    -- Permissions from roles
                    SELECT DISTINCT p.code 
                    FROM {safe_schema}.permissions p
                    JOIN {safe_schema}.role_permissions rp ON p.id = rp.permission_id
                    JOIN {safe_schema}.user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = $1 
                    AND ur.is_active = true
                    AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                    AND p.deleted_at IS NULL
                    AND ($2::varchar IS NULL OR ur.scope_type = $2)
                    AND ($3::uuid IS NULL OR ur.scope_id = $3 OR ur.scope_type = 'global')
                ),
                user_direct_permissions AS (
                    -- Direct permissions granted to user
                    SELECT DISTINCT p.code
                    FROM {safe_schema}.permissions p
                    JOIN {safe_schema}.user_permissions up ON p.id = up.permission_id
                    WHERE up.user_id = $1
                    AND up.is_active = true
                    AND up.is_granted = true
                    AND (up.expires_at IS NULL OR up.expires_at > NOW())
                    AND p.deleted_at IS NULL
                    AND ($2::varchar IS NULL OR up.scope_type = $2)
                    AND ($3::uuid IS NULL OR up.scope_id = $3 OR up.scope_type = 'global')
                )
                -- Combine both sources
                SELECT code FROM user_role_permissions
                UNION
                SELECT code FROM user_direct_permissions
                """
                
                # Determine scope parameters
                scope_type = None
                if scope_id:
                    scope_type = "tenant" if tenant_id else "team"
                
                rows = await conn.fetch(query, user_id.value, scope_type, scope_id)
                permissions = {row['code'] for row in rows}
                
                logger.debug(f"Found {len(permissions)} permissions for user {user_id.value} in {safe_schema}")
                return permissions
                
        except Exception as e:
            logger.error(f"Failed to get permissions for user {user_id.value}: {e}")
            return set()
    
    async def get_user_roles(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> List[Role]:
        """Get all roles assigned to a user in given scope."""
        try:
            # Determine schema and connection
            schema = "admin" if tenant_id is None else f"tenant_{tenant_id.value}"
            safe_schema = self._validate_schema_name(schema)
            connection_name = "admin" if schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                query = f"""
                SELECT r.*, ur.scope_type, ur.scope_id, ur.granted_at, ur.expires_at
                FROM {safe_schema}.roles r
                JOIN {safe_schema}.user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = $1
                AND ur.is_active = true
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                AND r.deleted_at IS NULL
                AND ($2::varchar IS NULL OR ur.scope_type = $2)
                AND ($3::uuid IS NULL OR ur.scope_id = $3 OR ur.scope_type = 'global')
                ORDER BY r.priority ASC, r.name ASC
                """
                
                # Determine scope parameters
                scope_type = None
                if scope_id:
                    scope_type = "tenant" if tenant_id else "team"
                
                rows = await conn.fetch(query, user_id.value, scope_type, scope_id)
                roles = []
                
                for row in rows:
                    # Convert database row to Role entity
                    from ....config.constants import RoleLevel
                    from ..entities.role import Role, RoleCode
                    
                    role = Role(
                        id=row['id'],
                        code=RoleCode(row['code']),
                        name=row['name'],
                        description=row.get('description'),
                        display_name=row.get('display_name'),
                        role_level=RoleLevel(row['role_level']),
                        is_system=row['is_system'],
                        is_default=row['is_default'],
                        requires_approval=row['requires_approval'],
                        scope_type=row['scope_type'],
                        priority=row['priority'],
                        max_assignees=row.get('max_assignees'),
                        auto_expire_days=row.get('auto_expire_days'),
                        role_config=row.get('role_config', {}),
                        metadata=row.get('metadata', {}),
                        populated_permissions=row.get('populated_permissions', {}),
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        deleted_at=row.get('deleted_at')
                    )
                    roles.append(role)
                
                logger.debug(f"Found {len(roles)} roles for user {user_id.value} in {safe_schema}")
                return roles
                
        except Exception as e:
            logger.error(f"Failed to get roles for user {user_id.value}: {e}")
            return []
    
    async def get_user_permissions_with_details(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get detailed permission information for a user including source (role/direct)."""
        try:
            # Determine schema and connection
            schema = "admin" if tenant_id is None else f"tenant_{tenant_id.value}"
            safe_schema = self._validate_schema_name(schema)
            connection_name = "admin" if schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                # Get permissions from roles with essential metadata
                role_perms_query = f"""
                SELECT DISTINCT p.code, p.resource, p.action, 
                       p.scope_level, p.is_dangerous, p.requires_mfa, p.requires_approval,
                       p.permission_config,
                       r.name as role_name, r.code as role_code, 'role' as source
                FROM {safe_schema}.permissions p
                JOIN {safe_schema}.role_permissions rp ON p.id = rp.permission_id
                JOIN {safe_schema}.roles r ON rp.role_id = r.id
                JOIN {safe_schema}.user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = $1 
                AND ur.is_active = true
                AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                AND p.deleted_at IS NULL
                AND r.deleted_at IS NULL
                """
                
                # Get direct permissions with essential metadata
                direct_perms_query = f"""
                SELECT DISTINCT p.code, p.resource, p.action,
                       p.scope_level, p.is_dangerous, p.requires_mfa, p.requires_approval,
                       p.permission_config, 'direct' as source
                FROM {safe_schema}.permissions p
                JOIN {safe_schema}.user_permissions up ON p.id = up.permission_id
                WHERE up.user_id = $1
                AND up.is_active = true
                AND up.is_granted = true
                AND (up.expires_at IS NULL OR up.expires_at > NOW())
                AND p.deleted_at IS NULL
                """
                
                role_rows = await conn.fetch(role_perms_query, user_id.value)
                direct_rows = await conn.fetch(direct_perms_query, user_id.value)
                
                permissions = {}
                
                # Process role permissions
                for row in role_rows:
                    perm_code = row['code']
                    if perm_code not in permissions:
                        permissions[perm_code] = {
                            'code': perm_code,
                            'resource': row['resource'],
                            'action': row['action'],
                            'scope_level': row['scope_level'],
                            'is_dangerous': row['is_dangerous'],
                            'requires_mfa': row['requires_mfa'],
                            'requires_approval': row['requires_approval'],
                            'permission_config': row['permission_config'] or {},
                            'sources': []
                        }
                    
                    permissions[perm_code]['sources'].append({
                        'type': 'role',
                        'role_name': row['role_name'],
                        'role_code': row['role_code']
                    })
                
                # Process direct permissions
                for row in direct_rows:
                    perm_code = row['code']
                    if perm_code not in permissions:
                        permissions[perm_code] = {
                            'code': perm_code,
                            'resource': row['resource'],
                            'action': row['action'],
                            'scope_level': row['scope_level'],
                            'is_dangerous': row['is_dangerous'],
                            'requires_mfa': row['requires_mfa'],
                            'requires_approval': row['requires_approval'],
                            'permission_config': row['permission_config'] or {},
                            'sources': []
                        }
                    
                    permissions[perm_code]['sources'].append({
                        'type': 'direct'
                    })
                
                return {
                    'user_id': user_id.value,
                    'schema': safe_schema,
                    'total_permissions': len(permissions),
                    'permissions': list(permissions.values())
                }
                
        except Exception as e:
            logger.error(f"Failed to get detailed permissions for user {user_id.value}: {e}")
            return {
                'user_id': user_id.value,
                'schema': schema,
                'total_permissions': 0,
                'permissions': [],
                'error': str(e)
            }