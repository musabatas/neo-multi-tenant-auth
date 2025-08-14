"""
Neo Commons Utils Package

This package contains common utility functions and helpers
for the NeoMultiTenant platform.

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

from .metadata import (
    MetadataCollector,
    PerformanceTracker,
    get_api_metadata,
    track_cache_operation,
    track_db_operation,
    create_operation_metadata,
    get_cache_statistics,
    reset_all_counters
)

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
    
    # Metadata utilities
    "MetadataCollector",
    "PerformanceTracker",
    "get_api_metadata",
    "track_cache_operation",
    "track_db_operation",
    "create_operation_metadata",
    "get_cache_statistics",
    "reset_all_counters",
    
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
    "is_uuid_v7_recent"
]