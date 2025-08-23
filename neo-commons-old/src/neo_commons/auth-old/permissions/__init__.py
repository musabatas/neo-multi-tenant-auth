"""
Permission management utilities for the NeoMultiTenant platform.

This module provides intelligent permission caching, validation, and management
patterns that can be reused across all platform services.
"""

from .cache_manager import PermissionCacheManager, DefaultPermissionCacheManager
from .protocols import PermissionCacheProtocol
from .factory import create_permission_cache_manager, create_wildcard_permission_matcher

__all__ = [
    "PermissionCacheManager",
    "DefaultPermissionCacheManager", 
    "PermissionCacheProtocol",
    "create_permission_cache_manager",
    "create_wildcard_permission_matcher"
]