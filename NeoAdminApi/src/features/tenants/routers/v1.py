"""
Tenant management API endpoints.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import Depends, Query, status, HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.common.routers.base import NeoAPIRouter
from src.common.models.base import APIResponse, PaginationParams
from src.common.exceptions.base import (
    NotFoundError,
    ValidationError,
    ConflictError,
    BadRequestError
)
from src.features.auth.decorators import require_permission
from src.features.auth.dependencies import security, get_current_user, CheckPermission

from ..models.request import (
    TenantCreate,
    TenantUpdate,
    TenantFilter,
    TenantStatusUpdate,
    TenantProvisionRequest
)
from ..models.response import (
    TenantResponse,
    TenantListResponse,
    TenantProvisionResponse
)
from ..models.domain import TenantStatus, DeploymentType, EnvironmentType, AuthProvider
from ..services.tenant_service import TenantService

router = NeoAPIRouter()


@router.get(
    "/",
    response_model=APIResponse[TenantListResponse],
    status_code=status.HTTP_200_OK,
    summary="List tenants",
    description="List all tenants with optional filters and pagination"
)
@require_permission("tenants:list", scope="platform", description="List tenants")
async def list_tenants(
    # Filters
    organization_id: Optional[UUID] = Query(None, description="Filter by organization"),
    tenant_status: Optional[List[TenantStatus]] = Query(None, alias="status", description="Filter by status"),
    environment: Optional[EnvironmentType] = Query(None, description="Filter by environment"),
    region_id: Optional[UUID] = Query(None, description="Filter by region"),
    deployment_type: Optional[DeploymentType] = Query(None, description="Filter by deployment type"),
    external_auth_provider: Optional[AuthProvider] = Query(None, description="Filter by auth provider"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in name, slug, description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    has_custom_domain: Optional[bool] = Query(None, description="Filter by custom domain presence"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Auth
    current_user: dict = Depends(CheckPermission(["tenants:list"], scope="platform"))
) -> APIResponse[TenantListResponse]:
    """
    List tenants with optional filtering and pagination.
    
    Requires platform-level permission to list tenants.
    """
    service = TenantService()
    
    # Build filters
    filters = TenantFilter(
        organization_id=organization_id,
        status=tenant_status,
        environment=environment,
        region_id=region_id,
        deployment_type=deployment_type,
        external_auth_provider=external_auth_provider,
        search=search,
        is_active=is_active,
        has_custom_domain=has_custom_domain
    )
    
    # Build pagination
    pagination = PaginationParams(page=page, page_size=page_size)
    
    try:
        result = await service.list_tenants(filters, pagination)
        
        return APIResponse.success_response(
            data=result,
            message="Tenants retrieved successfully"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        from loguru import logger
        logger.error(f"Failed to retrieve tenants: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tenants: {str(e)}"
        )


@router.post(
    "/",
    response_model=APIResponse[TenantResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create tenant",
    description="Create a new tenant"
)
@require_permission("tenants:create", scope="platform", description="Create tenants")
async def create_tenant(
    tenant_data: TenantCreate,
    current_user: dict = Depends(CheckPermission(["tenants:create"], scope="platform"))
) -> APIResponse[TenantResponse]:
    """
    Create a new tenant.
    
    The tenant will be created in PENDING status and requires provisioning
    to become active.
    
    Requires platform-level permission to create tenants.
    """
    service = TenantService()
    
    try:
        result = await service.create_tenant(
            tenant_data,
            created_by=current_user.get("id")
        )
        
        return APIResponse.success_response(
            data=result,
            message="Tenant created successfully"
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
            detail="Failed to create tenant"
        )


@router.get(
    "/{tenant_id}",
    response_model=APIResponse[TenantResponse],
    status_code=status.HTTP_200_OK,
    summary="Get tenant",
    description="Get tenant details by ID"
)
@require_permission("tenants:read", scope="platform", description="View tenant details")
async def get_tenant(
    tenant_id: UUID,
    current_user: dict = Depends(CheckPermission(["tenants:read"], scope="platform"))
) -> APIResponse[TenantResponse]:
    """
    Get tenant details by ID.
    
    Requires platform-level permission to read tenant details.
    """
    service = TenantService()
    
    try:
        result = await service.get_tenant(str(tenant_id))
        
        return APIResponse.success_response(
            data=result,
            message="Tenant retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant"
        )


@router.get(
    "/slug/{slug}",
    response_model=APIResponse[TenantResponse],
    status_code=status.HTTP_200_OK,
    summary="Get tenant by slug",
    description="Get tenant details by slug"
)
@require_permission("tenants:read", scope="platform", description="View tenant details")
async def get_tenant_by_slug(
    slug: str,
    current_user: dict = Depends(CheckPermission(["tenants:read"], scope="platform"))
) -> APIResponse[TenantResponse]:
    """
    Get tenant details by slug.
    
    Requires platform-level permission to read tenant details.
    """
    service = TenantService()
    
    try:
        result = await service.get_tenant_by_slug(slug)
        
        return APIResponse.success_response(
            data=result,
            message="Tenant retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tenant"
        )


@router.put(
    "/{tenant_id}",
    response_model=APIResponse[TenantResponse],
    status_code=status.HTTP_200_OK,
    summary="Update tenant",
    description="Update tenant details"
)
@require_permission("tenants:update", scope="platform", description="Update tenant details")
async def update_tenant(
    tenant_id: UUID,
    update_data: TenantUpdate,
    current_user: dict = Depends(CheckPermission(["tenants:update"], scope="platform"))
) -> APIResponse[TenantResponse]:
    """
    Update tenant details.
    
    Only certain fields can be updated. Status changes should use the
    dedicated status update endpoint.
    
    Requires platform-level permission to update tenants.
    """
    service = TenantService()
    
    try:
        result = await service.update_tenant(str(tenant_id), update_data)
        
        return APIResponse.success_response(
            data=result,
            message="Tenant updated successfully"
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
            detail="Failed to update tenant"
        )


@router.post(
    "/{tenant_id}/status",
    response_model=APIResponse[TenantResponse],
    status_code=status.HTTP_200_OK,
    summary="Update tenant status",
    description="Update tenant status (activate, suspend, deactivate)"
)
@require_permission("tenants:update_status", scope="platform", description="Update tenant status")
async def update_tenant_status(
    tenant_id: UUID,
    status_update: TenantStatusUpdate,
    current_user: dict = Depends(CheckPermission(["tenants:update_status"], scope="platform"))
) -> APIResponse[TenantResponse]:
    """
    Update tenant status.
    
    Valid status transitions:
    - PENDING -> PROVISIONING, SUSPENDED, DELETED
    - PROVISIONING -> ACTIVE, PENDING, SUSPENDED, DELETED
    - ACTIVE -> SUSPENDED, DEACTIVATED, DELETED
    - SUSPENDED -> ACTIVE, DEACTIVATED, DELETED
    - DEACTIVATED -> ACTIVE, SUSPENDED, DELETED
    
    Note: Suspension is now allowed from any status except DELETED.
    
    Requires platform-level permission to update tenant status.
    """
    service = TenantService()
    
    try:
        result = await service.update_tenant_status(str(tenant_id), status_update)
        
        return APIResponse.success_response(
            data=result,
            message=f"Tenant status updated to {status_update.status}"
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
            detail="Failed to update tenant status"
        )


@router.delete(
    "/{tenant_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete tenant",
    description="Soft delete a tenant"
)
@require_permission("tenants:delete", scope="platform", description="Delete tenants")
async def delete_tenant(
    tenant_id: UUID,
    current_user: dict = Depends(CheckPermission(["tenants:delete"], scope="platform"))
) -> APIResponse[dict]:
    """
    Soft delete a tenant.
    
    The tenant will be marked as deleted but data will be retained
    for audit purposes.
    
    Requires platform-level permission to delete tenants.
    """
    service = TenantService()
    
    try:
        await service.delete_tenant(str(tenant_id))
        
        return APIResponse.success_response(
            data={"tenant_id": str(tenant_id), "deleted": True},
            message="Tenant deleted successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tenant"
        )


@router.post(
    "/{tenant_id}/provision",
    response_model=APIResponse[TenantProvisionResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Provision tenant",
    description="Provision a tenant with Keycloak realm and database schema"
)
@require_permission("tenants:provision", scope="platform", description="Provision tenants")
async def provision_tenant(
    tenant_id: UUID,
    provision_request: TenantProvisionRequest,
    current_user: dict = Depends(CheckPermission(["tenants:provision"], scope="platform"))
) -> APIResponse[TenantProvisionResponse]:
    """
    Provision a tenant with all required resources.
    
    This will:
    1. Create a Keycloak realm for the tenant
    2. Create database schema in the regional database
    3. Create initial admin user
    4. Send welcome email (optional)
    5. Create sample data (optional)
    
    The tenant must be in PENDING status to be provisioned.
    
    Requires platform-level permission to provision tenants.
    """
    service = TenantService()
    
    try:
        result = await service.provision_tenant(str(tenant_id), provision_request)
        
        return APIResponse.success_response(
            data=result,
            message="Tenant provisioning started"
        )
    except BadRequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to provision tenant: {str(e)}"
        )