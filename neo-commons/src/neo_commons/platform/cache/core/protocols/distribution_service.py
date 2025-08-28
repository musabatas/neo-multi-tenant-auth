"""Distribution service protocol.

ONLY distribution contract - defines interface for cache distribution
services with pub/sub and replication support.

Following maximum separation architecture - one file = one purpose.
"""

from typing import List, Optional, Dict, Any, Callable
from typing_extensions import Protocol, runtime_checkable
from enum import Enum

from ..entities.cache_namespace import CacheNamespace
from ..value_objects.cache_key import CacheKey


class DistributionEvent(Enum):
    """Types of distribution events."""
    
    CACHE_SET = "cache.set"
    CACHE_DELETE = "cache.delete"
    CACHE_INVALIDATE = "cache.invalidate"
    NAMESPACE_FLUSH = "namespace.flush"
    PATTERN_INVALIDATE = "pattern.invalidate"


@runtime_checkable
class DistributionService(Protocol):
    """Distribution service protocol.
    
    Defines interface for cache distribution services with support for:
    - Publish/subscribe messaging
    - Cache replication and consistency
    - Distributed invalidation
    - Node coordination
    - Conflict resolution
    - Partition tolerance
    - Network failure handling
    """
    
    # Event publishing and subscription
    async def publish_event(
        self, 
        event_type: DistributionEvent,
        key: CacheKey,
        namespace: CacheNamespace,
        data: Optional[Dict[str, Any]] = None,
        target_nodes: Optional[List[str]] = None
    ) -> bool:
        """Publish cache event to distributed nodes.
        
        Args:
            event_type: Type of cache event
            key: Cache key involved in event
            namespace: Namespace of the key
            data: Optional event data
            target_nodes: Optional list of specific nodes to target
            
        Returns:
            True if event was published successfully
        """
        ...
    
    async def subscribe_to_events(
        self, 
        event_types: List[DistributionEvent],
        callback: Callable[[DistributionEvent, CacheKey, CacheNamespace, Dict[str, Any]], None],
        namespace_filter: Optional[CacheNamespace] = None
    ) -> str:
        """Subscribe to cache events.
        
        Args:
            event_types: List of event types to subscribe to
            callback: Function to call when event occurs
            namespace_filter: Optional namespace filter
            
        Returns:
            Subscription ID that can be used to unsubscribe
        """
        ...
    
    async def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """Unsubscribe from cache events.
        
        Args:
            subscription_id: ID returned from subscribe_to_events
            
        Returns:
            True if unsubscribed successfully
        """
        ...
    
    # Node management and coordination
    async def register_node(
        self, 
        node_id: str, 
        node_info: Dict[str, Any]
    ) -> bool:
        """Register cache node in distribution cluster.
        
        Args:
            node_id: Unique identifier for the node
            node_info: Node information (address, capabilities, etc.)
            
        Returns:
            True if node was registered successfully
        """
        ...
    
    async def unregister_node(self, node_id: str) -> bool:
        """Unregister cache node from distribution cluster.
        
        Args:
            node_id: Node identifier to unregister
            
        Returns:
            True if node was unregistered successfully
        """
        ...
    
    async def get_active_nodes(self) -> List[Dict[str, Any]]:
        """Get list of active nodes in cluster.
        
        Returns:
            List of node information dictionaries
        """
        ...
    
    async def ping_node(self, node_id: str) -> bool:
        """Check if specific node is alive and responsive.
        
        Args:
            node_id: Node identifier to ping
            
        Returns:
            True if node responded successfully
        """
        ...
    
    # Distributed operations
    async def broadcast_invalidation(
        self, 
        key: CacheKey,
        namespace: CacheNamespace,
        exclude_nodes: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Broadcast cache invalidation to all nodes.
        
        Args:
            key: Cache key to invalidate
            namespace: Namespace containing the key
            exclude_nodes: Optional nodes to exclude from broadcast
            
        Returns:
            Dictionary mapping node IDs to invalidation success status
        """
        ...
    
    async def broadcast_namespace_flush(
        self, 
        namespace: CacheNamespace,
        exclude_nodes: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """Broadcast namespace flush to all nodes.
        
        Args:
            namespace: Namespace to flush
            exclude_nodes: Optional nodes to exclude from broadcast
            
        Returns:
            Dictionary mapping node IDs to flush success status
        """
        ...
    
    async def coordinate_cache_set(
        self, 
        key: CacheKey,
        namespace: CacheNamespace,
        value_data: bytes,
        ttl_seconds: Optional[int] = None,
        replication_level: int = 1
    ) -> bool:
        """Coordinate distributed cache set operation.
        
        Args:
            key: Cache key to set
            namespace: Namespace for the key
            value_data: Serialized value data
            ttl_seconds: Optional TTL in seconds
            replication_level: Number of replicas to maintain
            
        Returns:
            True if operation was coordinated successfully
        """
        ...
    
    # Consistency and conflict resolution
    async def resolve_conflict(
        self, 
        key: CacheKey,
        namespace: CacheNamespace,
        conflicting_values: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Resolve conflict when multiple nodes have different values.
        
        Args:
            key: Cache key with conflict
            namespace: Namespace containing the key
            conflicting_values: List of conflicting value data from different nodes
            
        Returns:
            Resolved value data to be used
        """
        ...
    
    async def check_consistency(
        self, 
        key: CacheKey,
        namespace: CacheNamespace
    ) -> Dict[str, Any]:
        """Check consistency of key across nodes.
        
        Args:
            key: Cache key to check
            namespace: Namespace containing the key
            
        Returns:
            Consistency report with node values and conflicts
        """
        ...
    
    async def repair_consistency(
        self, 
        key: CacheKey,
        namespace: CacheNamespace,
        authoritative_node: Optional[str] = None
    ) -> bool:
        """Repair consistency issues for a key.
        
        Args:
            key: Cache key to repair
            namespace: Namespace containing the key
            authoritative_node: Optional node to use as source of truth
            
        Returns:
            True if consistency was repaired successfully
        """
        ...
    
    # Partition handling
    async def handle_network_partition(
        self, 
        partitioned_nodes: List[str]
    ) -> Dict[str, Any]:
        """Handle network partition scenario.
        
        Args:
            partitioned_nodes: List of nodes that are partitioned
            
        Returns:
            Partition handling strategy and actions taken
        """
        ...
    
    async def merge_partitions(
        self, 
        partition_groups: List[List[str]]
    ) -> Dict[str, Any]:
        """Merge cache state after partition resolution.
        
        Args:
            partition_groups: Groups of nodes that were partitioned
            
        Returns:
            Merge results and conflict resolutions
        """
        ...
    
    # Load balancing and routing
    async def get_preferred_nodes(
        self, 
        key: CacheKey,
        namespace: CacheNamespace,
        operation: str
    ) -> List[str]:
        """Get preferred nodes for cache operation.
        
        Args:
            key: Cache key for operation
            namespace: Namespace containing the key
            operation: Type of operation ('get', 'set', 'delete')
            
        Returns:
            List of node IDs in preference order
        """
        ...
    
    async def route_operation(
        self, 
        operation: str,
        key: CacheKey,
        namespace: CacheNamespace,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Route cache operation to appropriate nodes.
        
        Args:
            operation: Type of operation
            key: Cache key for operation
            namespace: Namespace containing the key
            data: Optional operation data
            
        Returns:
            Operation result from routed nodes
        """
        ...
    
    # Statistics and monitoring
    async def get_distribution_stats(self) -> Dict[str, Any]:
        """Get distribution statistics.
        
        Returns metrics like:
        - total_events_published: Number of events published
        - total_events_received: Number of events received
        - active_subscriptions: Number of active subscriptions
        - node_count: Number of active nodes
        - network_latency: Average network latency
        - replication_lag: Average replication lag
        - consistency_violations: Number of consistency violations
        """
        ...
    
    async def get_cluster_health(self) -> Dict[str, Any]:
        """Get overall cluster health information.
        
        Returns:
            Cluster health report including node status and connectivity
        """
        ...
    
    async def health_check(self) -> bool:
        """Check distribution service health.
        
        Returns:
            True if service is healthy and responsive
        """
        ...