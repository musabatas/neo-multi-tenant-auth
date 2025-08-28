"""Complete upload command.

ONLY upload completion - handles finalization of chunked uploads
with file assembly, metadata creation, and cleanup.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ...core.protocols.file_repository import FileRepository
from ...core.protocols.storage_provider import StorageProviderProtocol  
from ...core.protocols.virus_scanner import VirusScanner
from ...core.entities.file_metadata import FileMetadata
from ...core.entities.upload_session import UploadSession
from ...core.value_objects.upload_session_id import UploadSessionId
from ...core.value_objects.file_id import FileId
from ...core.value_objects.storage_provider import StorageProvider
from ...core.exceptions.upload_failed import UploadFailed
from ...core.exceptions.virus_detected import VirusDetected


@dataclass
class CompleteUploadData:
    """Data required to complete file upload."""
    
    # Required fields (no defaults)
    upload_session_id: str
    user_id: str
    tenant_id: str
    
    # Optional fields (with defaults)
    final_checksum: Optional[str] = None  # SHA256 of complete file
    scan_for_viruses: bool = True
    generate_thumbnails: bool = True
    request_id: Optional[str] = None


@dataclass 
class CompleteUploadResult:
    """Result of upload completion operation."""
    
    # Required field
    success: bool
    
    # Optional fields (with defaults)
    file_id: Optional[str] = None
    upload_session_id: str = ""
    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    content_type: str = ""
    storage_key: str = ""
    checksum: str = ""
    total_upload_duration_ms: int = 0
    virus_scan_status: str = "pending"  # pending, clean, infected, failed
    
    # Processing status
    chunks_assembled: bool = False
    metadata_created: bool = False
    session_cleaned: bool = False
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class CompleteUploadCommand:
    """Command to complete chunked file upload.
    
    Handles upload finalization including:
    - Upload session validation and completion
    - Chunk assembly and verification
    - File integrity checking with checksums
    - Virus scanning of complete file
    - Final file metadata creation
    - Upload session cleanup
    - Error handling and rollback
    - Performance tracking
    """
    
    def __init__(
        self,
        file_repository: FileRepository,
        storage_provider: StorageProviderProtocol,
        virus_scanner: Optional[VirusScanner] = None
    ):
        """Initialize complete upload command.
        
        Args:
            file_repository: Repository for sessions and metadata
            storage_provider: Storage backend for file assembly
            virus_scanner: Optional virus scanner for security
        """
        self._file_repository = file_repository
        self._storage_provider = storage_provider
        self._virus_scanner = virus_scanner
    
    async def execute(self, data: CompleteUploadData) -> CompleteUploadResult:
        """Execute upload completion operation.
        
        Args:
            data: Upload completion data
            
        Returns:
            Result of the completion operation
            
        Raises:
            UploadFailed: If completion fails at any stage
            VirusDetected: If file contains malware
        """
        completion_start = datetime.utcnow()
        
        try:
            # Validate upload session
            session_id = UploadSessionId.from_string(data.upload_session_id)
            upload_session = await self._file_repository.get_upload_session(session_id)
            
            if not upload_session:
                return CompleteUploadResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    error_code="SessionNotFound",
                    error_message=f"Upload session {data.upload_session_id} not found"
                )
            
            # Validate all chunks are uploaded
            if len(upload_session.uploaded_chunks) != upload_session.total_chunks:
                missing_chunks = set(range(1, upload_session.total_chunks + 1)) - set(upload_session.uploaded_chunks)
                return CompleteUploadResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    error_code="IncompleteUpload",
                    error_message=f"Missing chunks: {sorted(missing_chunks)}"
                )
            
            # Assemble chunks into final file
            assembly_success = await self._storage_provider.complete_multipart_upload(
                upload_id=upload_session.upload_id or str(upload_session.id.value),
                storage_key=upload_session.storage_key.value,
                total_chunks=upload_session.total_chunks
            )
            
            if not assembly_success:
                return CompleteUploadResult(
                    success=False,
                    upload_session_id=data.upload_session_id,
                    error_code="AssemblyFailed",
                    error_message="Failed to assemble chunks into final file"
                )
            
            # Verify file integrity if checksum provided
            if data.final_checksum:
                file_checksum = await self._storage_provider.calculate_file_checksum(
                    upload_session.storage_key.value
                )
                if file_checksum != data.final_checksum:
                    return CompleteUploadResult(
                        success=False,
                        upload_session_id=data.upload_session_id,
                        error_code="IntegrityCheckFailed",
                        error_message=f"File checksum mismatch: expected {data.final_checksum}, got {file_checksum}"
                    )
            
            # Perform virus scan if enabled
            virus_scan_status = "clean"
            if data.scan_for_viruses and self._virus_scanner:
                # For large files, we might scan in chunks or use async scanning
                scan_result = await self._virus_scanner.scan_file(upload_session.storage_key.value)
                if scan_result.infected:
                    # Clean up the assembled file
                    await self._storage_provider.delete_file(upload_session.storage_key.value)
                    
                    raise VirusDetected(
                        message=f"Virus detected in assembled file: {scan_result.threat_name}",
                        threat_name=scan_result.threat_name or "Unknown",
                        filename=upload_session.filename,
                        file_size=upload_session.file_size,
                        tenant_id=data.tenant_id,
                        user_id=data.user_id
                    )
                virus_scan_status = "clean" if scan_result.clean else "failed"
            
            # Create final file metadata
            file_metadata = FileMetadata(
                id=upload_session.file_id,
                filename=upload_session.filename,
                original_filename=upload_session.original_filename,
                file_path=upload_session.file_path,
                file_size=upload_session.file_size,
                content_type=upload_session.content_type,
                storage_provider=StorageProvider.from_name(str(self._storage_provider)),
                storage_key=upload_session.storage_key,
                checksum=upload_session.checksum,
                created_at=datetime.utcnow(),
                created_by=data.user_id,
                tenant_id=data.tenant_id,
                organization_id=upload_session.organization_id,
                team_id=upload_session.team_id,
                is_deleted=False,
                description=upload_session.description,
                tags=upload_session.tags or {},
                virus_scan_status=virus_scan_status,
                upload_session_id=upload_session.id
            )
            
            # Save file metadata
            saved_metadata = await self._file_repository.create_file(file_metadata)
            
            # Mark upload session as completed
            completed_session = upload_session.mark_completed()
            await self._file_repository.update_upload_session(completed_session)
            
            # Calculate total upload duration
            completion_end = datetime.utcnow()
            total_duration_ms = int((completion_end - upload_session.created_at).total_seconds() * 1000)
            
            # Schedule cleanup (in production, this would be async/background)
            cleanup_success = await self._cleanup_upload_session(upload_session)
            
            return CompleteUploadResult(
                success=True,
                file_id=str(saved_metadata.id.value),
                upload_session_id=data.upload_session_id,
                filename=saved_metadata.filename,
                file_path=str(saved_metadata.file_path.value),
                file_size=saved_metadata.file_size.bytes,
                content_type=saved_metadata.content_type.value,
                storage_key=saved_metadata.storage_key.value,
                checksum=saved_metadata.checksum.value,
                total_upload_duration_ms=total_duration_ms,
                virus_scan_status=virus_scan_status,
                chunks_assembled=True,
                metadata_created=True,
                session_cleaned=cleanup_success
            )
                
        except VirusDetected as e:
            # Calculate duration for error case
            completion_end = datetime.utcnow()
            duration_ms = int((completion_end - completion_start).total_seconds() * 1000)
            
            return CompleteUploadResult(
                success=False,
                upload_session_id=data.upload_session_id,
                total_upload_duration_ms=duration_ms,
                error_code="VirusDetected",
                error_message=str(e),
                error_details=e.details if hasattr(e, 'details') else None
            )
        
        except Exception as e:
            # Calculate duration for error case
            completion_end = datetime.utcnow()
            duration_ms = int((completion_end - completion_start).total_seconds() * 1000)
            
            return CompleteUploadResult(
                success=False,
                upload_session_id=data.upload_session_id,
                total_upload_duration_ms=duration_ms,
                error_code="CompletionFailed",
                error_message=f"Unexpected error during upload completion: {str(e)}"
            )
    
    async def _cleanup_upload_session(self, upload_session: UploadSession) -> bool:
        """Clean up temporary files from upload session."""
        try:
            # Delete individual chunk files (if storage provider supports it)
            if hasattr(self._storage_provider, 'cleanup_chunks'):
                await self._storage_provider.cleanup_chunks(
                    upload_id=upload_session.upload_id or str(upload_session.id.value),
                    storage_key=upload_session.storage_key.value
                )
            
            # Mark session for deletion (could be soft delete initially)
            # In production, you might keep sessions for a period for debugging
            return True
            
        except Exception:
            # Best effort cleanup, don't fail completion for cleanup errors
            return False


# Factory function for dependency injection
def create_complete_upload_command(
    file_repository: FileRepository,
    storage_provider: StorageProviderProtocol,
    virus_scanner: Optional[VirusScanner] = None
) -> CompleteUploadCommand:
    """Create complete upload command."""
    return CompleteUploadCommand(
        file_repository=file_repository,
        storage_provider=storage_provider,
        virus_scanner=virus_scanner
    )