"""
Repository layer for tenant data access.
"""

from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
import json
from loguru import logger

from src.common.database.connection import get_database
from src.common.database.utils import process_database_record
from src.common.exceptions.base import NotFoundError, ConflictError
from src.common.utils.datetime import utc_now
from src.common.utils.uuid import generate_uuid_v7
from ..models.domain import Tenant, TenantContact
from ..models.request import TenantCreate, TenantUpdate, TenantFilter, TenantStatusUpdate


class TenantRepository:
    """Repository for tenant database operations."""
    
    def __init__(self):
        """Initialize tenant repository."""
        self.db = get_database()
    
    async def get_by_id(self, tenant_id: str) -> Tenant:
        """Get tenant by ID.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Tenant domain model
            
        Raises:
            NotFoundError: If tenant not found
        """
        query = """
            SELECT 
                t.*,
                o.name as organization_name,
                o.slug as organization_slug,
                r.code as region_code,
                r.name as region_name
            FROM admin.tenants t
            LEFT JOIN admin.organizations o ON t.organization_id = o.id
            LEFT JOIN admin.regions r ON t.region_id = r.id
            WHERE t.id = $1 AND t.deleted_at IS NULL
        """
        
        result = await self.db.fetchrow(query, tenant_id)
        
        if not result:
            raise NotFoundError("Tenant", tenant_id)
        
        return self._map_to_domain(result)
    
    async def get_by_slug(self, slug: str) -> Tenant:
        """Get tenant by slug.
        
        Args:
            slug: Tenant slug
            
        Returns:
            Tenant domain model
            
        Raises:
            NotFoundError: If tenant not found
        """
        query = """
            SELECT 
                t.*,
                o.name as organization_name,
                o.slug as organization_slug,
                r.code as region_code,
                r.name as region_name
            FROM admin.tenants t
            LEFT JOIN admin.organizations o ON t.organization_id = o.id
            LEFT JOIN admin.regions r ON t.region_id = r.id
            WHERE t.slug = $1 AND t.deleted_at IS NULL
        """
        
        result = await self.db.fetchrow(query, slug)
        
        if not result:
            raise NotFoundError("Tenant", slug)
        
        return self._map_to_domain(result)
    
    async def list(
        self,
        filters: Optional[TenantFilter] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Tenant], int]:
        """List tenants with filters and pagination.
        
        Args:
            filters: Optional filters
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Tuple of (tenants list, total count)
        """
        # Build WHERE clause
        where_conditions = ["t.deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters:
            if filters.organization_id:
                param_count += 1
                where_conditions.append(f"t.organization_id = ${param_count}")
                params.append(str(filters.organization_id))
            
            if filters.status:
                param_count += 1
                where_conditions.append(f"t.status = ANY(${param_count})")
                params.append(filters.status)
            
            if filters.environment:
                param_count += 1
                where_conditions.append(f"t.environment = ${param_count}")
                params.append(filters.environment)
            
            if filters.region_id:
                param_count += 1
                where_conditions.append(f"t.region_id = ${param_count}")
                params.append(str(filters.region_id))
            
            if filters.deployment_type:
                param_count += 1
                where_conditions.append(f"t.deployment_type = ${param_count}")
                params.append(filters.deployment_type)
            
            if filters.external_auth_provider:
                param_count += 1
                where_conditions.append(f"t.external_auth_provider = ${param_count}")
                params.append(filters.external_auth_provider)
            
            if filters.is_active is not None:
                if filters.is_active:
                    where_conditions.append("t.status = 'active'")
                else:
                    where_conditions.append("t.status != 'active'")
            
            if filters.has_custom_domain is not None:
                if filters.has_custom_domain:
                    where_conditions.append("t.custom_domain IS NOT NULL")
                else:
                    where_conditions.append("t.custom_domain IS NULL")
            
            if filters.search:
                param_count += 1
                where_conditions.append(f"""
                    (LOWER(t.name) LIKE LOWER(${param_count}) OR 
                     LOWER(t.slug) LIKE LOWER(${param_count}) OR 
                     LOWER(t.description) LIKE LOWER(${param_count}))
                """)
                params.append(f"%{filters.search}%")
            
            if filters.created_after:
                param_count += 1
                where_conditions.append(f"t.created_at >= ${param_count}")
                params.append(filters.created_after)
            
            if filters.created_before:
                param_count += 1
                where_conditions.append(f"t.created_at <= ${param_count}")
                params.append(filters.created_before)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count query
        count_query = f"""
            SELECT COUNT(*) as total
            FROM admin.tenants t
            WHERE {where_clause}
        """
        
        # Data query
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        
        data_query = f"""
            SELECT 
                t.*,
                o.name as organization_name,
                o.slug as organization_slug,
                r.code as region_code,
                r.name as region_name
            FROM admin.tenants t
            LEFT JOIN admin.organizations o ON t.organization_id = o.id
            LEFT JOIN admin.regions r ON t.region_id = r.id
            WHERE {where_clause}
            ORDER BY t.created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        # Execute queries
        count_result = await self.db.fetchrow(count_query, *params)
        total_count = count_result['total']
        
        params.extend([limit, offset])
        results = await self.db.fetch(data_query, *params)
        
        tenants = [self._map_to_domain(row) for row in results]
        
        return tenants, total_count
    
    async def create(self, tenant_data: TenantCreate) -> Tenant:
        """Create a new tenant.
        
        Args:
            tenant_data: Tenant creation data
            
        Returns:
            Created tenant
            
        Raises:
            ConflictError: If slug already exists
        """
        # Check if slug exists
        existing = await self.db.fetchrow(
            "SELECT id FROM admin.tenants WHERE slug = $1",
            tenant_data.slug
        )
        
        if existing:
            raise ConflictError(
                message=f"Tenant with slug '{tenant_data.slug}' already exists",
                conflicting_field="slug",
                conflicting_value=tenant_data.slug
            )
        
        # Generate schema name if not provided
        schema_name = f"tenant_{tenant_data.slug.replace('-', '_')}"
        
        # Generate external auth realm if not provided
        external_auth_realm = tenant_data.external_auth_realm
        if not external_auth_realm:
            # Generate realm name but don't assume pattern
            external_auth_realm = f"tenant-{tenant_data.slug}"
        
        # Generate external user ID (for Keycloak realm admin)
        external_user_id = str(generate_uuid_v7())
        
        tenant_id = generate_uuid_v7()
        now = utc_now()
        
        query = """
            INSERT INTO admin.tenants (
                id, organization_id, slug, name, description,
                schema_name, database_name, deployment_type, environment,
                region_id, custom_domain,
                external_auth_provider, external_auth_realm, external_user_id,
                external_auth_metadata, allow_impersonations,
                status, features_enabled, feature_overrides,
                internal_notes, metadata,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9,
                $10, $11,
                $12, $13, $14,
                $15, $16,
                $17, $18, $19,
                $20, $21,
                $22, $23
            )
            RETURNING *
        """
        
        result = await self.db.fetchrow(
            query,
            tenant_id,
            str(tenant_data.organization_id),
            tenant_data.slug,
            tenant_data.name,
            tenant_data.description,
            schema_name,
            None,  # database_name
            tenant_data.deployment_type,
            tenant_data.environment,
            str(tenant_data.region_id) if tenant_data.region_id else None,
            tenant_data.custom_domain,
            tenant_data.external_auth_provider,
            external_auth_realm,
            external_user_id,
            json.dumps({}),  # external_auth_metadata
            tenant_data.allow_impersonations,
            'pending',  # status
            json.dumps(tenant_data.features_enabled),
            json.dumps({}),  # feature_overrides
            tenant_data.internal_notes,
            json.dumps(tenant_data.metadata),
            now,
            now
        )
        
        logger.info(f"Created tenant {tenant_id} with slug '{tenant_data.slug}'")
        
        return self._map_to_domain(result)
    
    async def update(self, tenant_id: str, update_data: TenantUpdate) -> Tenant:
        """Update a tenant.
        
        Args:
            tenant_id: Tenant ID to update
            update_data: Update data
            
        Returns:
            Updated tenant
            
        Raises:
            NotFoundError: If tenant not found
        """
        # Build UPDATE clause
        update_fields = []
        params = []
        param_count = 0
        
        if update_data.name is not None:
            param_count += 1
            update_fields.append(f"name = ${param_count}")
            params.append(update_data.name)
        
        if update_data.description is not None:
            param_count += 1
            update_fields.append(f"description = ${param_count}")
            params.append(update_data.description)
        
        if update_data.custom_domain is not None:
            param_count += 1
            update_fields.append(f"custom_domain = ${param_count}")
            params.append(update_data.custom_domain if update_data.custom_domain else None)
        
        if update_data.environment is not None:
            param_count += 1
            update_fields.append(f"environment = ${param_count}")
            params.append(update_data.environment)
        
        if update_data.allow_impersonations is not None:
            param_count += 1
            update_fields.append(f"allow_impersonations = ${param_count}")
            params.append(update_data.allow_impersonations)
        
        if update_data.features_enabled is not None:
            param_count += 1
            update_fields.append(f"features_enabled = ${param_count}")
            params.append(json.dumps(update_data.features_enabled))
        
        if update_data.feature_overrides is not None:
            param_count += 1
            update_fields.append(f"feature_overrides = ${param_count}")
            params.append(json.dumps(update_data.feature_overrides))
        
        if update_data.internal_notes is not None:
            param_count += 1
            update_fields.append(f"internal_notes = ${param_count}")
            params.append(update_data.internal_notes)
        
        if update_data.metadata is not None:
            param_count += 1
            update_fields.append(f"metadata = ${param_count}")
            params.append(json.dumps(update_data.metadata))
        
        # Always update updated_at
        param_count += 1
        update_fields.append(f"updated_at = ${param_count}")
        params.append(utc_now())
        
        # Add tenant_id as last parameter
        param_count += 1
        params.append(tenant_id)
        
        if not update_fields:
            # Nothing to update
            return await self.get_by_id(tenant_id)
        
        update_clause = ", ".join(update_fields)
        
        query = f"""
            UPDATE admin.tenants
            SET {update_clause}
            WHERE id = ${param_count} AND deleted_at IS NULL
            RETURNING *
        """
        
        result = await self.db.fetchrow(query, *params)
        
        if not result:
            raise NotFoundError("Tenant", tenant_id)
        
        logger.info(f"Updated tenant {tenant_id}")
        
        return self._map_to_domain(result)
    
    async def update_status(
        self, 
        tenant_id: str, 
        status_update: TenantStatusUpdate
    ) -> Tenant:
        """Update tenant status.
        
        Args:
            tenant_id: Tenant ID
            status_update: Status update data
            
        Returns:
            Updated tenant
        """
        now = utc_now()
        
        # Set status-specific timestamps
        provisioned_at = None
        activated_at = None
        suspended_at = None
        
        if status_update.status == 'active':
            activated_at = now
        elif status_update.status == 'suspended':
            suspended_at = now
        elif status_update.status == 'provisioning':
            provisioned_at = now
        
        query = """
            UPDATE admin.tenants
            SET 
                status = $1,
                updated_at = $2,
                provisioned_at = COALESCE($3, provisioned_at),
                activated_at = COALESCE($4, activated_at),
                suspended_at = COALESCE($5, suspended_at)
            WHERE id = $6 AND deleted_at IS NULL
            RETURNING *
        """
        
        result = await self.db.fetchrow(
            query,
            status_update.status,
            now,
            provisioned_at,
            activated_at,
            suspended_at,
            tenant_id
        )
        
        if not result:
            raise NotFoundError("Tenant", tenant_id)
        
        logger.info(f"Updated tenant {tenant_id} status to {status_update.status}")
        
        return self._map_to_domain(result)
    
    async def delete(self, tenant_id: str) -> None:
        """Soft delete a tenant.
        
        Args:
            tenant_id: Tenant ID to delete
        """
        query = """
            UPDATE admin.tenants
            SET 
                deleted_at = $1,
                status = 'deleted',
                updated_at = $1
            WHERE id = $2 AND deleted_at IS NULL
        """
        
        result = await self.db.execute(query, utc_now(), tenant_id)
        
        if result == "UPDATE 0":
            raise NotFoundError("Tenant", tenant_id)
        
        logger.info(f"Soft deleted tenant {tenant_id}")
    
    async def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant statistics.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Dictionary with statistics
        """
        # This would query the tenant's regional database
        # For now, return mock data
        return {
            'user_count': 0,
            'active_user_count': 0,
            'storage_used_mb': 0.0
        }
    
    async def get_organization_info(self, organization_id: str) -> Dict[str, Any]:
        """Get organization information.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Organization info dictionary
        """
        query = """
            SELECT id, name, slug, is_active
            FROM admin.organizations
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        result = await self.db.fetchrow(query, organization_id)
        
        if not result:
            raise NotFoundError("Organization", organization_id)
        
        return process_database_record(
            result,
            uuid_fields=['id']
        )
    
    async def get_region_info(self, region_id: str) -> Dict[str, Any]:
        """Get region information.
        
        Args:
            region_id: Region ID
            
        Returns:
            Region info dictionary
        """
        query = """
            SELECT id, code, name, country_code, is_active
            FROM admin.regions
            WHERE id = $1
        """
        
        result = await self.db.fetchrow(query, region_id)
        
        if not result:
            return None
        
        return process_database_record(
            result,
            uuid_fields=['id']
        )
    
    async def get_subscription_info(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant subscription information.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Subscription info dictionary
        """
        query = """
            SELECT 
                ts.id,
                sp.name as plan_name,
                sp.plan_tier,
                ts.status,
                ts.current_period_end
            FROM admin.tenant_subscriptions ts
            JOIN admin.subscription_plans sp ON ts.plan_id = sp.id
            WHERE ts.tenant_id = $1
            ORDER BY ts.created_at DESC
            LIMIT 1
        """
        
        result = await self.db.fetchrow(query, tenant_id)
        
        if not result:
            return None
        
        return process_database_record(
            result,
            uuid_fields=['id']
        )
    
    def _map_to_domain(self, row) -> Tenant:
        """Map database row to domain model.
        
        Args:
            row: Database row
            
        Returns:
            Tenant domain model
        """
        data = process_database_record(
            row,
            uuid_fields=['id', 'organization_id', 'region_id', 'database_connection_id'],
            jsonb_fields=['external_auth_metadata', 'features_enabled', 'feature_overrides', 'metadata']
        )
        
        return Tenant(**data)