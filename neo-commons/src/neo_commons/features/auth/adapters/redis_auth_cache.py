"""Redis implementation of auth cache protocols."""

import json
import logging
from typing import Dict, List, Optional

import redis.asyncio as redis

from ....core.exceptions.auth import CacheError
from ....core.value_objects.identifiers import RealmId, TenantId, UserId
from ..entities.auth_context import AuthContext
from ..entities.cache_protocols import AuthCacheManagerProtocol, BaseAuthCache

logger = logging.getLogger(__name__)


class RedisAuthCache(BaseAuthCache, AuthCacheManagerProtocol):
    """Redis implementation of auth cache manager."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        redis_password: Optional[str] = None,
        redis_db: int = 0,
        key_prefix: str = "neo_auth",
        default_ttl: int = 3600,
    ):
        """Initialize Redis auth cache."""
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.redis_db = redis_db
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        
        self._redis: Optional[redis.Redis] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._redis = redis.from_url(
                self.redis_url,
                password=self.redis_password,
                db=self.redis_db,
                decode_responses=True,
            )
            
            # Test connection
            await self._redis.ping()
            logger.info("Connected to Redis for auth cache")
        
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise CacheError(f"Redis connection failed: {e}") from e
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None
            logger.info("Disconnected from Redis")
    
    def _ensure_connected(self) -> redis.Redis:
        """Ensure Redis connection is active."""
        if not self._redis:
            raise CacheError("Redis not connected. Use async context manager or call connect().")
        return self._redis
    
    def _make_key(self, key: str) -> str:
        """Add prefix to cache key."""
        return f"{self.key_prefix}:{key}"
    
    # Base cache operations
    
    async def _get(self, key: str) -> Optional[str]:
        """Get value from Redis."""
        try:
            redis_client = self._ensure_connected()
            full_key = self._make_key(key)
            
            value = await redis_client.get(full_key)
            return value
        
        except Exception as e:
            logger.warning(f"Failed to get cache key {key}: {e}")
            return None
    
    async def _set(self, key: str, value: str, ttl: int) -> None:
        """Set value in Redis."""
        try:
            redis_client = self._ensure_connected()
            full_key = self._make_key(key)
            
            await redis_client.setex(full_key, ttl, value)
            logger.debug(f"Cached key {key} with TTL {ttl}")
        
        except Exception as e:
            logger.warning(f"Failed to set cache key {key}: {e}")
            # Don't raise exception for cache failures
    
    async def _delete(self, key: str) -> None:
        """Delete key from Redis."""
        try:
            redis_client = self._ensure_connected()
            full_key = self._make_key(key)
            
            await redis_client.delete(full_key)
            logger.debug(f"Deleted cache key {key}")
        
        except Exception as e:
            logger.warning(f"Failed to delete cache key {key}: {e}")
    
    async def _delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern."""
        try:
            redis_client = self._ensure_connected()
            full_pattern = self._make_key(pattern)
            
            # Get matching keys
            keys = await redis_client.keys(full_pattern)
            
            if keys:
                deleted_count = await redis_client.delete(*keys)
                logger.debug(f"Deleted {deleted_count} keys matching pattern {pattern}")
                return deleted_count
            
            return 0
        
        except Exception as e:
            logger.warning(f"Failed to delete keys matching pattern {pattern}: {e}")
            return 0
    
    async def _exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            redis_client = self._ensure_connected()
            full_key = self._make_key(key)
            
            exists = await redis_client.exists(full_key)
            return bool(exists)
        
        except Exception as e:
            logger.warning(f"Failed to check existence of key {key}: {e}")
            return False
    
    # Public key cache operations
    
    async def get_public_key(self, realm_id: RealmId) -> Optional[str]:
        """Get cached public key for realm."""
        key = self._make_public_key_key(realm_id)
        return await self._get(key)
    
    async def cache_public_key(self, realm_id: RealmId, public_key: str, ttl: int = 3600) -> None:
        """Cache public key for realm."""
        key = self._make_public_key_key(realm_id)
        await self._set(key, public_key, ttl)
    
    # Token cache operations
    
    async def get_cached_token(self, token_id: str) -> Optional[AuthContext]:
        """Get cached auth context for token."""
        key = self._make_token_key(token_id)
        cached_data = await self._get(key)
        
        if not cached_data:
            return None
        
        try:
            data = json.loads(cached_data)
            return AuthContext.from_dict(data)
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to deserialize cached token {token_id}: {e}")
            await self._delete(key)  # Clean up corrupted cache
            return None
    
    async def cache_token(self, token_id: str, auth_context: AuthContext, ttl: int) -> None:
        """Cache validated token and auth context."""
        key = self._make_token_key(token_id)
        
        try:
            data = auth_context.to_dict()
            cached_data = json.dumps(data, default=str)
            await self._set(key, cached_data, ttl)
        
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize auth context for token {token_id}: {e}")
    
    async def invalidate_token(self, token_id: str) -> None:
        """Invalidate specific cached token."""
        key = self._make_token_key(token_id)
        await self._delete(key)
    
    async def invalidate_user_tokens(self, user_id: UserId) -> None:
        """Invalidate all cached tokens for user."""
        pattern = self._make_user_tokens_pattern(user_id)
        deleted_count = await self._delete_pattern(pattern)
        logger.info(f"Invalidated {deleted_count} tokens for user {user_id.value}")
    
    # User mapping cache operations
    
    async def get_user_mapping(
        self, 
        keycloak_user_id: str, 
        tenant_id: TenantId,
    ) -> Optional[Dict]:
        """Get cached user mapping."""
        key = self._make_user_mapping_key(keycloak_user_id, tenant_id)
        cached_data = await self._get(key)
        
        if not cached_data:
            return None
        
        try:
            return json.loads(cached_data)
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to deserialize user mapping cache: {e}")
            await self._delete(key)
            return None
    
    async def cache_user_mapping(
        self,
        keycloak_user_id: str,
        tenant_id: TenantId,
        mapping_data: Dict,
        ttl: int = 1800,
    ) -> None:
        """Cache user mapping data."""
        key = self._make_user_mapping_key(keycloak_user_id, tenant_id)
        
        try:
            cached_data = json.dumps(mapping_data, default=str)
            await self._set(key, cached_data, ttl)
        
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize user mapping data: {e}")
    
    async def invalidate_user_mapping(
        self, 
        keycloak_user_id: str, 
        tenant_id: TenantId,
    ) -> None:
        """Invalidate specific user mapping."""
        key = self._make_user_mapping_key(keycloak_user_id, tenant_id)
        await self._delete(key)
    
    async def invalidate_tenant_mappings(self, tenant_id: TenantId) -> None:
        """Invalidate all user mappings for tenant."""
        pattern = f"auth:user_mapping:{tenant_id.value}:*"
        deleted_count = await self._delete_pattern(pattern)
        logger.info(f"Invalidated {deleted_count} user mappings for tenant {tenant_id.value}")
    
    # Realm config cache operations
    
    async def get_realm_config(self, tenant_id: TenantId) -> Optional[Dict]:
        """Get cached realm configuration."""
        key = self._make_realm_config_key(tenant_id)
        cached_data = await self._get(key)
        
        if not cached_data:
            return None
        
        try:
            return json.loads(cached_data)
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to deserialize realm config cache: {e}")
            await self._delete(key)
            return None
    
    async def cache_realm_config(
        self,
        tenant_id: TenantId,
        config_data: Dict,
        ttl: int = 3600,
    ) -> None:
        """Cache realm configuration."""
        key = self._make_realm_config_key(tenant_id)
        
        try:
            cached_data = json.dumps(config_data, default=str)
            await self._set(key, cached_data, ttl)
        
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize realm config data: {e}")
    
    async def invalidate_realm_config(self, tenant_id: TenantId) -> None:
        """Invalidate cached realm configuration."""
        key = self._make_realm_config_key(tenant_id)
        await self._delete(key)
    
    async def invalidate_all_realm_configs(self) -> None:
        """Invalidate all cached realm configurations."""
        pattern = "auth:realm_config:*"
        deleted_count = await self._delete_pattern(pattern)
        logger.info(f"Invalidated {deleted_count} realm configurations")
    
    # Bulk invalidation operations
    
    async def invalidate_tenant_data(self, tenant_id: TenantId) -> None:
        """Invalidate all cached data for tenant."""
        pattern = self._make_tenant_pattern(tenant_id)
        deleted_count = await self._delete_pattern(pattern)
        logger.info(f"Invalidated {deleted_count} cache entries for tenant {tenant_id.value}")
    
    async def invalidate_realm_data(self, realm_id: RealmId) -> None:
        """Invalidate all cached data for realm."""
        # Invalidate public key
        public_key_key = self._make_public_key_key(realm_id)
        await self._delete(public_key_key)
        
        # Could also invalidate realm-specific tokens if we tracked them
        logger.info(f"Invalidated cache data for realm {realm_id.value}")
    
    async def health_check(self) -> Dict[str, bool]:
        """Check cache connectivity and health."""
        try:
            redis_client = self._ensure_connected()
            
            # Test basic operations
            test_key = "auth:health_check"
            full_key = self._make_key(test_key)
            
            # Test set
            await redis_client.setex(full_key, 10, "health_check")
            
            # Test get
            value = await redis_client.get(full_key)
            
            # Test delete
            await redis_client.delete(full_key)
            
            return {
                "connected": True,
                "set_operation": True,
                "get_operation": value == "health_check",
                "delete_operation": True,
            }
        
        except Exception as e:
            logger.error(f"Cache health check failed: {e}")
            return {
                "connected": False,
                "set_operation": False,
                "get_operation": False,
                "delete_operation": False,
                "error": str(e),
            }
    
    async def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        try:
            redis_client = self._ensure_connected()
            
            # Get Redis info
            info = await redis_client.info("memory")
            keyspace_info = await redis_client.info("keyspace")
            
            # Count our keys
            pattern = self._make_key("*")
            our_keys = await redis_client.keys(pattern)
            
            return {
                "total_keys": len(our_keys),
                "memory_used": info.get("used_memory", 0),
                "memory_used_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": keyspace_info.get("keyspace_hits", 0),
                "keyspace_misses": keyspace_info.get("keyspace_misses", 0),
            }
        
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}