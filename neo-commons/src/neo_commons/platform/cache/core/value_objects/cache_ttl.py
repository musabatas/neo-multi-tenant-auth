"""Cache TTL value object.

ONLY TTL handling - time-to-live value object with timezone-aware
expiration and smart TTL extension policies.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass(frozen=True)  
class CacheTTL:
    """Cache TTL (Time To Live) value object.
    
    Time-to-live value object with support for:
    - Never-expire and instant-expire values
    - Timezone-aware expiration
    - Smart TTL extension policies
    - Relative and absolute expiration
    """
    
    seconds: int
    
    # Special TTL values
    NEVER_EXPIRE = -1
    INSTANT_EXPIRE = 0
    
    # Common TTL durations (in seconds)
    ONE_MINUTE = 60
    FIVE_MINUTES = 300
    TEN_MINUTES = 600
    THIRTY_MINUTES = 1800
    ONE_HOUR = 3600
    SIX_HOURS = 21600
    TWELVE_HOURS = 43200
    ONE_DAY = 86400
    ONE_WEEK = 604800
    
    def __post_init__(self):
        """Validate TTL value."""
        if self.seconds < self.NEVER_EXPIRE:
            raise ValueError(f"TTL cannot be less than {self.NEVER_EXPIRE}")
    
    @classmethod
    def never_expire(cls) -> "CacheTTL":
        """Create TTL that never expires."""
        return cls(cls.NEVER_EXPIRE)
    
    @classmethod
    def instant_expire(cls) -> "CacheTTL":
        """Create TTL that expires immediately."""
        return cls(cls.INSTANT_EXPIRE)
    
    @classmethod
    def minutes(cls, minutes: int) -> "CacheTTL":
        """Create TTL from minutes."""
        if minutes <= 0:
            raise ValueError("Minutes must be positive")
        return cls(minutes * 60)
    
    @classmethod
    def hours(cls, hours: int) -> "CacheTTL":
        """Create TTL from hours."""
        if hours <= 0:
            raise ValueError("Hours must be positive")
        return cls(hours * 3600)
    
    @classmethod
    def days(cls, days: int) -> "CacheTTL":
        """Create TTL from days."""
        if days <= 0:
            raise ValueError("Days must be positive")
        return cls(days * 86400)
    
    @classmethod
    def from_timedelta(cls, delta: timedelta) -> "CacheTTL":
        """Create TTL from timedelta."""
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            raise ValueError("Timedelta must be positive")
        return cls(total_seconds)
    
    def is_never_expire(self) -> bool:
        """Check if TTL never expires."""
        return self.seconds == self.NEVER_EXPIRE
    
    def is_instant_expire(self) -> bool:
        """Check if TTL expires instantly."""
        return self.seconds == self.INSTANT_EXPIRE
    
    def is_expired(self, created_at: datetime) -> bool:
        """Check if TTL has expired relative to creation time."""
        if self.is_never_expire():
            return False
        
        if self.is_instant_expire():
            return True
        
        expiry_time = created_at + timedelta(seconds=self.seconds)
        return datetime.utcnow() > expiry_time
    
    def get_expiry_time(self, created_at: datetime) -> Optional[datetime]:
        """Get absolute expiry time, None if never expires."""
        if self.is_never_expire():
            return None
        
        return created_at + timedelta(seconds=self.seconds)
    
    def seconds_until_expiry(self, created_at: datetime) -> Optional[int]:
        """Get seconds until expiry, None if never expires."""
        if self.is_never_expire():
            return None
        
        expiry_time = self.get_expiry_time(created_at)
        if expiry_time is None:
            return None
        
        remaining = expiry_time - datetime.utcnow()
        return max(0, int(remaining.total_seconds()))
    
    def extend(self, additional_seconds: int) -> "CacheTTL":
        """Create new TTL extended by additional seconds."""
        if self.is_never_expire():
            return self  # Cannot extend never-expire
        
        if additional_seconds <= 0:
            raise ValueError("Additional seconds must be positive")
        
        return CacheTTL(self.seconds + additional_seconds)
    
    def multiply(self, factor: float) -> "CacheTTL":
        """Create new TTL multiplied by factor."""
        if self.is_never_expire():
            return self  # Cannot multiply never-expire
        
        if factor <= 0:
            raise ValueError("Factor must be positive")
        
        new_seconds = int(self.seconds * factor)
        return CacheTTL(new_seconds)
    
    def to_timedelta(self) -> Optional[timedelta]:
        """Convert to timedelta, None if never expires."""
        if self.is_never_expire():
            return None
        return timedelta(seconds=self.seconds)
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        if self.is_never_expire():
            return "never expires"
        
        if self.is_instant_expire():
            return "expires instantly"
        
        if self.seconds < 60:
            return f"{self.seconds}s"
        elif self.seconds < 3600:
            return f"{self.seconds // 60}m"
        elif self.seconds < 86400:
            return f"{self.seconds // 3600}h"
        else:
            return f"{self.seconds // 86400}d"