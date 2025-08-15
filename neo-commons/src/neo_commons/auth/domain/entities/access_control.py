"""
Access control entity - User authorization state and decisions.

Handles resolved access control decisions and caching contexts.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from .permission import Permission
from .role import Role, RoleAssignment


class AccessLevel(str, Enum):
    """Access level for resource access control."""
    NONE = "none"          # No access
    READ = "read"          # Read-only access
    WRITE = "write"        # Read-write access
    ADMIN = "admin"        # Administrative access
    OWNER = "owner"        # Full ownership access


@dataclass(frozen=True)
class AccessControlEntry:
    """
    Resolved access control decision for a user-resource combination.
    
    This represents the final authorization decision after evaluating
    all roles, permissions, and context.
    """
    user_id: str
    resource: str
    access_level: AccessLevel
    tenant_id: Optional[str] = None
    team_id: Optional[str] = None
    
    # Supporting evidence for the decision
    granted_permissions: List[Permission] = None
    active_roles: List[Role] = None
    role_assignments: List[RoleAssignment] = None
    
    # Decision metadata
    decision_reason: str = "Computed from roles and permissions"
    computed_at: datetime = None
    cache_ttl: int = 300  # 5 minutes default
    
    def __post_init__(self):
        """Initialize collections and timestamp."""
        if self.granted_permissions is None:
            object.__setattr__(self, 'granted_permissions', [])
        if self.active_roles is None:
            object.__setattr__(self, 'active_roles', [])
        if self.role_assignments is None:
            object.__setattr__(self, 'role_assignments', [])
        if self.computed_at is None:
            from neo_commons.utils.datetime import utc_now
            object.__setattr__(self, 'computed_at', utc_now())
    
    @property
    def has_access(self) -> bool:
        """Check if user has any access to the resource."""
        return self.access_level != AccessLevel.NONE
    
    @property
    def can_read(self) -> bool:
        """Check if user can read the resource."""
        return self.access_level in [AccessLevel.READ, AccessLevel.WRITE, AccessLevel.ADMIN, AccessLevel.OWNER]
    
    @property
    def can_write(self) -> bool:
        """Check if user can modify the resource."""
        return self.access_level in [AccessLevel.WRITE, AccessLevel.ADMIN, AccessLevel.OWNER]
    
    @property
    def can_admin(self) -> bool:
        """Check if user has admin access to the resource."""
        return self.access_level in [AccessLevel.ADMIN, AccessLevel.OWNER]
    
    @property
    def is_owner(self) -> bool:
        """Check if user owns the resource."""
        return self.access_level == AccessLevel.OWNER
    
    @property
    def context_key(self) -> str:
        """Get context key for caching."""
        if self.tenant_id:
            return f"tenant:{self.tenant_id}"
        return "platform"
    
    def get_permission_codes(self) -> Set[str]:
        """Get all permission codes that grant this access."""
        return {perm.code for perm in self.granted_permissions}
    
    def has_permission(self, code: str) -> bool:
        """Check if a specific permission was granted."""
        return code in self.get_permission_codes()
    
    def has_role(self, role_code: str) -> bool:
        """Check if user has a specific role in this context."""
        return any(role.code == role_code for role in self.active_roles)
    
    def get_dangerous_permissions(self) -> List[Permission]:
        """Get all dangerous permissions granted."""
        return [perm for perm in self.granted_permissions if perm.is_dangerous]
    
    def requires_mfa(self) -> bool:
        """Check if any granted permissions require MFA."""
        return any(perm.requires_mfa for perm in self.granted_permissions)
    
    def requires_approval(self) -> bool:
        """Check if any granted permissions require approval."""
        return any(perm.requires_approval for perm in self.granted_permissions)
    
    def get_cache_key(self) -> str:
        """Generate cache key for this access control entry."""
        return f"acl:{self.user_id}:{self.resource}:{self.context_key}"
    
    @classmethod
    def no_access(cls, user_id: str, resource: str, tenant_id: Optional[str] = None) -> "AccessControlEntry":
        """Create an access control entry with no access."""
        return cls(
            user_id=user_id,
            resource=resource,
            access_level=AccessLevel.NONE,
            tenant_id=tenant_id,
            decision_reason="No matching permissions or roles found"
        )
    
    @classmethod
    def from_permissions(
        cls,
        user_id: str,
        resource: str,
        permissions: List[Permission],
        roles: List[Role],
        assignments: List[RoleAssignment],
        tenant_id: Optional[str] = None
    ) -> "AccessControlEntry":
        """
        Create access control entry from resolved permissions and roles.
        
        Determines the highest access level from available permissions.
        """
        if not permissions:
            return cls.no_access(user_id, resource, tenant_id)
        
        # Determine access level from permissions
        access_level = AccessLevel.NONE
        
        # Check for specific access patterns
        resource_perms = {perm.action for perm in permissions if perm.resource == resource}
        
        # Owner level - has all permissions or wildcard
        if "*" in resource_perms or all(action in resource_perms for action in ["read", "write", "delete", "admin"]):
            access_level = AccessLevel.OWNER
        # Admin level - has admin permission
        elif "admin" in resource_perms:
            access_level = AccessLevel.ADMIN
        # Write level - has write permission
        elif "write" in resource_perms or "create" in resource_perms or "update" in resource_perms:
            access_level = AccessLevel.WRITE
        # Read level - has read permission
        elif "read" in resource_perms or "list" in resource_perms:
            access_level = AccessLevel.READ
        
        return cls(
            user_id=user_id,
            resource=resource,
            access_level=access_level,
            tenant_id=tenant_id,
            granted_permissions=permissions,
            active_roles=roles,
            role_assignments=assignments,
            decision_reason=f"Computed from {len(permissions)} permissions and {len(roles)} roles"
        )
    
    def __str__(self) -> str:
        return f"{self.access_level.value}@{self.resource}"
    
    def __repr__(self) -> str:
        return f"AccessControlEntry(user={self.user_id}, resource='{self.resource}', level='{self.access_level}')"