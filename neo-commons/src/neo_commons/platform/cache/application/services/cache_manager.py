"""Cache manager orchestration service.

ONLY cache orchestration - main cache service providing high-level
API for cache operations across all business features.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Optional, Dict, List
from datetime import datetime

from ...core.protocols.cache_repository import CacheRepository
from ...core.protocols.cache_serializer import CacheSerializer
from ...core.protocols.invalidation_service import InvalidationService
from ...core.protocols.distribution_service import DistributionService
from ..commands.set_cache_entry import SetCacheEntryCommand, SetCacheEntryData, SetCacheEntryResult
from ..queries.get_cache_entry import GetCacheEntryQuery, GetCacheEntryData, GetCacheEntryResult


class CacheManager:
    """Cache manager orchestration service.
    
    High-level cache service providing unified API for all cache operations:
    - Simple get/set/delete operations with intelligent defaults
    - Automatic serialization and TTL management
    - Multi-tenant namespace isolation
    - Performance monitoring and statistics
    - Error handling with graceful degradation
    - Integration with invalidation and distribution services
    
    This is the main service that business features should use for caching.
    """
    
    def __init__(
        self,
        repository: CacheRepository,
        serializer: Optional[CacheSerializer] = None,
        invalidation_service: Optional[InvalidationService] = None,
        distribution_service: Optional[DistributionService] = None
    ):
        """Initialize cache manager.
        
        Args:
            repository: Cache repository for storage
            serializer: Optional serializer for value handling
            invalidation_service: Optional invalidation service
            distribution_service: Optional distribution service
        """
        self._repository = repository
        self._serializer = serializer
        self._invalidation_service = invalidation_service
        self._distribution_service = distribution_service
        
        # Initialize commands and queries
        self._set_command = SetCacheEntryCommand(repository, serializer)
        self._get_query = GetCacheEntryQuery(repository)
    
    # Main high-level API for business features
    
    async def get(
        self,
        key: str,
        namespace: str = "default",
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Optional[Any]:
        """Get cached value.
        
        Simple high-level cache get operation.
        
        Args:
            key: Cache key
            namespace: Cache namespace (default: "default")
            tenant_id: Optional tenant isolation
            user_id: Optional user context
            request_id: Optional request tracking
            
        Returns:
            Cached value if found, None if not found or error
        """
        try:
            data = GetCacheEntryData(
                key=key,
                namespace=namespace,
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id
            )
            
            result = await self._get_query.execute(data)
            return result.value if result.found else None
            
        except Exception:
            # Graceful degradation - return None on any error
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None,
        priority: str = "medium",
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> bool:
        """Set cached value.
        
        Simple high-level cache set operation.
        
        Args:
            key: Cache key
            value: Value to cache
            namespace: Cache namespace (default: "default")
            ttl_seconds: Optional TTL in seconds
            priority: Cache priority ("low", "medium", "high", "critical")
            tenant_id: Optional tenant isolation
            user_id: Optional user context
            request_id: Optional request tracking
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            data = SetCacheEntryData(
                key=key,
                value=value,
                namespace=namespace,
                ttl_seconds=ttl_seconds,
                priority=priority,
                tenant_id=tenant_id,
                user_id=user_id,
                request_id=request_id
            )
            
            result = await self._set_command.execute(data)
            return result.success
            
        except Exception:
            # Graceful degradation - return False on any error
            return False
    
    async def delete(
        self,
        key: str,
        namespace: str = "default",
        tenant_id: Optional[str] = None
    ) -> bool:
        """Delete cached value.
        
        Args:
            key: Cache key to delete
            namespace: Cache namespace (default: "default")
            tenant_id: Optional tenant isolation
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        try:
            from ...core.value_objects.cache_key import CacheKey
            from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
            
            cache_key = CacheKey(key)
            cache_namespace = CacheNamespace(
                name=namespace,
                description=f"Cache namespace: {namespace}",
                default_ttl=None,
                max_entries=10000,
                eviction_policy=EvictionPolicy.LRU,
                tenant_id=tenant_id
            )
            
            return await self._repository.delete(cache_key, cache_namespace)
            
        except Exception:
            return False
    
    async def exists(
        self,
        key: str,
        namespace: str = "default",
        tenant_id: Optional[str] = None
    ) -> bool:
        """Check if key exists in cache.
        
        Args:
            key: Cache key to check
            namespace: Cache namespace (default: "default")
            tenant_id: Optional tenant isolation
            
        Returns:
            True if key exists and is not expired, False otherwise
        """
        try:
            from ...core.value_objects.cache_key import CacheKey
            from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
            
            cache_key = CacheKey(key)
            cache_namespace = CacheNamespace(
                name=namespace,
                description=f"Cache namespace: {namespace}",
                default_ttl=None,
                max_entries=10000,
                eviction_policy=EvictionPolicy.LRU,
                tenant_id=tenant_id
            )
            
            return await self._repository.exists(cache_key, cache_namespace)
            
        except Exception:
            return False
    
    # Convenience methods with common patterns
    
    async def get_or_set(
        self,
        key: str,
        value_factory: callable,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> Any:
        """Get cached value or set it using factory function.
        
        Common cache pattern - check cache, if miss then compute and cache.
        
        Args:
            key: Cache key
            value_factory: Function to call if cache miss (async or sync)
            namespace: Cache namespace
            ttl_seconds: Optional TTL
            tenant_id: Optional tenant isolation
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache first
        value = await self.get(key, namespace, tenant_id)
        
        if value is not None:
            return value
        
        # Cache miss - compute value
        try:
            if callable(value_factory):
                if hasattr(value_factory, '__call__') and hasattr(value_factory.__call__, '__code__'):
                    # Check if it's an async function
                    import asyncio
                    if asyncio.iscoroutinefunction(value_factory):
                        computed_value = await value_factory()
                    else:
                        computed_value = value_factory()
                else:
                    computed_value = value_factory()
            else:
                computed_value = value_factory
            
            # Cache the computed value
            await self.set(key, computed_value, namespace, ttl_seconds, tenant_id=tenant_id)
            
            return computed_value
            
        except Exception:
            # Return None if factory fails
            return None
    
    async def get_many(
        self,
        keys: List[str],
        namespace: str = "default", 
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get multiple cached values.
        
        Args:
            keys: List of cache keys
            namespace: Cache namespace
            tenant_id: Optional tenant isolation
            
        Returns:
            Dictionary mapping keys to values (missing keys omitted)
        """
        result = {}
        
        for key in keys:
            value = await self.get(key, namespace, tenant_id)
            if value is not None:
                result[key] = value
        
        return result
    
    async def set_many(
        self,
        items: Dict[str, Any],
        namespace: str = "default",
        ttl_seconds: Optional[int] = None,
        tenant_id: Optional[str] = None
    ) -> Dict[str, bool]:
        """Set multiple cached values.
        
        Args:
            items: Dictionary mapping keys to values
            namespace: Cache namespace
            ttl_seconds: Optional TTL for all items
            tenant_id: Optional tenant isolation
            
        Returns:
            Dictionary mapping keys to success status
        """
        result = {}
        
        for key, value in items.items():
            success = await self.set(key, value, namespace, ttl_seconds, tenant_id=tenant_id)
            result[key] = success
        
        return result
    
    # User and tenant specific convenience methods
    
    async def get_user_cache(
        self,
        user_id: str,
        key: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Any]:
        """Get user-specific cached value."""
        user_key = f"user:{user_id}:{key}"
        return await self.get(user_key, "users", tenant_id)
    
    async def set_user_cache(
        self,
        user_id: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = 3600,  # 1 hour default for user cache
        tenant_id: Optional[str] = None
    ) -> bool:
        """Set user-specific cached value."""
        user_key = f"user:{user_id}:{key}"
        return await self.set(user_key, value, "users", ttl_seconds, tenant_id=tenant_id)
    
    async def get_tenant_cache(
        self,
        tenant_id: str,
        key: str
    ) -> Optional[Any]:
        """Get tenant-specific cached value."""
        return await self.get(key, "tenant_data", tenant_id)
    
    async def set_tenant_cache(
        self,
        tenant_id: str,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """Set tenant-specific cached value."""
        return await self.set(key, value, "tenant_data", ttl_seconds, tenant_id)
    
    # Management and monitoring
    
    async def flush_namespace(
        self,
        namespace: str,
        tenant_id: Optional[str] = None
    ) -> int:
        """Flush all entries in namespace.
        
        Args:
            namespace: Namespace to flush
            tenant_id: Optional tenant isolation
            
        Returns:
            Number of entries deleted
        """
        try:
            from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
            
            cache_namespace = CacheNamespace(
                name=namespace,
                description=f"Cache namespace: {namespace}",
                default_ttl=None,
                max_entries=10000,
                eviction_policy=EvictionPolicy.LRU,
                tenant_id=tenant_id
            )
            
            return await self._repository.flush_namespace(cache_namespace)
            
        except Exception:
            return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            return await self._repository.get_stats()
        except Exception:
            return {"error": "Unable to retrieve stats"}
    
    async def health_check(self) -> bool:
        """Check cache health."""
        try:
            return await self._repository.ping()
        except Exception:
            return False


# Factory function for dependency injection
def create_cache_manager(
    repository: CacheRepository,
    serializer: Optional[CacheSerializer] = None,
    invalidation_service: Optional[InvalidationService] = None,
    distribution_service: Optional[DistributionService] = None
) -> CacheManager:
    """Create cache manager with dependencies."""
    return CacheManager(
        repository=repository,
        serializer=serializer, 
        invalidation_service=invalidation_service,
        distribution_service=distribution_service
    )