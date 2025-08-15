"""
Neo Commons Utils Package

This package contains common utility functions and helpers
for neo-commons applications.

Components:
- Datetime: Timezone-aware datetime utilities and formatting
- Encryption: Password and data encryption with PBKDF2 + Fernet
- Metadata: Request metadata collection and performance tracking
- UUID: UUIDv7 generation and manipulation utilities
"""

# Import commonly used functions for convenience
from .datetime import (
    utc_now,
    utc_now_naive,
    format_iso8601,
    parse_iso8601,
    to_utc,
    from_utc,
    is_expired,
    format_utc,
    UTC,
    EPOCH
)

from .encryption import (
    PasswordEncryption,
    encrypt_password,
    decrypt_password,
    decrypt_password_safe,
    is_encrypted,
    encrypt_data,
    decrypt_data_to_string,
    validate_encryption_key
)

# Note: metadata functionality moved to middleware.unified_context
# Use UnifiedRequestContext for metadata collection

from .uuid import (
    generate_uuid_v7,
    generate_uuid_v7_object,
    extract_timestamp_from_uuid_v7,
    extract_datetime_from_uuid_v7,
    is_uuid_v7,
    is_valid_uuid,
    normalize_uuid,
    compare_uuid_v7_timestamps,
    sort_uuids_by_timestamp,
    uuid_v7_age_in_seconds,
    is_uuid_v7_recent
)

# Aliases for backward compatibility and convenience
generate_uuid7 = generate_uuid_v7
extract_timestamp_from_uuid7 = extract_timestamp_from_uuid_v7

__all__ = [
    # Datetime utilities
    "utc_now",
    "utc_now_naive", 
    "format_iso8601",
    "parse_iso8601",
    "to_utc",
    "from_utc",
    "is_expired",
    "format_utc",
    "UTC",
    "EPOCH",
    
    # Encryption utilities
    "PasswordEncryption",
    "encrypt_password",
    "decrypt_password",
    "decrypt_password_safe",
    "is_encrypted",
    "encrypt_data", 
    "decrypt_data_to_string",
    "validate_encryption_key",
    
    # Note: Metadata utilities moved to middleware.unified_context
    
    # UUID utilities
    "generate_uuid_v7",
    "generate_uuid_v7_object",
    "extract_timestamp_from_uuid_v7",
    "extract_datetime_from_uuid_v7",
    "is_uuid_v7",
    "is_valid_uuid",
    "normalize_uuid",
    "compare_uuid_v7_timestamps", 
    "sort_uuids_by_timestamp",
    "uuid_v7_age_in_seconds",
    "is_uuid_v7_recent",
    # Aliases
    "generate_uuid7",
    "extract_timestamp_from_uuid7"
]