"""Main cache router.

ONLY public cache operations - provides standard cache API endpoints
for application use.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from datetime import datetime

# Request/Response models
from ..models.requests.set_cache_request import SetCacheRequest
from ..models.requests.get_cache_request import GetCacheRequest, GetMultipleCacheRequest
from ..models.requests.delete_cache_request import DeleteCacheRequest
from ..models.responses.cache_response import CacheResponse, MultipleCacheResponse, CacheEntryResponse
from ..models.responses.operation_response import OperationResponse

# Dependencies
from ..dependencies.cache_dependencies import get_cache_manager, get_event_publisher

# Services
from ...application.services.cache_manager import CacheManager
from ...application.services.event_publisher import CacheEventPublisher


# Create router with tags for OpenAPI grouping
cache_router = APIRouter(
    prefix="/cache",
    tags=["Cache"],
    responses={404: {"description": "Cache entry not found"}}
)


@cache_router.post(
    "/set",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set cache entry",
    description="Store a value in the cache with optional TTL and metadata"
)
async def set_cache_entry(
    request: SetCacheRequest,
    background_tasks: BackgroundTasks,
    cache_manager: CacheManager = Depends(get_cache_manager),
    event_publisher: CacheEventPublisher = Depends(get_event_publisher)
) -> OperationResponse:
    """Set a cache entry."""
    try:
        start_time = datetime.utcnow()
        
        # Set cache entry
        success = await cache_manager.set(
            key=request.key,
            value=request.value,
            namespace=request.namespace,
            ttl_seconds=request.ttl_seconds,
            priority=request.priority,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            request_id=request.request_id
        )
        
        operation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        if success:
            # Publish cache set event in background
            background_tasks.add_task(
                _publish_cache_set_event,
                event_publisher,
                request,
                operation_time
            )
            
            return OperationResponse(
                success=True,
                message="Cache entry set successfully",
                data={"key": request.key, "namespace": request.namespace},
                request_id=request.request_id,
                operation_time_ms=operation_time
            )
        else:
            return OperationResponse(
                success=False,
                message="Failed to set cache entry",
                data={"key": request.key, "namespace": request.namespace},
                request_id=request.request_id,
                operation_time_ms=operation_time
            )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set cache entry: {str(e)}"
        )


@cache_router.post(
    "/get",
    response_model=CacheResponse,
    summary="Get cache entry",
    description="Retrieve a value from the cache"
)
async def get_cache_entry(
    request: GetCacheRequest,
    background_tasks: BackgroundTasks,
    cache_manager: CacheManager = Depends(get_cache_manager),
    event_publisher: CacheEventPublisher = Depends(get_event_publisher)
) -> CacheResponse:
    """Get a cache entry."""
    try:
        start_time = datetime.utcnow()
        
        # Get cache entry
        value = await cache_manager.get(
            key=request.key,
            namespace=request.namespace,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            request_id=request.request_id
        )
        
        operation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        found = value is not None
        
        # Create entry response
        entry_response = CacheEntryResponse(
            key=request.key,
            value=value,
            found=found,
            lookup_time_ms=operation_time
        )
        
        # Publish cache hit/miss event in background
        background_tasks.add_task(
            _publish_cache_access_event,
            event_publisher,
            request,
            found,
            operation_time,
            len(str(value)) if value else 0
        )
        
        return CacheResponse(
            success=True,
            data=entry_response,
            message="Cache lookup completed" if found else "Cache entry not found",
            request_id=request.request_id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache entry: {str(e)}"
        )


@cache_router.post(
    "/get-multiple",
    response_model=MultipleCacheResponse,
    summary="Get multiple cache entries",
    description="Retrieve multiple values from the cache in a single request"
)
async def get_multiple_cache_entries(
    request: GetMultipleCacheRequest,
    background_tasks: BackgroundTasks,
    cache_manager: CacheManager = Depends(get_cache_manager),
    event_publisher: CacheEventPublisher = Depends(get_event_publisher)
) -> MultipleCacheResponse:
    """Get multiple cache entries."""
    try:
        start_time = datetime.utcnow()
        
        # Get multiple cache entries
        results = await cache_manager.get_many(
            keys=request.keys,
            namespace=request.namespace,
            tenant_id=request.tenant_id
        )
        
        total_lookup_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Create entry responses
        entries = []
        found_count = 0
        
        for key in request.keys:
            value = results.get(key)
            found = value is not None
            if found:
                found_count += 1
            
            entry_response = CacheEntryResponse(
                key=key,
                value=value,
                found=found,
                lookup_time_ms=total_lookup_time / len(request.keys)  # Average time
            )
            entries.append(entry_response)
        
        # Calculate hit rate
        hit_rate = (found_count / len(request.keys)) * 100.0 if request.keys else 0.0
        
        # Publish bulk access events in background
        background_tasks.add_task(
            _publish_bulk_cache_events,
            event_publisher,
            request,
            entries,
            total_lookup_time
        )
        
        return MultipleCacheResponse(
            success=True,
            entries=entries,
            found_count=found_count,
            total_requested=len(request.keys),
            hit_rate_percentage=hit_rate,
            total_lookup_time_ms=total_lookup_time,
            message=f"Retrieved {found_count} out of {len(request.keys)} requested entries",
            request_id=request.request_id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get multiple cache entries: {str(e)}"
        )


@cache_router.delete(
    "/delete",
    response_model=OperationResponse,
    summary="Delete cache entry",
    description="Remove a cache entry"
)
async def delete_cache_entry(
    request: DeleteCacheRequest,
    background_tasks: BackgroundTasks,
    cache_manager: CacheManager = Depends(get_cache_manager),
    event_publisher: CacheEventPublisher = Depends(get_event_publisher)
) -> OperationResponse:
    """Delete a cache entry."""
    try:
        start_time = datetime.utcnow()
        
        # Delete cache entry
        deleted = await cache_manager.delete(
            key=request.key,
            namespace=request.namespace,
            tenant_id=request.tenant_id
        )
        
        operation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Publish cache invalidation event in background
        background_tasks.add_task(
            _publish_cache_delete_event,
            event_publisher,
            request,
            deleted,
            operation_time
        )
        
        return OperationResponse(
            success=True,
            message="Cache entry deleted successfully" if deleted else "Cache entry not found",
            data={"key": request.key, "deleted": deleted, "existed": deleted},
            request_id=request.request_id,
            operation_time_ms=operation_time
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cache entry: {str(e)}"
        )


@cache_router.get(
    "/exists/{namespace}/{key}",
    response_model=OperationResponse,
    summary="Check if cache entry exists",
    description="Check whether a cache entry exists without retrieving the value"
)
async def check_cache_entry_exists(
    namespace: str,
    key: str,
    tenant_id: Optional[str] = None,
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> OperationResponse:
    """Check if a cache entry exists."""
    try:
        start_time = datetime.utcnow()
        
        # Check if cache entry exists
        exists = await cache_manager.exists(
            key=key,
            namespace=namespace,
            tenant_id=tenant_id
        )
        
        operation_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return OperationResponse(
            success=True,
            message="Cache entry exists" if exists else "Cache entry not found",
            data={"key": key, "namespace": namespace, "exists": exists},
            operation_time_ms=operation_time
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check cache entry existence: {str(e)}"
        )


# Background task functions
async def _publish_cache_set_event(
    event_publisher: CacheEventPublisher,
    request: SetCacheRequest,
    operation_time_ms: float
):
    """Publish cache set event."""
    try:
        from ...core.value_objects.cache_key import CacheKey
        from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
        
        cache_key = CacheKey(request.key)
        cache_namespace = CacheNamespace(
            name=request.namespace,
            description=f"Namespace: {request.namespace}",
            default_ttl=None,
            max_entries=10000,
            eviction_policy=EvictionPolicy.LRU,
            tenant_id=request.tenant_id
        )
        
        # For set operations, we publish a custom event or use cache hit
        await event_publisher.publish_cache_hit(
            key=cache_key,
            namespace=cache_namespace,
            lookup_time_ms=operation_time_ms,
            value_size_bytes=request.get_estimated_size(),
            request_id=request.request_id,
            user_id=request.user_id,
            tenant_id=request.tenant_id,
            metadata={"operation": "set", "priority": request.priority}
        )
    except Exception:
        # Silent failure - don't break the main operation
        pass


async def _publish_cache_access_event(
    event_publisher: CacheEventPublisher,
    request: GetCacheRequest,
    found: bool,
    operation_time_ms: float,
    value_size_bytes: int
):
    """Publish cache access event."""
    try:
        from ...core.value_objects.cache_key import CacheKey
        from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
        
        cache_key = CacheKey(request.key)
        cache_namespace = CacheNamespace(
            name=request.namespace,
            description=f"Namespace: {request.namespace}",
            default_ttl=None,
            max_entries=10000,
            eviction_policy=EvictionPolicy.LRU,
            tenant_id=request.tenant_id
        )
        
        if found:
            await event_publisher.publish_cache_hit(
                key=cache_key,
                namespace=cache_namespace,
                lookup_time_ms=operation_time_ms,
                value_size_bytes=value_size_bytes,
                request_id=request.request_id,
                user_id=request.user_id,
                tenant_id=request.tenant_id
            )
        else:
            await event_publisher.publish_cache_miss(
                key=cache_key,
                namespace=cache_namespace,
                lookup_time_ms=operation_time_ms,
                request_id=request.request_id,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                reason="not_found"
            )
    except Exception:
        # Silent failure - don't break the main operation
        pass


async def _publish_bulk_cache_events(
    event_publisher: CacheEventPublisher,
    request: GetMultipleCacheRequest,
    entries: list,
    total_lookup_time_ms: float
):
    """Publish bulk cache access events."""
    try:
        from ...core.value_objects.cache_key import CacheKey
        from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
        
        cache_namespace = CacheNamespace(
            name=request.namespace,
            description=f"Namespace: {request.namespace}",
            default_ttl=None,
            max_entries=10000,
            eviction_policy=EvictionPolicy.LRU,
            tenant_id=request.tenant_id
        )
        
        # Publish events for each entry
        for entry in entries:
            cache_key = CacheKey(entry.key)
            
            if entry.found:
                await event_publisher.publish_cache_hit(
                    key=cache_key,
                    namespace=cache_namespace,
                    lookup_time_ms=entry.lookup_time_ms or 0,
                    value_size_bytes=len(str(entry.value)) if entry.value else 0,
                    request_id=request.request_id,
                    user_id=request.user_id,
                    tenant_id=request.tenant_id,
                    metadata={"operation": "bulk_get"}
                )
            else:
                await event_publisher.publish_cache_miss(
                    key=cache_key,
                    namespace=cache_namespace,
                    lookup_time_ms=entry.lookup_time_ms or 0,
                    request_id=request.request_id,
                    user_id=request.user_id,
                    tenant_id=request.tenant_id,
                    reason="not_found",
                    metadata={"operation": "bulk_get"}
                )
    except Exception:
        # Silent failure - don't break the main operation
        pass


async def _publish_cache_delete_event(
    event_publisher: CacheEventPublisher,
    request: DeleteCacheRequest,
    deleted: bool,
    operation_time_ms: float
):
    """Publish cache delete event."""
    try:
        from ...core.value_objects.cache_key import CacheKey
        from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
        
        cache_key = CacheKey(request.key)
        cache_namespace = CacheNamespace(
            name=request.namespace,
            description=f"Namespace: {request.namespace}",
            default_ttl=None,
            max_entries=10000,
            eviction_policy=EvictionPolicy.LRU,
            tenant_id=request.tenant_id
        )
        
        if deleted:
            await event_publisher.publish_cache_invalidated(
                key=cache_key,
                namespace=cache_namespace,
                invalidation_reason="manual_delete",
                request_id=request.request_id,
                user_id=request.user_id,
                tenant_id=request.tenant_id,
                metadata={"operation": "delete", "operation_time_ms": operation_time_ms}
            )
    except Exception:
        # Silent failure - don't break the main operation
        pass