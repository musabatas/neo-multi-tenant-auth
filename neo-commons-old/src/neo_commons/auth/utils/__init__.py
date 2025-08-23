"""
Auth utilities module exports.

This module provides utility functions and classes for authentication services:
- Cache key management with service namespacing
- Rate limiting with sliding window algorithm
- Permission scanning for endpoint discovery
"""

from .cache_keys import (
    CacheKeyProviderProtocol,
    DefaultCacheKeyProvider,
    AdminCacheKeyProvider,
    TenantCacheKeyProvider,
    create_cache_key_provider,
    create_admin_cache_key_provider,
    create_tenant_cache_key_provider,
)

from .rate_limiting import (
    RateLimitType,
    RateLimit,
    RateLimitState,
    RateLimiterProtocol,
    SlidingWindowRateLimiter,
    AuthRateLimitManager,
    create_auth_rate_limiter,
)

from .scanner import (
    EndpointPermissionScanner,
    create_permission_scanner,
)


__all__ = [
    # Cache key management
    "CacheKeyProviderProtocol",
    "DefaultCacheKeyProvider",
    "AdminCacheKeyProvider",
    "TenantCacheKeyProvider",
    "create_cache_key_provider",
    "create_admin_cache_key_provider",
    "create_tenant_cache_key_provider",
    
    # Rate limiting
    "RateLimitType",
    "RateLimit",
    "RateLimitState",
    "RateLimiterProtocol",
    "SlidingWindowRateLimiter",
    "AuthRateLimitManager",
    "create_auth_rate_limiter",
    
    # Permission scanning
    "EndpointPermissionScanner",
    "create_permission_scanner",
]