"""User repository for database operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from ....core.value_objects import UserId
from ....config.constants import UserStatus
from ....utils.uuid import generate_uuid_v7
from ..entities.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations with schema awareness."""
    
    def __init__(self, database_service):
        """Initialize user repository."""
        if not database_service:
            raise ValueError("Database service is required")
        self.database_service = database_service
    
    def _validate_schema_name(self, schema_name: str) -> str:
        """Validate schema name to prevent SQL injection."""
        if schema_name == 'admin' or schema_name.startswith('tenant_'):
            return schema_name
        raise ValueError(f"Invalid schema name: {schema_name}")
    
    async def sync_user_from_keycloak(
        self,
        external_user_id: str,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        schema_name: str = "admin"
    ) -> UserId:
        """Sync Keycloak user to database and return user ID."""
        safe_schema = self._validate_schema_name(schema_name)
        
        try:
            # Determine connection name based on schema
            connection_name = "admin" if safe_schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                # Check if user exists by external_user_id
                existing_user = await conn.fetchrow(
                    f"""
                    SELECT id FROM {safe_schema}.users 
                    WHERE external_user_id = $1
                    """,
                    external_user_id
                )
                
                if existing_user:
                    # Update existing user
                    await conn.execute(
                        f"""
                        UPDATE {safe_schema}.users 
                        SET username = $2, email = $3, first_name = $4, last_name = $5, 
                            updated_at = NOW(), last_activity_at = NOW()
                        WHERE external_user_id = $1
                        """,
                        external_user_id, username, email, first_name, last_name
                    )
                    logger.info(f"Updated existing user: {username} in {safe_schema}")
                    return UserId(str(existing_user['id']))
                else:
                    # Create new user
                    new_user_id = generate_uuid_v7()
                    
                    await conn.execute(
                        f"""
                        INSERT INTO {safe_schema}.users 
                        (id, external_user_id, username, email, first_name, last_name, 
                         external_auth_provider, status, created_at, updated_at, activated_at, last_activity_at)
                        VALUES ($1, $2, $3, $4, $5, $6, 'keycloak', 'active', 
                                NOW(), NOW(), NOW(), NOW())
                        """,
                        new_user_id, external_user_id, username, email, first_name, last_name
                    )
                    logger.info(f"Created new user: {username} with ID: {new_user_id} in {safe_schema}")
                    return UserId(str(new_user_id))
                    
        except Exception as e:
            logger.error(f"Failed to sync user {username} in {safe_schema}: {e}")
            # Return external_user_id as fallback (this matches current behavior)
            return UserId(external_user_id)
    
    async def get_user_by_id(self, user_id: UserId, schema_name: str = "admin") -> Optional[Dict[str, Any]]:
        """Get complete user information by ID from specified schema."""
        try:
            safe_schema = self._validate_schema_name(schema_name)
            connection_name = "admin" if safe_schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                user_data = await conn.fetchrow(
                    f"""
                    SELECT 
                        -- Core Identity
                        id, email, username,
                        
                        -- External Auth
                        external_user_id, external_auth_provider, external_auth_metadata,
                        
                        -- Profile Information  
                        first_name, last_name, display_name, avatar_url, phone, job_title,
                        
                        -- Localization
                        timezone, locale,
                        
                        -- Status
                        status,
                        
                        -- Organizational
                        departments, company, manager_id,
                        
                        -- Role and Access
                        default_role_level, is_system_user,
                        
                        -- Onboarding and Profile
                        is_onboarding_completed, profile_completion_percentage,
                        
                        -- Preferences
                        notification_preferences, ui_preferences, feature_flags,
                        
                        -- Tags and Custom Fields
                        tags, custom_fields, metadata,
                        
                        -- Activity Tracking
                        invited_at, activated_at, last_activity_at, last_login_at,
                        
                        -- Audit Fields
                        created_at, updated_at, deleted_at
                        
                    FROM {safe_schema}.users
                    WHERE id = $1 AND deleted_at IS NULL
                    """,
                    user_id.value
                )
                
                if user_data:
                    return dict(user_data)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user {user_id.value} from {safe_schema}: {e}")
            return None
    
    async def get_user_by_external_id(self, external_user_id: str, schema_name: str = "admin") -> Optional[Dict[str, Any]]:
        """Get complete user information by external user ID from specified schema."""
        try:
            safe_schema = self._validate_schema_name(schema_name)
            connection_name = "admin" if safe_schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                user_data = await conn.fetchrow(
                    f"""
                    SELECT 
                        -- Core Identity
                        id, email, username,
                        
                        -- External Auth
                        external_user_id, external_auth_provider, external_auth_metadata,
                        
                        -- Profile Information  
                        first_name, last_name, display_name, avatar_url, phone, job_title,
                        
                        -- Localization
                        timezone, locale,
                        
                        -- Status
                        status,
                        
                        -- Organizational
                        departments, company, manager_id,
                        
                        -- Role and Access
                        default_role_level, is_system_user,
                        
                        -- Onboarding and Profile
                        is_onboarding_completed, profile_completion_percentage,
                        
                        -- Preferences
                        notification_preferences, ui_preferences, feature_flags,
                        
                        -- Tags and Custom Fields
                        tags, custom_fields, metadata,
                        
                        -- Activity Tracking
                        invited_at, activated_at, last_activity_at, last_login_at,
                        
                        -- Audit Fields
                        created_at, updated_at, deleted_at
                        
                    FROM {safe_schema}.users
                    WHERE external_user_id = $1 AND deleted_at IS NULL
                    """,
                    external_user_id
                )
                
                if user_data:
                    return dict(user_data)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user by external ID {external_user_id} from {safe_schema}: {e}")
            return None
    
    async def get_by_id(self, user_id: UserId, schema_name: str = "admin") -> Optional[User]:
        """Get user by ID."""
        safe_schema = self._validate_schema_name(schema_name)
        
        try:
            connection_name = "admin" if safe_schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                user_row = await conn.fetchrow(
                    f"""
                    SELECT * FROM {safe_schema}.users 
                    WHERE id = $1 AND deleted_at IS NULL
                    """,
                    user_id.value
                )
                
                if user_row:
                    return self._row_to_user(user_row, safe_schema)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user {user_id.value} from {safe_schema}: {e}")
            return None
    
    async def get_by_external_id(self, external_user_id: str, schema_name: str = "admin") -> Optional[User]:
        """Get user by external user ID (Keycloak ID)."""
        safe_schema = self._validate_schema_name(schema_name)
        
        try:
            connection_name = "admin" if safe_schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                user_row = await conn.fetchrow(
                    f"""
                    SELECT * FROM {safe_schema}.users 
                    WHERE external_user_id = $1 AND deleted_at IS NULL
                    """,
                    external_user_id
                )
                
                if user_row:
                    return self._row_to_user(user_row, safe_schema)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user by external ID {external_user_id} from {safe_schema}: {e}")
            return None
    
    async def get_by_email(self, email: str, schema_name: str = "admin") -> Optional[User]:
        """Get user by email."""
        safe_schema = self._validate_schema_name(schema_name)
        
        try:
            connection_name = "admin" if safe_schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                user_row = await conn.fetchrow(
                    f"""
                    SELECT * FROM {safe_schema}.users 
                    WHERE email = $1 AND deleted_at IS NULL
                    """,
                    email
                )
                
                if user_row:
                    return self._row_to_user(user_row, safe_schema)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get user by email {email} from {safe_schema}: {e}")
            return None
    
    async def update_last_login(self, user_id: UserId, schema_name: str = "admin") -> None:
        """Update user's last login timestamp."""
        safe_schema = self._validate_schema_name(schema_name)
        
        try:
            connection_name = "admin" if safe_schema == "admin" else "shared"
            
            async with self.database_service.get_connection(connection_name) as conn:
                await conn.execute(
                    f"""
                    UPDATE {safe_schema}.users 
                    SET last_login_at = NOW(), last_activity_at = NOW(), updated_at = NOW()
                    WHERE id = $1
                    """,
                    user_id.value
                )
                logger.debug(f"Updated last login for user {user_id.value} in {safe_schema}")
                
        except Exception as e:
            logger.error(f"Failed to update last login for user {user_id.value} in {safe_schema}: {e}")
    
    def _row_to_user(self, row: dict, schema_name: str) -> User:
        """Convert database row to User entity."""
        from ....core.value_objects import TenantId, OrganizationId
        from ....config.constants import AuthProvider, UserStatus
        
        # Extract tenant_id from schema name for tenant users
        tenant_id = None
        if schema_name.startswith("tenant_"):
            tenant_id_str = schema_name.replace("tenant_", "")
            tenant_id = TenantId(tenant_id_str)
        
        return User(
            id=UserId(str(row['id'])),
            email=row['email'],
            external_user_id=row['external_user_id'],
            username=row.get('username'),
            external_auth_provider=AuthProvider(row.get('external_auth_provider', 'keycloak')),
            external_auth_metadata=row.get('external_auth_metadata', {}),
            first_name=row.get('first_name'),
            last_name=row.get('last_name'),
            display_name=row.get('display_name'),
            avatar_url=row.get('avatar_url'),
            phone=row.get('phone'),
            job_title=row.get('job_title'),
            timezone=row.get('timezone', 'UTC'),
            locale=row.get('locale', 'en-US'),
            status=UserStatus(row.get('status', 'active')),
            departments=row.get('departments', []),
            company=row.get('company'),
            manager_id=UserId(str(row['manager_id'])) if row.get('manager_id') else None,
            default_role_level=row.get('default_role_level', 'member'),
            is_system_user=row.get('is_system_user', False),
            is_onboarding_completed=row.get('is_onboarding_completed', False),
            profile_completion_percentage=row.get('profile_completion_percentage', 0),
            notification_preferences=row.get('notification_preferences', {}),
            ui_preferences=row.get('ui_preferences', {}),
            feature_flags=row.get('feature_flags', {}),
            tags=row.get('tags', []),
            custom_fields=row.get('custom_fields', {}),
            metadata=row.get('metadata', {}),
            invited_at=row.get('invited_at'),
            activated_at=row.get('activated_at'),
            last_activity_at=row.get('last_activity_at'),
            last_login_at=row.get('last_login_at'),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            deleted_at=row.get('deleted_at'),
            schema_name=schema_name,
            tenant_id=tenant_id,
            permissions=set(),  # Will be loaded separately by permission service
            roles=set()  # Will be loaded separately by permission service
        )