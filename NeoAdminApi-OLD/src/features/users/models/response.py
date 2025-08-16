"""
Platform Users response models.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field

from .domain import (
    PlatformUser, PlatformRole, PlatformPermission,
    PlatformUserRole, PlatformUserPermission,
    TenantUserRole, TenantUserPermission,
    AuthProvider, PlatformRoleLevel, PermissionScopeLevel
)


class PlatformUserResponse(BaseModel):
    """Response model for platform user details."""
    
    id: UUID
    email: str
    username: str
    external_id: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    full_name: Optional[str]
    avatar_url: Optional[str]
    phone: Optional[str]
    timezone: str
    locale: str
    external_auth_provider: AuthProvider
    external_user_id: str
    is_active: bool
    is_superadmin: bool
    last_login_at: Optional[datetime]
    is_onboarding_completed: bool
    profile_completion_percentage: int
    job_title: Optional[str]
    departments: Optional[List[str]]
    company: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Role and permission information
    platform_roles: List[str] = Field(default_factory=list, description="Platform role codes")
    tenant_roles: Dict[str, List[str]] = Field(default_factory=dict, description="Tenant roles by tenant ID")
    permissions: List[str] = Field(default_factory=list, description="All effective permissions")
    tenant_count: int = Field(default=0, description="Number of tenants user has access to")
    
    # Preferences (limited for security)
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)
    ui_preferences: Dict[str, Any] = Field(default_factory=dict)
    
    @classmethod
    def from_domain(
        cls, 
        user: PlatformUser,
        platform_roles: Optional[List[str]] = None,
        tenant_roles: Optional[Dict[str, List[str]]] = None,
        permissions: Optional[List[str]] = None,
        tenant_count: int = 0
    ) -> "PlatformUserResponse":
        """Create response from domain model."""
        return cls(
            id=user.id,
            email=user.email,
            username=user.username,
            external_id=user.external_id,
            first_name=user.first_name,
            last_name=user.last_name,
            display_name=user.display_name,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            timezone=user.timezone,
            locale=user.locale,
            external_auth_provider=user.external_auth_provider,
            external_user_id=user.external_user_id,
            is_active=user.is_active,
            is_superadmin=user.is_superadmin,
            last_login_at=user.last_login_at,
            is_onboarding_completed=user.is_onboarding_completed,
            profile_completion_percentage=user.profile_completion_percentage,
            job_title=user.job_title,
            departments=user.departments,
            company=user.company,
            created_at=user.created_at,
            updated_at=user.updated_at,
            platform_roles=platform_roles or [],
            tenant_roles=tenant_roles or {},
            permissions=permissions or [],
            tenant_count=tenant_count,
            notification_preferences=user.notification_preferences,
            ui_preferences=user.ui_preferences
        )


class PlatformUserListItem(BaseModel):
    """Response model for platform user list items."""
    
    id: UUID
    email: str
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    full_name: Optional[str]
    avatar_url: Optional[str]
    external_auth_provider: AuthProvider
    is_active: bool
    is_superadmin: bool
    last_login_at: Optional[datetime]
    company: Optional[str]
    job_title: Optional[str]
    created_at: datetime
    
    # Summary information
    role_count: int = Field(default=0, description="Number of roles assigned")
    tenant_count: int = Field(default=0, description="Number of tenants with access")
    permission_count: int = Field(default=0, description="Number of direct permissions")


class PlatformUserListResponse(BaseModel):
    """Response model for platform user list."""
    
    items: List[PlatformUserListItem]
    pagination: Dict[str, Any]


class PlatformUserListSummary(BaseModel):
    """Summary statistics for platform user list."""
    
    total_users: int
    active_users: int
    inactive_users: int
    superadmin_users: int
    by_provider: Dict[str, int] = Field(default_factory=dict)
    by_company: Dict[str, int] = Field(default_factory=dict)
    by_department: Dict[str, int] = Field(default_factory=dict)
    recent_logins_7d: int = Field(default=0)
    recent_logins_30d: int = Field(default=0)
    users_with_tenant_access: int = Field(default=0)
    average_profile_completion: float = Field(default=0.0)


class RoleResponse(BaseModel):
    """Response model for platform role."""
    
    id: int
    code: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    role_level: PlatformRoleLevel
    priority: int
    is_system: bool
    is_default: bool
    max_assignees: Optional[int]
    tenant_scoped: bool
    requires_approval: bool
    created_at: datetime
    updated_at: datetime
    
    # Permission information
    permission_count: int = Field(default=0, description="Number of permissions")
    user_count: int = Field(default=0, description="Number of users with this role")
    
    @classmethod
    def from_domain(
        cls, 
        role: PlatformRole,
        permission_count: int = 0,
        user_count: int = 0
    ) -> "RoleResponse":
        """Create response from domain model."""
        return cls(
            id=role.id,
            code=role.code,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            role_level=role.role_level,
            priority=role.priority,
            is_system=role.is_system,
            is_default=role.is_default,
            max_assignees=role.max_assignees,
            tenant_scoped=role.tenant_scoped,
            requires_approval=role.requires_approval,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permission_count=permission_count,
            user_count=user_count
        )


class PermissionResponse(BaseModel):
    """Response model for platform permission."""
    
    id: int
    code: str
    description: Optional[str]
    resource: str
    action: str
    scope_level: PermissionScopeLevel
    is_dangerous: bool
    requires_mfa: bool
    requires_approval: bool
    created_at: datetime
    updated_at: datetime
    
    # Usage information
    role_count: int = Field(default=0, description="Number of roles with this permission")
    user_count: int = Field(default=0, description="Number of users with this permission")
    
    @classmethod
    def from_domain(
        cls, 
        permission: PlatformPermission,
        role_count: int = 0,
        user_count: int = 0
    ) -> "PermissionResponse":
        """Create response from domain model."""
        return cls(
            id=permission.id,
            code=permission.code,
            description=permission.description,
            resource=permission.resource,
            action=permission.action,
            scope_level=permission.scope_level,
            is_dangerous=permission.is_dangerous,
            requires_mfa=permission.requires_mfa,
            requires_approval=permission.requires_approval,
            created_at=permission.created_at,
            updated_at=permission.updated_at,
            role_count=role_count,
            user_count=user_count
        )


class UserRoleAssignmentResponse(BaseModel):
    """Response model for user role assignment."""
    
    user_id: UUID
    role_id: int
    role_code: str
    role_name: str
    tenant_id: Optional[UUID] = None
    tenant_name: Optional[str] = None
    granted_by: Optional[UUID]
    granted_by_name: Optional[str]
    granted_reason: Optional[str]
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    
    @classmethod
    def from_platform_role(
        cls, 
        assignment: PlatformUserRole,
        role_code: str,
        role_name: str,
        granted_by_name: Optional[str] = None
    ) -> "UserRoleAssignmentResponse":
        """Create response from platform role assignment."""
        return cls(
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            role_code=role_code,
            role_name=role_name,
            granted_by=assignment.granted_by,
            granted_by_name=granted_by_name,
            granted_reason=assignment.granted_reason,
            granted_at=assignment.granted_at,
            expires_at=assignment.expires_at,
            is_active=assignment.is_active
        )
    
    @classmethod
    def from_tenant_role(
        cls, 
        assignment: TenantUserRole,
        role_code: str,
        role_name: str,
        tenant_name: Optional[str] = None,
        granted_by_name: Optional[str] = None
    ) -> "UserRoleAssignmentResponse":
        """Create response from tenant role assignment."""
        return cls(
            user_id=assignment.user_id,
            role_id=assignment.role_id,
            role_code=role_code,
            role_name=role_name,
            tenant_id=assignment.tenant_id,
            tenant_name=tenant_name,
            granted_by=assignment.granted_by,
            granted_by_name=granted_by_name,
            granted_reason=assignment.granted_reason,
            granted_at=assignment.granted_at,
            expires_at=assignment.expires_at,
            is_active=assignment.is_active
        )


class UserPermissionGrantResponse(BaseModel):
    """Response model for user permission grant."""
    
    user_id: UUID
    permission_id: int
    permission_code: str
    permission_description: Optional[str]
    tenant_id: Optional[UUID] = None
    tenant_name: Optional[str] = None
    is_granted: bool
    is_active: bool
    granted_by: Optional[UUID]
    granted_by_name: Optional[str]
    granted_reason: Optional[str]
    granted_at: datetime
    expires_at: Optional[datetime]
    revoked_by: Optional[UUID]
    revoked_reason: Optional[str]
    
    @classmethod
    def from_platform_permission(
        cls, 
        grant: PlatformUserPermission,
        permission_code: str,
        permission_description: Optional[str] = None,
        granted_by_name: Optional[str] = None
    ) -> "UserPermissionGrantResponse":
        """Create response from platform permission grant."""
        return cls(
            user_id=grant.user_id,
            permission_id=grant.permission_id,
            permission_code=permission_code,
            permission_description=permission_description,
            is_granted=grant.is_granted,
            is_active=grant.is_active,
            granted_by=grant.granted_by,
            granted_by_name=granted_by_name,
            granted_reason=grant.granted_reason,
            granted_at=grant.granted_at,
            expires_at=grant.expires_at,
            revoked_by=grant.revoked_by,
            revoked_reason=grant.revoked_reason
        )
    
    @classmethod
    def from_tenant_permission(
        cls, 
        grant: TenantUserPermission,
        permission_code: str,
        permission_description: Optional[str] = None,
        tenant_name: Optional[str] = None,
        granted_by_name: Optional[str] = None
    ) -> "UserPermissionGrantResponse":
        """Create response from tenant permission grant."""
        return cls(
            user_id=grant.user_id,
            permission_id=grant.permission_id,
            permission_code=permission_code,
            permission_description=permission_description,
            tenant_id=grant.tenant_id,
            tenant_name=tenant_name,
            is_granted=grant.is_granted,
            is_active=grant.is_active,
            granted_by=grant.granted_by,
            granted_by_name=granted_by_name,
            granted_reason=grant.granted_reason,
            granted_at=grant.granted_at,
            expires_at=grant.expires_at,
            revoked_by=grant.revoked_by,
            revoked_reason=grant.revoked_reason
        )


class BulkOperationResponse(BaseModel):
    """Response model for bulk operations."""
    
    operation: str
    total_requested: int
    successful: int
    failed: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    successful_ids: List[UUID] = Field(default_factory=list)
    failed_ids: List[UUID] = Field(default_factory=list)
    

class UserSearchResponse(BaseModel):
    """Response model for user search results."""
    
    query: str
    total_results: int
    results: List[PlatformUserListItem]
    facets: Dict[str, Dict[str, int]] = Field(default_factory=dict, description="Search facets")
    suggestions: List[str] = Field(default_factory=list, description="Search suggestions")
    pagination: Dict[str, Any]
