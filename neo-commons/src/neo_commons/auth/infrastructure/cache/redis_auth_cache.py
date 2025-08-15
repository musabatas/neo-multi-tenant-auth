"""
Redis cache implementation for general authentication and session data.

Provides caching for sessions, tokens, and general auth-related data.
"""
import json
from typing import Optional, Dict, Any
import redis.asyncio as redis
from loguru import logger

from ...domain.protocols.cache_protocols import AuthCacheProtocol


class RedisAuthCache(AuthCacheProtocol):
    """
    Redis implementation of general auth cache.
    
    Handles sessions, tokens, and other auth-related caching needs
    with tenant isolation and automatic TTL management.
    """

    def __init__(self, redis_client: redis.Redis, key_prefix: str = "neo_auth"):
        self._redis = redis_client
        self._key_prefix = key_prefix

    async def get_session_validity(self, cache_key: str) -> Optional[bool]:
        """Get cached session validity."""
        try:
            full_key = f"{self._key_prefix}:session_valid:{cache_key}"
            result = await self._redis.get(full_key)
            if result is not None:
                return result.decode() == "true"
            return None
        except Exception as e:
            logger.warning(f"Failed to get session validity from cache: {e}")
            return None

    async def set_session_validity(
        self,
        cache_key: str,
        is_valid: bool,
        ttl: int = 60
    ) -> None:
        """Cache session validity."""
        try:
            full_key = f"{self._key_prefix}:session_valid:{cache_key}"
            await self._redis.setex(full_key, ttl, "true" if is_valid else "false")
        except Exception as e:
            logger.warning(f"Failed to cache session validity: {e}")

    async def invalidate_session_validity(self, cache_key: str) -> None:
        """Invalidate cached session validity."""
        try:
            full_key = f"{self._key_prefix}:session_valid:{cache_key}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate session validity: {e}")

    async def get_token_claims(self, token_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached token claims."""
        try:
            full_key = f"{self._key_prefix}:token_claims:{token_hash}"
            result = await self._redis.get(full_key)
            if result is not None:
                return json.loads(result.decode())
            return None
        except Exception as e:
            logger.warning(f"Failed to get token claims from cache: {e}")
            return None

    async def set_token_claims(
        self,
        token_hash: str,
        claims: Dict[str, Any],
        ttl: int = 300
    ) -> None:
        """Cache token claims."""
        try:
            full_key = f"{self._key_prefix}:token_claims:{token_hash}"
            data = json.dumps(claims)
            await self._redis.setex(full_key, ttl, data)
        except Exception as e:
            logger.warning(f"Failed to cache token claims: {e}")

    async def invalidate_token_claims(self, token_hash: str) -> None:
        """Invalidate cached token claims."""
        try:
            full_key = f"{self._key_prefix}:token_claims:{token_hash}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate token claims: {e}")

    async def get_user_context(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached user context."""
        try:
            full_key = f"{self._key_prefix}:user_context:{cache_key}"
            result = await self._redis.get(full_key)
            if result is not None:
                return json.loads(result.decode())
            return None
        except Exception as e:
            logger.warning(f"Failed to get user context from cache: {e}")
            return None

    async def set_user_context(
        self,
        cache_key: str,
        context: Dict[str, Any],
        ttl: int = 300
    ) -> None:
        """Cache user context."""
        try:
            full_key = f"{self._key_prefix}:user_context:{cache_key}"
            data = json.dumps(context)
            await self._redis.setex(full_key, ttl, data)
        except Exception as e:
            logger.warning(f"Failed to cache user context: {e}")

    async def invalidate_user_context(self, cache_key: str) -> None:
        """Invalidate cached user context."""
        try:
            full_key = f"{self._key_prefix}:user_context:{cache_key}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate user context: {e}")

    async def get_realm_keys(self, realm_name: str) -> Optional[Dict[str, Any]]:
        """Get cached Keycloak realm public keys."""
        try:
            full_key = f"{self._key_prefix}:realm_keys:{realm_name}"
            result = await self._redis.get(full_key)
            if result is not None:
                return json.loads(result.decode())
            return None
        except Exception as e:
            logger.warning(f"Failed to get realm keys from cache: {e}")
            return None

    async def set_realm_keys(
        self,
        realm_name: str,
        keys: Dict[str, Any],
        ttl: int = 3600
    ) -> None:
        """Cache Keycloak realm public keys."""
        try:
            full_key = f"{self._key_prefix}:realm_keys:{realm_name}"
            data = json.dumps(keys)
            await self._redis.setex(full_key, ttl, data)
        except Exception as e:
            logger.warning(f"Failed to cache realm keys: {e}")

    async def invalidate_realm_keys(self, realm_name: str) -> None:
        """Invalidate cached realm keys."""
        try:
            full_key = f"{self._key_prefix}:realm_keys:{realm_name}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate realm keys: {e}")

    async def get_rate_limit(self, cache_key: str) -> Optional[int]:
        """Get current rate limit count."""
        try:
            full_key = f"{self._key_prefix}:rate_limit:{cache_key}"
            result = await self._redis.get(full_key)
            if result is not None:
                return int(result.decode())
            return None
        except Exception as e:
            logger.warning(f"Failed to get rate limit from cache: {e}")
            return None

    async def increment_rate_limit(
        self,
        cache_key: str,
        ttl: int = 60
    ) -> int:
        """Increment rate limit counter."""
        try:
            full_key = f"{self._key_prefix}:rate_limit:{cache_key}"
            
            # Use pipeline for atomic increment and expiry
            pipe = self._redis.pipeline()
            pipe.incr(full_key)
            pipe.expire(full_key, ttl)
            results = await pipe.execute()
            
            return results[0]
        except Exception as e:
            logger.warning(f"Failed to increment rate limit: {e}")
            return 1

    async def reset_rate_limit(self, cache_key: str) -> None:
        """Reset rate limit counter."""
        try:
            full_key = f"{self._key_prefix}:rate_limit:{cache_key}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to reset rate limit: {e}")

    async def get_blacklisted_token(self, token_hash: str) -> Optional[bool]:
        """Check if token is blacklisted."""
        try:
            full_key = f"{self._key_prefix}:blacklist:{token_hash}"
            result = await self._redis.get(full_key)
            return result is not None
        except Exception as e:
            logger.warning(f"Failed to check token blacklist: {e}")
            return False

    async def blacklist_token(
        self,
        token_hash: str,
        ttl: int = 86400
    ) -> None:
        """Add token to blacklist."""
        try:
            full_key = f"{self._key_prefix}:blacklist:{token_hash}"
            await self._redis.setex(full_key, ttl, "1")
        except Exception as e:
            logger.warning(f"Failed to blacklist token: {e}")

    async def remove_from_blacklist(self, token_hash: str) -> None:
        """Remove token from blacklist."""
        try:
            full_key = f"{self._key_prefix}:blacklist:{token_hash}"
            await self._redis.delete(full_key)
        except Exception as e:
            logger.warning(f"Failed to remove from blacklist: {e}")

    async def cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries (Redis handles this automatically)."""
        # Redis handles TTL automatically, but we can provide stats
        try:
            info = await self._redis.info("keyspace")
            # Return count of keys in our database
            return info.get("keys", 0)
        except Exception as e:
            logger.warning(f"Failed to get cleanup stats: {e}")
            return 0

    async def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health information."""
        try:
            info = await self._redis.info()
            
            return {
                "status": "healthy" if info.get("redis_version") else "unhealthy",
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "memory_used": info.get("used_memory_human"),
                "memory_peak": info.get("used_memory_peak_human"),
                "connected_clients": info.get("connected_clients"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "hit_rate": (
                    info.get("keyspace_hits", 0) / 
                    max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                ) * 100
            }
        except Exception as e:
            logger.error(f"Failed to get cache health: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }