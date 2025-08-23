"""
Cache Implementation Modules

Concrete implementations of cache protocols for the NeoMultiTenant platform.
"""

from .tenant_aware_cache import TenantAwareCacheService
# from .cache_adapter import CacheServiceAdapter  # Disabled due to protocol dependency

__all__ = ["TenantAwareCacheService"]