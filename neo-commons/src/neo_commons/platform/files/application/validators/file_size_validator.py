"""File size validator.

ONLY file size validation - handles size limits,
quota checks, and content length verification.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Optional

from ...core.value_objects.file_size import FileSize
from ...core.exceptions.storage_quota_exceeded import StorageQuotaExceeded


@dataclass
class FileSizeValidatorConfig:
    """Configuration for file size validator."""
    
    max_file_size_bytes: int = 500 * 1024 * 1024  # 500MB default
    min_file_size_bytes: int = 1  # 1 byte minimum
    check_content_length: bool = True
    allow_empty_files: bool = False


class FileSizeValidator:
    """File size validation service."""
    
    def __init__(self, config: Optional[FileSizeValidatorConfig] = None):
        self._config = config or FileSizeValidatorConfig()
    
    def validate_file_size(self, content: bytes, declared_size: Optional[int] = None) -> bool:
        """Validate file size constraints."""
        actual_size = len(content)
        
        # Check minimum size
        if not self._config.allow_empty_files and actual_size < self._config.min_file_size_bytes:
            return False
        
        # Check maximum size
        if actual_size > self._config.max_file_size_bytes:
            return False
        
        # Check declared vs actual size consistency
        if self._config.check_content_length and declared_size is not None:
            if actual_size != declared_size:
                return False
        
        return True


def create_file_size_validator(config: Optional[FileSizeValidatorConfig] = None) -> FileSizeValidator:
    """Create file size validator."""
    return FileSizeValidator(config)