"""
Permission management endpoints for platform administrators.
"""
from typing import List, Optional
from fastapi import Depends, Query, status
from src.common.routers.base import NeoAPIRouter
from fastapi.security import HTTPAuthorizationCredentials
from loguru import logger

from src.common.models.base import APIResponse
from src.common.exceptions.base import UnauthorizedError, NotFoundError
from ..decorators import require_permission
from ..dependencies import security
from ..services.permission_service import PermissionService
from ..models.response import PermissionResponse

router = NeoAPIRouter()


@router.get(
    "/permissions",
    response_model=APIResponse[List[PermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List all permissions",
    description="Get all available permissions in the system"
)
@require_permission("roles:read", scope="platform", description="View system permissions")
async def list_permissions(
    scope: Optional[str] = Query(None, description="Filter by scope (platform/tenant)"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[List[PermissionResponse]]:
    """
    List all available permissions with optional filtering.
    
    This endpoint requires the 'roles:read' permission.
    """
    permission_service = PermissionService()
    
    # Get all permissions
    permissions = await permission_service.get_all_permissions()
    
    # Filter permissions if requested
    if scope:
        permissions = [p for p in permissions if p.get('scope_level') == scope]
    if resource:
        permissions = [p for p in permissions if p.get('resource') == resource]
    
    # Map to response models
    response_permissions = [
        PermissionResponse(
            id=perm['id'],
            code=perm['code'],
            resource=perm['resource'],
            action=perm['action'],
            scope_level=perm['scope_level'],
            description=perm['description'],
            is_dangerous=perm.get('is_dangerous', False),
            requires_mfa=perm.get('requires_mfa', False),
            requires_approval=perm.get('requires_approval', False)
        )
        for perm in permissions
    ]
    
    return APIResponse.success_response(
        message="Permissions retrieved successfully",
        data=response_permissions
    )


@router.get(
    "/permissions/sync-status",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get permission sync status",
    description="Check the status of permission synchronization"
)
@require_permission(
    "platform:admin",
    scope="platform",
    description="Check permission sync status",
    is_dangerous=False
)
async def get_sync_status(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[dict]:
    """
    Get the current status of permission synchronization.
    
    This endpoint requires platform admin permissions.
    """
    # Get sync status from the database
    permission_service = PermissionService()
    
    # Get total permissions in database
    all_permissions = await permission_service.get_all_permissions()
    
    # Get summary stats
    status = {
        "total_permissions": len(all_permissions),
        "platform_permissions": len([p for p in all_permissions if p.get('scope_level') == 'platform']),
        "tenant_permissions": len([p for p in all_permissions if p.get('scope_level') == 'tenant']),
        "dangerous_permissions": len([p for p in all_permissions if p.get('is_dangerous')]),
        "mfa_required": len([p for p in all_permissions if p.get('requires_mfa')]),
        "last_sync": "Check application logs for last sync"
    }
    
    return APIResponse.success_response(
        message="Sync status retrieved",
        data=status
    )


@router.post(
    "/permissions/sync",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Trigger permission sync",
    description="Manually trigger permission synchronization from code to database"
)
@require_permission(
    "platform:admin",
    scope="platform",
    description="Trigger permission synchronization",
    is_dangerous=True,
    requires_mfa=True
)
async def trigger_sync(
    dry_run: bool = Query(False, description="Preview changes without applying"),
    force_update: bool = Query(False, description="Force update existing permissions"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[dict]:
    """
    Manually trigger permission synchronization.
    
    This endpoint requires platform admin permissions and MFA.
    """
    from src.app import create_app
    from ..services.permission_manager import PermissionSyncManager
    
    # Create app instance to scan
    app = create_app()
    
    # Run sync
    sync_manager = PermissionSyncManager()
    result = await sync_manager.sync_permissions(
        app=app,
        dry_run=dry_run,
        force_update=force_update
    )
    
    if result['success']:
        return APIResponse.success_response(
            message=f"Permission sync {'preview' if dry_run else 'completed'}: {result['stats']}",
            data=result
        )
    else:
        raise Exception(f"Permission sync failed: {result.get('error')}")


@router.get(
    "/check",
    response_model=APIResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Check user permissions",
    description="Check if the current user has specific permissions"
)
@require_permission("roles:read", scope="platform")
async def check_permissions(
    permissions: str = Query(..., description="Comma-separated list of permissions to check"),
    tenant_id: Optional[str] = Query(None, description="Tenant context for permission check"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> APIResponse[dict]:
    """
    Check if the current user has specific permissions.
    
    This endpoint requires the 'roles:read' permission.
    """
    from ..services.auth_service import AuthService
    
    auth_service = AuthService()
    
    # Get current user WITH CACHE - this already has all permissions
    user = await auth_service.get_current_user(credentials.credentials, use_cache=True)
    
    # Parse requested permissions
    permission_list = [p.strip() for p in permissions.split(',')]
    
    # Get user's permissions from the cached data (no extra DB queries!)
    user_permissions = user.get('permissions', [])
    is_superadmin = user.get('is_superadmin', False)
    
    # Check each permission against the cached list
    results = {}
    for perm in permission_list:
        if is_superadmin:
            # Superadmin has all permissions
            results[perm] = True
        else:
            # Check if permission is in user's permission list
            # Also check for wildcard permissions (e.g., "users:*" matches "users:read")
            resource = perm.split(':')[0] if ':' in perm else perm
            has_permission = (
                perm in user_permissions or 
                f"{resource}:*" in user_permissions
            )
            results[perm] = has_permission
    
    return APIResponse.success_response(
        message="Permission check completed",
        data={
            "user_id": user['id'],
            "tenant_id": tenant_id,
            "permissions": results
        }
    )