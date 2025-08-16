"""
DateTime utilities for consistent timezone handling.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
from zoneinfo import ZoneInfo


def utc_now() -> datetime:
    """
    Get the current UTC time with timezone awareness.
    
    Returns:
        datetime: Current UTC time with timezone info
    """
    return datetime.now(timezone.utc)


def utc_now_naive() -> datetime:
    """
    Get the current UTC time without timezone info (naive).
    
    Returns:
        datetime: Current UTC time without timezone info
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_utc(dt: datetime, source_tz: Optional[str] = None) -> datetime:
    """
    Convert a datetime to UTC timezone.
    
    Args:
        dt: Datetime to convert
        source_tz: Source timezone name (e.g., 'America/New_York'). 
                   If None and dt is naive, assumes UTC.
    
    Returns:
        datetime: Datetime in UTC timezone
    """
    if dt.tzinfo is None:
        # Naive datetime
        if source_tz:
            # Localize to source timezone first
            source_zone = ZoneInfo(source_tz)
            dt = dt.replace(tzinfo=source_zone)
        else:
            # Assume it's already UTC
            dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC if not already
    if dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    
    return dt


def from_utc(dt: datetime, target_tz: str) -> datetime:
    """
    Convert a UTC datetime to a specific timezone.
    
    Args:
        dt: UTC datetime to convert
        target_tz: Target timezone name (e.g., 'Europe/London')
    
    Returns:
        datetime: Datetime in target timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    target_zone = ZoneInfo(target_tz)
    return dt.astimezone(target_zone)


def timestamp_to_utc(timestamp: Union[int, float]) -> datetime:
    """
    Convert Unix timestamp to UTC datetime.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
    
    Returns:
        datetime: UTC datetime with timezone info
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def utc_to_timestamp(dt: datetime) -> float:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: Datetime to convert
    
    Returns:
        float: Unix timestamp
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.timestamp()


def is_expired(expiry_time: datetime, buffer_seconds: int = 0) -> bool:
    """
    Check if a datetime has expired (is in the past).
    
    Args:
        expiry_time: The expiry datetime to check
        buffer_seconds: Optional buffer in seconds before actual expiry
    
    Returns:
        bool: True if expired, False otherwise
    """
    if expiry_time.tzinfo is None:
        # Assume naive datetime is UTC
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
    
    current_time = utc_now()
    
    if buffer_seconds > 0:
        expiry_time = expiry_time - timedelta(seconds=buffer_seconds)
    
    return current_time >= expiry_time


def time_until_expiry(expiry_time: datetime) -> timedelta:
    """
    Calculate time remaining until expiry.
    
    Args:
        expiry_time: The expiry datetime
    
    Returns:
        timedelta: Time remaining (negative if already expired)
    """
    if expiry_time.tzinfo is None:
        # Assume naive datetime is UTC
        expiry_time = expiry_time.replace(tzinfo=timezone.utc)
    
    return expiry_time - utc_now()


def format_utc(dt: Optional[datetime] = None, format_string: str = "%Y-%m-%d %H:%M:%S UTC") -> str:
    """
    Format a datetime as UTC string.
    
    Args:
        dt: Datetime to format (defaults to current UTC time)
        format_string: strftime format string
    
    Returns:
        str: Formatted datetime string
    """
    if dt is None:
        dt = utc_now()
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        # Convert to UTC
        dt = dt.astimezone(timezone.utc)
    
    return dt.strftime(format_string)


def parse_utc(date_string: str, format_string: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse a string into UTC datetime.
    
    Args:
        date_string: Date string to parse
        format_string: strptime format string
    
    Returns:
        datetime: UTC datetime with timezone info
    """
    # Parse as naive datetime
    dt = datetime.strptime(date_string, format_string)
    # Add UTC timezone
    return dt.replace(tzinfo=timezone.utc)


def add_timezone(dt: datetime, tz: Optional[str] = None) -> datetime:
    """
    Add timezone info to a naive datetime.
    
    Args:
        dt: Naive datetime
        tz: Timezone name (defaults to UTC)
    
    Returns:
        datetime: Timezone-aware datetime
    """
    if dt.tzinfo is not None:
        return dt  # Already has timezone
    
    if tz:
        zone = ZoneInfo(tz)
        return dt.replace(tzinfo=zone)
    else:
        return dt.replace(tzinfo=timezone.utc)


def remove_timezone(dt: datetime) -> datetime:
    """
    Remove timezone info from a datetime (make it naive).
    
    Args:
        dt: Timezone-aware datetime
    
    Returns:
        datetime: Naive datetime
    """
    return dt.replace(tzinfo=None)


def format_iso8601(dt: Optional[datetime]) -> Optional[str]:
    """
    Format datetime to ISO 8601 string with consistent UTC notation.
    
    Args:
        dt: Datetime to format
        
    Returns:
        ISO 8601 formatted string with consistent +00:00 for UTC
    """
    if dt is None:
        return None
    
    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to UTC if in different timezone
    if dt.tzinfo != timezone.utc:
        dt = dt.astimezone(timezone.utc)
    
    # Return ISO format - Python's isoformat() automatically uses +00:00 for UTC
    return dt.isoformat()


# Convenience constants
UTC = timezone.utc
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)