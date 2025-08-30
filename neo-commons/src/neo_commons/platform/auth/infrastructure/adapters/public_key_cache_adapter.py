"""Public key cache adapter for authentication platform."""

import logging
from typing import Optional, Dict, Any, Set
from datetime import datetime, timezone, timedelta

from ...core.value_objects import PublicKey, RealmIdentifier
from ...core.exceptions import PublicKeyError

logger = logging.getLogger(__name__)


class PublicKeyCacheAdapter:
    """Public key cache adapter following maximum separation principle.
    
    Handles ONLY public key caching operations for authentication platform.
    Does not handle token validation, Keycloak operations, or general caching.
    """
    
    def __init__(
        self,
        cache_client,
        default_ttl_seconds: int = 3600,
        key_prefix: str = "auth_public_key"
    ):
        """Initialize public key cache adapter.
        
        Args:
            cache_client: Cache client instance (Redis, Memory, etc.)
            default_ttl_seconds: Default TTL for cached public keys
            key_prefix: Prefix for cache keys
        """
        if not cache_client:
            raise ValueError("Cache client is required")
        if default_ttl_seconds <= 0:
            raise ValueError("TTL must be positive")
            
        self.cache_client = cache_client
        self.default_ttl_seconds = default_ttl_seconds
        self.key_prefix = key_prefix
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def _make_cache_key(
        self,
        realm_id: RealmIdentifier,
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
            return f"{self.key_prefix}:{realm_id.value}:{key_id}"
        else:
            return f"{self.key_prefix}:{realm_id.value}:default"
    
    async def get_public_key(
        self,
        realm_id: RealmIdentifier,
        key_id: Optional[str] = None
    ) -> Optional[PublicKey]:
        """Get cached public key.
        
        Args:
            realm_id: Realm identifier
            key_id: Optional key identifier
            
        Returns:
            Public key or None if not cached
        """
        cache_key = self._make_cache_key(realm_id, key_id)
        
        try:
            logger.debug(f"Getting public key from cache: {cache_key}")
            
            # Get cached data
            cached_data = await self.cache_client.get(cache_key)
            
            if cached_data is None:
                self._misses += 1
                logger.debug(f"Public key cache miss: {cache_key}")
                return None
            
            # Parse cached data
            if isinstance(cached_data, str):
                import json
                cached_data = json.loads(cached_data)
            
            # Check expiration
            if "expires_at" in cached_data:
                expires_at = datetime.fromisoformat(cached_data["expires_at"])
                if expires_at <= datetime.now(timezone.utc):
                    logger.debug(f"Cached public key expired: {cache_key}")
                    await self.invalidate_public_key(realm_id, key_id)
                    self._misses += 1
                    return None
            
            # Reconstruct public key
            public_key = PublicKey(
                key_data=cached_data["key_data"],
                key_id=cached_data.get("key_id"),
                algorithm=cached_data.get("algorithm")
            )
            
            self._hits += 1
            logger.debug(f"Public key cache hit: {cache_key}")
            return public_key
            
        except Exception as e:
            logger.warning(f"Failed to get public key from cache {cache_key}: {e}")
            self._misses += 1
            return None
    
    async def store_public_key(
        self,
        realm_id: RealmIdentifier,
        public_key: PublicKey,
        key_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Store public key in cache.
        
        Args:
            realm_id: Realm identifier
            public_key: Public key to cache
            key_id: Optional key identifier
            ttl_seconds: Optional TTL (uses default if None)
        """
        cache_key = self._make_cache_key(realm_id, key_id)
        ttl = ttl_seconds or self.default_ttl_seconds
        
        try:
            logger.debug(f"Storing public key in cache: {cache_key} with TTL {ttl}s")
            
            # Prepare cache data
            cache_data = {
                "key_data": public_key.key_data,
                "key_id": public_key.key_id,
                "algorithm": public_key.algorithm,
                "is_rsa_key": public_key.is_rsa_key,
                "is_ec_key": public_key.is_ec_key,
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
            }
            
            # Store in cache
            import json
            await self.cache_client.set(
                cache_key,
                json.dumps(cache_data),
                ttl=ttl
            )
            
            logger.debug(f"Successfully stored public key in cache: {cache_key}")
            
        except Exception as e:
            logger.error(f"Failed to store public key in cache {cache_key}: {e}")
            raise PublicKeyError(
                "Failed to cache public key",
                context={
                    "realm_id": str(realm_id.value),
                    "key_id": key_id,
                    "error": str(e)
                }
            )
    
    async def invalidate_public_key(
        self,
        realm_id: RealmIdentifier,
        key_id: Optional[str] = None
    ) -> bool:
        """Invalidate cached public key.
        
        Args:
            realm_id: Realm identifier
            key_id: Optional key identifier
            
        Returns:
            True if key was invalidated
        """
        cache_key = self._make_cache_key(realm_id, key_id)
        
        try:
            logger.debug(f"Invalidating public key in cache: {cache_key}")
            
            result = await self.cache_client.delete(cache_key)
            
            if result:
                logger.debug(f"Successfully invalidated public key: {cache_key}")
                self._evictions += 1
            else:
                logger.debug(f"Public key not found for invalidation: {cache_key}")
            
            return bool(result)
            
        except Exception as e:
            logger.warning(f"Failed to invalidate public key {cache_key}: {e}")
            return False
    
    async def invalidate_realm_keys(
        self,
        realm_id: RealmIdentifier
    ) -> int:
        """Invalidate all cached public keys for a realm.
        
        Args:
            realm_id: Realm identifier
            
        Returns:
            Number of keys invalidated
        """
        try:
            logger.info(f"Invalidating all public keys for realm: {realm_id.value}")
            
            # Get all keys for this realm
            pattern = f"{self.key_prefix}:{realm_id.value}:*"
            
            # Find matching keys
            matching_keys = []
            if hasattr(self.cache_client, 'scan_iter'):
                # Redis-like interface
                async for key in self.cache_client.scan_iter(match=pattern):
                    matching_keys.append(key.decode() if isinstance(key, bytes) else key)
            elif hasattr(self.cache_client, 'keys'):
                # Memory cache interface
                all_keys = await self.cache_client.keys()
                for key in all_keys:
                    if key.startswith(f"{self.key_prefix}:{realm_id.value}:"):
                        matching_keys.append(key)
            
            # Delete all matching keys
            deleted_count = 0
            for key in matching_keys:
                try:
                    if await self.cache_client.delete(key):
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete key {key}: {e}")
                    continue
            
            logger.info(f"Invalidated {deleted_count} public keys for realm: {realm_id.value}")
            self._evictions += deleted_count
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to invalidate realm keys for {realm_id.value}: {e}")
            return 0
    
    async def refresh_public_key(
        self,
        realm_id: RealmIdentifier,
        key_provider,
        key_id: Optional[str] = None,
        ttl_seconds: Optional[int] = None
    ) -> PublicKey:
        """Refresh public key in cache from provider.
        
        Args:
            realm_id: Realm identifier
            key_provider: Provider function/method to get fresh key
            key_id: Optional key identifier
            ttl_seconds: Optional TTL (uses default if None)
            
        Returns:
            Refreshed public key
            
        Raises:
            PublicKeyError: If refresh fails
        """
        try:
            logger.debug(f"Refreshing public key for realm: {realm_id.value}")
            
            # Get fresh key from provider
            if callable(key_provider):
                fresh_key_data = await key_provider(realm_id, key_id)
            else:
                raise PublicKeyError(
                    "Key provider must be callable",
                    context={"realm_id": str(realm_id.value)}
                )
            
            # Create public key object
            if isinstance(fresh_key_data, str):
                public_key = PublicKey(
                    key_data=fresh_key_data,
                    key_id=key_id
                )
            elif isinstance(fresh_key_data, dict):
                public_key = PublicKey(
                    key_data=fresh_key_data.get("key_data"),
                    key_id=fresh_key_data.get("key_id", key_id),
                    algorithm=fresh_key_data.get("algorithm")
                )
            else:
                raise PublicKeyError(
                    "Invalid key data format from provider",
                    context={"realm_id": str(realm_id.value)}
                )
            
            # Store refreshed key in cache
            await self.store_public_key(realm_id, public_key, key_id, ttl_seconds)
            
            logger.debug(f"Successfully refreshed public key for realm: {realm_id.value}")
            return public_key
            
        except PublicKeyError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to refresh public key for realm {realm_id.value}: {e}")
            raise PublicKeyError(
                "Public key refresh failed",
                context={
                    "realm_id": str(realm_id.value),
                    "key_id": key_id,
                    "error": str(e)
                }
            )
    
    async def warm_cache(
        self,
        realm_keys: Dict[RealmIdentifier, Dict[str, Any]],
        ttl_seconds: Optional[int] = None
    ) -> int:
        """Warm cache with multiple public keys.
        
        Args:
            realm_keys: Dictionary mapping realm IDs to key data
            ttl_seconds: Optional TTL (uses default if None)
            
        Returns:
            Number of keys cached
        """
        cached_count = 0
        
        try:
            logger.info(f"Warming public key cache with {len(realm_keys)} realms")
            
            for realm_id, key_data in realm_keys.items():
                try:
                    # Create public key object
                    public_key = PublicKey(
                        key_data=key_data.get("key_data"),
                        key_id=key_data.get("key_id"),
                        algorithm=key_data.get("algorithm")
                    )
                    
                    # Store in cache
                    await self.store_public_key(
                        realm_id,
                        public_key,
                        key_data.get("key_id"),
                        ttl_seconds
                    )
                    
                    cached_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to warm cache for realm {realm_id.value}: {e}")
                    continue
            
            logger.info(f"Successfully warmed cache with {cached_count} public keys")
            return cached_count
            
        except Exception as e:
            logger.error(f"Cache warming failed: {e}")
            return cached_count
    
    async def clear_cache(self) -> bool:
        """Clear all cached public keys.
        
        Returns:
            True if cache was cleared successfully
        """
        try:
            logger.warning("Clearing all cached public keys")
            
            # Get all public key cache keys
            pattern = f"{self.key_prefix}:*"
            deleted_count = 0
            
            # Find and delete all matching keys
            if hasattr(self.cache_client, 'scan_iter'):
                # Redis-like interface
                async for key in self.cache_client.scan_iter(match=pattern):
                    if await self.cache_client.delete(key):
                        deleted_count += 1
            elif hasattr(self.cache_client, 'keys'):
                # Memory cache interface
                all_keys = await self.cache_client.keys()
                for key in all_keys:
                    if key.startswith(self.key_prefix):
                        if await self.cache_client.delete(key):
                            deleted_count += 1
            
            logger.warning(f"Cleared {deleted_count} public keys from cache")
            self._evictions += deleted_count
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear public key cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        hit_rate = self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "evictions": self._evictions,
            "default_ttl_seconds": self.default_ttl_seconds,
            "key_prefix": self.key_prefix
        }