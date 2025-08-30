"""Permission loading protocol contract."""

from typing import Protocol, runtime_checkable, Set, List, Dict, Any, Optional
from ....core.value_objects.identifiers import UserId, TenantId, PermissionCode, RoleCode


@runtime_checkable
class PermissionLoader(Protocol):
    """Protocol for permission and role loading operations.
    
    Defines ONLY the contract for permission data retrieval.
    Implementations handle specific data sources (database, cache, external services, etc.).
    """
    
    async def get_user_permissions(
        self, 
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> Set[PermissionCode]:
        """Get all permissions for a user in a tenant context.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (None for platform permissions)
            
        Returns:
            Set of permission codes the user has
        """
        ...
    
    async def get_user_roles(
        self,
        user_id: UserId, 
        tenant_id: Optional[TenantId] = None
    ) -> Set[RoleCode]:
        """Get all roles assigned to a user in a tenant context.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (None for platform roles)
            
        Returns:
            Set of role codes assigned to the user
        """
        ...
    
    async def get_user_permission_details(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> List[Dict[str, Any]]:
        """Get detailed permission information for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (None for platform permissions)
            
        Returns:
            List of permission dictionaries with details (code, resource, action, etc.)
        """
        ...
    
    async def check_user_permission(
        self,
        user_id: UserId,
        permission_code: PermissionCode,
        tenant_id: Optional[TenantId] = None
    ) -> bool:
        """Check if user has a specific permission.
        
        Args:
            user_id: User identifier
            permission_code: Permission to check
            tenant_id: Tenant identifier (None for platform permissions)
            
        Returns:
            True if user has the permission, False otherwise
        """
        ...
    
    async def check_user_role(
        self,
        user_id: UserId,
        role_code: RoleCode,
        tenant_id: Optional[TenantId] = None
    ) -> bool:
        """Check if user has a specific role.
        
        Args:
            user_id: User identifier
            role_code: Role to check
            tenant_id: Tenant identifier (None for platform roles)
            
        Returns:
            True if user has the role, False otherwise
        """
        ...
    
    async def get_role_permissions(self, role_code: RoleCode) -> Set[PermissionCode]:
        """Get all permissions for a specific role.
        
        Args:
            role_code: Role code to lookup
            
        Returns:
            Set of permission codes for the role
        """
        ...
    
    async def invalidate_user_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> None:
        """Invalidate cached permissions for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (None for all contexts)
        """
        ...
    
    async def preload_user_permissions(
        self,
        user_id: UserId,
        tenant_id: Optional[TenantId] = None
    ) -> None:
        """Preload and cache user permissions for better performance.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (None for platform permissions)
        """
        ...