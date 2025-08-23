"""Protocol interfaces for permission feature dependency injection.

Defines contracts for permission checking, data access, and role management
following clean architecture and protocol-based dependency injection patterns.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable, List, Optional, Dict, Any, Set, Tuple
from datetime import datetime
from uuid import UUID

from ....core.value_objects import UserId, TenantId
from .permission import Permission, PermissionCode
from .role import Role, RoleCode


@runtime_checkable
class PermissionChecker(Protocol):
    """Protocol for permission checking operations with caching support."""
    
    @abstractmethod
    async def has_permission(
        self,
        user_id: UserId,
        permission_code: str,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has a specific permission in given scope."""
        ...
    
    @abstractmethod
    async def has_any_permission(
        self,
        user_id: UserId,
        permission_codes: List[str],
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has any of the specified permissions."""
        ...
    
    @abstractmethod
    async def has_all_permissions(
        self,
        user_id: UserId,
        permission_codes: List[str],
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Check if user has all of the specified permissions."""
        ...
    
    @abstractmethod
    async def get_user_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> Set[str]:
        """Get all permission codes for a user in given scope."""
        ...
    
    @abstractmethod
    async def get_user_roles(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None,
        scope_id: Optional[UUID] = None
    ) -> List[Role]:
        """Get all roles assigned to a user in given scope."""
        ...


@runtime_checkable
class PermissionRepository(Protocol):
    """Protocol for permission data access operations."""
    
    @abstractmethod
    async def get_by_id(self, permission_id: int, schema: str = "admin") -> Optional[Permission]:
        """Get permission by ID from specified schema."""
        ...
    
    @abstractmethod
    async def get_by_code(self, code: PermissionCode, schema: str = "admin") -> Optional[Permission]:
        """Get permission by code from specified schema."""
        ...
    
    @abstractmethod
    async def get_by_codes(self, codes: List[PermissionCode], schema: str = "admin") -> List[Permission]:
        """Get multiple permissions by codes from specified schema."""
        ...
    
    @abstractmethod
    async def list_all(
        self,
        schema: str = "admin",
        include_deleted: bool = False,
        resource_filter: Optional[str] = None,
        scope_filter: Optional[str] = None
    ) -> List[Permission]:
        """List all permissions with optional filters."""
        ...
    
    @abstractmethod
    async def list_by_resource(self, resource: str, schema: str = "admin") -> List[Permission]:
        """List all permissions for a specific resource."""
        ...
    
    @abstractmethod
    async def list_dangerous(self, schema: str = "admin") -> List[Permission]:
        """List all dangerous permissions requiring extra security."""
        ...
    
    @abstractmethod
    async def create(self, permission: Permission, schema: str = "admin") -> Permission:
        """Create a new permission in specified schema."""
        ...
    
    @abstractmethod
    async def update(self, permission: Permission, schema: str = "admin") -> Permission:
        """Update an existing permission in specified schema."""
        ...
    
    @abstractmethod
    async def delete(self, permission_id: int, schema: str = "admin") -> bool:
        """Soft delete a permission by setting deleted_at."""
        ...
    
    @abstractmethod
    async def search(
        self,
        query: str,
        schema: str = "admin",
        limit: int = 100,
        offset: int = 0
    ) -> List[Permission]:
        """Search permissions by description or code."""
        ...


@runtime_checkable
class RoleRepository(Protocol):
    """Protocol for role data access operations."""
    
    @abstractmethod
    async def get_by_id(self, role_id: int, schema: str = "admin") -> Optional[Role]:
        """Get role by ID from specified schema."""
        ...
    
    @abstractmethod
    async def get_by_code(self, code: RoleCode, schema: str = "admin") -> Optional[Role]:
        """Get role by code from specified schema."""
        ...
    
    @abstractmethod
    async def get_by_codes(self, codes: List[RoleCode], schema: str = "admin") -> List[Role]:
        """Get multiple roles by codes from specified schema."""
        ...
    
    @abstractmethod
    async def list_all(
        self,
        schema: str = "admin",
        include_deleted: bool = False,
        level_filter: Optional[str] = None,
        scope_filter: Optional[str] = None
    ) -> List[Role]:
        """List all roles with optional filters."""
        ...
    
    @abstractmethod
    async def list_by_level(self, role_level: str, schema: str = "admin") -> List[Role]:
        """List all roles at a specific hierarchical level."""
        ...
    
    @abstractmethod
    async def list_default_roles(self, schema: str = "admin") -> List[Role]:
        """List all default roles that are auto-assigned."""
        ...
    
    @abstractmethod
    async def list_system_roles(self, schema: str = "admin") -> List[Role]:
        """List all system roles."""
        ...
    
    @abstractmethod
    async def get_with_permissions(self, role_id: int, schema: str = "admin") -> Optional[Role]:
        """Get role with all its permissions loaded."""
        ...
    
    @abstractmethod
    async def create(self, role: Role, schema: str = "admin") -> Role:
        """Create a new role in specified schema."""
        ...
    
    @abstractmethod
    async def update(self, role: Role, schema: str = "admin") -> Role:
        """Update an existing role in specified schema."""
        ...
    
    @abstractmethod
    async def delete(self, role_id: int, schema: str = "admin") -> bool:
        """Soft delete a role by setting deleted_at."""
        ...
    
    @abstractmethod
    async def add_permission(
        self,
        role_id: int,
        permission_id: int,
        granted_by: Optional[UUID] = None,
        granted_reason: Optional[str] = None,
        schema: str = "admin"
    ) -> bool:
        """Add a permission to a role."""
        ...
    
    @abstractmethod
    async def remove_permission(self, role_id: int, permission_id: int, schema: str = "admin") -> bool:
        """Remove a permission from a role."""
        ...
    
    @abstractmethod
    async def update_permissions_cache(self, role_id: int, schema: str = "admin") -> bool:
        """Update the populated_permissions JSONB cache for a role."""
        ...


@runtime_checkable
class UserRoleManager(Protocol):
    """Protocol for managing user role assignments."""
    
    @abstractmethod
    async def assign_role(
        self,
        user_id: UUID,
        role_id: int,
        scope_type: str = "global",
        scope_id: Optional[UUID] = None,
        granted_by: Optional[UUID] = None,
        granted_reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        schema: str = "admin"
    ) -> bool:
        """Assign a role to a user with optional scoping and expiration."""
        ...
    
    @abstractmethod
    async def revoke_role(
        self,
        user_id: UUID,
        role_id: int,
        scope_id: Optional[UUID] = None,
        schema: str = "admin"
    ) -> bool:
        """Revoke a role assignment from a user."""
        ...
    
    @abstractmethod
    async def get_user_roles(
        self,
        user_id: UUID,
        schema: str = "admin",
        scope_type: Optional[str] = None,
        scope_id: Optional[UUID] = None,
        include_expired: bool = False
    ) -> List[Tuple[Role, Dict[str, Any]]]:
        """Get all roles assigned to a user with assignment metadata."""
        ...
    
    @abstractmethod
    async def get_role_assignees(
        self,
        role_id: int,
        schema: str = "admin",
        scope_id: Optional[UUID] = None,
        include_expired: bool = False
    ) -> List[Tuple[UUID, Dict[str, Any]]]:
        """Get all users assigned to a role with assignment metadata."""
        ...
    
    @abstractmethod
    async def grant_permission(
        self,
        user_id: UUID,
        permission_id: int,
        is_granted: bool = True,
        scope_type: str = "global",
        scope_id: Optional[UUID] = None,
        granted_by: Optional[UUID] = None,
        granted_reason: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        schema: str = "admin"
    ) -> bool:
        """Grant or revoke a direct permission to/from a user."""
        ...
    
    @abstractmethod
    async def revoke_permission(
        self,
        user_id: UUID,
        permission_id: int,
        scope_id: Optional[UUID] = None,
        revoked_by: Optional[UUID] = None,
        revoked_reason: Optional[str] = None,
        schema: str = "admin"
    ) -> bool:
        """Revoke a direct permission from a user."""
        ...
    
    @abstractmethod
    async def get_user_direct_permissions(
        self,
        user_id: UUID,
        schema: str = "admin",
        scope_type: Optional[str] = None,
        scope_id: Optional[UUID] = None,
        include_revoked: bool = False
    ) -> List[Tuple[Permission, Dict[str, Any]]]:
        """Get all direct permissions granted to a user with grant metadata."""
        ...
    
    @abstractmethod
    async def cleanup_expired_assignments(self, schema: str = "admin") -> int:
        """Clean up expired role and permission assignments."""
        ...


@runtime_checkable
class PermissionCache(Protocol):
    """Protocol for permission caching operations."""
    
    @abstractmethod
    async def get_user_permissions(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        scope_id: Optional[UUID] = None
    ) -> Optional[Set[str]]:
        """Get cached user permissions."""
        ...
    
    @abstractmethod
    async def set_user_permissions(
        self,
        user_id: UUID,
        permissions: Set[str],
        tenant_id: Optional[UUID] = None,
        scope_id: Optional[UUID] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """Cache user permissions with optional TTL."""
        ...
    
    @abstractmethod
    async def invalidate_user_permissions(
        self,
        user_id: UUID,
        tenant_id: Optional[UUID] = None,
        scope_id: Optional[UUID] = None
    ) -> bool:
        """Invalidate cached user permissions."""
        ...
    
    @abstractmethod
    async def invalidate_role_permissions(self, role_id: int) -> bool:
        """Invalidate all cached permissions for users with a specific role."""
        ...
    
    @abstractmethod
    async def get_role_permissions(self, role_id: int) -> Optional[Set[str]]:
        """Get cached role permissions."""
        ...
    
    @abstractmethod
    async def set_role_permissions(
        self,
        role_id: int,
        permissions: Set[str],
        ttl: Optional[int] = None
    ) -> bool:
        """Cache role permissions with optional TTL."""
        ...
    
    @abstractmethod
    async def clear_all(self) -> bool:
        """Clear all permission caches."""
        ...