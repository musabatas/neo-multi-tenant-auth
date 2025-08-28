"""Cache application event handlers.

Event handling following maximum separation - one handler per event type.
Each handler provides monitoring, alerting, and optimization capabilities.
"""

from .cache_hit_handler import (
    CacheHitHandler,
    CacheHitHandlerResult,
    create_cache_hit_handler,
)
from .cache_miss_handler import (
    CacheMissHandler,
    CacheMissHandlerResult,
    create_cache_miss_handler,
)
from .cache_expired_handler import (
    CacheExpiredHandler,
    CacheExpiredHandlerResult,
    create_cache_expired_handler,
)

__all__ = [
    # Cache hit handling
    "CacheHitHandler",
    "CacheHitHandlerResult",
    "create_cache_hit_handler",
    
    # Cache miss handling  
    "CacheMissHandler",
    "CacheMissHandlerResult",
    "create_cache_miss_handler",
    
    # Cache expired handling
    "CacheExpiredHandler", 
    "CacheExpiredHandlerResult",
    "create_cache_expired_handler",
]