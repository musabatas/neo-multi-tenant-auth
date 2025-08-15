"""
UUID utilities for generating UUIDv7 identifiers.

MIGRATED TO NEO-COMMONS: Now using neo-commons UUID utilities with enhanced features and security.
Import compatibility maintained - all existing imports continue to work.
"""

# NEO-COMMONS IMPORT: Use neo-commons UUID utilities directly
from neo_commons.utils.uuid import (
    # Core UUIDv7 generation
    generate_uuid_v7,
    generate_uuid_v7_object,
    generate_multiple_uuid_v7,
    
    # Timestamp extraction and datetime conversion
    extract_timestamp_from_uuid_v7,
    extract_datetime_from_uuid_v7,
    
    # Validation functions
    is_uuid_v7,
    is_valid_uuid,
    
    # Utility functions
    normalize_uuid,
    uuid_v7_from_timestamp,
    
    # Comparison and sorting
    compare_uuid_v7_timestamps,
    sort_uuids_by_timestamp,
    
    # Age and recency checks
    uuid_v7_age_in_seconds,
    is_uuid_v7_recent,
    
    # Legacy compatibility
    generate_uuid,
    
    # Constants
    NULL_UUID,
    MAX_UUID,
)

# Re-export all functions for backward compatibility
__all__ = [
    # Core UUIDv7 generation
    "generate_uuid_v7",
    "generate_uuid_v7_object",
    "generate_multiple_uuid_v7",
    
    # Timestamp extraction and datetime conversion
    "extract_timestamp_from_uuid_v7",
    "extract_datetime_from_uuid_v7",
    
    # Validation functions
    "is_uuid_v7",
    "is_valid_uuid",
    
    # Utility functions (NEW from neo-commons)
    "normalize_uuid",
    "uuid_v7_from_timestamp",
    
    # Comparison and sorting (NEW from neo-commons)
    "compare_uuid_v7_timestamps",
    "sort_uuids_by_timestamp",
    
    # Age and recency checks (NEW from neo-commons)
    "uuid_v7_age_in_seconds",
    "is_uuid_v7_recent",
    
    # Legacy compatibility
    "generate_uuid",
    
    # Constants (NEW from neo-commons)
    "NULL_UUID",
    "MAX_UUID",
]