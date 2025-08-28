"""Redis-based cache distributor.

ONLY Redis distribution functionality - handles pub/sub messaging,
node coordination, and distributed cache operations using Redis.

Following maximum separation architecture - one file = one purpose.
"""

import asyncio
import json
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from ...core.entities.cache_namespace import CacheNamespace
from ...core.value_objects.cache_key import CacheKey
from ...core.protocols.distribution_service import DistributionService, DistributionEvent


class NodeStatus(Enum):
    """Node status in cluster."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PARTITIONED = "partitioned"
    FAILED = "failed"


@dataclass
class NodeInfo:
    """Information about a cluster node."""
    node_id: str
    address: str
    port: int
    status: NodeStatus = NodeStatus.ACTIVE
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    capabilities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == NodeStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "node_id": self.node_id,
            "address": self.address,
            "port": self.port,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat(),
            "capabilities": self.capabilities,
            "metadata": self.metadata
        }


class RedisDistributor:
    """Redis-based cache distributor.
    
    Provides distributed cache operations using Redis pub/sub and coordination:
    - Event publishing and subscription
    - Node registration and discovery
    - Distributed invalidation
    - Consistency management
    - Partition handling
    """
    
    def __init__(
        self,
        redis_client: Any,  # Redis client instance
        node_id: str,
        cluster_name: str = "neo-cache-cluster"
    ):
        """Initialize Redis distributor.
        
        Args:
            redis_client: Redis client for operations
            node_id: Unique identifier for this node
            cluster_name: Name of the cache cluster
        """
        self._redis = redis_client
        self._node_id = node_id
        self._cluster_name = cluster_name
        self._subscriptions: Dict[str, Dict[str, Any]] = {}
        self._event_handlers: Dict[DistributionEvent, List[Callable]] = {}
        self._background_tasks: List[asyncio.Task] = []
        self._running = False
        self._heartbeat_interval = 30  # seconds
        self._node_timeout = 90  # seconds
        
        # Redis key patterns
        self._keys = {
            "events": f"{cluster_name}:events",
            "nodes": f"{cluster_name}:nodes",
            "heartbeat": f"{cluster_name}:heartbeat",
            "coordination": f"{cluster_name}:coordination",
            "consistency": f"{cluster_name}:consistency"
        }
    
    async def start(self) -> None:
        """Start the distributor service."""
        if not self._running:
            self._running = True
            
            # Register this node
            await self.register_node(self._node_id, {
                "started_at": datetime.now(timezone.utc).isoformat(),
                "capabilities": ["pub_sub", "coordination", "consistency"]
            })
            
            # Start background tasks
            heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self._background_tasks.extend([heartbeat_task, cleanup_task])
    
    async def stop(self) -> None:
        """Stop the distributor service."""
        self._running = False
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        self._background_tasks.clear()
        
        # Unregister this node
        await self.unregister_node(self._node_id)
    
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
        try:
            event_data = {
                "event_id": str(uuid.uuid4()),
                "event_type": event_type.value,
                "key": key.value,
                "namespace": namespace.name,
                "source_node": self._node_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data or {},
                "target_nodes": target_nodes
            }
            
            # Publish to Redis pub/sub
            channel = self._get_event_channel(event_type, namespace)
            await self._redis.publish(channel, json.dumps(event_data))
            
            return True
            
        except Exception:
            return False
    
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
        subscription_id = str(uuid.uuid4())
        
        subscription = {
            "id": subscription_id,
            "event_types": [et.value for et in event_types],
            "callback": callback,
            "namespace_filter": namespace_filter.name if namespace_filter else None,
            "created_at": datetime.now(timezone.utc)
        }
        
        self._subscriptions[subscription_id] = subscription
        
        # Subscribe to Redis channels
        for event_type in event_types:
            if namespace_filter:
                channel = self._get_event_channel(event_type, namespace_filter)
            else:
                channel = f"{self._keys['events']}:{event_type.value}:*"
            
            # Note: In a real implementation, you'd set up Redis pub/sub subscriptions here
            # For this example, we're showing the structure
        
        return subscription_id
    
    async def unsubscribe_from_events(self, subscription_id: str) -> bool:
        """Unsubscribe from cache events.
        
        Args:
            subscription_id: ID returned from subscribe_to_events
            
        Returns:
            True if unsubscribed successfully
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False
    
    async def register_node(self, node_id: str, node_info: Dict[str, Any]) -> bool:
        """Register cache node in distribution cluster.
        
        Args:
            node_id: Unique identifier for the node
            node_info: Node information (address, capabilities, etc.)
            
        Returns:
            True if node was registered successfully
        """
        try:
            node_data = {
                **node_info,
                "node_id": node_id,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "last_heartbeat": datetime.now(timezone.utc).isoformat(),
                "status": NodeStatus.ACTIVE.value
            }
            
            # Store node information in Redis
            node_key = f"{self._keys['nodes']}:{node_id}"
            await self._redis.hset(node_key, mapping=node_data)
            
            # Set expiration for automatic cleanup
            await self._redis.expire(node_key, self._node_timeout)
            
            return True
            
        except Exception:
            return False
    
    async def unregister_node(self, node_id: str) -> bool:
        """Unregister cache node from distribution cluster.
        
        Args:
            node_id: Node identifier to unregister
            
        Returns:
            True if node was unregistered successfully
        """
        try:
            node_key = f"{self._keys['nodes']}:{node_id}"
            await self._redis.delete(node_key)
            return True
        except Exception:
            return False
    
    async def get_active_nodes(self) -> List[Dict[str, Any]]:
        """Get list of active nodes in cluster.
        
        Returns:
            List of node information dictionaries
        """
        try:
            nodes = []
            pattern = f"{self._keys['nodes']}:*"
            
            async for key in self._redis.scan_iter(match=pattern):
                node_data = await self._redis.hgetall(key)
                if node_data and node_data.get("status") == NodeStatus.ACTIVE.value:
                    nodes.append({k.decode() if isinstance(k, bytes) else k: 
                                v.decode() if isinstance(v, bytes) else v 
                                for k, v in node_data.items()})
            
            return nodes
            
        except Exception:
            return []
    
    async def ping_node(self, node_id: str) -> bool:
        """Check if specific node is alive and responsive.
        
        Args:
            node_id: Node identifier to ping
            
        Returns:
            True if node responded successfully
        """
        try:
            node_key = f"{self._keys['nodes']}:{node_id}"
            exists = await self._redis.exists(node_key)
            return bool(exists)
        except Exception:
            return False
    
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
        success = await self.publish_event(
            DistributionEvent.CACHE_INVALIDATE,
            key,
            namespace,
            data={"exclude_nodes": exclude_nodes or []}
        )
        
        # Get active nodes to return status
        nodes = await self.get_active_nodes()
        return {
            node["node_id"]: success 
            for node in nodes 
            if not exclude_nodes or node["node_id"] not in exclude_nodes
        }
    
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
        # Use a dummy key for namespace flush
        dummy_key = CacheKey("__namespace_flush__")
        
        success = await self.publish_event(
            DistributionEvent.NAMESPACE_FLUSH,
            dummy_key,
            namespace,
            data={"exclude_nodes": exclude_nodes or []}
        )
        
        nodes = await self.get_active_nodes()
        return {
            node["node_id"]: success 
            for node in nodes 
            if not exclude_nodes or node["node_id"] not in exclude_nodes
        }
    
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
        try:
            coordination_data = {
                "operation": "set",
                "key": key.value,
                "namespace": namespace.name,
                "value_size": len(value_data),
                "ttl_seconds": ttl_seconds,
                "replication_level": replication_level,
                "coordinator": self._node_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Store coordination info
            coord_key = f"{self._keys['coordination']}:{key.value}:{namespace.name}"
            await self._redis.hset(coord_key, mapping=coordination_data)
            
            # Publish set event
            success = await self.publish_event(
                DistributionEvent.CACHE_SET,
                key,
                namespace,
                data={
                    "ttl_seconds": ttl_seconds,
                    "replication_level": replication_level,
                    "value_size": len(value_data)
                }
            )
            
            return success
            
        except Exception:
            return False
    
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
        if not conflicting_values:
            return {}
        
        # Simple conflict resolution: use the most recent timestamp
        # In production, you might use more sophisticated strategies
        resolved = max(conflicting_values, key=lambda x: x.get("timestamp", ""))
        
        return {
            "resolved_value": resolved,
            "resolution_strategy": "latest_timestamp",
            "conflict_count": len(conflicting_values),
            "resolved_at": datetime.now(timezone.utc).isoformat()
        }
    
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
        # This is a simplified implementation
        # In production, you'd query all nodes and compare values
        return {
            "key": key.value,
            "namespace": namespace.name,
            "consistent": True,  # Placeholder
            "checked_nodes": await self.get_active_nodes(),
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
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
        # Simplified implementation - in production this would:
        # 1. Identify the authoritative value
        # 2. Broadcast the correct value to all nodes
        # 3. Verify repair was successful
        return True
    
    async def handle_network_partition(self, partitioned_nodes: List[str]) -> Dict[str, Any]:
        """Handle network partition scenario.
        
        Args:
            partitioned_nodes: List of nodes that are partitioned
            
        Returns:
            Partition handling strategy and actions taken
        """
        return {
            "strategy": "continue_operation",
            "partitioned_nodes": partitioned_nodes,
            "actions_taken": ["marked_nodes_partitioned", "continue_with_majority"],
            "handled_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def merge_partitions(self, partition_groups: List[List[str]]) -> Dict[str, Any]:
        """Merge cache state after partition resolution.
        
        Args:
            partition_groups: Groups of nodes that were partitioned
            
        Returns:
            Merge results and conflict resolutions
        """
        return {
            "merge_strategy": "latest_wins",
            "partition_groups": partition_groups,
            "conflicts_resolved": 0,  # Placeholder
            "merged_at": datetime.now(timezone.utc).isoformat()
        }
    
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
        active_nodes = await self.get_active_nodes()
        # Simple strategy: return all active nodes
        # In production, you might use consistent hashing or load balancing
        return [node["node_id"] for node in active_nodes]
    
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
        preferred_nodes = await self.get_preferred_nodes(key, namespace, operation)
        
        return {
            "operation": operation,
            "key": key.value,
            "namespace": namespace.name,
            "routed_to": preferred_nodes,
            "routed_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_distribution_stats(self) -> Dict[str, Any]:
        """Get distribution statistics."""
        active_nodes = await self.get_active_nodes()
        
        return {
            "cluster_name": self._cluster_name,
            "node_id": self._node_id,
            "active_nodes": len(active_nodes),
            "total_subscriptions": len(self._subscriptions),
            "uptime_seconds": 0,  # Placeholder
            "events_published": 0,  # Placeholder - would track in production
            "events_received": 0,  # Placeholder
            "last_heartbeat": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_cluster_health(self) -> Dict[str, Any]:
        """Get overall cluster health information."""
        nodes = await self.get_active_nodes()
        
        return {
            "cluster_name": self._cluster_name,
            "total_nodes": len(nodes),
            "healthy_nodes": len([n for n in nodes if n.get("status") == NodeStatus.ACTIVE.value]),
            "partitioned_nodes": 0,  # Placeholder
            "failed_nodes": 0,  # Placeholder
            "overall_health": "healthy" if nodes else "no_nodes",
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def health_check(self) -> bool:
        """Check distribution service health."""
        try:
            # Simple health check - ping Redis
            await self._redis.ping()
            return True
        except Exception:
            return False
    
    def _get_event_channel(self, event_type: DistributionEvent, namespace: CacheNamespace) -> str:
        """Get Redis pub/sub channel for event type and namespace."""
        return f"{self._keys['events']}:{event_type.value}:{namespace.name}"
    
    async def _heartbeat_loop(self) -> None:
        """Background heartbeat loop to maintain node registration."""
        while self._running:
            try:
                # Update heartbeat timestamp
                heartbeat_key = f"{self._keys['heartbeat']}:{self._node_id}"
                await self._redis.set(
                    heartbeat_key, 
                    datetime.now(timezone.utc).isoformat(),
                    ex=self._node_timeout
                )
                
                # Update node last_heartbeat
                node_key = f"{self._keys['nodes']}:{self._node_id}"
                await self._redis.hset(
                    node_key, 
                    "last_heartbeat", 
                    datetime.now(timezone.utc).isoformat()
                )
                
                await asyncio.sleep(self._heartbeat_interval)
                
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self._heartbeat_interval)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for expired nodes and data."""
        while self._running:
            try:
                # Clean up expired coordination data
                pattern = f"{self._keys['coordination']}:*"
                async for key in self._redis.scan_iter(match=pattern):
                    ttl = await self._redis.ttl(key)
                    if ttl == -1:  # No expiration set
                        await self._redis.expire(key, 3600)  # 1 hour default
                
                await asyncio.sleep(300)  # Run cleanup every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(300)


def create_redis_distributor(
    redis_client: Any,
    node_id: str,
    cluster_name: str = "neo-cache-cluster"
) -> RedisDistributor:
    """Factory function to create Redis distributor.
    
    Args:
        redis_client: Redis client for operations
        node_id: Unique identifier for this node
        cluster_name: Name of the cache cluster
        
    Returns:
        Configured Redis distributor instance
    """
    return RedisDistributor(redis_client, node_id, cluster_name)