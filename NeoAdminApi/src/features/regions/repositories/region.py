"""
Repository for region management operations.
"""

import asyncpg
from typing import Optional, List, Dict, Any
from src.common.utils.datetime import utc_now

from src.common.database.connection import DatabaseManager
from src.common.exceptions import NotFoundError, ConflictError, DatabaseError
from src.common.database.utils import process_database_record
from src.common.utils.uuid import generate_uuid_v7
from ..models.domain import Region
from ..models.request import RegionFilter, RegionCreate, RegionUpdate


class RegionRepository:
    """Repository for region database operations."""
    
    def __init__(self, db: DatabaseManager):
        """Initialize repository with database connection.
        
        Args:
            db: DatabaseManager instance
        """
        self.db = db
        self.pool = db.pool
    
    async def get_by_id(self, region_id: str) -> Region:
        """Get region by ID."""
        query = """
            SELECT 
                id, code, name, display_name,
                country_code, continent, city, timezone, coordinates,
                data_residency_compliant, gdpr_region, compliance_certifications, legal_entity,
                is_active, accepts_new_tenants, capacity_percentage,
                max_tenants, current_tenants, priority,
                provider, provider_region, availability_zones,
                primary_endpoint, backup_endpoints, internal_network,
                cost_per_gb_monthly_cents, cost_per_tenant_monthly_cents,
                created_at, updated_at
            FROM admin.regions
            WHERE id = $1
        """
        
        try:
            row = await self.pool.fetchrow(query, region_id)
            if not row:
                raise NotFoundError(f"Region {region_id} not found")
            
            data = process_database_record(
                dict(row),
                uuid_fields=['id'],
                list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
            )
            return Region(**data)
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get region: {str(e)}")
    
    async def get_by_code(self, code: str) -> Region:
        """Get region by code."""
        query = """
            SELECT 
                id, code, name, display_name,
                country_code, continent, city, timezone, coordinates,
                data_residency_compliant, gdpr_region, compliance_certifications, legal_entity,
                is_active, accepts_new_tenants, capacity_percentage,
                max_tenants, current_tenants, priority,
                provider, provider_region, availability_zones,
                primary_endpoint, backup_endpoints, internal_network,
                cost_per_gb_monthly_cents, cost_per_tenant_monthly_cents,
                created_at, updated_at
            FROM admin.regions
            WHERE code = $1
        """
        
        try:
            row = await self.pool.fetchrow(query, code)
            if not row:
                raise NotFoundError(f"Region with code {code} not found")
            
            data = process_database_record(
                dict(row),
                uuid_fields=['id'],
                list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
            )
            return Region(**data)
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to get region: {str(e)}")
    
    async def list(
        self,
        filters: Optional[RegionFilter] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Region], int]:
        """List regions with filters."""
        # Build WHERE clause
        where_clauses = []
        params = []
        param_count = 0
        
        if filters:
            if filters.is_active is not None:
                param_count += 1
                where_clauses.append(f"is_active = ${param_count}")
                params.append(filters.is_active)
            
            if filters.accepts_new_tenants is not None:
                param_count += 1
                where_clauses.append(f"accepts_new_tenants = ${param_count}")
                params.append(filters.accepts_new_tenants)
            
            if filters.gdpr_region is not None:
                param_count += 1
                where_clauses.append(f"gdpr_region = ${param_count}")
                params.append(filters.gdpr_region)
            
            if filters.provider:
                param_count += 1
                where_clauses.append(f"provider = ${param_count}")
                params.append(filters.provider)
            
            if filters.continent:
                param_count += 1
                where_clauses.append(f"continent = ${param_count}")
                params.append(filters.continent)
            
            if filters.search:
                param_count += 1
                where_clauses.append(
                    f"(name ILIKE ${param_count} OR code ILIKE ${param_count} OR display_name ILIKE ${param_count})"
                )
                params.append(f"%{filters.search}%")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Count query
        count_query = f"""
            SELECT COUNT(*) FROM admin.regions
            WHERE {where_clause}
        """
        
        # Data query
        param_count += 1
        limit_param = param_count
        params.append(limit)
        
        param_count += 1
        offset_param = param_count
        params.append(offset)
        
        data_query = f"""
            SELECT 
                id, code, name, display_name,
                country_code, continent, city, timezone, coordinates,
                data_residency_compliant, gdpr_region, compliance_certifications, legal_entity,
                is_active, accepts_new_tenants, capacity_percentage,
                max_tenants, current_tenants, priority,
                provider, provider_region, availability_zones,
                primary_endpoint, backup_endpoints, internal_network,
                cost_per_gb_monthly_cents, cost_per_tenant_monthly_cents,
                created_at, updated_at
            FROM admin.regions
            WHERE {where_clause}
            ORDER BY priority DESC, name ASC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        try:
            # Execute both queries
            count_params = params[:-2] if params else []  # Exclude limit/offset
            total_count = await self.pool.fetchval(count_query, *count_params)
            rows = await self.pool.fetch(data_query, *params)
            
            regions = []
            for row in rows:
                data = process_database_record(
                    dict(row),
                    uuid_fields=['id'],
                    list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
                )
                regions.append(Region(**data))
            
            return regions, total_count
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to list regions: {str(e)}")
    
    async def create(self, region_data: RegionCreate) -> Region:
        """Create a new region."""
        # Check if code already exists
        check_query = "SELECT id FROM admin.regions WHERE code = $1"
        existing = await self.pool.fetchval(check_query, region_data.code)
        if existing:
            raise ConflictError(f"Region with code {region_data.code} already exists")
        
        region_id = generate_uuid_v7()
        now = utc_now()
        
        query = """
            INSERT INTO admin.regions (
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
        
        try:
            row = await self.pool.fetchrow(
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
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to create region: {str(e)}")
    
    async def update(self, region_id: str, region_data: RegionUpdate) -> Region:
        """Update a region."""
        # Build UPDATE clause
        update_fields = []
        params = [region_id]
        param_count = 1
        
        update_dict = region_data.model_dump(exclude_unset=True)
        if not update_dict:
            # Nothing to update, just return current
            return await self.get_by_id(region_id)
        
        for field, value in update_dict.items():
            param_count += 1
            update_fields.append(f"{field} = ${param_count}")
            params.append(value)
        
        # Always update updated_at
        param_count += 1
        update_fields.append(f"updated_at = ${param_count}")
        params.append(utc_now())
        
        update_clause = ", ".join(update_fields)
        
        query = f"""
            UPDATE admin.regions
            SET {update_clause}
            WHERE id = $1
            RETURNING *
        """
        
        try:
            row = await self.pool.fetchrow(query, *params)
            if not row:
                raise NotFoundError(f"Region {region_id} not found")
            
            data = process_database_record(
                dict(row),
                uuid_fields=['id'],
                list_jsonb_fields=['compliance_certifications', 'availability_zones', 'backup_endpoints']
            )
            return Region(**data)
            
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to update region: {str(e)}")
    
    async def delete(self, region_id: str) -> None:
        """Delete a region (soft delete by deactivating)."""
        # Check if region has active database connections
        check_query = """
            SELECT COUNT(*) FROM admin.database_connections
            WHERE region_id = $1 AND is_active = true
        """
        active_connections = await self.pool.fetchval(check_query, region_id)
        
        if active_connections > 0:
            raise ConflictError(
                f"Cannot delete region with {active_connections} active database connections"
            )
        
        # Check if region has tenants
        tenant_check_query = """
            SELECT COUNT(*) FROM admin.tenants
            WHERE region_id = $1
        """
        tenant_count = await self.pool.fetchval(tenant_check_query, region_id)
        
        if tenant_count > 0:
            raise ConflictError(
                f"Cannot delete region with {tenant_count} tenants"
            )
        
        # Soft delete by deactivating
        query = """
            UPDATE admin.regions
            SET is_active = false,
                accepts_new_tenants = false,
                updated_at = $2
            WHERE id = $1
            RETURNING id
        """
        
        try:
            result = await self.pool.fetchval(query, region_id, utc_now())
            if not result:
                raise NotFoundError(f"Region {region_id} not found")
        except asyncpg.PostgresError as e:
            raise DatabaseError(f"Failed to delete region: {str(e)}")
    
    async def get_database_count(self, region_id: str) -> int:
        """Get count of database connections for a region."""
        query = """
            SELECT COUNT(*) FROM admin.database_connections
            WHERE region_id = $1
        """
        return await self.pool.fetchval(query, region_id)
    
    async def update_tenant_count(self, region_id: str) -> None:
        """Update current tenant count for a region."""
        query = """
            UPDATE admin.regions
            SET current_tenants = (
                SELECT COUNT(*) FROM admin.tenants
                WHERE region_id = $1 AND is_active = true
            ),
            capacity_percentage = CASE
                WHEN max_tenants IS NOT NULL AND max_tenants > 0 THEN
                    CAST((
                        SELECT COUNT(*) FROM admin.tenants
                        WHERE region_id = $1 AND is_active = true
                    ) * 100.0 / max_tenants AS INT)
                ELSE 0
            END,
            updated_at = $2
            WHERE id = $1
        """
        await self.pool.execute(query, region_id, utc_now())