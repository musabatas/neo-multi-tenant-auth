"""Upload coordinator protocol.

ONLY upload orchestration contract - defines interface for coordinating
complex upload workflows with validation, processing, and cleanup.

Following maximum separation architecture - one file = one purpose.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO, List, Callable
from typing_extensions import Protocol, runtime_checkable
from datetime import datetime

from ..entities.upload_session import UploadSession
from ..entities.file_metadata import FileMetadata
from ..value_objects.upload_session_id import UploadSessionId
from ..value_objects.file_id import FileId
from ..value_objects.mime_type import MimeType


@runtime_checkable
class UploadCoordinator(Protocol):
    """Upload coordinator protocol.
    
    Defines interface for coordinating complex upload workflows with support for:
    - Upload session lifecycle management
    - Multi-step upload processing (validation, storage, scanning, thumbnails)
    - Progress tracking and status updates
    - Error recovery and retry mechanisms
    - Cleanup of failed uploads
    - Event-driven upload notifications
    """
    
    # Upload session management
    async def initiate_upload(
        self,
        filename: str,
        file_size: int,
        mime_type: MimeType,
        tenant_id: str,
        user_id: str,
        folder_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        upload_options: Optional[Dict[str, Any]] = None
    ) -> UploadSession:
        """Initiate new upload session with validation.
        
        Args:
            filename: Original filename
            file_size: Size of file in bytes
            mime_type: MIME type of file
            tenant_id: Tenant context
            user_id: User performing upload
            folder_path: Destination folder path
            metadata: Additional file metadata
            upload_options: Upload-specific options (chunk_size, etc.)
        
        Returns:
            Created upload session with upload URLs/tokens
        
        Raises:
            InvalidFileType: If file type not allowed
            StorageQuotaExceeded: If upload would exceed quota
            PermissionDenied: If user lacks upload permission
        """
        ...
    
    async def get_upload_session(
        self,
        session_id: UploadSessionId,
        tenant_id: str
    ) -> Optional[UploadSession]:
        """Get upload session by ID with tenant isolation.
        
        Args:
            session_id: Upload session identifier
            tenant_id: Tenant context for isolation
        
        Returns:
            Upload session or None if not found/expired
        """
        ...
    
    async def update_upload_progress(
        self,
        session_id: UploadSessionId,
        bytes_uploaded: int,
        chunk_number: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> UploadSession:
        """Update upload progress for session.
        
        Args:
            session_id: Upload session identifier
            bytes_uploaded: Total bytes uploaded so far
            chunk_number: Current chunk number (for chunked uploads)
            tenant_id: Tenant context for validation
        
        Returns:
            Updated upload session with progress
        """
        ...
    
    async def complete_upload(
        self,
        session_id: UploadSessionId,
        final_checksum: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete upload and trigger post-processing workflow.
        
        Args:
            session_id: Upload session identifier
            final_checksum: Final file checksum for verification
            tenant_id: Tenant context for validation
        
        Returns:
            Dictionary with completion results:
            - file_metadata: Created file metadata
            - processing_status: Status of post-processing steps
            - file_id: Generated file identifier
            - storage_location: Final storage location
            - processing_duration_ms: Time taken for completion
        """
        ...
    
    async def cancel_upload(
        self,
        session_id: UploadSessionId,
        reason: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Cancel upload session and cleanup resources.
        
        Args:
            session_id: Upload session identifier
            reason: Cancellation reason for logging
            tenant_id: Tenant context for validation
        
        Returns:
            True if upload was cancelled successfully
        """
        ...
    
    # Chunked upload coordination
    async def upload_chunk(
        self,
        session_id: UploadSessionId,
        chunk_number: int,
        chunk_data: BinaryIO,
        chunk_checksum: Optional[str] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload single chunk and update session progress.
        
        Args:
            session_id: Upload session identifier
            chunk_number: Sequential chunk number
            chunk_data: Binary chunk data
            chunk_checksum: Checksum for chunk verification
            tenant_id: Tenant context for validation
        
        Returns:
            Dictionary with chunk upload results:
            - chunk_uploaded: Boolean success indicator
            - chunk_id: Storage identifier for chunk
            - upload_progress_percent: Overall upload progress
            - next_chunk_url: URL for next chunk (if applicable)
        """
        ...
    
    async def retry_failed_chunk(
        self,
        session_id: UploadSessionId,
        chunk_number: int,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retry upload of failed chunk.
        
        Args:
            session_id: Upload session identifier
            chunk_number: Chunk number to retry
            tenant_id: Tenant context for validation
        
        Returns:
            Dictionary with retry information:
            - retry_url: URL for chunk retry
            - retry_count: Number of retries attempted
            - max_retries: Maximum retries allowed
        """
        ...
    
    # Upload processing workflow
    async def process_uploaded_file(
        self,
        file_metadata: FileMetadata,
        processing_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process uploaded file through complete workflow.
        
        Args:
            file_metadata: File metadata for processing
            processing_options: Options for processing steps
        
        Returns:
            Dictionary with processing results:
            - virus_scan_result: Virus scanning results
            - thumbnail_generated: Thumbnail generation status
            - content_indexed: Content indexing status
            - processing_errors: Any errors encountered
            - processing_duration_ms: Total processing time
        """
        ...
    
    async def reprocess_file(
        self,
        file_id: FileId,
        processing_steps: List[str],
        tenant_id: str
    ) -> Dict[str, Any]:
        """Reprocess existing file with specified steps.
        
        Args:
            file_id: File identifier to reprocess
            processing_steps: List of processing steps to run
            tenant_id: Tenant context for validation
        
        Returns:
            Dictionary with reprocessing results
        """
        ...
    
    # Batch upload coordination
    async def initiate_batch_upload(
        self,
        files: List[Dict[str, Any]],
        tenant_id: str,
        user_id: str,
        batch_options: Optional[Dict[str, Any]] = None
    ) -> List[UploadSession]:
        """Initiate multiple upload sessions in batch.
        
        Args:
            files: List of file specifications
            tenant_id: Tenant context
            user_id: User performing uploads
            batch_options: Batch-specific options
        
        Returns:
            List of created upload sessions
        """
        ...
    
    async def get_batch_upload_status(
        self,
        session_ids: List[UploadSessionId],
        tenant_id: str
    ) -> Dict[UploadSessionId, Dict[str, Any]]:
        """Get status of multiple upload sessions.
        
        Args:
            session_ids: List of upload session identifiers
            tenant_id: Tenant context for validation
        
        Returns:
            Dictionary mapping session IDs to status information
        """
        ...
    
    # Upload monitoring and statistics
    async def get_active_uploads(
        self,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[UploadSession]:
        """Get currently active upload sessions.
        
        Args:
            tenant_id: Filter by tenant (None for all)
            user_id: Filter by user (None for all)
        
        Returns:
            List of active upload sessions
        """
        ...
    
    async def get_upload_statistics(
        self,
        tenant_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get upload statistics for reporting.
        
        Args:
            tenant_id: Filter by tenant (None for all)
            start_date: Statistics from this date
            end_date: Statistics to this date
        
        Returns:
            Dictionary with upload statistics:
            - total_uploads: Total number of uploads
            - successful_uploads: Number of successful uploads
            - failed_uploads: Number of failed uploads
            - total_bytes_uploaded: Total data uploaded
            - average_upload_time: Average upload duration
            - upload_trends: Upload volume trends
        """
        ...
    
    # Error handling and recovery
    async def handle_upload_failure(
        self,
        session_id: UploadSessionId,
        error_details: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle upload failure and determine recovery actions.
        
        Args:
            session_id: Failed upload session identifier
            error_details: Details about the failure
            tenant_id: Tenant context for validation
        
        Returns:
            Dictionary with failure handling results:
            - recovery_possible: Whether recovery is possible
            - recovery_actions: List of recovery actions to take
            - cleanup_performed: Whether cleanup was performed
            - retry_recommended: Whether retry is recommended
        """
        ...
    
    async def cleanup_expired_uploads(
        self,
        expiration_hours: int = 24,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cleanup expired upload sessions and temporary files.
        
        Args:
            expiration_hours: Hours after which uploads expire
            tenant_id: Filter by tenant (None for all)
        
        Returns:
            Dictionary with cleanup results:
            - sessions_cleaned: Number of sessions cleaned
            - bytes_freed: Amount of storage freed
            - files_removed: Number of temporary files removed
        """
        ...
    
    # Event handling and notifications
    async def register_upload_callback(
        self,
        session_id: UploadSessionId,
        callback_url: str,
        events: List[str],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Register webhook callback for upload events.
        
        Args:
            session_id: Upload session to monitor
            callback_url: URL to notify of events
            events: List of events to notify about
            tenant_id: Tenant context for validation
        
        Returns:
            True if callback was registered successfully
        """
        ...
    
    async def send_upload_notification(
        self,
        session_id: UploadSessionId,
        event_type: str,
        event_data: Dict[str, Any],
        tenant_id: Optional[str] = None
    ) -> bool:
        """Send upload event notification.
        
        Args:
            session_id: Upload session identifier
            event_type: Type of event (started, progress, completed, failed)
            event_data: Event-specific data
            tenant_id: Tenant context for validation
        
        Returns:
            True if notification was sent successfully
        """
        ...
    
    # Configuration and health
    async def get_upload_limits(self, tenant_id: str) -> Dict[str, Any]:
        """Get upload limits and quotas for tenant.
        
        Args:
            tenant_id: Tenant to check limits for
        
        Returns:
            Dictionary with upload limits:
            - max_file_size_mb: Maximum single file size
            - max_concurrent_uploads: Maximum concurrent uploads
            - allowed_file_types: List of allowed MIME types
            - storage_quota_mb: Total storage quota
            - current_usage_mb: Current storage usage
        """
        ...
    
    async def ping(self) -> bool:
        """Health check - verify coordinator is responsive.
        
        Returns:
            True if coordinator is healthy and responsive
        """
        ...