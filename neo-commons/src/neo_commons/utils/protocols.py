"""
Protocol interfaces for utility components.

Protocol-based interfaces for maximum flexibility and reusability
across different platform services in the NeoMultiTenant ecosystem.
"""
from typing import Protocol, Any, Dict, Optional, Union
from datetime import datetime
from uuid import UUID


class TimestampProtocol(Protocol):
    """Protocol for timestamp and datetime utility operations."""
    
    def utc_now(self) -> datetime:
        """Get current UTC datetime with timezone info."""
        ...
    
    def format_iso8601(self, dt: datetime) -> str:
        """Format datetime to ISO 8601 string with timezone."""
        ...
    
    def parse_iso8601(self, iso_string: str) -> datetime:
        """Parse ISO 8601 string to timezone-aware datetime."""
        ...
    
    def to_unix_timestamp(self, dt: datetime) -> int:
        """Convert datetime to Unix timestamp."""
        ...
    
    def from_unix_timestamp(self, timestamp: Union[int, float]) -> datetime:
        """Convert Unix timestamp to datetime."""
        ...


class UUIDProtocol(Protocol):
    """Protocol for UUID generation and validation operations."""
    
    def generate_uuidv7(self) -> str:
        """Generate a UUIDv7 (time-ordered) as string."""
        ...
    
    def generate_uuid4(self) -> str:
        """Generate a UUIDv4 (random) as string."""
        ...
    
    def is_valid_uuid(self, uuid_string: str) -> bool:
        """Validate if string is a valid UUID."""
        ...
    
    def extract_timestamp_from_uuidv7(self, uuid_string: str) -> Optional[datetime]:
        """Extract timestamp from UUIDv7."""
        ...
    
    def normalize_uuid(self, uuid_value: Union[str, UUID]) -> str:
        """Normalize UUID to string format."""
        ...


class EncryptionProtocol(Protocol):
    """Protocol for encryption and decryption operations."""
    
    def encrypt_password(self, password: str) -> str:
        """Encrypt a password using secure hashing."""
        ...
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hashed version."""
        ...
    
    def encrypt_data(self, data: str, key: Optional[str] = None) -> str:
        """Encrypt sensitive data."""
        ...
    
    def decrypt_data(self, encrypted_data: str, key: Optional[str] = None) -> str:
        """Decrypt sensitive data."""
        ...
    
    def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be encrypted."""
        ...


class MetadataProtocol(Protocol):
    """Protocol for metadata collection and processing operations."""
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get service metadata information."""
        ...
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        ...
    
    def format_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format metadata for consistent output."""
        ...
    
    def collect_request_metadata(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Collect metadata from request context."""
        ...
    
    def reset_counters(self) -> None:
        """Reset performance counters."""
        ...