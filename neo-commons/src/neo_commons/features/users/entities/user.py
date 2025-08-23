"""User domain entity.

This module defines the User entity and related business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone

from ....core.value_objects import UserId, TenantId, OrganizationId, PermissionCode, RoleCode
from ....config.constants import AuthProvider, UserStatus
from ....utils.uuid import generate_uuid_v7


@dataclass
class User:
    """User domain entity.
    
    Represents a user in the system, which can exist in either the admin schema
    (platform users) or tenant schemas (tenant users). Structure matches the
    unified database schema used in both admin.users and tenant_template.users.
    """
    
    # Core Identity (identical in both schemas)
    id: UserId
    email: str
    external_user_id: str
    
    # Optional core fields
    username: Optional[str] = None
    external_auth_provider: AuthProvider = AuthProvider.KEYCLOAK
    external_auth_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Profile Information (identical)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    
    # Localization (identical)
    timezone: str = "UTC"
    locale: str = "en-US"
    
    # Status (unified - replaces both status and is_active)
    status: UserStatus = UserStatus.ACTIVE
    
    # Organizational (conditional fields managed by configuration)
    departments: List[str] = field(default_factory=list)
    company: Optional[str] = None
    manager_id: Optional[UserId] = None
    
    # Role and Access (managed by scope context)
    default_role_level: str = "member"  # platform_common.role_level
    is_system_user: bool = False
    
    # Onboarding and Profile
    is_onboarding_completed: bool = False
    profile_completion_percentage: int = 0
    
    # Preferences (identical)
    notification_preferences: Dict[str, Any] = field(default_factory=dict)
    ui_preferences: Dict[str, Any] = field(default_factory=dict)
    feature_flags: Dict[str, Any] = field(default_factory=dict)
    
    # Tags and Custom Fields (unified)
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Activity Tracking (identical)
    invited_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    # Audit Fields (identical)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    
    # Runtime properties (not in database, computed)
    schema_name: str = "admin"
    tenant_id: Optional[TenantId] = None
    organization_id: Optional[OrganizationId] = None
    permissions: Set[PermissionCode] = field(default_factory=set)
    roles: Set[RoleCode] = field(default_factory=set)
    
    def __post_init__(self):
        """Post-initialization validation."""
        # Validate profile completion percentage
        if not (0 <= self.profile_completion_percentage <= 100):
            object.__setattr__(self, 'profile_completion_percentage', 0)
        
        # Set schema name based on tenant_id
        if self.tenant_id and self.schema_name == "admin":
            object.__setattr__(self, 'schema_name', f"tenant_{self.tenant_id.value}")
    
    @property
    def full_name(self) -> str:
        """Get full name from first and last name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name or self.username or self.email
    
    @property
    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE and self.deleted_at is None
    
    @property
    def is_admin_user(self) -> bool:
        """Check if user is an admin user (in admin schema)."""
        return self.schema_name == "admin"
    
    @property
    def is_tenant_user(self) -> bool:
        """Check if user is a tenant user."""
        return self.tenant_id is not None and self.schema_name.startswith("tenant_")
    
    def has_permission(self, permission: PermissionCode) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions
    
    def has_any_permission(self, permissions: List[PermissionCode]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[PermissionCode]) -> bool:
        """Check if user has all specified permissions."""
        return all(perm in self.permissions for perm in permissions)
    
    def has_role(self, role: RoleCode) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def add_permission(self, permission: PermissionCode) -> None:
        """Add permission to user."""
        self.permissions.add(permission)
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_permission(self, permission: PermissionCode) -> None:
        """Remove permission from user."""
        self.permissions.discard(permission)
        self.updated_at = datetime.now(timezone.utc)
    
    def add_role(self, role: RoleCode) -> None:
        """Add role to user."""
        self.roles.add(role)
        self.updated_at = datetime.now(timezone.utc)
    
    def remove_role(self, role: RoleCode) -> None:
        """Remove role from user."""
        self.roles.discard(role)
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate user."""
        self.status = UserStatus.INACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate user."""
        self.status = UserStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)
    
    def suspend(self) -> None:
        """Suspend user."""
        self.status = UserStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc)
    
    def archive(self) -> None:
        """Archive user."""
        self.status = UserStatus.ARCHIVED
        self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self) -> None:
        """Soft delete user."""
        self.deleted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_last_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_preference(self, category: str, key: str, value: Any) -> None:
        """Update user preference in specific category."""
        if category == "notification":
            self.notification_preferences[key] = value
        elif category == "ui":
            self.ui_preferences[key] = value
        elif category == "feature":
            self.feature_flags[key] = value
        self.updated_at = datetime.now(timezone.utc)
    
    def add_tag(self, tag: str) -> None:
        """Add tag to user."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_tag(self, tag: str) -> None:
        """Remove tag from user."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now(timezone.utc)
    
    def set_custom_field(self, key: str, value: Any) -> None:
        """Set custom field value."""
        self.custom_fields[key] = value
        self.updated_at = datetime.now(timezone.utc)
    
    def complete_onboarding(self) -> None:
        """Mark onboarding as completed."""
        self.is_onboarding_completed = True
        self.activated_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)