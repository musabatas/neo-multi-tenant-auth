"""
Permission entity - Core authorization business logic.

Handles fine-grained access control with resource-action patterns.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from datetime import datetime


class PermissionScope(str, Enum):
    """Permission scope levels for multi-tenant authorization."""
    PLATFORM = "platform"  # System-wide permissions
    TENANT = "tenant"      # Tenant-specific permissions
    TEAM = "team"          # Team-specific permissions (future)
    USER = "user"          # User-specific permissions (future)


@dataclass(frozen=True)
class Permission:
    """
    Core permission entity with resource-action pattern.
    
    Examples:
        - users:read (read user data)
        - tenants:create (create new tenants)
        - billing:* (all billing actions)
    """
    id: str
    code: str  # e.g., "users:read"
    resource: str  # e.g., "users" 
    action: str  # e.g., "read", "write", "*"
    scope_level: PermissionScope = PermissionScope.PLATFORM
    description: Optional[str] = None
    is_dangerous: bool = False
    requires_mfa: bool = False
    requires_approval: bool = False
    config: Dict[str, Any] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize config as empty dict if None."""
        if self.config is None:
            object.__setattr__(self, 'config', {})
    
    @property
    def is_wildcard(self) -> bool:
        """Check if this is a wildcard permission (action = '*')."""
        return self.action == "*"
    
    def implies(self, other_permission: "Permission") -> bool:
        """
        Check if this permission implies another permission.
        
        Rules:
        - Wildcard permissions (users:*) imply specific actions (users:read)
        - Same resource + same action implies each other
        - Different resources never imply each other
        
        Args:
            other_permission: Permission to check implication for
            
        Returns:
            True if this permission implies the other
        """
        # Different resources never imply each other
        if self.resource != other_permission.resource:
            return False
        
        # Wildcard action implies any action on same resource
        if self.is_wildcard:
            return True
        
        # Same resource + same action
        return self.action == other_permission.action
    
    def matches(self, resource: str, action: str) -> bool:
        """
        Check if permission matches resource:action pattern.
        
        Args:
            resource: Resource name to check
            action: Action name to check
            
        Returns:
            True if permission matches the pattern
        """
        if self.resource != resource:
            return False
        
        return self.is_wildcard or self.action == action
    
    @classmethod
    def from_code(cls, code: str, scope_level: PermissionScope = PermissionScope.PLATFORM) -> "Permission":
        """
        Create permission from code string.
        
        Args:
            code: Permission code like "users:read"
            scope_level: Permission scope level
            
        Returns:
            Permission instance
            
        Raises:
            ValueError: If code format is invalid
        """
        if ":" not in code:
            raise ValueError(f"Invalid permission code format: {code}. Expected 'resource:action'")
        
        resource, action = code.split(":", 1)
        
        return cls(
            id=code,  # Use code as ID for generated permissions
            code=code,
            resource=resource,
            action=action,
            scope_level=scope_level
        )
    
    def __str__(self) -> str:
        return self.code
    
    def __repr__(self) -> str:
        return f"Permission(code='{self.code}', scope='{self.scope_level}')"


@dataclass(frozen=True) 
class PermissionGroup:
    """
    Collection of related permissions for easier management.
    
    Used for organizing permissions in admin interfaces and bulk operations.
    """
    id: str
    name: str
    description: Optional[str] = None
    permissions: List[Permission] = None
    scope_level: PermissionScope = PermissionScope.PLATFORM
    is_system: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize permissions as empty list if None."""
        if self.permissions is None:
            object.__setattr__(self, 'permissions', [])
    
    def get_permission_codes(self) -> Set[str]:
        """Get all permission codes in this group."""
        return {perm.code for perm in self.permissions}
    
    def has_permission(self, code: str) -> bool:
        """Check if group contains a specific permission code."""
        return code in self.get_permission_codes()
    
    def get_dangerous_permissions(self) -> List[Permission]:
        """Get all dangerous permissions in this group."""
        return [perm for perm in self.permissions if perm.is_dangerous]
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return f"PermissionGroup(name='{self.name}', permissions={len(self.permissions)})"