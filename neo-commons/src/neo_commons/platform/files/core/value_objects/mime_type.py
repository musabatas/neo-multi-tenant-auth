"""MIME type value object.

ONLY MIME type - represents validated MIME type with categorization,
validation, and utility methods for file type handling.

Following maximum separation architecture - one file = one purpose.
"""

import re
from dataclasses import dataclass
from typing import Dict, Set, Optional, Tuple


# MIME type validation pattern (RFC 6838)
MIME_PATTERN = re.compile(
    r'^([a-zA-Z][a-zA-Z0-9][a-zA-Z0-9!#$&\\-\\^_]*)'  # type
    r'/'  # separator
    r'([a-zA-Z0-9][a-zA-Z0-9!#$&\\-\\^_.]*)'  # subtype
    r'(;.*)?$'  # optional parameters
)

# Common MIME types by category
IMAGE_TYPES = frozenset({
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
    'image/svg+xml', 'image/bmp', 'image/tiff', 'image/ico', 'image/heic'
})

VIDEO_TYPES = frozenset({
    'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo',
    'video/webm', 'video/ogg', 'video/x-flv', 'video/3gpp'
})

AUDIO_TYPES = frozenset({
    'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp3', 'audio/mp4',
    'audio/aac', 'audio/flac', 'audio/x-wav', 'audio/webm'
})

DOCUMENT_TYPES = frozenset({
    'application/pdf', 'application/msword', 'text/plain', 'text/html',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/rtf', 'text/csv', 'text/markdown'
})

ARCHIVE_TYPES = frozenset({
    'application/zip', 'application/x-rar-compressed', 'application/x-tar',
    'application/gzip', 'application/x-7z-compressed', 'application/x-bzip2'
})

TEXT_TYPES = frozenset({
    'text/plain', 'text/html', 'text/css', 'text/javascript', 'text/csv',
    'text/xml', 'text/markdown', 'text/rtf'
})

# Potentially dangerous MIME types (executables, scripts)
DANGEROUS_TYPES = frozenset({
    'application/x-msdownload', 'application/x-executable', 'application/x-dosexec',
    'application/x-winexe', 'application/x-msi', 'application/x-msdos-program',
    'text/javascript', 'application/javascript', 'application/x-javascript',
    'application/x-shellscript', 'text/x-script', 'application/x-bat',
    'application/x-perl', 'application/x-python-code'
})

# Common file extension mappings (immutable)
EXTENSION_MAP = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
    'gif': 'image/gif', 'webp': 'image/webp', 'svg': 'image/svg+xml',
    'pdf': 'application/pdf', 'doc': 'application/msword',
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'txt': 'text/plain', 'html': 'text/html', 'css': 'text/css',
    'js': 'text/javascript', 'json': 'application/json',
    'zip': 'application/zip', 'csv': 'text/csv',
    'mp4': 'video/mp4', 'mp3': 'audio/mpeg'
}


