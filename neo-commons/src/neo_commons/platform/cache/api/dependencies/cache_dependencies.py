"""Cache service dependencies.

ONLY cache service dependencies - provides FastAPI dependency injection
for cache services across all business features.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Annotated
from fastapi import Depends

from ....platform.container import get_container, Container
from ...core.protocols.cache_repository import CacheRepository
from ...core.protocols.cache_serializer import CacheSerializer
from ...application.services.cache_manager import CacheManager


async def get_cache_container() -> Container:
    """Get the DI container with cache services."""
    return get_container()


async def get_cache_repository(
    container: Annotated[Container, Depends(get_cache_container)]
) -> CacheRepository:
    """Get cache repository dependency.
    
    This provides the low-level cache repository for direct cache operations.
    Most features should use get_cache_manager instead.
    """
    return await container.get(CacheRepository)


async def get_cache_serializer(
    container: Annotated[Container, Depends(get_cache_container)]
) -> CacheSerializer:
    """Get cache serializer dependency."""
    return await container.get(CacheSerializer)


async def get_cache_manager(
    container: Annotated[Container, Depends(get_cache_container)]
) -> CacheManager:
    """Get cache manager dependency.
    
    This is the main cache service that business features should use.
    Provides high-level cache operations with intelligent defaults.
    
    Usage in feature endpoints:
    
    ```python
    from fastapi import Depends
    from neo_commons.platform.cache.api.dependencies import get_cache_manager
    from neo_commons.platform.cache.application.services.cache_manager import CacheManager
    
    @router.get("/users/{user_id}")
    async def get_user(
        user_id: str,
        cache: CacheManager = Depends(get_cache_manager)
    ):
        # Try cache first
        cached_user = await cache.get_user_cache(user_id, "profile")
        if cached_user:
            return cached_user
        
        # Cache miss - get from database and cache
        user = await database.get_user(user_id)
        await cache.set_user_cache(user_id, "profile", user, ttl_seconds=3600)
        return user
    ```
    """
    return await container.get(CacheManager)


# Convenience alias for the main cache service
async def get_cache_service(
    cache_manager: Annotated[CacheManager, Depends(get_cache_manager)]
) -> CacheManager:
    """Get cache service dependency.
    
    Alias for get_cache_manager - provides the main cache service.
    Use this in your feature endpoints for caching operations.
    """
    return cache_manager


# Type annotations for easier imports
CacheDependency = Annotated[CacheManager, Depends(get_cache_service)]
CacheManagerDependency = Annotated[CacheManager, Depends(get_cache_manager)]
CacheRepositoryDependency = Annotated[CacheRepository, Depends(get_cache_repository)]
CacheSerializerDependency = Annotated[CacheSerializer, Depends(get_cache_serializer)]