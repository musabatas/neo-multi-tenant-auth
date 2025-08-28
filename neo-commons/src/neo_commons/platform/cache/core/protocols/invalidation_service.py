"""Invalidation service protocol.

ONLY invalidation contract - defines interface for cache invalidation
services with pattern-based and event-driven invalidation.

Following maximum separation architecture - one file = one purpose.
"""

from typing import List, Optional, Dict, Any
from typing_extensions import Protocol, runtime_checkable

from ..entities.cache_namespace import CacheNamespace
from ..value_objects.cache_key import CacheKey
from ..value_objects.invalidation_pattern import InvalidationPattern


@runtime_checkable
class InvalidationService(Protocol):
    """Invalidation service protocol.
    
    Defines interface for cache invalidation services with support for:
    - Pattern-based invalidation (wildcard, regex)
    - Event-driven invalidation
    - Dependency-based invalidation
    - Cascade invalidation
    - Batch invalidation operations
    - Invalidation scheduling
    - Distributed coordination
    """
    
    async def invalidate_key(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> bool:
        """Invalidate single cache key.
        
        Args:
            key: Cache key to invalidate
            namespace: Namespace containing the key
            reason: Optional reason for invalidation (for auditing)
            
        Returns:
            True if key was invalidated, False if key didn't exist
        """
        ...
    
    async def invalidate_keys(
        self, 
        keys: List[CacheKey], 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> Dict[CacheKey, bool]:
        """Invalidate multiple cache keys.
        
        Args:
            keys: List of cache keys to invalidate
            namespace: Namespace containing the keys
            reason: Optional reason for invalidation
            
        Returns:
            Dictionary mapping keys to invalidation status
        """
        ...
    
    async def invalidate_pattern(
        self, 
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None,
        reason: Optional[str] = None
    ) -> int:
        """Invalidate keys matching pattern.
        
        Args:
            pattern: Invalidation pattern to match
            namespace: Optional namespace to limit search (None = all namespaces)
            reason: Optional reason for invalidation
            
        Returns:
            Number of keys invalidated
        """
        ...
    
    async def invalidate_namespace(
        self, 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> int:
        """Invalidate entire namespace.
        
        Args:
            namespace: Namespace to invalidate
            reason: Optional reason for invalidation
            
        Returns:
            Number of keys invalidated
        """
        ...
    
    # Dependency-based invalidation
    async def add_dependency(
        self, 
        source_key: CacheKey, 
        dependent_key: CacheKey,
        namespace: CacheNamespace
    ) -> bool:
        """Add cache dependency relationship.
        
        When source_key is invalidated, dependent_key will also be invalidated.
        
        Args:
            source_key: Key that triggers invalidation
            dependent_key: Key that gets invalidated when source changes
            namespace: Namespace for both keys
            
        Returns:
            True if dependency was added successfully
        """
        ...
    
    async def remove_dependency(
        self, 
        source_key: CacheKey, 
        dependent_key: CacheKey,
        namespace: CacheNamespace
    ) -> bool:
        """Remove cache dependency relationship.
        
        Args:
            source_key: Source key in dependency
            dependent_key: Dependent key in dependency
            namespace: Namespace for both keys
            
        Returns:
            True if dependency was removed successfully
        """
        ...
    
    async def get_dependencies(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace
    ) -> List[CacheKey]:
        """Get all keys that depend on given key.
        
        Args:
            key: Source key to check dependencies for
            namespace: Namespace containing the key
            
        Returns:
            List of keys that depend on the given key
        """
        ...
    
    async def invalidate_with_dependencies(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace,
        reason: Optional[str] = None
    ) -> int:
        """Invalidate key and all its dependencies.
        
        Cascading invalidation that follows dependency chains.
        
        Args:
            key: Root key to invalidate
            namespace: Namespace containing the key
            reason: Optional reason for invalidation
            
        Returns:
            Total number of keys invalidated (including dependencies)
        """
        ...
    
    # Scheduled invalidation
    async def schedule_invalidation(
        self, 
        key: CacheKey, 
        namespace: CacheNamespace,
        delay_seconds: int,
        reason: Optional[str] = None
    ) -> str:
        """Schedule key invalidation after delay.
        
        Args:
            key: Cache key to invalidate later
            namespace: Namespace containing the key
            delay_seconds: Delay before invalidation
            reason: Optional reason for invalidation
            
        Returns:
            Schedule ID that can be used to cancel
        """
        ...
    
    async def cancel_scheduled_invalidation(self, schedule_id: str) -> bool:
        """Cancel scheduled invalidation.
        
        Args:
            schedule_id: ID returned from schedule_invalidation
            
        Returns:
            True if cancellation was successful
        """
        ...
    
    async def list_scheduled_invalidations(
        self, 
        namespace: Optional[CacheNamespace] = None
    ) -> List[Dict[str, Any]]:
        """List pending scheduled invalidations.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            List of scheduled invalidation details
        """
        ...
    
    # Event-driven invalidation
    async def register_event_trigger(
        self, 
        event_type: str,
        pattern: InvalidationPattern,
        namespace: Optional[CacheNamespace] = None
    ) -> str:
        """Register event-driven invalidation trigger.
        
        When specified event occurs, keys matching pattern will be invalidated.
        
        Args:
            event_type: Type of event that triggers invalidation
            pattern: Pattern of keys to invalidate
            namespace: Optional namespace limit
            
        Returns:
            Trigger ID that can be used for management
        """
        ...
    
    async def unregister_event_trigger(self, trigger_id: str) -> bool:
        """Unregister event-driven invalidation trigger.
        
        Args:
            trigger_id: ID returned from register_event_trigger
            
        Returns:
            True if trigger was unregistered successfully
        """
        ...
    
    async def trigger_event_invalidation(
        self, 
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> int:
        """Trigger invalidation based on event.
        
        Args:
            event_type: Type of event occurring
            event_data: Optional event data for context
            
        Returns:
            Number of keys invalidated
        """
        ...
    
    # Statistics and monitoring
    async def get_invalidation_stats(self) -> Dict[str, Any]:
        """Get invalidation statistics.
        
        Returns metrics like:
        - total_invalidations: Total number of invalidations
        - pattern_invalidations: Number of pattern-based invalidations
        - dependency_invalidations: Number of dependency-based invalidations
        - scheduled_invalidations: Number of scheduled invalidations
        - event_invalidations: Number of event-driven invalidations
        - average_keys_per_invalidation: Average keys invalidated per operation
        """
        ...
    
    async def get_dependency_graph(
        self, 
        namespace: Optional[CacheNamespace] = None
    ) -> Dict[str, List[str]]:
        """Get cache dependency graph.
        
        Args:
            namespace: Optional namespace filter
            
        Returns:
            Dictionary mapping source keys to dependent keys
        """
        ...
    
    async def health_check(self) -> bool:
        """Check invalidation service health.
        
        Returns:
            True if service is healthy and responsive
        """
        ...