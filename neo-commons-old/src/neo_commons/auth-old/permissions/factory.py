"""
Permission Cache Manager Factory for Neo-Commons

Factory functions for creating permission cache manager instances with
proper dependency injection and configuration.
"""
from typing import Optional

from ...cache.protocols import TenantAwareCacheProtocol
from .protocols import PermissionDataSourceProtocol, WildcardMatcherProtocol
from .cache_manager import DefaultPermissionCacheManager
from .matcher import DefaultWildcardMatcher


def create_permission_cache_manager(
    cache_service: TenantAwareCacheProtocol,
    data_source: PermissionDataSourceProtocol,
    wildcard_matcher: Optional[WildcardMatcherProtocol] = None
) -> DefaultPermissionCacheManager:
    """
    Create a permission cache manager with proper dependencies.
    
    Args:
        cache_service: Cache service for storing permission data
        data_source: Data source for loading permission data
        wildcard_matcher: Optional wildcard permission matcher
        
    Returns:
        Configured DefaultPermissionCacheManager instance
    """
    if wildcard_matcher is None:
        wildcard_matcher = DefaultWildcardMatcher()
    
    return DefaultPermissionCacheManager(
        cache_service=cache_service,
        data_source=data_source,
        wildcard_matcher=wildcard_matcher
    )


def create_wildcard_permission_matcher() -> DefaultWildcardMatcher:
    """
    Create a standalone wildcard permission matcher.
    
    Returns:
        DefaultWildcardMatcher instance
    """
    return DefaultWildcardMatcher()