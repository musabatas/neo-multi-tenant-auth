"""Tenant API v1 endpoints using neo-commons with admin database and schema."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from neo_commons.core.value_objects.identifiers import TenantId, OrganizationId
from neo_commons.features.tenants.models.requests import (
    TenantCreateRequest, TenantUpdateRequest, TenantProvisionRequest, TenantConfigRequest
)
from neo_commons.features.tenants.models.responses import (
    TenantResponse, TenantListResponse, TenantStatusResponse, 
    TenantConfigResponse, TenantHealthResponse
)
from ....common.dependencies import get_tenant_service, get_tenant_dependencies

logger = logging.getLogger(__name__)

# Create our own router following auth pattern
router = APIRouter()


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of items to return"),
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    status: Optional[str] = Query(None, description="Filter by tenant status"),
    search: Optional[str] = Query(None, description="Search in name or slug"),
    tenant_service = Depends(get_tenant_service),
) -> TenantListResponse:
    """List tenants with pagination and filtering."""
    try:
        org_id = OrganizationId(organization_id) if organization_id else None
        
        tenants = await tenant_service.list_tenants(
            skip=skip,
            limit=limit,
            organization_id=org_id,
            status=status,
            search=search
        )
        
        total = await tenant_service.count_tenants(
            organization_id=org_id,
            status=status,
            search=search
        )
        
        # Convert skip/limit to page/size for response model
        page = (skip // limit) + 1 if limit > 0 else 1
        size = limit
        
        return TenantListResponse(
            tenants=[TenantResponse.from_entity(tenant) for tenant in tenants],
            total=total,
            page=page,
            size=size
        )
        
    except Exception as e:
        logger.error(f"Failed to list tenants: {e}")
        raise HTTPException(
            status_code=500,  # Use integer instead of 500
            detail=f"Failed to list tenants: {str(e)}"
        )


@router.post("/", response_model=TenantResponse, status_code=201)
async def create_tenant(
    request: TenantCreateRequest,
    tenant_service = Depends(get_tenant_service),
) -> TenantResponse:
    """Create a new tenant."""
    try:
        tenant = await tenant_service.create_tenant(
            name=request.name,
            slug=request.slug,
            organization_id=OrganizationId(request.organization_id),
            subscription_plan_id=request.subscription_plan_id,
            database_name=request.database_name,
            schema_name=request.schema_name,
            region=request.region,
            settings=request.settings or {},
            metadata=request.metadata or {}
        )
        
        return TenantResponse.from_entity(tenant)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create tenant: {str(e)}"
        )


@router.get("/{tenant_id}/status", response_model=TenantStatusResponse)
async def get_tenant_status(
    tenant_id: UUID,
    tenant_service = Depends(get_tenant_service),
) -> TenantStatusResponse:
    """Get tenant status and health information."""
    try:
        status_info = await tenant_service.get_tenant_status(TenantId(str(tenant_id)))
        return status_info
        
    except Exception as e:
        logger.error(f"Failed to get tenant status {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tenant status: {str(e)}"
        )


@router.post("/{tenant_id}/provision", response_model=TenantResponse)
async def provision_tenant(
    tenant_id: UUID,
    request: TenantProvisionRequest,
    tenant_service = Depends(get_tenant_service),
) -> TenantResponse:
    """Provision tenant resources."""
    try:
        tenant = await tenant_service.provision_tenant(
            tenant_id=TenantId(str(tenant_id)),
            database_name=request.database_name,
            schema_name=request.schema_name,
            region=request.region
        )
        
        return TenantResponse.from_entity(tenant)
        
    except Exception as e:
        logger.error(f"Failed to provision tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to provision tenant: {str(e)}"
        )


@router.get("/by-slug/{slug}", response_model=TenantResponse)
async def get_tenant_by_slug(
    slug: str,
    tenant_dependencies = Depends(get_tenant_dependencies),
) -> TenantResponse:
    """Get tenant by slug."""
    try:
        tenant = await tenant_dependencies.get_tenant_by_slug(slug)
        return TenantResponse.from_entity(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tenant by slug '{slug}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tenant: {str(e)}"
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    tenant_dependencies = Depends(get_tenant_dependencies),
) -> TenantResponse:
    """Get tenant by ID."""
    try:
        tenant = await tenant_dependencies.get_tenant_by_id(TenantId(str(tenant_id)))
        return TenantResponse.from_entity(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tenant: {str(e)}"
        )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdateRequest,
    tenant_service = Depends(get_tenant_service),
) -> TenantResponse:
    """Update tenant."""
    try:
        tenant = await tenant_service.update_tenant(
            tenant_id=TenantId(str(tenant_id)),
            name=request.name,
            is_active=request.is_active,
            subscription_plan_id=request.subscription_plan_id,
            settings=request.settings,
            metadata=request.metadata
        )
        
        return TenantResponse.from_entity(tenant)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update tenant: {str(e)}"
        )


@router.delete("/{tenant_id}", status_code=204)
async def delete_tenant(
    tenant_id: UUID,
    force: bool = Query(False, description="Force delete even if data exists"),
    tenant_service = Depends(get_tenant_service),
) -> None:
    """Delete tenant."""
    try:
        await tenant_service.delete_tenant(TenantId(str(tenant_id)), force=force)
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to delete tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete tenant: {str(e)}"
        )