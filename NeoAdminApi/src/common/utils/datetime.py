"""
DateTime utilities for consistent timezone handling.

MIGRATED TO NEO-COMMONS: Now using neo-commons datetime utilities with additional helpful functions.
Import compatibility maintained - all existing imports continue to work.
"""

# NEO-COMMONS IMPORT: Use neo-commons datetime utilities directly
from neo_commons.utils.datetime import (
    # Core datetime functions
    utc_now,
    utc_now_naive,
    to_utc,
    from_utc,
    timestamp_to_utc,
    utc_to_timestamp,
    
    # Expiry and time calculations
    is_expired,
    time_until_expiry,
    age_in_seconds,
    is_recent,
    
    # Formatting and parsing
    format_utc,
    parse_utc,
    parse_iso8601,
    format_iso8601,
    
    # Timezone operations
    add_timezone,
    remove_timezone,
    
    # Day boundaries
    start_of_day,
    end_of_day,
    
    # Constants
    UTC,
    EPOCH,
)

# Re-export for backward compatibility
__all__ = [
    # Core datetime functions
    "utc_now",
    "utc_now_naive", 
    "to_utc",
    "from_utc",
    "timestamp_to_utc",
    "utc_to_timestamp",
    
    # Expiry and time calculations
    "is_expired",
    "time_until_expiry",
    "age_in_seconds",
    "is_recent",
    
    # Formatting and parsing
    "format_utc",
    "parse_utc",
    "parse_iso8601",
    "format_iso8601",
    
    # Timezone operations
    "add_timezone",
    "remove_timezone",
    
    # Day boundaries (NEW from neo-commons)
    "start_of_day",
    "end_of_day",
    
    # Constants
    "UTC",
    "EPOCH",
]