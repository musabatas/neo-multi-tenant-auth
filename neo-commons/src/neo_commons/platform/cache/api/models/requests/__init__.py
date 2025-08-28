"""Cache API request models.

One request model per file following maximum separation.
"""

from .set_cache_request import SetCacheRequest
from .get_cache_request import GetCacheRequest
from .delete_cache_request import DeleteCacheRequest
from .invalidate_request import InvalidateRequest
from .flush_request import FlushNamespaceRequest
from .cache_stats_request import CacheStatsRequest

__all__ = [
    "SetCacheRequest",
    "GetCacheRequest", 
    "DeleteCacheRequest",
    "InvalidateRequest",
    "FlushNamespaceRequest",
    "CacheStatsRequest",
]