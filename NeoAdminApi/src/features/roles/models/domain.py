"""
Domain models for roles.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class PlatformRoleLevel(str, Enum):
    """Platform role level enum matching database type."""
    SYSTEM = "system"
    PLATFORM = "platform"
    TENANT = "tenant"


class PermissionScopeLevel(str, Enum):
    """Permission scope level enum matching database type."""
    PLATFORM = "platform"
    TENANT = "tenant"
    USER = "user"


class PlatformRole(BaseModel):
    """Platform role domain model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Identity
    id: int
    code: str
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    
    # Role configuration
    role_level: PlatformRoleLevel = PlatformRoleLevel.PLATFORM
    priority: int = 100
    is_system: bool = False
    is_default: bool = False
    max_assignees: Optional[int] = None
    tenant_scoped: bool = False
    requires_approval: bool = False
    
    # Configuration
    role_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    # Dynamic fields (populated when needed)
    permission_count: Optional[int] = None
    user_count: Optional[int] = None
    permissions: Optional[List[Any]] = None


class PlatformPermission(BaseModel):
    """Platform permission domain model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    # Identity
    id: int
    code: str
    description: Optional[str] = None
    
    # Permission details
    resource: str
    action: str
    scope_level: PermissionScopeLevel = PermissionScopeLevel.PLATFORM
    
    # Security flags
    is_dangerous: bool = False
    requires_mfa: bool = False
    requires_approval: bool = False
    
    # Configuration
    permissions_config: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class RolePermission(BaseModel):
    """Role-permission assignment model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    role_id: int
    permission_id: int
    granted_at: datetime
    
    # Populated when needed
    role: Optional[PlatformRole] = None
    permission: Optional[PlatformPermission] = None


class UserRoleAssignment(BaseModel):
    """User role assignment model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    user_id: UUID
    role_id: int
    granted_by: Optional[UUID] = None
    granted_reason: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    # Populated when needed
    role: Optional[PlatformRole] = None
    granted_by_user: Optional[Any] = None  # Will be PlatformUser when populated


class TenantUserRoleAssignment(BaseModel):
    """Tenant-specific user role assignment model."""
    
    model_config = ConfigDict(from_attributes=True)
    
    tenant_id: UUID
    user_id: UUID
    role_id: int
    granted_by: Optional[UUID] = None
    granted_reason: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    # Populated when needed
    role: Optional[PlatformRole] = None
    granted_by_user: Optional[Any] = None  # Will be PlatformUser when populated
    tenant: Optional[Any] = None  # Will be Tenant when populated