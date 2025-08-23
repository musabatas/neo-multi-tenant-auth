"""
Permission Management Module for Neo-Commons

Provides comprehensive permission management capabilities including:
- Permission checking with wildcard support
- Multi-level caching with tenant isolation  
- Registry-based permission definitions
- Data source abstraction with fallback strategies
- Protocol-based dependency injection

Key Features:
- Sub-millisecond permission checks with intelligent caching
- Tenant-aware permission contexts
- Wildcard pattern matching (users:*, *:read, *:*)
- Dangerous permission flagging with MFA/approval requirements
- Platform and tenant-scoped permission hierarchies
- Composite data sources with fallback mechanisms
"""

# Core permission checking
from .checker import DefaultPermissionChecker

# Permission caching
from .cache import DefaultPermissionCache

# Permission registry and definitions
from .registry import (
    DefaultPermissionRegistry,
    PermissionDefinition,
    PLATFORM_PERMISSIONS,
    TENANT_PERMISSIONS,
    PERMISSION_GROUPS,
    get_permission_registry,
)

# Wildcard pattern matching
from .matcher import (
    DefaultWildcardMatcher,
    create_wildcard_matcher,
)

# Data source implementations
from .data_source import (
    DatabasePermissionDataSource,
    CompositePermissionDataSource,
    CachedPermissionDataSource,
)

# Protocol definitions
from .protocols import (
    PermissionValidatorProtocol,
    PermissionRegistryProtocol,
    PermissionDecoratorProtocol,
    PermissionCheckerProtocol,
    PermissionCacheProtocol,
    PermissionDataSourceProtocol,
    WildcardMatcherProtocol,
)


# Factory functions for dependency injection
def create_permission_checker(
    data_source=None,
    cache_service=None,
    matcher=None,
    config=None
) -> DefaultPermissionChecker:
    """
    Create a permission checker with default implementations.
    
    Args:
        data_source: Optional permission data source
        cache_service: Optional cache service
        matcher: Optional wildcard matcher
        config: Optional configuration
        
    Returns:
        Configured DefaultPermissionChecker instance
    """
    if matcher is None:
        matcher = create_wildcard_matcher()
    
    if cache_service and data_source:
        # Wrap data source with caching
        cached_data_source = CachedPermissionDataSource(
            wrapped_source=data_source,
            cache_service=cache_service,
            config=config
        )
        return DefaultPermissionChecker(
            data_source=cached_data_source,
            matcher=matcher,
            config=config
        )
    
    return DefaultPermissionChecker(
        data_source=data_source,
        matcher=matcher,
        config=config
    )


def create_permission_cache(
    cache_service,
    cache_key_provider=None,
    config=None
) -> DefaultPermissionCache:
    """
    Create a permission cache with configuration.
    
    Args:
        cache_service: Cache service implementation
        cache_key_provider: Optional cache key provider
        config: Optional configuration
        
    Returns:
        Configured DefaultPermissionCache instance
    """
    return DefaultPermissionCache(
        cache_service=cache_service,
        cache_key_provider=cache_key_provider,
        config=config
    )


def create_composite_data_source(
    primary_source,
    fallback_sources=None,
    config=None
) -> CompositePermissionDataSource:
    """
    Create a composite data source with fallback strategy.
    
    Args:
        primary_source: Primary data source
        fallback_sources: Optional list of fallback sources
        config: Optional configuration
        
    Returns:
        Configured CompositePermissionDataSource instance
    """
    return CompositePermissionDataSource(
        primary_source=primary_source,
        fallback_sources=fallback_sources,
        config=config
    )




__all__ = [
    # Core implementations
    "DefaultPermissionChecker",
    "DefaultPermissionCache",
    "DefaultPermissionRegistry",
    "DefaultWildcardMatcher",
    
    # Data sources
    "DatabasePermissionDataSource",
    "CompositePermissionDataSource", 
    "CachedPermissionDataSource",
    
    # Registry and definitions
    "PermissionDefinition",
    "PLATFORM_PERMISSIONS",
    "TENANT_PERMISSIONS", 
    "PERMISSION_GROUPS",
    "get_permission_registry",
    
    # Protocols
    "PermissionValidatorProtocol",
    "PermissionRegistryProtocol",
    "PermissionDecoratorProtocol", 
    "PermissionCheckerProtocol",
    "PermissionCacheProtocol",
    "PermissionDataSourceProtocol",
    "WildcardMatcherProtocol",
    
    # Factory functions
    "create_permission_checker",
    "create_permission_cache",
    "create_wildcard_matcher",
    "create_composite_data_source",
]