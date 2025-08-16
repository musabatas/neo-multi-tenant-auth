"""
Utilities Package - Common utility functions and helpers.

This package contains utility functions that are used across the platform
for consistent data processing, datetime handling, validation, and more.
"""

from neo_commons.utils.datetime import (
    utc_now,
    utc_now_naive,
    to_utc,
    from_utc,
    timestamp_to_utc,
    utc_to_timestamp,
    is_expired,
    time_until_expiry,
    format_utc,
    parse_utc,
    add_timezone,
    remove_timezone,
    format_iso8601,
    UTC,
    EPOCH,
)

from neo_commons.utils.uuid import (
    generate_uuid_v7,
    extract_timestamp_from_uuid_v7,
    is_uuid_v7,
    is_valid_uuid,
    generate_uuid,
    uuid_v7,
)

from neo_commons.utils.encryption import (
    PasswordEncryption,
    get_encryption,
    encrypt_password,
    decrypt_password,
    is_encrypted,
    reset_encryption_instance,
)

from neo_commons.utils.metadata import (
    MetadataCollector,
    track_db_operation,
    track_cache_operation,
    get_basic_metadata,
    get_performance_summary,
)

from .protocols import (
    TimestampProtocol,
    UUIDProtocol,
    EncryptionProtocol,
    MetadataProtocol
)

__all__ = [
    # DateTime utilities
    "utc_now",
    "utc_now_naive", 
    "to_utc",
    "from_utc",
    "timestamp_to_utc",
    "utc_to_timestamp",
    "is_expired",
    "time_until_expiry",
    "format_utc",
    "parse_utc",
    "add_timezone",
    "remove_timezone",
    "format_iso8601",
    "UTC",
    "EPOCH",
    
    # UUID utilities
    "generate_uuid_v7",
    "extract_timestamp_from_uuid_v7",
    "is_uuid_v7",
    "is_valid_uuid",
    "generate_uuid",
    "uuid_v7",
    
    # Encryption utilities
    "PasswordEncryption",
    "get_encryption",
    "encrypt_password",
    "decrypt_password",
    "is_encrypted",
    "reset_encryption_instance",
    
    # Metadata utilities
    "MetadataCollector",
    "track_db_operation",
    "track_cache_operation",
    "get_basic_metadata",
    "get_performance_summary",
    
    # Protocol interfaces
    "TimestampProtocol",
    "UUIDProtocol",
    "EncryptionProtocol",
    "MetadataProtocol"
]