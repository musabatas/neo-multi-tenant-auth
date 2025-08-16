"""
Cache Protocol Definitions for NeoMultiTenant Platform

Enhanced cache protocols supporting tenant isolation, multi-service deployments,
and enterprise-grade caching patterns.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class TenantAwareCacheProtocol(Protocol):
    """
    Protocol for tenant-aware cache operations.
    
    Provides comprehensive caching capabilities with built-in tenant isolation,
    pattern-based operations, and enterprise-grade features.
    """
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
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
        ...
    
    async def health_check(self) -> bool:
        """
        Check cache service health.
        
        Returns:
            True if cache is healthy
        """
        ...
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics if available.
        
        Returns:
            Cache statistics including health status
        """
        ...
    
    def _build_key(self, key: str, tenant_id: Optional[str] = None) -> str:
        """
        Build namespaced cache key.
        
        Args:
            key: Base key
            tenant_id: Optional tenant ID for namespacing
            
        Returns:
            Namespaced key
        """
        ...


@runtime_checkable  
class CacheManagerProtocol(Protocol):
    """
    Protocol for cache manager operations.
    
    Provides lower-level cache operations that can be used
    to implement higher-level cache services.
    """
    
    async def get(
        self, 
        key: str, 
        namespace: Optional[str] = None
    ) -> Optional[Any]:
        """Get value from cache with namespace support."""
        ...
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        namespace: Optional[str] = None
    ) -> bool:
        """Set value in cache with namespace support."""
        ...
    
    async def delete(
        self, 
        key: str, 
        namespace: Optional[str] = None
    ) -> bool:
        """Delete value from cache with namespace support."""
        ...
    
    async def delete_pattern(
        self, 
        pattern: str, 
        namespace: Optional[str] = None
    ) -> int:
        """Delete all keys matching a pattern."""
        ...
    
    async def exists(
        self, 
        key: str, 
        namespace: Optional[str] = None
    ) -> bool:
        """Check if key exists in cache."""
        ...
    
    async def expire(
        self, 
        key: str, 
        ttl: int, 
        namespace: Optional[str] = None
    ) -> bool:
        """Set expiration time for a key."""
        ...
    
    async def increment(
        self, 
        key: str, 
        amount: int = 1,
        namespace: Optional[str] = None
    ) -> Optional[int]:
        """Increment a counter in cache."""
        ...
    
    async def decrement(
        self, 
        key: str, 
        amount: int = 1,
        namespace: Optional[str] = None
    ) -> Optional[int]:
        """Decrement a counter in cache."""
        ...
    
    async def health_check(self) -> bool:
        """Check cache health."""
        ...