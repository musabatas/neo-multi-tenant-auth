"""Storage provider protocol.

ONLY storage backend contract - defines interface for storage provider
implementations supporting local filesystem and cloud storage.

Following maximum separation architecture - one file = one purpose.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, BinaryIO, AsyncIterator
from typing_extensions import Protocol, runtime_checkable

from ..value_objects.storage_key import StorageKey
from ..value_objects.file_size import FileSize
from ..value_objects.checksum import Checksum
from ..value_objects.upload_session_id import UploadSessionId


@runtime_checkable 
class StorageProviderProtocol(Protocol):
    """Storage provider protocol.
    
    Defines interface for storage backend implementations with support for:
    - Basic file operations (upload, download, delete)
    - Chunked/multipart uploads for large files
    - Pre-signed URL generation for direct uploads
    - Storage metadata and statistics
    - Health monitoring and diagnostics
    - Tenant isolation through key prefixing
    """
    
    # Basic file operations
    async def upload_file(
        self,
        storage_key: StorageKey,
        content: BinaryIO,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload file to storage.
        
        Args:
            storage_key: Unique key for file in storage
            content: File content as binary stream
            content_type: MIME type of the content
            metadata: Additional metadata to store with file
        
        Returns:
            Dictionary with upload results including:
            - size_bytes: Size of uploaded file
            - checksum: Checksum of uploaded content
            - version_id: Storage version identifier (if versioning enabled)
            - url: Access URL (if applicable)
        """
        ...
    
    async def download_file(
        self,
        storage_key: StorageKey
    ) -> Optional[BinaryIO]:
        """Download file from storage.
        
        Args:
            storage_key: Key of file to download
        
        Returns:
            Binary stream of file content, or None if not found
        """
        ...
    
    async def delete_file(self, storage_key: StorageKey) -> bool:
        """Delete file from storage.
        
        Args:
            storage_key: Key of file to delete
        
        Returns:
            True if file existed and was deleted, False if not found
        """
        ...
    
    async def file_exists(self, storage_key: StorageKey) -> bool:
        """Check if file exists in storage.
        
        Args:
            storage_key: Key of file to check
        
        Returns:
            True if file exists, False otherwise
        """
        ...
    
    async def get_file_info(self, storage_key: StorageKey) -> Optional[Dict[str, Any]]:
        """Get file metadata from storage.
        
        Args:
            storage_key: Key of file to inspect
        
        Returns:
            Dictionary with file info including:
            - size_bytes: File size in bytes
            - last_modified: Last modification timestamp
            - content_type: MIME type
            - checksum: File checksum
            - version_id: Storage version identifier
            - metadata: Custom metadata
        """
        ...
    
    # Chunked/multipart upload operations
    async def initiate_multipart_upload(
        self,
        storage_key: StorageKey,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadSessionId:
        """Initiate multipart upload session.
        
        Args:
            storage_key: Key where file will be stored
            content_type: MIME type of the content
            metadata: Additional metadata to store with file
        
        Returns:
            Upload session identifier for subsequent chunk uploads
        """
        ...
    
    async def upload_chunk(
        self,
        session_id: UploadSessionId,
        chunk_number: int,
        chunk_data: BinaryIO,
        chunk_size: int
    ) -> Dict[str, Any]:
        """Upload a single chunk in multipart upload.
        
        Args:
            session_id: Upload session identifier
            chunk_number: Sequential chunk number (1-based)
            chunk_data: Binary data for this chunk
            chunk_size: Size of chunk in bytes
        
        Returns:
            Dictionary with chunk upload results including:
            - chunk_number: Confirmed chunk number
            - etag: Chunk identifier for completion
            - size_bytes: Actual chunk size uploaded
        """
        ...
    
    async def complete_multipart_upload(
        self,
        session_id: UploadSessionId,
        chunk_info: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Complete multipart upload by assembling chunks.
        
        Args:
            session_id: Upload session identifier
            chunk_info: List of chunk information from upload_chunk calls
        
        Returns:
            Dictionary with final upload results (same as upload_file)
        """
        ...
    
    async def abort_multipart_upload(self, session_id: UploadSessionId) -> bool:
        """Abort multipart upload and clean up chunks.
        
        Args:
            session_id: Upload session identifier
        
        Returns:
            True if upload was aborted successfully
        """
        ...
    
    async def list_upload_parts(
        self,
        session_id: UploadSessionId
    ) -> List[Dict[str, Any]]:
        """List uploaded parts for multipart upload.
        
        Args:
            session_id: Upload session identifier
        
        Returns:
            List of uploaded parts with chunk_number and etag
        """
        ...
    
    # Pre-signed URL operations (for direct client uploads)
    async def generate_presigned_upload_url(
        self,
        storage_key: StorageKey,
        content_type: Optional[str] = None,
        expires_in_seconds: int = 3600,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate pre-signed URL for direct client upload.
        
        Args:
            storage_key: Key where file will be stored
            content_type: Required MIME type
            expires_in_seconds: URL expiration time
            conditions: Upload conditions (size limits, etc.)
        
        Returns:
            Dictionary with:
            - upload_url: Pre-signed upload URL
            - fields: Additional form fields required
            - expires_at: URL expiration timestamp
        """
        ...
    
    async def generate_presigned_download_url(
        self,
        storage_key: StorageKey,
        expires_in_seconds: int = 3600
    ) -> Optional[str]:
        """Generate pre-signed URL for file download.
        
        Args:
            storage_key: Key of file to download
            expires_in_seconds: URL expiration time
        
        Returns:
            Pre-signed download URL, or None if file not found
        """
        ...
    
    # Batch operations
    async def upload_files(
        self,
        files: List[Dict[str, Any]]
    ) -> Dict[StorageKey, Dict[str, Any]]:
        """Upload multiple files in batch.
        
        Args:
            files: List of file upload specifications
        
        Returns:
            Dictionary mapping storage keys to upload results
        """
        ...
    
    async def delete_files(
        self,
        storage_keys: List[StorageKey]
    ) -> Dict[StorageKey, bool]:
        """Delete multiple files in batch.
        
        Args:
            storage_keys: List of keys to delete
        
        Returns:
            Dictionary mapping storage keys to deletion success
        """
        ...
    
    # Storage operations
    async def list_files(
        self,
        prefix: Optional[str] = None,
        limit: int = 1000,
        continuation_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List files in storage with optional prefix filtering.
        
        Args:
            prefix: Key prefix to filter by
            limit: Maximum number of files to return
            continuation_token: Token for pagination
        
        Returns:
            Dictionary with:
            - files: List of file information
            - next_token: Token for next page (if more results)
            - total_count: Total number of files (if available)
        """
        ...
    
    async def copy_file(
        self,
        source_key: StorageKey,
        destination_key: StorageKey,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Copy file to new location within storage.
        
        Args:
            source_key: Source file key
            destination_key: Destination file key
            metadata: New metadata for copied file
        
        Returns:
            True if copy was successful
        """
        ...
    
    async def move_file(
        self,
        source_key: StorageKey,
        destination_key: StorageKey
    ) -> bool:
        """Move file to new location within storage.
        
        Args:
            source_key: Source file key
            destination_key: Destination file key
        
        Returns:
            True if move was successful
        """
        ...
    
    # Storage statistics and monitoring
    async def get_storage_usage(self, prefix: Optional[str] = None) -> Dict[str, Any]:
        """Get storage usage statistics.
        
        Args:
            prefix: Key prefix to analyze (None for all storage)
        
        Returns:
            Dictionary with:
            - total_files: Number of files
            - total_size_bytes: Total storage used
            - average_file_size: Average file size
            - largest_file_size: Size of largest file
        """
        ...
    
    async def get_provider_info(self) -> Dict[str, Any]:
        """Get storage provider information.
        
        Returns:
            Dictionary with provider-specific info like:
            - provider_type: Type of storage (local, s3, etc.)
            - version: Provider version
            - region: Storage region (if applicable)
            - bucket/container: Storage bucket/container name
        """
        ...
    
    async def ping(self) -> bool:
        """Health check - verify storage is responsive.
        
        Returns:
            True if storage is healthy and responsive
        """
        ...