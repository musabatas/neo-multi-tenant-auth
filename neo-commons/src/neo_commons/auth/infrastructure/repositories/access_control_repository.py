"""
Access control repository implementation using AsyncPG for resource-level permissions.

Handles fine-grained access control entries and resource permissions with high performance.
"""
from typing import List, Optional, Dict, Any
import asyncpg
from loguru import logger

from ...domain.entities.access_control import AccessControlEntry, AccessLevel
from ...domain.protocols.repository_protocols import AccessControlRepositoryProtocol
from .access_control_repository_base import AccessControlRepositoryBase


class AccessControlRepository(AccessControlRepositoryBase, AccessControlRepositoryProtocol):
    """
    AsyncPG implementation of access control repository for sub-millisecond performance.
    
    Manages resource-level access control with direct SQL for optimal performance.
    """

    async def check_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific access level to a resource."""
        async with self._db_pool.acquire() as conn:
            query = self._get_access_check_query(tenant_scoped=tenant_id is not None)
            
            if tenant_id:
                result = await conn.fetchval(
                    query, user_id, resource_type, resource_id, tenant_id, access_level.value
                )
            else:
                result = await conn.fetchval(
                    query, user_id, resource_type, resource_id, access_level.value
                )

        self._log_access_check(user_id, resource_type, resource_id, access_level, tenant_id, result)
        return result

    async def create_access_control_entry(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        granted_by_user_id: str,
        tenant_id: Optional[str] = None,
        expiry_date: Optional[str] = None
    ) -> AccessControlEntry:
        """Create a new access control entry."""
        async with self._db_pool.acquire() as conn:
            async with conn.transaction():
                query = self._get_create_ace_query(tenant_scoped=tenant_id is not None)
                
                if tenant_id:
                    result = await conn.fetchrow(
                        query, user_id, resource_type, resource_id, access_level.value,
                        tenant_id, granted_by_user_id, expiry_date
                    )
                else:
                    result = await conn.fetchrow(
                        query, user_id, resource_type, resource_id, access_level.value,
                        granted_by_user_id, expiry_date
                    )

        ace = AccessControlEntry(
            id=result['id'],
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            access_level=access_level,
            tenant_id=tenant_id,
            granted_by_user_id=granted_by_user_id,
            created_at=result['created_at'],
            expires_at=expiry_date
        )

        self._log_ace_created(
            ace.id, user_id, resource_type, resource_id, 
            access_level, granted_by_user_id, tenant_id
        )
        return ace

    async def revoke_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: Optional[AccessLevel],
        revoked_by_user_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Revoke user access to a resource."""
        async with self._db_pool.acquire() as conn:
            query = self._get_revoke_query(
                tenant_scoped=tenant_id is not None,
                specific_level=access_level is not None
            )
            
            # Build parameters based on query type
            if tenant_id:
                if access_level:
                    params = [user_id, resource_type, resource_id, access_level.value, tenant_id, revoked_by_user_id]
                else:
                    params = [user_id, resource_type, resource_id, tenant_id, revoked_by_user_id]
            else:
                if access_level:
                    params = [user_id, resource_type, resource_id, access_level.value, revoked_by_user_id]
                else:
                    params = [user_id, resource_type, resource_id, revoked_by_user_id]
            
            result = await conn.execute(query, *params)

        success = "UPDATE" in result and result != "UPDATE 0"
        
        if success:
            logger.info(
                f"Access revoked: {resource_type}:{resource_id} from user {user_id}",
                extra={
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "access_level": access_level.value if access_level else "ALL",
                    "revoked_by": revoked_by_user_id,
                    "tenant_id": tenant_id
                }
            )

        return success

    async def get_user_resources(
        self,
        user_id: str,
        resource_type: str,
        access_level: Optional[AccessLevel] = None,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get all resources a user has access to."""
        async with self._db_pool.acquire() as conn:
            query = self._get_user_resources_query(
                tenant_scoped=tenant_id is not None,
                with_access_level=access_level is not None
            )
            
            if tenant_id:
                if access_level:
                    rows = await conn.fetch(query, user_id, resource_type, access_level.value, tenant_id)
                else:
                    rows = await conn.fetch(query, user_id, resource_type, tenant_id)
            else:
                if access_level:
                    rows = await conn.fetch(query, user_id, resource_type, access_level.value)
                else:
                    rows = await conn.fetch(query, user_id, resource_type)

        resources = [row['resource_id'] for row in rows]
        
        logger.debug(
            f"Retrieved {len(resources)} {resource_type} resources for user {user_id}",
            extra={
                "user_id": user_id,
                "resource_type": resource_type,
                "access_level": access_level.value if access_level else "ANY",
                "tenant_id": tenant_id,
                "resource_count": len(resources)
            }
        )

        return resources

    async def get_resource_users(
        self,
        resource_type: str,
        resource_id: str,
        access_level: Optional[AccessLevel] = None,
        tenant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all users who have access to a resource."""
        async with self._db_pool.acquire() as conn:
            if tenant_id:
                base_query = f"""
                    SELECT ace.user_id, ace.access_level, ace.created_at, ace.expires_at,
                           u.username, u.email
                    FROM {self.tenant_schema}.access_control_entries ace
                    LEFT JOIN {self.tenant_schema}.users u ON ace.user_id = u.id
                    WHERE ace.resource_type = $1 
                        AND ace.resource_id = $2
                        AND ace.tenant_id = $3
                        AND ace.is_active = true
                        AND (ace.expires_at IS NULL OR ace.expires_at > NOW())
                """
                if access_level:
                    query = base_query + " AND ace.access_level = $4 ORDER BY ace.created_at DESC"
                    rows = await conn.fetch(query, resource_type, resource_id, tenant_id, access_level.value)
                else:
                    query = base_query + " ORDER BY ace.access_level DESC, ace.created_at DESC"
                    rows = await conn.fetch(query, resource_type, resource_id, tenant_id)
            else:
                base_query = f"""
                    SELECT ace.user_id, ace.access_level, ace.created_at, ace.expires_at,
                           u.username, u.email
                    FROM {self.admin_schema}.platform_access_control_entries ace
                    LEFT JOIN {self.admin_schema}.platform_users u ON ace.user_id = u.id
                    WHERE ace.resource_type = $1 
                        AND ace.resource_id = $2
                        AND ace.is_active = true
                        AND (ace.expires_at IS NULL OR ace.expires_at > NOW())
                """
                if access_level:
                    query = base_query + " AND ace.access_level = $3 ORDER BY ace.created_at DESC"
                    rows = await conn.fetch(query, resource_type, resource_id, access_level.value)
                else:
                    query = base_query + " ORDER BY ace.access_level DESC, ace.created_at DESC"
                    rows = await conn.fetch(query, resource_type, resource_id)

        users = []
        for row in rows:
            users.append({
                "user_id": row['user_id'],
                "username": row['username'],
                "email": row['email'],
                "access_level": AccessLevel(row['access_level']),
                "granted_at": row['created_at'],
                "expires_at": row['expires_at']
            })

        return users

    async def transfer_ownership(
        self,
        resource_type: str,
        resource_id: str,
        from_user_id: str,
        to_user_id: str,
        transferred_by_user_id: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Transfer ownership of a resource."""
        async with self._db_pool.acquire() as conn:
            async with conn.transaction():
                # Revoke owner access from old owner
                await self.revoke_resource_access(
                    from_user_id, resource_type, resource_id, 
                    AccessLevel.OWNER, transferred_by_user_id, tenant_id
                )
                
                # Grant owner access to new owner
                await self.create_access_control_entry(
                    to_user_id, resource_type, resource_id,
                    AccessLevel.OWNER, transferred_by_user_id, tenant_id
                )

        logger.info(
            f"Ownership transferred: {resource_type}:{resource_id} from {from_user_id} to {to_user_id}",
            extra={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
                "transferred_by": transferred_by_user_id,
                "tenant_id": tenant_id
            }
        )

        return True

    def __init__(self, db_pool: asyncpg.Pool, tenant_schema: str = "tenant_template", admin_schema: str = "admin"):
        """
        Initialize access control repository with configurable schemas.
        
        Args:
            db_pool: AsyncPG connection pool
            tenant_schema: Schema name for tenant-scoped tables (default: tenant_template)
            admin_schema: Schema name for admin/platform tables (default: admin)
        """
        super().__init__(db_pool, tenant_schema, admin_schema)
