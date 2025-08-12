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
from src.features.auth.decorators import require_permission
from src.features.auth.dependencies import security, CheckPermission

from ..models.request import (
    PlatformUserCreate,
    PlatformUserUpdate,
    PlatformUserFilter,
    RoleAssignmentRequest,
    PermissionGrantRequest,
    UserStatusUpdate,
    UserPreferencesUpdate,
    BulkUserOperation,
    UserSearchRequest
)
from ..models.response import (
    PlatformUserResponse,
    PlatformUserListResponse,
    BulkOperationResponse,
    UserSearchResponse
)
from ..models.domain import AuthProvider
from ..services.user_service import PlatformUserService

router = NeoAPIRouter()


@router.get(
    "/",
    response_model=APIResponse[PlatformUserListResponse],
    status_code=status.HTTP_200_OK,
    summary="List platform users",
    description="List all platform users with optional filters and pagination"
)
@require_permission("users:list", scope="platform", description="List platform users")
async def list_users(
    # Filters
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in email, username, name"),
    email: Optional[str] = Query(None, description="Filter by email"),
    username: Optional[str] = Query(None, description="Filter by username"),
    external_auth_provider: Optional[AuthProvider] = Query(None, description="Filter by auth provider"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_superadmin: Optional[bool] = Query(None, description="Filter by superadmin status"),
    company: Optional[str] = Query(None, description="Filter by company"),
    department: Optional[str] = Query(None, description="Filter by department"),
    job_title: Optional[str] = Query(None, description="Filter by job title"),
    has_role: Optional[str] = Query(None, description="Filter by role code"),
    has_permission: Optional[str] = Query(None, description="Filter by permission code"),
    tenant_access: Optional[UUID] = Query(None, description="Filter by tenant access"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    # Auth
    current_user: dict = Depends(CheckPermission(["users:list"], scope="platform"))
) -> APIResponse[PlatformUserListResponse]:
    """
    List platform users with optional filtering and pagination.
    
    Requires platform-level permission to list users.
    """
    service = PlatformUserService()
    
    # Build filters
    filters = PlatformUserFilter(
        search=search,
        email=email,
        username=username,
        external_auth_provider=external_auth_provider,
        is_active=is_active,
        is_superadmin=is_superadmin,
        company=company,
        department=department,
        job_title=job_title,
        has_role=has_role,
        has_permission=has_permission,
        tenant_access=tenant_access
    )
    
    # Build pagination
    pagination = PaginationParams(page=page, page_size=page_size)
    
    try:
        result = await service.list_users(filters, pagination)
        
        return APIResponse.success_response(
            data=result,
            message="Users retrieved successfully"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        import traceback
        from loguru import logger
        logger.error(f"Failed to retrieve users: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve users: {str(e)}"
        )


@router.post(
    "/",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create platform user",
    description="Create a new platform user"
)
@require_permission("users:create", scope="platform", description="Create platform users")
async def create_user(
    user_data: PlatformUserCreate,
    current_user: dict = Depends(CheckPermission(["users:create"], scope="platform"))
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


@router.get(
    "/{user_id}",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get platform user",
    description="Get platform user details by ID"
)
@require_permission("users:read", scope="platform", description="View user details")
async def get_user(
    user_id: UUID,
    current_user: dict = Depends(CheckPermission(["users:read"], scope="platform"))
) -> APIResponse[PlatformUserResponse]:
    """
    Get platform user details by ID.
    
    Requires platform-level permission to read user details.
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
            detail="Failed to retrieve user"
        )


@router.get(
    "/email/{email}",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user by email",
    description="Get platform user details by email"
)
@require_permission("users:read", scope="platform", description="View user details")
async def get_user_by_email(
    email: str,
    current_user: dict = Depends(CheckPermission(["users:read"], scope="platform"))
) -> APIResponse[PlatformUserResponse]:
    """
    Get platform user details by email.
    
    Requires platform-level permission to read user details.
    """
    service = PlatformUserService()
    
    try:
        result = await service.get_user_by_email(email)
        
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
            detail="Failed to retrieve user"
        )


@router.get(
    "/username/{username}",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user by username",
    description="Get platform user details by username"
)
@require_permission("users:read", scope="platform", description="View user details")
async def get_user_by_username(
    username: str,
    current_user: dict = Depends(CheckPermission(["users:read"], scope="platform"))
) -> APIResponse[PlatformUserResponse]:
    """
    Get platform user details by username.
    
    Requires platform-level permission to read user details.
    """
    service = PlatformUserService()
    
    try:
        result = await service.get_user_by_username(username)
        
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
            detail="Failed to retrieve user"
        )


@router.put(
    "/{user_id}",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update platform user",
    description="Update platform user details"
)
@require_permission("users:update", scope="platform", description="Update user details")
async def update_user(
    user_id: UUID,
    update_data: PlatformUserUpdate,
    current_user: dict = Depends(CheckPermission(["users:update"], scope="platform"))
) -> APIResponse[PlatformUserResponse]:
    """
    Update platform user details.
    
    Requires platform-level permission to update users.
    """
    service = PlatformUserService()
    
    try:
        result = await service.update_user(str(user_id), update_data)
        
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


@router.post(
    "/{user_id}/status",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update user status",
    description="Update user active status (activate/deactivate)"
)
@require_permission("users:update_status", scope="platform", description="Update user status")
async def update_user_status(
    user_id: UUID,
    status_update: UserStatusUpdate,
    current_user: dict = Depends(CheckPermission(["users:update_status"], scope="platform"))
) -> APIResponse[PlatformUserResponse]:
    """
    Update user status (active/inactive).
    
    Requires platform-level permission to update user status.
    """
    service = PlatformUserService()
    
    try:
        result = await service.update_user_status(str(user_id), status_update)
        
        return APIResponse.success_response(
            data=result,
            message=f"User {'activated' if status_update.is_active else 'deactivated'} successfully"
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
            detail="Failed to update user status"
        )


@router.put(
    "/{user_id}/preferences",
    response_model=APIResponse[PlatformUserResponse],
    status_code=status.HTTP_200_OK,
    summary="Update user preferences",
    description="Update user preferences (timezone, locale, notifications, UI)"
)
@require_permission("users:update_preferences", scope="platform", description="Update user preferences")
async def update_user_preferences(
    user_id: UUID,
    preferences_update: UserPreferencesUpdate,
    current_user: dict = Depends(CheckPermission(["users:update_preferences"], scope="platform"))
) -> APIResponse[PlatformUserResponse]:
    """
    Update user preferences.
    
    Requires platform-level permission to update user preferences.
    """
    service = PlatformUserService()
    
    try:
        result = await service.update_user_preferences(str(user_id), preferences_update)
        
        return APIResponse.success_response(
            data=result,
            message="User preferences updated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user preferences"
        )


@router.delete(
    "/{user_id}",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Delete platform user",
    description="Soft delete a platform user"
)
@require_permission("users:delete", scope="platform", description="Delete users")
async def delete_user(
    user_id: UUID,
    current_user: dict = Depends(CheckPermission(["users:delete"], scope="platform"))
) -> APIResponse[dict]:
    """
    Soft delete a platform user.
    
    The user will be marked as deleted but data will be retained
    for audit purposes.
    
    Requires platform-level permission to delete users.
    """
    service = PlatformUserService()
    
    try:
        await service.delete_user(str(user_id))
        
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
    "/search",
    response_model=APIResponse[UserSearchResponse],
    status_code=status.HTTP_200_OK,
    summary="Search platform users",
    description="Advanced search for platform users"
)
@require_permission("users:search", scope="platform", description="Search users")
async def search_users(
    search_request: UserSearchRequest,
    current_user: dict = Depends(CheckPermission(["users:search"], scope="platform"))
) -> APIResponse[UserSearchResponse]:
    """
    Advanced search for platform users.
    
    Requires platform-level permission to search users.
    """
    service = PlatformUserService()
    
    try:
        result = await service.search_users(search_request)
        
        return APIResponse.success_response(
            data=result,
            message="Search completed successfully"
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search users"
        )


@router.post(
    "/bulk",
    response_model=APIResponse[BulkOperationResponse],
    status_code=status.HTTP_200_OK,
    summary="Bulk user operations",
    description="Perform bulk operations on multiple users (activate, deactivate, delete)"
)
@require_permission("users:bulk_operations", scope="platform", description="Perform bulk user operations")
async def bulk_user_operation(
    bulk_request: BulkUserOperation,
    current_user: dict = Depends(CheckPermission(["users:bulk_operations"], scope="platform"))
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