"""Permission service for business logic orchestration.

Coordinates permission checking, role management, and caching operations
following clean architecture principles with protocol-based dependency injection.
"""

from typing import List, Optional, Set, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
import logging

from ....core.value_objects import UserId, TenantId
from ....core.exceptions import AuthorizationError
from ..entities import (
    Permission, PermissionCode, Role, RoleCode,
    PermissionChecker, PermissionRepository, RoleRepository, 
    UserRoleManager, PermissionCache
)


logger = logging.getLogger(__name__)


class PermissionService:
    """Service orchestrating permission operations with caching and validation."""
    
    def __init__(
        self,
        permission_repo: PermissionRepository,
        role_repo: RoleRepository,
        user_role_manager: UserRoleManager,
        permission_checker: PermissionChecker,
        cache: Optional[PermissionCache] = None
    ):
        self.permission_repo = permission_repo
        self.role_repo = role_repo
        self.user_role_manager = user_role_manager
        self.permission_checker = permission_checker
        self.cache = cache
    
    # Permission Management
    
    async def get_permission(self, permission_code: str, schema: str = "admin") -> Optional[Permission]:
        """Get a permission by code."""
        try:
            code = PermissionCode(permission_code)
            return await self.permission_repo.get_by_code(code, schema)
        except AuthorizationError as e:
            logger.warning(f"Invalid permission code format: {permission_code} - {e}")
            return None
    
    async def create_permission(
        self,
        code: str,
        description: Optional[str],
        resource: str,
        action: str,
        scope_level: str = "platform",
        is_dangerous: bool = False,
        requires_mfa: bool = False,
        requires_approval: bool = False,
        permission_config: Optional[Dict[str, Any]] = None,
        schema: str = "admin"
    ) -> Permission:
        """Create a new permission with validation."""
        try:
            permission_code = PermissionCode(code)
        except AuthorizationError as e:
            raise AuthorizationError(f"Invalid permission code: {e}")
        
        # Validate resource/action match code
        if permission_code.resource != resource:
            raise AuthorizationError(f"Resource mismatch: code says '{permission_code.resource}', provided '{resource}'")
        if permission_code.action != action:
            raise AuthorizationError(f"Action mismatch: code says '{permission_code.action}', provided '{action}'")
        
        # Check if permission already exists
        existing = await self.permission_repo.get_by_code(permission_code, schema)
        if existing:
            raise AuthorizationError(f"Permission already exists: {code}")
        
        permission = Permission(
            id=None,
            code=permission_code,
            description=description,
            resource=resource,
            action=action,
            scope_level=scope_level,
            is_dangerous=is_dangerous,
            requires_mfa=requires_mfa,
            requires_approval=requires_approval,
            permission_config=permission_config or {}
        )
        
        created = await self.permission_repo.create(permission, schema)
        logger.info(f"Created permission: {code} in schema {schema}")
        return created
    
    async def list_permissions(
        self,
        schema: str = "admin",
        resource_filter: Optional[str] = None,
        include_dangerous: bool = True
    ) -> List[Permission]:
        """List permissions with optional filtering."""
        permissions = await self.permission_repo.list_all(
            schema=schema,
            resource_filter=resource_filter
        )
        
        if not include_dangerous:
            permissions = [p for p in permissions if not p.is_dangerous]
        
        return permissions
    
    async def search_permissions(
        self,
        query: str,
        schema: str = "admin",
        limit: int = 100
    ) -> List[Permission]:
        """Search permissions by code or description."""
        return await self.permission_repo.search(query, schema, limit)
    
    # Role Management
    
    async def get_role(self, role_code: str, schema: str = "admin") -> Optional[Role]:
        """Get a role by code."""
        try:
            code = RoleCode(role_code)
            return await self.role_repo.get_by_code(code, schema)
        except AuthorizationError as e:
            logger.warning(f"Invalid role code format: {role_code} - {e}")
            return None
    
    async def get_role_with_permissions(self, role_code: str, schema: str = "admin") -> Optional[Role]:
        """Get a role with all its permissions loaded."""
        role = await self.get_role(role_code, schema)
        if not role:
            return None
        
        return await self.role_repo.get_with_permissions(role.id, schema)
    
    async def create_role(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        role_level: str = "member",
        scope_type: str = "global",
        priority: int = 100,
        is_default: bool = False,
        requires_approval: bool = False,
        max_assignees: Optional[int] = None,
        auto_expire_days: Optional[int] = None,
        role_config: Optional[Dict[str, Any]] = None,
        schema: str = "admin"
    ) -> Role:
        """Create a new role with validation."""
        try:
            role_code = RoleCode(code)
        except AuthorizationError as e:
            raise AuthorizationError(f"Invalid role code: {e}")
        
        # Check if role already exists
        existing = await self.role_repo.get_by_code(role_code, schema)
        if existing:
            raise AuthorizationError(f"Role already exists: {code}")
        
        role = Role(
            id=None,
            code=role_code,
            name=name,
            description=description,
            display_name=name,
            role_level=role_level,
            scope_type=scope_type,
            priority=priority,
            is_default=is_default,
            requires_approval=requires_approval,
            max_assignees=max_assignees,
            auto_expire_days=auto_expire_days,
            role_config=role_config or {}
        )
        
        created = await self.role_repo.create(role, schema)
        logger.info(f"Created role: {code} in schema {schema}")
        return created
    
    async def list_roles(
        self,
        schema: str = "admin",
        level_filter: Optional[str] = None,
        scope_filter: Optional[str] = None,
        include_system: bool = True
    ) -> List[Role]:
        """List roles with optional filtering."""
        roles = await self.role_repo.list_all(
            schema=schema,
            level_filter=level_filter,
            scope_filter=scope_filter
        )
        
        if not include_system:
            roles = [r for r in roles if not r.is_system]
        
        return roles
    
    async def assign_permission_to_role(
        self,
        role_code: str,
        permission_code: str,
        granted_by: Optional[UUID] = None,
        granted_reason: Optional[str] = None,
        schema: str = "admin"
    ) -> bool:
        """Assign a permission to a role."""
        role = await self.get_role(role_code, schema)
        if not role:
            raise AuthorizationError(f"Role not found: {role_code}")
        
        permission = await self.get_permission(permission_code, schema)
        if not permission:
            raise AuthorizationError(f"Permission not found: {permission_code}")
        
        success = await self.role_repo.add_permission(
            role.id, permission.id, granted_by, granted_reason, schema
        )
        
        if success:
            # Update role permissions cache
            await self.role_repo.update_permissions_cache(role.id, schema)
            
            # Invalidate user permission caches for this role
            if self.cache:
                await self.cache.invalidate_role_permissions(role.id)
            
            logger.info(f"Assigned permission {permission_code} to role {role_code}")
        
        return success
    
    async def remove_permission_from_role(
        self,
        role_code: str,
        permission_code: str,
        schema: str = "admin"
    ) -> bool:
        """Remove a permission from a role."""
        role = await self.get_role(role_code, schema)
        if not role:
            raise AuthorizationError(f"Role not found: {role_code}")
        
        permission = await self.get_permission(permission_code, schema)
        if not permission:
            raise AuthorizationError(f"Permission not found: {permission_code}")
        
        success = await self.role_repo.remove_permission(role.id, permission.id, schema)
        
        if success:
            # Update role permissions cache
            await self.role_repo.update_permissions_cache(role.id, schema)
            
            # Invalidate user permission caches for this role
            if self.cache:
                await self.cache.invalidate_role_permissions(role.id)
            
            logger.info(f"Removed permission {permission_code} from role {role_code}")
        
        return success
    
    # User Role Assignment
    
    async def assign_role_to_user(
        self,
        user_id: UUID,
        role_code: str,
        scope_type: str = "global",
        scope_id: Optional[UUID] = None,
        granted_by: Optional[UUID] = None,
        granted_reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        schema: str = "admin"
    ) -> bool:
        """Assign a role to a user with validation."""
        role = await self.get_role(role_code, schema)
        if not role:
            raise AuthorizationError(f"Role not found: {role_code}")
        
        if not role.is_assignable():
            raise AuthorizationError(f"Role is not assignable: {role_code}")
        
        # Check approval requirement
        if role.requires_approval and not granted_by:
            raise AuthorizationError(f"Role {role_code} requires approval but no granted_by provided")
        
        # Check max assignees
        if role.max_assignees:
            current_assignees = await self.user_role_manager.get_role_assignees(
                role.id, schema, scope_id
            )
            if not role.can_be_assigned_to_user_count(len(current_assignees)):
                raise AuthorizationError(f"Role {role_code} has reached maximum assignees ({role.max_assignees})")
        
        # Set expiration if role has auto-expire
        if not expires_at and role.auto_expire_days:
            expires_at = datetime.utcnow() + timedelta(days=role.auto_expire_days)
        
        success = await self.user_role_manager.assign_role(
            user_id, role.id, scope_type, scope_id,
            granted_by, granted_reason, expires_at, schema
        )
        
        if success:
            # Invalidate user permission cache
            if self.cache:
                await self.cache.invalidate_user_permissions(user_id, scope_id, scope_id)
            
            logger.info(f"Assigned role {role_code} to user {user_id}")
        
        return success
    
    async def revoke_role_from_user(
        self,
        user_id: UUID,
        role_code: str,
        scope_id: Optional[UUID] = None,
        schema: str = "admin"
    ) -> bool:
        """Revoke a role from a user."""
        role = await self.get_role(role_code, schema)
        if not role:
            raise AuthorizationError(f"Role not found: {role_code}")
        
        success = await self.user_role_manager.revoke_role(user_id, role.id, scope_id, schema)
        
        if success:
            # Invalidate user permission cache
            if self.cache:
                await self.cache.invalidate_user_permissions(user_id, scope_id, scope_id)
            
            logger.info(f"Revoked role {role_code} from user {user_id}")
        
        return success
    
    # Permission Checking
    
    async def check_permission(
        self,
        user_id: UserId,
        permission_code: str,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has a specific permission with caching."""
        return await self.permission_checker.has_permission(
            user_id, permission_code, tenant_id, scope_id
        )
    
    async def check_any_permission(
        self,
        user_id: UserId,
        permission_codes: List[str],
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has any of the specified permissions."""
        return await self.permission_checker.has_any_permission(
            user_id, permission_codes, tenant_id, scope_id
        )
    
    async def check_all_permissions(
        self,
        user_id: UserId,
        permission_codes: List[str],
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has all of the specified permissions."""
        return await self.permission_checker.has_all_permissions(
            user_id, permission_codes, tenant_id, scope_id
        )
    
    async def get_user_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> Set[str]:
        """Get all permission codes for a user."""
        return await self.permission_checker.get_user_permissions(
            user_id, tenant_id, scope_id
        )
    
    async def get_user_roles_with_permissions(
        self,
        user_id: UUID,
        schema: str = "admin",
        scope_type: Optional[str] = None,
        scope_id: Optional[UUID] = None
    ) -> List[Tuple[Role, Dict[str, Any]]]:
        """Get all roles assigned to a user with their permissions."""
        return await self.user_role_manager.get_user_roles(
            user_id, schema, scope_type, scope_id
        )
    
    # Cache Management
    
    async def invalidate_user_cache(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Invalidate permission cache for a specific user."""
        if not self.cache:
            return False
        
        return await self.cache.invalidate_user_permissions(user_id, tenant_id, scope_id)
    
    async def invalidate_role_cache(self, role_id: int) -> bool:
        """Invalidate permission cache for all users with a specific role."""
        if not self.cache:
            return False
        
        return await self.cache.invalidate_role_permissions(role_id)
    
    async def warm_user_cache(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Pre-load user permissions into cache."""
        if not self.cache:
            return False
        
        try:
            permissions = await self.get_user_permissions(user_id, tenant_id, scope_id)
            return await self.cache.set_user_permissions(
                user_id, permissions, tenant_id, scope_id
            )
        except Exception as e:
            logger.error(f"Failed to warm cache for user {user_id}: {e}")
            return False
    
    # Maintenance Operations
    
    async def cleanup_expired_assignments(self, schema: str = "admin") -> int:
        """Clean up expired role and permission assignments."""
        count = await self.user_role_manager.cleanup_expired_assignments(schema)
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired assignments in schema {schema}")
            
            # Clear all permission caches since we don't know which users were affected
            if self.cache:
                await self.cache.clear_all()
        
        return count
    
    async def refresh_all_role_caches(self, schema: str = "admin") -> int:
        """Refresh populated_permissions cache for all roles."""
        roles = await self.role_repo.list_all(schema)
        count = 0
        
        for role in roles:
            if await self.role_repo.update_permissions_cache(role.id, schema):
                count += 1
        
        logger.info(f"Refreshed permissions cache for {count} roles in schema {schema}")
        return count