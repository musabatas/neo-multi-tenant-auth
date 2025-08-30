"""Database user repository for authentication platform."""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone

from .....core.value_objects.identifiers import (
    UserId, TenantId, KeycloakUserId, PermissionCode, RoleCode
)
from .....utils.uuid import generate_uuid_v7
from ...core.value_objects import RealmIdentifier
from ...core.entities import UserContext
from ...core.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class DatabaseUserRepository:
    """Database user repository following maximum separation principle.
    
    Handles ONLY user database operations for authentication platform.
    Does not handle Keycloak operations, caching, or session management.
    """
    
    def __init__(self, database_service):
        """Initialize database user repository.
        
        Args:
            database_service: Database service for connection management
        """
        if not database_service:
            raise ValueError("Database service is required")
        self.database_service = database_service
    
    def _validate_schema_name(self, schema_name: str) -> str:
        """Validate schema name to prevent SQL injection.
        
        Args:
            schema_name: Schema name to validate
            
        Returns:
            Validated schema name
            
        Raises:
            ValueError: If schema name is invalid
        """
        # Allow admin schema and tenant schemas
        if schema_name == 'admin' or schema_name.startswith('tenant_'):
            return schema_name
        raise ValueError(f"Invalid schema name: {schema_name}")
    
    def _get_connection_name_for_schema(self, schema_name: str) -> str:
        """Get database connection name for schema.
        
        Args:
            schema_name: Database schema name
            
        Returns:
            Database connection name
        """
        if schema_name == 'admin':
            return 'admin'
        elif schema_name.startswith('tenant_'):
            return 'shared'
        else:
            raise ValueError(f"Cannot determine connection for schema: {schema_name}")
    
    async def get_user_by_external_id(
        self, 
        external_user_id: str, 
        schema_name: str = "admin"
    ) -> Optional[Dict[str, Any]]:
        """Get user by external (Keycloak) user ID.
        
        Args:
            external_user_id: External user identifier
            schema_name: Database schema to search in
            
        Returns:
            User record dictionary or None if not found
        """
        safe_schema = self._validate_schema_name(schema_name)
        connection_name = self._get_connection_name_for_schema(safe_schema)
        
        try:
            async with self.database_service.get_connection(connection_name) as conn:
                result = await conn.fetchrow(
                    f"""
                    SELECT 
                        id, email, username, external_user_id, external_auth_provider,
                        first_name, last_name, display_name, status, is_system_user,
                        created_at, updated_at, last_login_at, last_activity_at
                    FROM {safe_schema}.users 
                    WHERE external_user_id = $1
                    AND deleted_at IS NULL
                    """,
                    external_user_id
                )
                
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Failed to get user by external ID {external_user_id}: {e}")
            raise AuthenticationFailed(
                "Failed to retrieve user from database",
                reason="database_error",
                context={"external_user_id": external_user_id, "error": str(e)}
            )
    
    async def get_user_by_platform_id(
        self, 
        user_id: UserId, 
        schema_name: str = "admin"
    ) -> Optional[Dict[str, Any]]:
        """Get user by platform user ID.
        
        Args:
            user_id: Platform user identifier
            schema_name: Database schema to search in
            
        Returns:
            User record dictionary or None if not found
        """
        safe_schema = self._validate_schema_name(schema_name)
        connection_name = self._get_connection_name_for_schema(safe_schema)
        
        try:
            async with self.database_service.get_connection(connection_name) as conn:
                result = await conn.fetchrow(
                    f"""
                    SELECT 
                        id, email, username, external_user_id, external_auth_provider,
                        first_name, last_name, display_name, status, is_system_user,
                        created_at, updated_at, last_login_at, last_activity_at
                    FROM {safe_schema}.users 
                    WHERE id = $1
                    AND deleted_at IS NULL
                    """,
                    user_id.value
                )
                
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Failed to get user by platform ID {user_id.value}: {e}")
            raise AuthenticationFailed(
                "Failed to retrieve user from database",
                reason="database_error",
                context={"user_id": str(user_id.value), "error": str(e)}
            )
    
    async def sync_user_from_keycloak(
        self,
        external_user_id: str,
        user_data: Dict[str, Any],
        schema_name: str = "admin"
    ) -> UserId:
        """Sync user from Keycloak to database.
        
        Args:
            external_user_id: External user identifier
            user_data: User data from Keycloak
            schema_name: Database schema to sync to
            
        Returns:
            Platform user ID
        """
        safe_schema = self._validate_schema_name(schema_name)
        connection_name = self._get_connection_name_for_schema(safe_schema)
        
        try:
            async with self.database_service.get_connection(connection_name) as conn:
                # Check if user already exists
                existing_user = await self.get_user_by_external_id(external_user_id, safe_schema)
                
                if existing_user:
                    # Update existing user
                    await conn.execute(
                        f"""
                        UPDATE {safe_schema}.users SET
                            email = $2,
                            username = $3,
                            first_name = $4,
                            last_name = $5,
                            display_name = $6,
                            updated_at = NOW(),
                            last_activity_at = NOW()
                        WHERE external_user_id = $1
                        """,
                        external_user_id,
                        user_data.get('email'),
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        user_data.get('display_name')
                    )
                    
                    logger.info(f"Updated existing user: {external_user_id}")
                    return UserId(existing_user['id'])
                else:
                    # Create new user
                    new_user_id = generate_uuid_v7()
                    
                    await conn.execute(
                        f"""
                        INSERT INTO {safe_schema}.users (
                            id, email, username, external_user_id, external_auth_provider,
                            first_name, last_name, display_name, status,
                            created_at, updated_at, last_activity_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW(), NOW(), NOW())
                        """,
                        new_user_id,
                        user_data.get('email'),
                        user_data.get('username'),
                        external_user_id,
                        'keycloak',
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        user_data.get('display_name'),
                        'active'
                    )
                    
                    logger.info(f"Created new user: {external_user_id} -> {new_user_id}")
                    return UserId(new_user_id)
                    
        except Exception as e:
            logger.error(f"Failed to sync user from Keycloak {external_user_id}: {e}")
            raise AuthenticationFailed(
                "Failed to sync user to database",
                reason="database_sync_error",
                context={"external_user_id": external_user_id, "error": str(e)}
            )
    
    async def update_user_login_time(
        self,
        user_id: UserId,
        login_time: Optional[datetime] = None,
        schema_name: str = "admin"
    ) -> None:
        """Update user's last login time.
        
        Args:
            user_id: Platform user identifier
            login_time: Login timestamp (defaults to current time)
            schema_name: Database schema to update
        """
        safe_schema = self._validate_schema_name(schema_name)
        connection_name = self._get_connection_name_for_schema(safe_schema)
        login_timestamp = login_time or datetime.now(timezone.utc)
        
        try:
            async with self.database_service.get_connection(connection_name) as conn:
                await conn.execute(
                    f"""
                    UPDATE {safe_schema}.users SET
                        last_login_at = $2,
                        last_activity_at = $2,
                        updated_at = NOW()
                    WHERE id = $1
                    """,
                    user_id.value,
                    login_timestamp
                )
                
                logger.debug(f"Updated login time for user {user_id.value}")
                
        except Exception as e:
            logger.error(f"Failed to update login time for user {user_id.value}: {e}")
            # Don't raise exception for login time updates - it's not critical
    
    async def get_user_roles(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        schema_name: str = "admin"
    ) -> Set[RoleCode]:
        """Get user roles from database.
        
        Args:
            user_id: Platform user identifier
            tenant_id: Tenant identifier for scope filtering
            schema_name: Database schema to query
            
        Returns:
            Set of role codes
        """
        safe_schema = self._validate_schema_name(schema_name)
        connection_name = self._get_connection_name_for_schema(safe_schema)
        
        try:
            async with self.database_service.get_connection(connection_name) as conn:
                # Query for active user roles with optional tenant scoping
                if tenant_id:
                    results = await conn.fetch(
                        f"""
                        SELECT DISTINCT r.code
                        FROM {safe_schema}.user_roles ur
                        JOIN {safe_schema}.roles r ON ur.role_id = r.id
                        WHERE ur.user_id = $1
                        AND ur.is_active = true
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                        AND (ur.scope_type = 'global' OR (ur.scope_type = 'tenant' AND ur.scope_id = $2))
                        AND r.deleted_at IS NULL
                        """,
                        user_id.value,
                        tenant_id.value
                    )
                else:
                    results = await conn.fetch(
                        f"""
                        SELECT DISTINCT r.code
                        FROM {safe_schema}.user_roles ur
                        JOIN {safe_schema}.roles r ON ur.role_id = r.id
                        WHERE ur.user_id = $1
                        AND ur.is_active = true
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                        AND r.deleted_at IS NULL
                        """,
                        user_id.value
                    )
                
                return {RoleCode(row['code']) for row in results}
                
        except Exception as e:
            logger.error(f"Failed to get user roles for {user_id.value}: {e}")
            # Return empty set on error - don't fail authentication
            return set()
    
    async def get_user_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        schema_name: str = "admin"
    ) -> Set[PermissionCode]:
        """Get user permissions from database (both direct and role-based).
        
        Args:
            user_id: Platform user identifier
            tenant_id: Tenant identifier for scope filtering
            schema_name: Database schema to query
            
        Returns:
            Set of permission codes
        """
        safe_schema = self._validate_schema_name(schema_name)
        connection_name = self._get_connection_name_for_schema(safe_schema)
        
        try:
            async with self.database_service.get_connection(connection_name) as conn:
                # Get permissions from roles and direct assignments
                if tenant_id:
                    # Scoped query for tenant-specific permissions
                    results = await conn.fetch(
                        f"""
                        -- Role-based permissions
                        SELECT DISTINCT p.code
                        FROM {safe_schema}.user_roles ur
                        JOIN {safe_schema}.roles r ON ur.role_id = r.id
                        JOIN {safe_schema}.role_permissions rp ON r.id = rp.role_id
                        JOIN {safe_schema}.permissions p ON rp.permission_id = p.id
                        WHERE ur.user_id = $1
                        AND ur.is_active = true
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                        AND (ur.scope_type = 'global' OR (ur.scope_type = 'tenant' AND ur.scope_id = $2))
                        AND r.deleted_at IS NULL
                        AND p.deleted_at IS NULL
                        
                        UNION
                        
                        -- Direct permissions
                        SELECT DISTINCT p.code
                        FROM {safe_schema}.user_permissions up
                        JOIN {safe_schema}.permissions p ON up.permission_id = p.id
                        WHERE up.user_id = $1
                        AND up.is_granted = true
                        AND up.is_active = true
                        AND (up.expires_at IS NULL OR up.expires_at > NOW())
                        AND (up.scope_type = 'global' OR (up.scope_type = 'tenant' AND up.scope_id = $2))
                        AND p.deleted_at IS NULL
                        """,
                        user_id.value,
                        tenant_id.value
                    )
                else:
                    # Global query for all permissions
                    results = await conn.fetch(
                        f"""
                        -- Role-based permissions
                        SELECT DISTINCT p.code
                        FROM {safe_schema}.user_roles ur
                        JOIN {safe_schema}.roles r ON ur.role_id = r.id
                        JOIN {safe_schema}.role_permissions rp ON r.id = rp.role_id
                        JOIN {safe_schema}.permissions p ON rp.permission_id = p.id
                        WHERE ur.user_id = $1
                        AND ur.is_active = true
                        AND (ur.expires_at IS NULL OR ur.expires_at > NOW())
                        AND r.deleted_at IS NULL
                        AND p.deleted_at IS NULL
                        
                        UNION
                        
                        -- Direct permissions
                        SELECT DISTINCT p.code
                        FROM {safe_schema}.user_permissions up
                        JOIN {safe_schema}.permissions p ON up.permission_id = p.id
                        WHERE up.user_id = $1
                        AND up.is_granted = true
                        AND up.is_active = true
                        AND (up.expires_at IS NULL OR up.expires_at > NOW())
                        AND p.deleted_at IS NULL
                        """,
                        user_id.value
                    )
                
                return {PermissionCode(row['code']) for row in results}
                
        except Exception as e:
            logger.error(f"Failed to get user permissions for {user_id.value}: {e}")
            # Return empty set on error - don't fail authentication
            return set()
    
    async def get_user_auth_context_data(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        schema_name: str = "admin"
    ) -> Dict[str, Any]:
        """Get comprehensive user authentication context data.
        
        Args:
            user_id: Platform user identifier
            tenant_id: Tenant identifier for scope filtering
            schema_name: Database schema to query
            
        Returns:
            Dictionary containing user, roles, and permissions data
        """
        try:
            # Get user data, roles, and permissions in parallel
            user_data = await self.get_user_by_platform_id(user_id, schema_name)
            roles = await self.get_user_roles(user_id, tenant_id, schema_name)
            permissions = await self.get_user_permissions(user_id, tenant_id, schema_name)
            
            if not user_data:
                raise AuthenticationFailed(
                    "User not found in database",
                    reason="user_not_found",
                    context={"user_id": str(user_id.value)}
                )
            
            return {
                "user": user_data,
                "roles": {"codes": [role.value for role in roles]},
                "permissions": [{"code": perm.value} for perm in permissions],
                "tenant_id": tenant_id.value if tenant_id else None,
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get auth context data for user {user_id.value}: {e}")
            raise AuthenticationFailed(
                "Failed to retrieve user authentication context",
                reason="context_retrieval_error",
                context={"user_id": str(user_id.value), "error": str(e)}
            )