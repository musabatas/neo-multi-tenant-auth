"""
UUID utilities for generating UUIDv7 identifiers.
"""

import uuid
import time
import random
from typing import Optional


def generate_uuid_v7() -> str:
    """Generate a UUIDv7 identifier.
    
    UUIDv7 provides:
    - Time-ordered IDs for better database indexing
    - Millisecond precision timestamps
    - Uniqueness guarantees
    
    Returns:
        String representation of UUIDv7
    """
    # Get current timestamp in milliseconds
    timestamp_ms = int(time.time() * 1000)
    
    # UUIDv7 layout:
    # 48 bits: Unix timestamp in milliseconds
    # 4 bits: Version (0111 for v7)
    # 12 bits: Random data
    # 2 bits: Variant (10)
    # 62 bits: More random data
    
    # Convert timestamp to bytes (48 bits = 6 bytes)
    timestamp_bytes = timestamp_ms.to_bytes(6, byteorder='big')
    
    # Generate random bytes for the rest
    random_bytes = random.getrandbits(74).to_bytes(10, byteorder='big')
    
    # Combine timestamp and random parts
    uuid_bytes = timestamp_bytes + random_bytes
    
    # Set version (v7 = 0111)
    uuid_bytes = bytearray(uuid_bytes)
    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70
    
    # Set variant (10)
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80
    
    # Create UUID from bytes
    return str(uuid.UUID(bytes=bytes(uuid_bytes)))


def extract_timestamp_from_uuid_v7(uuid_str: str) -> Optional[float]:
    """Extract the timestamp from a UUIDv7.
    
    Args:
        uuid_str: String representation of UUIDv7
        
    Returns:
        Timestamp in seconds since Unix epoch, or None if invalid
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
        
        # Extract first 48 bits (timestamp in milliseconds)
        timestamp_ms = int.from_bytes(uuid_obj.bytes[:6], byteorder='big')
        
        # Convert to seconds
        return timestamp_ms / 1000.0
        
    except (ValueError, AttributeError):
        return None


def is_uuid_v7(uuid_str: str) -> bool:
    """Check if a UUID string is version 7.
    
    Args:
        uuid_str: String to check
        
    Returns:
        True if valid UUIDv7, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
        # Check version field (bits 48-51 should be 0111)
        version = (uuid_obj.bytes[6] & 0xF0) >> 4
        return version == 7
    except (ValueError, AttributeError):
        return False