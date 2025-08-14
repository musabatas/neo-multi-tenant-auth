"""
UUID utilities for generating UUIDv7 identifiers.
Enhanced for neo-commons with additional validation and conversion utilities.
"""

import uuid
import time
import random
import secrets
from typing import Optional, Union, List
from datetime import datetime, timezone


def generate_uuid_v7() -> str:
    """
    Generate a UUIDv7 identifier.
    
    UUIDv7 provides:
    - Time-ordered IDs for better database indexing
    - Millisecond precision timestamps
    - Uniqueness guarantees
    - Monotonic ordering within the same millisecond
    
    Returns:
        str: String representation of UUIDv7
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
    
    # Generate cryptographically secure random bytes for the rest
    random_bytes = secrets.randbits(74).to_bytes(10, byteorder='big')
    
    # Combine timestamp and random parts
    uuid_bytes = timestamp_bytes + random_bytes
    
    # Set version (v7 = 0111)
    uuid_bytes = bytearray(uuid_bytes)
    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70
    
    # Set variant (10)
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80
    
    # Create UUID from bytes
    return str(uuid.UUID(bytes=bytes(uuid_bytes)))


def generate_uuid_v7_object() -> uuid.UUID:
    """
    Generate a UUIDv7 as a UUID object.
    
    Returns:
        uuid.UUID: UUIDv7 object
    """
    uuid_str = generate_uuid_v7()
    return uuid.UUID(uuid_str)


def generate_multiple_uuid_v7(count: int) -> List[str]:
    """
    Generate multiple UUIDv7 identifiers.
    
    Args:
        count: Number of UUIDs to generate
        
    Returns:
        List[str]: List of UUIDv7 strings
        
    Raises:
        ValueError: If count is not positive
    """
    if count <= 0:
        raise ValueError("Count must be positive")
    
    return [generate_uuid_v7() for _ in range(count)]


def extract_timestamp_from_uuid_v7(uuid_input: Union[str, uuid.UUID]) -> Optional[float]:
    """
    Extract the timestamp from a UUIDv7.
    
    Args:
        uuid_input: String representation or UUID object
        
    Returns:
        float: Timestamp in seconds since Unix epoch, or None if invalid
    """
    try:
        if isinstance(uuid_input, str):
            uuid_obj = uuid.UUID(uuid_input)
        elif isinstance(uuid_input, uuid.UUID):
            uuid_obj = uuid_input
        else:
            return None
        
        # Check if it's actually UUIDv7
        if not is_uuid_v7(uuid_obj):
            return None
        
        # Extract first 48 bits (timestamp in milliseconds)
        timestamp_ms = int.from_bytes(uuid_obj.bytes[:6], byteorder='big')
        
        # Convert to seconds
        return timestamp_ms / 1000.0
        
    except (ValueError, AttributeError, TypeError):
        return None


def extract_datetime_from_uuid_v7(uuid_input: Union[str, uuid.UUID]) -> Optional[datetime]:
    """
    Extract the datetime from a UUIDv7.
    
    Args:
        uuid_input: String representation or UUID object
        
    Returns:
        datetime: UTC datetime object, or None if invalid
    """
    timestamp = extract_timestamp_from_uuid_v7(uuid_input)
    if timestamp is not None:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return None


def is_uuid_v7(uuid_input: Union[str, uuid.UUID]) -> bool:
    """
    Check if a UUID is version 7.
    
    Args:
        uuid_input: String or UUID object to check
        
    Returns:
        bool: True if valid UUIDv7, False otherwise
    """
    try:
        if isinstance(uuid_input, str):
            uuid_obj = uuid.UUID(uuid_input)
        elif isinstance(uuid_input, uuid.UUID):
            uuid_obj = uuid_input
        else:
            return False
        
        # Check version field (bits 48-51 should be 0111)
        version = (uuid_obj.bytes[6] & 0xF0) >> 4
        return version == 7
    except (ValueError, AttributeError, TypeError):
        return False


def is_valid_uuid(uuid_input: Union[str, uuid.UUID]) -> bool:
    """
    Check if a string or object is a valid UUID of any version.
    
    Args:
        uuid_input: String or UUID object to check
        
    Returns:
        bool: True if valid UUID, False otherwise
    """
    try:
        if isinstance(uuid_input, uuid.UUID):
            return True
        elif isinstance(uuid_input, str):
            uuid.UUID(uuid_input)
            return True
        else:
            return False
    except (ValueError, TypeError):
        return False


def normalize_uuid(uuid_input: Union[str, uuid.UUID]) -> Optional[str]:
    """
    Normalize a UUID to standard string format.
    
    Args:
        uuid_input: UUID string or object to normalize
        
    Returns:
        str: Normalized UUID string, or None if invalid
    """
    try:
        if isinstance(uuid_input, str):
            return str(uuid.UUID(uuid_input))
        elif isinstance(uuid_input, uuid.UUID):
            return str(uuid_input)
        else:
            return None
    except (ValueError, TypeError):
        return None


def uuid_v7_from_timestamp(timestamp_ms: int, random_data: Optional[bytes] = None) -> str:
    """
    Generate a UUIDv7 from a specific timestamp.
    Useful for testing or when you need deterministic ordering.
    
    Args:
        timestamp_ms: Timestamp in milliseconds since Unix epoch
        random_data: Optional 10 bytes of random data (generated if not provided)
        
    Returns:
        str: UUIDv7 string
        
    Raises:
        ValueError: If timestamp is invalid or random_data is wrong size
    """
    if timestamp_ms < 0 or timestamp_ms > (2**48 - 1):
        raise ValueError("Timestamp must be between 0 and 2^48 - 1")
    
    # Convert timestamp to bytes (48 bits = 6 bytes)
    timestamp_bytes = timestamp_ms.to_bytes(6, byteorder='big')
    
    # Use provided random data or generate it
    if random_data is None:
        random_bytes = secrets.randbits(74).to_bytes(10, byteorder='big')
    else:
        if len(random_data) != 10:
            raise ValueError("Random data must be exactly 10 bytes")
        random_bytes = random_data
    
    # Combine timestamp and random parts
    uuid_bytes = timestamp_bytes + random_bytes
    
    # Set version (v7 = 0111)
    uuid_bytes = bytearray(uuid_bytes)
    uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70
    
    # Set variant (10)
    uuid_bytes[8] = (uuid_bytes[8] & 0x3F) | 0x80
    
    # Create UUID from bytes
    return str(uuid.UUID(bytes=bytes(uuid_bytes)))


def compare_uuid_v7_timestamps(uuid1: Union[str, uuid.UUID], uuid2: Union[str, uuid.UUID]) -> Optional[int]:
    """
    Compare the timestamps of two UUIDv7 identifiers.
    
    Args:
        uuid1: First UUIDv7 to compare
        uuid2: Second UUIDv7 to compare
        
    Returns:
        int: -1 if uuid1 is older, 1 if uuid1 is newer, 0 if same timestamp, None if invalid
    """
    timestamp1 = extract_timestamp_from_uuid_v7(uuid1)
    timestamp2 = extract_timestamp_from_uuid_v7(uuid2)
    
    if timestamp1 is None or timestamp2 is None:
        return None
    
    if timestamp1 < timestamp2:
        return -1
    elif timestamp1 > timestamp2:
        return 1
    else:
        return 0


def sort_uuids_by_timestamp(uuid_list: List[Union[str, uuid.UUID]], reverse: bool = False) -> List[str]:
    """
    Sort a list of UUIDv7 identifiers by their embedded timestamps.
    Non-UUIDv7 values are filtered out.
    
    Args:
        uuid_list: List of UUIDs to sort
        reverse: If True, sort newest first
        
    Returns:
        List[str]: Sorted list of UUIDv7 strings
    """
    valid_uuids = []
    
    for uuid_input in uuid_list:
        if is_uuid_v7(uuid_input):
            normalized = normalize_uuid(uuid_input)
            if normalized:
                timestamp = extract_timestamp_from_uuid_v7(normalized)
                if timestamp is not None:
                    valid_uuids.append((timestamp, normalized))
    
    # Sort by timestamp
    valid_uuids.sort(key=lambda x: x[0], reverse=reverse)
    
    # Return just the UUID strings
    return [uuid_str for _, uuid_str in valid_uuids]


def uuid_v7_age_in_seconds(uuid_input: Union[str, uuid.UUID]) -> Optional[float]:
    """
    Calculate the age of a UUIDv7 in seconds from now.
    
    Args:
        uuid_input: UUIDv7 to calculate age for
        
    Returns:
        float: Age in seconds (positive if in the past), or None if invalid
    """
    timestamp = extract_timestamp_from_uuid_v7(uuid_input)
    if timestamp is not None:
        return time.time() - timestamp
    return None


def is_uuid_v7_recent(uuid_input: Union[str, uuid.UUID], threshold_seconds: float = 300) -> bool:
    """
    Check if a UUIDv7 was generated recently.
    
    Args:
        uuid_input: UUIDv7 to check
        threshold_seconds: Maximum age in seconds (default: 5 minutes)
        
    Returns:
        bool: True if within threshold, False otherwise
    """
    age = uuid_v7_age_in_seconds(uuid_input)
    return age is not None and 0 <= age <= threshold_seconds


# Legacy compatibility function
def generate_uuid() -> str:
    """
    Legacy function that generates UUIDv7.
    Kept for backward compatibility.
    
    Returns:
        str: UUIDv7 string
    """
    return generate_uuid_v7()


# Convenience constants
NULL_UUID = str(uuid.UUID(int=0))
MAX_UUID = str(uuid.UUID(int=2**128 - 1))