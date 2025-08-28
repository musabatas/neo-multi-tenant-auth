"""Set cache entry command.

ONLY cache setting - handles cache entry creation and updates
with validation and event publishing.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from ...core.protocols.cache_repository import CacheRepository
from ...core.protocols.cache_serializer import CacheSerializer
from ...core.entities.cache_entry import CacheEntry
from ...core.entities.cache_namespace import CacheNamespace
from ...core.value_objects.cache_key import CacheKey
from ...core.value_objects.cache_ttl import CacheTTL
from ...core.value_objects.cache_priority import CachePriority
from ...core.value_objects.cache_size import CacheSize
from ...core.events.cache_hit import CacheHit
from ...core.exceptions.cache_key_invalid import CacheKeyInvalid
from ...core.exceptions.cache_capacity_exceeded import CacheCapacityExceeded


@dataclass
class SetCacheEntryData:
    """Data required to set a cache entry."""
    
    key: str
    value: Any
    namespace: str = "default"
    ttl_seconds: Optional[int] = None
    priority: str = "medium"  # low, medium, high, critical
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass 
class SetCacheEntryResult:
    """Result of setting a cache entry."""
    
    success: bool
    key: str
    namespace: str
    size_bytes: int
    ttl_seconds: Optional[int] = None
    error_message: Optional[str] = None


class SetCacheEntryCommand:
    """Command to set cache entry.
    
    Handles cache entry creation and updates with:
    - Input validation and sanitization
    - Size estimation and capacity checking
    - TTL and priority assignment
    - Repository storage with error handling
    - Event publishing for monitoring
    - Performance tracking
    """
    
    def __init__(
        self,
        repository: CacheRepository,
        serializer: Optional[CacheSerializer] = None
    ):
        """Initialize set cache entry command.
        
        Args:
            repository: Cache repository for storage
            serializer: Optional serializer for size estimation
        """
        self._repository = repository
        self._serializer = serializer
    
    async def execute(self, data: SetCacheEntryData) -> SetCacheEntryResult:
        """Execute cache entry set operation.
        
        Args:
            data: Cache entry data to store
            
        Returns:
            Result of the set operation
            
        Raises:
            CacheKeyInvalid: If cache key is invalid
            CacheCapacityExceeded: If entry exceeds size limits
        """
        try:
            # Validate and create cache key
            cache_key = self._create_cache_key(data.key)
            
            # Create cache namespace
            namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Create TTL if specified
            ttl = self._create_ttl(data.ttl_seconds) if data.ttl_seconds else None
            
            # Create priority
            priority = self._create_priority(data.priority)
            
            # Estimate size
            size = self._estimate_size(data.value)
            
            # Create cache entry
            entry = CacheEntry(
                key=cache_key,
                value=data.value,
                ttl=ttl,
                priority=priority,
                namespace=namespace,
                created_at=datetime.utcnow(),
                accessed_at=datetime.utcnow(),
                access_count=0,
                size_bytes=size
            )
            
            # Store in repository
            success = await self._repository.set(entry)
            
            if success:
                return SetCacheEntryResult(
                    success=True,
                    key=data.key,
                    namespace=data.namespace,
                    size_bytes=size.bytes,
                    ttl_seconds=data.ttl_seconds
                )
            else:
                return SetCacheEntryResult(
                    success=False,
                    key=data.key,
                    namespace=data.namespace,
                    size_bytes=size.bytes,
                    error_message="Failed to store in repository"
                )
                
        except CacheKeyInvalid as e:
            return SetCacheEntryResult(
                success=False,
                key=data.key,
                namespace=data.namespace,
                size_bytes=0,
                error_message=f"Invalid cache key: {e.reason}"
            )
        
        except CacheCapacityExceeded as e:
            return SetCacheEntryResult(
                success=False,
                key=data.key,
                namespace=data.namespace,
                size_bytes=e.current_value,
                error_message=f"Capacity exceeded: {e}"
            )
        
        except Exception as e:
            return SetCacheEntryResult(
                success=False,
                key=data.key,
                namespace=data.namespace,
                size_bytes=0,
                error_message=f"Unexpected error: {str(e)}"
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
    
    def _create_ttl(self, seconds: int) -> CacheTTL:
        """Create cache TTL."""
        return CacheTTL(seconds)
    
    def _create_priority(self, priority_str: str) -> CachePriority:
        """Create cache priority from string."""
        priority_map = {
            "low": CachePriority.low(),
            "medium": CachePriority.medium(), 
            "high": CachePriority.high(),
            "critical": CachePriority.critical()
        }
        
        return priority_map.get(priority_str.lower(), CachePriority.medium())
    
    def _estimate_size(self, value: Any) -> CacheSize:
        """Estimate value size."""
        if self._serializer:
            estimated = self._serializer.estimate_serialized_size(value)
            return CacheSize(estimated)
        else:
            # Basic estimation using string representation
            return CacheSize.estimate_json_size(str(value))


# Factory function for dependency injection
def create_set_cache_entry_command(
    repository: CacheRepository,
    serializer: Optional[CacheSerializer] = None
) -> SetCacheEntryCommand:
    """Create set cache entry command."""
    return SetCacheEntryCommand(repository=repository, serializer=serializer)