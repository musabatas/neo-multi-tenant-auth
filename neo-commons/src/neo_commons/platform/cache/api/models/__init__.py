"""Cache API models.

Request and response models following maximum separation.
"""

from .requests import *
from .responses import *

__all__ = [
    # Request Models
    "SetCacheRequest",
    "GetCacheRequest",
    "GetMultipleCacheRequest", 
    "DeleteCacheRequest",
    "InvalidateRequest",
    
    # Response Models
    "CacheResponse",
    "CacheEntryResponse",
    "MultipleCacheResponse",
    "CacheStatsResponse",
    "CacheHealthResponse", 
    "OperationResponse",
    "BulkOperationResponse",
]