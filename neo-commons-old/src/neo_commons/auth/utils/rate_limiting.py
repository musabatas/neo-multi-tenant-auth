"""
Neo-Commons Rate Limiting Module

Standardized rate limiting implementation for authentication services with:
- Session-based rate limiting for authenticated users
- IP-based rate limiting for anonymous/guest users  
- Sliding window rate limiting for API endpoints
- Configurable limits and time windows
- Redis-backed state management with automatic expiration
- Protocol-based design for service integration
"""

from typing import Dict, Any, Optional, Protocol, runtime_checkable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from loguru import logger

from ..core import (
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    SessionError,
    RateLimitError,
)


class RateLimitType(Enum):
    """Rate limit types for different scenarios"""
    SESSION = "session"           # Per-session limits (guest sessions)
    USER = "user"                 # Per-user limits (authenticated users)
    IP = "ip"                     # Per-IP limits (anonymous requests)
    ENDPOINT = "endpoint"         # Per-endpoint limits (API throttling)
    TENANT = "tenant"             # Per-tenant limits (multi-tenant quotas)


@dataclass
class RateLimit:
    """Rate limit configuration"""
    limit: int                    # Maximum requests
    window_seconds: int           # Time window in seconds
    limit_type: RateLimitType     # Type of rate limiting
    burst_limit: Optional[int] = None    # Allow burst requests
    
    def __post_init__(self):
        if self.burst_limit and self.burst_limit < self.limit:
            raise ValueError("Burst limit cannot be less than regular limit")


@dataclass
class RateLimitState:
    """Current rate limit state"""
    requests_made: int            # Requests made in current window
    window_start: datetime        # Start of current window
    last_request: datetime        # Last request timestamp
    requests_remaining: int       # Requests remaining in window
    reset_time: datetime          # When the window resets
    is_exceeded: bool             # Whether limit is exceeded


@runtime_checkable
class RateLimiterProtocol(Protocol):
    """Protocol for rate limiting implementations"""
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        rate_limit: RateLimit,
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Check if identifier is within rate limits"""
        ...
    
    async def increment_usage(
        self, 
        identifier: str, 
        rate_limit: RateLimit,
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Increment usage and return new state"""
        ...
    
    async def reset_limit(
        self, 
        identifier: str, 
        rate_limit: RateLimit,
        tenant_id: Optional[str] = None
    ) -> bool:
        """Reset rate limit for identifier"""
        ...


