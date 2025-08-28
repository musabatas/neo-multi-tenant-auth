"""Cache domain entities.

One entity per file following maximum separation architecture.
"""

from .cache_entry import CacheEntry
from .cache_namespace import CacheNamespace

__all__ = [
    "CacheEntry",
    "CacheNamespace",
]