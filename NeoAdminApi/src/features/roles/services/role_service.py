"""
Service layer for role management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import logging

from src.common.services.base import BaseService
from src.common.models.pagination import PaginationParams, PaginatedResponse
from src.common.exceptions.base import NotFoundError, ConflictError, ValidationError
from src.common.cache.client import get_cache
from src.features.auth.services.permission_service import PermissionService
from src.features.roles.repositories.role_repository import RoleRepository
from src.features.roles.models.domain import (
    PlatformRole, PlatformPermission, UserRoleAssignment
)
from src.features.roles.models.request import (
    RoleCreateRequest, RoleUpdateRequest, RoleAssignmentRequest,
    BulkRoleAssignmentRequest, RolePermissionUpdateRequest, RoleSearchFilter
)
from src.features.roles.models.response import (
    RoleResponse, RoleDetailResponse, PermissionResponse,
    RoleAssignmentResponse, BulkRoleOperationResponse
)

logger = logging.getLogger(__name__)


class RoleService(BaseService[PlatformRole]):
    """Service for managing platform roles."""
    
    def __init__(self):
        super().__init__()
        self.repository = RoleRepository()
        self.permission_service = PermissionService()
        self.cache = get_cache()
    
    async def list_roles(
        self,
        filters: Optional[RoleSearchFilter] = None,
        pagination: Optional[PaginationParams] = None
    ) -> PaginatedResponse[RoleResponse]:
        """List roles with optional filters and pagination."""
        
        # Default pagination
        if not pagination:
            pagination = PaginationParams(page=1, page_size=20)
        
        # Convert filters to dict
        filter_dict = {}
        if filters:
            filter_dict = filters.model_dump(exclude_unset=True)
        
        # Get roles from repository
        roles, total_count = await self.repository.list_roles(filter_dict, pagination)
        
        # Convert to response models
        items = [RoleResponse.from_domain(role) for role in roles]
        
        # Create pagination metadata
        pagination_meta = self.create_pagination_metadata(
            pagination.page,
            pagination.page_size,
            total_count
        )
        
        return PaginatedResponse(
            items=items,
            pagination=pagination_meta
        )
    
    async def get_role(self, role_id: int) -> RoleDetailResponse:
        """Get role by ID with permissions."""
        
        # Try cache first
        cache_key = f"role:{role_id}:detail"
        cached = await self.cache.get(cache_key)
        if cached:
            return RoleDetailResponse(**cached)
        
        # Get role from repository
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise NotFoundError(
                resource="Role",
                identifier=str(role_id)
            )
        
        # Get permissions
        permissions = await self.repository.get_role_permissions(role_id)
        
        # Create response
        response = RoleDetailResponse(
            id=role.id,
            code=role.code,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            role_level=role.role_level,
            priority=role.priority,
            is_system=role.is_system,
            is_default=role.is_default,
            max_assignees=role.max_assignees,
            tenant_scoped=role.tenant_scoped,
            requires_approval=role.requires_approval,
            role_config=role.role_config,
            metadata=role.metadata,
            permission_count=len(permissions),
            user_count=role.user_count,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=[PermissionResponse.from_domain(p) for p in permissions]
        )
        
        # Cache the result
        await self.cache.set(cache_key, response.model_dump(mode="json"), ttl=300)
        
        return response
    
    async def get_role_by_code(self, code: str) -> RoleResponse:
        """Get role by code."""
        
        role = await self.repository.get_by_code(code)
        if not role:
            raise NotFoundError(
                resource="Role",
                identifier=code
            )
        
        return RoleResponse.from_domain(role)
    
    async def create_role(self, request: RoleCreateRequest) -> RoleResponse:
        """Create a new role."""
        
        # Validate role doesn't exist
        existing = await self.repository.get_by_code(request.code)
        if existing:
            raise ConflictError(
                message=f"Role with code '{request.code}' already exists",
                conflicting_field="code",
                conflicting_value=request.code
            )
        
        # Create role
        role_data = request.model_dump()
        role = await self.repository.create(role_data)
        
        logger.info(f"Created role: {role.code} (ID: {role.id})")
        
        return RoleResponse.from_domain(role)
    
    async def update_role(
        self,
        role_id: int,
        request: RoleUpdateRequest
    ) -> RoleResponse:
        """Update a role."""
        
        # Check role exists
        existing = await self.repository.get_by_id(role_id)
        if not existing:
            raise NotFoundError(
                resource="Role",
                identifier=str(role_id)
            )
        
        # Don't allow updating system roles
        if existing.is_system:
            raise ValidationError(
                message="Cannot update system roles",
                errors=[{
                    "field": "is_system",
                    "message": "System roles cannot be modified"
                }]
            )
        
        # Update role
        updates = request.model_dump(exclude_unset=True)
        role = await self.repository.update(role_id, updates)
        
        # Invalidate cache
        await self.cache.delete(f"role:{role_id}:detail")
        
        logger.info(f"Updated role: {role.code} (ID: {role.id})")
        
        return RoleResponse.from_domain(role)
    
    async def delete_role(self, role_id: int) -> bool:
        """Delete a role."""
        
        # Check role exists
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise NotFoundError(
                resource="Role",
                identifier=str(role_id)
            )
        
        # Don't allow deleting system roles
        if role.is_system:
            raise ValidationError(
                message="Cannot delete system roles",
                errors=[{
                    "field": "is_system",
                    "message": "System roles cannot be deleted"
                }]
            )
        
        # Delete role
        success = await self.repository.delete(role_id)
        
        if success:
            # Invalidate cache
            await self.cache.delete(f"role:{role_id}:detail")
            logger.info(f"Deleted role: {role.code} (ID: {role_id})")
        
        return success
    
    async def update_role_permissions(
        self,
        role_id: int,
        request: RolePermissionUpdateRequest
    ) -> List[PermissionResponse]:
        """Update permissions for a role."""
        
        # Check role exists
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise NotFoundError(
                resource="Role",
                identifier=str(role_id)
            )
        
        # Update permissions
        permissions = await self.repository.update_role_permissions(
            role_id,
            request.permission_ids,
            request.replace
        )
        
        # Invalidate cache
        await self.cache.delete(f"role:{role_id}:detail")
        
        # Invalidate permission cache for all users with this role
        await self._invalidate_users_with_role(role_id)
        
        logger.info(f"Updated permissions for role: {role.code} (ID: {role_id})")
        
        return [PermissionResponse.from_domain(p) for p in permissions]
    
    async def assign_role_to_user(
        self,
        role_id: int,
        request: RoleAssignmentRequest,
        granted_by: Optional[UUID] = None
    ) -> RoleAssignmentResponse:
        """Assign a role to a user."""
        
        # Check role exists
        role = await self.repository.get_by_id(role_id)
        if not role:
            raise NotFoundError(
                resource="Role",
                identifier=str(role_id)
            )
        
        # Check max assignees limit
        if role.max_assignees and role.user_count >= role.max_assignees:
            raise ValidationError(
                message=f"Role '{role.code}' has reached maximum assignees limit",
                errors=[{
                    "field": "max_assignees",
                    "message": f"Maximum {role.max_assignees} users allowed"
                }]
            )
        
        # Assign role
        assignment = await self.repository.assign_role_to_user(
            user_id=request.user_id,
            role_id=role_id,
            granted_by=granted_by,
            granted_reason=request.reason,
            expires_at=request.expires_at,
            tenant_id=request.tenant_id
        )
        
        # Invalidate user's permission cache
        await self.permission_service.invalidate_user_permissions_cache(
            str(request.user_id),
            str(request.tenant_id) if request.tenant_id else None
        )
        
        logger.info(
            f"Assigned role {role.code} to user {request.user_id}"
            + (f" in tenant {request.tenant_id}" if request.tenant_id else "")
        )
        
        return RoleAssignmentResponse.from_domain(
            assignment,
            role_code=role.code,
            role_name=role.name,
            tenant_id=request.tenant_id
        )
    
    async def remove_role_from_user(
        self,
        role_id: int,
        user_id: UUID,
        tenant_id: Optional[UUID] = None
    ) -> bool:
        """Remove a role from a user."""
        
        # Remove role
        success = await self.repository.remove_role_from_user(
            user_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id
        )
        
        if success:
            # Invalidate user's permission cache
            await self.permission_service.invalidate_user_permissions_cache(
                str(user_id),
                str(tenant_id) if tenant_id else None
            )
            
            logger.info(
                f"Removed role ID {role_id} from user {user_id}"
                + (f" in tenant {tenant_id}" if tenant_id else "")
            )
        
        return success
    
    async def bulk_assign_roles(
        self,
        request: BulkRoleAssignmentRequest,
        granted_by: Optional[UUID] = None
    ) -> BulkRoleOperationResponse:
        """Bulk assign roles to users."""
        
        successful_items = []
        failed_items = []
        errors = []
        
        for user_id in request.user_ids:
            for role_id in request.role_ids:
                try:
                    # Check role exists
                    role = await self.repository.get_by_id(role_id)
                    if not role:
                        raise NotFoundError(
                            resource="Role",
                            identifier=str(role_id)
                        )
                    
                    # Assign role
                    assignment = await self.repository.assign_role_to_user(
                        user_id=user_id,
                        role_id=role_id,
                        granted_by=granted_by,
                        granted_reason=request.reason,
                        expires_at=request.expires_at,
                        tenant_id=request.tenant_id
                    )
                    
                    successful_items.append({
                        "user_id": str(user_id),
                        "role_id": role_id,
                        "role_code": role.code
                    })
                    
                except Exception as e:
                    failed_items.append({
                        "user_id": str(user_id),
                        "role_id": role_id
                    })
                    errors.append({
                        "user_id": str(user_id),
                        "role_id": role_id,
                        "error": str(e)
                    })
        
        # Invalidate cache for all affected users
        for user_id in request.user_ids:
            await self.permission_service.invalidate_user_permissions_cache(
                str(user_id),
                str(request.tenant_id) if request.tenant_id else None
            )
        
        total_requested = len(request.user_ids) * len(request.role_ids)
        
        return BulkRoleOperationResponse(
            operation="assign_roles",
            total_requested=total_requested,
            successful=len(successful_items),
            failed=len(failed_items),
            errors=errors,
            successful_items=successful_items,
            failed_items=failed_items
        )
    
    async def get_user_roles(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        include_inactive: bool = False
    ) -> List[RoleAssignmentResponse]:
        """Get all roles assigned to a user."""
        
        assignments = await self.repository.get_user_role_assignments(
            user_id=user_id,
            tenant_id=tenant_id,
            include_inactive=include_inactive
        )
        
        responses = []
        for assignment in assignments:
            # Get role details
            role = await self.repository.get_by_id(assignment.role_id)
            if role:
                responses.append(
                    RoleAssignmentResponse.from_domain(
                        assignment,
                        role_code=role.code,
                        role_name=role.name,
                        tenant_id=tenant_id
                    )
                )
        
        return responses
    
    async def _invalidate_users_with_role(self, role_id: int):
        """Invalidate permission cache for all users with a specific role."""
        
        # This would need to query all users with the role
        # For now, we'll rely on TTL-based cache expiration
        # In production, you might want to track user-role mappings
        # in a separate cache structure for efficient invalidation
        
        logger.info(f"Permission cache invalidation triggered for role ID {role_id}")
        
        # Could implement pattern-based cache deletion if Redis supports it
        # Example: await self.cache.delete_pattern(f"perms:*:role:{role_id}:*")