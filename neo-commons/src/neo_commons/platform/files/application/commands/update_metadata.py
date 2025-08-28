"""Update metadata command.

ONLY metadata updates - handles file metadata modification
without affecting file content or storage location.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

from ...core.protocols.file_repository import FileRepository
from ...core.value_objects.file_id import FileId


@dataclass
class UpdateMetadataData:
    """Data required to update file metadata."""
    
    file_id: str
    user_id: str
    tenant_id: str
    
    # Optional updates (None means no change)
    description: Optional[str] = None
    tags: Optional[Dict[str, str]] = None
    filename: Optional[str] = None  # Rename without moving
    
    request_id: Optional[str] = None


@dataclass 
class UpdateMetadataResult:
    """Result of metadata update operation."""
    
    # Required fields
    success: bool
    file_id: str
    
    # Optional fields (with defaults)
    filename: str = ""
    updates_applied: int = 0
    update_duration_ms: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class UpdateMetadataCommand:
    """Command to update file metadata."""
    
    def __init__(self, file_repository: FileRepository):
        self._file_repository = file_repository
    
    async def execute(self, data: UpdateMetadataData) -> UpdateMetadataResult:
        """Execute metadata update operation."""
        start_time = datetime.utcnow()
        
        try:
            # TODO: Implement metadata update logic
            
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return UpdateMetadataResult(
                success=False,
                file_id=data.file_id,
                update_duration_ms=duration_ms,
                error_code="NotImplemented",
                error_message="Update metadata command not yet implemented"
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return UpdateMetadataResult(
                success=False,
                file_id=data.file_id,
                update_duration_ms=duration_ms,
                error_code="UpdateFailed",
                error_message=str(e)
            )


def create_update_metadata_command(file_repository: FileRepository) -> UpdateMetadataCommand:
    """Create update metadata command."""
    return UpdateMetadataCommand(file_repository)