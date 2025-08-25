"""Organization router with comprehensive CRUD operations.

Provides ready-to-use FastAPI router for organization management
that services can include directly without duplicating routing logic.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from fastapi.responses import JSONResponse, Response

from ....features.pagination.entities import OffsetPaginationRequest, SortField, SortOrder

from ....core.value_objects import OrganizationId
from ....core.exceptions import (
    EntityNotFoundError,
    EntityAlreadyExistsError,
    ValidationError,
    DatabaseError
)
from ..models.requests import (
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    OrganizationSearchRequest,
    OrganizationMetadataRequest
)
from ..models.responses import (
    OrganizationResponse,
    OrganizationSummaryResponse,
    OrganizationListResponse,
    OrganizationSearchResponse,
    OrganizationMetadataResponse
)
from ..services.organization_service import OrganizationService
from .dependencies import get_organization_service


# Create router with consistent tags and prefix
router = APIRouter(
    prefix="/organizations",
    tags=["Organizations"],
    responses={
        404: {"description": "Organization not found"},
        409: {"description": "Organization already exists"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization with comprehensive validation",
    responses={
        201: {"description": "Organization created successfully"},
        409: {"description": "Organization with slug already exists"},
        422: {"description": "Invalid organization data"}
    }
)
async def create_organization(
    request: CreateOrganizationRequest,
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Create new organization."""
    try:
        # Convert request to service parameters
        create_params = request.model_dump(exclude_unset=True)
        
        # Create organization using service
        organization = await service.create_organization(**create_params)
        
        # Convert to response model
        return OrganizationResponse.from_entity(organization)
        
    except EntityAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}"
        )


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Get organization by ID",
    description="Retrieve organization details by ID with caching support",
    responses={
        200: {"description": "Organization found"},
        404: {"description": "Organization not found"}
    }
)
async def get_organization(
    organization_id: str = Path(..., description="Organization ID"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Get organization by ID."""
    try:
        org_id = OrganizationId(organization_id)
        organization = await service.get_by_id(org_id)
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {organization_id} not found"
            )
        
        return OrganizationResponse.from_entity(organization)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid organization ID format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve organization: {str(e)}"
        )


@router.get(
    "/slug/{slug}",
    response_model=OrganizationResponse,
    summary="Get organization by slug",
    description="Retrieve organization details by slug with caching support",
    responses={
        200: {"description": "Organization found"},
        404: {"description": "Organization not found"}
    }
)
async def get_organization_by_slug(
    slug: str = Path(..., description="Organization slug"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Get organization by slug."""
    try:
        organization = await service.get_by_slug(slug)
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with slug '{slug}' not found"
            )
        
        return OrganizationResponse.from_entity(organization)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve organization: {str(e)}"
        )


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Update organization",
    description="Update organization with change tracking and validation",
    responses={
        200: {"description": "Organization updated successfully"},
        404: {"description": "Organization not found"},
        422: {"description": "Invalid update data"}
    }
)
async def update_organization(
    organization_id: str = Path(..., description="Organization ID"),
    request: UpdateOrganizationRequest = None,
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Update organization."""
    try:
        org_id = OrganizationId(organization_id)
        
        # Get existing organization
        organization = await service.get_by_id(org_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {organization_id} not found"
            )
        
        # Apply updates from request
        if request:
            update_data = request.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(organization, field):
                    setattr(organization, field, value)
        
        # Update organization using service
        updated_organization = await service.update_organization(organization, update_data if request else None)
        
        return OrganizationResponse.from_entity(updated_organization)
        
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        )


@router.delete(
    "/{organization_id}",
    summary="Delete organization",
    description="Delete organization (soft delete by default)",
    responses={
        200: {"description": "Organization deleted successfully"},
        404: {"description": "Organization not found"}
    }
)
async def delete_organization(
    organization_id: str = Path(..., description="Organization ID"),
    hard_delete: bool = Query(False, description="Perform hard delete instead of soft delete"),
    service: OrganizationService = Depends(get_organization_service)
):
    """Delete organization."""
    try:
        org_id = OrganizationId(organization_id)
        
        deleted_organization = await service.delete_organization(org_id, hard_delete=hard_delete)
        
        # Return success message for both soft and hard delete
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Organization successfully deleted"}
        )
        
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete organization: {str(e)}"
        )


@router.get(
    "/",
    response_model=OrganizationListResponse,
    summary="List organizations",
    description="List organizations with filtering and pagination support"
)
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    light: bool = Query(True, description="Return light data (summary) or full data"),
    active_only: bool = Query(True, description="Show only active organizations"),
    verified_only: bool = Query(False, description="Show only verified organizations"),
    industry: Optional[str] = Query(None, description="Filter by industry"),
    country_code: Optional[str] = Query(None, description="Filter by country code"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationListResponse:
    """List organizations with filtering and pagination."""
    try:
        # Helper function to convert organizations based on light parameter
        def convert_organizations(orgs: List):
            if light:
                return [OrganizationSummaryResponse.from_entity(org) for org in orgs]
            else:
                return [OrganizationResponse.from_entity(org) for org in orgs]
        # Use new standardized pagination system for the main case
        if not verified_only and not industry and not country_code:
            # Create pagination request with proper sorting
            pagination_request = OffsetPaginationRequest(
                page=page,
                per_page=per_page,
                sort_fields=[SortField(field="name", order=SortOrder.ASC)]
            )
            
            # Use standardized pagination service
            paginated_response = await service.list_paginated(pagination_request)
            
            # Convert based on light parameter
            org_responses = convert_organizations(paginated_response.items)
            
            return OrganizationListResponse(
                organizations=org_responses,
                total=paginated_response.total,
                page=paginated_response.page,
                per_page=paginated_response.per_page,
                has_next=paginated_response.has_next,
                has_prev=paginated_response.has_prev
            )
        
        # For filtered queries, use existing methods (these should also be paginated in future)
        # TODO: Implement database-level pagination for filtered queries
        if verified_only:
            organizations = await service.get_verified_organizations(per_page)
        elif industry:
            organizations = await service.get_by_industry(industry)
        elif country_code:
            organizations = await service.get_by_country(country_code)
        
        # Apply memory pagination for filtered queries (temporary solution)
        offset = (page - 1) * per_page
        paginated_orgs = organizations[offset:offset + per_page]
        
        # Convert based on light parameter
        org_responses = convert_organizations(paginated_orgs)
        
        return OrganizationListResponse(
            organizations=org_responses,
            total=len(organizations),
            page=page,
            per_page=per_page,
            has_next=(offset + per_page) < len(organizations),
            has_prev=page > 1
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list organizations: {str(e)}"
        )


@router.post(
    "/search",
    response_model=OrganizationSearchResponse,
    summary="Search organizations",
    description="Advanced organization search with filters and full-text search"
)
async def search_organizations(
    request: OrganizationSearchRequest,
    light: bool = Query(True, description="Return light data (summary) or full data"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationSearchResponse:
    """Search organizations with advanced filters."""
    try:
        import time
        start_time = time.time()
        
        # Helper function to convert organizations based on light parameter
        def convert_organizations_search(orgs: List):
            if light:
                return [OrganizationSummaryResponse.from_entity(org) for org in orgs]
            else:
                return [OrganizationResponse.from_entity(org) for org in orgs]
        
        # Perform search using service
        organizations = await service.search_organizations(
            query=request.query,
            filters=request.get_combined_filters(),
            limit=request.limit
        )
        
        # Calculate search duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Convert based on light parameter
        org_responses = convert_organizations_search(organizations)
        
        return OrganizationSearchResponse(
            organizations=org_responses,
            query=request.query,
            filters=request.filters or {},
            total=len(org_responses),
            took_ms=duration_ms
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post(
    "/{organization_id}/verify",
    response_model=OrganizationResponse,
    summary="Verify organization",
    description="Verify organization with required documents"
)
async def verify_organization(
    organization_id: str = Path(..., description="Organization ID"),
    documents: List[str] = None,
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Verify organization with documents."""
    try:
        org_id = OrganizationId(organization_id)
        
        organization = await service.verify_organization(
            org_id, 
            documents or []
        )
        
        return OrganizationResponse.from_entity(organization)
        
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify organization: {str(e)}"
        )


