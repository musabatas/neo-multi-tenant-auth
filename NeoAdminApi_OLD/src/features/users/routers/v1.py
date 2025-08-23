"""
Platform Users API endpoints.
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
    UnauthorizedError
)
from neo_commons.auth.decorators import require_permission as require_permission_decorator
from src.features.auth.dependencies import require_permission, security
from src.features.users.services.user_service import PlatformUserService
from src.features.users.models.request import BulkUserOperation, PlatformUserCreate, PlatformUserUpdate
from src.features.users.models.response import BulkOperationResponse, PlatformUserResponse
from src.common.models import PaginatedResponse

router = NeoAPIRouter()


@router.get(
    "/",
    response_model=APIResponse[PaginatedResponse[PlatformUserResponse]],
    summary="List platform users",
    description="Get a paginated list of platform users"
)
@require_permission_decorator("users:list")
async def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by username, email, or name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_superadmin: Optional[bool] = Query(None, description="Filter by superadmin status"),
    current_user: dict = Depends(require_permission("users:list"))
) -> APIResponse[PaginatedResponse[PlatformUserResponse]]:
    """
    List all platform users with pagination and filtering.
    
    Requires platform-level permission to list users.
    """
    service = PlatformUserService()
    
    try:
        result = await service.list_users(
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
            is_superadmin=is_superadmin
        )
        
        return APIResponse.success_response(
            data=result,
            message="Users retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.get(
    "/{user_id}",
    response_model=APIResponse[PlatformUserResponse],
    summary="Get user by ID",
    description="Get details of a specific platform user"
)
@require_permission_decorator("users:read")
async def get_user(
    user_id: UUID,
    current_user: dict = Depends(require_permission("users:read"))
) -> APIResponse[PlatformUserResponse]:
    """
    Get details of a specific platform user.
    
    Requires platform-level permission to read users.
    """
    service = PlatformUserService()
    
    try:
        result = await service.get_user(str(user_id))
        
        return APIResponse.success_response(
            data=result,
            message="User retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.post(
    "/",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new platform user",
    description="Create a new platform user"
)
@require_permission_decorator("users:create")
async def create_user(
    user_data: PlatformUserCreate,
    current_user: dict = Depends(require_permission("users:create"))
) -> APIResponse[PlatformUserResponse]:
    """
    Create a new platform user.
    
    Requires platform-level permission to create users.
    """
    service = PlatformUserService()
    
    try:
        result = await service.create_user(
            user_data,
            created_by=current_user.get("id")
        )
        
        return APIResponse.success_response(
            data=result,
            message="User created successfully"
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
            detail="Failed to create user"
        )


@router.put(
    "/{user_id}",
    response_model=APIResponse[PlatformUserResponse],
    summary="Update user",
    description="Update an existing platform user"
)
@require_permission_decorator("users:update")
async def update_user(
    user_id: UUID,
    user_data: PlatformUserUpdate,
    current_user: dict = Depends(require_permission("users:update"))
) -> APIResponse[PlatformUserResponse]:
    """
    Update an existing platform user.
    
    Requires platform-level permission to update users.
    """
    service = PlatformUserService()
    
    try:
        result = await service.update_user(
            str(user_id),
            user_data,
            updated_by=current_user.get("id")
        )
        
        return APIResponse.success_response(
            data=result,
            message="User updated successfully"
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
            detail="Failed to update user"
        )


@router.delete(
    "/{user_id}",
    response_model=APIResponse[dict],
    summary="Delete user",
    description="Delete a platform user"
)
@require_permission_decorator("users:delete")
async def delete_user(
    user_id: UUID,
    current_user: dict = Depends(require_permission("users:delete"))
) -> APIResponse[dict]:
    """
    Delete a platform user.
    
    Requires platform-level permission to delete users.
    """
    service = PlatformUserService()
    
    try:
        await service.delete_user(
            str(user_id),
            deleted_by=current_user.get("id")
        )
        
        return APIResponse.success_response(
            data={"user_id": str(user_id), "deleted": True},
            message="User deleted successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.post(
    "/bulk",
    response_model=APIResponse[BulkOperationResponse],
    status_code=status.HTTP_200_OK,
    summary="Bulk operations on users",
    description="Perform bulk operations on multiple users"
)
@require_permission_decorator("users:bulk_operations")
async def bulk_operations(
    bulk_request: BulkUserOperation,
    current_user: dict = Depends(require_permission("users:bulk_operations"))
) -> APIResponse[BulkOperationResponse]:
    """
    Perform bulk operations on users.
    
    Supported operations: activate, deactivate, delete
    
    Requires platform-level permission to perform bulk operations.
    """
    service = PlatformUserService()
    
    try:
        result = await service.bulk_operation(
            bulk_request,
            performed_by=current_user.get("id")
        )
        
        return APIResponse.success_response(
            data=result,
            message=f"Bulk {bulk_request.operation} completed: {result.successful} successful, {result.failed} failed"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk operation"
        )


@router.post(
    "/sync-from-token",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Sync user from Keycloak token",
    description="Sync user data from Keycloak token (create if not exists)"
)
async def sync_user_from_token(
    create_if_not_exists: bool = Query(True, description="Create user if not exists"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[PlatformUserResponse]:
    """
    Sync user data from Keycloak token.
    
    This endpoint is used during authentication to sync user data
    from the authentication provider.
    """
    service = PlatformUserService()
    
    try:
        result = await service.sync_user_from_keycloak(
            credentials.credentials,
            create_if_not_exists=create_if_not_exists
        )
        
        return APIResponse.success_response(
            data=result,
            message="User synchronized successfully"
        )
    except UnauthorizedError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
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
            detail="Failed to synchronize user"
        )