"""
Common utility modules.

Note: Utilities have been migrated to neo-commons package.
- datetime utilities: Import from neo_commons.utils.datetime
- uuid utilities: Import from neo_commons.utils.uuid
"""

# Re-export from neo-commons for backward compatibility
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
    EPOCH
)

from neo_commons.utils.uuid import (
    generate_uuid_v7,
    extract_timestamp_from_uuid_v7,
    is_uuid_v7,
    is_valid_uuid,
    generate_uuid,
    uuid_v7
)

# Import encryption from local wrapper (handles NeoAdminApi settings)
from .encryption import (
    PasswordEncryption,
    get_encryption,
    encrypt_password,
    decrypt_password,
    is_encrypted,
    reset_encryption_instance
)

# Import metadata from local wrapper (handles NeoAdminApi middleware)
from .metadata import (
    MetadataCollector,
    track_db_operation,
    track_cache_operation,
    get_api_metadata,
    collect_request_metadata,
    get_basic_metadata,
    get_performance_summary
)

__all__ = [
    # datetime utilities (from neo-commons)
    'utc_now',
    'utc_now_naive', 
    'to_utc',
    'from_utc',
    'timestamp_to_utc',
    'utc_to_timestamp',
    'is_expired',
    'time_until_expiry',
    'format_utc',
    'parse_utc',
    'add_timezone',
    'remove_timezone',
    'format_iso8601',
    'UTC',
    'EPOCH',
    
    # uuid utilities (from neo-commons)
    'generate_uuid_v7',
    'extract_timestamp_from_uuid_v7',
    'is_uuid_v7',
    'is_valid_uuid',
    'generate_uuid',
    'uuid_v7',
    
    # encryption utilities (local wrapper + neo-commons)
    'PasswordEncryption',
    'get_encryption',
    'encrypt_password',
    'decrypt_password',
    'is_encrypted',
    'reset_encryption_instance',
    
    # metadata utilities (local wrapper + neo-commons)
    'MetadataCollector',
    'track_db_operation',
    'track_cache_operation',
    'get_api_metadata',
    'collect_request_metadata',
    'get_basic_metadata',
    'get_performance_summary',
]