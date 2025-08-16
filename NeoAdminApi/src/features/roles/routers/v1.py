"""
API endpoints for role management.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials

from src.common.models.base import APIResponse
from src.common.models import PaginationParams, PaginatedResponse
from src.common.exceptions.base import NotFoundError, ConflictError, ValidationError
from src.features.auth.dependencies import security, CheckPermission
from neo_commons.auth.decorators import require_permission
from src.features.roles.dependencies import get_role_service
from src.features.roles.models.request import (
    RoleCreateRequest, RoleUpdateRequest, RoleAssignmentRequest,
    BulkRoleAssignmentRequest, RolePermissionUpdateRequest, RoleSearchFilter
)
from src.features.roles.models.response import (
    RoleResponse, RoleDetailResponse, PermissionResponse,
    RoleAssignmentResponse, BulkRoleOperationResponse
)

router = APIRouter()


@router.get(
    "/",
    response_model=APIResponse[PaginatedResponse[RoleResponse]],
    summary="List roles",
    description="List all platform roles with optional filters"
)
@require_permission("roles:list", scope="platform", description="List all roles")
async def list_roles(
    code: Optional[str] = Query(None, description="Filter by role code"),
    name: Optional[str] = Query(None, description="Filter by role name"),
    role_level: Optional[str] = Query(None, description="Filter by role level"),
    is_system: Optional[bool] = Query(None, description="Filter by system roles"),
    is_default: Optional[bool] = Query(None, description="Filter by default roles"),
    tenant_scoped: Optional[bool] = Query(None, description="Filter by tenant-scoped roles"),
    min_priority: Optional[int] = Query(None, ge=0, description="Minimum priority"),
    max_priority: Optional[int] = Query(None, le=1000, description="Maximum priority"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: dict = Depends(CheckPermission(["roles:list"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[PaginatedResponse[RoleResponse]]:
    """
    List all platform roles with optional filtering.
    
    Requires platform-level permission to list roles.
    """
    
    # Build filters
    filters = RoleSearchFilter(
        code=code,
        name=name,
        role_level=role_level,
        is_system=is_system,
        is_default=is_default,
        tenant_scoped=tenant_scoped,
        min_priority=min_priority,
        max_priority=max_priority
    )
    
    pagination = PaginationParams(page=page, page_size=page_size)
    
    try:
        result = await service.list_roles(filters, pagination)
        
        return APIResponse.success_response(
            data=result,
            message="Roles retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list roles"
        )


@router.get(
    "/{role_id}",
    response_model=APIResponse[RoleDetailResponse],
    summary="Get role details",
    description="Get detailed information about a specific role"
)
@require_permission("roles:read", scope="platform", description="Read role details")
async def get_role(
    role_id: int,
    current_user: dict = Depends(CheckPermission(["roles:read"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[RoleDetailResponse]:
    """
    Get detailed information about a role including its permissions.
    
    Requires platform-level permission to read roles.
    """
    
    try:
        role = await service.get_role(role_id)
        
        return APIResponse.success_response(
            data=role,
            message="Role retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role"
        )


@router.get(
    "/code/{code}",
    response_model=APIResponse[RoleResponse],
    summary="Get role by code",
    description="Get role information by its code"
)
@require_permission("roles:read", scope="platform", description="Read role by code")
async def get_role_by_code(
    code: str,
    current_user: dict = Depends(CheckPermission(["roles:read"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[RoleResponse]:
    """
    Get role information by its unique code.
    
    Requires platform-level permission to read roles.
    """
    
    try:
        role = await service.get_role_by_code(code)
        
        return APIResponse.success_response(
            data=role,
            message="Role retrieved successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get role"
        )


@router.post(
    "/",
    response_model=APIResponse[RoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new role",
    description="Create a new platform role"
)
@require_permission("roles:create", scope="platform", description="Create new roles")
async def create_role(
    request: RoleCreateRequest,
    current_user: dict = Depends(CheckPermission(["roles:create"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[RoleResponse]:
    """
    Create a new platform role.
    
    Requires platform-level permission to create roles.
    """
    
    try:
        role = await service.create_role(request)
        
        return APIResponse.success_response(
            data=role,
            message="Role created successfully"
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
            detail="Failed to create role"
        )


@router.put(
    "/{role_id}",
    response_model=APIResponse[RoleResponse],
    summary="Update a role",
    description="Update an existing platform role"
)
@require_permission("roles:update", scope="platform", description="Update roles")
async def update_role(
    role_id: int,
    request: RoleUpdateRequest,
    current_user: dict = Depends(CheckPermission(["roles:update"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[RoleResponse]:
    """
    Update an existing platform role.
    
    System roles cannot be modified.
    Requires platform-level permission to update roles.
    """
    
    try:
        role = await service.update_role(role_id, request)
        
        return APIResponse.success_response(
            data=role,
            message="Role updated successfully"
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
            detail="Failed to update role"
        )


@router.delete(
    "/{role_id}",
    response_model=APIResponse[dict],
    summary="Delete a role",
    description="Delete a platform role"
)
@require_permission("roles:delete", scope="platform", description="Delete roles")
async def delete_role(
    role_id: int,
    current_user: dict = Depends(CheckPermission(["roles:delete"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[dict]:
    """
    Delete a platform role.
    
    System roles cannot be deleted.
    Requires platform-level permission to delete roles.
    """
    
    try:
        success = await service.delete_role(role_id)
        
        return APIResponse.success_response(
            data={"role_id": role_id, "deleted": success},
            message="Role deleted successfully"
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
            detail="Failed to delete role"
        )


@router.put(
    "/{role_id}/permissions",
    response_model=APIResponse[List[PermissionResponse]],
    summary="Update role permissions",
    description="Update permissions assigned to a role"
)
@require_permission("roles:manage_permissions", scope="platform", description="Manage role permissions")
async def update_role_permissions(
    role_id: int,
    request: RolePermissionUpdateRequest,
    current_user: dict = Depends(CheckPermission(["roles:manage_permissions"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[List[PermissionResponse]]:
    """
    Update permissions assigned to a role.
    
    Can either replace all permissions or add to existing ones.
    Requires platform-level permission to manage role permissions.
    """
    
    try:
        permissions = await service.update_role_permissions(role_id, request)
        
        return APIResponse.success_response(
            data=permissions,
            message="Role permissions updated successfully"
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update role permissions"
        )


@router.post(
    "/{role_id}/assign",
    response_model=APIResponse[RoleAssignmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Assign role to user",
    description="Assign a role to a user"
)
@require_permission("roles:assign", scope="platform", description="Assign roles to users")
async def assign_role_to_user(
    role_id: int,
    request: RoleAssignmentRequest,
    current_user: dict = Depends(CheckPermission(["roles:assign"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[RoleAssignmentResponse]:
    """
    Assign a role to a user.
    
    Can be platform-level or tenant-specific assignment.
    Requires platform-level permission to assign roles.
    """
    
    try:
        assignment = await service.assign_role_to_user(
            role_id,
            request,
            granted_by=UUID(current_user.get("id"))
        )
        
        return APIResponse.success_response(
            data=assignment,
            message="Role assigned successfully"
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
            detail="Failed to assign role"
        )


@router.delete(
    "/{role_id}/users/{user_id}",
    response_model=APIResponse[dict],
    summary="Remove role from user",
    description="Remove a role assignment from a user"
)
@require_permission("roles:unassign", scope="platform", description="Remove role assignments")
async def remove_role_from_user(
    role_id: int,
    user_id: UUID,
    tenant_id: Optional[UUID] = Query(None, description="Tenant context for removal"),
    current_user: dict = Depends(CheckPermission(["roles:unassign"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[dict]:
    """
    Remove a role assignment from a user.
    
    Requires platform-level permission to unassign roles.
    """
    
    try:
        success = await service.remove_role_from_user(role_id, user_id, tenant_id)
        
        return APIResponse.success_response(
            data={
                "role_id": role_id,
                "user_id": str(user_id),
                "removed": success
            },
            message="Role removed successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove role"
        )


@router.post(
    "/bulk-assign",
    response_model=APIResponse[BulkRoleOperationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk assign roles",
    description="Assign multiple roles to multiple users"
)
@require_permission("roles:bulk_assign", scope="platform", description="Bulk role assignments")
async def bulk_assign_roles(
    request: BulkRoleAssignmentRequest,
    current_user: dict = Depends(CheckPermission(["roles:bulk_assign"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[BulkRoleOperationResponse]:
    """
    Assign multiple roles to multiple users in a single operation.
    
    Requires platform-level permission for bulk role assignments.
    """
    
    try:
        result = await service.bulk_assign_roles(
            request,
            granted_by=UUID(current_user.get("id"))
        )
        
        return APIResponse.success_response(
            data=result,
            message=f"Bulk assignment completed: {result.successful} successful, {result.failed} failed"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to perform bulk assignment"
        )


@router.get(
    "/users/{user_id}/roles",
    response_model=APIResponse[List[RoleAssignmentResponse]],
    summary="Get user roles",
    description="Get all roles assigned to a user"
)
@require_permission("roles:view_assignments", scope="platform", description="View role assignments")
async def get_user_roles(
    user_id: UUID,
    tenant_id: Optional[UUID] = Query(None, description="Filter by tenant context"),
    include_inactive: bool = Query(False, description="Include inactive assignments"),
    current_user: dict = Depends(CheckPermission(["roles:view_assignments"], scope="platform")),
    service = Depends(get_role_service)
) -> APIResponse[List[RoleAssignmentResponse]]:
    """
    Get all roles assigned to a specific user.
    
    Can optionally filter by tenant context and include inactive assignments.
    Requires platform-level permission to view role assignments.
    """
    
    try:
        roles = await service.get_user_roles(user_id, tenant_id, include_inactive)
        
        return APIResponse.success_response(
            data=roles,
            message="User roles retrieved successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user roles"
        )