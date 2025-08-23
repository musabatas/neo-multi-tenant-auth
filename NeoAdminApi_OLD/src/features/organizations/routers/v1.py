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
from neo_commons.auth.decorators import require_permission as require_permission_decorator
from src.features.auth.dependencies import require_permission
from src.features.organizations.services.organization_service import OrganizationService

router = NeoAPIRouter()


@router.delete(
    "/{organization_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete organization",
    description="Soft delete an organization"
)
@require_permission_decorator("organizations:delete")
async def delete_organization(
    organization_id: UUID,
    current_user: dict = Depends(require_permission("organizations:delete")),
    service: OrganizationService = Depends(OrganizationService)
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