"""Upload session entity.

ONLY upload session - represents upload session business entity with
chunk tracking, progress management, and completion handling.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set
from enum import Enum

# No base Entity class needed - using plain dataclass
from .....core.value_objects import UserId, TenantId
from .....utils import utc_now
from ..value_objects import (
    UploadSessionId, FileId, FilePath, FileSize, MimeType,
    StorageProvider, Checksum
)


class UploadStatus(Enum):
    """Upload session status."""
    INITIALIZED = "initialized"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class UploadType(Enum):
    """Type of upload session."""
    SINGLE = "single"          # Single file upload
    CHUNKED = "chunked"        # Multi-part chunked upload
    MULTIPART = "multipart"    # S3 multipart upload
    RESUMABLE = "resumable"    # Resumable upload with state recovery


@dataclass
class ChunkInfo:
    """Information about an uploaded chunk."""
    chunk_number: int
    chunk_size: int
    checksum: Optional[Checksum] = None
    uploaded_at: datetime = field(default_factory=utc_now)
    etag: Optional[str] = None  # S3 ETag for multipart uploads


@dataclass
class UploadSession:
    """Upload session entity.
    
    Represents an upload session for tracking file uploads, especially
    multi-part, chunked, and resumable uploads. Manages upload progress,
    chunk tracking, and session lifecycle.
    
    Features:
    - Multi-part upload coordination
    - Chunk progress tracking
    - Resume capability for interrupted uploads
    - Expiration handling
    - Storage provider integration
    - Upload validation and completion
    """
    
    # Core identification
    id: UploadSessionId = field(default_factory=lambda: UploadSessionId.generate())
    tenant_id: TenantId = field(default_factory=lambda: TenantId.generate())
    
    # Target file information
    target_file_id: Optional[FileId] = None
    original_filename: str = ""
    target_path: FilePath = field(default_factory=lambda: FilePath(""))
    
    # File properties
    expected_size: FileSize = field(default_factory=lambda: FileSize.zero())
    expected_mime_type: MimeType = field(default_factory=lambda: MimeType("application/octet-stream"))
    expected_checksum: Optional[Checksum] = None
    
    # Upload configuration
    upload_type: UploadType = UploadType.SINGLE
    storage_provider: StorageProvider = field(default_factory=lambda: StorageProvider.local())
    chunk_size: int = 5 * 1024 * 1024  # 5MB default chunk size
    
    # Progress tracking
    status: UploadStatus = UploadStatus.INITIALIZED
    uploaded_size: int = 0
    total_chunks: int = 0
    completed_chunks: Set[int] = field(default_factory=set)
    chunk_info: Dict[int, ChunkInfo] = field(default_factory=dict)
    
    # Storage-specific information
    storage_upload_id: Optional[str] = None  # S3 multipart upload ID
    storage_key: Optional[str] = None
    storage_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Session metadata
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Ownership and permissions
    created_by: UserId = field(default_factory=lambda: UserId.generate())
    
    # Session lifecycle
    expires_at: datetime = field(default_factory=lambda: utc_now() + timedelta(hours=24))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # Error handling
    failure_reason: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Configuration
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Audit fields
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    
    def __post_init__(self):
        """Validate entity state after initialization."""
        
        if not self.original_filename.strip():
            raise ValueError("Original filename cannot be empty")
        
        if self.expected_size.value < 0:
            raise ValueError("Expected file size cannot be negative")
        
        if self.chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        
        if self.uploaded_size < 0:
            raise ValueError("Uploaded size cannot be negative")
        
        if self.total_chunks < 0:
            raise ValueError("Total chunks cannot be negative")
        
        if self.retry_count < 0:
            raise ValueError("Retry count cannot be negative")
        
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")
        
        # Calculate total chunks if expected size is known
        if self.expected_size.value > 0 and self.total_chunks == 0:
            self.total_chunks = self._calculate_total_chunks()
    
    def _calculate_total_chunks(self) -> int:
        """Calculate total number of chunks based on file size and chunk size."""
        if self.expected_size.value == 0:
            return 0
        
        return (self.expected_size.value + self.chunk_size - 1) // self.chunk_size
    
    def start_upload(self, storage_upload_id: Optional[str] = None, 
                    storage_key: Optional[str] = None) -> None:
        """Start the upload session."""
        if self.status != UploadStatus.INITIALIZED:
            raise ValueError(f"Cannot start upload: session status is {self.status.value}")
        
        if self.is_expired():
            raise ValueError("Cannot start upload: session has expired")
        
        self.status = UploadStatus.IN_PROGRESS
        self.started_at = utc_now()
        
        if storage_upload_id:
            self.storage_upload_id = storage_upload_id
        
        if storage_key:
            self.storage_key = storage_key
        
        self.updated_at = utc_now()
    
    def add_chunk(self, chunk_number: int, chunk_size: int, 
                 checksum: Optional[Checksum] = None, etag: Optional[str] = None) -> None:
        """Add a completed chunk to the upload session."""
        if self.status not in {UploadStatus.INITIALIZED, UploadStatus.IN_PROGRESS}:
            raise ValueError(f"Cannot add chunk: session status is {self.status.value}")
        
        if self.is_expired():
            raise ValueError("Cannot add chunk: session has expired")
        
        if chunk_number < 1:
            raise ValueError("Chunk number must be positive")
        
        if chunk_size <= 0:
            raise ValueError("Chunk size must be positive")
        
        # Start session if not already started
        if self.status == UploadStatus.INITIALIZED:
            self.start_upload()
        
        # Record chunk info
        chunk_info = ChunkInfo(
            chunk_number=chunk_number,
            chunk_size=chunk_size,
            checksum=checksum,
            etag=etag,
            uploaded_at=utc_now()
        )
        
        self.chunk_info[chunk_number] = chunk_info
        self.completed_chunks.add(chunk_number)
        
        # Update uploaded size (handle potential duplicates)
        if chunk_number not in self.completed_chunks or chunk_number not in self.chunk_info:
            self.uploaded_size += chunk_size
        else:
            # Update size if chunk was re-uploaded with different size
            old_size = self.chunk_info.get(chunk_number, ChunkInfo(0, 0)).chunk_size
            self.uploaded_size += chunk_size - old_size
        
        self.updated_at = utc_now()
        
        # Check if upload is complete
        if self.is_upload_complete():
            self._complete_upload()
    
    def remove_chunk(self, chunk_number: int) -> None:
        """Remove a chunk from the upload session (for retry scenarios)."""
        if chunk_number in self.completed_chunks:
            chunk_info = self.chunk_info.get(chunk_number)
            if chunk_info:
                self.uploaded_size -= chunk_info.chunk_size
                del self.chunk_info[chunk_number]
            
            self.completed_chunks.remove(chunk_number)
            self.updated_at = utc_now()
    
    def get_missing_chunks(self) -> List[int]:
        """Get list of chunks that still need to be uploaded."""
        if self.total_chunks == 0:
            return []
        
        all_chunks = set(range(1, self.total_chunks + 1))
        return sorted(all_chunks - self.completed_chunks)
    
    def get_progress_percentage(self) -> float:
        """Get upload progress as percentage (0.0 to 100.0)."""
        if self.expected_size.value == 0:
            return 0.0
        
        return min((self.uploaded_size / self.expected_size.value) * 100.0, 100.0)
    
    def is_upload_complete(self) -> bool:
        """Check if all chunks have been uploaded."""
        if self.total_chunks == 0:
            return self.uploaded_size >= self.expected_size.value
        
        return len(self.completed_chunks) >= self.total_chunks
    
    def _complete_upload(self) -> None:
        """Mark upload as completed."""
        self.status = UploadStatus.COMPLETED
        self.completed_at = utc_now()
        self.updated_at = utc_now()
    
    def complete_upload(self, final_checksum: Optional[Checksum] = None) -> None:
        """Manually complete the upload session."""
        if self.status != UploadStatus.IN_PROGRESS:
            raise ValueError(f"Cannot complete upload: session status is {self.status.value}")
        
        if not self.is_upload_complete():
            missing_chunks = self.get_missing_chunks()
            raise ValueError(f"Cannot complete upload: missing chunks {missing_chunks}")
        
        if final_checksum:
            self.expected_checksum = final_checksum
        
        self._complete_upload()
    
    def fail_upload(self, reason: str) -> None:
        """Mark upload as failed."""
        self.status = UploadStatus.FAILED
        self.failure_reason = reason
        self.failed_at = utc_now()
        self.updated_at = utc_now()
    
    def cancel_upload(self) -> None:
        """Cancel the upload session."""
        if self.status in {UploadStatus.COMPLETED, UploadStatus.FAILED, UploadStatus.EXPIRED}:
            raise ValueError(f"Cannot cancel upload: session status is {self.status.value}")
        
        self.status = UploadStatus.CANCELLED
        self.cancelled_at = utc_now()
        self.updated_at = utc_now()
    
    def retry_upload(self) -> None:
        """Retry a failed upload."""
        if self.status != UploadStatus.FAILED:
            raise ValueError(f"Cannot retry upload: session status is {self.status.value}")
        
        if self.retry_count >= self.max_retries:
            raise ValueError(f"Cannot retry upload: maximum retries ({self.max_retries}) reached")
        
        self.status = UploadStatus.IN_PROGRESS
        self.retry_count += 1
        self.failure_reason = None
        self.failed_at = None
        self.updated_at = utc_now()
    
    def extend_expiration(self, hours: int = 24) -> None:
        """Extend session expiration."""
        if hours <= 0:
            raise ValueError("Extension hours must be positive")
        
        self.expires_at = utc_now() + timedelta(hours=hours)
        self.updated_at = utc_now()
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return utc_now() > self.expires_at
    
    def mark_expired(self) -> None:
        """Mark session as expired."""
        if self.status in {UploadStatus.COMPLETED, UploadStatus.CANCELLED}:
            return  # Don't change status for completed/cancelled uploads
        
        self.status = UploadStatus.EXPIRED
        self.updated_at = utc_now()
    
    def can_resume(self) -> bool:
        """Check if upload can be resumed."""
        return (
            self.status == UploadStatus.IN_PROGRESS and
            not self.is_expired() and
            self.upload_type in {UploadType.CHUNKED, UploadType.MULTIPART, UploadType.RESUMABLE}
        )
    
    def get_next_chunk_number(self) -> int:
        """Get the next chunk number to upload."""
        if not self.completed_chunks:
            return 1
        
        # Find first missing chunk
        for chunk_num in range(1, self.total_chunks + 1):
            if chunk_num not in self.completed_chunks:
                return chunk_num
        
        # All chunks completed
        return self.total_chunks + 1
    
    def get_upload_summary(self) -> Dict[str, Any]:
        """Get upload session summary."""
        return {
            "session_id": str(self.id),
            "filename": self.original_filename,
            "status": self.status.value,
            "upload_type": self.upload_type.value,
            "progress_percentage": self.get_progress_percentage(),
            "uploaded_size": self.uploaded_size,
            "expected_size": self.expected_size.value,
            "completed_chunks": len(self.completed_chunks),
            "total_chunks": self.total_chunks,
            "is_expired": self.is_expired(),
            "can_resume": self.can_resume(),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "failure_reason": self.failure_reason,
            "retry_count": self.retry_count
        }
    
    def __str__(self) -> str:
        """String representation."""
        return f"{self.original_filename} ({self.get_progress_percentage():.1f}%)"
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"UploadSession(id='{self.id}', filename='{self.original_filename}', status='{self.status.value}')"