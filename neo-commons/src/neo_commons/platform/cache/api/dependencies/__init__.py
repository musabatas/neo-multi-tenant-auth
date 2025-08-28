"""Cache API dependencies.

Dependency injection for cache services following maximum separation.
"""

from .cache_dependencies import (
    get_cache_service,
    get_cache_manager,
    get_cache_repository,
    get_cache_serializer
)

__all__ = [
    "get_cache_service",
    "get_cache_manager", 
    "get_cache_repository",
    "get_cache_serializer",
]