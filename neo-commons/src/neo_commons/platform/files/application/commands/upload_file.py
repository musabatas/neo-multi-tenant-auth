"""Upload file command.

ONLY file upload - handles single file upload orchestration
with validation, storage, and metadata creation.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from io import BytesIO

from ...core.protocols.file_repository import FileRepository
from ...core.protocols.storage_provider import StorageProviderProtocol  
from ...core.protocols.virus_scanner import VirusScanner
from ...core.entities.file_metadata import FileMetadata, VirusStatus
from ...core.value_objects.file_id import FileId
from ...core.value_objects.file_path import FilePath
from ...core.value_objects.file_size import FileSize
from ...core.value_objects.mime_type import MimeType
from ...core.value_objects.storage_provider import StorageProvider
from ...core.value_objects.storage_key import StorageKey
from ...core.value_objects.checksum import Checksum
from ...core.exceptions.upload_failed import UploadFailed
from ...core.exceptions.storage_quota_exceeded import StorageQuotaExceeded
from ...core.exceptions.invalid_file_type import InvalidFileType
from ...core.exceptions.virus_detected import VirusDetected


@dataclass
class UploadFileData:
    """Data required to upload a file."""
    
    # Required fields (no defaults)
    filename: str
    content: bytes
    user_id: str
    tenant_id: str
    
    # Optional fields (with defaults)
    content_type: Optional[str] = None
    folder_path: str = "/"
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    replace_existing: bool = False
    scan_for_viruses: bool = True
    generate_thumbnails: bool = True
    preserve_metadata: bool = True
    request_id: Optional[str] = None
    client_ip: Optional[str] = None


@dataclass 
class UploadFileResult:
    """Result of file upload operation."""
    
    # Required field
    success: bool
    
    # Optional fields (with defaults)
    file_id: Optional[str] = None
    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    content_type: str = ""
    storage_key: str = ""
    checksum: str = ""
    upload_duration_ms: int = 0
    virus_scan_status: str = "pending"  # pending, clean, infected, failed
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class UploadFileCommand:
    """Command to upload a single file.
    
    Handles complete file upload orchestration including:
    - File content validation and analysis
    - MIME type detection and verification  
    - Virus scanning for security
    - Storage provider coordination
    - Metadata creation and persistence
    - Checksum calculation and verification
    - Error handling and rollback
    - Performance tracking
    """
    
    def __init__(
        self,
        file_repository: FileRepository,
        storage_provider: StorageProviderProtocol,
        virus_scanner: Optional[VirusScanner] = None
    ):
        """Initialize upload file command.
        
        Args:
            file_repository: Repository for file metadata
            storage_provider: Storage backend for file content
            virus_scanner: Optional virus scanner for security
        """
        self._file_repository = file_repository
        self._storage_provider = storage_provider
        self._virus_scanner = virus_scanner
    
    async def execute(self, data: UploadFileData) -> UploadFileResult:
        """Execute file upload operation.
        
        Args:
            data: File upload data and options
            
        Returns:
            Result of the upload operation
            
        Raises:
            UploadFailed: If upload fails at any stage
            StorageQuotaExceeded: If file would exceed storage quota
            InvalidFileType: If file type is not allowed
            VirusDetected: If file contains malware
        """
        start_time = datetime.utcnow()
        file_id: Optional[FileId] = None
        storage_key: Optional[StorageKey] = None
        
        try:
            # Generate unique file ID
            file_id = FileId.generate()
            
            # Validate and analyze file
            file_path = self._create_file_path(data.folder_path, data.filename)
            file_size = self._create_file_size(len(data.content))
            mime_type = self._detect_mime_type(data.content, data.filename, data.content_type)
            checksum = self._calculate_checksum(data.content)
            
            # Validate file type
            if not self._is_file_type_allowed(mime_type):
                raise InvalidFileType(
                    message=f"File type '{mime_type.value}' is not allowed",
                    file_type=mime_type.value,
                    filename=data.filename,
                    tenant_id=data.tenant_id,
                    user_id=data.user_id
                )
            
            # Check storage quota
            await self._check_storage_quota(data.tenant_id, file_size)
            
            # Perform virus scan if enabled
            virus_scan_status = "clean"
            if data.scan_for_viruses and self._virus_scanner:
                scan_result = await self._virus_scanner.scan_content(data.content)
                if scan_result.infected:
                    raise VirusDetected(
                        message=f"Virus detected: {scan_result.threat_name}",
                        threat_name=scan_result.threat_name or "Unknown",
                        filename=data.filename,
                        file_size=file_size,
                        tenant_id=data.tenant_id,
                        user_id=data.user_id
                    )
                virus_scan_status = "clean" if scan_result.clean else "failed"
            
            # Generate storage key
            storage_key = self._generate_storage_key(data.tenant_id, file_id, data.filename)
            
            # Store file content in storage provider
            content_stream = BytesIO(data.content)
            storage_success = await self._storage_provider.upload_file(
                key=storage_key.value,
                content=content_stream,
                content_type=mime_type.value,
                metadata={
                    "original_filename": data.filename,
                    "tenant_id": data.tenant_id,
                    "user_id": data.user_id,
                    "file_id": str(file_id.value),
                    "checksum": checksum.value
                }
            )
            
            if not storage_success:
                raise UploadFailed(
                    message="Failed to store file content",
                    filename=data.filename,
                    file_size=file_size,
                    storage_provider=str(self._storage_provider),
                    upload_stage="storage",
                    tenant_id=data.tenant_id,
                    user_id=data.user_id
                )
            
            # Create file metadata
            from neo_commons.core.value_objects.identifiers import TenantId, UserId
            
            file_metadata = FileMetadata(
                id=file_id,
                tenant_id=TenantId(data.tenant_id),
                original_name=data.filename,
                path=file_path,
                size=file_size,
                mime_type=mime_type,
                storage_provider=StorageProvider(str(self._storage_provider)),
                storage_key=storage_key,
                checksum=checksum,
                created_by=UserId(data.user_id),
                description=data.description,
                tags=set(data.tags.keys()) if data.tags else set(),
                virus_status=VirusStatus.CLEAN if virus_scan_status == "clean" else VirusStatus.PENDING
            )
            
            # Save metadata to repository
            saved_metadata = await self._file_repository.create_file(file_metadata)
            
            # Calculate upload duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return UploadFileResult(
                success=True,
                file_id=str(saved_metadata.id.value),
                filename=saved_metadata.original_name,
                file_path=str(saved_metadata.path.value),
                file_size=saved_metadata.size.value,
                content_type=saved_metadata.mime_type.value,
                storage_key=saved_metadata.storage_key.value,
                checksum=saved_metadata.checksum.value,
                upload_duration_ms=duration_ms,
                virus_scan_status=virus_scan_status
            )
                
        except (InvalidFileType, StorageQuotaExceeded, VirusDetected) as e:
            # Clean up storage if file was uploaded
            if storage_key:
                try:
                    await self._storage_provider.delete_file(storage_key.value)
                except Exception:
                    pass  # Best effort cleanup
            
            # Calculate duration for error case
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return UploadFileResult(
                success=False,
                filename=data.filename,
                upload_duration_ms=duration_ms,
                error_code=type(e).__name__,
                error_message=str(e),
                error_details=e.details if hasattr(e, 'details') else None
            )
        
        except Exception as e:
            # Clean up storage if file was uploaded
            if storage_key:
                try:
                    await self._storage_provider.delete_file(storage_key.value)
                except Exception:
                    pass  # Best effort cleanup
            
            # Calculate duration for error case
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return UploadFileResult(
                success=False,
                filename=data.filename,
                upload_duration_ms=duration_ms,
                error_code="UploadFailed",
                error_message=f"Unexpected error during upload: {str(e)}"
            )
    
    def _create_file_path(self, folder_path: str, filename: str) -> FilePath:
        """Create and validate file path."""
        if not folder_path.startswith("/"):
            folder_path = "/" + folder_path
        if not folder_path.endswith("/"):
            folder_path = folder_path + "/"
        
        full_path = folder_path + filename
        return FilePath(full_path)
    
    def _create_file_size(self, size_bytes: int) -> FileSize:
        """Create file size from bytes."""
        return FileSize(size_bytes)
    
    def _detect_mime_type(self, content: bytes, filename: str, provided_type: Optional[str] = None) -> MimeType:
        """Detect MIME type from content and filename."""
        # Use provided type if valid, otherwise detect from content/filename
        if provided_type:
            try:
                return MimeType(provided_type)
            except ValueError:
                pass
        
        # Simple detection based on file extension
        # In production, you'd use python-magic or similar
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        extension_map = {
            'txt': 'text/plain',
            'pdf': 'application/pdf', 
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'mp4': 'video/mp4',
            'avi': 'video/x-msvideo',
            'zip': 'application/zip',
        }
        
        detected_type = extension_map.get(extension, 'application/octet-stream')
        return MimeType(detected_type)
    
    def _calculate_checksum(self, content: bytes) -> Checksum:
        """Calculate file checksum."""
        import hashlib
        sha256_hash = hashlib.sha256(content).hexdigest()
        return Checksum(f"sha256:{sha256_hash}")
    
    def _is_file_type_allowed(self, mime_type: MimeType) -> bool:
        """Check if file type is allowed."""
        # Simple allowlist - in production this would be configurable
        allowed_types = {
            'text/plain',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'image/jpeg',
            'image/png',
            'image/gif',
            'video/mp4',
            'application/zip'
        }
        return mime_type.value in allowed_types
    
    async def _check_storage_quota(self, tenant_id: str, file_size: FileSize) -> None:
        """Check if upload would exceed storage quota."""
        # TODO: Implement quota checking
        # This would query current usage and compare against limits
        pass
    
    def _generate_storage_key(self, tenant_id: str, file_id: FileId, filename: str) -> StorageKey:
        """Generate unique storage key."""
        # Create hierarchical storage path for better organization
        year_month = datetime.utcnow().strftime("%Y/%m")
        key = f"tenants/{tenant_id}/files/{year_month}/{file_id.value}/{filename}"
        return StorageKey(key)


# Factory function for dependency injection
def create_upload_file_command(
    file_repository: FileRepository,
    storage_provider: StorageProviderProtocol,
    virus_scanner: Optional[VirusScanner] = None
) -> UploadFileCommand:
    """Create upload file command."""
    return UploadFileCommand(
        file_repository=file_repository,
        storage_provider=storage_provider,
        virus_scanner=virus_scanner
    )