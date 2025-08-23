"""
API routes for region management.
"""

from typing import Optional
from fastapi import Depends, Query, HTTPException, status, Path
from src.common.routers.base import NeoAPIRouter

from src.common.models.base import APIResponse
from src.common.models import PaginationParams
from neo_commons.auth.decorators import require_permission as require_permission_decorator
from src.features.auth.dependencies import require_permission
from ..models.request import RegionFilter, RegionCreate, RegionUpdate
from ..models.response import RegionResponse, RegionListResponse
from ..services.region import RegionService
from ..repositories.region import RegionRepository

router = NeoAPIRouter()


def get_region_repository() -> RegionRepository:
    """Get region repository instance using neo-commons patterns."""
    return RegionRepository()

def get_region_service(
    repository: RegionRepository = Depends(get_region_repository)
) -> RegionService:
    """Get region service instance using neo-commons dependency injection."""
    return RegionService(repository)


@router.get(
    "",
    response_model=APIResponse[RegionListResponse],
    summary="List regions",
    description="Get a paginated list of regions with filtering"
)
@require_permission_decorator("regions:read", scope="platform", description="View regions")
async def list_regions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    accepts_new_tenants: Optional[bool] = Query(None, description="Filter by tenant acceptance"),
    gdpr_region: Optional[bool] = Query(None, description="Filter by GDPR compliance"),
    provider: Optional[str] = Query(None, description="Filter by cloud provider"),
    continent: Optional[str] = Query(None, description="Filter by continent"),
    search: Optional[str] = Query(None, description="Search in name, code, or display name"),
    service: RegionService = Depends(get_region_service),
    current_user: dict = Depends(require_permission("regions:read"))
) -> APIResponse[RegionListResponse]:
    """
    List all regions with pagination and filtering.
    
    This endpoint provides:
    - Paginated list of regions
    - Database count for each region
    - Summary statistics across all regions
    - Filtering by status, provider, continent
    - Search functionality
    """
    try:
        # Create filter object
        filters = RegionFilter(
            is_active=is_active,
            accepts_new_tenants=accepts_new_tenants,
            gdpr_region=gdpr_region,
            provider=provider,
            continent=continent,
            search=search
        )
        
        # Create pagination params
        pagination = PaginationParams(page=page, page_size=page_size)
        
        # Get regions
        result = await service.list_regions(
            filters=filters,
            pagination=pagination
        )
        
        return APIResponse.success_response(
            data=result,
            message=f"Retrieved {len(result.items)} regions"
        )
        
    except Exception as e:
        import traceback
        from loguru import logger
        logger.error(f"Error in list_regions: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/{region_id}",
    response_model=APIResponse[RegionResponse],
    summary="Get region details",
    description="Get detailed information about a specific region"
)
@require_permission_decorator("regions:read", scope="platform", description="View region details")
async def get_region(
    region_id: str = Path(..., description="Region ID"),
    service: RegionService = Depends(get_region_service),
    current_user: dict = Depends(require_permission("regions:read"))
) -> APIResponse[RegionResponse]:
    """
    Get detailed information about a specific region.
    
    This includes:
    - Region configuration
    - Location and compliance information
    - Capacity and tenant statistics
    - Infrastructure details
    - Cost information
    - Database connection count
    """
    try:
        result = await service.get_region(region_id)
        
        return APIResponse.success_response(
            data=result,
            message="Region retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/code/{code}",
    response_model=APIResponse[RegionResponse],
    summary="Get region by code",
    description="Get region details by region code"
)
@require_permission_decorator("regions:read", scope="platform", description="View region by code")
async def get_region_by_code(
    code: str = Path(..., description="Region code (e.g., us-east-1)"),
    service: RegionService = Depends(get_region_service),
    current_user: dict = Depends(require_permission("regions:read"))
) -> APIResponse[RegionResponse]:
    """
    Get region information by region code.
    
    This is useful when you have the region code but not the ID.
    """
    try:
        result = await service.get_region_by_code(code)
        
        return APIResponse.success_response(
            data=result,
            message="Region retrieved successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "",
    response_model=APIResponse[RegionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new region",
    description="Create a new region in the system"
)
@require_permission_decorator("regions:create", scope="platform", description="Create new regions", is_dangerous=True)
async def create_region(
    region_data: RegionCreate,
    service: RegionService = Depends(get_region_service),
    current_user: dict = Depends(require_permission("regions:create"))
) -> APIResponse[RegionResponse]:
    """
    Create a new region.
    
    This endpoint creates a new region with the specified configuration.
    The region will be created in an active state and ready to accept tenants.
    """
    try:
        result = await service.create_region(region_data)
        
        return APIResponse.success_response(
            data=result,
            message=f"Region '{region_data.name}' created successfully"
        )
        
    except Exception as e:
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        if "validation failed" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.put(
    "/{region_id}",
    response_model=APIResponse[RegionResponse],
    summary="Update a region",
    description="Update region configuration"
)
@require_permission_decorator("regions:update", scope="platform", description="Update regions", is_dangerous=True)
async def update_region(
    region_id: str = Path(..., description="Region ID"),
    region_data: RegionUpdate = ...,
    service: RegionService = Depends(get_region_service),
    current_user: dict = Depends(require_permission("regions:update"))
) -> APIResponse[RegionResponse]:
    """
    Update a region's configuration.
    
    This endpoint allows updating:
    - Display name
    - Active status
    - Tenant acceptance
    - Capacity limits
    - Priority
    - Compliance certifications
    - Cost settings
    """
    try:
        result = await service.update_region(region_id, region_data)
        
        return APIResponse.success_response(
            data=result,
            message=f"Region updated successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete(
    "/{region_id}",
    response_model=APIResponse,
    summary="Delete a region",
    description="Deactivate a region (soft delete)"
)
@require_permission_decorator("regions:delete", scope="platform", description="Delete regions", is_dangerous=True, requires_mfa=True)
async def delete_region(
    region_id: str = Path(..., description="Region ID"),
    service: RegionService = Depends(get_region_service),
    current_user: dict = Depends(require_permission("regions:delete"))
) -> APIResponse:
    """
    Delete (deactivate) a region.
    
    This performs a soft delete by:
    - Setting is_active to false
    - Setting accepts_new_tenants to false
    
    The region cannot be deleted if it has:
    - Active database connections
    - Existing tenants
    """
    try:
        await service.delete_region(region_id)
        
        return APIResponse.success_response(
            data=None,
            message=f"Region deactivated successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        if "cannot delete" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post(
    "/{region_id}/update-tenant-count",
    response_model=APIResponse,
    summary="Update tenant count",
    description="Recalculate and update tenant count for a region"
)
@require_permission_decorator("regions:update", scope="platform", description="Update region metrics")
async def update_tenant_count(
    region_id: str = Path(..., description="Region ID"),
    service: RegionService = Depends(get_region_service),
    current_user: dict = Depends(require_permission("regions:update"))
) -> APIResponse:
    """
    Update the tenant count and capacity percentage for a region.
    
    This recalculates:
    - current_tenants: Count of active tenants in the region
    - capacity_percentage: Based on current vs max tenants
    """
    try:
        repository = service.repository
        await repository.update_tenant_count(region_id)
        
        return APIResponse.success_response(
            data=None,
            message="Tenant count updated successfully"
        )
        
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )