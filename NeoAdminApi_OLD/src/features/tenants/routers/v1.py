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
from neo_commons.auth.decorators import require_permission as require_permission_decorator
from src.features.auth.dependencies import require_permission
from src.features.tenants.services.tenant_service import TenantService
from src.features.tenants.models.request import TenantProvisionRequest  
from src.features.tenants.models.response import TenantProvisionResponse

router = NeoAPIRouter()


@router.post(
    "/{tenant_id}/provision",
    response_model=APIResponse[TenantProvisionResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Provision tenant",
    description="Provision a tenant with all required resources"
)
@require_permission_decorator("tenants:provision")
async def provision_tenant(
    tenant_id: UUID,
    provision_request: TenantProvisionRequest,
    current_user: dict = Depends(require_permission("tenants:provision"))
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