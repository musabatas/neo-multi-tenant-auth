"""File type validator.

ONLY file type validation - handles MIME type checking,
extension validation, and content type verification.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from typing import Set, Optional, Dict, List

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

from ...core.value_objects.mime_type import MimeType
from ...core.exceptions.invalid_file_type import InvalidFileType


@dataclass
class FileTypeValidatorConfig:
    """Configuration for file type validator."""
    
    # Allowed MIME types (None means allow all)
    allowed_mime_types: Optional[Set[str]] = None
    
    # Blocked MIME types (takes precedence over allowed)
    blocked_mime_types: Optional[Set[str]] = None
    
    # Allowed file extensions
    allowed_extensions: Optional[Set[str]] = None
    
    # Blocked file extensions (takes precedence over allowed)
    blocked_extensions: Optional[Set[str]] = None
    
    # Validation strictness
    verify_content_matches_extension: bool = True
    verify_content_matches_mime_type: bool = True
    detect_mime_from_content: bool = True
    
    # Security settings
    scan_for_embedded_executables: bool = True
    block_double_extensions: bool = True  # e.g., file.pdf.exe
    max_filename_length: int = 255


class ValidationResult:
    """File type validation result."""
    
    def __init__(self, valid: bool, reason: Optional[str] = None, details: Optional[Dict] = None):
        self.valid = valid
        self.reason = reason
        self.details = details or {}


class FileTypeValidator:
    """File type validation service.
    
    Handles comprehensive file type validation including:
    - MIME type allowlists and blocklists
    - File extension validation
    - Content-based type detection
    - Security scanning for embedded threats
    - Double extension detection
    - Content vs extension consistency
    - Filename safety validation
    """
    
    def __init__(self, config: Optional[FileTypeValidatorConfig] = None):
        """Initialize file type validator.
        
        Args:
            config: Validator configuration
        """
        self._config = config or FileTypeValidatorConfig()
        
        # Initialize default configurations if not provided
        if self._config.allowed_mime_types is None:
            self._config.allowed_mime_types = self._get_default_allowed_mime_types()
        
        if self._config.blocked_mime_types is None:
            self._config.blocked_mime_types = self._get_default_blocked_mime_types()
        
        if self._config.allowed_extensions is None:
            self._config.allowed_extensions = self._get_default_allowed_extensions()
        
        if self._config.blocked_extensions is None:
            self._config.blocked_extensions = self._get_default_blocked_extensions()
    
    def validate_file(
        self,
        filename: str,
        content: bytes,
        declared_mime_type: Optional[str] = None
    ) -> ValidationResult:
        """Validate file type comprehensively.
        
        Args:
            filename: Original filename with extension
            content: File content bytes
            declared_mime_type: MIME type provided by client
            
        Returns:
            ValidationResult with validation status and details
        """
        try:
            # 1. Validate filename
            filename_result = self._validate_filename(filename)
            if not filename_result.valid:
                return filename_result
            
            # 2. Extract and validate extension
            extension = self._extract_extension(filename)
            extension_result = self._validate_extension(extension)
            if not extension_result.valid:
                return extension_result
            
            # 3. Detect MIME type from content
            detected_mime_type = None
            if self._config.detect_mime_from_content:
                detected_mime_type = self._detect_mime_type(content)
            
            # 4. Validate MIME type
            mime_type_to_validate = declared_mime_type or detected_mime_type
            if mime_type_to_validate:
                mime_result = self._validate_mime_type(mime_type_to_validate)
                if not mime_result.valid:
                    return mime_result
            
            # 5. Cross-validate extension vs MIME type
            if self._config.verify_content_matches_extension and detected_mime_type:
                consistency_result = self._validate_extension_mime_consistency(
                    extension, detected_mime_type
                )
                if not consistency_result.valid:
                    return consistency_result
            
            # 6. Security validation
            security_result = self._validate_security(filename, content)
            if not security_result.valid:
                return security_result
            
            # All validations passed
            return ValidationResult(
                valid=True,
                details={
                    "filename": filename,
                    "extension": extension,
                    "declared_mime_type": declared_mime_type,
                    "detected_mime_type": detected_mime_type,
                    "validation_checks": [
                        "filename_valid",
                        "extension_allowed", 
                        "mime_type_allowed",
                        "content_consistency",
                        "security_passed"
                    ]
                }
            )
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                reason=f"Validation error: {str(e)}",
                details={"error_type": "validation_exception"}
            )
    
    def _validate_filename(self, filename: str) -> ValidationResult:
        """Validate filename safety and structure."""
        # Check length
        if len(filename) > self._config.max_filename_length:
            return ValidationResult(
                valid=False,
                reason=f"Filename too long: {len(filename)} > {self._config.max_filename_length}",
                details={"filename_length": len(filename)}
            )
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00', '\r', '\n']
        for char in dangerous_chars:
            if char in filename:
                return ValidationResult(
                    valid=False,
                    reason=f"Filename contains dangerous character: '{char}'",
                    details={"dangerous_character": char}
                )
        
        # Check for double extensions if enabled
        if self._config.block_double_extensions:
            parts = filename.split('.')
            if len(parts) > 2:  # More than one extension
                # Check if any part except the last looks like an executable extension
                executable_extensions = {'.exe', '.bat', '.cmd', '.com', '.scr', '.pif'}
                for part in parts[1:-1]:  # Skip filename and last extension
                    if f".{part.lower()}" in executable_extensions:
                        return ValidationResult(
                            valid=False,
                            reason=f"Double extension detected with executable: .{part}",
                            details={"double_extension": f".{part}"}
                        )
        
        return ValidationResult(valid=True)
    
    def _extract_extension(self, filename: str) -> str:
        """Extract file extension from filename."""
        if '.' not in filename:
            return ""
        return filename.split('.')[-1].lower()
    
    def _validate_extension(self, extension: str) -> ValidationResult:
        """Validate file extension against allowlists and blocklists."""
        # Check blocked extensions first
        if extension in self._config.blocked_extensions:
            return ValidationResult(
                valid=False,
                reason=f"File extension '{extension}' is blocked",
                details={"blocked_extension": extension}
            )
        
        # Check allowed extensions
        if self._config.allowed_extensions and extension not in self._config.allowed_extensions:
            return ValidationResult(
                valid=False,
                reason=f"File extension '{extension}' is not allowed",
                details={"disallowed_extension": extension}
            )
        
        return ValidationResult(valid=True)
    
    def _detect_mime_type(self, content: bytes) -> Optional[str]:
        """Detect MIME type from file content."""
        try:
            # Use python-magic for content-based detection if available
            if HAS_MAGIC:
                return magic.from_buffer(content, mime=True)
            else:
                # Fallback to basic detection if magic is not available
                return None
        except Exception:
            # Fallback to basic detection if magic fails
            return None
    
    def _validate_mime_type(self, mime_type: str) -> ValidationResult:
        """Validate MIME type against allowlists and blocklists."""
        # Check blocked MIME types first
        if mime_type in self._config.blocked_mime_types:
            return ValidationResult(
                valid=False,
                reason=f"MIME type '{mime_type}' is blocked",
                details={"blocked_mime_type": mime_type}
            )
        
        # Check allowed MIME types
        if self._config.allowed_mime_types and mime_type not in self._config.allowed_mime_types:
            return ValidationResult(
                valid=False,
                reason=f"MIME type '{mime_type}' is not allowed",
                details={"disallowed_mime_type": mime_type}
            )
        
        return ValidationResult(valid=True)
    
    def _validate_extension_mime_consistency(self, extension: str, mime_type: str) -> ValidationResult:
        """Validate consistency between extension and detected MIME type."""
        expected_mime_types = self._get_expected_mime_types_for_extension(extension)
        
        if expected_mime_types and mime_type not in expected_mime_types:
            return ValidationResult(
                valid=False,
                reason=f"MIME type '{mime_type}' doesn't match extension '{extension}'",
                details={
                    "extension": extension,
                    "detected_mime_type": mime_type,
                    "expected_mime_types": list(expected_mime_types)
                }
            )
        
        return ValidationResult(valid=True)
    
    def _validate_security(self, filename: str, content: bytes) -> ValidationResult:
        """Perform security validation on file."""
        if self._config.scan_for_embedded_executables:
            # Basic check for executable signatures in content
            executable_signatures = [
                b'MZ',      # DOS/Windows executable
                b'\x7fELF',  # Linux ELF executable
                b'\xca\xfe\xba\xbe',  # Mach-O (macOS)
                b'PK\x03\x04',  # ZIP/JAR (could contain executables)
            ]
            
            for signature in executable_signatures:
                if content.startswith(signature):
                    return ValidationResult(
                        valid=False,
                        reason="File appears to contain executable code",
                        details={"executable_signature": signature.hex()}
                    )
        
        return ValidationResult(valid=True)
    
    def _get_expected_mime_types_for_extension(self, extension: str) -> Optional[Set[str]]:
        """Get expected MIME types for file extension."""
        extension_map = {
            'txt': {'text/plain'},
            'pdf': {'application/pdf'},
            'doc': {'application/msword'},
            'docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'},
            'jpg': {'image/jpeg'},
            'jpeg': {'image/jpeg'},
            'png': {'image/png'},
            'gif': {'image/gif'},
            'mp4': {'video/mp4'},
            'avi': {'video/x-msvideo'},
            'zip': {'application/zip'},
            'json': {'application/json'},
            'xml': {'application/xml', 'text/xml'},
            'csv': {'text/csv'},
            'html': {'text/html'},
            'css': {'text/css'},
            'js': {'application/javascript', 'text/javascript'},
        }
        
        return extension_map.get(extension)
    
    def _get_default_allowed_mime_types(self) -> Set[str]:
        """Get default allowed MIME types."""
        return {
            # Text
            'text/plain',
            'text/csv',
            'text/html',
            'text/css',
            'application/json',
            'application/xml',
            
            # Documents
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            
            # Images
            'image/jpeg',
            'image/png',
            'image/gif',
            'image/webp',
            'image/svg+xml',
            
            # Video
            'video/mp4',
            'video/avi',
            'video/quicktime',
            
            # Audio
            'audio/mpeg',
            'audio/wav',
            'audio/ogg',
            
            # Archives
            'application/zip',
            'application/x-tar',
            'application/gzip',
        }
    
    def _get_default_blocked_mime_types(self) -> Set[str]:
        """Get default blocked MIME types."""
        return {
            # Executables
            'application/x-executable',
            'application/x-msdownload',
            'application/octet-stream',  # Generic binary - often executables
            
            # Scripts
            'application/x-sh',
            'application/x-csh',
            'text/x-python',
            'text/x-php',
        }
    
    def _get_default_allowed_extensions(self) -> Set[str]:
        """Get default allowed file extensions."""
        return {
            # Text
            'txt', 'csv', 'json', 'xml', 'html', 'css', 'js',
            
            # Documents  
            'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
            
            # Images
            'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
            
            # Video
            'mp4', 'avi', 'mov', 'wmv', 'flv',
            
            # Audio
            'mp3', 'wav', 'ogg', 'flac',
            
            # Archives
            'zip', 'tar', 'gz', 'bz2',
        }
    
    def _get_default_blocked_extensions(self) -> Set[str]:
        """Get default blocked file extensions."""
        return {
            # Executables
            'exe', 'bat', 'cmd', 'com', 'scr', 'pif', 'msi',
            
            # Scripts
            'sh', 'csh', 'py', 'php', 'pl', 'rb',
            
            # System files
            'sys', 'dll', 'deb', 'rpm',
        }


# Factory function for dependency injection
def create_file_type_validator(config: Optional[FileTypeValidatorConfig] = None) -> FileTypeValidator:
    """Create file type validator."""
    return FileTypeValidator(config)