"""Cache module registration and dependency injection.

Module registration for cache infrastructure with maximum separation
and protocol-based dependency injection.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Dict, Any, Optional

from ...platform.module import Module
from ...platform.container import Container

# Import protocols for DI registration
from .core.protocols.cache_repository import CacheRepository
from .core.protocols.cache_serializer import CacheSerializer
from .core.protocols.invalidation_service import InvalidationService
from .core.protocols.distribution_service import DistributionService

# Import configuration system
from .infrastructure.configuration import (
    CacheConfig, create_cache_config,
    RepositoryConfig, create_repository_config,
    InvalidationConfig, create_invalidation_config,
    DistributionConfig, create_distribution_config
)


class CacheModule(Module):
    """Cache module with dependency injection support.
    
    Provides:
    - Cache repository implementations (Redis, Memory, Distributed)
    - Serialization services (JSON, Pickle, MessagePack)
    - Invalidation services (Pattern-based, Event-driven)
    - Distribution services (Pub/Sub, Replication)
    - Cache manager and orchestration services
    - Configuration management system
    """
    
    def __init__(
        self,
        cache_config: Optional[CacheConfig] = None,
        repository_config: Optional[RepositoryConfig] = None,
        invalidation_config: Optional[InvalidationConfig] = None,
        distribution_config: Optional[DistributionConfig] = None
    ):
        """Initialize cache module with configuration.
        
        Args:
            cache_config: Main cache configuration
            repository_config: Repository-specific configuration
            invalidation_config: Invalidation-specific configuration
            distribution_config: Distribution-specific configuration
        """
        self._cache_config = cache_config or create_cache_config()
        self._repository_config = repository_config or create_repository_config()
        self._invalidation_config = invalidation_config or create_invalidation_config()
        self._distribution_config = distribution_config or create_distribution_config()
    
    def get_name(self) -> str:
        """Get module name."""
        return "cache"
    
    def get_version(self) -> str:
        """Get module version."""
        return "1.0.0"
    
    def get_dependencies(self) -> list[str]:
        """Get module dependencies."""
        return ["database", "events"]  # Depends on database and events modules
    
    def configure_services(self, container: Container) -> None:
        """Configure cache services in DI container."""
        
        # Register configuration instances
        self._register_configurations(container)
        
        # Register cache repository implementations
        self._register_repositories(container)
        
        # Register serialization services
        self._register_serializers(container)
        
        # Register invalidation services
        self._register_invalidation_services(container)
        
        # Register distribution services
        self._register_distribution_services(container)
        
        # Register application services
        self._register_application_services(container)
        
        # Register API components
        self._register_api_components(container)
    
    def _register_configurations(self, container: Container) -> None:
        """Register configuration instances in DI container."""
        
        # Register individual configuration instances
        container.register_instance(CacheConfig, self._cache_config)
        container.register_instance(RepositoryConfig, self._repository_config) 
        container.register_instance(InvalidationConfig, self._invalidation_config)
        container.register_instance(DistributionConfig, self._distribution_config)
        
        # Register configuration factory functions for dynamic creation
        container.register_factory(
            "cache_config_factory",
            lambda: create_cache_config(
                source="environment",
                overrides=self._cache_config.to_dict()
            )
        )
    
    def _register_repositories(self, container: Container) -> None:
        """Register cache repository implementations."""
        
        # Default Redis repository
        container.register(
            CacheRepository,
            lambda: self._create_redis_repository(container),
            singleton=True
        )
        
        # Named repository implementations
        container.register_named(
            "redis_cache_repository",
            CacheRepository,
            lambda: self._create_redis_repository(container),
            singleton=True
        )
        
        container.register_named(
            "memory_cache_repository", 
            CacheRepository,
            lambda: self._create_memory_repository(container),
            singleton=True
        )
        
        container.register_named(
            "distributed_cache_repository",
            CacheRepository,
            lambda: self._create_distributed_repository(container),
            singleton=True
        )
    
    def _register_serializers(self, container: Container) -> None:
        """Register cache serializer implementations."""
        
        # Default JSON serializer
        container.register(
            CacheSerializer,
            lambda: self._create_json_serializer(),
            singleton=True
        )
        
        # Named serializer implementations
        container.register_named(
            "json_serializer",
            CacheSerializer,
            lambda: self._create_json_serializer(),
            singleton=True
        )
        
        container.register_named(
            "pickle_serializer",
            CacheSerializer,
            lambda: self._create_pickle_serializer(),
            singleton=True
        )
        
        container.register_named(
            "msgpack_serializer",
            CacheSerializer,
            lambda: self._create_msgpack_serializer(),
            singleton=True
        )
    
    def _register_invalidation_services(self, container: Container) -> None:
        """Register cache invalidation services."""
        
        container.register(
            InvalidationService,
            lambda: self._create_invalidation_service(container),
            singleton=True
        )
    
    def _register_distribution_services(self, container: Container) -> None:
        """Register cache distribution services."""
        
        # Default Redis distribution service
        container.register(
            DistributionService,
            lambda: self._create_redis_distributor(container),
            singleton=True
        )
        
        # Named distribution implementations
        container.register_named(
            "redis_distributor",
            DistributionService,
            lambda: self._create_redis_distributor(container),
            singleton=True
        )
        
        container.register_named(
            "kafka_distributor",
            DistributionService,
            lambda: self._create_kafka_distributor(container),
            singleton=True
        )
    
    def _register_application_services(self, container: Container) -> None:
        """Register application layer services."""
        
        from .application.services.cache_manager import CacheManager, create_cache_manager
        from .application.services.invalidation_service import create_invalidation_service
        from .application.services.event_publisher import CacheEventPublisher, create_cache_event_publisher
        from .application.services.health_check_service import CacheHealthCheckService, create_cache_health_check_service
        
        # Cache manager - main orchestration service
        container.register(
            CacheManager,
            lambda: create_cache_manager(
                repository=container.get(CacheRepository),
                serializer=container.get(CacheSerializer),
                invalidation_service=container.get(InvalidationService),
                distribution_service=container.get(DistributionService)
            ),
            singleton=True
        )
        
        # Invalidation orchestration service
        container.register_named(
            "invalidation_orchestration_service",
            lambda: create_invalidation_service(
                repository=container.get(CacheRepository),
                distribution_service=container.get(DistributionService)
            ),
            singleton=True
        )
        
        # Event publisher service
        container.register(
            CacheEventPublisher,
            lambda: create_cache_event_publisher(
                event_publisher=None,  # TODO: Inject from events module when available
                batch_size=self._cache_config.event_batch_size,
                flush_interval_seconds=self._cache_config.event_flush_interval,
                enable_metrics=True
            ),
            singleton=True
        )
        
        # Health check service
        container.register(
            CacheHealthCheckService,
            lambda: create_cache_health_check_service(
                cache_repository=container.get(CacheRepository),
                cache_serializer=container.get(CacheSerializer),
                invalidation_service=container.get(InvalidationService),
                distribution_service=container.get(DistributionService),
                event_publisher=container.get(CacheEventPublisher),
                timeout_seconds=self._cache_config.health_check_timeout_seconds
            ),
            singleton=True
        )
    
    def _register_api_components(self, container: Container) -> None:
        """Register API layer components."""
        
        from .api.dependencies.cache_dependencies import (
            get_cache_service,
            get_cache_manager,
            get_invalidation_service
        )
        
        # Register dependency factories
        container.register_named(
            "cache_service_factory",
            lambda: lambda: container.get(CacheManager)
        )
        
        container.register_named(
            "cache_manager_factory", 
            lambda: lambda: container.get(CacheManager)
        )
        
        container.register_named(
            "invalidation_service_factory",
            lambda: lambda: container.get(InvalidationService)
        )
    
    def _create_redis_repository(self, container: Container) -> CacheRepository:
        """Create Redis cache repository implementation."""
        from .infrastructure.repositories.redis_cache_repository import create_redis_cache_repository
        
        # TODO: Get Redis client from container when Redis module is available
        # For now, create a mock Redis client placeholder
        redis_client = None  # This would be injected from Redis service
        
        return create_redis_cache_repository(
            redis_client=redis_client,
            key_prefix="cache:"
        )
    
    def _create_memory_repository(self, container: Container) -> CacheRepository:
        """Create in-memory cache repository implementation."""
        from .infrastructure.repositories.memory_cache_repository import MemoryCacheRepository
        
        return MemoryCacheRepository(
            max_entries=self._repository_config.memory_max_entries,
            max_memory_mb=self._repository_config.memory_max_memory_mb
        )
    
    def _create_distributed_repository(self, container: Container) -> CacheRepository:
        """Create distributed cache repository implementation."""
        from .infrastructure.repositories.distributed_cache_repository import DistributedCacheRepository
        
        return DistributedCacheRepository(
            primary_repository=self._create_redis_repository(container),
            distribution_service=container.get(DistributionService)
        )
    
    def _create_json_serializer(self) -> CacheSerializer:
        """Create JSON cache serializer."""
        from .infrastructure.serializers.json_serializer import JsonSerializer
        return JsonSerializer()
    
    def _create_pickle_serializer(self) -> CacheSerializer:
        """Create pickle cache serializer."""
        from .infrastructure.serializers.pickle_serializer import PickleSerializer
        return PickleSerializer()
    
    def _create_msgpack_serializer(self) -> CacheSerializer:
        """Create MessagePack cache serializer."""
        from .infrastructure.serializers.msgpack_serializer import MsgPackSerializer
        return MsgPackSerializer()
    
    def _create_invalidation_service(self, container: Container) -> InvalidationService:
        """Create cache invalidation service."""
        from .infrastructure.invalidators.pattern_invalidator import PatternInvalidator
        
        return PatternInvalidator(
            repository=container.get(CacheRepository),
            distribution_service=container.get(DistributionService)
        )
    
    def _create_redis_distributor(self, container: Container) -> DistributionService:
        """Create Redis distribution service."""
        from .infrastructure.distributors.redis_distributor import RedisDistributor
        
        # TODO: Get Redis client from container when Redis module is available
        # For now, create a mock Redis client placeholder
        redis_client = None  # This would be injected from Redis service
        
        return RedisDistributor(
            redis_client=redis_client,
            node_id=self._distribution_config.node_id,
            cluster_name=self._distribution_config.cluster_name
        )
    
    def _create_kafka_distributor(self, container: Container) -> DistributionService:
        """Create Kafka distribution service."""
        from .infrastructure.distributors.kafka_distributor import create_kafka_distributor
        
        kafka_config = self._distribution_config.get_kafka_config()
        
        return create_kafka_distributor(
            kafka_producer=None,  # Would be injected from Kafka module
            kafka_consumer=None,  # Would be injected from Kafka module  
            node_id=self._distribution_config.node_id,
            cluster_name=self._distribution_config.cluster_name
        )
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get module configuration schema."""
        return {
            "cache": {
                "default_repository": {
                    "type": "string",
                    "default": "redis",
                    "enum": ["redis", "memory", "distributed"]
                },
                "default_serializer": {
                    "type": "string", 
                    "default": "json",
                    "enum": ["json", "pickle", "msgpack"]
                },
                "redis": {
                    "connection_name": {
                        "type": "string",
                        "default": "redis"
                    },
                    "key_prefix": {
                        "type": "string", 
                        "default": "cache:"
                    },
                    "channel_prefix": {
                        "type": "string",
                        "default": "cache:"
                    }
                },
                "memory": {
                    "max_entries": {
                        "type": "integer",
                        "default": 10000,
                        "minimum": 100
                    },
                    "max_memory_mb": {
                        "type": "integer",
                        "default": 100,
                        "minimum": 10
                    }
                },
                "invalidation": {
                    "enable_distributed": {
                        "type": "boolean",
                        "default": True
                    },
                    "enable_event_driven": {
                        "type": "boolean", 
                        "default": True
                    }
                }
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform module health check."""
        # This would be implemented to check cache repository, serializers, etc.
        return {
            "module": self.get_name(),
            "version": self.get_version(),
            "status": "healthy",  # TODO: Implement actual health checks
            "components": {
                "repository": "healthy",
                "serializer": "healthy", 
                "invalidation_service": "healthy",
                "distribution_service": "healthy"
            }
        }


# Module instance for registration
cache_module = CacheModule()