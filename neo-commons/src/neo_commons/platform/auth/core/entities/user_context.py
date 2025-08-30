"""User context domain entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set, List
from ....core.value_objects.identifiers import UserId, TenantId, PermissionCode, RoleCode
from ..value_objects import RealmIdentifier


@dataclass
class UserContext:
    """User authentication context entity.
    
    Handles ONLY user context representation and permission aggregation.
    Does not perform authentication operations - that's handled by auth services.
    """
    
    # Core Identity
    user_id: UserId
    tenant_id: Optional[TenantId] = None
    realm_id: Optional[RealmIdentifier] = None
    
    # User Information
    external_user_id: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    
    # Authentication Status
    is_authenticated: bool = False
    authentication_method: str = "password"
    mfa_verified: bool = False
    
    # Permission Context
    roles: Set[RoleCode] = field(default_factory=set)
    direct_permissions: Set[PermissionCode] = field(default_factory=set)
    effective_permissions: Set[PermissionCode] = field(default_factory=set)
    team_permissions: Set[PermissionCode] = field(default_factory=set)
    
    # User Status and Flags
    is_active: bool = True
    is_system_user: bool = False
    is_onboarding_completed: bool = True
    requires_mfa: bool = False
    requires_approval: bool = False
    is_dangerous: bool = False
    
    # Profile Information
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    
    # Localization
    timezone: str = "UTC"
    locale: str = "en-US"
    
    # Context Metadata
    session_metadata: Dict[str, Any] = field(default_factory=dict)
    user_metadata: Dict[str, Any] = field(default_factory=dict)
    permission_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Audit Information
    last_login_at: Optional[datetime] = None
    permissions_loaded_at: Optional[datetime] = None
    context_created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context_updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self) -> None:
        """Initialize user context after creation."""
        # Ensure timezone awareness
        if self.context_created_at.tzinfo is None:
            self.context_created_at = self.context_created_at.replace(tzinfo=timezone.utc)
        
        if self.context_updated_at.tzinfo is None:
            self.context_updated_at = self.context_updated_at.replace(tzinfo=timezone.utc)
        
        if self.last_login_at and self.last_login_at.tzinfo is None:
            self.last_login_at = self.last_login_at.replace(tzinfo=timezone.utc)
        
        if self.permissions_loaded_at and self.permissions_loaded_at.tzinfo is None:
            self.permissions_loaded_at = self.permissions_loaded_at.replace(tzinfo=timezone.utc)
        
        # Set display name if not provided
        if not self.display_name:
            if self.first_name and self.last_name:
                self.display_name = f"{self.first_name} {self.last_name}"
            elif self.username:
                self.display_name = self.username
            elif self.email:
                self.display_name = self.email.split('@')[0]
        
        # Aggregate effective permissions
        self._update_effective_permissions()
    
    def _update_effective_permissions(self) -> None:
        """Update effective permissions by aggregating all permission sources."""
        # Combine direct permissions, role permissions, and team permissions
        self.effective_permissions = (
            self.direct_permissions | 
            self.team_permissions | 
            set()  # Role-based permissions would be resolved by application layer
        )
        self.context_updated_at = datetime.now(timezone.utc)
    
    @property
    def is_valid(self) -> bool:
        """Check if user context is valid for authentication."""
        return (
            self.is_authenticated and 
            self.is_active and 
            not self.requires_approval and
            (not self.requires_mfa or self.mfa_verified)
        )
    
    @property
    def full_name(self) -> Optional[str]:
        """Get user's full name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin-level permissions."""
        admin_roles = {'admin', 'super_admin', 'platform_admin'}
        return any(role.value in admin_roles for role in self.roles) or self.is_system_user
    
    @property
    def permission_count(self) -> int:
        """Get total effective permissions count."""
        return len(self.effective_permissions)
    
    @property
    def role_count(self) -> int:
        """Get total roles count."""
        return len(self.roles)
    
    @property
    def context_age_seconds(self) -> int:
        """Get context age in seconds."""
        delta = datetime.now(timezone.utc) - self.context_created_at
        return int(delta.total_seconds())
    
    @property
    def is_fresh(self, max_age_seconds: int = 300) -> bool:
        """Check if context is fresh (recently created)."""
        return self.context_age_seconds <= max_age_seconds
    
    def add_role(self, role: RoleCode) -> None:
        """Add a role to the user context."""
        self.roles.add(role)
        self._update_effective_permissions()
    
    def remove_role(self, role: RoleCode) -> None:
        """Remove a role from the user context."""
        self.roles.discard(role)
        self._update_effective_permissions()
    
    def has_role(self, role: RoleCode) -> bool:
        """Check if user has a specific role."""
        return role in self.roles
    
    def add_permission(self, permission: PermissionCode, source: str = "direct") -> None:
        """Add a permission to the user context."""
        if source == "direct":
            self.direct_permissions.add(permission)
        elif source == "team":
            self.team_permissions.add(permission)
        
        self._update_effective_permissions()
    
    def remove_permission(self, permission: PermissionCode, source: str = "direct") -> None:
        """Remove a permission from the user context."""
        if source == "direct":
            self.direct_permissions.discard(permission)
        elif source == "team":
            self.team_permissions.discard(permission)
        
        self._update_effective_permissions()
    
    def has_permission(self, permission: PermissionCode) -> bool:
        """Check if user has a specific permission."""
        return permission in self.effective_permissions
    
    def has_any_permission(self, permissions: List[PermissionCode]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(self.has_permission(perm) for perm in permissions)
    
    def has_all_permissions(self, permissions: List[PermissionCode]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(self.has_permission(perm) for perm in permissions)
    
    def clear_permissions(self, source: str = "all") -> None:
        """Clear permissions from specified source."""
        if source == "all":
            self.direct_permissions.clear()
            self.team_permissions.clear()
        elif source == "direct":
            self.direct_permissions.clear()
        elif source == "team":
            self.team_permissions.clear()
        
        self._update_effective_permissions()
    
    def update_session_metadata(self, key: str, value: Any) -> None:
        """Update session metadata."""
        self.session_metadata[key] = value
        self.context_updated_at = datetime.now(timezone.utc)
    
    def get_session_metadata(self, key: str, default: Any = None) -> Any:
        """Get session metadata value."""
        return self.session_metadata.get(key, default)
    
    def update_user_metadata(self, key: str, value: Any) -> None:
        """Update user metadata."""
        self.user_metadata[key] = value
        self.context_updated_at = datetime.now(timezone.utc)
    
    def get_user_metadata(self, key: str, default: Any = None) -> Any:
        """Get user metadata value."""
        return self.user_metadata.get(key, default)
    
    def mark_permissions_loaded(self) -> None:
        """Mark permissions as loaded."""
        self.permissions_loaded_at = datetime.now(timezone.utc)
        self.context_updated_at = datetime.now(timezone.utc)
    
    def mark_authenticated(self, method: str = "password", mfa_verified: bool = False) -> None:
        """Mark user as authenticated."""
        self.is_authenticated = True
        self.authentication_method = method
        self.mfa_verified = mfa_verified
        self.last_login_at = datetime.now(timezone.utc)
        self.context_updated_at = datetime.now(timezone.utc)
    
    def mark_unauthenticated(self) -> None:
        """Mark user as unauthenticated."""
        self.is_authenticated = False
        self.mfa_verified = False
        self.context_updated_at = datetime.now(timezone.utc)
    
    def update_profile(
        self,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        phone: Optional[str] = None,
        job_title: Optional[str] = None,
        company: Optional[str] = None
    ) -> None:
        """Update user profile information."""
        if first_name is not None:
            self.first_name = first_name
        if last_name is not None:
            self.last_name = last_name
        if display_name is not None:
            self.display_name = display_name
        if avatar_url is not None:
            self.avatar_url = avatar_url
        if phone is not None:
            self.phone = phone
        if job_title is not None:
            self.job_title = job_title
        if company is not None:
            self.company = company
        
        # Update display name if needed
        if not self.display_name and (first_name or last_name):
            self.display_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        
        self.context_updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user context to dictionary representation."""
        return {
            'user_id': str(self.user_id.value),
            'tenant_id': str(self.tenant_id.value) if self.tenant_id else None,
            'realm_id': str(self.realm_id.value) if self.realm_id else None,
            'external_user_id': self.external_user_id,
            'email': self.email,
            'username': self.username,
            'display_name': self.display_name,
            'is_authenticated': self.is_authenticated,
            'authentication_method': self.authentication_method,
            'mfa_verified': self.mfa_verified,
            'roles': [str(role.value) for role in self.roles],
            'direct_permissions': [str(perm.value) for perm in self.direct_permissions],
            'effective_permissions': [str(perm.value) for perm in self.effective_permissions],
            'team_permissions': [str(perm.value) for perm in self.team_permissions],
            'is_active': self.is_active,
            'is_system_user': self.is_system_user,
            'is_onboarding_completed': self.is_onboarding_completed,
            'requires_mfa': self.requires_mfa,
            'requires_approval': self.requires_approval,
            'is_dangerous': self.is_dangerous,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'avatar_url': self.avatar_url,
            'phone': self.phone,
            'job_title': self.job_title,
            'company': self.company,
            'timezone': self.timezone,
            'locale': self.locale,
            'session_metadata': self.session_metadata,
            'user_metadata': self.user_metadata,
            'permission_metadata': self.permission_metadata,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'permissions_loaded_at': self.permissions_loaded_at.isoformat() if self.permissions_loaded_at else None,
            'context_created_at': self.context_created_at.isoformat(),
            'context_updated_at': self.context_updated_at.isoformat(),
            'is_valid': self.is_valid,
            'is_admin': self.is_admin,
            'permission_count': self.permission_count,
            'role_count': self.role_count,
            'context_age_seconds': self.context_age_seconds,
            'is_fresh': self.is_fresh
        }
    
    def __str__(self) -> str:
        """String representation."""
        status = "authenticated" if self.is_authenticated else "unauthenticated"
        return f"UserContext({self.display_name or self.user_id}, {status}, {self.permission_count} perms)"
    
    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"UserContext(user_id={self.user_id}, tenant_id={self.tenant_id}, "
            f"is_authenticated={self.is_authenticated}, roles={len(self.roles)}, "
            f"permissions={len(self.effective_permissions)})"
        )