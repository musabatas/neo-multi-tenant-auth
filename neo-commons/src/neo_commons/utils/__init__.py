"""Utilities module for neo-commons.

This module provides utility functions and helpers used throughout
the neo-commons library.
"""

from .uuid import *
from .timezone import *
from .encryption import (
    PasswordEncryption,
    get_encryption,
    encrypt_password,
    decrypt_password,
    is_encrypted,
    reset_encryption_instance,
)

__all__ = [
    # UUID Generation
    "generate_uuid_v7",
    "generate_uuid_v4",
    "extract_timestamp_from_uuid_v7",
    "is_valid_uuid",
    "is_uuid_v7",
    "is_uuid_v4",
    "generate_short_id",
    "generate_tenant_slug",
    "normalize_uuid",
    "uuid_to_base64",
    "base64_to_uuid",
    "UUIDGenerator",
    "default_generator",
    "generate",
    "generate_id",
    # Timezone Utilities
    "utc_now",
    "utc_timestamp",
    "utc_timestamp_ms",
    "ensure_utc",
    "to_utc_string",
    "from_utc_string",
    "from_timestamp",
    "from_timestamp_ms",
    "to_timestamp",
    "to_timestamp_ms",
    "age_in_seconds",
    "age_in_minutes",
    "age_in_hours",
    "age_in_days",
    "is_future",
    "is_past",
    "time_until",
    "time_since",
    "start_of_day",
    "end_of_day",
    "days_ago",
    "days_from_now",
    "hours_ago",
    "hours_from_now",
    "format_duration",
    "calculate_duration_ms",
    "TimezoneHelper",
    "default_helper",
    "now",
    "current_time",
    "Timer",
    # Password Encryption
    "PasswordEncryption",
    "get_encryption",
    "encrypt_password",
    "decrypt_password",
    "is_encrypted",
    "reset_encryption_instance",
]