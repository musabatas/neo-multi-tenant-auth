"""
Service layer for region management.
"""

from typing import Optional, List, Dict, Any

from src.common.services.base import BaseService
from src.common.exceptions import NotFoundError, ValidationError
from src.common.models.pagination import PaginationParams, PaginationMetadata
from ..models.domain import Region
from ..models.request import RegionFilter, RegionCreate, RegionUpdate
from ..models.response import (
    RegionResponse, RegionListResponse, RegionListSummary
)
from ..repositories.region import RegionRepository


class RegionService(BaseService):
    """Service for region business logic."""
    
    def __init__(self, repository: RegionRepository):
        """Initialize region service.
        
        Args:
            repository: Region repository for database operations
        """
        super().__init__()
        self.repository = repository
    
    async def get_region(self, region_id: str) -> RegionResponse:
        """Get a region by ID.
        
        Args:
            region_id: Region ID
            
        Returns:
            RegionResponse with region details
        """
        region = await self.repository.get_by_id(region_id)
        database_count = await self.repository.get_database_count(region_id)
        return RegionResponse.from_domain(region, database_count)
    
    async def get_region_by_code(self, code: str) -> RegionResponse:
        """Get a region by code.
        
        Args:
            code: Region code
            
        Returns:
            RegionResponse with region details
        """
        region = await self.repository.get_by_code(code)
        database_count = await self.repository.get_database_count(region.id)
        return RegionResponse.from_domain(region, database_count)
    
    async def list_regions(
        self,
        filters: Optional[RegionFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> RegionListResponse:
        """List regions with optional filters and pagination.
        
        Args:
            filters: Optional filters for regions
            pagination: Optional pagination parameters
            
        Returns:
            RegionListResponse with regions and metadata
        """
        if pagination is None:
            pagination = PaginationParams(page=1, page_size=20)
        
        # Validate pagination
        self.validate_pagination_params(pagination.page, pagination.page_size)
        
        # Get regions from repository
        offset = (pagination.page - 1) * pagination.page_size
        regions, total_count = await self.repository.list(
            filters=filters,
            limit=pagination.page_size,
            offset=offset
        )
        
        # Build response with database counts
        response_items = []
        for region in regions:
            database_count = await self.repository.get_database_count(region.id)
            response_items.append(
                RegionResponse.from_domain(region, database_count)
            )
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page, pagination.page_size, total_count
        )
        
        return RegionListResponse(
            items=response_items,
            pagination=pagination_meta
        )
    
    async def create_region(self, region_data: RegionCreate) -> RegionResponse:
        """Create a new region.
        
        Args:
            region_data: Region creation data
            
        Returns:
            RegionResponse with created region
        """
        # Validate region data
        self._validate_region_create(region_data)
        
        # Create region
        region = await self.repository.create(region_data)
        
        return RegionResponse.from_domain(region, database_count=0)
    
    async def update_region(
        self,
        region_id: str,
        region_data: RegionUpdate
    ) -> RegionResponse:
        """Update a region.
        
        Args:
            region_id: Region ID to update
            region_data: Update data
            
        Returns:
            RegionResponse with updated region
        """
        # Update region
        region = await self.repository.update(region_id, region_data)
        
        # Update tenant count if capacity changed
        if region_data.max_tenants is not None:
            await self.repository.update_tenant_count(region_id)
        
        database_count = await self.repository.get_database_count(region_id)
        return RegionResponse.from_domain(region, database_count)
    
    async def delete_region(self, region_id: str) -> None:
        """Delete (deactivate) a region.
        
        Args:
            region_id: Region ID to delete
        """
        await self.repository.delete(region_id)
    
    async def _create_list_summary(self, regions: List[Region]) -> RegionListSummary:
        """Create summary statistics for region list.
        
        Args:
            regions: List of regions
            
        Returns:
            RegionListSummary with statistics
        """
        total_regions = len(regions)
        active_regions = sum(1 for r in regions if r.is_active)
        accepting_tenants = sum(1 for r in regions if r.accepts_new_tenants)
        gdpr_regions = sum(1 for r in regions if r.gdpr_region)
        
        # Group by provider
        by_provider: Dict[str, int] = {}
        for region in regions:
            provider = region.provider
            by_provider[provider] = by_provider.get(provider, 0) + 1
        
        # Group by continent
        by_continent: Dict[str, int] = {}
        for region in regions:
            continent = region.continent
            by_continent[continent] = by_continent.get(continent, 0) + 1
        
        # Calculate total capacity
        total_capacity = sum(
            r.max_tenants for r in regions 
            if r.max_tenants is not None
        )
        total_current_tenants = sum(r.current_tenants for r in regions)
        
        return RegionListSummary(
            total_regions=total_regions,
            active_regions=active_regions,
            accepting_tenants=accepting_tenants,
            gdpr_regions=gdpr_regions,
            by_provider=by_provider,
            by_continent=by_continent,
            total_capacity=total_capacity,
            total_current_tenants=total_current_tenants
        )
    
    def _validate_region_create(self, region_data: RegionCreate) -> None:
        """Validate region creation data.
        
        Args:
            region_data: Region creation data
            
        Raises:
            ValidationError: If validation fails
        """
        errors = []
        
        # Validate code format
        if not region_data.code or not region_data.code.replace("-", "").replace("_", "").isalnum():
            errors.append({
                "field": "code",
                "value": region_data.code,
                "requirement": "Code must contain only alphanumeric characters, hyphens, and underscores"
            })
        
        # Validate country code
        if len(region_data.country_code) != 2:
            errors.append({
                "field": "country_code",
                "value": region_data.country_code,
                "requirement": "Country code must be 2 characters (ISO 3166-1 alpha-2)"
            })
        
        # Validate max_tenants if provided
        if region_data.max_tenants is not None and region_data.max_tenants <= 0:
            errors.append({
                "field": "max_tenants",
                "value": region_data.max_tenants,
                "requirement": "Max tenants must be positive if specified"
            })
        
        if errors:
            raise ValidationError(
                message="Region validation failed",
                errors=errors
            )