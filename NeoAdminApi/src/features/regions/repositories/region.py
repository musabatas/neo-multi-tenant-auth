"""
Repository for region management operations.
"""

import asyncpg
from typing import Optional, List, Dict, Any, Tuple
from src.common.utils import utc_now

# Import neo-commons base repository
from src.common.repositories.base import BaseRepository
from src.common.exceptions import NotFoundError, ConflictError, DatabaseError
from src.common.database.utils import process_database_record
from src.common.utils import generate_uuid_v7
from src.common.models import PaginationParams
from ..models.domain import Region
from ..models.request import RegionFilter, RegionCreate, RegionUpdate


class RegionRepository(BaseRepository[Region]):
    """Repository for region database operations using neo-commons BaseRepository."""
    
    def __init__(self, db=None):
        """Initialize repository with neo-commons BaseRepository.
        
        Args:
            db: DatabaseManager instance (deprecated, kept for backward compatibility)
        """
        super().__init__(table_name="regions", schema="admin")
        # db parameter is deprecated but kept for backward compatibility
    
    async def get_by_id(self, region_id: str) -> Region:
        """Get region by ID using neo-commons BaseRepository."""
        select_fields = """
            id, code, name, display_name,
            country_code, continent, city, timezone, coordinates,
            data_residency_compliant, gdpr_region, compliance_certifications, legal_entity,
            is_active, accepts_new_tenants, capacity_percentage,
            max_tenants, current_tenants, priority,
            provider, provider_region, availability_zones,
            primary_endpoint, backup_endpoints, internal_network,
            cost_per_gb_monthly_cents, cost_per_tenant_monthly_cents,
            created_at, updated_at
        """
        
        row = await super().get_by_id(region_id, select_fields)
        if not row:
            raise NotFoundError(f"Region {region_id} not found")
        
        data = process_database_record(
            row,
            uuid_fields=['id'],
            list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
        )
        return Region(**data)
    
    async def get_by_code(self, code: str) -> Region:
        """Get region by code using neo-commons BaseRepository."""
        select_fields = """
            id, code, name, display_name,
            country_code, continent, city, timezone, coordinates,
            data_residency_compliant, gdpr_region, compliance_certifications, legal_entity,
            is_active, accepts_new_tenants, capacity_percentage,
            max_tenants, current_tenants, priority,
            provider, provider_region, availability_zones,
            primary_endpoint, backup_endpoints, internal_network,
            cost_per_gb_monthly_cents, cost_per_tenant_monthly_cents,
            created_at, updated_at
        """
        
        table_name = self.get_full_table_name()
        query = f"""
            SELECT {select_fields}
            FROM {table_name}
            WHERE code = $1 AND deleted_at IS NULL
        """
        
        db = await self.get_connection()
        row = await db.fetchrow(query, code)
        if not row:
            raise NotFoundError(f"Region with code {code} not found")
        
        data = process_database_record(
            dict(row),
            uuid_fields=['id'],
            list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
        )
        return Region(**data)
    
    async def list(
        self,
        filters: Optional[RegionFilter] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Region], int]:
        """List regions with filters using neo-commons BaseRepository."""
        select_fields = """
            id, code, name, display_name,
            country_code, continent, city, timezone, coordinates,
            data_residency_compliant, gdpr_region, compliance_certifications, legal_entity,
            is_active, accepts_new_tenants, capacity_percentage,
            max_tenants, current_tenants, priority,
            provider, provider_region, availability_zones,
            primary_endpoint, backup_endpoints, internal_network,
            cost_per_gb_monthly_cents, cost_per_tenant_monthly_cents,
            created_at, updated_at
        """
        
        # Convert filters to dict format for neo-commons
        filter_dict = {}
        additional_where = None
        
        if filters:
            if filters.is_active is not None:
                filter_dict['is_active'] = filters.is_active
            if filters.accepts_new_tenants is not None:
                filter_dict['accepts_new_tenants'] = filters.accepts_new_tenants
            if filters.gdpr_region is not None:
                filter_dict['gdpr_region'] = filters.gdpr_region
            if filters.provider:
                filter_dict['provider'] = filters.provider
            if filters.continent:
                filter_dict['continent'] = filters.continent
            if filters.search:
                additional_where = f"(name ILIKE '%{filters.search}%' OR code ILIKE '%{filters.search}%' OR display_name ILIKE '%{filters.search}%')"
        
        # Create pagination params
        page = (offset // limit) + 1
        pagination = PaginationParams(page=page, limit=limit)
        
        # Use neo-commons paginated_list with priority ordering
        rows, total_count = await super().paginated_list(
            pagination=pagination,
            filters=filter_dict,
            select_columns=select_fields,
            additional_where=additional_where,
            order_by="priority DESC, name ASC"
        )
        
        # Convert rows to Region objects
        regions = []
        for row in rows:
            data = process_database_record(
                row,
                uuid_fields=['id'],
                list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
            )
            regions.append(Region(**data))
        
        return regions, total_count
    
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create method required by BaseRepository - converts RegionCreate to dict."""
        # This method is required by BaseRepository interface
        # For regions, use create_region method instead
        raise NotImplementedError("Use create_region method for typed region creation")
    
    async def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update method required by BaseRepository - converts RegionUpdate to dict."""
        # This method is required by BaseRepository interface
        # For regions, use update_region method instead  
        raise NotImplementedError("Use update_region method for typed region updates")
    
    async def create_region(self, region_data: RegionCreate) -> Region:
        """Create a new region with typed data."""
        # Check if code already exists
        table_name = self.get_full_table_name()
        check_query = f"SELECT id FROM {table_name} WHERE code = $1 AND deleted_at IS NULL"
        
        db = await self.get_connection()
        existing = await db.fetchval(check_query, region_data.code)
        if existing:
            raise ConflictError(f"Region with code {region_data.code} already exists")
        
        region_id = generate_uuid_v7()
        now = utc_now()
        
        query = f"""
            INSERT INTO {table_name} (
                id, code, name, display_name,
                country_code, continent, city, timezone, coordinates,
                data_residency_compliant, gdpr_region, compliance_certifications,
                is_active, accepts_new_tenants, max_tenants, priority,
                provider, provider_region, primary_endpoint,
                cost_per_gb_monthly_cents, cost_per_tenant_monthly_cents,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                true, $13, $14, $15, $16, $17, $18, 0, 0, $19, $20
            )
            RETURNING *
        """
        
        row = await db.fetchrow(
            query,
            region_id,
            region_data.code,
            region_data.name,
            region_data.display_name,
            region_data.country_code,
            region_data.continent,
            region_data.city,
            region_data.timezone,
            region_data.coordinates,
            region_data.data_residency_compliant,
            region_data.gdpr_region,
            region_data.compliance_certifications,
            region_data.accepts_new_tenants,
            region_data.max_tenants,
            region_data.priority,
            region_data.provider,
            region_data.provider_region,
            region_data.primary_endpoint,
            now,
            now
        )
        
        data = process_database_record(
            dict(row),
            uuid_fields=['id'],
            list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
        )
        return Region(**data)
    
    # Backward compatibility methods for service layer
    async def create(self, region_data: RegionCreate) -> Region:
        """Backward compatible create method."""
        return await self.create_region(region_data)
    
    async def update_region(self, region_id: str, region_data: RegionUpdate) -> Region:
        """Update a region with typed data."""
        # Build UPDATE clause
        update_dict = region_data.model_dump(exclude_unset=True)
        if not update_dict:
            # Nothing to update, just return current
            return await self.get_by_id(region_id)
        
        # Add updated_at timestamp
        update_dict['updated_at'] = utc_now()
        
        # Build query dynamically
        update_fields = []
        params = [region_id]
        param_count = 1
        
        for field, value in update_dict.items():
            param_count += 1
            update_fields.append(f"{field} = ${param_count}")
            params.append(value)
        
        update_clause = ", ".join(update_fields)
        table_name = self.get_full_table_name()
        
        query = f"""
            UPDATE {table_name}
            SET {update_clause}
            WHERE id = $1 AND deleted_at IS NULL
            RETURNING *
        """
        
        db = await self.get_connection()
        row = await db.fetchrow(query, *params)
        if not row:
            raise NotFoundError(f"Region {region_id} not found")
        
        data = process_database_record(
            dict(row),
            uuid_fields=['id'],
            list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
        )
        return Region(**data)
    
    # Backward compatibility method for service layer
    async def update(self, region_id: str, region_data: RegionUpdate) -> Region:
        """Backward compatible update method."""
        return await self.update_region(region_id, region_data)
    
    async def delete_region(self, region_id: str) -> None:
        """Delete a region (soft delete by deactivating)."""
        db = await self.get_connection()
        admin_schema = self.schema_provider.get_admin_schema()
        
        # Check if region has active database connections
        check_query = f"""
            SELECT COUNT(*) FROM {admin_schema}.database_connections
            WHERE region_id = $1 AND is_active = true
        """
        active_connections = await db.fetchval(check_query, region_id)
        
        if active_connections > 0:
            raise ConflictError(
                f"Cannot delete region with {active_connections} active database connections"
            )
        
        # Check if region has tenants
        tenant_check_query = f"""
            SELECT COUNT(*) FROM {admin_schema}.tenants
            WHERE region_id = $1
        """
        tenant_count = await db.fetchval(tenant_check_query, region_id)
        
        if tenant_count > 0:
            raise ConflictError(
                f"Cannot delete region with {tenant_count} tenants"
            )
        
        # Soft delete by deactivating
        table_name = self.get_full_table_name()
        query = f"""
            UPDATE {table_name}
            SET is_active = false,
                accepts_new_tenants = false,
                updated_at = $2
            WHERE id = $1 AND deleted_at IS NULL
            RETURNING id
        """
        
        result = await db.fetchval(query, region_id, utc_now())
        if not result:
            raise NotFoundError(f"Region {region_id} not found")
    
    # Backward compatibility method for service layer
    async def delete(self, region_id: str) -> None:
        """Backward compatible delete method."""
        return await self.delete_region(region_id)
    
    async def get_database_count(self, region_id: str) -> int:
        """Get count of database connections for a region."""
        db = await self.get_connection()
        admin_schema = self.schema_provider.get_admin_schema()
        
        query = f"""
            SELECT COUNT(*) FROM {admin_schema}.database_connections
            WHERE region_id = $1
        """
        return await db.fetchval(query, region_id)
    
    async def update_tenant_count(self, region_id: str) -> None:
        """Update current tenant count for a region."""
        db = await self.get_connection()
        admin_schema = self.schema_provider.get_admin_schema()
        table_name = self.get_full_table_name()
        
        query = f"""
            UPDATE {table_name}
            SET current_tenants = (
                SELECT COUNT(*) FROM {admin_schema}.tenants
                WHERE region_id = $1 AND is_active = true
            ),
            capacity_percentage = CASE
                WHEN max_tenants IS NOT NULL AND max_tenants > 0 THEN
                    CAST((
                        SELECT COUNT(*) FROM {admin_schema}.tenants
                        WHERE region_id = $1 AND is_active = true
                    ) * 100.0 / max_tenants AS INT)
                ELSE 0
            END,
            updated_at = $2
            WHERE id = $1
        """
        await db.execute(query, region_id, utc_now())