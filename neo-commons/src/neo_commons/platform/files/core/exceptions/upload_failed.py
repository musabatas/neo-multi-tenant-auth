"""Upload failed exception for file management platform infrastructure.

ONLY upload failed - represents when a file upload operation fails
at any stage of the upload process.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Dict, Optional

from .....core.exceptions import APIError
from ..value_objects import UploadSessionId, FileId, FileSize


class UploadFailed(APIError):
    """Raised when a file upload operation fails.
    
    This exception represents failures during any stage of the file upload
    process including validation, storage, metadata creation, or cleanup.
    """
    
    def __init__(
        self,
        message: str,
        upload_session_id: Optional[UploadSessionId] = None,
        file_id: Optional[FileId] = None,
        filename: Optional[str] = None,
        file_size: Optional[FileSize] = None,
        upload_stage: Optional[str] = None,
        storage_provider: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        bytes_uploaded: Optional[int] = None,
        total_chunks: Optional[int] = None,
        failed_chunk: Optional[int] = None,
        retry_count: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize upload failed exception.
        
        Args:
            message: Human-readable error message
            upload_session_id: ID of the upload session that failed
            file_id: ID of the file being uploaded
            filename: Original filename being uploaded
            file_size: Size of the file being uploaded
            upload_stage: Stage where upload failed (validation, chunk_upload, finalization, etc.)
            storage_provider: Storage provider being used (local, s3)
            tenant_id: Tenant context for multi-tenant isolation
            user_id: User performing the upload
            bytes_uploaded: Number of bytes successfully uploaded before failure
            total_chunks: Total number of chunks for chunked upload
            failed_chunk: Chunk number that failed (for chunked uploads)
            retry_count: Number of retry attempts made
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if upload_session_id:
            enhanced_details["upload_session_id"] = str(upload_session_id)
        if file_id:
            enhanced_details["file_id"] = str(file_id)
        if filename:
            enhanced_details["filename"] = filename
        if file_size:
            enhanced_details["file_size"] = str(file_size)
            enhanced_details["file_size_bytes"] = file_size.bytes
        if upload_stage:
            enhanced_details["upload_stage"] = upload_stage
        if storage_provider:
            enhanced_details["storage_provider"] = storage_provider
        if tenant_id:
            enhanced_details["tenant_id"] = tenant_id
        if user_id:
            enhanced_details["user_id"] = user_id
        if bytes_uploaded is not None:
            enhanced_details["bytes_uploaded"] = bytes_uploaded
        if total_chunks is not None:
            enhanced_details["total_chunks"] = total_chunks
        if failed_chunk is not None:
            enhanced_details["failed_chunk"] = failed_chunk
        if retry_count is not None:
            enhanced_details["retry_count"] = retry_count
            
        super().__init__(
            message=message,
            error_code=error_code or "UPLOAD_FAILED",
            details=enhanced_details
        )
        
        # Store upload-specific fields
        self.upload_session_id = upload_session_id
        self.file_id = file_id
        self.filename = filename
        self.file_size = file_size
        self.upload_stage = upload_stage
        self.storage_provider = storage_provider
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.bytes_uploaded = bytes_uploaded
        self.total_chunks = total_chunks
        self.failed_chunk = failed_chunk
        self.retry_count = retry_count