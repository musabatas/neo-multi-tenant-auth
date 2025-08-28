"""Cache core domain layer.

Clean core containing only essential value objects, exceptions,
and shared contracts. No business logic or external dependencies.
"""

from .entities import *
from .value_objects import *
from .events import *
from .exceptions import *
from .protocols import *

__all__ = [
    # Entities
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
]