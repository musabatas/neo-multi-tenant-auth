"""Role domain entity for neo-commons permissions feature.

Represents a system role with hierarchical levels, behavioral configuration,
and permission assignments. Maps to both admin.roles and tenant_template.roles tables.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field

from ....core.exceptions import AuthorizationError
from ....config.constants import RoleLevel
from .permission import Permission, PermissionCode


@dataclass(frozen=True)
class RoleCode:
    """Immutable value object for role identifier with validation."""
    
    value: str
    
    def __post_init__(self):
        """Validate role code format and constraints."""
        if not self.value:
            raise AuthorizationError("Role code cannot be empty")
        
        if len(self.value) > 100:
            raise AuthorizationError(f"Role code cannot exceed 100 characters, got: {len(self.value)}")
        
        # Basic format validation - alphanumeric, underscores, hyphens
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', self.value):
            raise AuthorizationError(f"Role code must contain only alphanumeric characters, underscores, and hyphens: {self.value}")
    
    def __str__(self) -> str:
        return self.value


@dataclass
class Role:
    """Domain entity representing a system role with permissions and behavior configuration."""
    
    id: Optional[int]
    code: RoleCode
    name: str
    description: Optional[str]
    display_name: Optional[str]
    role_level: RoleLevel
    is_system: bool = False
    is_default: bool = False
    requires_approval: bool = False
    scope_type: str = "global"
    priority: int = 100
    max_assignees: Optional[int] = None
    auto_expire_days: Optional[int] = None
    role_config: Dict[str, Any] = None
    metadata: Dict[str, Any] = None
    populated_permissions: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    # Runtime permission cache (not persisted)
    _permissions: Set[Permission] = field(default_factory=set, init=False, repr=False)
    _permission_codes: Set[str] = field(default_factory=set, init=False, repr=False)
    
    def __post_init__(self):
        """Validate role entity and initialize defaults."""
        if self.role_config is None:
            object.__setattr__(self, 'role_config', {})
        
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
        
        if self.populated_permissions is None:
            object.__setattr__(self, 'populated_permissions', {})
        
        if self.display_name is None:
            object.__setattr__(self, 'display_name', self.name)
        
        # Validate scope type
        valid_scopes = {"global", "team", "tenant"}
        if self.scope_type not in valid_scopes:
            raise AuthorizationError(f"Invalid scope_type: {self.scope_type}. Must be one of: {valid_scopes}")
        
        # Validate priority
        if self.priority <= 0:
            raise AuthorizationError(f"Role priority must be positive, got: {self.priority}")
        
        # Validate max_assignees
        if self.max_assignees is not None and self.max_assignees <= 0:
            raise AuthorizationError(f"max_assignees must be positive or None, got: {self.max_assignees}")
        
        # Validate auto_expire_days
        if self.auto_expire_days is not None and self.auto_expire_days <= 0:
            raise AuthorizationError(f"auto_expire_days must be positive or None, got: {self.auto_expire_days}")
    
    def is_active(self) -> bool:
        """Check if role is active (not deleted)."""
        return self.deleted_at is None
    
    def is_assignable(self) -> bool:
        """Check if role can be assigned to users."""
        return self.is_active() and not self.is_system
    
    def has_permission(self, permission_code: str) -> bool:
        """Check if role has a specific permission."""
        return permission_code in self._permission_codes
    
    def has_permission_pattern(self, pattern: str) -> bool:
        """Check if role has any permission matching a pattern (supports wildcards)."""
        if pattern == "*":
            return len(self._permission_codes) > 0
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return any(code.startswith(prefix) for code in self._permission_codes)
        
        return pattern in self._permission_codes
    
    def get_permissions(self) -> Set[Permission]:
        """Get all permissions assigned to this role."""
        return self._permissions.copy()
    
    def get_permission_codes(self) -> Set[str]:
        """Get all permission codes assigned to this role."""
        return self._permission_codes.copy()
    
    def add_permission(self, permission: Permission) -> None:
        """Add a permission to this role (runtime cache only)."""
        self._permissions.add(permission)
        self._permission_codes.add(permission.code.value)
    
    def remove_permission(self, permission_code: str) -> None:
        """Remove a permission from this role (runtime cache only)."""
        self._permission_codes.discard(permission_code)
        self._permissions = {p for p in self._permissions if p.code.value != permission_code}
    
    def clear_permissions(self) -> None:
        """Clear all permissions from this role (runtime cache only)."""
        self._permissions.clear()
        self._permission_codes.clear()
    
    def load_permissions_from_cache(self, permissions_data: Dict[str, Any]) -> None:
        """Load permissions from populated_permissions JSONB cache."""
        self.clear_permissions()
        
        for permission_code, permission_data in permissions_data.items():
            if isinstance(permission_data, dict):
                # Full permission data
                permission = Permission(
                    id=permission_data.get('id'),
                    code=PermissionCode(permission_code),
                    description=permission_data.get('description'),
                    resource=permission_data.get('resource', permission_code.split(':')[0]),
                    action=permission_data.get('action', permission_code.split(':')[1]),
                    scope_level=permission_data.get('scope_level', 'platform'),
                    is_dangerous=permission_data.get('is_dangerous', False),
                    requires_mfa=permission_data.get('requires_mfa', False),
                    requires_approval=permission_data.get('requires_approval', False),
                    permission_config=permission_data.get('permission_config', {})
                )
                self.add_permission(permission)
            else:
                # Just permission code
                self._permission_codes.add(permission_code)
    
    def get_security_level(self) -> str:
        """Get overall security level based on assigned permissions."""
        if any(p.is_dangerous for p in self._permissions):
            return "critical"
        elif any(p.requires_mfa for p in self._permissions):
            return "high"
        elif any(p.requires_approval for p in self._permissions):
            return "medium"
        else:
            return "low"
    
    def can_be_assigned_to_user_count(self, current_assignees: int) -> bool:
        """Check if role can be assigned to more users."""
        if self.max_assignees is None:
            return True
        return current_assignees < self.max_assignees
    
    def get_hierarchy_level(self) -> int:
        """Get numerical hierarchy level for comparison (higher = more privileged)."""
        hierarchy_map = {
            RoleLevel.SYSTEM: 1000,
            RoleLevel.PLATFORM: 900,
            RoleLevel.TENANT: 800,
            RoleLevel.OWNER: 700,
            RoleLevel.ADMIN: 600,
            RoleLevel.MANAGER: 500,
            RoleLevel.MEMBER: 400,
            RoleLevel.VIEWER: 300,
            RoleLevel.GUEST: 200
        }
        return hierarchy_map.get(self.role_level, 0)
    
    def is_higher_than(self, other_role: 'Role') -> bool:
        """Check if this role has higher privilege than another role."""
        return self.get_hierarchy_level() > other_role.get_hierarchy_level()
    
    def __str__(self) -> str:
        return f"Role({self.code})"
    
    def __repr__(self) -> str:
        flags = []
        if self.is_system:
            flags.append("system")
        if self.is_default:
            flags.append("default")
        if self.requires_approval:
            flags.append("approval")
        
        flag_info = f" [{', '.join(flags)}]" if flags else ""
        permission_count = len(self._permission_codes)
        return f"Role({self.code}, level={self.role_level.value}, priority={self.priority}, permissions={permission_count}{flag_info})"