@dataclass(frozen=True)
class MimeType:
    """MIME type value object.
    
    Represents a validated MIME type with categorization utilities and
    security validation. Provides methods for type checking, categorization,
    and format validation according to RFC 6838.
    
    Features:
    - RFC 6838 compliant MIME type validation
    - Media type categorization (image, video, document, etc.)
    - Security classification (safe/dangerous types)
    - File extension mapping
    - Subtype analysis
    """
    
    value: str
    
    def __post_init__(self):
        """Validate MIME type format."""
        if not isinstance(self.value, str):
            raise ValueError(f"MimeType must be a string, got {type(self.value).__name__}")
        
        # Normalize to lowercase
        normalized = self.value.strip().lower()
        if not normalized:
            raise ValueError("MIME type cannot be empty")
        
        # Validate format
        if not MIME_PATTERN.match(normalized):
            raise ValueError(f"Invalid MIME type format: {self.value}")
        
        # Store normalized value
        object.__setattr__(self, 'value', normalized)
    
    def get_main_type(self) -> str:
        """Get the main type part (e.g., 'image' from 'image/jpeg')."""
        return self.value.split('/')[0]
    
    def get_sub_type(self) -> str:
        """Get the subtype part (e.g., 'jpeg' from 'image/jpeg')."""
        parts = self.value.split('/')
        subtype_with_params = parts[1]
        
        # Remove parameters if present
        if ';' in subtype_with_params:
            return subtype_with_params.split(';')[0]
        
        return subtype_with_params
    
    def get_parameters(self) -> Dict[str, str]:
        """Get MIME type parameters as a dictionary."""
        if ';' not in self.value:
            return {}
        
        params = {}
        param_string = self.value.split(';', 1)[1]
        
        for param in param_string.split(';'):
            param = param.strip()
            if '=' in param:
                key, value = param.split('=', 1)
                params[key.strip()] = value.strip().strip('"')
        
        return params
    
    def without_parameters(self) -> 'MimeType':
        """Get MIME type without parameters."""
        if ';' not in self.value:
            return self
        
        base_type = self.value.split(';')[0]
        return MimeType(base_type)
    
    def is_image(self) -> bool:
        """Check if this is an image MIME type."""
        return self.value in IMAGE_TYPES or self.get_main_type() == 'image'
    
    def is_video(self) -> bool:
        """Check if this is a video MIME type."""
        return self.value in VIDEO_TYPES or self.get_main_type() == 'video'
    
    def is_audio(self) -> bool:
        """Check if this is an audio MIME type."""
        return self.value in AUDIO_TYPES or self.get_main_type() == 'audio'
    
    def is_text(self) -> bool:
        """Check if this is a text MIME type."""
        return self.value in TEXT_TYPES or self.get_main_type() == 'text'
    
    def is_document(self) -> bool:
        """Check if this is a document MIME type."""
        return self.value in DOCUMENT_TYPES
    
    def is_archive(self) -> bool:
        """Check if this is an archive MIME type."""
        return self.value in ARCHIVE_TYPES
    
    def is_media(self) -> bool:
        """Check if this is any media type (image, video, audio)."""
        return self.is_image() or self.is_video() or self.is_audio()
    
    def is_dangerous(self) -> bool:
        """Check if this is a potentially dangerous MIME type."""
        return self.value in DANGEROUS_TYPES
    
    def is_safe(self) -> bool:
        """Check if this is considered a safe MIME type."""
        return not self.is_dangerous()
    
    def get_category(self) -> str:
        """Get the general category of this MIME type."""
        if self.is_image():
            return 'image'
        elif self.is_video():
            return 'video'
        elif self.is_audio():
            return 'audio'
        elif self.is_document():
            return 'document'
        elif self.is_archive():
            return 'archive'
        elif self.is_text():
            return 'text'
        else:
            return self.get_main_type()
    
    def get_common_extensions(self) -> Set[str]:
        """Get common file extensions for this MIME type."""
        extensions = set()
        
        for ext, mime in EXTENSION_MAP.items():
            if mime == self.value:
                extensions.add(ext)
        
        return extensions
    
    def matches_extension(self, extension: str) -> bool:
        """Check if this MIME type matches a file extension."""
        extension = extension.lower().lstrip('.')
        expected_mime = EXTENSION_MAP.get(extension)
        return expected_mime == self.value
    
    @classmethod
    def from_extension(cls, extension: str) -> Optional['MimeType']:
        """Create MimeType from file extension."""
        extension = extension.lower().lstrip('.')
        mime_type = EXTENSION_MAP.get(extension)
        
        if mime_type:
            return cls(mime_type)
        
        return None
    
    @classmethod
    def from_filename(cls, filename: str) -> Optional['MimeType']:
        """Create MimeType from filename by extracting extension."""
        if '.' not in filename:
            return None
        
        extension = filename.split('.')[-1]
        return cls.from_extension(extension)
    
    @classmethod 
    def guess_from_content(cls, content: bytes, filename: Optional[str] = None) -> Optional['MimeType']:
        """Guess MIME type from file content and filename."""
        # This is a simplified implementation
        # In production, you might use python-magic or similar
        
        if filename:
            mime_from_filename = cls.from_filename(filename)
            if mime_from_filename:
                return mime_from_filename
        
        # Simple content-based detection
        if content.startswith(b'\\xff\\xd8\\xff'):
            return cls('image/jpeg')
        elif content.startswith(b'\\x89PNG\\r\\n\\x1a\\n'):
            return cls('image/png')
        elif content.startswith(b'GIF8'):
            return cls('image/gif')
        elif content.startswith(b'%PDF'):
            return cls('application/pdf')
        elif content.startswith(b'PK\\x03\\x04'):
            return cls('application/zip')
        
        return None
    
    def __str__(self) -> str:
        """String representation for display."""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation."""
        return f"MimeType('{self.value}')"