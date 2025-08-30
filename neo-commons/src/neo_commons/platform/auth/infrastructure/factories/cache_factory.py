"""Cache factory for authentication platform."""

import logging
from typing import Dict, Any, Optional, Union

from ..repositories import MemoryTokenCache
from ..adapters import RedisCacheAdapter, PublicKeyCacheAdapter
from ...core.exceptions import CacheError

logger = logging.getLogger(__name__)


class CacheFactory:
    """Cache factory following maximum separation principle.
    
    Handles ONLY cache instantiation and configuration for authentication platform.
    Does not handle caching logic, token validation, or authentication operations.
    """
    
    def __init__(self, cache_config: Dict[str, Any]):
        """Initialize cache factory.
        
        Args:
            cache_config: Cache configuration dictionary
        """
        self.config = cache_config or {}
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate cache configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate memory cache settings
        max_size = self.config.get("memory_max_size", 10000)
        if not isinstance(max_size, int) or max_size <= 0:
            raise ValueError("Memory max size must be a positive integer")
        
        # Validate TTL settings
        default_ttl = self.config.get("default_ttl_seconds", 300)
        if not isinstance(default_ttl, int) or default_ttl <= 0:
            raise ValueError("Default TTL must be a positive integer")
        
        # Validate cleanup interval
        cleanup_interval = self.config.get("cleanup_interval_seconds", 60)
        if not isinstance(cleanup_interval, int) or cleanup_interval <= 0:
            raise ValueError("Cleanup interval must be a positive integer")
        
        # Validate memory limit
        max_memory_mb = self.config.get("max_memory_mb", 100)
        if not isinstance(max_memory_mb, (int, float)) or max_memory_mb <= 0:
            raise ValueError("Max memory MB must be a positive number")
        
        logger.debug("Cache factory configuration validated successfully")
    
    async def create_memory_token_cache(
        self,
        max_size: Optional[int] = None,
        default_ttl_seconds: Optional[int] = None,
        cleanup_interval_seconds: Optional[int] = None,
        max_memory_mb: Optional[int] = None
    ) -> MemoryTokenCache:
        """Create memory token cache.
        
        Args:
            max_size: Optional maximum number of cached tokens
            default_ttl_seconds: Optional default TTL for cached tokens
            cleanup_interval_seconds: Optional cleanup interval
            max_memory_mb: Optional maximum memory usage in MB
            
        Returns:
            Configured MemoryTokenCache instance
            
        Raises:
            CacheError: If cache creation fails
        """
        try:
            logger.debug("Creating memory token cache")
            
            # Get configuration
            max_size = max_size or self.config.get("memory_max_size", 10000)
            ttl = default_ttl_seconds or self.config.get("default_ttl_seconds", 300)
            cleanup_interval = cleanup_interval_seconds or self.config.get("cleanup_interval_seconds", 60)
            max_memory = max_memory_mb or self.config.get("max_memory_mb", 100)
            
            cache = MemoryTokenCache(
                max_size=max_size,
                default_ttl_seconds=ttl,
                cleanup_interval_seconds=cleanup_interval,
                max_memory_mb=max_memory
            )
            
            logger.debug(f"Successfully created memory token cache with max_size: {max_size}")
            return cache
            
        except Exception as e:
            logger.error(f"Failed to create memory token cache: {e}")
            raise CacheError(
                "Memory token cache creation failed",
                context={
                    "cache_type": "memory_token",
                    "max_size": max_size,
                    "ttl": default_ttl_seconds,
                    "error": str(e)
                }
            )
    
    async def create_redis_cache_adapter(
        self,
        redis_client,
        key_prefix: Optional[str] = None,
        default_ttl_seconds: Optional[int] = None
    ) -> RedisCacheAdapter:
        """Create Redis cache adapter.
        
        Args:
            redis_client: Redis client instance
            key_prefix: Optional key prefix for cache
            default_ttl_seconds: Optional default TTL
            
        Returns:
            Configured RedisCacheAdapter instance
            
        Raises:
            CacheError: If adapter creation fails
        """
        try:
            logger.debug("Creating Redis cache adapter")
            
            if not redis_client:
                raise ValueError("Redis client is required")
            
            # Get configuration
            prefix = key_prefix or self.config.get("redis_key_prefix", "auth_cache")
            ttl = default_ttl_seconds or self.config.get("default_ttl_seconds", 300)
            
            adapter = RedisCacheAdapter(
                redis_client=redis_client,
                key_prefix=prefix,
                default_ttl_seconds=ttl
            )
            
            logger.debug(f"Successfully created Redis cache adapter with prefix: {prefix}")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create Redis cache adapter: {e}")
            raise CacheError(
                "Redis cache adapter creation failed",
                context={
                    "cache_type": "redis",
                    "key_prefix": key_prefix,
                    "ttl": default_ttl_seconds,
                    "error": str(e)
                }
            )
    
    async def create_public_key_cache_adapter(
        self,
        cache_client,
        default_ttl_seconds: Optional[int] = None,
        key_prefix: Optional[str] = None
    ) -> PublicKeyCacheAdapter:
        """Create public key cache adapter.
        
        Args:
            cache_client: Cache client instance (Redis, Memory, etc.)
            default_ttl_seconds: Optional default TTL for cached keys
            key_prefix: Optional key prefix
            
        Returns:
            Configured PublicKeyCacheAdapter instance
            
        Raises:
            CacheError: If adapter creation fails
        """
        try:
            logger.debug("Creating public key cache adapter")
            
            if not cache_client:
                raise ValueError("Cache client is required")
            
            # Get configuration
            ttl = default_ttl_seconds or self.config.get("public_key_ttl_seconds", 3600)
            prefix = key_prefix or self.config.get("public_key_prefix", "auth_public_key")
            
            adapter = PublicKeyCacheAdapter(
                cache_client=cache_client,
                default_ttl_seconds=ttl,
                key_prefix=prefix
            )
            
            logger.debug(f"Successfully created public key cache adapter with TTL: {ttl}s")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create public key cache adapter: {e}")
            raise CacheError(
                "Public key cache adapter creation failed",
                context={
                    "cache_type": "public_key",
                    "ttl": default_ttl_seconds,
                    "key_prefix": key_prefix,
                    "error": str(e)
                }
            )
    
    async def create_cache_tier(
        self,
        redis_client,
        tier_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create multi-tier cache setup (memory + Redis).
        
        Args:
            redis_client: Redis client for distributed cache
            tier_config: Optional tier configuration
            
        Returns:
            Dictionary with cache tier components
            
        Raises:
            CacheError: If tier creation fails
        """
        try:
            logger.debug("Creating multi-tier cache setup")
            
            if not redis_client:
                raise ValueError("Redis client is required")
            
            config = tier_config or {}
            
            # Create L1 cache (memory)
            memory_config = config.get("memory", {})
            l1_cache = await self.create_memory_token_cache(
                max_size=memory_config.get("max_size"),
                default_ttl_seconds=memory_config.get("ttl_seconds"),
                cleanup_interval_seconds=memory_config.get("cleanup_interval_seconds"),
                max_memory_mb=memory_config.get("max_memory_mb")
            )
            
            # Create L2 cache (Redis)
            redis_config = config.get("redis", {})
            l2_cache = await self.create_redis_cache_adapter(
                redis_client=redis_client,
                key_prefix=redis_config.get("key_prefix"),
                default_ttl_seconds=redis_config.get("ttl_seconds")
            )
            
            # Create public key cache (Redis-backed)
            pubkey_config = config.get("public_key", {})
            pubkey_cache = await self.create_public_key_cache_adapter(
                cache_client=redis_client,
                default_ttl_seconds=pubkey_config.get("ttl_seconds"),
                key_prefix=pubkey_config.get("key_prefix")
            )
            
            tier_setup = {
                "l1_cache": l1_cache,  # Memory cache (fastest)
                "l2_cache": l2_cache,  # Redis cache (distributed)
                "public_key_cache": pubkey_cache,  # Public key cache
                "config": {
                    "tier_strategy": config.get("tier_strategy", "write_through"),
                    "promote_on_hit": config.get("promote_on_hit", True),
                    "l1_write_through": config.get("l1_write_through", True),
                    "l2_write_behind": config.get("l2_write_behind", False),
                    "eviction_policy": config.get("eviction_policy", "lru"),
                    "sync_interval_seconds": config.get("sync_interval_seconds", 30),
                }
            }
            
            logger.debug("Successfully created multi-tier cache setup")
            return tier_setup
            
        except Exception as e:
            logger.error(f"Failed to create cache tier: {e}")
            raise CacheError(
                "Cache tier creation failed",
                context={
                    "tier_config": tier_config,
                    "error": str(e)
                }
            )
    
    async def create_specialized_caches(
        self,
        redis_client,
        specialization_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create specialized caches for different auth components.
        
        Args:
            redis_client: Redis client instance
            specialization_config: Optional configuration for specializations
            
        Returns:
            Dictionary with specialized cache components
            
        Raises:
            CacheError: If specialized cache creation fails
        """
        try:
            logger.debug("Creating specialized authentication caches")
            
            if not redis_client:
                raise ValueError("Redis client is required")
            
            config = specialization_config or {}
            caches = {}
            
            # Token validation cache (short TTL, high frequency)
            token_config = config.get("token_validation", {})
            caches["token_validation"] = await self.create_redis_cache_adapter(
                redis_client=redis_client,
                key_prefix=token_config.get("key_prefix", "auth_token_validation"),
                default_ttl_seconds=token_config.get("ttl_seconds", 300)  # 5 minutes
            )
            
            # User permissions cache (medium TTL, frequent reads)
            permissions_config = config.get("user_permissions", {})
            caches["user_permissions"] = await self.create_redis_cache_adapter(
                redis_client=redis_client,
                key_prefix=permissions_config.get("key_prefix", "auth_user_permissions"),
                default_ttl_seconds=permissions_config.get("ttl_seconds", 900)  # 15 minutes
            )
            
            # Public key cache (long TTL, infrequent updates)
            pubkey_config = config.get("public_keys", {})
            caches["public_keys"] = await self.create_public_key_cache_adapter(
                cache_client=redis_client,
                default_ttl_seconds=pubkey_config.get("ttl_seconds", 3600),  # 1 hour
                key_prefix=pubkey_config.get("key_prefix", "auth_public_keys")
            )
            
            # Session metadata cache (medium TTL, session lifecycle)
            session_config = config.get("session_metadata", {})
            caches["session_metadata"] = await self.create_redis_cache_adapter(
                redis_client=redis_client,
                key_prefix=session_config.get("key_prefix", "auth_session_metadata"),
                default_ttl_seconds=session_config.get("ttl_seconds", 1800)  # 30 minutes
            )
            
            # Rate limiting cache (short TTL, high write frequency)
            ratelimit_config = config.get("rate_limiting", {})
            caches["rate_limiting"] = await self.create_redis_cache_adapter(
                redis_client=redis_client,
                key_prefix=ratelimit_config.get("key_prefix", "auth_rate_limit"),
                default_ttl_seconds=ratelimit_config.get("ttl_seconds", 60)  # 1 minute
            )
            
            # Add configuration metadata
            caches["config"] = {
                "specialization_strategy": config.get("strategy", "by_use_case"),
                "cache_types": list(caches.keys()),
                "total_caches": len(caches) - 1,  # Exclude config itself
                "created_at": logger.debug("Specialized caches created")
            }
            
            logger.debug(f"Successfully created {len(caches)-1} specialized caches")
            return caches
            
        except Exception as e:
            logger.error(f"Failed to create specialized caches: {e}")
            raise CacheError(
                "Specialized caches creation failed",
                context={
                    "specialization_config": specialization_config,
                    "error": str(e)
                }
            )
    
    def create_cache_config(
        self,
        cache_type: str = "hybrid",
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create cache configuration with defaults and overrides.
        
        Args:
            cache_type: Type of cache setup (memory, redis, hybrid, specialized)
            custom_config: Optional custom configuration overrides
            
        Returns:
            Complete cache configuration dictionary
        """
        # Base configuration
        base_config = {
            "cache_type": cache_type,
            "default_ttl_seconds": 300,
            "cleanup_enabled": True,
            "metrics_enabled": True,
            "compression_enabled": False,
            "encryption_enabled": False,
        }
        
        # Type-specific defaults
        if cache_type == "memory":
            type_config = {
                "memory_max_size": 10000,
                "max_memory_mb": 100,
                "cleanup_interval_seconds": 60,
                "eviction_policy": "lru",
            }
        elif cache_type == "redis":
            type_config = {
                "redis_key_prefix": "auth_cache",
                "connection_pool_size": 10,
                "connection_timeout_seconds": 5,
                "retry_on_timeout": True,
                "max_connections": 50,
            }
        elif cache_type == "hybrid":
            type_config = {
                "memory_max_size": 5000,
                "max_memory_mb": 50,
                "cleanup_interval_seconds": 60,
                "redis_key_prefix": "auth_cache",
                "tier_strategy": "write_through",
                "promote_on_hit": True,
            }
        elif cache_type == "specialized":
            type_config = {
                "token_validation": {"ttl_seconds": 300, "key_prefix": "auth_token_validation"},
                "user_permissions": {"ttl_seconds": 900, "key_prefix": "auth_user_permissions"},
                "public_keys": {"ttl_seconds": 3600, "key_prefix": "auth_public_keys"},
                "session_metadata": {"ttl_seconds": 1800, "key_prefix": "auth_session_metadata"},
                "rate_limiting": {"ttl_seconds": 60, "key_prefix": "auth_rate_limit"},
            }
        else:
            type_config = {}
        
        # Merge configurations
        merged_config = {**base_config, **type_config, **self.config}
        
        # Apply custom overrides
        if custom_config:
            merged_config.update(custom_config)
        
        return merged_config
    
    async def validate_cache_setup(
        self,
        redis_client,
        cache_type: str = "hybrid"
    ) -> Dict[str, Any]:
        """Validate cache setup and connectivity.
        
        Args:
            redis_client: Redis client for validation
            cache_type: Type of cache to validate
            
        Returns:
            Dictionary with validation results
            
        Raises:
            CacheError: If validation fails
        """
        try:
            logger.info(f"Validating cache setup for type: {cache_type}")
            
            validation_results = {
                "cache_type": cache_type,
                "redis_connection": False,
                "memory_cache_creation": False,
                "redis_adapter_creation": False,
                "public_key_cache_creation": False,
                "overall_status": False
            }
            
            # Test Redis connection if needed
            if cache_type in ["redis", "hybrid", "specialized"] and redis_client:
                try:
                    await redis_client.ping()
                    validation_results["redis_connection"] = True
                    logger.debug("Redis connection validated successfully")
                except Exception as e:
                    logger.error(f"Redis connection validation failed: {e}")
                    validation_results["redis_error"] = str(e)
            else:
                validation_results["redis_connection"] = True  # Not required
            
            # Test memory cache creation
            if cache_type in ["memory", "hybrid"]:
                try:
                    memory_cache = await self.create_memory_token_cache()
                    validation_results["memory_cache_creation"] = True
                    logger.debug("Memory cache creation validated successfully")
                except Exception as e:
                    logger.error(f"Memory cache creation validation failed: {e}")
                    validation_results["memory_cache_error"] = str(e)
            else:
                validation_results["memory_cache_creation"] = True  # Not required
            
            # Test Redis adapter creation
            if cache_type in ["redis", "hybrid", "specialized"] and validation_results["redis_connection"]:
                try:
                    redis_adapter = await self.create_redis_cache_adapter(redis_client)
                    validation_results["redis_adapter_creation"] = True
                    logger.debug("Redis adapter creation validated successfully")
                except Exception as e:
                    logger.error(f"Redis adapter creation validation failed: {e}")
                    validation_results["redis_adapter_error"] = str(e)
            else:
                validation_results["redis_adapter_creation"] = True  # Not required
            
            # Test public key cache creation
            if validation_results["redis_connection"]:
                try:
                    pubkey_cache = await self.create_public_key_cache_adapter(redis_client)
                    validation_results["public_key_cache_creation"] = True
                    logger.debug("Public key cache creation validated successfully")
                except Exception as e:
                    logger.error(f"Public key cache creation validation failed: {e}")
                    validation_results["public_key_cache_error"] = str(e)
            
            # Overall status
            validation_results["overall_status"] = all([
                validation_results["redis_connection"],
                validation_results["memory_cache_creation"],
                validation_results["redis_adapter_creation"],
                validation_results["public_key_cache_creation"]
            ])
            
            if validation_results["overall_status"]:
                logger.info(f"Cache setup validation completed successfully for type: {cache_type}")
            else:
                logger.warning(f"Cache setup validation completed with errors for type: {cache_type}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Cache setup validation failed: {e}")
            raise CacheError(
                "Cache setup validation failed",
                context={
                    "cache_type": cache_type,
                    "error": str(e)
                }
            )
    
    def get_factory_info(self) -> Dict[str, Any]:
        """Get cache factory information.
        
        Returns:
            Dictionary with factory information
        """
        return {
            "supported_cache_types": ["memory", "redis", "hybrid", "specialized"],
            "supported_adapters": ["memory_token", "redis", "public_key"],
            "tier_support": True,
            "specialization_support": True,
            "validation_support": True,
            "default_configs": {
                cache_type: self.create_cache_config(cache_type) 
                for cache_type in ["memory", "redis", "hybrid", "specialized"]
            },
            "factory_config": dict(self.config)
        }