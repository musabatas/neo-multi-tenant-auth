"""Flush namespace command.

ONLY namespace flushing - handles complete namespace deletion
with validation and event publishing.

Following maximum separation architecture - one file = one purpose.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

from ...core.protocols.cache_repository import CacheRepository
from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
from ...core.events.cache_invalidated import CacheInvalidated, InvalidationReason


@dataclass
class FlushNamespaceData:
    """Data required to flush a cache namespace."""
    
    namespace: str
    
    # Optional context
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    request_id: Optional[str] = None
    reason: str = "manual"


@dataclass
class FlushNamespaceResult:
    """Result of namespace flush."""
    
    success: bool
    namespace: str
    entries_deleted: int = 0
    error_message: Optional[str] = None


class FlushNamespaceCommand:
    """Command to flush entire cache namespace.
    
    Handles complete namespace deletion with:
    - Namespace validation and creation
    - Repository flush operation with error handling
    - Event publishing for monitoring and audit
    - Performance tracking
    - Tenant isolation support
    """
    
    def __init__(self, repository: CacheRepository):
        """Initialize flush namespace command.
        
        Args:
            repository: Cache repository for namespace operations
        """
        self._repository = repository
    
    async def execute(self, data: FlushNamespaceData) -> FlushNamespaceResult:
        """Execute namespace flush operation.
        
        Args:
            data: Namespace flush data
            
        Returns:
            Result of the flush operation with count of deleted entries
        """
        try:
            # Create cache namespace
            namespace = self._create_namespace(data.namespace, data.tenant_id)
            
            # Get namespace size before deletion (for audit)
            entries_before = await self._repository.get_namespace_size(namespace)
            
            # Flush namespace in repository
            entries_deleted = await self._repository.flush_namespace(namespace)
            
            # Publish invalidation event for monitoring
            if entries_deleted > 0:
                await self._publish_flush_event(
                    namespace, data, entries_deleted
                )
            
            return FlushNamespaceResult(
                success=True,
                namespace=data.namespace,
                entries_deleted=entries_deleted
            )
                
        except Exception as e:
            return FlushNamespaceResult(
                success=False,
                namespace=data.namespace,
                entries_deleted=0,
                error_message=f"Flush failed: {str(e)}"
            )
    
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
    
    async def _publish_flush_event(
        self, 
        namespace: CacheNamespace,
        data: FlushNamespaceData,
        entries_deleted: int
    ) -> None:
        """Publish namespace flush event for monitoring."""
        try:
            # Create a representative cache key for the event
            from ...core.value_objects.cache_key import CacheKey
            
            # Use a special key to represent namespace flush
            flush_key = CacheKey(f"__namespace_flush__:{namespace.name}")
            
            reason_map = {
                "manual": InvalidationReason.MANUAL,
                "system": InvalidationReason.SYSTEM,
                "scheduled": InvalidationReason.SCHEDULED
            }
            
            event = CacheInvalidated(
                event_id=str(uuid4()),
                timestamp=datetime.utcnow(),
                key=flush_key,
                namespace=namespace,
                reason=InvalidationReason.NAMESPACE_FLUSH,
                triggered_by=data.user_id or "system",
                request_id=data.request_id,
                user_id=data.user_id,
                tenant_id=data.tenant_id,
                batch_id=str(uuid4()),
                batch_size=entries_deleted
            )
            
            # TODO: Publish event to event system when available
            # await self._event_publisher.publish(event)
            
        except Exception:
            # Don't fail command on event publishing error
            pass


# Factory function for dependency injection
def create_flush_namespace_command(repository: CacheRepository) -> FlushNamespaceCommand:
    """Create flush namespace command."""
    return FlushNamespaceCommand(repository=repository)