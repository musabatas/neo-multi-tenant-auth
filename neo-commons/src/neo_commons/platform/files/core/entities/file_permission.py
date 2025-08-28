"""File permission entity.

ONLY file permission - represents file access permission business entity with
RBAC integration, team-based sharing, and granular access control.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from enum import Enum

# No base Entity class needed - using plain dataclass
from .....core.value_objects import UserId, TenantId, RoleCode, PermissionCode
from .....utils import generate_uuid_v7, utc_now
from ..value_objects import FileId


class PermissionLevel(Enum):
    """File permission levels."""
    NONE = "none"          # No access
    READ = "read"          # Read-only access
    WRITE = "write"        # Read and write access
    ADMIN = "admin"        # Full administrative access
    OWNER = "owner"        # Ownership rights


class PermissionType(Enum):
    """Type of permission grant."""
    USER = "user"          # Direct user permission
    ROLE = "role"          # Role-based permission
    TEAM = "team"          # Team-based permission
    PUBLIC = "public"      # Public access permission
    LINK = "link"          # Share link permission


class ShareLinkType(Enum):
    """Type of share link."""
    VIEW_ONLY = "view_only"
    DOWNLOAD = "download"
    EDIT = "edit"
    FULL_ACCESS = "full_access"


@dataclass
class FilePermission:
    """File permission entity.
    
    Represents access permissions for files with support for user-based,
    role-based, and team-based access control. Integrates with the RBAC
    system and provides granular permission management.
    
    Features:
    - Multi-level permission system (read, write, admin, owner)
    - User, role, and team-based permissions
    - Public access and share links
    - Temporary permissions with expiration
    - Permission inheritance from folders
    - Audit trail for permission changes
    """
    
    # Core identification
    id: str = field(default_factory=lambda: str(generate_uuid_v7()))
    tenant_id: TenantId = field(default_factory=lambda: TenantId.generate())
    
    # Target file
    file_id: FileId = field(default_factory=lambda: FileId.generate())
    
    # Permission details
    permission_type: PermissionType = PermissionType.USER
    permission_level: PermissionLevel = PermissionLevel.READ
    
    # Subject (who gets the permission)
    user_id: Optional[UserId] = None
    role_code: Optional[RoleCode] = None
    team_id: Optional[str] = None  # Team ID from team management system
    
    # Public access and sharing
    is_public: bool = False
    share_token: Optional[str] = None
    share_link_type: Optional[ShareLinkType] = None
    public_url: Optional[str] = None
    
    # Permission scope and conditions
    allowed_actions: Set[str] = field(default_factory=lambda: {"read"})
    denied_actions: Set[str] = field(default_factory=set)
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Temporal permissions
    expires_at: Optional[datetime] = None
    is_temporary: bool = False
    
    # Inheritance
    inherited_from_folder_id: Optional[FileId] = None
    is_inherited: bool = False
    can_be_inherited: bool = True
    
    # Access restrictions
    ip_restrictions: Set[str] = field(default_factory=set)
    time_restrictions: Dict[str, Any] = field(default_factory=dict)
    max_downloads: Optional[int] = None
    download_count: int = 0
    
    # Permission metadata
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Grant information
    granted_by: Optional[UserId] = None
    granted_at: datetime = field(default_factory=utc_now)
    last_used_at: Optional[datetime] = None
    usage_count: int = 0
    
    # Revocation
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UserId] = None
    revoked_reason: Optional[str] = None
    is_revoked: bool = False
    
    # Audit fields
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self):
        """Validate entity state after initialization."""
        if self.permission_type == PermissionType.USER and not self.user_id:
            raise ValueError("User ID required for user permission type")
        
        if self.permission_type == PermissionType.ROLE and not self.role_code:
            raise ValueError("Role code required for role permission type")
        
        if self.permission_type == PermissionType.TEAM and not self.team_id:
            raise ValueError("Team ID required for team permission type")
        
        if self.permission_type == PermissionType.LINK and not self.share_token:
            # Generate share token if not provided
            self.share_token = self._generate_share_token()
        
        if self.download_count < 0:
            raise ValueError("Download count cannot be negative")
        
        if self.usage_count < 0:
            raise ValueError("Usage count cannot be negative")
        
        # Set default allowed actions based on permission level
        if not self.allowed_actions:
            self._set_default_actions()
    
    def _generate_share_token(self) -> str:
        """Generate a secure share token."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _set_default_actions(self) -> None:
        """Set default allowed actions based on permission level."""
        if self.permission_level == PermissionLevel.NONE:
            self.allowed_actions = set()
        elif self.permission_level == PermissionLevel.READ:
            self.allowed_actions = {"read", "download"}
        elif self.permission_level == PermissionLevel.WRITE:
            self.allowed_actions = {"read", "download", "write", "update"}
        elif self.permission_level == PermissionLevel.ADMIN:
            self.allowed_actions = {"read", "download", "write", "update", "delete", "share"}
        elif self.permission_level == PermissionLevel.OWNER:
            self.allowed_actions = {"read", "download", "write", "update", "delete", "share", "admin"}
    
    @classmethod
    def create_user_permission(cls, file_id: FileId, user_id: UserId, 
                              permission_level: PermissionLevel,
                              granted_by: Optional[UserId] = None,
                              expires_at: Optional[datetime] = None) -> 'FilePermission':
        """Create a user-based permission."""
        permission = cls(
            file_id=file_id,
            permission_type=PermissionType.USER,
            permission_level=permission_level,
            user_id=user_id,
            granted_by=granted_by,
            expires_at=expires_at,
            is_temporary=expires_at is not None
        )
        return permission
    
    @classmethod
    def create_role_permission(cls, file_id: FileId, role_code: RoleCode,
                              permission_level: PermissionLevel,
                              granted_by: Optional[UserId] = None) -> 'FilePermission':
        """Create a role-based permission."""
        permission = cls(
            file_id=file_id,
            permission_type=PermissionType.ROLE,
            permission_level=permission_level,
            role_code=role_code,
            granted_by=granted_by
        )
        return permission
    
    @classmethod
    def create_team_permission(cls, file_id: FileId, team_id: str,
                              permission_level: PermissionLevel,
                              granted_by: Optional[UserId] = None) -> 'FilePermission':
        """Create a team-based permission."""
        permission = cls(
            file_id=file_id,
            permission_type=PermissionType.TEAM,
            permission_level=permission_level,
            team_id=team_id,
            granted_by=granted_by
        )
        return permission
    
    @classmethod
    def create_public_permission(cls, file_id: FileId, permission_level: PermissionLevel,
                                granted_by: Optional[UserId] = None) -> 'FilePermission':
        """Create a public access permission."""
        permission = cls(
            file_id=file_id,
            permission_type=PermissionType.PUBLIC,
            permission_level=permission_level,
            is_public=True,
            granted_by=granted_by
        )
        return permission
    
    @classmethod
    def create_share_link(cls, file_id: FileId, share_link_type: ShareLinkType,
                         granted_by: Optional[UserId] = None,
                         expires_at: Optional[datetime] = None,
                         max_downloads: Optional[int] = None) -> 'FilePermission':
        """Create a share link permission."""
        # Map share link type to permission level
        permission_level_map = {
            ShareLinkType.VIEW_ONLY: PermissionLevel.READ,
            ShareLinkType.DOWNLOAD: PermissionLevel.READ,
            ShareLinkType.EDIT: PermissionLevel.WRITE,
            ShareLinkType.FULL_ACCESS: PermissionLevel.ADMIN
        }
        
        permission = cls(
            file_id=file_id,
            permission_type=PermissionType.LINK,
            permission_level=permission_level_map[share_link_type],
            share_link_type=share_link_type,
            granted_by=granted_by,
            expires_at=expires_at,
            is_temporary=expires_at is not None,
            max_downloads=max_downloads
        )
        return permission
    
    def grant_action(self, action: str) -> None:
        """Grant a specific action."""
        self.allowed_actions.add(action)
        self.denied_actions.discard(action)  # Remove from denied if present
        self.updated_at = utc_now()
    
    def deny_action(self, action: str) -> None:
        """Deny a specific action."""
        self.denied_actions.add(action)
        self.allowed_actions.discard(action)  # Remove from allowed if present
        self.updated_at = utc_now()
    
    def has_action(self, action: str) -> bool:
        """Check if permission allows a specific action."""
        if self.is_expired() or self.is_revoked:
            return False
        
        # Explicit denial takes precedence
        if action in self.denied_actions:
            return False
        
        return action in self.allowed_actions
    
    def can_read(self) -> bool:
        """Check if permission allows reading."""
        return self.has_action("read")
    
    def can_write(self) -> bool:
        """Check if permission allows writing."""
        return self.has_action("write")
    
    def can_delete(self) -> bool:
        """Check if permission allows deletion."""
        return self.has_action("delete")
    
    def can_share(self) -> bool:
        """Check if permission allows sharing."""
        return self.has_action("share")
    
    def can_admin(self) -> bool:
        """Check if permission allows administration."""
        return self.has_action("admin")
    
    def set_expiration(self, expires_at: datetime) -> None:
        """Set permission expiration."""
        self.expires_at = expires_at
        self.is_temporary = True
        self.updated_at = utc_now()
    
    def extend_expiration(self, hours: int) -> None:
        """Extend permission expiration."""
        if not self.expires_at:
            self.expires_at = utc_now() + timedelta(hours=hours)
        else:
            self.expires_at += timedelta(hours=hours)
        
        self.is_temporary = True
        self.updated_at = utc_now()
    
    def remove_expiration(self) -> None:
        """Remove permission expiration (make permanent)."""
        self.expires_at = None
        self.is_temporary = False
        self.updated_at = utc_now()
    
    def is_expired(self) -> bool:
        """Check if permission has expired."""
        if not self.expires_at:
            return False
        
        return utc_now() > self.expires_at
    
    def revoke(self, revoked_by: UserId, reason: Optional[str] = None) -> None:
        """Revoke the permission."""
        self.is_revoked = True
        self.revoked_at = utc_now()
        self.revoked_by = revoked_by
        self.revoked_reason = reason
        self.updated_at = utc_now()
    
    def restore(self) -> None:
        """Restore a revoked permission."""
        self.is_revoked = False
        self.revoked_at = None
        self.revoked_by = None
        self.revoked_reason = None
        self.updated_at = utc_now()
    
    def record_usage(self) -> None:
        """Record permission usage."""
        self.usage_count += 1
        self.last_used_at = utc_now()
        
        # Handle download counting for share links
        if self.permission_type == PermissionType.LINK:
            self.download_count += 1
            
            # Check if max downloads reached
            if self.max_downloads and self.download_count >= self.max_downloads:
                self.revoke(
                    revoked_by=self.granted_by or UserId.generate(),
                    reason="Maximum download limit reached"
                )
        
        # Note: updated_at is not modified for usage tracking to avoid unnecessary updates
    
    def add_ip_restriction(self, ip_address: str) -> None:
        """Add IP address restriction."""
        self.ip_restrictions.add(ip_address)
        self.updated_at = utc_now()
    
    def remove_ip_restriction(self, ip_address: str) -> None:
        """Remove IP address restriction."""
        self.ip_restrictions.discard(ip_address)
        self.updated_at = utc_now()
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed."""
        if not self.ip_restrictions:
            return True
        
        return ip_address in self.ip_restrictions
    
    def set_time_restriction(self, start_hour: int, end_hour: int) -> None:
        """Set time-based access restriction (24-hour format)."""
        if not 0 <= start_hour <= 23 or not 0 <= end_hour <= 23:
            raise ValueError("Hours must be between 0 and 23")
        
        self.time_restrictions = {
            "start_hour": start_hour,
            "end_hour": end_hour
        }
        self.updated_at = utc_now()
    
    def is_time_allowed(self, current_time: Optional[datetime] = None) -> bool:
        """Check if current time is within allowed hours."""
        if not self.time_restrictions:
            return True
        
        if current_time is None:
            current_time = utc_now()
        
        current_hour = current_time.hour
        start_hour = self.time_restrictions.get("start_hour", 0)
        end_hour = self.time_restrictions.get("end_hour", 23)
        
        if start_hour <= end_hour:
            return start_hour <= current_hour <= end_hour
        else:
            # Handles overnight restrictions (e.g., 22:00 to 06:00)
            return current_hour >= start_hour or current_hour <= end_hour
    
    def is_active(self) -> bool:
        """Check if permission is currently active."""
        return not self.is_expired() and not self.is_revoked
    
    def get_effective_level(self) -> PermissionLevel:
        """Get effective permission level considering revocation and expiration."""
        if self.is_revoked or self.is_expired():
            return PermissionLevel.NONE
        
        return self.permission_level
    
    def get_permission_summary(self) -> Dict[str, Any]:
        """Get permission summary information."""
        return {
            "permission_id": self.id,
            "file_id": str(self.file_id),
            "permission_type": self.permission_type.value,
            "permission_level": self.permission_level.value,
            "is_active": self.is_active(),
            "is_expired": self.is_expired(),
            "is_revoked": self.is_revoked,
            "is_inherited": self.is_inherited,
            "is_temporary": self.is_temporary,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "allowed_actions": list(self.allowed_actions),
            "denied_actions": list(self.denied_actions),
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "granted_at": self.granted_at.isoformat(),
            "granted_by": str(self.granted_by) if self.granted_by else None
        }
    
    def __str__(self) -> str:
        """String representation."""
        subject = ""
        if self.permission_type == PermissionType.USER and self.user_id:
            subject = f"user:{self.user_id}"
        elif self.permission_type == PermissionType.ROLE and self.role_code:
            subject = f"role:{self.role_code}"
        elif self.permission_type == PermissionType.TEAM and self.team_id:
            subject = f"team:{self.team_id}"
        elif self.permission_type == PermissionType.PUBLIC:
            subject = "public"
        elif self.permission_type == PermissionType.LINK:
            subject = f"link:{self.share_token[:8] if self.share_token else 'unknown'}"
        
        return f"{subject} -> {self.permission_level.value}"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"FilePermission(id='{self.id}', type='{self.permission_type.value}', level='{self.permission_level.value}')"