"""Cache entities - domain objects and protocols."""

from .protocols import Cache, CacheBackend
from .config import CacheSettings, CacheInstanceConfig

__all__ = [
    "Cache",
    "CacheBackend", 
    "CacheSettings",
    "CacheInstanceConfig",
]