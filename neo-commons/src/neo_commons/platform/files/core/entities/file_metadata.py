"""File metadata entity.

ONLY file metadata - represents file business entity with metadata,
lifecycle management, and state transitions.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, Set
from enum import Enum

# No base Entity class needed - using plain dataclass
from .....core.value_objects import UserId, TenantId
from .....utils import generate_uuid_v7, utc_now
from ..value_objects import (
    FileId, FilePath, FileSize, MimeType, StorageProvider, 
    Checksum, StorageKey
)


class FileStatus(Enum):
    """File processing status."""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    AVAILABLE = "available"
    QUARANTINED = "quarantined"
    DELETED = "deleted"
    FAILED = "failed"


class VirusStatus(Enum):
    """Virus scanning status."""
    PENDING = "pending"
    SCANNING = "scanning"
    CLEAN = "clean"
    INFECTED = "infected"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileMetadata:
    """File metadata entity.
    
    Represents a file in the system with its metadata, storage information,
    and lifecycle state. Handles business logic for file operations,
    permissions, and state transitions.
    
    Features:
    - Complete file lifecycle management
    - Storage provider abstraction
    - Virus scanning integration
    - Version tracking support
    - Metadata and tag management
    - Access control integration
    """
    
    # Core identification
    id: FileId = field(default_factory=lambda: FileId.generate())
    tenant_id: TenantId = field(default_factory=lambda: TenantId.generate())
    
    # File properties
    original_name: str = ""
    path: FilePath = field(default_factory=lambda: FilePath(""))
    size: FileSize = field(default_factory=lambda: FileSize.zero())
    mime_type: MimeType = field(default_factory=lambda: MimeType("application/octet-stream"))
    checksum: Optional[Checksum] = None
    
    # Storage information
    storage_provider: StorageProvider = field(default_factory=lambda: StorageProvider.local())
    storage_key: Optional[StorageKey] = None
    storage_region: Optional[str] = None
    
    # Status tracking
    status: FileStatus = FileStatus.UPLOADING
    virus_status: VirusStatus = VirusStatus.PENDING
    
    # Ownership and permissions
    created_by: Optional[UserId] = None
    owned_by: Optional[UserId] = None
    
    # Metadata
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Versioning
    version: int = 1
    is_latest_version: bool = True
    parent_version_id: Optional[FileId] = None
    
    # Folders and organization
    parent_folder_id: Optional[FileId] = None
    folder_path: Optional[str] = None
    
    # Thumbnails and previews
    has_thumbnail: bool = False
    thumbnail_key: Optional[StorageKey] = None
    has_preview: bool = False
    preview_key: Optional[StorageKey] = None
    
    # Sharing and access
    is_public: bool = False
    public_url: Optional[str] = None
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    
    # Audit fields
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate entity state after initialization."""
        
        if not self.original_name.strip():
            raise ValueError("Original filename cannot be empty")
        
        if self.size.value < 0:
            raise ValueError("File size cannot be negative")
        
        if self.version < 1:
            raise ValueError("File version must be positive")
        
        if self.access_count < 0:
            raise ValueError("Access count cannot be negative")
    
    def mark_as_processing(self) -> None:
        """Mark file as being processed."""
        if self.status != FileStatus.UPLOADING:
            raise ValueError(f"Cannot mark as processing: file status is {self.status.value}")
        
        self.status = FileStatus.PROCESSING
        self.updated_at = utc_now()
    
    def mark_as_available(self) -> None:
        """Mark file as available for use."""
        if self.status not in {FileStatus.PROCESSING, FileStatus.UPLOADING}:
            raise ValueError(f"Cannot mark as available: file status is {self.status.value}")
        
        self.status = FileStatus.AVAILABLE
        self.updated_at = utc_now()
    
    def mark_as_quarantined(self, reason: str = "") -> None:
        """Mark file as quarantined due to security issues."""
        self.status = FileStatus.QUARANTINED
        if reason:
            self.metadata["quarantine_reason"] = reason
        self.updated_at = utc_now()
    
    def mark_as_failed(self, error: str = "") -> None:
        """Mark file processing as failed."""
        self.status = FileStatus.FAILED
        if error:
            self.metadata["failure_reason"] = error
        self.updated_at = utc_now()
    
    def soft_delete(self) -> None:
        """Soft delete the file."""
        self.status = FileStatus.DELETED
        self.deleted_at = utc_now()
        self.updated_at = utc_now()
    
    def restore(self) -> None:
        """Restore a soft-deleted file."""
        if self.status != FileStatus.DELETED:
            raise ValueError("Cannot restore: file is not deleted")
        
        self.status = FileStatus.AVAILABLE
        self.deleted_at = None
        self.updated_at = utc_now()
    
    def update_virus_status(self, status: VirusStatus, scan_result: str = "") -> None:
        """Update virus scanning status."""
        self.virus_status = status
        
        if scan_result:
            self.metadata["virus_scan_result"] = scan_result
        
        # Handle infected files
        if status == VirusStatus.INFECTED:
            self.mark_as_quarantined("Virus detected during scan")
        
        self.updated_at = utc_now()
    
    def set_storage_info(self, provider: StorageProvider, key: StorageKey, region: Optional[str] = None) -> None:
        """Set storage provider information."""
        self.storage_provider = provider
        self.storage_key = key
        self.storage_region = region
        self.updated_at = utc_now()
    
    def set_checksum(self, checksum: Checksum) -> None:
        """Set file checksum for integrity verification."""
        self.checksum = checksum
        self.updated_at = utc_now()
    
    def update_metadata(self, title: Optional[str] = None, description: Optional[str] = None, 
                       tags: Optional[Set[str]] = None, custom_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update file metadata."""
        if title is not None:
            self.title = title.strip() if title.strip() else None
        
        if description is not None:
            self.description = description.strip() if description.strip() else None
        
        if tags is not None:
            # Normalize tags (lowercase, strip whitespace, remove empty)
            self.tags = {tag.strip().lower() for tag in tags if tag.strip()}
        
        if custom_metadata is not None:
            self.metadata.update(custom_metadata)
        
        self.updated_at = utc_now()
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the file."""
        if not tag or not tag.strip():
            return
        
        normalized_tag = tag.strip().lower()
        self.tags.add(normalized_tag)
        self.updated_at = utc_now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the file."""
        if not tag or not tag.strip():
            return
        
        normalized_tag = tag.strip().lower()
        self.tags.discard(normalized_tag)
        self.updated_at = utc_now()
    
    def has_tag(self, tag: str) -> bool:
        """Check if file has a specific tag."""
        if not tag or not tag.strip():
            return False
        
        normalized_tag = tag.strip().lower()
        return normalized_tag in self.tags
    
    def set_thumbnail(self, thumbnail_key: StorageKey) -> None:
        """Set thumbnail information."""
        self.has_thumbnail = True
        self.thumbnail_key = thumbnail_key
        self.updated_at = utc_now()
    
    def set_preview(self, preview_key: StorageKey) -> None:
        """Set preview information."""
        self.has_preview = True
        self.preview_key = preview_key
        self.updated_at = utc_now()
    
    def set_parent_folder(self, folder_id: FileId, folder_path: str) -> None:
        """Set parent folder information."""
        self.parent_folder_id = folder_id
        self.folder_path = folder_path.strip()
        self.updated_at = utc_now()
    
    def make_public(self, public_url: str) -> None:
        """Make file publicly accessible."""
        self.is_public = True
        self.public_url = public_url
        self.updated_at = utc_now()
    
    def make_private(self) -> None:
        """Make file private."""
        self.is_public = False
        self.public_url = None
        self.updated_at = utc_now()
    
    def record_access(self) -> None:
        """Record file access for analytics."""
        self.access_count += 1
        self.last_accessed_at = utc_now()
        # Note: updated_at is not modified for access tracking to avoid unnecessary updates
    
    def create_version(self) -> 'FileMetadata':
        """Create a new version of this file."""
        # Mark current version as not latest
        self.is_latest_version = False
        self.updated_at = utc_now()
        
        # Create new version
        new_version = FileMetadata(
            id=FileId.generate(),
            tenant_id=self.tenant_id,
            original_name=self.original_name,
            path=self.path,
            size=self.size,
            mime_type=self.mime_type,
            storage_provider=self.storage_provider,
            status=FileStatus.UPLOADING,
            virus_status=VirusStatus.PENDING,
            created_by=self.created_by,
            owned_by=self.owned_by,
            title=self.title,
            description=self.description,
            tags=self.tags.copy(),
            metadata=self.metadata.copy(),
            version=self.version + 1,
            is_latest_version=True,
            parent_version_id=self.id,
            parent_folder_id=self.parent_folder_id,
            folder_path=self.folder_path,
            created_at=utc_now(),
            updated_at=utc_now()
        )
        
        return new_version
    
    def is_available(self) -> bool:
        """Check if file is available for use."""
        return self.status == FileStatus.AVAILABLE and self.virus_status in {
            VirusStatus.CLEAN, VirusStatus.SKIPPED
        }
    
    def is_processing(self) -> bool:
        """Check if file is being processed."""
        return self.status in {FileStatus.UPLOADING, FileStatus.PROCESSING}
    
    def is_deleted(self) -> bool:
        """Check if file is deleted."""
        return self.status == FileStatus.DELETED
    
    def is_quarantined(self) -> bool:
        """Check if file is quarantined."""
        return self.status == FileStatus.QUARANTINED or self.virus_status == VirusStatus.INFECTED
    
    def is_image(self) -> bool:
        """Check if file is an image."""
        return self.mime_type.is_image()
    
    def is_document(self) -> bool:
        """Check if file is a document."""
        return self.mime_type.is_document()
    
    def is_media(self) -> bool:
        """Check if file is media (image, video, audio)."""
        return self.mime_type.is_media()
    
    def can_have_thumbnail(self) -> bool:
        """Check if file type supports thumbnails."""
        return self.is_image() or self.mime_type.value == "application/pdf"
    
    def can_have_preview(self) -> bool:
        """Check if file type supports previews."""
        return self.is_image() or self.is_document() or self.mime_type.is_text()
    
    def get_display_name(self) -> str:
        """Get display name for the file."""
        return self.title if self.title else self.original_name
    
    def get_file_extension(self) -> str:
        """Get file extension from original name."""
        if '.' not in self.original_name:
            return ""
        return '.' + self.original_name.split('.')[-1].lower()
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.get_display_name()} ({self.size})"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"FileMetadata(id='{self.id}', name='{self.original_name}', status='{self.status.value}')"