"""
Service layer for organization management.
"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from loguru import logger

from src.common.exceptions.base import (
    NotFoundError, 
    ValidationError, 
    ConflictError
)
from src.common.models.base import PaginationParams
from src.common.services.base import BaseService
# Removed cache import - organizations are not critical performance endpoints
from src.common.utils.datetime import utc_now

from ..models.domain import Organization
from ..models.request import (
    OrganizationCreate, 
    OrganizationUpdate, 
    OrganizationFilter
)
from ..models.response import (
    OrganizationResponse,
    OrganizationListItem,
    OrganizationListResponse,
    OrganizationListSummary
)
from ..repositories.organization_repository import OrganizationRepository


class OrganizationService(BaseService):
    """Service for organization business logic."""
    
    def __init__(self):
        """Initialize organization service."""
        super().__init__()
        self.repository = OrganizationRepository()
        # Removed caching - organizations are administrative data, not performance-critical
    
    async def get_organization(self, organization_id: str) -> OrganizationResponse:
        """Get an organization by ID.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            OrganizationResponse with organization details
        """
        # Get from repository (no caching for admin operations)
        organization = await self.repository.get_by_id(organization_id)
        
        # Get statistics
        stats = await self.repository.get_organization_stats(organization_id)
        
        # Get contact info if available
        contact_info = None
        if organization.primary_contact_id:
            contact_info = await self.repository.get_contact_info(str(organization.primary_contact_id))
        
        # Build response
        response = OrganizationResponse.from_domain(
            organization,
            stats,
            contact_info
        )
        
        return response
    
    async def get_organization_by_slug(self, slug: str) -> OrganizationResponse:
        """Get an organization by slug.
        
        Args:
            slug: Organization slug
            
        Returns:
            OrganizationResponse with organization details
        """
        # Get from repository (no caching for admin operations)
        organization = await self.repository.get_by_slug(slug)
        
        # Get statistics
        stats = await self.repository.get_organization_stats(str(organization.id))
        
        # Get contact info if available
        contact_info = None
        if organization.primary_contact_id:
            contact_info = await self.repository.get_contact_info(str(organization.primary_contact_id))
        
        # Build response
        response = OrganizationResponse.from_domain(
            organization,
            stats,
            contact_info
        )
        
        return response
    
    async def list_organizations(
        self,
        filters: Optional[OrganizationFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> OrganizationListResponse:
        """List organizations with optional filters and pagination.
        
        Args:
            filters: Optional filters for organizations
            pagination: Optional pagination parameters
            
        Returns:
            OrganizationListResponse with organizations and metadata
        """
        if pagination is None:
            pagination = PaginationParams(page=1, page_size=20)
        
        # Validate pagination
        self.validate_pagination_params(pagination.page, pagination.page_size)
        
        # Get organizations from repository
        offset = (pagination.page - 1) * pagination.page_size
        organizations, total_count = await self.repository.list(
            filters=filters,
            limit=pagination.page_size,
            offset=offset
        )
        
        # Build list items
        items = []
        for org in organizations:
            # Get statistics
            stats = await self.repository.get_organization_stats(str(org.id))
            
            item = OrganizationListItem(
                id=org.id,
                name=org.name,
                slug=org.slug,
                industry=org.industry,
                country_code=org.country_code,
                is_active=org.is_active,
                is_verified=org.is_verified,
                tenant_count=stats['tenant_count'],
                user_count=stats['user_count'],
                created_at=org.created_at
            )
            items.append(item)
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page, 
            pagination.page_size, 
            total_count
        )
        
        return OrganizationListResponse(
            items=items,
            pagination=pagination_meta.model_dump()
        )
    
    async def create_organization(
        self, 
        organization_data: OrganizationCreate,
        created_by: Optional[str] = None
    ) -> OrganizationResponse:
        """Create a new organization.
        
        Args:
            organization_data: Organization creation data
            created_by: User ID who created the organization
            
        Returns:
            OrganizationResponse with created organization
        """
        # Validate organization data
        await self._validate_organization_create(organization_data)
        
        # Create organization in database
        organization = await self.repository.create(organization_data)
        
        # Get contact info if available
        contact_info = None
        if organization.primary_contact_id:
            contact_info = await self.repository.get_contact_info(str(organization.primary_contact_id))
        
        response = OrganizationResponse.from_domain(
            organization,
            {'tenant_count': 0, 'active_tenant_count': 0, 'user_count': 0},
            contact_info
        )
        
        logger.info(f"Created organization {organization.id} ({organization.slug})")
        
        return response
    
    async def update_organization(
        self,
        organization_id: str,
        update_data: OrganizationUpdate
    ) -> OrganizationResponse:
        """Update an organization.
        
        Args:
            organization_id: Organization ID to update
            update_data: Update data
            
        Returns:
            OrganizationResponse with updated organization
        """
        # Update organization
        organization = await self.repository.update(organization_id, update_data)
        
        # No cache invalidation needed (no caching)
        
        # Get statistics
        stats = await self.repository.get_organization_stats(organization_id)
        
        # Get contact info if available
        contact_info = None
        if organization.primary_contact_id:
            contact_info = await self.repository.get_contact_info(str(organization.primary_contact_id))
        
        response = OrganizationResponse.from_domain(
            organization,
            stats,
            contact_info
        )
        
        logger.info(f"Updated organization {organization_id}")
        
        return response
    
    async def delete_organization(self, organization_id: str) -> None:
        """Delete (deactivate) an organization.
        
        Args:
            organization_id: Organization ID to delete
        """
        # Check if organization has active tenants
        stats = await self.repository.get_organization_stats(organization_id)
        if stats['active_tenant_count'] > 0:
            raise ValidationError(
                message="Cannot delete organization with active tenants",
                errors=[{
                    "field": "organization_id",
                    "value": organization_id,
                    "requirement": "Organization must have no active tenants"
                }]
            )
        
        # Get organization for deletion
        organization = await self.repository.get_by_id(organization_id)
        
        # Soft delete
        await self.repository.delete(organization_id)
        
        # No cache invalidation needed (no caching)
        
        logger.info(f"Soft deleted organization {organization_id}")
    
    async def _validate_organization_create(self, organization_data: OrganizationCreate) -> None:
        """Validate organization creation data.
        
        Args:
            organization_data: Organization creation data
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        
        # Validate primary contact if specified
        if organization_data.primary_contact_id:
            contact_info = await self.repository.get_contact_info(str(organization_data.primary_contact_id))
            if not contact_info:
                errors.append({
                    "field": "primary_contact_id",
                    "value": str(organization_data.primary_contact_id),
                    "requirement": "Primary contact must exist"
                })
        
        if errors:
            raise ValidationError(
                message="Organization validation failed",
                errors=errors
            )
    
    async def _create_list_summary(self, organizations: List[Organization]) -> OrganizationListSummary:
        """Create summary statistics for organization list.
        
        Args:
            organizations: List of organizations
            
        Returns:
            OrganizationListSummary with statistics
        """
        by_country = {}
        by_industry = {}
        by_company_size = {}
        
        active_count = 0
        verified_count = 0
        
        for org in organizations:
            # Active count
            if org.is_active:
                active_count += 1
            
            # Verified count
            if org.is_verified:
                verified_count += 1
            
            # Country counts
            if org.country_code:
                by_country[org.country_code] = by_country.get(org.country_code, 0) + 1
            
            # Industry counts
            if org.industry:
                by_industry[org.industry] = by_industry.get(org.industry, 0) + 1
            
            # Company size counts
            if org.company_size:
                by_company_size[org.company_size] = by_company_size.get(org.company_size, 0) + 1
        
        return OrganizationListSummary(
            total_organizations=len(organizations),
            active_organizations=active_count,
            verified_organizations=verified_count,
            by_country=by_country,
            by_industry=by_industry,
            by_company_size=by_company_size,
            total_tenants=0,  # Would aggregate from all orgs
            total_users=0  # Would aggregate from all orgs
        )
    
    # Removed cache invalidation method - no caching for administrative operations