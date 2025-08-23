"""
Tenant-Aware Cache Service Implementation

High-performance cache service with built-in tenant isolation, comprehensive
caching patterns, and enterprise-grade features for the NeoMultiTenant platform.

Migrated from NeoAdminApi to provide shared caching infrastructure across all services.
"""

from typing import Any, Dict, List, Optional
import json
from loguru import logger

from ..protocols import TenantAwareCacheProtocol, CacheManagerProtocol


class TenantAwareCacheService:
    """
    Tenant-aware cache service implementation.
    
    Provides comprehensive caching capabilities with built-in tenant isolation,
    pattern-based operations, and enterprise-grade features.
    
    Features:
    - Automatic tenant namespace isolation
    - JSON serialization/deserialization
    - Pattern-based key operations
    - Health monitoring and statistics
    - Fallback error handling
    - Performance optimizations
    """
    
    def __init__(self, cache_manager: CacheManagerProtocol):
        """
        Initialize tenant-aware cache service.
        
        Args:
            cache_manager: Underlying cache manager implementation
        """
        self.cache = cache_manager
    
    async def get(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get value from cache with optional tenant isolation.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            Cached value if found, None otherwise
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Get from cache using namespace
            namespace = self._get_namespace(tenant_id)
            value = await self.cache.get(cache_key, namespace=namespace)
            
            if value is not None:
                # Try to deserialize JSON
                try:
                    return json.loads(value) if isinstance(value, str) else value
                except (json.JSONDecodeError, TypeError):
                    # Return raw value if not JSON
                    return value
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get failed for key {key} (tenant: {tenant_id}): {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        tenant_id: Optional[str] = None,
        ttl: int = 3600
    ) -> bool:
        """
        Set value in cache with optional tenant isolation.
        
        Args:
            key: Cache key
            value: Value to cache
            tenant_id: Optional tenant ID for namespacing
            ttl: Time to live in seconds
            
        Returns:
            True if successful
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized_value = json.dumps(value, default=str)
            else:
                serialized_value = str(value)
            
            # Set in cache using namespace
            namespace = self._get_namespace(tenant_id)
            return await self.cache.set(
                cache_key, 
                serialized_value, 
                ttl=ttl, 
                namespace=namespace
            )
            
        except Exception as e:
            logger.error(f"Cache set failed for key {key} (tenant: {tenant_id}): {e}")
            return False
    
    async def delete(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Delete value from cache with optional tenant isolation.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            True if successful
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Delete from cache using namespace
            namespace = self._get_namespace(tenant_id)
            return await self.cache.delete(cache_key, namespace=namespace)
            
        except Exception as e:
            logger.error(f"Cache delete failed for key {key} (tenant: {tenant_id}): {e}")
            return False
    
    async def exists(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            True if key exists
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Check existence using namespace
            namespace = self._get_namespace(tenant_id)
            return await self.cache.exists(cache_key, namespace=namespace)
            
        except Exception as e:
            logger.error(f"Cache exists check failed for key {key} (tenant: {tenant_id}): {e}")
            return False
    
    async def expire(
        self,
        key: str,
        ttl: int,
        tenant_id: Optional[str] = None
    ) -> bool:
        """
        Set expiration for key.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            True if successful
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Set expiration using namespace
            namespace = self._get_namespace(tenant_id)
            return await self.cache.expire(cache_key, ttl, namespace=namespace)
            
        except Exception as e:
            logger.error(f"Cache expire failed for key {key} (tenant: {tenant_id}): {e}")
            return False
    
    async def ttl(
        self,
        key: str,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Get time to live for key.
        
        Args:
            key: Cache key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Get TTL - need to implement this in cache manager
            # For now, return -1 (no expiry info available)
            logger.warning(f"TTL operation not fully implemented for key {key}")
            return -1
            
        except Exception as e:
            logger.error(f"Cache TTL check failed for key {key} (tenant: {tenant_id}): {e}")
            return -2
    
    async def increment(
        self,
        key: str,
        amount: int = 1,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Increment numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            New value after increment
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Use cache manager increment if available
            namespace = self._get_namespace(tenant_id)
            result = await self.cache.increment(cache_key, amount, namespace=namespace)
            
            if result is not None:
                return result
            else:
                # Fallback for basic cache implementations
                current = await self.get(key, tenant_id) or 0
                new_value = int(current) + amount
                await self.set(key, new_value, tenant_id)
                return new_value
                
        except Exception as e:
            logger.error(f"Cache increment failed for key {key} (tenant: {tenant_id}): {e}")
            return 0
    
    async def decrement(
        self,
        key: str,
        amount: int = 1,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Decrement numeric value in cache.
        
        Args:
            key: Cache key
            amount: Amount to decrement by
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            New value after decrement
        """
        try:
            # Build namespaced key
            cache_key = self._build_key(key, tenant_id)
            
            # Use cache manager decrement if available
            namespace = self._get_namespace(tenant_id)
            result = await self.cache.decrement(cache_key, amount, namespace=namespace)
            
            if result is not None:
                return result
            else:
                # Fallback for basic cache implementations
                current = await self.get(key, tenant_id) or 0
                new_value = int(current) - amount
                await self.set(key, new_value, tenant_id)
                return new_value
                
        except Exception as e:
            logger.error(f"Cache decrement failed for key {key} (tenant: {tenant_id}): {e}")
            return 0
    
    async def keys(
        self,
        pattern: str,
        tenant_id: Optional[str] = None
    ) -> List[str]:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            List of matching keys (without namespace prefix)
        """
        try:
            # Build namespaced pattern
            search_pattern = self._build_key(pattern, tenant_id)
            
            # Note: This functionality depends on cache manager implementation
            # For now, return empty list with warning
            logger.warning(f"Keys operation not fully implemented for pattern {pattern}")
            return []
                
        except Exception as e:
            logger.error(f"Cache keys search failed for pattern {pattern} (tenant: {tenant_id}): {e}")
            return []
    
    async def clear_pattern(
        self,
        pattern: str,
        tenant_id: Optional[str] = None
    ) -> int:
        """
        Delete all keys matching pattern.
        
        Args:
            pattern: Key pattern (supports wildcards)
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            Number of keys deleted
        """
        try:
            # Build namespaced pattern
            search_pattern = self._build_key(pattern, tenant_id)
            
            # Use cache manager delete_pattern if available
            namespace = self._get_namespace(tenant_id)
            return await self.cache.delete_pattern(search_pattern, namespace=namespace)
            
        except Exception as e:
            logger.error(f"Cache pattern clear failed for pattern {pattern} (tenant: {tenant_id}): {e}")
            return 0
    
    async def health_check(self) -> bool:
        """
        Check cache service health.
        
        Returns:
            True if cache is healthy
        """
        try:
            # Test basic operations
            test_key = "health_check_test"
            test_value = "test_value"
            
            # Set, get, and delete test value
            await self.set(test_key, test_value, ttl=10)
            retrieved = await self.get(test_key)
            await self.delete(test_key)
            
            return retrieved == test_value
            
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics if available.
        
        Returns:
            Cache statistics including health status
        """
        try:
            # Start with basic health status
            stats = {
                "healthy": await self.health_check(),
                "service_type": "TenantAwareCacheService",
                "features": [
                    "tenant_isolation",
                    "json_serialization", 
                    "pattern_operations",
                    "health_monitoring"
                ]
            }
            
            # Try to get underlying cache manager health if available
            if hasattr(self.cache, 'health_check'):
                stats["cache_manager_healthy"] = await self.cache.health_check()
            
            # Try to get cache manager status if available
            if hasattr(self.cache, 'get_cache_status'):
                stats["cache_manager_status"] = self.cache.get_cache_status()
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"healthy": False, "error": str(e)}
    
    def _build_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """
        Build namespaced cache key.
        
        Args:
            key: Base key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            Namespaced key
        """
        if tenant_id:
            return f"tenant:{tenant_id}:{key}"
        else:
            return f"platform:{key}"
    
    def _get_namespace(self, tenant_id: Optional[str] = None) -> Optional[str]:
        """
        Get namespace for cache operations.
        
        Args:
            tenant_id: Optional tenant ID
            
        Returns:
            Namespace string or None
        """
        if tenant_id:
            return f"tenant:{tenant_id}"
        else:
            return "platform"


# Factory function for easy instantiation
def create_tenant_aware_cache(cache_manager: CacheManagerProtocol) -> TenantAwareCacheService:
    """
    Create a tenant-aware cache service instance.
    
    Args:
        cache_manager: Underlying cache manager implementation
        
    Returns:
        Configured TenantAwareCacheService instance
    """
    return TenantAwareCacheService(cache_manager)