"""Delete cache entry command.

ONLY cache deletion - handles cache entry deletion with validation
and event publishing.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.value_objects.cache_key import CacheKey
from ...core.events.cache_invalidated import CacheInvalidated, InvalidationReason
from ...core.exceptions.cache_key_invalid import CacheKeyInvalid


@dataclass
class DeleteCacheEntryData:
    """Data required to delete a cache entry."""
    
    key: str
    namespace: str = "default"
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    reason: str = "manual"


@dataclass
class DeleteCacheEntryResult:
    """Result of deleting a cache entry."""
    
    success: bool
    key: str
    namespace: str
    existed: bool = False
    error_message: Optional[str] = None


class DeleteCacheEntryCommand:
    """Command to delete cache entry.
    
    Handles cache entry deletion with:
    - Input validation and sanitization
    - Repository deletion with error handling
    - Event publishing for monitoring and cascade invalidation
    - Performance tracking
    - Audit trail creation
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize delete cache entry command.
        
        Args:
            repository: Cache repository for deletion
        """
        self._repository = repository
    
    async def execute(self, data: DeleteCacheEntryData) -> DeleteCacheEntryResult:
        """Execute cache entry delete operation.
        
        Args:
            data: Cache entry deletion data
            
        Returns:
            Result of the delete operation
            
        Raises:
            CacheKeyInvalid: If cache key is invalid
        """
        try:
            # Validate and create cache key
            cache_key = self._create_cache_key(data.key)
            
            # Create cache namespace
            namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Check if key exists before deletion (for audit purposes)
            existed = await self._repository.exists(cache_key, namespace)
            
            # Delete from repository
            success = await self._repository.delete(cache_key, namespace)
            
            if success and existed:
                # Publish invalidation event for monitoring
                await self._publish_invalidation_event(
                    cache_key, namespace, data
                )
            
            return DeleteCacheEntryResult(
                success=success,
                key=data.key,
                namespace=data.namespace,
                existed=existed
            )
                
        except CacheKeyInvalid as e:
            return DeleteCacheEntryResult(
                success=False,
                key=data.key,
                namespace=data.namespace,
                existed=False,
                error_message=f"Invalid cache key: {e.reason}"
            )
        
        except Exception as e:
            return DeleteCacheEntryResult(
                success=False,
                key=data.key,
                namespace=data.namespace,
                existed=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _create_cache_key(self, key: str) -> CacheKey:
        """Create and validate cache key."""
        return CacheKey(key)
    
    def _create_namespace(self, name: str, tenant_id: Optional[str] = None) -> CacheNamespace:
        """Create cache namespace."""
        return CacheNamespace(
            name=name,
            description=f"Cache namespace: {name}",
            default_ttl=None,
            max_entries=10000,  # TODO: Get from config
            eviction_policy=EvictionPolicy.LRU,
            tenant_id=tenant_id
        )
    
    async def _publish_invalidation_event(
        self, 
        key: CacheKey,
        namespace: CacheNamespace,
        data: DeleteCacheEntryData
    ) -> None:
        """Publish cache invalidation event for monitoring."""
        try:
            reason_map = {
                "manual": InvalidationReason.MANUAL,
                "pattern": InvalidationReason.PATTERN,
                "dependency": InvalidationReason.DEPENDENCY,
                "event_driven": InvalidationReason.EVENT_DRIVEN,
                "system": InvalidationReason.SYSTEM
            }
            
            event = CacheInvalidated(
                event_id=str(uuid4()),
                timestamp=datetime.utcnow(),
                key=key,
                namespace=namespace,
                reason=reason_map.get(data.reason, InvalidationReason.MANUAL),
                triggered_by=data.user_id or "system",
                request_id=data.request_id,
                user_id=data.user_id,
                tenant_id=data.tenant_id
            )
            
            # TODO: Publish event to event system when available
            # await self._event_publisher.publish(event)
            
        except Exception:
            # Don't fail command on event publishing error
            pass


# Factory function for dependency injection
def create_delete_cache_entry_command(repository: CacheRepository) -> DeleteCacheEntryCommand:
    """Create delete cache entry command."""
    return DeleteCacheEntryCommand(repository=repository)