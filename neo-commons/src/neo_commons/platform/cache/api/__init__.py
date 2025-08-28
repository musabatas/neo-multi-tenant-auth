"""Cache API layer.

Reusable API components for cross-service usage following maximum separation.
"""

# Request/Response Models
from .models.requests import *
from .models.responses import *

# API Dependencies
from .dependencies import *

# API Middleware
from .middleware import *

__all__ = [
    # Request Models
    "SetCacheRequest",
    "GetCacheRequest",
    "InvalidateRequest",
    
    # Response Models
    "CacheResponse",
    "CacheStatsResponse", 
    "CacheHealthResponse",
    
    # Dependencies
    "get_cache_service",
    "get_cache_manager",
    
    # Middleware
    "cache_middleware",
    "cache_metrics_middleware",
]