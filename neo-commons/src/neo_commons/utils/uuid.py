"""UUID utilities for neo-commons."""

import uuid
import time
from typing import Optional, Union
from datetime import datetime, timezone


def generate_uuid_v7() -> str:
    """
    Generate a UUIDv7 with time-based ordering.
    
    UUIDv7 provides better database performance by being time-ordered,
    which improves index performance and reduces page fragmentation.
    
    Returns:
        String representation of UUIDv7
    """
    # Get current timestamp in milliseconds
    timestamp_ms = int(time.time() * 1000)
    
    # Create timestamp bytes (48 bits)
    timestamp_bytes = timestamp_ms.to_bytes(6, byteorder='big')
    
    # Generate random bytes for the rest (80 bits)
    random_bytes = uuid.uuid4().bytes[6:]
    
    # Combine timestamp and random bytes
    uuid_bytes = timestamp_bytes + random_bytes
    
    # Set version to 7 (bits 12-15 of the 7th byte)
    uuid_bytes = uuid_bytes[:6] + bytes([(uuid_bytes[6] & 0x0f) | 0x70]) + uuid_bytes[7:]
    
    # Set variant to 10 (bits 6-7 of the 9th byte)  
    uuid_bytes = uuid_bytes[:8] + bytes([(uuid_bytes[8] & 0x3f) | 0x80]) + uuid_bytes[9:]
    
    # Create UUID from bytes
    result_uuid = uuid.UUID(bytes=uuid_bytes)
    
    return str(result_uuid)


def generate_uuid_v4() -> str:
    """
    Generate a standard UUIDv4 (random).
    
    Returns:
        String representation of UUIDv4
    """
    return str(uuid.uuid4())


def extract_timestamp_from_uuid_v7(uuid_str: str) -> Optional[datetime]:
    """
    Extract timestamp from UUIDv7.
    
    Args:
        uuid_str: String representation of UUIDv7
        
    Returns:
        Datetime object representing the timestamp, or None if invalid
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
        
        # Check if it's a UUIDv7 (version field should be 7)
        if uuid_obj.version != 7:
            return None
        
        # Extract timestamp from the first 48 bits
        uuid_bytes = uuid_obj.bytes
        timestamp_bytes = uuid_bytes[:6]
        
        # Convert bytes to milliseconds timestamp
        timestamp_ms = int.from_bytes(timestamp_bytes, byteorder='big')
        
        # Convert to datetime
        timestamp_seconds = timestamp_ms / 1000.0
        return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        
    except (ValueError, TypeError):
        return None


def is_valid_uuid(uuid_str: str, version: Optional[int] = None) -> bool:
    """
    Check if string is a valid UUID.
    
    Args:
        uuid_str: String to validate
        version: Optional specific version to check (4, 7, etc.)
        
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(uuid_str)
        
        if version is not None:
            return uuid_obj.version == version
            
        return True
        
    except (ValueError, TypeError):
        return False


def is_uuid_v7(uuid_str: str) -> bool:
    """
    Check if string is a valid UUIDv7.
    
    Args:
        uuid_str: String to validate
        
    Returns:
        True if valid UUIDv7, False otherwise
    """
    return is_valid_uuid(uuid_str, version=7)


def is_uuid_v4(uuid_str: str) -> bool:
    """
    Check if string is a valid UUIDv4.
    
    Args:
        uuid_str: String to validate
        
    Returns:
        True if valid UUIDv4, False otherwise
    """
    return is_valid_uuid(uuid_str, version=4)


def generate_short_id(length: int = 8) -> str:
    """
    Generate a short alphanumeric ID.
    
    Useful for human-readable IDs, slugs, etc.
    
    Args:
        length: Length of the generated ID
        
    Returns:
        Short alphanumeric string
    """
    import secrets
    import string
    
    alphabet = string.ascii_lowercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_tenant_slug(organization_name: str, tenant_name: str) -> str:
    """
    Generate a tenant slug from organization and tenant names.
    
    Args:
        organization_name: Name of the organization
        tenant_name: Name of the tenant
        
    Returns:
        URL-safe slug for the tenant
    """
    import re
    
    # Combine organization and tenant names
    combined = f"{organization_name}-{tenant_name}"
    
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-z0-9]+', '-', combined.lower())
    
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Limit length and ensure it doesn't end with hyphen
    if len(slug) > 50:
        slug = slug[:47] + '...'
    
    # Add random suffix if needed to ensure uniqueness
    if len(slug) < 3:
        slug += '-' + generate_short_id(4)
    
    return slug


def normalize_uuid(uuid_input: Union[str, uuid.UUID]) -> str:
    """
    Normalize UUID input to lowercase string without hyphens.
    
    Args:
        uuid_input: UUID as string or UUID object
        
    Returns:
        Normalized UUID string
        
    Raises:
        ValueError: If input is not a valid UUID
    """
    if isinstance(uuid_input, uuid.UUID):
        return str(uuid_input).lower()
    
    if isinstance(uuid_input, str):
        # Validate the UUID first
        try:
            uuid_obj = uuid.UUID(uuid_input)
            return str(uuid_obj).lower()
        except ValueError:
            raise ValueError(f"Invalid UUID format: {uuid_input}")
    
    raise ValueError(f"UUID must be string or UUID object, got {type(uuid_input)}")


def uuid_to_base64(uuid_str: str) -> str:
    """
    Convert UUID to base64 string for compact representation.
    
    Args:
        uuid_str: UUID string
        
    Returns:
        Base64 encoded UUID
        
    Raises:
        ValueError: If input is not a valid UUID
    """
    import base64
    
    try:
        uuid_obj = uuid.UUID(uuid_str)
        return base64.urlsafe_b64encode(uuid_obj.bytes).decode('ascii').rstrip('=')
    except ValueError:
        raise ValueError(f"Invalid UUID format: {uuid_str}")


def base64_to_uuid(base64_str: str) -> str:
    """
    Convert base64 string back to UUID.
    
    Args:
        base64_str: Base64 encoded UUID
        
    Returns:
        UUID string
        
    Raises:
        ValueError: If input is not a valid base64 UUID
    """
    import base64
    
    try:
        # Add padding if needed
        padding = 4 - (len(base64_str) % 4)
        if padding != 4:
            base64_str += '=' * padding
        
        uuid_bytes = base64.urlsafe_b64decode(base64_str)
        uuid_obj = uuid.UUID(bytes=uuid_bytes)
        return str(uuid_obj)
    except Exception:
        raise ValueError(f"Invalid base64 UUID format: {base64_str}")


class UUIDGenerator:
    """UUID generator with configurable defaults."""
    
    def __init__(self, default_version: int = 7):
        """
        Initialize UUID generator.
        
        Args:
            default_version: Default UUID version to generate (4 or 7)
        """
        if default_version not in (4, 7):
            raise ValueError("UUID version must be 4 or 7")
        
        self.default_version = default_version
    
    def generate(self) -> str:
        """Generate UUID using default version."""
        if self.default_version == 7:
            return generate_uuid_v7()
        else:
            return generate_uuid_v4()
    
    def generate_v4(self) -> str:
        """Generate UUIDv4."""
        return generate_uuid_v4()
    
    def generate_v7(self) -> str:
        """Generate UUIDv7."""
        return generate_uuid_v7()


# Default generator instance
default_generator = UUIDGenerator(default_version=7)

# Convenience functions using default generator
generate = default_generator.generate
generate_id = default_generator.generate

# Aliases for compatibility
generate_uuid7 = generate_uuid_v7
generate_uuid4 = generate_uuid_v4