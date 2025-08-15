"""
Redis operations utilities for cache management.

Provides helper methods and operations for Redis cache functionality.
"""
import json
import pickle
from typing import Any, List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RedisOperations:
    """Helper class for Redis operations and utilities."""
    
    @staticmethod
    def serialize_value(value: Any, serialize: bool = True) -> Any:
        """Serialize value for Redis storage."""
        if not serialize:
            return value
            
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value)
        elif not isinstance(value, (str, bytes, int, float)):
            return pickle.dumps(value)
        
        return value
    
    @staticmethod
    def deserialize_value(value: Any, deserialize: bool = True) -> Any:
        """Deserialize value from Redis storage."""
        if value is None or not deserialize:
            return value
            
        if isinstance(value, str):
            try:
                # Try JSON first
                return json.loads(value)
            except json.JSONDecodeError:
                # Return as string if not JSON
                return value
        elif isinstance(value, bytes):
            try:
                # Try pickle for bytes
                return pickle.loads(value)
            except:
                return value.decode('utf-8')
        
        return value
    
    @staticmethod
    def make_key(key: str, prefix: str, namespace: Optional[str] = None) -> str:
        """Create a namespaced cache key."""
        if namespace:
            return f"{prefix}{namespace}:{key}"
        return f"{prefix}{key}"
    
    @staticmethod
    def process_multi_get_result(keys: List[str], values: List[Any]) -> Dict[str, Any]:
        """Process multi-get results with deserialization."""
        result = {}
        
        for key, value in zip(keys, values):
            if value is not None:
                try:
                    result[key] = json.loads(value) if isinstance(value, str) else value
                except:
                    result[key] = value
        
        return result
    
    @staticmethod
    def get_cache_status_info(
        redis_url: Optional[str], 
        is_available: bool,
        connection_attempted: bool
    ) -> Dict[str, Any]:
        """Get cache status information."""
        return {
            "redis_configured": bool(redis_url),
            "redis_available": is_available,
            "connection_attempted": connection_attempted,
            "redis_url": redis_url if redis_url else None,
            "performance_impact": not is_available,
            "warnings": [
                "Redis not configured - set REDIS_URL environment variable",
                "Using database for all operations (no caching)",
                "Performance may be significantly impacted",
                "Permission checks will be slower (no cache)",
                "Token validation will be slower (repeated external calls)"
            ] if not is_available else []
        }


class RedisConnectionManager:
    """Manages Redis connection and availability."""
    
    def __init__(self, redis_url: str, pool_size: int = 50, decode_responses: bool = True):
        self.redis_url = redis_url
        self.pool_size = pool_size
        self.decode_responses = decode_responses
        self.is_available = False
        self.connection_attempted = False
        self._client = None
        self._pool = None
    
    async def create_connection(self):
        """Create Redis connection with error handling."""
        from redis.asyncio import Redis, ConnectionPool
        
        # Skip if already attempted and failed
        if self.connection_attempted and not self.is_available:
            return None
            
        if self._client is None:
            # Check if Redis URL is configured
            if not self.redis_url:
                # Redis not configured
                if not self.connection_attempted:
                    logger.info(
                        "Redis URL not configured (REDIS_URL environment variable not set). "
                        "Running without cache - this will impact performance! "
                        "Set REDIS_URL to enable caching for better performance."
                    )
                    self.connection_attempted = True
                return None
            
            try:
                logger.info("Creating Redis connection pool...")
                
                self._pool = ConnectionPool.from_url(
                    self.redis_url,
                    max_connections=self.pool_size,
                    decode_responses=self.decode_responses,
                    health_check_interval=30
                )
                
                self._client = Redis(connection_pool=self._pool)
                
                # Test connection
                await self._client.ping()
                logger.info("Redis connection established successfully")
                self.is_available = True
                self.connection_attempted = True
                
            except Exception as e:
                logger.warning(
                    f"Redis connection failed: {e}. "
                    "Running without cache - this will impact performance!"
                )
                self.is_available = False
                self.connection_attempted = True
                
                # Clean up failed connection
                await self._cleanup_failed_connection()
                return None
            
        return self._client
    
    async def _cleanup_failed_connection(self):
        """Clean up failed connection attempts."""
        if self._client:
            try:
                await self._client.close()
            except:
                pass
        if self._pool:
            try:
                await self._pool.disconnect()
            except:
                pass
                
        self._client = None
        self._pool = None
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            if self._pool:
                await self._pool.disconnect()
            self._client = None
            self._pool = None
            logger.info("Redis connection closed")
    
    async def health_check(self) -> bool:
        """Check Redis health."""
        try:
            client = await self.create_connection()
            if not client:
                return False
            await client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False