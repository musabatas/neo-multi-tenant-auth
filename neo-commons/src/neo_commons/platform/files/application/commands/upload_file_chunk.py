"""Upload file chunk command.

ONLY chunk upload - handles individual chunk upload for large files
with resumable upload session management.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ...core.protocols.file_repository import FileRepository
from ...core.protocols.storage_provider import StorageProviderProtocol  
from ...core.entities.upload_session import UploadSession
from ...core.value_objects.upload_session_id import UploadSessionId
from ...core.value_objects.file_size import FileSize
from ...core.value_objects.checksum import Checksum
from ...core.exceptions.upload_failed import UploadFailed


@dataclass
class UploadFileChunkData:
    """Data required to upload a file chunk."""
    
    # Upload session
    upload_session_id: str
    
    # Chunk data
    chunk_number: int  # 1-based chunk number
    chunk_content: bytes
    chunk_checksum: str  # SHA256 of chunk content
    
    # Upload context
    user_id: str
    tenant_id: str
    
    # Optional context
    request_id: Optional[str] = None
    client_ip: Optional[str] = None


@dataclass 
class UploadFileChunkResult:
    """Result of file chunk upload operation."""
    
    success: bool
    upload_session_id: str
    chunk_number: int
    bytes_uploaded: int = 0
    total_chunks: int = 0
    upload_progress: float = 0.0  # 0.0 to 1.0
    chunk_upload_duration_ms: int = 0
    
    # Session status
    session_complete: bool = False
    all_chunks_uploaded: bool = False
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class UploadFileChunkCommand:
    """Command to upload a single file chunk.
    
    Handles chunked file upload including:
    - Upload session validation and management
    - Chunk integrity verification with checksums
    - Sequential and parallel chunk handling
    - Progress tracking and status updates
    - Storage provider chunk coordination
    - Error handling with retry capability
    - Performance monitoring per chunk
    """
    
    def __init__(
        self,
        file_repository: FileRepository,
        storage_provider: StorageProviderProtocol
    ):
        """Initialize upload file chunk command.
        
        Args:
            file_repository: Repository for upload session management
            storage_provider: Storage backend for chunk upload
        """
        self._file_repository = file_repository
        self._storage_provider = storage_provider
    
    async def execute(self, data: UploadFileChunkData) -> UploadFileChunkResult:
        """Execute file chunk upload operation.
        
        Args:
            data: File chunk upload data
            
        Returns:
            Result of the chunk upload operation
            
        Raises:
            UploadFailed: If chunk upload fails
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate upload session
            session_id = UploadSessionId.from_string(data.upload_session_id)
            upload_session = await self._file_repository.get_upload_session(session_id)
            
            if not upload_session:
                return UploadFileChunkResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    chunk_number=data.chunk_number,
                    error_code="SessionNotFound",
                    error_message=f"Upload session {data.upload_session_id} not found"
                )
            
            # Validate session is active and not expired
            if upload_session.status != "active":
                return UploadFileChunkResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    chunk_number=data.chunk_number,
                    error_code="SessionInactive",
                    error_message=f"Upload session is {upload_session.status}"
                )
            
            if upload_session.expires_at and datetime.utcnow() > upload_session.expires_at:
                return UploadFileChunkResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    chunk_number=data.chunk_number,
                    error_code="SessionExpired",
                    error_message="Upload session has expired"
                )
            
            # Validate chunk data
            if data.chunk_number < 1 or data.chunk_number > upload_session.total_chunks:
                return UploadFileChunkResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    chunk_number=data.chunk_number,
                    error_code="InvalidChunkNumber",
                    error_message=f"Chunk number {data.chunk_number} is out of range (1-{upload_session.total_chunks})"
                )
            
            # Verify chunk checksum
            calculated_checksum = self._calculate_chunk_checksum(data.chunk_content)
            if calculated_checksum != data.chunk_checksum:
                return UploadFileChunkResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    chunk_number=data.chunk_number,
                    error_code="ChecksumMismatch",
                    error_message=f"Chunk checksum mismatch: expected {data.chunk_checksum}, got {calculated_checksum}"
                )
            
            # Check if chunk already uploaded (idempotency)
            if data.chunk_number in upload_session.uploaded_chunks:
                # Chunk already uploaded, return success
                end_time = datetime.utcnow()
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                
                return UploadFileChunkResult(
                    success=True,
                    upload_session_id=data.upload_session_id,
                    chunk_number=data.chunk_number,
                    bytes_uploaded=len(data.chunk_content),
                    total_chunks=upload_session.total_chunks,
                    upload_progress=len(upload_session.uploaded_chunks) / upload_session.total_chunks,
                    chunk_upload_duration_ms=duration_ms,
                    all_chunks_uploaded=len(upload_session.uploaded_chunks) == upload_session.total_chunks
                )
            
            # Generate chunk storage key
            chunk_storage_key = self._generate_chunk_storage_key(
                upload_session.storage_key.value,
                data.chunk_number
            )
            
            # Upload chunk to storage provider
            from io import BytesIO
            chunk_stream = BytesIO(data.chunk_content)
            
            storage_success = await self._storage_provider.upload_chunk(
                upload_id=upload_session.upload_id or upload_session.id.value,
                chunk_number=data.chunk_number,
                content=chunk_stream,
                storage_key=chunk_storage_key
            )
            
            if not storage_success:
                return UploadFileChunkResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    chunk_number=data.chunk_number,
                    error_code="StorageUploadFailed",
                    error_message=f"Failed to upload chunk {data.chunk_number} to storage"
                )
            
            # Update upload session with chunk progress
            updated_session = upload_session.with_chunk_uploaded(
                chunk_number=data.chunk_number,
                bytes_uploaded=len(data.chunk_content),
                chunk_checksum=data.chunk_checksum
            )
            
            # Save updated session
            await self._file_repository.update_upload_session(updated_session)
            
            # Calculate results
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            all_chunks_uploaded = len(updated_session.uploaded_chunks) == updated_session.total_chunks
            progress = len(updated_session.uploaded_chunks) / updated_session.total_chunks
            
            return UploadFileChunkResult(
                success=True,
                upload_session_id=data.upload_session_id,
                chunk_number=data.chunk_number,
                bytes_uploaded=len(data.chunk_content),
                total_chunks=updated_session.total_chunks,
                upload_progress=progress,
                chunk_upload_duration_ms=duration_ms,
                all_chunks_uploaded=all_chunks_uploaded
            )
                
        except Exception as e:
            # Calculate duration for error case
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return UploadFileChunkResult(
                success=False,
                upload_session_id=data.upload_session_id,
                chunk_number=data.chunk_number,
                chunk_upload_duration_ms=duration_ms,
                error_code="UploadFailed",
                error_message=f"Unexpected error during chunk upload: {str(e)}"
            )
    
    def _calculate_chunk_checksum(self, content: bytes) -> str:
        """Calculate SHA256 checksum of chunk content."""
        import hashlib
        return hashlib.sha256(content).hexdigest()
    
    def _generate_chunk_storage_key(self, base_storage_key: str, chunk_number: int) -> str:
        """Generate storage key for individual chunk."""
        return f"{base_storage_key}.chunk.{chunk_number:06d}"


# Factory function for dependency injection
def create_upload_file_chunk_command(
    file_repository: FileRepository,
    storage_provider: StorageProviderProtocol
) -> UploadFileChunkCommand:
    """Create upload file chunk command."""
    return UploadFileChunkCommand(
        file_repository=file_repository,
        storage_provider=storage_provider
    )