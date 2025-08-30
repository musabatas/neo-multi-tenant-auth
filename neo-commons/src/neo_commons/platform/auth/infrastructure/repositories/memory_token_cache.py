"""Memory token cache for authentication platform."""

import asyncio
import logging
from typing import Dict, Optional, Any, Set
from datetime import datetime, timezone, timedelta
from collections import OrderedDict
import weakref

from .....core.value_objects.identifiers import UserId, TenantId
from ...core.value_objects import AccessToken, PublicKey
from ...core.entities import TokenMetadata

logger = logging.getLogger(__name__)


class MemoryTokenCache:
    """Memory-based token cache following maximum separation principle.
    
    Handles ONLY in-memory token caching operations for authentication platform.
    Does not handle token validation, database operations, or Redis storage.
    
    Features:
    - LRU eviction policy
    - TTL-based expiration
    - Memory usage monitoring
    - Thread-safe operations
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl_seconds: int = 300,
        cleanup_interval_seconds: int = 60,
        max_memory_mb: int = 100
    ):
        """Initialize memory token cache.
        
        Args:
            max_size: Maximum number of cached tokens
            default_ttl_seconds: Default TTL for cached tokens
            cleanup_interval_seconds: Interval for cleanup of expired tokens
            max_memory_mb: Maximum memory usage in MB (approximate)
        """
        if max_size <= 0:
            raise ValueError("Max size must be positive")
        if default_ttl_seconds <= 0:
            raise ValueError("Default TTL must be positive")
        
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.cleanup_interval_seconds = cleanup_interval_seconds
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # Cache storage: token_key -> CacheEntry
        self._cache: OrderedDict[str, 'CacheEntry'] = OrderedDict()
        
        # Indexes for efficient lookups
        self._user_tokens: Dict[str, Set[str]] = {}  # user_id -> set of token_keys
        self._tenant_tokens: Dict[str, Set[str]] = {}  # tenant_id -> set of token_keys
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._memory_usage = 0
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Start cleanup task
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start periodic cleanup task."""
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(self.cleanup_interval_seconds)
                    await self._cleanup_expired()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Cleanup task error: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        
        # Use weak reference to avoid circular dependency
        weakref.finalize(self, self._stop_cleanup_task, self._cleanup_task)
    
    @staticmethod
    def _stop_cleanup_task(task: Optional[asyncio.Task]):
        """Stop cleanup task."""
        if task and not task.done():
            task.cancel()
    
    def _make_token_key(
        self,
        token: AccessToken,
        user_id: Optional[UserId] = None,
        tenant_id: Optional[TenantId] = None
    ) -> str:
        """Create cache key for token.
        
        Args:
            token: Access token
            user_id: Optional user identifier for scoping
            tenant_id: Optional tenant identifier for scoping
            
        Returns:
            Cache key string
        """
        # Use first and last 8 characters of token for key (avoid storing full token)
        token_str = str(token.value)
        if len(token_str) > 16:
            token_part = f"{token_str[:8]}...{token_str[-8:]}"
        else:
            token_part = token_str
        
        key_parts = [f"token:{token_part}"]
        
        if user_id:
            key_parts.append(f"user:{user_id.value}")
        
        if tenant_id:
            key_parts.append(f"tenant:{tenant_id.value}")
        
        return "|".join(key_parts)
    
    def _make_public_key_cache_key(
        self,
        realm_id: str,
        key_id: Optional[str] = None
    ) -> str:
        """Create cache key for public key.
        
        Args:
            realm_id: Realm identifier
            key_id: Optional key identifier
            
        Returns:
            Cache key string
        """
        if key_id:
            return f"pubkey:{realm_id}:{key_id}"
        else:
            return f"pubkey:{realm_id}:default"
    
    def _estimate_entry_size(self, entry: 'CacheEntry') -> int:
        """Estimate memory size of cache entry in bytes.
        
        Args:
            entry: Cache entry
            
        Returns:
            Estimated size in bytes
        """
        try:
            # Basic estimation - could be more sophisticated
            data_size = 0
            
            if isinstance(entry.data, dict):
                # Estimate JSON size
                import json
                data_size = len(json.dumps(entry.data, default=str).encode('utf-8'))
            elif isinstance(entry.data, str):
                data_size = len(entry.data.encode('utf-8'))
            elif hasattr(entry.data, '__sizeof__'):
                data_size = entry.data.__sizeof__()
            else:
                data_size = 1024  # Default estimate
            
            # Add overhead for entry metadata
            overhead = 200  # Rough estimate for timestamps, key, etc.
            return data_size + overhead
            
        except Exception:
            return 1024  # Fallback estimate
    
    async def put_token_validation(
        self,
        token: AccessToken,
        validation_result: Dict[str, Any],
        user_id: Optional[UserId] = None,
        tenant_id: Optional[TenantId] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache token validation result.
        
        Args:
            token: Access token
            validation_result: Token validation result dictionary
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            ttl_seconds: Optional TTL (uses default if None)
        """
        async with self._lock:
            cache_key = self._make_token_key(token, user_id, tenant_id)
            ttl = ttl_seconds or self.default_ttl_seconds
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                data=validation_result,
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc)
            )
            
            # Add to cache with LRU update
            if cache_key in self._cache:
                # Update existing entry
                old_entry = self._cache.pop(cache_key)
                self._memory_usage -= self._estimate_entry_size(old_entry)
            
            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)
            self._memory_usage += self._estimate_entry_size(entry)
            
            # Update indexes
            if user_id:
                user_key = str(user_id.value)
                if user_key not in self._user_tokens:
                    self._user_tokens[user_key] = set()
                self._user_tokens[user_key].add(cache_key)
            
            if tenant_id:
                tenant_key = str(tenant_id.value)
                if tenant_key not in self._tenant_tokens:
                    self._tenant_tokens[tenant_key] = set()
                self._tenant_tokens[tenant_key].add(cache_key)
            
            # Perform eviction if needed
            await self._evict_if_needed()
            
            logger.debug(f"Cached token validation: {cache_key}")
    
    async def get_token_validation(
        self,
        token: AccessToken,
        user_id: Optional[UserId] = None,
        tenant_id: Optional[TenantId] = None
    ) -> Optional[Dict[str, Any]]:
        """Get cached token validation result.
        
        Args:
            token: Access token
            user_id: Optional user identifier
            tenant_id: Optional tenant identifier
            
        Returns:
            Validation result or None if not cached
        """
        async with self._lock:
            cache_key = self._make_token_key(token, user_id, tenant_id)
            
            if cache_key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[cache_key]
            
            # Check expiration
            if entry.expires_at <= datetime.now(timezone.utc):
                await self._remove_entry(cache_key)
                self._misses += 1
                return None
            
            # Move to end (LRU)
            self._cache.move_to_end(cache_key)
            self._hits += 1
            
            logger.debug(f"Token validation cache hit: {cache_key}")
            return entry.data
    
    async def put_public_key(
        self,
        realm_id: str,
        public_key: PublicKey,
        key_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Cache public key.
        
        Args:
            realm_id: Realm identifier
            public_key: Public key to cache
            key_id: Optional key identifier
            ttl_seconds: Optional TTL (uses default if None)
        """
        async with self._lock:
            cache_key = self._make_public_key_cache_key(realm_id, key_id)
            ttl = ttl_seconds or self.default_ttl_seconds
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            
            # Store public key data
            key_data = {
                "key_data": public_key.key_data,
                "key_id": public_key.key_id,
                "algorithm": public_key.algorithm,
                "is_rsa_key": public_key.is_rsa_key,
                "is_ec_key": public_key.is_ec_key
            }
            
            entry = CacheEntry(
                key=cache_key,
                data=key_data,
                expires_at=expires_at,
                created_at=datetime.now(timezone.utc)
            )
            
            # Add to cache
            if cache_key in self._cache:
                old_entry = self._cache.pop(cache_key)
                self._memory_usage -= self._estimate_entry_size(old_entry)
            
            self._cache[cache_key] = entry
            self._cache.move_to_end(cache_key)
            self._memory_usage += self._estimate_entry_size(entry)
            
            await self._evict_if_needed()
            
            logger.debug(f"Cached public key: {cache_key}")
    
    async def get_public_key(
        self,
        realm_id: str,
        key_id: Optional[str] = None
    ) -> Optional[PublicKey]:
        """Get cached public key.
        
        Args:
            realm_id: Realm identifier
            key_id: Optional key identifier
            
        Returns:
            Public key or None if not cached
        """
        async with self._lock:
            cache_key = self._make_public_key_cache_key(realm_id, key_id)
            
            if cache_key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[cache_key]
            
            if entry.expires_at <= datetime.now(timezone.utc):
                await self._remove_entry(cache_key)
                self._misses += 1
                return None
            
            self._cache.move_to_end(cache_key)
            self._hits += 1
            
            # Reconstruct public key
            key_data = entry.data
            public_key = PublicKey(
                key_data=key_data["key_data"],
                key_id=key_data.get("key_id"),
                algorithm=key_data.get("algorithm")
            )
            
            logger.debug(f"Public key cache hit: {cache_key}")
            return public_key
    
    async def invalidate_user_tokens(self, user_id: UserId) -> int:
        """Invalidate all cached tokens for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of tokens invalidated
        """
        async with self._lock:
            user_key = str(user_id.value)
            
            if user_key not in self._user_tokens:
                return 0
            
            token_keys = self._user_tokens[user_key].copy()
            count = 0
            
            for cache_key in token_keys:
                if cache_key in self._cache:
                    await self._remove_entry(cache_key)
                    count += 1
            
            del self._user_tokens[user_key]
            
            logger.debug(f"Invalidated {count} tokens for user {user_id.value}")
            return count
    
    async def invalidate_tenant_tokens(self, tenant_id: TenantId) -> int:
        """Invalidate all cached tokens for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Number of tokens invalidated
        """
        async with self._lock:
            tenant_key = str(tenant_id.value)
            
            if tenant_key not in self._tenant_tokens:
                return 0
            
            token_keys = self._tenant_tokens[tenant_key].copy()
            count = 0
            
            for cache_key in token_keys:
                if cache_key in self._cache:
                    await self._remove_entry(cache_key)
                    count += 1
            
            del self._tenant_tokens[tenant_key]
            
            logger.debug(f"Invalidated {count} tokens for tenant {tenant_id.value}")
            return count
    
    async def clear(self) -> None:
        """Clear all cached data."""
        async with self._lock:
            self._cache.clear()
            self._user_tokens.clear()
            self._tenant_tokens.clear()
            self._memory_usage = 0
            
            logger.debug("Cleared token cache")
    
    async def _remove_entry(self, cache_key: str) -> None:
        """Remove entry from cache and update indexes.
        
        Args:
            cache_key: Cache key to remove
        """
        if cache_key not in self._cache:
            return
        
        entry = self._cache.pop(cache_key)
        self._memory_usage -= self._estimate_entry_size(entry)
        
        # Update indexes
        for user_key, token_keys in self._user_tokens.items():
            if cache_key in token_keys:
                token_keys.discard(cache_key)
                if not token_keys:
                    del self._user_tokens[user_key]
                break
        
        for tenant_key, token_keys in self._tenant_tokens.items():
            if cache_key in token_keys:
                token_keys.discard(cache_key)
                if not token_keys:
                    del self._tenant_tokens[tenant_key]
                break
    
    async def _cleanup_expired(self) -> int:
        """Clean up expired entries.
        
        Returns:
            Number of entries cleaned up
        """
        async with self._lock:
            current_time = datetime.now(timezone.utc)
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.expires_at <= current_time:
                    expired_keys.append(key)
            
            for key in expired_keys:
                await self._remove_entry(key)
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    async def _evict_if_needed(self) -> int:
        """Evict entries if cache is over limits.
        
        Returns:
            Number of entries evicted
        """
        evicted = 0
        
        # Check size limit
        while len(self._cache) > self.max_size:
            # Remove least recently used (first item)
            oldest_key = next(iter(self._cache))
            await self._remove_entry(oldest_key)
            evicted += 1
            self._evictions += 1
        
        # Check memory limit
        while self._memory_usage > self.max_memory_bytes and self._cache:
            oldest_key = next(iter(self._cache))
            await self._remove_entry(oldest_key)
            evicted += 1
            self._evictions += 1
        
        if evicted > 0:
            logger.debug(f"Evicted {evicted} cache entries due to size/memory limits")
        
        return evicted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        hit_rate = self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "memory_usage_bytes": self._memory_usage,
            "memory_usage_mb": self._memory_usage / (1024 * 1024),
            "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "user_token_indexes": len(self._user_tokens),
            "tenant_token_indexes": len(self._tenant_tokens)
        }


class CacheEntry:
    """Cache entry with expiration and metadata."""
    
    def __init__(
        self,
        key: str,
        data: Any,
        expires_at: datetime,
        created_at: datetime
    ):
        self.key = key
        self.data = data
        self.expires_at = expires_at
        self.created_at = created_at