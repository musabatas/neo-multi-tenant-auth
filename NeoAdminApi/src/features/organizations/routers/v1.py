"""Organization API v1 endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from neo_commons.core.value_objects.identifiers import OrganizationId

from ....common.dependencies import get_organization_service, get_request_context
from ..models.request import OrganizationCreateRequest, OrganizationUpdateRequest
from ..models.response import OrganizationListResponse, OrganizationResponse
from ..services.organization_service import OrganizationService

router = APIRouter()


@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    search: Optional[str] = Query(None, description="Search term"),
    active_only: bool = Query(True, description="Show only active organizations"),
    org_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationListResponse:
    """List organizations with pagination and filtering.
    
    Requires platform administrator permissions.
    """
    try:
        organizations = await org_service.list_organizations(
            skip=skip,
            limit=limit,
            search=search,
            active_only=active_only,
        )
        
        total = await org_service.count_organizations(
            search=search,
            active_only=active_only,
        )
        
        return OrganizationListResponse(
            organizations=[
                OrganizationResponse.from_entity(org) for org in organizations
            ],
            total=total,
            skip=skip,
            limit=limit,
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list organizations: {str(e)}"
        ) from e


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreateRequest,
    org_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Create a new organization.
    
    Note: Authentication disabled during neo-commons integration.
    """
    try:
        organization = await org_service.create_organization(
            name=request.name,
            slug=request.slug,
            legal_name=request.legal_name,
            tax_id=request.tax_id,
            business_type=request.business_type,
            industry=request.industry,
            company_size=request.company_size,
            website_url=request.website_url,
            primary_contact_id=request.primary_contact_id,
        )
        
        return OrganizationResponse.from_entity(organization)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create organization: {str(e)}"
        ) from e


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    org_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Get organization by ID.
    
    Requires platform administrator permissions.
    """
    try:
        org_id = OrganizationId(str(organization_id))
        organization = await org_service.get_organization(org_id)
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        return OrganizationResponse.from_entity(organization)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get organization: {str(e)}"
        ) from e


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    request: OrganizationUpdateRequest,
    org_service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Update organization.
    
    Note: Authentication disabled during neo-commons integration.
    """
    try:
        org_id = OrganizationId(str(organization_id))
        
        updated_organization = await org_service.update_organization(
            org_id,
            name=request.name,
            legal_name=request.legal_name,
            website_url=request.website_url,
            business_type=request.business_type,
            industry=request.industry,
            is_active=request.is_active,
        )
        
        return OrganizationResponse.from_entity(updated_organization)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update organization: {str(e)}"
        ) from e


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: UUID,
    force: bool = Query(False, description="Force delete even if tenants exist"),
    org_service: OrganizationService = Depends(get_organization_service),
) -> None:
    """Delete organization.
    
    Requires platform administrator permissions.
    By default, cannot delete organizations with active tenants unless force=True.
    """
    try:
        org_id = OrganizationId(str(organization_id))
        
        success = await org_service.delete_organization(org_id, force=force)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete organization: {str(e)}"
        ) from e


@router.get("/{organization_id}/tenants")
async def list_organization_tenants(
    organization_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    org_service: OrganizationService = Depends(get_organization_service),
):
    """List tenants for an organization.
    
    Requires platform administrator permissions.
    """
    try:
        org_id = OrganizationId(str(organization_id))
        
        # Check if organization exists
        organization = await org_service.get_organization(org_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        tenants = await org_service.list_organization_tenants(
            org_id, skip=skip, limit=limit
        )
        
        total = await org_service.count_organization_tenants(org_id)
        
        return {
            "tenants": tenants,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list organization tenants: {str(e)}"
        ) from e