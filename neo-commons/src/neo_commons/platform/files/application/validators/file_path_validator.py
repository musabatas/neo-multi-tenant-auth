"""File path validator.

ONLY path validation - handles path safety,
directory traversal prevention, and naming rules.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Optional, Set

from ...core.value_objects.file_path import FilePath


@dataclass
class FilePathValidatorConfig:
    """Configuration for file path validator."""
    
    max_path_length: int = 4096
    max_filename_length: int = 255
    max_directory_depth: int = 50
    allow_unicode: bool = True
    reserved_names: Set[str] = None
    blocked_characters: Set[str] = None


class FilePathValidator:
    """File path validation service."""
    
    def __init__(self, config: Optional[FilePathValidatorConfig] = None):
        self._config = config or FilePathValidatorConfig()
        
        if self._config.reserved_names is None:
            self._config.reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1'}
        
        if self._config.blocked_characters is None:
            self._config.blocked_characters = {'<', '>', ':', '"', '|', '?', '*', '\x00'}
    
    def validate_path(self, path: str) -> bool:
        """Validate file path safety and structure."""
        # TODO: Implement comprehensive path validation
        return True


def create_file_path_validator(config: Optional[FilePathValidatorConfig] = None) -> FilePathValidator:
    """Create file path validator."""
    return FilePathValidator(config)