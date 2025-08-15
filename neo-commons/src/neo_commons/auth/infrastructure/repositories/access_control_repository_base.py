"""
Base access control repository with core functionality.

Provides common database operations and utilities for access control.
"""
from typing import Optional
import asyncpg
from loguru import logger

from ...domain.entities.access_control import AccessLevel


class AccessControlRepositoryBase:
    """
    Base class for access control repository operations.
    
    Provides shared utilities and common database operations.
    """

    def __init__(self, db_pool: asyncpg.Pool, tenant_schema: str = "tenant_template", admin_schema: str = "admin"):
        """
        Initialize access control repository with configurable schemas.
        
        Args:
            db_pool: AsyncPG connection pool
            tenant_schema: Schema name for tenant-scoped tables (default: tenant_template)
            admin_schema: Schema name for admin/platform tables (default: admin)
        """
        self._db_pool = db_pool
        self.tenant_schema = tenant_schema
        self.admin_schema = admin_schema

    def _get_access_check_query(self, tenant_scoped: bool) -> str:
        """Get SQL query for access level checking."""
        if tenant_scoped:
            return f"""
                SELECT EXISTS(
                    SELECT 1 FROM {self.tenant_schema}.access_control_entries ace
                    WHERE ace.user_id = $1 
                        AND ace.resource_type = $2 
                        AND ace.resource_id = $3
                        AND ace.tenant_id = $4
                        AND ace.access_level >= $5
                        AND ace.is_active = true
                        AND (ace.expires_at IS NULL OR ace.expires_at > NOW())
                )
            """
        else:
            return f"""
                SELECT EXISTS(
                    SELECT 1 FROM {self.admin_schema}.platform_access_control_entries ace
                    WHERE ace.user_id = $1 
                        AND ace.resource_type = $2 
                        AND ace.resource_id = $3
                        AND ace.access_level >= $4
                        AND ace.is_active = true
                        AND (ace.expires_at IS NULL OR ace.expires_at > NOW())
                )
            """

    def _get_create_ace_query(self, tenant_scoped: bool) -> str:
        """Get SQL query for creating access control entries."""
        if tenant_scoped:
            return f"""
                INSERT INTO {self.tenant_schema}.access_control_entries 
                (user_id, resource_type, resource_id, access_level, tenant_id, 
                 granted_by_user_id, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, created_at
            """
        else:
            return f"""
                INSERT INTO {self.admin_schema}.platform_access_control_entries 
                (user_id, resource_type, resource_id, access_level, 
                 granted_by_user_id, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, created_at
            """

    def _get_revoke_query(self, tenant_scoped: bool, specific_level: bool) -> str:
        """Get SQL query for revoking access."""
        if tenant_scoped:
            if specific_level:
                return f"""
                    UPDATE {self.tenant_schema}.access_control_entries 
                    SET is_active = false, revoked_at = NOW(), revoked_by_user_id = $6
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND resource_id = $3
                        AND access_level = $4
                        AND tenant_id = $5
                        AND is_active = true
                """
            else:
                return f"""
                    UPDATE {self.tenant_schema}.access_control_entries 
                    SET is_active = false, revoked_at = NOW(), revoked_by_user_id = $5
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND resource_id = $3
                        AND tenant_id = $4
                        AND is_active = true
                """
        else:
            if specific_level:
                return f"""
                    UPDATE {self.admin_schema}.platform_access_control_entries 
                    SET is_active = false, revoked_at = NOW(), revoked_by_user_id = $5
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND resource_id = $3
                        AND access_level = $4
                        AND is_active = true
                """
            else:
                return f"""
                    UPDATE {self.admin_schema}.platform_access_control_entries 
                    SET is_active = false, revoked_at = NOW(), revoked_by_user_id = $4
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND resource_id = $3
                        AND is_active = true
                """

    def _get_user_resources_query(
        self, 
        tenant_scoped: bool, 
        with_access_level: bool
    ) -> str:
        """Get SQL query for retrieving user resources."""
        if tenant_scoped:
            if with_access_level:
                return f"""
                    SELECT DISTINCT resource_id 
                    FROM {self.tenant_schema}.access_control_entries
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND access_level >= $3
                        AND tenant_id = $4
                        AND is_active = true
                        AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY resource_id
                """
            else:
                return f"""
                    SELECT DISTINCT resource_id 
                    FROM {self.tenant_schema}.access_control_entries
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND tenant_id = $3
                        AND is_active = true
                        AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY resource_id
                """
        else:
            if with_access_level:
                return f"""
                    SELECT DISTINCT resource_id 
                    FROM {self.admin_schema}.platform_access_control_entries
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND access_level >= $3
                        AND is_active = true
                        AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY resource_id
                """
            else:
                return f"""
                    SELECT DISTINCT resource_id 
                    FROM {self.admin_schema}.platform_access_control_entries
                    WHERE user_id = $1 
                        AND resource_type = $2 
                        AND is_active = true
                        AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY resource_id
                """

    def _log_access_check(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        tenant_id: Optional[str],
        result: bool
    ) -> None:
        """Log access check results."""
        logger.debug(
            f"Resource access check: {resource_type}:{resource_id} for user {user_id} = {result}",
            extra={
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "access_level": access_level.value,
                "tenant_id": tenant_id,
                "has_access": result
            }
        )

    def _log_ace_created(
        self,
        ace_id: str,
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        granted_by: str,
        tenant_id: Optional[str]
    ) -> None:
        """Log access control entry creation."""
        logger.info(
            f"Access control entry created: {resource_type}:{resource_id} for user {user_id}",
            extra={
                "ace_id": ace_id,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "access_level": access_level.value,
                "granted_by": granted_by,
                "tenant_id": tenant_id
            }
        )