@router.post(
    "/{organization_id}/deactivate",
    response_model=OrganizationResponse,
    summary="Deactivate organization",
    description="Deactivate organization with optional reason"
)
async def deactivate_organization(
    organization_id: str = Path(..., description="Organization ID"),
    reason: Optional[str] = Query(None, description="Reason for deactivation"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Deactivate organization."""
    try:
        org_id = OrganizationId(organization_id)
        
        organization = await service.deactivate_organization(org_id, reason)
        
        return OrganizationResponse.from_entity(organization)
        
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate organization: {str(e)}"
        )


@router.post(
    "/{organization_id}/activate",
    response_model=OrganizationResponse,
    summary="Activate organization",
    description="Activate previously deactivated organization"
)
async def activate_organization(
    organization_id: str = Path(..., description="Organization ID"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """Activate organization."""
    try:
        org_id = OrganizationId(organization_id)
        
        organization = await service.activate_organization(org_id)
        
        return OrganizationResponse.from_entity(organization)
        
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate organization: {str(e)}"
        )


# Metadata operations
@router.get(
    "/{organization_id}/metadata",
    response_model=OrganizationMetadataResponse,
    summary="Get organization metadata",
    description="Retrieve organization metadata"
)
async def get_organization_metadata(
    organization_id: str = Path(..., description="Organization ID"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationMetadataResponse:
    """Get organization metadata."""
    try:
        org_id = OrganizationId(organization_id)
        
        metadata = await service.get_metadata(org_id)
        organization = await service.get_by_id(org_id)
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {organization_id} not found"
            )
        
        return OrganizationMetadataResponse(
            organization_id=organization_id,
            metadata=metadata,
            updated_at=organization.updated_at
        )
        
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metadata: {str(e)}"
        )


@router.put(
    "/{organization_id}/metadata",
    response_model=OrganizationMetadataResponse,
    summary="Update organization metadata",
    description="Update organization metadata with merge support"
)
async def update_organization_metadata(
    organization_id: str = Path(..., description="Organization ID"),
    request: OrganizationMetadataRequest = None,
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationMetadataResponse:
    """Update organization metadata."""
    try:
        org_id = OrganizationId(organization_id)
        
        if not request:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Metadata request body is required"
            )
        
        organization = await service.update_metadata(
            org_id,
            request.metadata,
            merge=request.merge
        )
        
        return OrganizationMetadataResponse(
            organization_id=organization_id,
            metadata=organization.metadata or {},
            updated_at=organization.updated_at
        )
        
    except EntityNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update metadata: {str(e)}"
        )


@router.post(
    "/search/metadata",
    response_model=OrganizationSearchResponse,
    summary="Search by metadata",
    description="Search organizations by metadata filters using JSONB operators"
)
async def search_organizations_by_metadata(
    metadata_filters: Dict[str, Any],
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    service: OrganizationService = Depends(get_organization_service)
) -> OrganizationSearchResponse:
    """Search organizations by metadata."""
    try:
        import time
        start_time = time.time()
        
        organizations = await service.search_by_metadata(
            metadata_filters,
            limit=limit,
            offset=offset
        )
        
        # Calculate search duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Convert to summary responses
        org_summaries = [
            OrganizationSummaryResponse.from_entity(org) 
            for org in organizations
        ]
        
        return OrganizationSearchResponse(
            organizations=org_summaries,
            query="metadata search",
            filters=metadata_filters,
            total=len(org_summaries),
            took_ms=duration_ms
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metadata search failed: {str(e)}"
        )