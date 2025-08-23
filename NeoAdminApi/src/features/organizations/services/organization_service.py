"""Organization service for business logic using neo-commons patterns."""

from typing import List, Optional

from neo_commons.core.value_objects.identifiers import OrganizationId, UserId
from neo_commons.features.organizations.entities import Organization
from ..repositories.organization_repository import OrganizationRepository


class OrganizationService:
    """Organization service implementation for admin operations."""
    
    def __init__(self, organization_repository: OrganizationRepository):
        """Initialize service with repository."""
        self.repository = organization_repository
    
    async def create_organization(
        self,
        name: str,
        slug: str,
        legal_name: Optional[str] = None,
        tax_id: Optional[str] = None,
        business_type: Optional[str] = None,
        industry: Optional[str] = None,
        company_size: Optional[str] = None,
        website_url: Optional[str] = None,
        primary_contact_id: Optional[str] = None,
    ) -> Organization:
        """Create new organization with validation."""
        # Check if organization name already exists
        existing = await self.repository.get_by_name(name)
        if existing:
            raise ValueError(f"Organization with name '{name}' already exists")
        
        # Create organization entity using proper neo-commons structure
        from neo_commons.features.organizations.entities import Organization
        from neo_commons.core.value_objects.identifiers import OrganizationId
        from neo_commons.utils.uuid import generate_uuid_v7
        
        organization = Organization(
            id=OrganizationId(generate_uuid_v7()),
            name=name,
            slug=slug,
            legal_name=legal_name,
            tax_id=tax_id,
            business_type=business_type,
            industry=industry,
            company_size=company_size,
            website_url=website_url,
            primary_contact_id=primary_contact_id,
            is_active=True,
        )
        
        # Save organization
        return await self.repository.create(organization)
    
    async def get_organization(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Get organization by ID."""
        return await self.repository.get_by_id(organization_id)
    
    async def update_organization(
        self,
        organization_id: OrganizationId,
        name: Optional[str] = None,
        legal_name: Optional[str] = None,
        website_url: Optional[str] = None,
        business_type: Optional[str] = None,
        industry: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Organization:
        """Update organization with validation."""
        organization = await self.repository.get_by_id(organization_id)
        if not organization:
            raise ValueError(f"Organization {organization_id.value} not found")
        
        # Update fields if provided - note: Organization entity is immutable dataclass
        # So we need to create a new instance with updated fields
        import dataclasses
        
        updates = {}
        if name is not None:
            updates['name'] = name
        if legal_name is not None:
            updates['legal_name'] = legal_name
        if website_url is not None:
            updates['website_url'] = website_url
        if business_type is not None:
            updates['business_type'] = business_type
        if industry is not None:
            updates['industry'] = industry
        if is_active is not None:
            updates['is_active'] = is_active
        
        # Create updated organization
        updated_organization = dataclasses.replace(organization, **updates)
        
        return await self.repository.update(updated_organization)
    
    async def delete_organization(
        self,
        organization_id: OrganizationId,
        force: bool = False,
    ) -> bool:
        """Delete organization with validation."""
        # Check if organization has tenants
        if not force:
            tenant_count = await self.repository.count_organization_tenants(organization_id)
            if tenant_count > 0:
                raise ValueError(
                    f"Cannot delete organization with {tenant_count} tenants. Use force=True to override."
                )
        
        return await self.repository.delete(organization_id)
    
    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Organization]:
        """List organizations with pagination and filtering."""
        return await self.repository.list_organizations(
            skip=skip,
            limit=limit,
            search=search,
            active_only=active_only,
        )
    
    async def count_organizations(
        self,
        search: Optional[str] = None,
        active_only: bool = True,
    ) -> int:
        """Count organizations with filtering."""
        return await self.repository.count_organizations(
            search=search,
            active_only=active_only,
        )
    
    async def list_organization_tenants(
        self,
        organization_id: OrganizationId,
        skip: int = 0,
        limit: int = 50,
    ) -> List[dict]:
        """List tenants for an organization."""
        return await self.repository.list_organization_tenants(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
        )
    
    async def count_organization_tenants(self, organization_id: OrganizationId) -> int:
        """Count tenants for an organization."""
        return await self.repository.count_organization_tenants(organization_id)