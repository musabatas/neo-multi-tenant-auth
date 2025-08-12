"""
Platform Users domain models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict, field_validator

from src.common.models.base import BaseSchema


class AuthProvider(str, Enum):
    """External authentication providers."""
    KEYCLOAK = "keycloak"
    AUTH0 = "auth0"
    AUTHELIA = "authelia"
    AUTHENTIK = "authentik"
    AZURE = "azure"
    GOOGLE = "google"
    CUSTOM = "custom"


class PlatformRoleLevel(str, Enum):
    """Platform role levels."""
    SYSTEM = "system"
    PLATFORM = "platform"
    TENANT = "tenant"


class PermissionScopeLevel(str, Enum):
    """Permission scope levels."""
    PLATFORM = "platform"
    TENANT = "tenant"
    USER = "user"


class PlatformUser(BaseSchema):
    """Platform user domain model."""
    
    id: UUID
    email: str = Field(..., max_length=320)
    username: str = Field(..., max_length=39)
    external_id: Optional[str] = Field(None, max_length=255)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    display_name: Optional[str] = Field(None, max_length=150)
    avatar_url: Optional[str] = Field(None, max_length=2048)
    phone: Optional[str] = Field(None, max_length=20)
    timezone: str = Field(default="UTC", max_length=50)
    locale: str = Field(default="en-US", max_length=10)
    external_auth_provider: AuthProvider
    external_user_id: str = Field(..., max_length=255)
    is_active: bool = Field(default=True)
    is_superadmin: bool = Field(default=False)
    last_login_at: Optional[datetime] = None
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    is_onboarding_completed: bool = Field(default=False)
    profile_completion_percentage: int = Field(default=0, ge=0, le=100)
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    ui_preferences: Dict[str, Any] = Field(default_factory=dict)
    job_title: Optional[str] = Field(None, max_length=150)
    departments: Optional[List[str]] = None
    company: Optional[str] = Field(None, max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        import re
        pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError('Invalid email format')
        return v.lower()
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format."""
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Username can only contain letters, numbers, dots, underscores, and hyphens')
        return v.lower()
    
    @property
    def full_name(self) -> Optional[str]:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.display_name:
            return self.display_name
        elif self.first_name:
            return self.first_name
        return None
    
    @property
    def is_deleted(self) -> bool:
        """Check if user is soft deleted."""
        return self.deleted_at is not None


class PlatformRole(BaseSchema):
    """Platform role domain model."""
    
    id: int
    code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=150)
    display_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    role_level: PlatformRoleLevel = Field(default=PlatformRoleLevel.PLATFORM)
    priority: int = Field(default=100)
    is_system: bool = Field(default=False)
    is_default: bool = Field(default=False)
    max_assignees: Optional[int] = None
    tenant_scoped: bool = Field(default=False)
    requires_approval: bool = Field(default=False)
    role_config: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    @property
    def is_deleted(self) -> bool:
        """Check if role is soft deleted."""
        return self.deleted_at is not None


class PlatformPermission(BaseSchema):
    """Platform permission domain model."""
    
    id: int
    code: str = Field(..., max_length=100)
    description: Optional[str] = None
    resource: str = Field(..., max_length=50)
    action: str = Field(..., max_length=50)
    scope_level: PermissionScopeLevel = Field(default=PermissionScopeLevel.PLATFORM)
    is_dangerous: bool = Field(default=False)
    requires_mfa: bool = Field(default=False)
    requires_approval: bool = Field(default=False)
    permissions_config: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    
    @property
    def is_deleted(self) -> bool:
        """Check if permission is soft deleted."""
        return self.deleted_at is not None


class PlatformUserRole(BaseSchema):
    """Platform user role assignment."""
    
    user_id: UUID
    role_id: int
    granted_by: Optional[UUID] = None
    granted_reason: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    
    # Relationships
    role: Optional[PlatformRole] = None
    granted_by_user: Optional[str] = None  # User name who granted


class PlatformUserPermission(BaseSchema):
    """Platform user permission assignment."""
    
    user_id: UUID
    permission_id: int
    is_granted: bool = Field(default=True)
    is_active: bool = Field(default=True)
    granted_at: datetime
    expires_at: Optional[datetime] = None
    granted_by: Optional[UUID] = None
    granted_reason: Optional[str] = None
    revoked_by: Optional[UUID] = None
    revoked_reason: Optional[str] = None
    
    # Relationships
    permission: Optional[PlatformPermission] = None
    granted_by_user: Optional[str] = None  # User name who granted


class TenantUserRole(BaseSchema):
    """Tenant-scoped user role assignment."""
    
    tenant_id: UUID
    user_id: UUID
    role_id: int
    granted_by: Optional[UUID] = None
    granted_reason: Optional[str] = None
    granted_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    
    # Relationships
    role: Optional[PlatformRole] = None
    granted_by_user: Optional[str] = None
    tenant_name: Optional[str] = None


class TenantUserPermission(BaseSchema):
    """Tenant-scoped user permission assignment."""
    
    tenant_id: UUID
    user_id: UUID
    permission_id: int
    is_granted: bool = Field(default=True)
    is_active: bool = Field(default=True)
    granted_at: datetime
    expires_at: Optional[datetime] = None
    granted_by: Optional[UUID] = None
    granted_reason: Optional[str] = None
    revoked_by: Optional[UUID] = None
    revoked_reason: Optional[str] = None
    
    # Relationships
    permission: Optional[PlatformPermission] = None
    granted_by_user: Optional[str] = None
    tenant_name: Optional[str] = None
