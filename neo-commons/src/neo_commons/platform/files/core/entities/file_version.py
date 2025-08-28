"""File version entity.

ONLY file version - represents file version business entity with
version tracking, change management, and restoration capabilities.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

# No base Entity class needed - using plain dataclass
from .....core.value_objects import UserId, TenantId
from .....utils import utc_now
from ..value_objects import (
    FileId, FilePath, FileSize, MimeType, StorageProvider, 
    Checksum, StorageKey
)


class VersionType(Enum):
    """Type of file version."""
    MAJOR = "major"        # Major version (1.0, 2.0, etc.)
    MINOR = "minor"        # Minor version (1.1, 1.2, etc.)
    AUTO = "auto"          # Automatic version (from auto-save, etc.)
    BACKUP = "backup"      # Backup version
    BRANCH = "branch"      # Branch version


@dataclass
class FileVersion:
    """File version entity.
    
    Represents a specific version of a file with complete metadata
    and storage information. Handles version relationships, change
    tracking, and restoration capabilities.
    
    Features:
    - Complete version history tracking
    - Parent-child version relationships
    - Change description and metadata
    - Storage information per version
    - Restoration and rollback support
    - Version comparison utilities
    """
    
    # Core identification
    id: FileId = field(default_factory=lambda: FileId.generate())
    tenant_id: TenantId = field(default_factory=lambda: TenantId.generate())
    
    # Version relationships
    original_file_id: FileId = field(default_factory=lambda: FileId.generate())
    parent_version_id: Optional[FileId] = None
    
    # Version information
    version_number: int = 1
    version_type: VersionType = VersionType.AUTO
    is_current: bool = False
    
    # File properties (snapshot at version creation time)
    original_name: str = ""
    path: FilePath = field(default_factory=lambda: FilePath(""))
    size: FileSize = field(default_factory=lambda: FileSize.zero())
    mime_type: MimeType = field(default_factory=lambda: MimeType("application/octet-stream"))
    checksum: Optional[Checksum] = None
    
    # Storage information for this version
    storage_provider: StorageProvider = field(default_factory=lambda: StorageProvider.local())
    storage_key: StorageKey = field(default_factory=lambda: StorageKey(""))
    storage_region: Optional[str] = None
    
    # Version metadata
    title: Optional[str] = None
    description: Optional[str] = None
    change_description: Optional[str] = None
    version_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Thumbnails and previews for this version
    has_thumbnail: bool = False
    thumbnail_key: Optional[StorageKey] = None
    has_preview: bool = False
    preview_key: Optional[StorageKey] = None
    
    # Version lifecycle
    created_by: Optional[UserId] = None
    created_at: datetime = field(default_factory=utc_now)
    archived_at: Optional[datetime] = None
    is_archived: bool = False
    
    # Restoration tracking
    restored_from_version_id: Optional[FileId] = None
    restored_at: Optional[datetime] = None
    restored_by: Optional[UserId] = None
    
    def __post_init__(self):
        """Validate entity state after initialization."""
        
        if not self.original_name.strip():
            raise ValueError("Original filename cannot be empty")
        
        if self.size.value < 0:
            raise ValueError("File size cannot be negative")
        
        if self.version_number < 1:
            raise ValueError("Version number must be positive")
    
    def set_as_current(self) -> None:
        """Mark this version as the current version."""
        self.is_current = True
        # Note: The caller should handle unmarking other versions
    
    def unset_as_current(self) -> None:
        """Unmark this version as the current version."""
        self.is_current = False
    
    def archive(self) -> None:
        """Archive this version."""
        if self.is_current:
            raise ValueError("Cannot archive current version")
        
        self.is_archived = True
        self.archived_at = utc_now()
    
    def restore(self) -> None:
        """Restore this archived version."""
        self.is_archived = False
        self.archived_at = None
    
    def set_change_description(self, description: str) -> None:
        """Set change description for this version."""
        self.change_description = description.strip() if description else None
    
    def set_version_notes(self, notes: str) -> None:
        """Set version notes."""
        self.version_notes = notes.strip() if notes else None
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update version metadata."""
        self.metadata.update(metadata)
    
    def set_storage_info(self, provider: StorageProvider, key: StorageKey, region: Optional[str] = None) -> None:
        """Set storage information for this version."""
        self.storage_provider = provider
        self.storage_key = key
        self.storage_region = region
    
    def set_thumbnail(self, thumbnail_key: StorageKey) -> None:
        """Set thumbnail for this version."""
        self.has_thumbnail = True
        self.thumbnail_key = thumbnail_key
    
    def set_preview(self, preview_key: StorageKey) -> None:
        """Set preview for this version."""
        self.has_preview = True
        self.preview_key = preview_key
    
    def create_child_version(self, version_type: VersionType = VersionType.AUTO, 
                           change_description: Optional[str] = None) -> 'FileVersion':
        """Create a new child version based on this version."""
        child_version = FileVersion(
            id=FileId.generate(),
            tenant_id=self.tenant_id,
            original_file_id=self.original_file_id,
            parent_version_id=self.id,
            version_number=self._get_next_version_number(),
            version_type=version_type,
            is_current=False,  # Will be set explicitly if needed
            original_name=self.original_name,
            path=self.path,
            size=self.size,
            mime_type=self.mime_type,
            storage_provider=self.storage_provider,
            title=self.title,
            description=self.description,
            change_description=change_description,
            metadata=self.metadata.copy(),
            created_at=utc_now()
        )
        
        return child_version
    
    def _get_next_version_number(self) -> int:
        """Get next version number (simplified - in real implementation, this would query the repository)."""
        return self.version_number + 1
    
    def mark_as_restored_from(self, source_version_id: FileId, restored_by: UserId) -> None:
        """Mark this version as restored from another version."""
        self.restored_from_version_id = source_version_id
        self.restored_at = utc_now()
        self.restored_by = restored_by
    
    def is_restored_version(self) -> bool:
        """Check if this version was created from restoration."""
        return self.restored_from_version_id is not None
    
    def is_major_version(self) -> bool:
        """Check if this is a major version."""
        return self.version_type == VersionType.MAJOR
    
    def is_minor_version(self) -> bool:
        """Check if this is a minor version."""
        return self.version_type == VersionType.MINOR
    
    def is_auto_version(self) -> bool:
        """Check if this is an auto-generated version."""
        return self.version_type == VersionType.AUTO
    
    def is_backup_version(self) -> bool:
        """Check if this is a backup version."""
        return self.version_type == VersionType.BACKUP
    
    def is_image(self) -> bool:
        """Check if this version is an image."""
        return self.mime_type.is_image()
    
    def is_document(self) -> bool:
        """Check if this version is a document."""
        return self.mime_type.is_document()
    
    def can_have_thumbnail(self) -> bool:
        """Check if this version can have thumbnails."""
        return self.is_image() or self.mime_type.value == "application/pdf"
    
    def can_have_preview(self) -> bool:
        """Check if this version can have previews."""
        return self.is_image() or self.is_document() or self.mime_type.is_text()
    
    def get_display_name(self) -> str:
        """Get display name for this version."""
        base_name = self.title if self.title else self.original_name
        return f"{base_name} (v{self.version_number})"
    
    def get_version_summary(self) -> Dict[str, Any]:
        """Get version summary information."""
        return {
            "version_id": str(self.id),
            "version_number": self.version_number,
            "version_type": self.version_type.value,
            "is_current": self.is_current,
            "is_archived": self.is_archived,
            "filename": self.original_name,
            "size": self.size.value,
            "mime_type": self.mime_type.value,
            "change_description": self.change_description,
            "created_at": self.created_at.isoformat(),
            "created_by": str(self.created_by) if self.created_by else None,
            "has_thumbnail": self.has_thumbnail,
            "has_preview": self.has_preview,
            "is_restored": self.is_restored_version()
        }
    
    def calculate_size_difference(self, other_version: 'FileVersion') -> int:
        """Calculate size difference with another version."""
        return self.size.value - other_version.size.value
    
    def is_same_content(self, other_version: 'FileVersion') -> bool:
        """Check if this version has same content as another version (by checksum)."""
        if not self.checksum or not other_version.checksum:
            return False
        
        return self.checksum.secure_compare(other_version.checksum)
    
    def __str__(self) -> str:
        """String representation."""
        return self.get_display_name()
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"FileVersion(id='{self.id}', version={self.version_number}, current={self.is_current})"