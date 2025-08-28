"""Cache infrastructure layer.

Platform implementations for cache repositories, serializers,
invalidators, and distributors.

Following maximum separation architecture - one implementation per file.
"""

from .repositories import *
from .serializers import *
from .invalidators import *
from .distributors import *
from .configuration import *

__all__ = [
    # Repositories
    "MemoryCacheRepository",
    "create_memory_cache_repository",
    "RedisCacheRepository",
    "create_redis_cache_repository",
    # "DistributedCacheRepository",  # TODO: Implement
    
    # Serializers
    "JSONCacheSerializer",
    "PickleCacheSerializer", 
    "MessagePackCacheSerializer",
    
    # Invalidators
    "PatternInvalidator",
    "create_pattern_invalidator",
    "TimeInvalidator", 
    "create_time_invalidator",
    "EventInvalidator",
    "create_event_invalidator",
    
    # Distributors
    "RedisDistributor",
    "create_redis_distributor",
    "KafkaDistributor",
    "create_kafka_distributor",
    
    # Configuration
    "CacheConfig",
    "create_cache_config",
    "RepositoryConfig",
    "create_repository_config",
    "InvalidationConfig",
    "create_invalidation_config",
    "DistributionConfig",
    "create_distribution_config",
]