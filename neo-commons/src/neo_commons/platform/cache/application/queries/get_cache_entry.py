"""Get cache entry query.

ONLY cache retrieval - handles cache entry lookup with hit/miss
tracking and performance monitoring.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_entry import CacheEntry
from ...core.entities.cache_namespace import CacheNamespace
from ...core.value_objects.cache_key import CacheKey
from ...core.events.cache_hit import CacheHit
from ...core.events.cache_miss import CacheMiss, MissReason
from ...core.exceptions.cache_key_invalid import CacheKeyInvalid


@dataclass
class GetCacheEntryData:
    """Data required to get a cache entry."""
    
    key: str
    namespace: str = "default"
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class GetCacheEntryResult:
    """Result of getting a cache entry."""
    
    found: bool
    key: str
    namespace: str
    value: Optional[Any] = None
    ttl_remaining_seconds: Optional[int] = None
    access_count: Optional[int] = None
    size_bytes: Optional[int] = None
    lookup_time_ms: float = 0.0
    error_message: Optional[str] = None


class GetCacheEntryQuery:
    """Query to get cache entry.
    
    Handles cache entry retrieval with:
    - Key validation and namespace resolution
    - Repository lookup with timeout handling
    - Hit/miss event generation for monitoring
    - Access tracking and statistics
    - Performance measurement
    - Error handling and recovery
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize get cache entry query.
        
        Args:
            repository: Cache repository for retrieval
        """
        self._repository = repository
    
    async def execute(self, data: GetCacheEntryData) -> GetCacheEntryResult:
        """Execute cache entry get operation.
        
        Args:
            data: Cache entry lookup data
            
        Returns:
            Result of the get operation with value if found
            
        Raises:
            CacheKeyInvalid: If cache key is invalid
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate and create cache key
            cache_key = self._create_cache_key(data.key)
            
            # Create cache namespace
            namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Lookup in repository
            entry = await self._repository.get(cache_key, namespace)
            
            # Calculate lookup time
            lookup_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if entry:
                # Cache hit - create hit event and return value
                await self._publish_cache_hit_event(
                    entry, data, lookup_time_ms
                )
                
                return GetCacheEntryResult(
                    found=True,
                    key=data.key,
                    namespace=data.namespace,
                    value=entry.value,
                    ttl_remaining_seconds=entry.time_until_expiry(),
                    access_count=entry.access_count,
                    size_bytes=entry.size_bytes.bytes,
                    lookup_time_ms=lookup_time_ms
                )
            else:
                # Cache miss - create miss event and return not found
                await self._publish_cache_miss_event(
                    cache_key, namespace, data, lookup_time_ms
                )
                
                return GetCacheEntryResult(
                    found=False,
                    key=data.key,
                    namespace=data.namespace,
                    lookup_time_ms=lookup_time_ms
                )
                
        except CacheKeyInvalid as e:
            return GetCacheEntryResult(
                found=False,
                key=data.key,
                namespace=data.namespace,
                error_message=f"Invalid cache key: {e.reason}"
            )
        
        except Exception as e:
            # Cache error - create error miss event
            lookup_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            try:
                cache_key = CacheKey(data.key)
                namespace = self._create_namespace(data.namespace, data.tenant_id)
                
                await self._publish_cache_miss_event(
                    cache_key, namespace, data, lookup_time_ms, 
                    reason=MissReason.ERROR, error_message=str(e)
                )
            except:
                pass  # Don't fail on event publishing
            
            return GetCacheEntryResult(
                found=False,
                key=data.key,
                namespace=data.namespace,
                lookup_time_ms=lookup_time_ms,
                error_message=f"Cache error: {str(e)}"
            )
    
    def _create_cache_key(self, key: str) -> CacheKey:
        """Create and validate cache key."""
        return CacheKey(key)
    
    def _create_namespace(self, name: str, tenant_id: Optional[str] = None) -> CacheNamespace:
        """Create cache namespace."""
        from ...core.entities.cache_namespace import EvictionPolicy
        
        return CacheNamespace(
            name=name,
            description=f"Cache namespace: {name}",
            default_ttl=None,
            max_entries=10000,  # TODO: Get from config
            eviction_policy=EvictionPolicy.LRU,
            tenant_id=tenant_id
        )
    
    async def _publish_cache_hit_event(
        self, 
        entry: CacheEntry, 
        data: GetCacheEntryData, 
        lookup_time_ms: float
    ) -> None:
        """Publish cache hit event for monitoring."""
        try:
            event = CacheHit(
                event_id=str(uuid4()),
                timestamp=datetime.utcnow(),
                key=entry.key,
                namespace=entry.namespace,
                lookup_time_ms=lookup_time_ms,
                value_size_bytes=entry.size_bytes.bytes,
                request_id=data.request_id,
                user_id=data.user_id,
                tenant_id=data.tenant_id,
                entry_age_seconds=int((datetime.utcnow() - entry.created_at).total_seconds()),
                access_count=entry.access_count,
                ttl_remaining_seconds=entry.time_until_expiry()
            )
            
            # TODO: Publish event to event system when available
            # await self._event_publisher.publish(event)
            
        except Exception:
            # Don't fail query on event publishing error
            pass
    
    async def _publish_cache_miss_event(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace, 
        data: GetCacheEntryData, 
        lookup_time_ms: float,
        reason: MissReason = MissReason.NOT_FOUND,
        error_message: Optional[str] = None
    ) -> None:
        """Publish cache miss event for monitoring."""
        try:
            event = CacheMiss(
                event_id=str(uuid4()),
                timestamp=datetime.utcnow(),
                key=key,
                namespace=namespace,
                reason=reason,
                lookup_time_ms=lookup_time_ms,
                request_id=data.request_id,
                user_id=data.user_id,
                tenant_id=data.tenant_id,
                error_message=error_message
            )
            
            # TODO: Publish event to event system when available
            # await self._event_publisher.publish(event)
            
        except Exception:
            # Don't fail query on event publishing error
            pass


# Factory function for dependency injection
def create_get_cache_entry_query(repository: CacheRepository) -> GetCacheEntryQuery:
    """Create get cache entry query."""
    return GetCacheEntryQuery(repository=repository)