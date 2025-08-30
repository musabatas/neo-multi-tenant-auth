"""Session manager factory for authentication platform."""

import logging
from typing import Dict, Any, Optional

from ..repositories import RedisSessionRepository
from ..adapters import RedisCacheAdapter
from ...core.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class SessionManagerFactory:
    """Session manager factory following maximum separation principle.
    
    Handles ONLY session manager instantiation and configuration for authentication platform.
    Does not handle session management logic, authentication, or caching operations.
    """
    
    def __init__(self, session_config: Dict[str, Any]):
        """Initialize session manager factory.
        
        Args:
            session_config: Session manager configuration dictionary
        """
        self.config = session_config or {}
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate session manager configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate session timeout
        timeout = self.config.get("session_timeout_seconds", 3600)
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("Session timeout must be a positive integer")
        
        # Validate cleanup interval
        cleanup_interval = self.config.get("cleanup_interval_seconds", 300)
        if not isinstance(cleanup_interval, int) or cleanup_interval <= 0:
            raise ValueError("Cleanup interval must be a positive integer")
        
        # Validate key prefix
        key_prefix = self.config.get("key_prefix", "auth_session")
        if not isinstance(key_prefix, str) or not key_prefix:
            raise ValueError("Key prefix must be a non-empty string")
        
        logger.debug("Session manager configuration validated successfully")
    
    async def create_redis_session_repository(
        self,
        redis_client,
        key_prefix: Optional[str] = None
    ) -> RedisSessionRepository:
        """Create Redis session repository.
        
        Args:
            redis_client: Redis client instance
            key_prefix: Optional key prefix for sessions
            
        Returns:
            Configured RedisSessionRepository instance
            
        Raises:
            AuthenticationFailed: If repository creation fails
        """
        try:
            logger.debug("Creating Redis session repository")
            
            if not redis_client:
                raise ValueError("Redis client is required")
            
            # Get configuration
            prefix = key_prefix or self.config.get("key_prefix", "auth_session")
            
            repository = RedisSessionRepository(redis_client, prefix)
            
            logger.debug(f"Successfully created Redis session repository with prefix: {prefix}")
            return repository
            
        except Exception as e:
            logger.error(f"Failed to create Redis session repository: {e}")
            raise AuthenticationFailed(
                "Redis session repository creation failed",
                reason="session_repository_creation_failed",
                context={
                    "repository_type": "redis",
                    "key_prefix": key_prefix,
                    "error": str(e)
                }
            )
    
    async def create_session_cache_adapter(
        self,
        cache_client,
        key_prefix: Optional[str] = None,
        default_ttl_seconds: Optional[int] = None
    ) -> RedisCacheAdapter:
        """Create session cache adapter.
        
        Args:
            cache_client: Cache client instance (Redis, etc.)
            key_prefix: Optional key prefix for cache
            default_ttl_seconds: Optional default TTL
            
        Returns:
            Configured cache adapter instance
            
        Raises:
            AuthenticationFailed: If adapter creation fails
        """
        try:
            logger.debug("Creating session cache adapter")
            
            if not cache_client:
                raise ValueError("Cache client is required")
            
            # Get configuration
            prefix = key_prefix or self.config.get("cache_key_prefix", "auth_session_cache")
            ttl = default_ttl_seconds or self.config.get("cache_ttl_seconds", 300)
            
            adapter = RedisCacheAdapter(
                redis_client=cache_client,
                key_prefix=prefix,
                default_ttl_seconds=ttl
            )
            
            logger.debug(f"Successfully created session cache adapter with prefix: {prefix}")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to create session cache adapter: {e}")
            raise AuthenticationFailed(
                "Session cache adapter creation failed",
                reason="session_cache_creation_failed",
                context={
                    "adapter_type": "redis",
                    "key_prefix": key_prefix,
                    "ttl": default_ttl_seconds,
                    "error": str(e)
                }
            )
    
    async def create_session_manager_components(
        self,
        redis_client,
        cache_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create complete session manager components.
        
        Args:
            redis_client: Redis client for session storage
            cache_client: Optional cache client (uses redis_client if None)
            
        Returns:
            Dictionary with session manager components
            
        Raises:
            AuthenticationFailed: If component creation fails
        """
        try:
            logger.debug("Creating complete session manager components")
            
            if not redis_client:
                raise ValueError("Redis client is required")
            
            # Use Redis client for cache if no separate cache client provided
            cache_client = cache_client or redis_client
            
            components = {}
            
            # Create session repository
            session_prefix = self.config.get("key_prefix", "auth_session")
            components["repository"] = await self.create_redis_session_repository(
                redis_client, session_prefix
            )
            
            # Create session cache adapter
            cache_prefix = self.config.get("cache_key_prefix", "auth_session_cache")
            cache_ttl = self.config.get("cache_ttl_seconds", 300)
            components["cache"] = await self.create_session_cache_adapter(
                cache_client, cache_prefix, cache_ttl
            )
            
            # Add configuration info
            components["config"] = {
                "session_timeout_seconds": self.config.get("session_timeout_seconds", 3600),
                "cleanup_interval_seconds": self.config.get("cleanup_interval_seconds", 300),
                "key_prefix": session_prefix,
                "cache_key_prefix": cache_prefix,
                "cache_ttl_seconds": cache_ttl,
                "max_sessions_per_user": self.config.get("max_sessions_per_user", 10),
                "enable_session_tracking": self.config.get("enable_session_tracking", True),
            }
            
            logger.debug("Successfully created complete session manager components")
            return components
            
        except Exception as e:
            logger.error(f"Failed to create session manager components: {e}")
            raise AuthenticationFailed(
                "Session manager components creation failed",
                reason="session_components_creation_failed",
                context={"error": str(e)}
            )
    
    async def create_session_cleanup_manager(
        self,
        session_repository: RedisSessionRepository,
        cleanup_interval_seconds: Optional[int] = None,
        batch_size: Optional[int] = None
    ) -> 'SessionCleanupManager':
        """Create session cleanup manager.
        
        Args:
            session_repository: Session repository instance
            cleanup_interval_seconds: Optional cleanup interval
            batch_size: Optional batch size for cleanup operations
            
        Returns:
            Configured session cleanup manager
            
        Raises:
            AuthenticationFailed: If cleanup manager creation fails
        """
        try:
            logger.debug("Creating session cleanup manager")
            
            if not session_repository:
                raise ValueError("Session repository is required")
            
            # Get configuration
            interval = cleanup_interval_seconds or self.config.get("cleanup_interval_seconds", 300)
            batch_size = batch_size or self.config.get("cleanup_batch_size", 100)
            
            # Create cleanup manager (placeholder implementation)
            cleanup_manager = {
                "repository": session_repository,
                "cleanup_interval_seconds": interval,
                "batch_size": batch_size,
                "enabled": self.config.get("enable_cleanup", True),
                "max_cleanup_time_seconds": self.config.get("max_cleanup_time_seconds", 30),
            }
            
            logger.debug(f"Successfully created session cleanup manager with interval: {interval}s")
            return cleanup_manager
            
        except Exception as e:
            logger.error(f"Failed to create session cleanup manager: {e}")
            raise AuthenticationFailed(
                "Session cleanup manager creation failed",
                reason="cleanup_manager_creation_failed",
                context={
                    "interval": cleanup_interval_seconds,
                    "batch_size": batch_size,
                    "error": str(e)
                }
            )
    
    def create_session_config(
        self,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create session configuration with defaults and overrides.
        
        Args:
            custom_config: Optional custom configuration overrides
            
        Returns:
            Complete session configuration dictionary
        """
        # Default configuration
        default_config = {
            "session_timeout_seconds": 3600,  # 1 hour
            "cleanup_interval_seconds": 300,  # 5 minutes
            "key_prefix": "auth_session",
            "cache_key_prefix": "auth_session_cache",
            "cache_ttl_seconds": 300,  # 5 minutes
            "max_sessions_per_user": 10,
            "enable_session_tracking": True,
            "enable_cleanup": True,
            "cleanup_batch_size": 100,
            "max_cleanup_time_seconds": 30,
            "session_id_length": 32,
            "secure_session_ids": True,
            "track_ip_address": True,
            "track_user_agent": True,
            "enable_concurrent_sessions": True,
            "max_idle_time_seconds": 1800,  # 30 minutes
        }
        
        # Merge with factory config
        merged_config = {**default_config, **self.config}
        
        # Apply custom overrides
        if custom_config:
            merged_config.update(custom_config)
        
        return merged_config
    
    async def validate_session_setup(
        self,
        redis_client,
        cache_client: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Validate session manager setup and connectivity.
        
        Args:
            redis_client: Redis client for validation
            cache_client: Optional cache client for validation
            
        Returns:
            Dictionary with validation results
            
        Raises:
            AuthenticationFailed: If validation fails
        """
        try:
            logger.info("Validating session manager setup")
            
            validation_results = {
                "redis_connection": False,
                "cache_connection": False,
                "repository_creation": False,
                "cache_adapter_creation": False,
                "overall_status": False
            }
            
            # Test Redis connection
            try:
                await redis_client.ping()
                validation_results["redis_connection"] = True
                logger.debug("Redis connection validated successfully")
            except Exception as e:
                logger.error(f"Redis connection validation failed: {e}")
                validation_results["redis_error"] = str(e)
            
            # Test cache connection (if different from Redis)
            if cache_client and cache_client != redis_client:
                try:
                    await cache_client.ping()
                    validation_results["cache_connection"] = True
                    logger.debug("Cache connection validated successfully")
                except Exception as e:
                    logger.error(f"Cache connection validation failed: {e}")
                    validation_results["cache_error"] = str(e)
            else:
                validation_results["cache_connection"] = validation_results["redis_connection"]
            
            # Test repository creation
            if validation_results["redis_connection"]:
                try:
                    repository = await self.create_redis_session_repository(redis_client)
                    validation_results["repository_creation"] = True
                    logger.debug("Session repository creation validated successfully")
                except Exception as e:
                    logger.error(f"Session repository creation validation failed: {e}")
                    validation_results["repository_error"] = str(e)
            
            # Test cache adapter creation
            if validation_results["cache_connection"]:
                try:
                    cache_client = cache_client or redis_client
                    adapter = await self.create_session_cache_adapter(cache_client)
                    validation_results["cache_adapter_creation"] = True
                    logger.debug("Session cache adapter creation validated successfully")
                except Exception as e:
                    logger.error(f"Session cache adapter creation validation failed: {e}")
                    validation_results["cache_adapter_error"] = str(e)
            
            # Overall status
            validation_results["overall_status"] = all([
                validation_results["redis_connection"],
                validation_results["cache_connection"],
                validation_results["repository_creation"],
                validation_results["cache_adapter_creation"]
            ])
            
            if validation_results["overall_status"]:
                logger.info("Session manager setup validation completed successfully")
            else:
                logger.warning("Session manager setup validation completed with errors")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Session manager setup validation failed: {e}")
            raise AuthenticationFailed(
                "Session manager setup validation failed",
                reason="setup_validation_failed",
                context={"error": str(e)}
            )
    
    def get_factory_info(self) -> Dict[str, Any]:
        """Get session manager factory information.
        
        Returns:
            Dictionary with factory information
        """
        return {
            "supported_repositories": ["redis"],
            "supported_cache_adapters": ["redis"],
            "default_config": self.create_session_config(),
            "factory_config": dict(self.config),
            "validation_supported": True,
            "cleanup_manager_supported": True,
        }