"""Cache domain events.

One event per file following maximum separation architecture.
"""

from .cache_hit import CacheHit
from .cache_miss import CacheMiss
from .cache_invalidated import CacheInvalidated
from .cache_expired import CacheExpired

__all__ = [
    "CacheHit",
    "CacheMiss", 
    "CacheInvalidated",
    "CacheExpired",
]