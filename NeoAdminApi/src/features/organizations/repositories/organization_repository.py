"""Organization repository for data access using neo-commons database service."""

from typing import List, Optional

from neo_commons.core.value_objects.identifiers import OrganizationId, UserId
from neo_commons.features.database.services import DatabaseService
from neo_commons.features.organizations.entities import Organization
class OrganizationRepository:
    """Organization repository implementation using neo-commons database service."""
    
    def __init__(self, database_service: DatabaseService):
        """Initialize repository with database service."""
        self.database_service = database_service
    
    async def create(self, organization: Organization) -> Organization:
        """Create new organization."""
        query = """
            INSERT INTO admin.organizations (
                id, name, slug, legal_name, tax_id, business_type, industry,
                company_size, website_url, primary_contact_id, address_line1,
                address_line2, city, state_province, postal_code, country_code,
                default_timezone, default_locale, default_currency, logo_url,
                brand_colors, is_active, verified_at, verification_documents
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                    $16, $17, $18, $19, $20, $21, $22, $23, $24)
            RETURNING *
        """
        
        async with self.database_service.get_connection("admin") as conn:
            row = await conn.fetchrow(
                query,
                organization.id.value, organization.name, organization.slug,
                organization.legal_name, organization.tax_id, organization.business_type,
                organization.industry, organization.company_size, organization.website_url,
                organization.primary_contact_id, organization.address_line1,
                organization.address_line2, organization.city, organization.state_province,
                organization.postal_code, organization.country_code, organization.default_timezone,
                organization.default_locale, organization.default_currency, organization.logo_url,
                organization.brand_colors, organization.is_active, organization.verified_at,
                organization.verification_documents
            )
            
            return self._row_to_organization(row)
    
    async def get_by_id(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Get organization by ID."""
        query = """
            SELECT * FROM admin.organizations 
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        async with self.database_service.get_connection("admin") as conn:
            row = await conn.fetchrow(query, organization_id.value)
            return self._row_to_organization(row) if row else None
    
    async def get_by_name(self, name: str) -> Optional[Organization]:
        """Get organization by name."""
        query = """
            SELECT * FROM admin.organizations 
            WHERE name = $1 AND deleted_at IS NULL
        """
        
        async with self.database_service.get_connection("admin") as conn:
            row = await conn.fetchrow(query, name)
            return self._row_to_organization(row) if row else None
    
    async def update(self, organization: Organization) -> Organization:
        """Update organization."""
        query = """
            UPDATE admin.organizations SET
                name = $2, slug = $3, legal_name = $4, tax_id = $5, business_type = $6,
                industry = $7, company_size = $8, website_url = $9, primary_contact_id = $10,
                address_line1 = $11, address_line2 = $12, city = $13, state_province = $14,
                postal_code = $15, country_code = $16, default_timezone = $17,
                default_locale = $18, default_currency = $19, logo_url = $20,
                brand_colors = $21, is_active = $22, verified_at = $23,
                verification_documents = $24, updated_at = NOW()
            WHERE id = $1 AND deleted_at IS NULL
            RETURNING *
        """
        
        async with self.database_service.get_connection("admin") as conn:
            row = await conn.fetchrow(
                query,
                organization.id.value, organization.name, organization.slug,
                organization.legal_name, organization.tax_id, organization.business_type,
                organization.industry, organization.company_size, organization.website_url,
                organization.primary_contact_id, organization.address_line1,
                organization.address_line2, organization.city, organization.state_province,
                organization.postal_code, organization.country_code, organization.default_timezone,
                organization.default_locale, organization.default_currency, organization.logo_url,
                organization.brand_colors, organization.is_active, organization.verified_at,
                organization.verification_documents
            )
            
            if not row:
                raise ValueError(f"Organization {organization.id.value} not found or already deleted")
            
            return self._row_to_organization(row)
    
    async def delete(self, organization_id: OrganizationId) -> bool:
        """Delete organization (soft delete)."""
        query = """
            UPDATE admin.organizations SET
                deleted_at = NOW(),
                is_active = false,
                updated_at = NOW()
            WHERE id = $1 AND deleted_at IS NULL
        """
        
        async with self.database_service.get_connection("admin") as conn:
            result = await conn.execute(query, organization_id.value)
            return result == "UPDATE 1"
    
    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Organization]:
        """List organizations with pagination and filtering."""
        conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if active_only:
            conditions.append("is_active = true")
        
        if search:
            param_count += 1
            conditions.append(f"(name ILIKE ${param_count} OR slug ILIKE ${param_count} OR legal_name ILIKE ${param_count})")
            params.append(f"%{search}%")
        
        where_clause = " AND ".join(conditions)
        
        param_count += 1
        params.append(limit)
        param_count += 1
        params.append(skip)
        
        query = f"""
            SELECT * FROM admin.organizations
            WHERE {where_clause}
            ORDER BY name ASC
            LIMIT ${param_count - 1} OFFSET ${param_count}
        """
        
        async with self.database_service.get_connection("admin") as conn:
            rows = await conn.fetch(query, *params)
            return [self._row_to_organization(row) for row in rows]
    
    async def count_organizations(
        self,
        search: Optional[str] = None,
        active_only: bool = True,
    ) -> int:
        """Count organizations with filtering."""
        conditions = ["deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if active_only:
            conditions.append("is_active = true")
        
        if search:
            param_count += 1
            conditions.append(f"(name ILIKE ${param_count} OR slug ILIKE ${param_count} OR legal_name ILIKE ${param_count})")
            params.append(f"%{search}%")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
            SELECT COUNT(*) FROM admin.organizations
            WHERE {where_clause}
        """
        
        async with self.database_service.get_connection("admin") as conn:
            result = await conn.fetchval(query, *params)
            return result or 0
    
    async def list_organization_tenants(
        self,
        organization_id: OrganizationId,
        skip: int = 0,
        limit: int = 50,
    ) -> List[dict]:
        """List tenants for an organization."""
        query = """
            SELECT id, slug, name, description, schema_name, deployment_type,
                   environment, status, created_at, updated_at
            FROM admin.tenants
            WHERE organization_id = $1 AND deleted_at IS NULL
            ORDER BY name ASC
            LIMIT $2 OFFSET $3
        """
        
        async with self.database_service.get_connection("admin") as conn:
            rows = await conn.fetch(query, organization_id.value, limit, skip)
            return [dict(row) for row in rows]
    
    async def count_organization_tenants(self, organization_id: OrganizationId) -> int:
        """Count tenants for an organization."""
        query = """
            SELECT COUNT(*) FROM admin.tenants
            WHERE organization_id = $1 AND deleted_at IS NULL
        """
        
        async with self.database_service.get_connection("admin") as conn:
            result = await conn.fetchval(query, organization_id.value)
            return result or 0
    
    def _row_to_organization(self, row) -> Organization:
        """Convert database row to Organization entity."""
        from neo_commons.core.value_objects.identifiers import OrganizationId
        
        return Organization(
            id=OrganizationId(row["id"]),
            name=row["name"],
            slug=row["slug"],
            legal_name=row["legal_name"],
            tax_id=row["tax_id"],
            business_type=row["business_type"],
            industry=row["industry"],
            company_size=row["company_size"],
            website_url=row["website_url"],
            primary_contact_id=str(row["primary_contact_id"]) if row["primary_contact_id"] else None,
            address_line1=row["address_line1"],
            address_line2=row["address_line2"],
            city=row["city"],
            state_province=row["state_province"],
            postal_code=row["postal_code"],
            country_code=row["country_code"],
            default_timezone=row["default_timezone"],
            default_locale=row["default_locale"],
            default_currency=row["default_currency"],
            logo_url=row["logo_url"],
            brand_colors=row["brand_colors"] or {},
            is_active=row["is_active"],
            verified_at=row["verified_at"],
            verification_documents=row["verification_documents"] or [],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"]
        )