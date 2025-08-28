"""Cache API routers.

Role-based routers for cross-service usage following maximum separation.
"""

from .cache_router import cache_router
from .admin_cache_router import admin_cache_router
from .internal_cache_router import internal_cache_router

__all__ = [
    "cache_router",           # Public cache operations
    "admin_cache_router",     # Administrative cache operations  
    "internal_cache_router",  # Internal service-to-service operations
]