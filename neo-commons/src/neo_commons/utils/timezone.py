"""Timezone utilities for neo-commons.

Provides consistent timezone handling across the entire platform,
ensuring all timestamps are UTC-aware and properly formatted.
"""

from datetime import datetime, timezone, date, time
from typing import Optional, Union
import time as time_module


def utc_now() -> datetime:
    """
    Get current UTC datetime with timezone awareness.
    
    Replacement for datetime.now(timezone.utc) to ensure consistency
    and provide a single source of truth for current timestamps.
    
    Returns:
        Current UTC datetime with timezone info
    """
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """
    Get current UTC timestamp as float seconds.
    
    Useful for performance measurements and API responses.
    
    Returns:
        Current timestamp in seconds since epoch
    """
    return time_module.time()


def utc_timestamp_ms() -> int:
    """
    Get current UTC timestamp in milliseconds.
    
    Useful for UUIDv7 generation and high-precision timing.
    
    Returns:
        Current timestamp in milliseconds since epoch
    """
    return int(time_module.time() * 1000)


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure datetime has UTC timezone.
    
    If datetime is naive (no timezone), assumes it's UTC and adds timezone info.
    If datetime has timezone, converts to UTC.
    
    Args:
        dt: Datetime to process
        
    Returns:
        UTC datetime with timezone info
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        return dt.astimezone(timezone.utc)
    return dt


def to_utc_string(dt: datetime) -> str:
    """
    Convert datetime to UTC ISO format string.
    
    Ensures consistent string representation across the platform.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        ISO format UTC string (e.g., "2024-01-15T10:30:45.123456Z")
    """
    utc_dt = ensure_utc(dt)
    return utc_dt.isoformat().replace('+00:00', 'Z')


def from_utc_string(iso_string: str) -> datetime:
    """
    Parse UTC ISO format string to datetime.
    
    Handles various ISO formats and ensures UTC timezone.
    
    Args:
        iso_string: ISO format string
        
    Returns:
        UTC datetime with timezone info
        
    Raises:
        ValueError: If string format is invalid
    """
    try:
        # Handle 'Z' suffix
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'
        
        # Parse ISO format
        dt = datetime.fromisoformat(iso_string)
        return ensure_utc(dt)
        
    except ValueError as e:
        raise ValueError(f"Invalid ISO datetime format: {iso_string}") from e


def from_timestamp(timestamp: float) -> datetime:
    """
    Convert timestamp to UTC datetime.
    
    Args:
        timestamp: Unix timestamp in seconds
        
    Returns:
        UTC datetime with timezone info
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def from_timestamp_ms(timestamp_ms: int) -> datetime:
    """
    Convert millisecond timestamp to UTC datetime.
    
    Args:
        timestamp_ms: Unix timestamp in milliseconds
        
    Returns:
        UTC datetime with timezone info
    """
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc)


def to_timestamp(dt: datetime) -> float:
    """
    Convert datetime to Unix timestamp.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Unix timestamp in seconds
    """
    return ensure_utc(dt).timestamp()


def to_timestamp_ms(dt: datetime) -> int:
    """
    Convert datetime to millisecond timestamp.
    
    Args:
        dt: Datetime to convert
        
    Returns:
        Unix timestamp in milliseconds
    """
    return int(to_timestamp(dt) * 1000)


def age_in_seconds(dt: datetime) -> float:
    """
    Calculate age of datetime in seconds from now.
    
    Args:
        dt: Datetime to calculate age for
        
    Returns:
        Age in seconds (positive for past dates)
    """
    now = utc_now()
    utc_dt = ensure_utc(dt)
    return (now - utc_dt).total_seconds()


def age_in_minutes(dt: datetime) -> float:
    """
    Calculate age of datetime in minutes from now.
    
    Args:
        dt: Datetime to calculate age for
        
    Returns:
        Age in minutes (positive for past dates)
    """
    return age_in_seconds(dt) / 60.0


def age_in_hours(dt: datetime) -> float:
    """
    Calculate age of datetime in hours from now.
    
    Args:
        dt: Datetime to calculate age for
        
    Returns:
        Age in hours (positive for past dates)
    """
    return age_in_seconds(dt) / 3600.0


def age_in_days(dt: datetime) -> float:
    """
    Calculate age of datetime in days from now.
    
    Args:
        dt: Datetime to calculate age for
        
    Returns:
        Age in days (positive for past dates)
    """
    return age_in_seconds(dt) / 86400.0


def is_future(dt: datetime) -> bool:
    """
    Check if datetime is in the future.
    
    Args:
        dt: Datetime to check
        
    Returns:
        True if datetime is in the future
    """
    return ensure_utc(dt) > utc_now()


def is_past(dt: datetime) -> bool:
    """
    Check if datetime is in the past.
    
    Args:
        dt: Datetime to check
        
    Returns:
        True if datetime is in the past
    """
    return ensure_utc(dt) < utc_now()


def time_until(dt: datetime) -> float:
    """
    Calculate seconds until datetime.
    
    Args:
        dt: Target datetime
        
    Returns:
        Seconds until datetime (negative if in past)
    """
    return -age_in_seconds(dt)


def time_since(dt: datetime) -> float:
    """
    Calculate seconds since datetime.
    
    Args:
        dt: Source datetime
        
    Returns:
        Seconds since datetime (negative if in future)
    """
    return age_in_seconds(dt)


def start_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get start of day (00:00:00) for given datetime.
    
    Args:
        dt: Datetime to process (defaults to now)
        
    Returns:
        Start of day as UTC datetime
    """
    if dt is None:
        dt = utc_now()
    
    utc_dt = ensure_utc(dt)
    return utc_dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: Optional[datetime] = None) -> datetime:
    """
    Get end of day (23:59:59.999999) for given datetime.
    
    Args:
        dt: Datetime to process (defaults to now)
        
    Returns:
        End of day as UTC datetime
    """
    if dt is None:
        dt = utc_now()
    
    utc_dt = ensure_utc(dt)
    return utc_dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def days_ago(days: int) -> datetime:
    """
    Get datetime N days ago from now.
    
    Args:
        days: Number of days in the past
        
    Returns:
        UTC datetime N days ago
    """
    from datetime import timedelta
    return utc_now() - timedelta(days=days)


