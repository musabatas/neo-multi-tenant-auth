"""
Permission check value objects.

Immutable types for permission checking operations and results.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class CheckType(str, Enum):
    """Type of permission check being performed."""
    SINGLE = "single"        # Check single permission
    ANY = "any"             # Check if user has any of the permissions
    ALL = "all"             # Check if user has all of the permissions
    RESOURCE_ACCESS = "resource_access"  # Check resource-level access


@dataclass(frozen=True)
class PermissionCheck:
    """
    Immutable permission check request.
    
    Represents a request to check user permissions in a specific context.
    """
    user_id: str
    permissions: List[str]  # Permission codes to check
    check_type: CheckType = CheckType.SINGLE
    tenant_id: Optional[str] = None
    team_id: Optional[str] = None
    resource_id: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        """Validate and initialize the permission check."""
        if not self.permissions:
            raise ValueError("At least one permission must be specified")
        
        if self.check_type == CheckType.SINGLE and len(self.permissions) > 1:
            raise ValueError("Single permission check can only check one permission")
        
        if self.context is None:
            object.__setattr__(self, 'context', {})
    
    @property
    def primary_permission(self) -> str:
        """Get the primary permission being checked."""
        return self.permissions[0]
    
    @property
    def context_key(self) -> str:
        """Get context key for caching."""
        if self.tenant_id:
            return f"tenant:{self.tenant_id}"
        return "platform"
    
    def get_cache_key(self) -> str:
        """Generate cache key for this permission check."""
        perms_str = "|".join(sorted(self.permissions))
        return f"pcheck:{self.user_id}:{perms_str}:{self.check_type}:{self.context_key}"
    
    @classmethod
    def single(cls, user_id: str, permission: str, tenant_id: Optional[str] = None) -> "PermissionCheck":
        """Create a single permission check."""
        return cls(
            user_id=user_id,
            permissions=[permission],
            check_type=CheckType.SINGLE,
            tenant_id=tenant_id
        )
    
    @classmethod
    def any_of(cls, user_id: str, permissions: List[str], tenant_id: Optional[str] = None) -> "PermissionCheck":
        """Create a check for any of the specified permissions."""
        return cls(
            user_id=user_id,
            permissions=permissions,
            check_type=CheckType.ANY,
            tenant_id=tenant_id
        )
    
    @classmethod
    def all_of(cls, user_id: str, permissions: List[str], tenant_id: Optional[str] = None) -> "PermissionCheck":
        """Create a check for all of the specified permissions."""
        return cls(
            user_id=user_id,
            permissions=permissions,
            check_type=CheckType.ALL,
            tenant_id=tenant_id
        )
    
    @classmethod
    def resource_access(cls, user_id: str, resource: str, action: str, 
                       tenant_id: Optional[str] = None, resource_id: Optional[str] = None) -> "PermissionCheck":
        """Create a resource access check."""
        permission = f"{resource}:{action}"
        return cls(
            user_id=user_id,
            permissions=[permission],
            check_type=CheckType.RESOURCE_ACCESS,
            tenant_id=tenant_id,
            resource_id=resource_id
        )
    
    def __str__(self) -> str:
        perms = ", ".join(self.permissions)
        return f"{self.check_type}({perms}) for user {self.user_id}"


@dataclass(frozen=True)
class PermissionResult:
    """
    Immutable permission check result.
    
    Contains the result of a permission check with supporting evidence.
    """
    check: PermissionCheck
    granted: bool
    
    # Supporting evidence
    matched_permissions: List[str] = None
    active_roles: List[str] = None
    decision_reason: str = ""
    
    # Performance info
    from_cache: bool = False
    check_duration_ms: float = 0.0
    
    # Additional context
    requires_mfa: bool = False
    requires_approval: bool = False
    is_dangerous: bool = False
    
    def __post_init__(self):
        """Initialize collections."""
        if self.matched_permissions is None:
            object.__setattr__(self, 'matched_permissions', [])
        if self.active_roles is None:
            object.__setattr__(self, 'active_roles', [])
    
    @property
    def denied(self) -> bool:
        """Check if permission was denied."""
        return not self.granted
    
    @property
    def user_id(self) -> str:
        """Get user ID from the check."""
        return self.check.user_id
    
    @property
    def permissions_checked(self) -> List[str]:
        """Get permissions that were checked."""
        return self.check.permissions
    
    @property
    def tenant_id(self) -> Optional[str]:
        """Get tenant ID from the check."""
        return self.check.tenant_id
    
    def get_cache_value(self) -> Dict[str, Any]:
        """Get cacheable representation of this result."""
        return {
            "granted": self.granted,
            "matched_permissions": self.matched_permissions,
            "active_roles": self.active_roles,
            "decision_reason": self.decision_reason,
            "requires_mfa": self.requires_mfa,
            "requires_approval": self.requires_approval,
            "is_dangerous": self.is_dangerous
        }
    
    @classmethod
    def granted(cls, check: PermissionCheck, matched_permissions: List[str] = None,
               active_roles: List[str] = None, reason: str = "Permission granted") -> "PermissionResult":
        """Create a granted permission result."""
        return cls(
            check=check,
            granted=True,
            matched_permissions=matched_permissions or [],
            active_roles=active_roles or [],
            decision_reason=reason
        )
    
    @classmethod
    def denied(cls, check: PermissionCheck, reason: str = "Permission denied") -> "PermissionResult":
        """Create a denied permission result."""
        return cls(
            check=check,
            granted=False,
            decision_reason=reason
        )
    
    @classmethod
    def from_cache(cls, check: PermissionCheck, cached_data: Dict[str, Any]) -> "PermissionResult":
        """Create permission result from cached data."""
        return cls(
            check=check,
            granted=cached_data["granted"],
            matched_permissions=cached_data.get("matched_permissions", []),
            active_roles=cached_data.get("active_roles", []),
            decision_reason=cached_data.get("decision_reason", ""),
            from_cache=True,
            requires_mfa=cached_data.get("requires_mfa", False),
            requires_approval=cached_data.get("requires_approval", False),
            is_dangerous=cached_data.get("is_dangerous", False)
        )
    
    def __str__(self) -> str:
        status = "GRANTED" if self.granted else "DENIED"
        cache_indicator = " (cached)" if self.from_cache else ""
        return f"{status}: {self.check}{cache_indicator}"
    
    def __repr__(self) -> str:
        return f"PermissionResult(granted={self.granted}, check={self.check})"