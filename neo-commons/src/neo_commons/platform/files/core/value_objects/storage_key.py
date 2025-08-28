"""Storage key value object.

ONLY storage key - represents storage-provider-specific file key with
validation, path manipulation, and security checks.

Following maximum separation architecture - one file = one purpose.
"""

import re
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import quote, unquote

@dataclass(frozen=True)
class StorageKey:
    """Storage key value object.
    
    Represents a storage-provider-specific key for identifying files.
    Handles path normalization, security validation, and provider-specific
    format requirements for both local filesystem and cloud storage.
    
    Features:
    - Provider-agnostic key format
    - Security validation (prevents directory traversal)
    - Path normalization and encoding
    - Hierarchical path support
    - Extension and name extraction
    """
    
    value: str
    
    # Key validation constants
    MAX_KEY_LENGTH = 1024
    MAX_SEGMENT_LENGTH = 255
    FORBIDDEN_CHARS = {'<', '>', ':', '"', '|', '?', '*', '\0', '\r', '\n'}
    
    # Reserved segments (case-insensitive)
    RESERVED_SEGMENTS = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # Key pattern for validation (allows letters, numbers, hyphens, underscores, dots, slashes)
    KEY_PATTERN = re.compile(r'^[a-zA-Z0-9\-_./]+$')
    
    def __post_init__(self):
        """Validate and normalize storage key."""
        if not isinstance(self.value, str):
            raise ValueError(f"StorageKey must be a string, got {type(self.value).__name__}")
        
        if not self.value or not self.value.strip():
            raise ValueError("Storage key cannot be empty")
        
        # Normalize key
        normalized = self._normalize_key(self.value.strip())
        
        # Security validations
        self._validate_security(normalized)
        self._validate_length(normalized)
        self._validate_characters(normalized)
        self._validate_segments(normalized)
        
        # Store normalized value
        object.__setattr__(self, 'value', normalized)
    
    def _normalize_key(self, key: str) -> str:
        """Normalize storage key format."""
        # Convert backslashes to forward slashes
        normalized = key.replace('\\', '/')
        
        # Remove duplicate slashes
        while '//' in normalized:
            normalized = normalized.replace('//', '/')
        
        # Remove leading slash (storage keys should be relative)
        normalized = normalized.lstrip('/')
        
        # Remove trailing slash unless it's a directory marker
        if normalized.endswith('/') and len(normalized) > 1:
            # Keep trailing slash only for explicit directory keys
            pass
        
        return normalized
    
    def _validate_security(self, key: str) -> None:
        """Check for security issues like path traversal."""
        # Check for path traversal attempts
        if '..' in key:
            segments = key.split('/')
            if '..' in segments:
                raise ValueError("Storage key contains path traversal sequence: '..'")
        
        # Check for absolute path indicators
        if key.startswith('/'):
            raise ValueError("Storage key cannot be absolute (start with '/')")
        
        # Check for drive letter (Windows)
        if len(key) > 1 and key[1] == ':':
            raise ValueError("Storage key cannot contain drive letter")
    
    def _validate_length(self, key: str) -> None:
        """Validate key and segment lengths."""
        if len(key) > self.MAX_KEY_LENGTH:
            raise ValueError(f"Storage key too long: {len(key)} > {self.MAX_KEY_LENGTH}")
        
        # Check individual segment lengths
        segments = key.split('/')
        for segment in segments:
            if segment and len(segment) > self.MAX_SEGMENT_LENGTH:
                raise ValueError(f"Key segment too long: '{segment}' ({len(segment)} > {self.MAX_SEGMENT_LENGTH})")
    
    def _validate_characters(self, key: str) -> None:
        """Validate allowed characters in key."""
        # Check for forbidden characters
        forbidden_found = self.FORBIDDEN_CHARS.intersection(set(key))
        if forbidden_found:
            raise ValueError(f"Storage key contains forbidden characters: {', '.join(sorted(forbidden_found))}")
        
        # Check for control characters
        for char in key:
            if ord(char) < 32 and char not in {'\t'}:  # Allow tab but not other control chars
                raise ValueError(f"Storage key contains control character: {repr(char)}")
        
        # Basic pattern validation
        if not self.KEY_PATTERN.match(key):
            raise ValueError(f"Storage key contains invalid characters: {key}")
    
    def _validate_segments(self, key: str) -> None:
        """Validate individual key segments."""
        segments = key.split('/')
        
        for segment in segments:
            if not segment:  # Empty segment (double slash)
                continue
            
            # Check reserved names (Windows compatibility)
            name_without_ext = segment.split('.')[0].upper()
            if name_without_ext in self.RESERVED_SEGMENTS:
                raise ValueError(f"Storage key contains reserved segment: {segment}")
            
            # Check for segments ending with spaces or dots (Windows issues)
            if segment.endswith(' ') or segment.endswith('.'):
                raise ValueError(f"Key segment cannot end with space or dot: '{segment}'")
    
    @classmethod
    def from_file_path(cls, file_path: str, prefix: Optional[str] = None) -> 'StorageKey':
        """Create storage key from file path with optional prefix."""
        if prefix:
            # Ensure prefix doesn't end with slash
            prefix = prefix.rstrip('/')
            key = f"{prefix}/{file_path}"
        else:
            key = file_path
        
        return cls(key)
    
    @classmethod
    def from_components(cls, *components: str) -> 'StorageKey':
        """Create storage key from path components."""
        if not components:
            raise ValueError("At least one component required")
        
        # Filter out empty components and join
        valid_components = [str(comp).strip() for comp in components if str(comp).strip()]
        if not valid_components:
            raise ValueError("No valid components provided")
        
        key = '/'.join(valid_components)
        return cls(key)
    
    def get_name(self) -> str:
        """Get the file name (last segment) from the key."""
        if not self.value or self.value.endswith('/'):
            return ""
        return self.value.split('/')[-1]
    
    def get_directory(self) -> Optional['StorageKey']:
        """Get the directory part of the key."""
        if '/' not in self.value:
            return None
        
        directory = '/'.join(self.value.split('/')[:-1])
        if not directory:
            return None
        
        return StorageKey(directory)
    
    def get_parent(self) -> Optional['StorageKey']:
        """Get parent directory key."""
        return self.get_directory()
    
    def get_extension(self) -> str:
        """Get file extension including the dot (e.g., '.txt')."""
        name = self.get_name()
        if '.' not in name:
            return ""
        
        return '.' + name.split('.')[-1].lower()
    
    def get_name_without_extension(self) -> str:
        """Get filename without extension."""
        name = self.get_name()
        if '.' not in name:
            return name
        
        return '.'.join(name.split('.')[:-1])
    
    def get_segments(self) -> List[str]:
        """Get all key segments as a list."""
        if not self.value:
            return []
        return [seg for seg in self.value.split('/') if seg]
    
    def get_depth(self) -> int:
        """Get key depth (number of directory levels)."""
        return len(self.get_segments())
    
    def is_directory(self) -> bool:
        """Check if key represents a directory."""
        return self.value.endswith('/')
    
    def is_file(self) -> bool:
        """Check if key represents a file."""
        return not self.is_directory()
    
    def is_in_directory(self, directory_key: 'StorageKey') -> bool:
        """Check if this key is within the specified directory."""
        if not isinstance(directory_key, StorageKey):
            return False
        
        directory_path = directory_key.value.rstrip('/') + '/'
        return self.value.startswith(directory_path)
    
    def join(self, *segments: str) -> 'StorageKey':
        """Join this key with additional segments."""
        all_segments = [self.value] + list(segments)
        return StorageKey.from_components(*all_segments)
    
    def with_extension(self, extension: str) -> 'StorageKey':
        """Create new key with different extension."""
        if not extension.startswith('.'):
            extension = '.' + extension
        
        name_without_ext = self.get_name_without_extension()
        directory = self.get_directory()
        
        new_name = name_without_ext + extension
        
        if directory:
            return directory.join(new_name)
        else:
            return StorageKey(new_name)
    
    def with_prefix(self, prefix: str) -> 'StorageKey':
        """Create new key with prefix."""
        return StorageKey.from_file_path(self.value, prefix)
    
    def without_extension(self) -> 'StorageKey':
        """Create new key without file extension."""
        name_without_ext = self.get_name_without_extension()
        directory = self.get_directory()
        
        if directory:
            return directory.join(name_without_ext)
        else:
            return StorageKey(name_without_ext)
    
    def url_encode(self) -> str:
        """Get URL-encoded version of the key."""
        # Encode each segment separately to preserve slashes
        segments = self.value.split('/')
        encoded_segments = [quote(segment, safe='') for segment in segments]
        return '/'.join(encoded_segments)
    
    @classmethod
    def from_url_encoded(cls, encoded_key: str) -> 'StorageKey':
        """Create storage key from URL-encoded string."""
        # Decode each segment separately
        segments = encoded_key.split('/')
        decoded_segments = [unquote(segment) for segment in segments]
        decoded_key = '/'.join(decoded_segments)
        return cls(decoded_key)
    
    def __str__(self) -> str:
        """String representation for display."""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"StorageKey('{self.value}')"