"""
Cache layer utilities for the NeoMultiTenant platform.

This module provides generic cache utilities and patterns
that can be used across all platform services.
"""

from .client import CacheManager, CacheConfig
from .protocols import TenantAwareCacheProtocol, CacheManagerProtocol
from .implementations import TenantAwareCacheService, CacheServiceAdapter

__all__ = [
    "CacheManager", 
    "CacheConfig",
    "TenantAwareCacheProtocol",
    "CacheManagerProtocol", 
    "TenantAwareCacheService",
    "CacheServiceAdapter"
]