def utc_now() -> datetime:
    """Get current UTC time - utility function."""
    return datetime.utcnow()


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter with Redis backing.
    
    Provides accurate rate limiting using a sliding time window approach
    with automatic cleanup and configurable burst handling.
    """
    
    def __init__(self, cache):  # TenantAwareCacheProtocol - avoiding import
        """
        Initialize rate limiter.
        
        Args:
            cache: Cache service for storing rate limit state
        """
        self.cache = cache
    
    async def check_rate_limit(
        self, 
        identifier: str, 
        rate_limit: RateLimit,
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """
        Check rate limit status without incrementing.
        
        Args:
            identifier: Unique identifier (user_id, session_id, ip, etc.)
            rate_limit: Rate limit configuration
            tenant_id: Optional tenant context
            
        Returns:
            Current rate limit state
        """
        cache_key = self._build_cache_key(identifier, rate_limit.limit_type)
        current_time = utc_now()
        
        # Get current state from cache
        state_data = await self.cache.get(cache_key, tenant_id=tenant_id)
        
        if not state_data:
            # No previous state - within limits
            return RateLimitState(
                requests_made=0,
                window_start=current_time,
                last_request=current_time,
                requests_remaining=rate_limit.limit,
                reset_time=current_time + timedelta(seconds=rate_limit.window_seconds),
                is_exceeded=False
            )
        
        # Parse existing state with robust timezone handling
        def parse_datetime_safe(dt_string: str) -> datetime:
            """Safely parse datetime string with proper timezone handling."""
            try:
                # Handle Z suffix (UTC) - Python 3.11+ supports this natively
                if dt_string.endswith('Z'):
                    dt_string = dt_string[:-1] + '+00:00'
                return datetime.fromisoformat(dt_string)
            except ValueError:
                # Fallback for malformed timestamps - assume UTC
                logger.warning(f"Invalid datetime format, using current time: {dt_string}")
                return utc_now()
        
        window_start = parse_datetime_safe(state_data["window_start"])
        last_request = parse_datetime_safe(state_data["last_request"])
        
        # Check if window has expired
        if current_time >= window_start + timedelta(seconds=rate_limit.window_seconds):
            # Window expired - reset
            return RateLimitState(
                requests_made=0,
                window_start=current_time,
                last_request=current_time,
                requests_remaining=rate_limit.limit,
                reset_time=current_time + timedelta(seconds=rate_limit.window_seconds),
                is_exceeded=False
            )
        
        # Window is active - check current usage
        requests_made = state_data["requests_made"]
        effective_limit = rate_limit.burst_limit or rate_limit.limit
        requests_remaining = max(0, effective_limit - requests_made)
        is_exceeded = requests_made >= effective_limit
        
        return RateLimitState(
            requests_made=requests_made,
            window_start=window_start,
            last_request=last_request,
            requests_remaining=requests_remaining,
            reset_time=window_start + timedelta(seconds=rate_limit.window_seconds),
            is_exceeded=is_exceeded
        )
    
    async def increment_usage(
        self, 
        identifier: str, 
        rate_limit: RateLimit,
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """
        Increment usage and check limits.
        
        Args:
            identifier: Unique identifier
            rate_limit: Rate limit configuration
            tenant_id: Optional tenant context
            
        Returns:
            Updated rate limit state
            
        Raises:
            RateLimitError: If rate limit is exceeded
        """
        current_state = await self.check_rate_limit(identifier, rate_limit, tenant_id)
        
        # Check if already exceeded
        if current_state.is_exceeded:
            raise RateLimitError(
                f"Rate limit exceeded for {rate_limit.limit_type.value}. "
                f"Resets at {current_state.reset_time.isoformat()}"
            )
        
        # Increment usage
        current_time = utc_now()
        new_requests_made = current_state.requests_made + 1
        effective_limit = rate_limit.burst_limit or rate_limit.limit
        
        # Check if this increment would exceed limit
        if new_requests_made > effective_limit:
            raise RateLimitError(
                f"Rate limit would be exceeded for {rate_limit.limit_type.value}. "
                f"Resets at {current_state.reset_time.isoformat()}"
            )
        
        # Update state in cache
        new_state_data = {
            "requests_made": new_requests_made,
            "window_start": current_state.window_start.isoformat(),
            "last_request": current_time.isoformat(),
            "limit_type": rate_limit.limit_type.value,
            "limit": rate_limit.limit,
            "window_seconds": rate_limit.window_seconds
        }
        
        cache_key = self._build_cache_key(identifier, rate_limit.limit_type)
        ttl = int((current_state.reset_time - current_time).total_seconds()) + 1
        await self.cache.set(cache_key, new_state_data, ttl=ttl, tenant_id=tenant_id)
        
        # Return updated state
        return RateLimitState(
            requests_made=new_requests_made,
            window_start=current_state.window_start,
            last_request=current_time,
            requests_remaining=max(0, effective_limit - new_requests_made),
            reset_time=current_state.reset_time,
            is_exceeded=new_requests_made >= effective_limit
        )
    
    async def reset_limit(
        self, 
        identifier: str, 
        rate_limit: RateLimit,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Reset rate limit for identifier.
        
        Args:
            identifier: Unique identifier
            rate_limit: Rate limit configuration
            tenant_id: Optional tenant context
            
        Returns:
            True if reset successful
        """
        cache_key = self._build_cache_key(identifier, rate_limit.limit_type)
        return await self.cache.delete(cache_key, tenant_id=tenant_id)
    
    def _build_cache_key(self, identifier: str, limit_type: RateLimitType) -> str:
        """Build cache key for rate limit state"""
        return f"rate_limit:{limit_type.value}:{identifier}"


