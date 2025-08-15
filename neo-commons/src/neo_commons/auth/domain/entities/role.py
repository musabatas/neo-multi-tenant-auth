"""
Role entity - Authorization role management with hierarchy.

Handles collections of permissions and role assignments.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from .permission import Permission, PermissionScope


class RoleLevel(str, Enum):
    """Role hierarchy levels for platform and tenant contexts."""
    # Platform roles (system-wide)
    SUPERADMIN = "superadmin"    # Complete system access
    PLATFORM_ADMIN = "platform_admin"  # Platform management
    SUPPORT = "support"          # Customer support
    
    # Tenant roles (tenant-specific)
    OWNER = "owner"              # Tenant owner
    ADMIN = "admin"              # Tenant administrator
    MANAGER = "manager"          # Team manager
    MEMBER = "member"            # Regular member
    VIEWER = "viewer"            # Read-only access
    GUEST = "guest"              # Limited access


@dataclass(frozen=True)
class Role:
    """
    Core role entity with permission collections.
    
    Roles group permissions for easier management and assignment.
    """
    id: str
    code: str  # e.g., "platform_admin", "tenant_owner"
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    role_level: RoleLevel = RoleLevel.MEMBER
    scope_level: PermissionScope = PermissionScope.PLATFORM
    priority: int = 0  # Higher priority overrides lower
    permissions: List[Permission] = None
    role_config: Dict[str, Any] = None
    is_system: bool = False  # System roles can't be deleted
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize collections as empty if None."""
        if self.permissions is None:
            object.__setattr__(self, 'permissions', [])
        if self.role_config is None:
            object.__setattr__(self, 'role_config', {})
        if self.display_name is None:
            object.__setattr__(self, 'display_name', self.name)
    
    @property
    def is_superadmin(self) -> bool:
        """Check if this is a superadmin role."""
        return self.role_level == RoleLevel.SUPERADMIN
    
    @property
    def is_platform_role(self) -> bool:
        """Check if this is a platform-level role."""
        return self.scope_level == PermissionScope.PLATFORM
    
    @property
    def is_tenant_role(self) -> bool:
        """Check if this is a tenant-level role."""
        return self.scope_level == PermissionScope.TENANT
    
    def get_permission_codes(self) -> Set[str]:
        """Get all permission codes granted by this role."""
        return {perm.code for perm in self.permissions}
    
    def has_permission(self, code: str) -> bool:
        """
        Check if role has a specific permission.
        
        Supports wildcard matching (users:* matches users:read).
        """
        for permission in self.permissions:
            if permission.code == code:
                return True
            # Check wildcard implication
            if permission.is_wildcard:
                resource = code.split(":")[0] if ":" in code else code
                if permission.resource == resource:
                    return True
        return False
    
    def has_any_permission(self, codes: List[str]) -> bool:
        """Check if role has any of the specified permissions."""
        return any(self.has_permission(code) for code in codes)
    
    def has_all_permissions(self, codes: List[str]) -> bool:
        """Check if role has all of the specified permissions."""
        return all(self.has_permission(code) for code in codes)
    
    def get_dangerous_permissions(self) -> List[Permission]:
        """Get all dangerous permissions in this role."""
        return [perm for perm in self.permissions if perm.is_dangerous]
    
    def can_be_assigned_by(self, assigner_role: "Role") -> bool:
        """
        Check if this role can be assigned by another role.
        
        Business rules:
        - Higher priority roles can assign lower priority roles
        - Same scope level required
        - Superadmin can assign any role
        """
        # Superadmin can assign any role
        if assigner_role.is_superadmin:
            return True
        
        # Must be same or higher priority
        return assigner_role.priority >= self.priority
    
    def __str__(self) -> str:
        return self.display_name or self.name
    
    def __repr__(self) -> str:
        return f"Role(code='{self.code}', level='{self.role_level}', permissions={len(self.permissions)})"


@dataclass(frozen=True)
class RoleAssignment:
    """
    Role assignment to a user with context and constraints.
    
    Tracks who has what roles in which contexts with expiration.
    """
    id: str
    user_id: str
    role_id: str
    role: Optional[Role] = None
    tenant_id: Optional[str] = None  # None for platform roles
    team_id: Optional[str] = None    # Future: team-scoped roles
    granted_by: Optional[str] = None
    granted_at: datetime = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    assignment_config: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize config as empty dict if None."""
        if self.assignment_config is None:
            object.__setattr__(self, 'assignment_config', {})
        if self.granted_at is None:
            from neo_commons.utils.datetime import utc_now
            object.__setattr__(self, 'granted_at', utc_now())
    
    @property
    def is_expired(self) -> bool:
        """Check if assignment has expired."""
        if self.expires_at is None:
            return False
        from neo_commons.utils.datetime import utc_now
        return utc_now() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if assignment is currently valid."""
        return self.is_active and not self.is_expired
    
    @property
    def is_platform_assignment(self) -> bool:
        """Check if this is a platform-level role assignment."""
        return self.tenant_id is None
    
    @property
    def is_tenant_assignment(self) -> bool:
        """Check if this is a tenant-level role assignment."""
        return self.tenant_id is not None
    
    def get_context_key(self) -> str:
        """Get unique context key for caching."""
        if self.tenant_id:
            return f"tenant:{self.tenant_id}"
        return "platform"
    
    def matches_context(self, tenant_id: Optional[str] = None) -> bool:
        """Check if assignment matches the given context."""
        # Platform assignments match any context
        if self.is_platform_assignment:
            return True
        
        # Tenant assignments must match tenant
        return self.tenant_id == tenant_id
    
    def __str__(self) -> str:
        role_name = self.role.name if self.role else f"role:{self.role_id}"
        context = f"tenant:{self.tenant_id}" if self.tenant_id else "platform"
        return f"{role_name}@{context}"
    
    def __repr__(self) -> str:
        return f"RoleAssignment(user={self.user_id}, role={self.role_id}, context={self.get_context_key()})"