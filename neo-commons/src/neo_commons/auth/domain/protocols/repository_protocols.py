"""
Repository protocol interfaces for authorization domain.

Defines contracts for data access layer implementations.
"""
from typing import Protocol, runtime_checkable, List, Optional, Dict, Any
from ..entities.permission import Permission, PermissionGroup
from ..entities.role import Role, RoleAssignment
from ..entities.access_control import AccessControlEntry
from ..entities.session import Session, SessionContext
from ..value_objects.user_context import UserContext
from ..value_objects.tenant_context import TenantContext


@runtime_checkable
class PermissionRepositoryProtocol(Protocol):
    """Protocol for permission data access operations."""
    
    async def get_permission_by_id(self, permission_id: str) -> Optional[Permission]:
        """Get permission by ID."""
        ...
    
    async def get_permission_by_code(self, code: str) -> Optional[Permission]:
        """Get permission by code (e.g., 'users:read')."""
        ...
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        include_role_permissions: bool = True,
        include_direct_permissions: bool = True
    ) -> List[Permission]:
        """Get all permissions for a user in given context."""
        ...
    
    async def get_platform_user_permissions(self, user_id: str) -> List[Permission]:
        """Get platform-level permissions for user."""
        ...
    
    async def get_tenant_user_permissions(self, user_id: str, tenant_id: str) -> List[Permission]:
        """Get tenant-level permissions for user."""
        ...
    
    async def check_permission(
        self,
        user_id: str,
        permission_code: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if user has specific permission."""
        ...
    
    async def get_all_permissions(self, active_only: bool = True) -> List[Permission]:
        """Get all available permissions."""
        ...
    
    async def get_permission_resources(self) -> List[str]:
        """Get all unique permission resources."""
        ...
    
    async def get_permission_group_by_id(self, group_id: str) -> Optional[PermissionGroup]:
        """Get permission group by ID."""
        ...
    
    async def get_permission_groups(self, active_only: bool = True) -> List[PermissionGroup]:
        """Get all permission groups."""
        ...


@runtime_checkable
class RoleRepositoryProtocol(Protocol):
    """Protocol for role data access operations."""
    
    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
        """Get role by ID."""
        ...
    
    async def get_role_by_code(self, role_code: str) -> Optional[Role]:
        """Get role by code."""
        ...
    
    async def get_user_roles(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[Role]:
        """Get all roles for a user."""
        ...
    
    async def get_platform_user_roles(self, user_id: str, active_only: bool = True) -> List[Role]:
        """Get platform-level roles for user."""
        ...
    
    async def get_tenant_user_roles(
        self,
        user_id: str,
        tenant_id: str,
        active_only: bool = True
    ) -> List[Role]:
        """Get tenant-level roles for user."""
        ...
    
    async def get_role_permissions(self, role_id: str) -> List[Permission]:
        """Get all permissions for a role."""
        ...
    
    async def get_user_role_assignments(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        active_only: bool = True
    ) -> List[RoleAssignment]:
        """Get role assignments for a user."""
        ...
    
    async def create_role_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        """Create a new role assignment."""
        ...
    
    async def update_role_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        """Update an existing role assignment."""
        ...
    
    async def delete_role_assignment(self, assignment_id: str) -> bool:
        """Delete a role assignment."""
        ...


@runtime_checkable
class AccessControlRepositoryProtocol(Protocol):
    """Protocol for access control data operations."""
    
    async def get_user_access_control(
        self,
        user_id: str,
        resource: str,
        tenant_id: Optional[str] = None
    ) -> Optional[AccessControlEntry]:
        """Get access control entry for user-resource combination."""
        ...
    
    async def compute_user_access_control(
        self,
        user_context: UserContext,
        resource: str,
        tenant_context: Optional[TenantContext] = None
    ) -> AccessControlEntry:
        """Compute access control entry from user permissions and roles."""
        ...
    
    async def get_user_accessible_resources(
        self,
        user_id: str,
        resource_type: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """Get list of resources user has access to."""
        ...
    
    async def bulk_check_access(
        self,
        user_id: str,
        resource_actions: List[tuple[str, str]],  # (resource, action) pairs
        tenant_id: Optional[str] = None
    ) -> Dict[str, bool]:
        """Bulk check access for multiple resource-action combinations."""
        ...


@runtime_checkable
class SessionRepositoryProtocol(Protocol):
    """Protocol for session data operations."""
    
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by ID."""
        ...
    
    async def get_session_by_user(self, user_id: str) -> Optional[Session]:
        """Get active session for user."""
        ...
    
    async def create_session(self, session: Session) -> Session:
        """Create a new session."""
        ...
    
    async def update_session(self, session: Session) -> Session:
        """Update an existing session."""
        ...
    
    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        ...
    
    async def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user. Returns count of invalidated sessions."""
        ...
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions. Returns count of cleaned sessions."""
        ...
    
    async def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Session]:
        """Get all sessions for a user."""
        ...