class AuthRateLimitManager:
    """
    Rate limit manager for authentication services.
    
    Provides pre-configured rate limits for common authentication scenarios
    with intelligent defaults and service-specific customization.
    """
    
    # Default rate limits for authentication scenarios
    DEFAULT_LIMITS = {
        RateLimitType.SESSION: RateLimit(
            limit=1000,              # 1000 requests per session
            window_seconds=3600,     # 1 hour window
            limit_type=RateLimitType.SESSION,
            burst_limit=1200         # Allow 20% burst
        ),
        RateLimitType.USER: RateLimit(
            limit=5000,              # 5000 requests per user
            window_seconds=3600,     # 1 hour window
            limit_type=RateLimitType.USER,
            burst_limit=6000         # Allow 20% burst
        ),
        RateLimitType.IP: RateLimit(
            limit=5000,              # 5000 requests per IP
            window_seconds=86400,    # 24 hour window
            limit_type=RateLimitType.IP
        ),
        RateLimitType.ENDPOINT: RateLimit(
            limit=60,                # 60 requests per endpoint
            window_seconds=60,       # 1 minute window
            limit_type=RateLimitType.ENDPOINT
        ),
        RateLimitType.TENANT: RateLimit(
            limit=100000,            # 100k requests per tenant
            window_seconds=86400,    # 24 hour window
            limit_type=RateLimitType.TENANT
        )
    }
    
    def __init__(
        self, 
        cache,  # TenantAwareCacheProtocol - avoiding import
        custom_limits: Optional[Dict[RateLimitType, RateLimit]] = None
    ):
        """
        Initialize rate limit manager.
        
        Args:
            cache: Cache service for rate limit state
            custom_limits: Override default limits
        """
        self.limiter = SlidingWindowRateLimiter(cache)
        self.limits = {**self.DEFAULT_LIMITS}
        
        if custom_limits:
            self.limits.update(custom_limits)
    
    async def check_session_limit(
        self, 
        session_id: str, 
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Check session-based rate limit"""
        return await self.limiter.check_rate_limit(
            session_id, 
            self.limits[RateLimitType.SESSION],
            tenant_id
        )
    
    async def check_user_limit(
        self, 
        user_id: str, 
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Check user-based rate limit"""
        return await self.limiter.check_rate_limit(
            user_id, 
            self.limits[RateLimitType.USER],
            tenant_id
        )
    
    async def check_ip_limit(
        self, 
        ip_address: str, 
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Check IP-based rate limit"""
        return await self.limiter.check_rate_limit(
            ip_address, 
            self.limits[RateLimitType.IP],
            tenant_id
        )
    
    async def check_endpoint_limit(
        self, 
        endpoint: str, 
        identifier: str,
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Check endpoint-specific rate limit"""
        combined_id = f"{endpoint}:{identifier}"
        return await self.limiter.check_rate_limit(
            combined_id, 
            self.limits[RateLimitType.ENDPOINT],
            tenant_id
        )
    
    async def check_tenant_limit(
        self, 
        tenant_id: str
    ) -> RateLimitState:
        """Check tenant-wide rate limit"""
        return await self.limiter.check_rate_limit(
            tenant_id, 
            self.limits[RateLimitType.TENANT],
            tenant_id
        )
    
    async def enforce_session_limit(
        self, 
        session_id: str, 
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Enforce session rate limit (increment and check)"""
        return await self.limiter.increment_usage(
            session_id, 
            self.limits[RateLimitType.SESSION],
            tenant_id
        )
    
    async def enforce_user_limit(
        self, 
        user_id: str, 
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Enforce user rate limit (increment and check)"""
        return await self.limiter.increment_usage(
            user_id, 
            self.limits[RateLimitType.USER],
            tenant_id
        )
    
    async def enforce_ip_limit(
        self, 
        ip_address: str, 
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Enforce IP rate limit (increment and check)"""
        return await self.limiter.increment_usage(
            ip_address, 
            self.limits[RateLimitType.IP],
            tenant_id
        )
    
    async def enforce_endpoint_limit(
        self, 
        endpoint: str, 
        identifier: str,
        tenant_id: Optional[str] = None
    ) -> RateLimitState:
        """Enforce endpoint rate limit (increment and check)"""
        combined_id = f"{endpoint}:{identifier}"
        return await self.limiter.increment_usage(
            combined_id, 
            self.limits[RateLimitType.ENDPOINT],
            tenant_id
        )
    
    async def enforce_tenant_limit(
        self, 
        tenant_id: str
    ) -> RateLimitState:
        """Enforce tenant rate limit (increment and check)"""
        return await self.limiter.increment_usage(
            tenant_id, 
            self.limits[RateLimitType.TENANT],
            tenant_id
        )
    
    def get_limit_config(self, limit_type: RateLimitType) -> RateLimit:
        """Get rate limit configuration for type"""
        return self.limits[limit_type]
    
    def update_limit(self, limit_type: RateLimitType, rate_limit: RateLimit) -> None:
        """Update rate limit configuration"""
        self.limits[limit_type] = rate_limit


# Factory function for creating rate limit manager
def create_auth_rate_limiter(
    cache,  # TenantAwareCacheProtocol - avoiding import
    custom_limits: Optional[Dict[RateLimitType, RateLimit]] = None
) -> AuthRateLimitManager:
    """
    Create an authentication rate limit manager.
    
    Args:
        cache: Cache service for rate limit state
        custom_limits: Optional custom rate limits
        
    Returns:
        Configured AuthRateLimitManager instance
    """
    return AuthRateLimitManager(cache, custom_limits)


__all__ = [
    "RateLimitType",
    "RateLimit",
    "RateLimitState",
    "RateLimiterProtocol",
    "SlidingWindowRateLimiter",
    "AuthRateLimitManager",
    "create_auth_rate_limiter",
]