def days_from_now(days: int) -> datetime:
    """
    Get datetime N days from now.
    
    Args:
        days: Number of days in the future
        
    Returns:
        UTC datetime N days from now
    """
    from datetime import timedelta
    return utc_now() + timedelta(days=days)


def hours_ago(hours: int) -> datetime:
    """
    Get datetime N hours ago from now.
    
    Args:
        hours: Number of hours in the past
        
    Returns:
        UTC datetime N hours ago
    """
    from datetime import timedelta
    return utc_now() - timedelta(hours=hours)


def hours_from_now(hours: int) -> datetime:
    """
    Get datetime N hours from now.
    
    Args:
        hours: Number of hours in the future
        
    Returns:
        UTC datetime N hours from now
    """
    from datetime import timedelta
    return utc_now() + timedelta(hours=hours)


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def calculate_duration_ms(start_time: datetime, end_time: Optional[datetime] = None) -> int:
    """
    Calculate duration between two datetimes in milliseconds.
    
    Useful for performance tracking and metrics.
    
    Args:
        start_time: Start datetime
        end_time: End datetime (defaults to now)
        
    Returns:
        Duration in milliseconds
    """
    if end_time is None:
        end_time = utc_now()
    
    start_utc = ensure_utc(start_time)
    end_utc = ensure_utc(end_time)
    
    duration = end_utc - start_utc
    return int(duration.total_seconds() * 1000)


class TimezoneHelper:
    """Timezone helper with configurable defaults."""
    
    def __init__(self, default_timezone: timezone = timezone.utc):
        """
        Initialize timezone helper.
        
        Args:
            default_timezone: Default timezone to use
        """
        self.default_timezone = default_timezone
    
    def now(self) -> datetime:
        """Get current datetime in default timezone."""
        if self.default_timezone == timezone.utc:
            return utc_now()
        else:
            return datetime.now(self.default_timezone)
    
    def ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime has default timezone."""
        if self.default_timezone == timezone.utc:
            return ensure_utc(dt)
        elif dt.tzinfo is None:
            return dt.replace(tzinfo=self.default_timezone)
        else:
            return dt.astimezone(self.default_timezone)


# Default helper instance (UTC)
default_helper = TimezoneHelper(timezone.utc)

# Convenience functions using default helper  
now = default_helper.now
current_time = utc_now  # Alias for clarity

# Performance timing helpers
class Timer:
    """Simple timer for performance measurements."""
    
    def __init__(self):
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def start(self) -> None:
        """Start the timer."""
        self.start_time = utc_now()
        self.end_time = None
    
    def stop(self) -> int:
        """
        Stop the timer and return duration in milliseconds.
        
        Returns:
            Duration in milliseconds since start
        """
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        self.end_time = utc_now()
        return calculate_duration_ms(self.start_time, self.end_time)
    
    def elapsed_ms(self) -> int:
        """
        Get elapsed time in milliseconds without stopping.
        
        Returns:
            Elapsed time in milliseconds since start
        """
        if self.start_time is None:
            raise ValueError("Timer not started")
        
        return calculate_duration_ms(self.start_time)
    
    def elapsed_seconds(self) -> float:
        """
        Get elapsed time in seconds without stopping.
        
        Returns:
            Elapsed time in seconds since start
        """
        return self.elapsed_ms() / 1000.0