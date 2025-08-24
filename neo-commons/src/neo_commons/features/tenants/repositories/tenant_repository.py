"""Tenant repository implementation using existing database infrastructure.

This implementation leverages the existing database service from neo-commons
without duplicating connection management or query logic.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ....core.value_objects import TenantId, OrganizationId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, DatabaseError
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.tenant import Tenant
from ..entities.protocols import TenantRepository


logger = logging.getLogger(__name__)


class TenantDatabaseRepository:
    """Database repository for tenant operations.
    
    Uses existing database infrastructure without duplication.
    Accepts any database connection via dependency injection.
    """
    
    def __init__(self, database_repository: DatabaseRepository, schema: str = "admin"):
        """Initialize with existing database repository.
        
        Args:
            database_repository: Database repository from neo-commons
            schema: Database schema name (default: admin)
        """
        self._db = database_repository
        self._schema = schema
        self._table = f"{schema}.tenants"
    
    async def save(self, tenant: Tenant) -> Tenant:
        """Save tenant to database."""
        try:
            # Check if tenant already exists
            existing = await self.find_by_id(tenant.id)
            if existing:
                raise EntityAlreadyExistsError(f"Tenant {tenant.id} already exists")
            
            query = f"""
                INSERT INTO {self._table} (
                    id, organization_id, slug, name, description, schema_name, database_name,
                    custom_domain, deployment_type, environment, region_id, database_connection_id,
                    external_auth_provider, external_auth_realm, external_user_id, external_auth_metadata,
                    allow_impersonations, status, internal_notes, features_enabled, feature_overrides,
                    provisioned_at, activated_at, suspended_at, last_activity_at, metadata,
                    created_at, updated_at, deleted_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
                    $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29
                )
                RETURNING *
            """
            
            params = [
                str(tenant.id.value), str(tenant.organization_id.value), tenant.slug, tenant.name,
                tenant.description, tenant.schema_name, tenant.database_name, tenant.custom_domain,
                tenant.deployment_type.value, tenant.environment, tenant.region_id, tenant.database_connection_id,
                tenant.external_auth_provider, tenant.external_auth_realm, tenant.external_user_id,
                tenant.external_auth_metadata, tenant.allow_impersonations, tenant.status.value,
                tenant.internal_notes, tenant.features_enabled, tenant.feature_overrides,
                tenant.provisioned_at, tenant.activated_at, tenant.suspended_at, tenant.last_activity_at,
                tenant.metadata, tenant.created_at, tenant.updated_at, tenant.deleted_at
            ]
            
            result = await self._db.execute_query(query, params)
            if result:
                logger.info(f"Created tenant {tenant.id}")
                return tenant
            
            raise DatabaseError("Failed to create tenant")
            
        except Exception as e:
            logger.error(f"Failed to save tenant {tenant.id}: {e}")
            raise DatabaseError(f"Failed to save tenant: {e}")
    
    async def find_by_id(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Find tenant by ID."""
        try:
            query = f"SELECT * FROM {self._table} WHERE id = $1 AND deleted_at IS NULL"
            result = await self._db.fetch_one(query, [str(tenant_id.value)])
            
            if result:
                return self._map_row_to_tenant(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find tenant {tenant_id}: {e}")
            raise DatabaseError(f"Failed to find tenant: {e}")
    
    async def find_by_slug(self, slug: str) -> Optional[Tenant]:
        """Find tenant by slug."""
        try:
            query = f"SELECT * FROM {self._table} WHERE slug = $1 AND deleted_at IS NULL"
            result = await self._db.fetch_one(query, [slug])
            
            if result:
                return self._map_row_to_tenant(result)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to find tenant by slug {slug}: {e}")
            raise DatabaseError(f"Failed to find tenant by slug: {e}")
    
    async def find_by_organization(self, organization_id: OrganizationId) -> List[Tenant]:
        """Find all tenants for an organization."""
        try:
            query = f"""
                SELECT * FROM {self._table} 
                WHERE organization_id = $1 AND deleted_at IS NULL
                ORDER BY created_at DESC
            """
            results = await self._db.fetch_all(query, [str(organization_id.value)])
            
            return [self._map_row_to_tenant(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to find tenants for organization {organization_id}: {e}")
            raise DatabaseError(f"Failed to find tenants for organization: {e}")
    
    async def find_active(self, limit: Optional[int] = None) -> List[Tenant]:
        """Find active tenants."""
        try:
            query = f"""
                SELECT * FROM {self._table}
                WHERE status = 'active' AND deleted_at IS NULL
                ORDER BY last_activity_at DESC NULLS LAST, created_at DESC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            results = await self._db.fetch_all(query)
            return [self._map_row_to_tenant(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to find active tenants: {e}")
            raise DatabaseError(f"Failed to find active tenants: {e}")
    
    async def update(self, tenant: Tenant) -> Tenant:
        """Update tenant."""
        try:
            # Update timestamp
            tenant.updated_at = datetime.now(tenant.updated_at.tzinfo)
            
            query = f"""
                UPDATE {self._table} SET
                    organization_id = $2, slug = $3, name = $4, description = $5,
                    schema_name = $6, database_name = $7, custom_domain = $8,
                    deployment_type = $9, environment = $10, region_id = $11,
                    database_connection_id = $12, external_auth_provider = $13,
                    external_auth_realm = $14, external_user_id = $15,
                    external_auth_metadata = $16, allow_impersonations = $17,
                    status = $18, internal_notes = $19, features_enabled = $20,
                    feature_overrides = $21, provisioned_at = $22, activated_at = $23,
                    suspended_at = $24, last_activity_at = $25, metadata = $26,
                    updated_at = $27, deleted_at = $28
                WHERE id = $1 AND deleted_at IS NULL
                RETURNING *
            """
            
            params = [
                str(tenant.id.value), str(tenant.organization_id.value), tenant.slug, tenant.name,
                tenant.description, tenant.schema_name, tenant.database_name, tenant.custom_domain,
                tenant.deployment_type.value, tenant.environment, tenant.region_id,
                tenant.database_connection_id, tenant.external_auth_provider, tenant.external_auth_realm,
                tenant.external_user_id, tenant.external_auth_metadata, tenant.allow_impersonations,
                tenant.status.value, tenant.internal_notes, tenant.features_enabled,
                tenant.feature_overrides, tenant.provisioned_at, tenant.activated_at,
                tenant.suspended_at, tenant.last_activity_at, tenant.metadata,
                tenant.updated_at, tenant.deleted_at
            ]
            
            result = await self._db.execute_query(query, params)
            if result:
                logger.info(f"Updated tenant {tenant.id}")
                return tenant
            
            raise EntityNotFoundError(f"Tenant {tenant.id} not found")
            
        except Exception as e:
            logger.error(f"Failed to update tenant {tenant.id}: {e}")
            raise DatabaseError(f"Failed to update tenant: {e}")
    
    async def delete(self, tenant_id: TenantId) -> bool:
        """Hard delete tenant."""
        try:
            query = f"DELETE FROM {self._table} WHERE id = $1"
            result = await self._db.execute_query(query, [str(tenant_id.value)])
            
            if result:
                logger.info(f"Deleted tenant {tenant_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise DatabaseError(f"Failed to delete tenant: {e}")
    
    async def exists(self, tenant_id: TenantId) -> bool:
        """Check if tenant exists."""
        try:
            query = f"SELECT 1 FROM {self._table} WHERE id = $1 AND deleted_at IS NULL"
            result = await self._db.fetch_one(query, [str(tenant_id.value)])
            return result is not None
            
        except Exception as e:
            logger.error(f"Failed to check tenant existence {tenant_id}: {e}")
            raise DatabaseError(f"Failed to check tenant existence: {e}")
    
    def _map_row_to_tenant(self, row: Dict[str, Any]) -> Tenant:
        """Map database row to Tenant entity."""
        from ....config.constants import TenantStatus, DeploymentType
        
        return Tenant(
            id=TenantId(row["id"]),
            organization_id=OrganizationId(row["organization_id"]),
            slug=row["slug"],
            name=row["name"],
            description=row.get("description"),
            schema_name=row.get("schema_name", ""),
            database_name=row.get("database_name"),
            custom_domain=row.get("custom_domain"),
            deployment_type=DeploymentType(row.get("deployment_type", "schema")),
            environment=row.get("environment", "production"),
            region_id=row.get("region_id"),
            database_connection_id=row.get("database_connection_id"),
            external_auth_provider=row.get("external_auth_provider", "keycloak"),
            external_auth_realm=row.get("external_auth_realm", ""),
            external_user_id=row.get("external_user_id", ""),
            external_auth_metadata=row.get("external_auth_metadata") or {},
            allow_impersonations=row.get("allow_impersonations", False),
            status=TenantStatus(row.get("status", "pending")),
            internal_notes=row.get("internal_notes"),
            features_enabled=row.get("features_enabled") or {},
            feature_overrides=row.get("feature_overrides") or {},
            provisioned_at=row.get("provisioned_at"),
            activated_at=row.get("activated_at"),
            suspended_at=row.get("suspended_at"),
            last_activity_at=row.get("last_activity_at"),
            metadata=row.get("metadata") or {},
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row.get("deleted_at")
        )