"""Cache domain exceptions.

One exception per file following maximum separation architecture.
"""

from .cache_key_invalid import CacheKeyInvalid
from .cache_timeout import CacheTimeout
from .cache_capacity_exceeded import CacheCapacityExceeded
from .serialization_error import SerializationError
from .deserialization_error import DeserializationError

__all__ = [
    "CacheKeyInvalid",
    "CacheTimeout",
    "CacheCapacityExceeded",
    "SerializationError",
    "DeserializationError",
]