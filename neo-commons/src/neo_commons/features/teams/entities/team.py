"""Team domain entity.

This module defines the Team entity and related business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timezone


from ....config.constants import TeamType


@dataclass
class Team:
    """Team domain entity.
    
    Represents a team within the admin or tenant schema for organizing users.
    Matches both admin.teams and tenant_template.teams table structures.
    """
    
    # Core Identity
    id: str  # UUID PRIMARY KEY
    name: str
    slug: str
    description: Optional[str] = None
    
    # Hierarchy
    parent_team_id: Optional[str] = None  # UUID references teams(id)
    team_path: Optional[str] = None
    team_type: TeamType = TeamType.WORKING_GROUP
    
    # Configuration
    max_members: Optional[int] = None
    is_private: bool = False
    is_active: bool = True
    
    # Ownership
    owner_id: Optional[str] = None  # UUID references users(id)
    
    # Customization
    settings: Dict[str, Any] = field(default_factory=dict)
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Lifecycle
    archived_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Post-initialization validation."""
        # Validate slug format and length
        import re
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', self.slug):
            raise ValueError(f"Invalid team slug format: {self.slug}")
        if not (4 <= len(self.slug) <= 60):
            raise ValueError(f"Team slug length must be 4-60 characters: {self.slug}")
    
    @property
    def is_root_team(self) -> bool:
        """Check if team is a root team (no parent)."""
        return self.parent_team_id is None
    
    @property
    def is_archived(self) -> bool:
        """Check if team is archived."""
        return self.archived_at is not None
    
    @property
    def effective_status(self) -> str:
        """Get effective status considering active and archived flags."""
        if self.is_archived:
            return "archived"
        elif self.is_active:
            return "active"
        else:
            return "inactive"
    
    def deactivate(self) -> None:
        """Deactivate team."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate team."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def archive(self) -> None:
        """Archive team."""
        self.is_active = False
        self.archived_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def unarchive(self) -> None:
        """Unarchive team."""
        self.archived_at = None
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def change_owner(self, new_owner_id: str) -> None:
        """Change team owner."""
        self.owner_id = new_owner_id
        self.updated_at = datetime.now(timezone.utc)
    
    def update_settings(self, new_settings: Dict[str, Any]) -> None:
        """Update team settings."""
        self.settings.update(new_settings)
        self.updated_at = datetime.now(timezone.utc)
    
    def set_custom_field(self, key: str, value: Any) -> None:
        """Set custom field value."""
        self.custom_fields[key] = value
        self.updated_at = datetime.now(timezone.utc)
    
    def update_team_path(self, path: str) -> None:
        """Update team path (used for hierarchical organization)."""
        self.team_path = path
        self.updated_at = datetime.now(timezone.utc)


