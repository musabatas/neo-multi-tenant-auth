"""
Repository layer for organization data access.
"""

from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID
import json
from loguru import logger

from neo_commons.repositories.base import BaseRepository
from neo_commons.database.utils import process_database_record
from neo_commons.exceptions.base import NotFoundError, ConflictError
from src.common.utils import utc_now
from src.common.utils import generate_uuid_v7
from src.common.database.connection_provider import neo_admin_connection_provider
from ..models.domain import Organization
from ..models.request import OrganizationCreate, OrganizationUpdate, OrganizationFilter


class OrganizationRepository(BaseRepository[Dict[str, Any]]):
    """Repository for organization database operations."""
    
    def __init__(self, schema: str = "admin"):
        """Initialize organization repository with BaseRepository and configurable schema.
        
        Args:
            schema: Database schema to use (default: admin)
        """
        super().__init__(
            table_name="organizations", 
            default_schema=schema,
            connection_provider=neo_admin_connection_provider
        )
    
    async def get_by_id(self, organization_id: str) -> Organization:
        """Get organization by ID.
        
        Args:
            organization_id: Organization UUID
            
        Returns:
            Organization domain model
            
        Raises:
            NotFoundError: If organization not found
        """
        query = f"""
            SELECT * FROM {self.get_current_schema()}.organizations
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        db = await self.get_connection()
        result = await db.fetchrow(query, organization_id)
        
        if not result:
            raise NotFoundError("Organization", organization_id)
        
        return self._map_to_domain(result)
    
    async def get_by_slug(self, slug: str) -> Organization:
        """Get organization by slug.
        
        Args:
            slug: Organization slug
            
        Returns:
            Organization domain model
            
        Raises:
            NotFoundError: If organization not found
        """
        query = f"""
            SELECT * FROM {self.get_current_schema()}.organizations
            WHERE slug = $1 AND deleted_at IS NULL
        """
        
        db = await self.get_connection()
        result = await db.fetchrow(query, slug)
        
        if not result:
            raise NotFoundError("Organization", slug)
        
        return self._map_to_domain(result)
    
    async def list(
        self,
        filters: Optional[OrganizationFilter] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Organization], int]:
        """List organizations with filters and pagination.
        
        Args:
            filters: Optional filters
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Tuple of (organizations list, total count)
        """
        # Build WHERE clause
        where_conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if filters:
            if filters.search:
                param_count += 1
                where_conditions.append(f"""
                    (LOWER(name) LIKE LOWER(${param_count}) OR 
                     LOWER(slug) LIKE LOWER(${param_count}) OR 
                     LOWER(legal_name) LIKE LOWER(${param_count}))
                """)
                params.append(f"%{filters.search}%")
            
            if filters.country_code:
                param_count += 1
                where_conditions.append(f"country_code = ${param_count}")
                params.append(filters.country_code)
            
            if filters.industry:
                param_count += 1
                where_conditions.append(f"industry = ${param_count}")
                params.append(filters.industry)
            
            if filters.company_size:
                param_count += 1
                where_conditions.append(f"company_size = ${param_count}")
                params.append(filters.company_size)
            
            if filters.is_active is not None:
                param_count += 1
                where_conditions.append(f"is_active = ${param_count}")
                params.append(filters.is_active)
            
            if filters.is_verified is not None:
                if filters.is_verified:
                    where_conditions.append("verified_at IS NOT NULL")
                else:
                    where_conditions.append("verified_at IS NULL")
            
            if filters.created_after:
                param_count += 1
                where_conditions.append(f"created_at >= ${param_count}")
                params.append(filters.created_after)
            
            if filters.created_before:
                param_count += 1
                where_conditions.append(f"created_at <= ${param_count}")
                params.append(filters.created_before)
        
        where_clause = " AND ".join(where_conditions)
        
        # Count query
        count_query = f"""
            SELECT COUNT(*) as total
            FROM {self.get_current_schema()}.organizations
            WHERE {where_clause}
        """
        
        # Data query
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        
        data_query = f"""
            SELECT * FROM {self.get_current_schema()}.organizations
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        # Execute queries
        db = await self.get_connection()
        count_result = await db.fetchrow(count_query, *params)
        total_count = count_result['total']
        
        params.extend([limit, offset])
        results = await db.fetch(data_query, *params)
        
        organizations = [self._map_to_domain(row) for row in results]
        
        return organizations, total_count
    
    async def create(self, organization_data: OrganizationCreate) -> Organization:
        """Create a new organization.
        
        Args:
            organization_data: Organization creation data
            
        Returns:
            Created organization
            
        Raises:
            ConflictError: If slug already exists
        """
        # Check if slug exists
        db = await self.get_connection()
        existing = await db.fetchrow(
            f"SELECT id FROM {self.get_current_schema()}.organizations WHERE slug = $1",
            organization_data.slug
        )
        
        if existing:
            raise ConflictError(
                message=f"Organization with slug '{organization_data.slug}' already exists",
                conflicting_field="slug",
                conflicting_value=organization_data.slug
            )
        
        organization_id = generate_uuid_v7()
        now = utc_now()
        
        query = f"""
            INSERT INTO {self.get_current_schema()}.organizations (
                id, name, slug, legal_name,
                tax_id, business_type, industry, company_size, website_url,
                primary_contact_id,
                address_line1, address_line2, city, state_province, postal_code, country_code,
                default_timezone, default_locale, default_currency,
                logo_url, brand_colors,
                is_active, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4,
                $5, $6, $7, $8, $9,
                $10,
                $11, $12, $13, $14, $15, $16,
                $17, $18, $19,
                $20, $21,
                $22, $23, $24
            )
            RETURNING *
        """
        
        db = await self.get_connection()
        result = await db.fetchrow(
            query,
            organization_id,
            organization_data.name,
            organization_data.slug,
            organization_data.legal_name,
            organization_data.tax_id,
            organization_data.business_type,
            organization_data.industry,
            organization_data.company_size,
            organization_data.website_url,
            str(organization_data.primary_contact_id) if organization_data.primary_contact_id else None,
            organization_data.address_line1,
            organization_data.address_line2,
            organization_data.city,
            organization_data.state_province,
            organization_data.postal_code,
            organization_data.country_code,
            organization_data.default_timezone,
            organization_data.default_locale,
            organization_data.default_currency,
            organization_data.logo_url,
            json.dumps(organization_data.brand_colors),
            True,  # is_active
            now,
            now
        )
        
        logger.info(f"Created organization {organization_id} with slug '{organization_data.slug}'")
        
        return self._map_to_domain(result)
    
    async def update(self, organization_id: str, update_data: OrganizationUpdate) -> Organization:
        """Update an organization.
        
        Args:
            organization_id: Organization ID to update
            update_data: Update data
            
        Returns:
            Updated organization
            
        Raises:
            NotFoundError: If organization not found
        """
        # Build UPDATE clause
        update_fields = []
        params = []
        param_count = 0
        
        if update_data.name is not None:
            param_count += 1
            update_fields.append(f"name = ${param_count}")
            params.append(update_data.name)
        
        if update_data.legal_name is not None:
            param_count += 1
            update_fields.append(f"legal_name = ${param_count}")
            params.append(update_data.legal_name)
        
        if update_data.tax_id is not None:
            param_count += 1
            update_fields.append(f"tax_id = ${param_count}")
            params.append(update_data.tax_id if update_data.tax_id else None)
        
        if update_data.business_type is not None:
            param_count += 1
            update_fields.append(f"business_type = ${param_count}")
            params.append(update_data.business_type)
        
        if update_data.industry is not None:
            param_count += 1
            update_fields.append(f"industry = ${param_count}")
            params.append(update_data.industry)
        
        if update_data.company_size is not None:
            param_count += 1
            update_fields.append(f"company_size = ${param_count}")
            params.append(update_data.company_size)
        
        if update_data.website_url is not None:
            param_count += 1
            update_fields.append(f"website_url = ${param_count}")
            params.append(update_data.website_url if update_data.website_url else None)
        
        if update_data.primary_contact_id is not None:
            param_count += 1
            update_fields.append(f"primary_contact_id = ${param_count}")
            params.append(str(update_data.primary_contact_id) if update_data.primary_contact_id else None)
        
        if update_data.address_line1 is not None:
            param_count += 1
            update_fields.append(f"address_line1 = ${param_count}")
            params.append(update_data.address_line1)
        
        if update_data.address_line2 is not None:
            param_count += 1
            update_fields.append(f"address_line2 = ${param_count}")
            params.append(update_data.address_line2)
        
        if update_data.city is not None:
            param_count += 1
            update_fields.append(f"city = ${param_count}")
            params.append(update_data.city)
        
        if update_data.state_province is not None:
            param_count += 1
            update_fields.append(f"state_province = ${param_count}")
            params.append(update_data.state_province)
        
        if update_data.postal_code is not None:
            param_count += 1
            update_fields.append(f"postal_code = ${param_count}")
            params.append(update_data.postal_code)
        
        if update_data.country_code is not None:
            param_count += 1
            update_fields.append(f"country_code = ${param_count}")
            params.append(update_data.country_code)
        
        if update_data.default_timezone is not None:
            param_count += 1
            update_fields.append(f"default_timezone = ${param_count}")
            params.append(update_data.default_timezone)
        
        if update_data.default_locale is not None:
            param_count += 1
            update_fields.append(f"default_locale = ${param_count}")
            params.append(update_data.default_locale)
        
        if update_data.default_currency is not None:
            param_count += 1
            update_fields.append(f"default_currency = ${param_count}")
            params.append(update_data.default_currency)
        
        if update_data.logo_url is not None:
            param_count += 1
            update_fields.append(f"logo_url = ${param_count}")
            params.append(update_data.logo_url if update_data.logo_url else None)
        
        if update_data.brand_colors is not None:
            param_count += 1
            update_fields.append(f"brand_colors = ${param_count}")
            params.append(json.dumps(update_data.brand_colors))
        
        if update_data.is_active is not None:
            param_count += 1
            update_fields.append(f"is_active = ${param_count}")
            params.append(update_data.is_active)
        
        # Always update updated_at
        param_count += 1
        update_fields.append(f"updated_at = ${param_count}")
        params.append(utc_now())
        
        # Add organization_id as last parameter
        param_count += 1
        params.append(organization_id)
        
        if not update_fields:
            # Nothing to update
            return await self.get_by_id(organization_id)
        
        update_clause = ", ".join(update_fields)
        
        query = f"""
            UPDATE {self.get_current_schema()}.organizations
            SET {update_clause}
            WHERE id = ${param_count} AND deleted_at IS NULL
            RETURNING *
        """
        
        db = await self.get_connection()
        result = await db.fetchrow(query, *params)
        
        if not result:
            raise NotFoundError("Organization", organization_id)
        
        logger.info(f"Updated organization {organization_id}")
        
        return self._map_to_domain(result)
    
    async def delete(self, organization_id: str) -> None:
        """Soft delete an organization.
        
        Args:
            organization_id: Organization ID to delete
        """
        query = f"""
            UPDATE {self.get_current_schema()}.organizations
            SET 
                deleted_at = $1,
                is_active = false,
                updated_at = $1
            WHERE id = $2 AND deleted_at IS NULL
        """
        
        db = await self.get_connection()
        result = await db.execute(query, utc_now(), organization_id)
        
        if result == "UPDATE 0":
            raise NotFoundError("Organization", organization_id)
        
        logger.info(f"Soft deleted organization {organization_id}")
    
    async def get_organization_stats(self, organization_id: str) -> Dict[str, Any]:
        """Get organization statistics.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Dictionary with statistics
        """
        # Get tenant count
        tenant_query = f"""
            SELECT COUNT(*) as tenant_count,
                   COUNT(*) FILTER (WHERE status = 'active') as active_tenant_count
            FROM {self.get_current_schema()}.tenants
            WHERE organization_id = $1 AND deleted_at IS NULL
        """
        
        db = await self.get_connection()
        tenant_result = await db.fetchrow(tenant_query, organization_id)
        
        # User count would come from tenant databases
        # For now, return mock data
        return {
            'tenant_count': tenant_result['tenant_count'],
            'active_tenant_count': tenant_result['active_tenant_count'],
            'user_count': 0  # Would aggregate from tenant DBs
        }
    
    async def get_contact_info(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact information for a user.
        
        Args:
            contact_id: User ID
            
        Returns:
            Contact info dictionary or None
        """
        if not contact_id:
            return None
        
        query = f"""
            SELECT id, name, email
            FROM {self.get_current_schema()}.platform_users
            WHERE id = $1
        """
        
        db = await self.get_connection()
        result = await db.fetchrow(query, contact_id)
        
        if not result:
            return None
        
        return process_database_record(
            result,
            uuid_fields=['id']
        )
    
    def _map_to_domain(self, row) -> Organization:
        """Map database row to domain model.
        
        Args:
            row: Database row
            
        Returns:
            Organization domain model
        """
        data = process_database_record(
            row,
            uuid_fields=['id', 'primary_contact_id'],
            jsonb_fields=['brand_colors']
        )
        
        # Handle verification_documents array
        if 'verification_documents' in data and data['verification_documents'] is None:
            data['verification_documents'] = []
        
        return Organization(**data)