"""
Platform Users repository for database operations.
"""

from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from loguru import logger

from src.common.repositories.base import BaseRepository
from src.common.database.connection import get_database
from src.common.database.utils import process_database_record
from src.common.exceptions.base import NotFoundError, ConflictError
from src.common.utils.datetime import utc_now

from ..models.domain import (
    PlatformUser, PlatformRole, PlatformPermission,
    PlatformUserRole, PlatformUserPermission,
    TenantUserRole, TenantUserPermission,
    AuthProvider, PlatformRoleLevel, PermissionScopeLevel
)
from ..models.request import PlatformUserCreate, PlatformUserUpdate, PlatformUserFilter


class PlatformUserRepository(BaseRepository[PlatformUser]):
    """Repository for platform user data access."""
    
    def __init__(self):
        """Initialize the repository."""
        super().__init__(table_name="platform_users", schema="admin")
    
    async def get_by_id(self, user_id: str) -> PlatformUser:
        """Get a platform user by ID."""
        db = get_database()
        query = """
            SELECT * FROM admin.platform_users 
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        record = await db.fetchrow(query, UUID(user_id))
        if not record:
            raise NotFoundError(resource="PlatformUser", identifier=user_id)
        
        # Process database record
        processed_data = process_database_record(
            record,
            uuid_fields=['id'],
            jsonb_fields=['provider_metadata', 'notification_preferences', 'ui_preferences', 'metadata']
        )
        
        return PlatformUser(**processed_data)
    
    async def get_by_email(self, email: str) -> PlatformUser:
        """Get a platform user by email."""
        db = get_database()
        query = """
            SELECT * FROM admin.platform_users 
            WHERE email = $1 AND deleted_at IS NULL
        """
        
        record = await db.fetchrow(query, email.lower())
        if not record:
            raise NotFoundError(resource="PlatformUser", identifier=f"email:{email}")
        
        processed_data = process_database_record(
            record,
            uuid_fields=['id'],
            jsonb_fields=['provider_metadata', 'notification_preferences', 'ui_preferences', 'metadata']
        )
        
        return PlatformUser(**processed_data)
    
    async def get_by_username(self, username: str) -> PlatformUser:
        """Get a platform user by username."""
        db = get_database()
        query = """
            SELECT * FROM admin.platform_users 
            WHERE username = $1 AND deleted_at IS NULL
        """
        
        record = await db.fetchrow(query, username.lower())
        if not record:
            raise NotFoundError(resource="PlatformUser", identifier=f"username:{username}")
        
        processed_data = process_database_record(
            record,
            uuid_fields=['id'],
            jsonb_fields=['provider_metadata', 'notification_preferences', 'ui_preferences', 'metadata']
        )
        
        return PlatformUser(**processed_data)
    
    async def get_by_external_id(self, provider: AuthProvider, external_user_id: str) -> Optional[PlatformUser]:
        """Get a platform user by external provider credentials."""
        db = get_database()
        query = """
            SELECT * FROM admin.platform_users 
            WHERE external_auth_provider = $1 AND external_user_id = $2 AND deleted_at IS NULL
        """
        
        record = await db.fetchrow(query, provider.value, external_user_id)
        if not record:
            return None
        
        processed_data = process_database_record(
            record,
            uuid_fields=['id'],
            jsonb_fields=['provider_metadata', 'notification_preferences', 'ui_preferences', 'metadata']
        )
        
        return PlatformUser(**processed_data)
    
    async def list(
        self, 
        filters: Optional[PlatformUserFilter] = None, 
        limit: int = 20, 
        offset: int = 0
    ) -> Tuple[List[PlatformUser], int]:
        """List platform users with optional filtering."""
        db = get_database()
        
        # Build WHERE conditions
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_counter = 1
        
        if filters:
            if filters.search:
                where_conditions.append(f"""(
                    email ILIKE ${param_counter} OR 
                    username ILIKE ${param_counter} OR 
                    first_name ILIKE ${param_counter} OR 
                    last_name ILIKE ${param_counter} OR 
                    display_name ILIKE ${param_counter} OR
                    company ILIKE ${param_counter}
                )""")
                params.append(f"%{filters.search}%")
                param_counter += 1
            
            if filters.email:
                where_conditions.append(f"email = ${param_counter}")
                params.append(filters.email.lower())
                param_counter += 1
            
            if filters.username:
                where_conditions.append(f"username = ${param_counter}")
                params.append(filters.username.lower())
                param_counter += 1
            
            if filters.external_auth_provider:
                where_conditions.append(f"external_auth_provider = ${param_counter}")
                params.append(filters.external_auth_provider.value)
                param_counter += 1
            
            if filters.is_active is not None:
                where_conditions.append(f"is_active = ${param_counter}")
                params.append(filters.is_active)
                param_counter += 1
            
            if filters.is_superadmin is not None:
                where_conditions.append(f"is_superadmin = ${param_counter}")
                params.append(filters.is_superadmin)
                param_counter += 1
            
            if filters.company:
                where_conditions.append(f"company ILIKE ${param_counter}")
                params.append(f"%{filters.company}%")
                param_counter += 1
            
            if filters.department:
                where_conditions.append(f"${param_counter} = ANY(departments)")
                params.append(filters.department)
                param_counter += 1
            
            if filters.job_title:
                where_conditions.append(f"job_title ILIKE ${param_counter}")
                params.append(f"%{filters.job_title}%")
                param_counter += 1
            
            if filters.created_after:
                where_conditions.append(f"created_at >= ${param_counter}")
                params.append(filters.created_after)
                param_counter += 1
            
            if filters.created_before:
                where_conditions.append(f"created_at <= ${param_counter}")
                params.append(filters.created_before)
                param_counter += 1
            
            if filters.last_login_after:
                where_conditions.append(f"last_login_at >= ${param_counter}")
                params.append(filters.last_login_after)
                param_counter += 1
            
            if filters.last_login_before:
                where_conditions.append(f"last_login_at <= ${param_counter}")
                params.append(filters.last_login_before)
                param_counter += 1
        
        where_clause = " AND ".join(where_conditions)
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM admin.platform_users WHERE {where_clause}"
        total_count = await db.fetchval(count_query, *params)
        
        # Get paginated results
        list_query = f"""
            SELECT * FROM admin.platform_users 
            WHERE {where_clause}
            ORDER BY created_at DESC, email ASC
            LIMIT ${param_counter} OFFSET ${param_counter + 1}
        """
        params.extend([limit, offset])
        
        records = await db.fetch(list_query, *params)
        
        users = []
        for record in records:
            processed_data = process_database_record(
                record,
                uuid_fields=['id'],
                jsonb_fields=['provider_metadata', 'notification_preferences', 'ui_preferences', 'metadata']
            )
            users.append(PlatformUser(**processed_data))
        
        return users, total_count
    
    async def create(self, user_data: PlatformUserCreate) -> PlatformUser:
        """Create a new platform user."""
        db = get_database()
        
        # Check for conflicts
        conflicts = await self._check_conflicts(user_data.email, user_data.username, user_data.external_user_id, user_data.external_auth_provider)
        if conflicts:
            raise ConflictError(f"User conflicts detected: {', '.join(conflicts)}")
        
        # Prepare data
        now = utc_now()
        user_id = None  # Let database generate UUID
        
        query = """
            INSERT INTO admin.platform_users (
                email, username, external_id, first_name, last_name, display_name,
                avatar_url, phone, timezone, locale, external_auth_provider, external_user_id,
                is_active, is_superadmin, provider_metadata, notification_preferences,
                ui_preferences, job_title, departments, company, metadata, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23
            ) RETURNING id
        """
        
        user_id = await db.fetchval(
            query,
            user_data.email.lower(),
            user_data.username.lower(),
            user_data.external_id,
            user_data.first_name,
            user_data.last_name,
            user_data.display_name,
            user_data.avatar_url,
            user_data.phone,
            user_data.timezone,
            user_data.locale,
            user_data.external_auth_provider.value,
            user_data.external_user_id,
            user_data.is_active,
            user_data.is_superadmin,
            user_data.provider_metadata,
            user_data.notification_preferences,
            user_data.ui_preferences,
            user_data.job_title,
            user_data.departments,
            user_data.company,
            user_data.metadata,
            now,
            now
        )
        
        return await self.get_by_id(str(user_id))
    
    async def update(self, user_id: str, update_data: PlatformUserUpdate) -> PlatformUser:
        """Update a platform user."""
        db = get_database()
        
        # Build update query dynamically
        update_fields = []
        params = []
        param_counter = 1
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ${param_counter}")
                params.append(value)
                param_counter += 1
        
        if not update_fields:
            # No fields to update
            return await self.get_by_id(user_id)
        
        # Always update updated_at
        update_fields.append(f"updated_at = ${param_counter}")
        params.append(utc_now())
        param_counter += 1
        
        # Add user_id parameter
        params.append(UUID(user_id))
        
        query = f"""
            UPDATE admin.platform_users 
            SET {', '.join(update_fields)}
            WHERE id = ${param_counter} AND deleted_at IS NULL
            RETURNING id
        """
        
        result = await db.fetchval(query, *params)
        if not result:
            raise NotFoundError(resource="PlatformUser", identifier=user_id)
        
        return await self.get_by_id(user_id)
    
    async def delete(self, user_id: str) -> None:
        """Soft delete a platform user."""
        db = get_database()
        
        query = """
            UPDATE admin.platform_users 
            SET deleted_at = $1, updated_at = $1, is_active = false
            WHERE id = $2 AND deleted_at IS NULL
            RETURNING id
        """
        
        result = await db.fetchval(query, utc_now(), UUID(user_id))
        if not result:
            raise NotFoundError(resource="PlatformUser", identifier=user_id)
    
    async def update_last_login(self, user_id: str, login_time: Optional[datetime] = None) -> None:
        """Update user's last login timestamp."""
        db = get_database()
        
        if login_time is None:
            login_time = utc_now()
        
        query = """
            UPDATE admin.platform_users 
            SET last_login_at = $1, updated_at = $2
            WHERE id = $3 AND deleted_at IS NULL
        """
        
        await db.execute(query, login_time, utc_now(), UUID(user_id))
    
    async def get_user_platform_roles(self, user_id: str) -> List[PlatformUserRole]:
        """Get platform roles assigned to user."""
        db = get_database()
        
        query = """
            SELECT pur.*, pr.code, pr.name, pu.username as granted_by_username
            FROM admin.platform_user_roles pur
            JOIN admin.platform_roles pr ON pur.role_id = pr.id
            LEFT JOIN admin.platform_users pu ON pur.granted_by = pu.id
            WHERE pur.user_id = $1 AND pur.is_active = true
            ORDER BY pr.priority ASC, pur.granted_at ASC
        """
        
        records = await db.fetch(query, UUID(user_id))
        
        roles = []
        for record in records:
            # Convert record to dict and exclude extra fields
            record_dict = dict(record)
            # Remove extra fields that aren't part of the domain model
            record_dict.pop('code', None)
            record_dict.pop('name', None)
            record_dict.pop('granted_by_username', None)
            
            processed_data = process_database_record(
                record_dict,
                uuid_fields=['user_id', 'granted_by']
            )
            
            role = PlatformUserRole(**processed_data)
            role.granted_by_user = record.get('granted_by_username')
            roles.append(role)
        
        return roles
    
    async def get_user_tenant_roles(self, user_id: str, tenant_id: Optional[str] = None) -> List[TenantUserRole]:
        """Get tenant roles assigned to user."""
        db = get_database()
        
        base_query = """
            SELECT tur.*, pr.code, pr.name, pu.username as granted_by_username, t.name as tenant_name
            FROM admin.tenant_user_roles tur
            JOIN admin.platform_roles pr ON tur.role_id = pr.id
            JOIN admin.tenants t ON tur.tenant_id = t.id
            LEFT JOIN admin.platform_users pu ON tur.granted_by = pu.id
            WHERE tur.user_id = $1 AND tur.is_active = true
        """
        
        params = [UUID(user_id)]
        if tenant_id:
            base_query += " AND tur.tenant_id = $2"
            params.append(UUID(tenant_id))
        
        base_query += " ORDER BY t.name ASC, pr.priority ASC, tur.granted_at ASC"
        
        records = await db.fetch(base_query, *params)
        
        roles = []
        for record in records:
            # Convert record to dict and exclude extra fields
            record_dict = dict(record)
            # Remove extra fields that aren't part of the domain model
            record_dict.pop('code', None)
            record_dict.pop('name', None)
            record_dict.pop('granted_by_username', None)
            record_dict.pop('tenant_name', None)
            
            processed_data = process_database_record(
                record_dict,
                uuid_fields=['tenant_id', 'user_id', 'granted_by']
            )
            
            role = TenantUserRole(**processed_data)
            role.granted_by_user = record.get('granted_by_username')
            role.tenant_name = record.get('tenant_name')
            roles.append(role)
        
        return roles
    
    async def get_user_permissions(self, user_id: str, include_tenant_permissions: bool = True) -> List[str]:
        """Get all effective permissions for user (from roles and direct grants)."""
        db = get_database()
        
        # Get platform permissions from roles
        platform_role_perms_query = """
            SELECT DISTINCT pp.code
            FROM admin.platform_user_roles pur
            JOIN admin.role_permissions rp ON pur.role_id = rp.role_id
            JOIN admin.platform_permissions pp ON rp.permission_id = pp.id
            WHERE pur.user_id = $1 AND pur.is_active = true
              AND (pur.expires_at IS NULL OR pur.expires_at > NOW())
              AND pp.deleted_at IS NULL
        """
        
        platform_role_perms = await db.fetch(platform_role_perms_query, UUID(user_id))
        permissions = [record['code'] for record in platform_role_perms]
        
        # Get direct platform permissions
        platform_direct_perms_query = """
            SELECT DISTINCT pp.code
            FROM admin.platform_user_permissions pup
            JOIN admin.platform_permissions pp ON pup.permission_id = pp.id
            WHERE pup.user_id = $1 AND pup.is_active = true AND pup.is_granted = true
              AND (pup.expires_at IS NULL OR pup.expires_at > NOW())
              AND pp.deleted_at IS NULL
        """
        
        platform_direct_perms = await db.fetch(platform_direct_perms_query, UUID(user_id))
        permissions.extend([record['code'] for record in platform_direct_perms])
        
        if include_tenant_permissions:
            # Get tenant permissions from roles
            tenant_role_perms_query = """
                SELECT DISTINCT pp.code
                FROM admin.tenant_user_roles tur
                JOIN admin.role_permissions rp ON tur.role_id = rp.role_id
                JOIN admin.platform_permissions pp ON rp.permission_id = pp.id
                WHERE tur.user_id = $1 AND tur.is_active = true
                  AND (tur.expires_at IS NULL OR tur.expires_at > NOW())
                  AND pp.deleted_at IS NULL
            """
            
            tenant_role_perms = await db.fetch(tenant_role_perms_query, UUID(user_id))
            permissions.extend([record['code'] for record in tenant_role_perms])
            
            # Get direct tenant permissions
            tenant_direct_perms_query = """
                SELECT DISTINCT pp.code
                FROM admin.tenant_user_permissions tup
                JOIN admin.platform_permissions pp ON tup.permission_id = pp.id
                WHERE tup.user_id = $1 AND tup.is_active = true AND tup.is_granted = true
                  AND (tup.expires_at IS NULL OR tup.expires_at > NOW())
                  AND pp.deleted_at IS NULL
            """
            
            tenant_direct_perms = await db.fetch(tenant_direct_perms_query, UUID(user_id))
            permissions.extend([record['code'] for record in tenant_direct_perms])
        
        return list(set(permissions))  # Remove duplicates
    
    async def get_user_tenant_count(self, user_id: str) -> int:
        """Get count of tenants user has access to."""
        db = get_database()
        
        query = """
            SELECT COUNT(DISTINCT tenant_id)
            FROM admin.tenant_user_roles
            WHERE user_id = $1 AND is_active = true
        """
        
        return await db.fetchval(query, UUID(user_id)) or 0
    
    async def _check_conflicts(
        self, 
        email: str, 
        username: str, 
        external_user_id: str, 
        external_auth_provider: AuthProvider,
        exclude_user_id: Optional[str] = None
    ) -> List[str]:
        """Check for conflicting user data."""
        db = get_database()
        conflicts = []
        
        # Email conflict check
        email_query = "SELECT id FROM admin.platform_users WHERE email = $1 AND deleted_at IS NULL"
        params = [email.lower()]
        if exclude_user_id:
            email_query += " AND id != $2"
            params.append(UUID(exclude_user_id))
        
        email_exists = await db.fetchval(email_query, *params)
        if email_exists:
            conflicts.append("email")
        
        # Username conflict check
        username_query = "SELECT id FROM admin.platform_users WHERE username = $1 AND deleted_at IS NULL"
        params = [username.lower()]
        if exclude_user_id:
            username_query += " AND id != $2"
            params.append(UUID(exclude_user_id))
        
        username_exists = await db.fetchval(username_query, *params)
        if username_exists:
            conflicts.append("username")
        
        # External user ID conflict check
        external_query = """
            SELECT id FROM admin.platform_users 
            WHERE external_auth_provider = $1 AND external_user_id = $2 AND deleted_at IS NULL
        """
        params = [external_auth_provider.value, external_user_id]
        if exclude_user_id:
            external_query += " AND id != $3"
            params.append(UUID(exclude_user_id))
        
        external_exists = await db.fetchval(external_query, *params)
        if external_exists:
            conflicts.append("external_user_id")
        
        return conflicts