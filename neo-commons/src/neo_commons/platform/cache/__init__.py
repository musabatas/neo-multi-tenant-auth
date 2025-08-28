"""Platform cache module.

Enterprise-grade cache management system providing unified caching,
invalidation, and distribution services to all business features.

Following ultra single responsibility architecture and maximum separation
design principles for perfect modularity and testability.
"""

from .core.entities import *
from .core.value_objects import *
from .core.events import *
from .core.exceptions import *
from .core.protocols import *

from .application.commands import *
from .application.queries import *
from .application.validators import *
from .application.handlers import *
from .application.services import *

from .api.models.requests import *  # API request models
from .api.models.responses import *  # API response models
from .api.routers import *  # API routers
from .api.dependencies import *  # API dependencies
# from .api.middleware import *  # TODO: Implement API middleware

__all__ = [
    # Core Domain
    "CacheEntry",
    "CacheNamespace",
    
    # Value Objects
    "CacheKey",
    "CacheTTL", 
    "CachePriority",
    "CacheSize",
    "InvalidationPattern",
    
    # Events
    "CacheHit",
    "CacheMiss",
    "CacheInvalidated",
    "CacheExpired",
    
    # Exceptions
    "CacheKeyInvalid",
    "CacheTimeout",
    "CacheCapacityExceeded",
    
    # Protocols
    "CacheRepository",
    "CacheSerializer",
    "InvalidationService",
    "DistributionService",
    
    # Commands
    "SetCacheEntryCommand",
    "DeleteCacheEntryCommand",
    "InvalidatePatternCommand",
    "FlushNamespaceCommand", 
    "WarmCacheCommand",
    
    # Queries
    "GetCacheEntryQuery",
    "CheckCacheExistsQuery",
    "GetCacheStatsQuery",
    "ListCacheKeysQuery",
    
    # Validators
    "CacheKeyValidator",
    "TTLValidator",
    "SizeValidator",
    
    # Handlers
    "CacheHitHandler",
    "CacheMissHandler",
    "CacheExpiredHandler",
    
    # Services
    "CacheManager",
    "create_cache_manager", 
    "InvalidationServiceImpl",
    "create_invalidation_service",
    "CacheEventPublisher",
    "create_cache_event_publisher",
    "CacheHealthCheckService",
    "create_cache_health_check_service",
    
    # API Models
    "SetCacheRequest",
    "GetCacheRequest",
    "GetMultipleCacheRequest",
    "DeleteCacheRequest", 
    "InvalidateRequest",
    "FlushNamespaceRequest",
    "CacheStatsRequest",
    "CacheResponse",
    "CacheEntryResponse",
    "MultipleCacheResponse",
    "CacheStatsResponse",
    "CacheHealthResponse",
    "OperationResponse",
    "BulkOperationResponse",
    
    # API Routers
    "cache_router",
    # "admin_cache_router",  # TODO: Implement admin router
    # "internal_cache_router",  # TODO: Implement internal router
    
    # Dependencies
    "get_cache_manager",
    "get_event_publisher",
    # "get_cache_service",  # TODO: Implement cache service dependency
    
    # Middleware - TODO: Implement
    # "cache_middleware",
    # "cache_metrics_middleware",
]