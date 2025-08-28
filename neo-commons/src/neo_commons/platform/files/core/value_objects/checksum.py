"""File checksum value object.

ONLY file checksum - represents validated file checksum with algorithm support,
verification capabilities, and integrity validation.

Following maximum separation architecture - one file = one purpose.
"""

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import BinaryIO, Union, Optional

# No ValueObject base class needed - using plain dataclass


class ChecksumAlgorithm(Enum):
    """Supported checksum algorithms."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"


@dataclass(frozen=True)
class Checksum:
    """File checksum value object.
    
    Represents a file checksum with algorithm specification and validation.
    Provides methods for checksum calculation, verification, and format
    validation.
    
    Features:
    - Multiple algorithm support (MD5, SHA1, SHA256, SHA512)
    - Format validation with algorithm prefix
    - File content verification
    - Stream-based calculation for large files
    - Secure comparison operations
    """
    
    value: str  # Format: "algorithm:hexdigest" (e.g., "sha256:abc123...")
    
    # Supported algorithms
    SUPPORTED_ALGORITHMS = {alg.value for alg in ChecksumAlgorithm}
    
    # Algorithm display names
    ALGORITHM_NAMES = {
        ChecksumAlgorithm.MD5.value: "MD5",
        ChecksumAlgorithm.SHA1.value: "SHA-1",
        ChecksumAlgorithm.SHA256.value: "SHA-256",
        ChecksumAlgorithm.SHA512.value: "SHA-512"
    }
    
    # Recommended algorithm for new files
    DEFAULT_ALGORITHM = ChecksumAlgorithm.SHA256
    
    def __post_init__(self):
        """Validate checksum format and algorithm."""
        if not isinstance(self.value, str):
            raise ValueError(f"Checksum must be a string, got {type(self.value).__name__}")
        
        if not self.value or not self.value.strip():
            raise ValueError("Checksum cannot be empty")
        
        normalized = self.value.strip().lower()
        
        # Validate format: "algorithm:hexdigest"
        if ':' not in normalized:
            raise ValueError(f"Invalid checksum format: {self.value}. Expected format: 'algorithm:hexdigest'")
        
        algorithm, hexdigest = normalized.split(':', 1)
        
        # Validate algorithm
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"Unsupported checksum algorithm: {algorithm}. "
                f"Supported algorithms: {', '.join(sorted(self.SUPPORTED_ALGORITHMS))}"
            )
        
        # Validate hexdigest format
        if not hexdigest:
            raise ValueError("Checksum digest cannot be empty")
        
        # Validate hexadecimal format
        try:
            int(hexdigest, 16)
        except ValueError as e:
            raise ValueError(f"Invalid hexadecimal digest: {hexdigest}") from e
        
        # Validate digest length for known algorithms
        expected_lengths = {
            ChecksumAlgorithm.MD5.value: 32,
            ChecksumAlgorithm.SHA1.value: 40,
            ChecksumAlgorithm.SHA256.value: 64,
            ChecksumAlgorithm.SHA512.value: 128
        }
        
        expected_length = expected_lengths.get(algorithm)
        if expected_length and len(hexdigest) != expected_length:
            raise ValueError(
                f"Invalid digest length for {algorithm}: got {len(hexdigest)}, expected {expected_length}"
            )
        
        # Store normalized value
        object.__setattr__(self, 'value', normalized)
    
    @classmethod
    def calculate_from_bytes(cls, content: bytes, algorithm: ChecksumAlgorithm = None) -> 'Checksum':
        """Calculate checksum from byte content."""
        if algorithm is None:
            algorithm = cls.DEFAULT_ALGORITHM
        
        hasher = hashlib.new(algorithm.value)
        hasher.update(content)
        digest = hasher.hexdigest()
        
        return cls(f"{algorithm.value}:{digest}")
    
    @classmethod
    def calculate_from_file(cls, file_path: str, algorithm: ChecksumAlgorithm = None) -> 'Checksum':
        """Calculate checksum from file path."""
        if algorithm is None:
            algorithm = cls.DEFAULT_ALGORITHM
        
        hasher = hashlib.new(algorithm.value)
        
        try:
            with open(file_path, 'rb') as f:
                # Read file in chunks to handle large files efficiently
                chunk_size = 8192
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
        except IOError as e:
            raise ValueError(f"Failed to read file for checksum calculation: {e}") from e
        
        digest = hasher.hexdigest()
        return cls(f"{algorithm.value}:{digest}")
    
    @classmethod
    def calculate_from_stream(cls, stream: BinaryIO, algorithm: ChecksumAlgorithm = None) -> 'Checksum':
        """Calculate checksum from binary stream."""
        if algorithm is None:
            algorithm = cls.DEFAULT_ALGORITHM
        
        hasher = hashlib.new(algorithm.value)
        
        # Save current position
        original_position = stream.tell() if hasattr(stream, 'tell') else None
        
        try:
            # Read stream in chunks
            chunk_size = 8192
            while chunk := stream.read(chunk_size):
                hasher.update(chunk)
        finally:
            # Restore original position if possible
            if original_position is not None and hasattr(stream, 'seek'):
                try:
                    stream.seek(original_position)
                except (IOError, OSError):
                    pass  # Stream might not be seekable
        
        digest = hasher.hexdigest()
        return cls(f"{algorithm.value}:{digest}")
    
    @classmethod
    def from_algorithm_and_digest(cls, algorithm: ChecksumAlgorithm, digest: str) -> 'Checksum':
        """Create checksum from algorithm and digest components."""
        return cls(f"{algorithm.value}:{digest.lower()}")
    
    def get_algorithm(self) -> ChecksumAlgorithm:
        """Get the checksum algorithm."""
        algorithm_str = self.value.split(':', 1)[0]
        return ChecksumAlgorithm(algorithm_str)
    
    def get_algorithm_name(self) -> str:
        """Get the display name of the algorithm."""
        algorithm = self.get_algorithm()
        return self.ALGORITHM_NAMES.get(algorithm.value, algorithm.value.upper())
    
    def get_digest(self) -> str:
        """Get the hexadecimal digest part."""
        return self.value.split(':', 1)[1]
    
    def verify_bytes(self, content: bytes) -> bool:
        """Verify checksum against byte content."""
        try:
            calculated = self.calculate_from_bytes(content, self.get_algorithm())
            return self.secure_compare(calculated)
        except Exception:
            return False
    
    def verify_file(self, file_path: str) -> bool:
        """Verify checksum against file content."""
        try:
            calculated = self.calculate_from_file(file_path, self.get_algorithm())
            return self.secure_compare(calculated)
        except Exception:
            return False
    
    def verify_stream(self, stream: BinaryIO) -> bool:
        """Verify checksum against stream content."""
        try:
            calculated = self.calculate_from_stream(stream, self.get_algorithm())
            return self.secure_compare(calculated)
        except Exception:
            return False
    
    def secure_compare(self, other: 'Checksum') -> bool:
        """Secure comparison to prevent timing attacks."""
        if not isinstance(other, Checksum):
            return False
        
        # Use hmac.compare_digest for constant-time comparison
        import hmac
        return hmac.compare_digest(self.value, other.value)
    
    def is_algorithm(self, algorithm: ChecksumAlgorithm) -> bool:
        """Check if checksum uses specific algorithm."""
        return self.get_algorithm() == algorithm
    
    def is_secure_algorithm(self) -> bool:
        """Check if algorithm is considered cryptographically secure."""
        algorithm = self.get_algorithm()
        # MD5 and SHA1 are considered weak
        return algorithm in {ChecksumAlgorithm.SHA256, ChecksumAlgorithm.SHA512}
    
    def upgrade_to_secure(self, content: bytes) -> 'Checksum':
        """Upgrade to a secure algorithm if current one is weak."""
        if self.is_secure_algorithm():
            return self
        
        # Upgrade to SHA256
        return self.calculate_from_bytes(content, ChecksumAlgorithm.SHA256)
    
    def __eq__(self, other) -> bool:
        """Secure equality comparison."""
        if isinstance(other, Checksum):
            return self.secure_compare(other)
        return False
    
    def __hash__(self) -> int:
        """Hash implementation for use in sets and dicts."""
        return hash(self.value)
    
    def __str__(self) -> str:
        """String representation for display."""
        return self.value
    
    def __repr__(self) -> str:
        """Developer representation."""
        algorithm = self.get_algorithm_name()
        digest = self.get_digest()[:12] + "..." if len(self.get_digest()) > 12 else self.get_digest()
        return f"Checksum({algorithm}: {digest})"