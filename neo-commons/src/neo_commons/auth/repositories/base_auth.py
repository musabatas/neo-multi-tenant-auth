"""
Authentication repository for platform user management.
Handles database operations for authentication and user data.
"""
import json
from typing import Optional, Dict, Any, List
from uuid import UUID
from loguru import logger

from ...repositories.base import BaseRepository
from ...exceptions.base import NotFoundError
from ...utils.datetime import utc_now
from ...utils.uuid import generate_uuid_v7
from ...database.utils import process_database_record


class BaseAuthRepository(BaseRepository[Dict[str, Any]]):
    """
    Database access for authentication data with dynamic schema configuration.
    
    Handles:
    - Platform user management
    - User authentication data
    - Session tracking
    - Tenant access grants
    
    Uses neo-commons BaseRepository for consistent data access patterns.
    """
    
    def __init__(self, connection_provider, schema_name: str = "admin"):
        """
        Initialize repository with BaseRepository and configurable schema.
        
        Args:
            connection_provider: Database connection provider
            schema_name: Database schema to use (default: admin)
        """
        super().__init__(
            table_name="platform_users", 
            connection_provider=connection_provider,
            default_schema=schema_name
        )
        self.db = connection_provider
        self.schema_name = schema_name
    
    def _user_select_query(self) -> str:
        """Get the standard user select query with column mappings."""
        table_name = self.get_full_table_name()
        return f"""
            SELECT 
                u.id,
                u.email,
                u.username,
                u.first_name,
                u.last_name,
                u.display_name,
                u.external_auth_provider,
                u.external_user_id as external_user_id,
                u.is_active,
                u.is_superadmin,
                u.last_login_at as last_login,
                0 as login_count,
                0 as failed_login_count,
                NULL::timestamp as last_failed_login,
                false as mfa_enabled,
                NULL as mfa_secret_encrypted,
                false as email_verified,
                NULL::timestamp as email_verified_at,
                u.phone as phone_number,
                false as phone_verified,
                NULL::timestamp as phone_verified_at,
                u.avatar_url,
                u.timezone,
                u.locale as language,
                u.metadata,
                u.created_at,
                u.updated_at
            FROM {table_name} u
        """
    
    async def get_user_by_email(
        self,
        email: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get platform user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User data if found, None otherwise
        """
        query = self._user_select_query() + " WHERE LOWER(u.email) = LOWER($1)"
        
        db = await self.get_connection()
        result = await db.fetchrow(query, email)
        
        if result:
            return process_database_record(
                result,
                uuid_fields=['id'],
                jsonb_fields=['metadata']
            )
        
        return None
    
    async def get_user_by_username(
        self,
        username: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get platform user by username.
        
        Args:
            username: Username
            
        Returns:
            User data if found, None otherwise
        """
        query = self._user_select_query() + " WHERE LOWER(u.username) = LOWER($1)"
        
        db = await self.get_connection()
        result = await db.fetchrow(query, username)
        
        if result:
            return process_database_record(
                result,
                uuid_fields=['id'],
                jsonb_fields=['metadata']
            )
        
        return None
    
    async def get_user_by_external_id(
        self,
        provider: str,
        external_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get platform user by external auth provider ID.
        
        Args:
            provider: Auth provider (keycloak, auth0, etc.)
            external_id: Provider-specific user ID
            
        Returns:
            User data if found, None otherwise
        """
        query = self._user_select_query() + """
            WHERE u.external_auth_provider = $1
                AND u.external_user_id = $2
        """
        
        db = await self.get_connection()
        result = await db.fetchrow(query, provider, external_id)
        
        if result:
            return process_database_record(
                result,
                uuid_fields=['id'],
                jsonb_fields=['metadata']
            )
        
        return None
    
    async def get_user_by_id(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get platform user by ID.
        
        Args:
            user_id: User UUID
            
        Returns:
            User data if found
            
        Raises:
            NotFoundError: User not found
        """
        query = self._user_select_query() + " WHERE u.id = $1"
        
        db = await self.get_connection()
        result = await db.fetchrow(query, user_id)
        
        if not result:
            raise NotFoundError("User", user_id)
        
        return process_database_record(
            result,
            uuid_fields=['id'],
            jsonb_fields=['metadata']
        )
    
    async def create_or_update_user(
        self,
        email: str,
        username: str,
        external_auth_provider: str,
        external_user_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create or update a platform user.
        
        Args:
            email: Email address
            username: Username
            external_auth_provider: Auth provider
            external_user_id: Provider user ID
            first_name: First name
            last_name: Last name
            metadata: Additional metadata
            
        Returns:
            Created or updated user data
        """
        # Check if user exists
        existing_user = await self.get_user_by_external_id(
            external_auth_provider,
            external_user_id
        )
        
        if existing_user:
            # Update existing user
            table_name = self.get_full_table_name()
            query = f"""
                UPDATE {table_name}
                SET 
                    email = $1,
                    username = $2,
                    first_name = COALESCE($3, first_name),
                    last_name = COALESCE($4, last_name),
                    display_name = COALESCE($5, display_name),
                    metadata = COALESCE($6, metadata),
                    updated_at = $7
                WHERE id = $8
                RETURNING id
            """
            
            display_name = f"{first_name or ''} {last_name or ''}".strip() or username
            
            db = await self.get_connection()
            result = await db.fetchrow(
                query,
                email,
                username,
                first_name,
                last_name,
                display_name,
                json.dumps(metadata) if metadata else None,
                utc_now(),
                existing_user["id"]
            )
            
            # Reduce verbose logging for frequent user updates
            
            # Fetch the full user record
            return await self.get_user_by_id(str(result['id']))
            
        else:
            # Create new user
            table_name = self.get_full_table_name()
            query = f"""
                INSERT INTO {table_name} (
                    id,
                    email,
                    username,
                    first_name,
                    last_name,
                    display_name,
                    external_auth_provider,
                    external_user_id,
                    is_active,
                    is_superadmin,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
                )
                RETURNING id
            """
            
            user_id = generate_uuid_v7()
            display_name = f"{first_name or ''} {last_name or ''}".strip() or username
            now = utc_now()
            
            db = await self.get_connection()
            result = await db.fetchrow(
                query,
                user_id,
                email,
                username,
                first_name,
                last_name,
                display_name,
                external_auth_provider,
                external_user_id,
                True,  # is_active
                False,  # is_superadmin (default)
                json.dumps(metadata or {}),
                now,
                now
            )
            
            logger.info(f"Created new user {user_id} ({email})")
            
            # Fetch the full user record
            return await self.get_user_by_id(str(result['id']))
    
    async def update_last_login(
        self,
        user_id: str,
        increment_count: bool = True
    ) -> bool:
        """
        Update user's last login timestamp.
        
        Args:
            user_id: User UUID
            increment_count: Whether to increment login count (not used, kept for compatibility)
            
        Returns:
            True if updated successfully
        """
        table_name = self.get_full_table_name()
        query = f"""
            UPDATE {table_name}
            SET 
                last_login_at = $1,
                updated_at = $1
            WHERE id = $2
        """
        
        db = await self.get_connection()
        await db.execute(query, utc_now(), user_id)
        # Reduce verbose logging for frequent login updates
        return True
    
    async def update_failed_login(
        self,
        user_id: str
    ) -> int:
        """
        Update failed login attempt for a user.
        
        Since we don't have failed_login_count in the database,
        we'll just log the attempt and return 1.
        
        Args:
            user_id: User UUID
            
        Returns:
            Failed login count (always 1 for now)
        """
        logger.warning(f"Failed login attempt for user {user_id}")
        return 1
    
    async def get_user_tenant_access(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get tenant access grants for a user.
        
        Args:
            user_id: User UUID
            active_only: Only return active grants
            
        Returns:
            List of tenant access grants
        """
        query = f"""
            SELECT 
                tag.id,
                tag.user_id,
                tag.tenant_id,
                tag.access_level,
                tag.granted_by,
                tag.granted_at,
                tag.expires_at,
                tag.ip_restrictions,
                tag.granted_reason as notes,
                tag.is_active,
                t.name as tenant_name,
                t.slug as tenant_slug,
                t.external_auth_realm as tenant_realm,
                (t.deleted_at IS NULL) as tenant_is_active
            FROM {self.get_current_schema()}.tenant_access_grants tag
            JOIN {self.get_current_schema()}.tenants t ON t.id = tag.tenant_id
            WHERE tag.user_id = $1
        """
        
        if active_only:
            query += """
                AND tag.is_active = true
                AND t.deleted_at IS NULL
                AND (tag.expires_at IS NULL OR tag.expires_at > CURRENT_TIMESTAMP)
            """
        
        query += " ORDER BY tag.granted_at DESC"
        
        db = await self.get_connection()
        results = await db.fetch(query, user_id)
        
        from src.common.database.utils import process_database_record
        return [
            process_database_record(
                record,
                uuid_fields=['id', 'user_id', 'tenant_id', 'granted_by'],
                jsonb_fields=['ip_restrictions']
            )
            for record in results
        ]
    
    async def check_tenant_access(
        self,
        user_id: str,
        tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Check if user has access to a specific tenant.
        
        Args:
            user_id: User UUID
            tenant_id: Tenant UUID
            
        Returns:
            Access grant if exists and valid, None otherwise
        """
        query = f"""
            SELECT 
                tag.id,
                tag.user_id,
                tag.tenant_id,
                tag.access_level,
                tag.granted_by,
                tag.granted_at,
                tag.expires_at,
                tag.ip_restrictions,
                tag.granted_reason as notes,
                tag.is_active,
                t.name as tenant_name,
                t.slug as tenant_slug,
                t.external_auth_realm as tenant_realm,
                (t.deleted_at IS NULL) as tenant_is_active
            FROM {self.get_current_schema()}.tenant_access_grants tag
            JOIN {self.get_current_schema()}.tenants t ON t.id = tag.tenant_id
            WHERE tag.user_id = $1
                AND tag.tenant_id = $2
                AND tag.is_active = true
                AND t.deleted_at IS NULL
                AND (tag.expires_at IS NULL OR tag.expires_at > CURRENT_TIMESTAMP)
        """
        
        db = await self.get_connection()
        result = await db.fetchrow(query, user_id, tenant_id)
        
        if result:
            return process_database_record(
                result,
                uuid_fields=['id', 'user_id', 'tenant_id', 'granted_by'],
                jsonb_fields=['ip_restrictions']
            )
        
        return None
    
    async def is_user_active(self, user_id: str) -> bool:
        """
        Check if a user is active.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if user is active
        """
        table_name = self.get_full_table_name()
        query = f"SELECT is_active FROM {table_name} WHERE id = $1"
        db = await self.get_connection()
        
        # Debug logging
        logger.debug(f"Checking user active status: user_id={user_id}, table={table_name}")
        
        # First check if user exists at all
        exists_query = f"SELECT COUNT(*) FROM {table_name} WHERE id = $1"
        user_count = await db.fetchval(exists_query, user_id)
        logger.debug(f"User exists check: count={user_count}")
        
        if user_count == 0:
            logger.warning(f"User {user_id} not found in database")
            return False
        
        result = await db.fetchval(query, user_id)
        logger.debug(f"User active query result: {result} (type: {type(result)})")
        
        is_active = bool(result)
        logger.debug(f"User {user_id} active status: {is_active}")
        
        return is_active
    
    async def is_user_superadmin(self, user_id: str) -> bool:
        """
        Check if a user is a superadmin.
        
        Args:
            user_id: User UUID
            
        Returns:
            True if user is a superuser
        """
        table_name = self.get_full_table_name()
        query = f"SELECT is_superadmin FROM {table_name} WHERE id = $1"
        db = await self.get_connection()
        result = await db.fetchval(query, user_id)
        return bool(result)
    
    async def update_user_metadata_by_external_id(
        self,
        provider: str,
        external_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update user metadata by external ID.
        
        Args:
            provider: External auth provider
            external_id: External user ID
            metadata: Updated metadata
            
        Returns:
            True if user was updated
        """
        table_name = self.get_full_table_name()
        query = f"""
            UPDATE {table_name}
            SET 
                metadata = $1,
                updated_at = $2
            WHERE external_auth_provider = $3 
              AND external_user_id = $4
              AND deleted_at IS NULL
        """
        
        db = await self.get_connection()
        result = await db.execute(
            query,
            json.dumps(metadata) if metadata else None,
            utc_now(),
            provider,
            external_id
        )
        
        # Check if any row was actually updated
        rows_affected = int(result.split()[-1]) if result else 0
        
        if rows_affected > 0:
            logger.info(f"Updated metadata for user with external_id {external_id}")
            return True
        else:
            logger.warning(f"No user found with external_id {external_id} for provider {provider}")
            return False