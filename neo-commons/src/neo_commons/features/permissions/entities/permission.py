"""Permission domain entity for neo-commons permissions feature.

Represents a system permission with resource/action structure, security controls,
and audit information. Maps to both admin.permissions and tenant_template.permissions tables.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ....core.exceptions import AuthorizationError
from ....config.constants import PermissionScope


@dataclass(frozen=True)
class PermissionCode:
    """Immutable value object for permission identifier with validation."""
    
    value: str
    
    def __post_init__(self):
        """Validate permission code format: resource:action"""
        if not self.value or ":" not in self.value:
            raise AuthorizationError(f"Permission code must be in format 'resource:action', got: {self.value}")
        
        parts = self.value.split(":")
        if len(parts) != 2:
            raise AuthorizationError(f"Permission code must have exactly one colon, got: {self.value}")
        
        resource, action = parts
        if not resource or not action:
            raise AuthorizationError(f"Both resource and action must be non-empty, got: {self.value}")
    
    @property
    def resource(self) -> str:
        """Extract resource part from permission code."""
        return self.value.split(":")[0]
    
    @property
    def action(self) -> str:
        """Extract action part from permission code."""
        return self.value.split(":")[1]
    
    def __str__(self) -> str:
        return self.value


@dataclass
class Permission:
    """Domain entity representing a system permission with security controls."""
    
    id: Optional[int]
    code: PermissionCode
    description: Optional[str]
    resource: str
    action: str
    scope_level: PermissionScope
    is_dangerous: bool = False
    requires_mfa: bool = False
    requires_approval: bool = False
    permission_config: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate permission entity consistency."""
        if self.permission_config is None:
            self.permission_config = {}
        
        # Validate resource/action match code
        if self.code.resource != self.resource:
            raise AuthorizationError(f"Permission resource mismatch: code={self.code.resource}, field={self.resource}")
        if self.code.action != self.action:
            raise AuthorizationError(f"Permission action mismatch: code={self.code.action}, field={self.action}")
    
    def is_active(self) -> bool:
        """Check if permission is active (not deleted)."""
        return self.deleted_at is None
    
    def requires_security_check(self) -> bool:
        """Check if permission requires additional security measures."""
        return self.is_dangerous or self.requires_mfa or self.requires_approval
    
    def get_security_requirements(self) -> Dict[str, bool]:
        """Get all security requirements for this permission."""
        return {
            "is_dangerous": self.is_dangerous,
            "requires_mfa": self.requires_mfa,
            "requires_approval": self.requires_approval
        }
    
    def matches_pattern(self, pattern: str) -> bool:
        """Check if permission matches a pattern (supports wildcards)."""
        if pattern == "*":
            return True
        
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return self.code.value.startswith(prefix)
        
        return self.code.value == pattern
    
    def __str__(self) -> str:
        return f"Permission({self.code})"
    
    def __repr__(self) -> str:
        security_flags = []
        if self.is_dangerous:
            security_flags.append("dangerous")
        if self.requires_mfa:
            security_flags.append("mfa")
        if self.requires_approval:
            security_flags.append("approval")
        
        security_info = f" [{', '.join(security_flags)}]" if security_flags else ""
        return f"Permission({self.code}, scope={self.scope_level.value}{security_info})"