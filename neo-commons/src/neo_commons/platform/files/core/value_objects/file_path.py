"""File path value object.

ONLY file path - represents validated file path with security checks,
normalization, and path manipulation utilities.

Following maximum separation architecture - one file = one purpose.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass(frozen=True)
class FilePath:
    """File path value object.
    
    Represents a validated file path with security checks to prevent
    path traversal attacks. Provides utilities for path manipulation,
    normalization, and validation.
    
    Security features:
    - Prevents path traversal (../ sequences)
    - Normalizes path separators
    - Validates path length and characters
    - Ensures relative paths only
    """
    
    value: str
    
    # Path validation constants
    MAX_PATH_LENGTH = 4096
    MAX_FILENAME_LENGTH = 255
    FORBIDDEN_CHARS = {'<', '>', ':', '"', '|', '?', '*', '\0'}
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    def __post_init__(self):
        """Validate and normalize file path."""
        if not isinstance(self.value, str):
            raise ValueError(f"FilePath must be a string, got {type(self.value).__name__}")
        
        if not self.value or not self.value.strip():
            raise ValueError("File path cannot be empty")
        
        # Normalize path
        normalized = self._normalize_path(self.value.strip())
        
        # Security validations
        self._validate_security(normalized)
        self._validate_length(normalized)
        self._validate_characters(normalized)
        self._validate_components(normalized)
        
        # Store normalized value
        object.__setattr__(self, 'value', normalized)
    
    def _normalize_path(self, path: str) -> str:
        """Normalize path separators and remove redundant components."""
        # Convert backslashes to forward slashes
        normalized = path.replace('\\', '/')
        
        # Remove duplicate slashes
        while '//' in normalized:
            normalized = normalized.replace('//', '/')
        
        # Remove leading/trailing slashes for relative paths
        normalized = normalized.strip('/')
        
        return normalized
    
    def _validate_security(self, path: str) -> None:
        """Check for path traversal attempts."""
        if '..' in path:
            # Check if .. is actually a path component
            components = path.split('/')
            if '..' in components:
                raise ValueError("Path traversal not allowed: contains '..' component")
        
        # Ensure path is relative (no absolute path indicators)
        if path.startswith('/') or (len(path) > 1 and path[1] == ':'):
            raise ValueError("Absolute paths not allowed")
    
    def _validate_length(self, path: str) -> None:
        """Validate path and component lengths."""
        if len(path) > self.MAX_PATH_LENGTH:
            raise ValueError(f"Path too long: {len(path)} > {self.MAX_PATH_LENGTH}")
        
        # Check individual component lengths
        components = path.split('/')
        for component in components:
            if len(component) > self.MAX_FILENAME_LENGTH:
                raise ValueError(f"Path component too long: '{component}' ({len(component)} > {self.MAX_FILENAME_LENGTH})")
    
    def _validate_characters(self, path: str) -> None:
        """Validate allowed characters in path."""
        forbidden_found = self.FORBIDDEN_CHARS.intersection(set(path))
        if forbidden_found:
            raise ValueError(f"Path contains forbidden characters: {', '.join(sorted(forbidden_found))}")
        
        # Check for control characters
        for char in path:
            if ord(char) < 32 and char not in {'\t'}:  # Allow tab but not other control chars
                raise ValueError(f"Path contains control character: {repr(char)}")
    
    def _validate_components(self, path: str) -> None:
        """Validate individual path components."""
        components = path.split('/')
        
        for component in components:
            if not component:  # Empty component (double slash)
                continue
                
            # Check reserved names (Windows)
            name_without_ext = component.split('.')[0].upper()
            if name_without_ext in self.RESERVED_NAMES:
                raise ValueError(f"Reserved filename not allowed: {component}")
            
            # Check for names ending with spaces or dots (Windows issues)
            if component.endswith(' ') or component.endswith('.'):
                raise ValueError(f"Filename cannot end with space or dot: '{component}'")
    
    def get_filename(self) -> str:
        """Get the filename (last component) from the path."""
        if not self.value:
            return ""
        return self.value.split('/')[-1]
    
    def get_directory(self) -> Optional['FilePath']:
        """Get the directory path (all components except filename)."""
        if '/' not in self.value:
            return None
        
        directory = '/'.join(self.value.split('/')[:-1])
        if not directory:
            return None
            
        return FilePath(directory)
    
    def get_extension(self) -> str:
        """Get file extension including the dot (e.g., '.txt')."""
        filename = self.get_filename()
        if '.' not in filename:
            return ""
        
        return '.' + filename.split('.')[-1].lower()
    
    def get_name_without_extension(self) -> str:
        """Get filename without extension."""
        filename = self.get_filename()
        if '.' not in filename:
            return filename
        
        return '.'.join(filename.split('.')[:-1])
    
    def get_components(self) -> List[str]:
        """Get all path components as a list."""
        if not self.value:
            return []
        return self.value.split('/')
    
    def join(self, *paths: str) -> 'FilePath':
        """Join this path with additional path components."""
        combined = self.value
        
        for path in paths:
            if combined and not combined.endswith('/'):
                combined += '/'
            combined += str(path).strip('/')
        
        return FilePath(combined)
    
    def with_extension(self, extension: str) -> 'FilePath':
        """Create new path with different extension."""
        if not extension.startswith('.'):
            extension = '.' + extension
        
        name_without_ext = self.get_name_without_extension()
        directory = self.get_directory()
        
        new_filename = name_without_ext + extension
        
        if directory:
            return directory.join(new_filename)
        else:
            return FilePath(new_filename)
    
    def is_hidden(self) -> bool:
        """Check if filename starts with dot (hidden file)."""
        filename = self.get_filename()
        return filename.startswith('.') and len(filename) > 1
    
    def depth(self) -> int:
        """Get path depth (number of directory levels)."""
        if not self.value:
            return 0
        return len(self.get_components())
    
    @classmethod
    def from_components(cls, *components: str) -> 'FilePath':
        """Create FilePath from individual components."""
        if not components:
            raise ValueError("At least one path component required")
        
        # Filter out empty components and join
        valid_components = [str(comp).strip('/') for comp in components if str(comp).strip('/')]
        if not valid_components:
            raise ValueError("No valid path components provided")
        
        return cls('/'.join(valid_components))
    
    def __str__(self) -> str:
        """String representation for display."""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"FilePath('{self.value}')"