"""
Organization management API endpoints.
"""

from typing import Optional
from uuid import UUID
from fastapi import Depends, Query, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.common.routers.base import NeoAPIRouter
from src.common.models.base import APIResponse, PaginationParams
from src.common.exceptions.base import (
    NotFoundError,
    ValidationError,
    ConflictError
)
from neo_commons.auth.decorators import require_permission
from src.features.auth.dependencies import security, CheckPermission

from ..models.request import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationFilter
)
from ..models.response import (
    OrganizationResponse,
    OrganizationListResponse
)
from ..services.organization_service import OrganizationService

router = NeoAPIRouter()


def get_organization_service() -> OrganizationService:
    """Get organization service instance using neo-commons dependency injection."""
    return OrganizationService()


@router.get(
    "/",
    response_model=APIResponse[OrganizationListResponse],
    status_code=status.HTTP_200_OK,
    summary="List organizations",
    description="List all organizations with optional filters and pagination"
)
@require_permission("organizations:list", scope="platform", description="List organizations")
async def list_organizations(
    # Filters
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in name, slug, legal_name"),
    country_code: Optional[str] = Query(None, pattern=r'^[A-Z]{2}$', description="Filter by country code"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    company_size: Optional[str] = Query(None, description="Filter by company size"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_verified: Optional[bool] = Query(None, description="Filter by verification status"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Auth
    current_user: dict = Depends(CheckPermission(["organizations:list"], scope="platform")),
    service: OrganizationService = Depends(get_organization_service)
) -> APIResponse[OrganizationListResponse]:
    """
    List organizations with optional filtering and pagination.
    
    Requires platform-level permission to list organizations.
    """
    
    # Build filters
    filters = OrganizationFilter(
        search=search,
        country_code=country_code,
        industry=industry,
        company_size=company_size,
        is_active=is_active,
        is_verified=is_verified
    )
    
    # Build pagination
    pagination = PaginationParams(page=page, page_size=page_size)
    
    try:
        result = await service.list_organizations(filters, pagination)
        
        return APIResponse.success_response(
            data=result,
            message="Organizations retrieved successfully"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        from loguru import logger
        logger.error(f"Failed to retrieve organizations: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve organizations: {str(e)}"
        )


@router.post(
    "/",
    response_model=APIResponse[OrganizationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization"
)
@require_permission("organizations:create", scope="platform", description="Create organizations")
async def create_organization(
    organization_data: OrganizationCreate,
    current_user: dict = Depends(CheckPermission(["organizations:create"], scope="platform")),
    service: OrganizationService = Depends(get_organization_service)
) -> APIResponse[OrganizationResponse]:
    """
    Create a new organization.
    
    Requires platform-level permission to create organizations.
    """
    
    try:
        result = await service.create_organization(
            organization_data,
            created_by=current_user.get("id")
        )
        
        return APIResponse.success_response(
            data=result,
            message="Organization created successfully"
        )
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization"
        )


@router.get(
    "/{organization_id}",
    response_model=APIResponse[OrganizationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get organization",
    description="Get organization details by ID"
)
@require_permission("organizations:read", scope="platform", description="View organization details")
async def get_organization(
    organization_id: UUID,
    current_user: dict = Depends(CheckPermission(["organizations:read"], scope="platform")),
    service: OrganizationService = Depends(get_organization_service)
) -> APIResponse[OrganizationResponse]:
    """
    Get organization details by ID.
    
    Requires platform-level permission to read organization details.
    """
    
    try:
        result = await service.get_organization(str(organization_id))
        
        return APIResponse.success_response(
            data=result,
            message="Organization retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )


@router.get(
    "/slug/{slug}",
    response_model=APIResponse[OrganizationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get organization by slug",
    description="Get organization details by slug"
)
@require_permission("organizations:read", scope="platform", description="View organization details")
async def get_organization_by_slug(
    slug: str,
    current_user: dict = Depends(CheckPermission(["organizations:read"], scope="platform")),
    service: OrganizationService = Depends(get_organization_service)
) -> APIResponse[OrganizationResponse]:
    """
    Get organization details by slug.
    
    Requires platform-level permission to read organization details.
    """
    
    try:
        result = await service.get_organization_by_slug(slug)
        
        return APIResponse.success_response(
            data=result,
            message="Organization retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )


@router.put(
    "/{organization_id}",
    response_model=APIResponse[OrganizationResponse],
    status_code=status.HTTP_200_OK,
    summary="Update organization",
    description="Update organization details"
)
@require_permission("organizations:update", scope="platform", description="Update organization details")
async def update_organization(
    organization_id: UUID,
    update_data: OrganizationUpdate,
    current_user: dict = Depends(CheckPermission(["organizations:update"], scope="platform")),
    service: OrganizationService = Depends(get_organization_service)
) -> APIResponse[OrganizationResponse]:
    """
    Update organization details.
    
    Requires platform-level permission to update organizations.
    """
    
    try:
        result = await service.update_organization(str(organization_id), update_data)
        
        return APIResponse.success_response(
            data=result,
            message="Organization updated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


@router.delete(
    "/{organization_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete organization",
    description="Soft delete an organization"
)
@require_permission("organizations:delete", scope="platform", description="Delete organizations")
async def delete_organization(
    organization_id: UUID,
    current_user: dict = Depends(CheckPermission(["organizations:delete"], scope="platform")),
    service: OrganizationService = Depends(get_organization_service)
) -> APIResponse[dict]:
    """
    Soft delete an organization.
    
    The organization will be marked as deleted but data will be retained
    for audit purposes. Organization must have no active tenants.
    
    Requires platform-level permission to delete organizations.
    """
    
    try:
        await service.delete_organization(str(organization_id))
        
        return APIResponse.success_response(
            data={"organization_id": str(organization_id), "deleted": True},
            message="Organization deleted successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization"
        )