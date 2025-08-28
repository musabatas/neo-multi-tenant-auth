"""Cache protocol interfaces.

Core contracts following maximum separation - one protocol per file.
"""

from .cache_repository import CacheRepository
from .cache_serializer import CacheSerializer
from .invalidation_service import InvalidationService
from .distribution_service import DistributionService

__all__ = [
    "CacheRepository",
    "CacheSerializer", 
    "InvalidationService",
    "DistributionService",
]