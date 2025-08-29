"""Redis-based event publisher for high-throughput event streaming.

This implementation uses Redis Streams for reliable event publishing following
the development plan architecture. Supports 50K+ events/second performance
with partitioning and consumer groups.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from ....application.protocols.event_publisher import EventPublisherProtocol
from ....domain.entities.event import Event
from .....core.exceptions import EventPublishingError


logger = logging.getLogger(__name__)


class RedisEventPublisher(EventPublisherProtocol):
    """Redis Streams-based event publisher implementation.
    
    Follows the development plan Redis architecture:
    - Events Stream: events:admin:*, events:tenant:*
    - Partitioning by tenant/event type
    - Consumer Groups for multiple workers
    - High performance with 50K+ events/second capability
    """
    
    def __init__(self, redis_client, max_len: int = 100000):
        """Initialize Redis event publisher.
        
        Args:
            redis_client: Async Redis client (e.g., aioredis.Redis)
            max_len: Maximum stream length for memory management
        """
        self._redis = redis_client
        self._max_len = max_len
    
    async def publish(
        self, 
        event: Event, 
        schema: str,
        queue_name: Optional[str] = None,
        partition_key: Optional[str] = None
    ) -> str:
        """Publish single event to Redis stream.
        
        Args:
            event: Event entity to publish
            schema: Database schema context for routing
            queue_name: Optional specific queue name override
            partition_key: Optional partition key override
            
        Returns:
            Stream message ID
            
        Raises:
            PublishError: If publishing fails
        """
        try:
            # Build stream name following development plan pattern
            stream_name = self._build_stream_name(event, schema, queue_name)
            
            # Build partition key for stream distribution
            partition = self._build_partition_key(event, schema, partition_key)
            
            # Prepare event payload for Redis stream
            payload = self._serialize_event(event, schema, partition)
            
            # Publish to Redis stream with MAXLEN for memory management
            message_id = await self._redis.xadd(
                stream_name,
                payload,
                maxlen=self._max_len,
                approximate=True
            )
            
            # Update event with queue information
            event.queue_name = stream_name
            event.message_id = str(message_id)
            event.partition_key = partition
            
            logger.info(
                f"Published event {event.id} to stream '{stream_name}' "
                f"with message_id '{message_id}' and partition '{partition}'"
            )
            
            return str(message_id)
            
        except Exception as e:
            logger.error(f"Failed to publish event {event.id} to Redis: {e}")
            raise PublishError(f"Failed to publish event: {e}")
    
    async def publish_batch(
        self, 
        events: List[Event], 
        schema: str,
        queue_name: Optional[str] = None
    ) -> List[str]:
        """Publish multiple events in batch using Redis pipeline.
        
        Args:
            events: List of event entities to publish
            schema: Database schema context
            queue_name: Optional specific queue name override
            
        Returns:
            List of stream message IDs
            
        Raises:
            PublishError: If batch publishing fails
        """
        if not events:
            return []
        
        try:
            # Use Redis pipeline for batch efficiency
            pipeline = self._redis.pipeline()
            message_ids = []
            
            for event in events:
                # Build stream name for each event
                stream_name = self._build_stream_name(event, schema, queue_name)
                partition = self._build_partition_key(event, schema)
                payload = self._serialize_event(event, schema, partition)
                
                # Add to pipeline
                pipeline.xadd(
                    stream_name,
                    payload,
                    maxlen=self._max_len,
                    approximate=True
                )
                
                # Update event with queue information
                event.queue_name = stream_name
                event.partition_key = partition
            
            # Execute pipeline batch
            results = await pipeline.execute()
            
            # Extract message IDs and update events
            for i, (event, result) in enumerate(zip(events, results)):
                message_id = str(result)
                event.message_id = message_id
                message_ids.append(message_id)
            
            logger.info(f"Published batch of {len(events)} events to Redis streams")
            return message_ids
            
        except Exception as e:
            logger.error(f"Failed to publish event batch to Redis: {e}")
            raise PublishError(f"Failed to publish event batch: {e}")
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get Redis stream statistics for monitoring.
        
        Args:
            queue_name: Redis stream name
            
        Returns:
            Dictionary with stream statistics
        """
        try:
            # Get stream info from Redis
            info = await self._redis.xinfo_stream(queue_name)
            
            # Get consumer group info if exists
            groups = []
            try:
                groups = await self._redis.xinfo_groups(queue_name)
            except Exception:
                # No consumer groups exist yet
                pass
            
            return {
                "stream_name": queue_name,
                "length": info.get("length", 0),
                "first_entry_id": info.get("first-entry", [None])[0],
                "last_entry_id": info.get("last-entry", [None])[0],
                "consumer_groups": len(groups),
                "last_generated_id": info.get("last-generated-id"),
                "radix_tree_keys": info.get("radix-tree-keys", 0),
                "radix_tree_nodes": info.get("radix-tree-nodes", 0),
                "recorded_first_entry_id": info.get("recorded-first-entry-id"),
            }
            
        except Exception as e:
            logger.error(f"Failed to get queue stats for '{queue_name}': {e}")
            return {
                "stream_name": queue_name,
                "error": str(e),
                "length": 0
            }
    
    async def is_healthy(self) -> bool:
        """Check Redis connection health.
        
        Returns:
            True if Redis is accessible and responsive
        """
        try:
            # Simple ping to check connectivity
            pong = await self._redis.ping()
            return pong == True or pong == b"PONG"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def _build_stream_name(
        self, 
        event: Event, 
        schema: str, 
        override_name: Optional[str] = None
    ) -> str:
        """Build Redis stream name following development plan pattern.
        
        Pattern: events:{schema}:{event_type} or events:{schema}:all
        
        Args:
            event: Event entity
            schema: Database schema context
            override_name: Optional name override
            
        Returns:
            Redis stream name
        """
        if override_name:
            return override_name
        
        # Follow development plan pattern: events:admin:*, events:tenant:*
        event_category = event.event_type.value.split('.')[0]  # e.g., "tenants" from "tenants.created"
        return f"events:{schema}:{event_category}"
    
    def _build_partition_key(
        self, 
        event: Event, 
        schema: str,
        override_key: Optional[str] = None
    ) -> str:
        """Build partition key for stream distribution.
        
        Args:
            event: Event entity
            schema: Database schema context
            override_key: Optional key override
            
        Returns:
            Partition key for distribution
        """
        if override_key:
            return override_key
        
        # Use tenant_id if available for tenant isolation
        if event.tenant_id:
            return f"{schema}:tenant:{event.tenant_id}"
        
        # Use organization_id for organization-level partitioning
        if event.organization_id:
            return f"{schema}:org:{event.organization_id}"
        
        # Default to schema-based partitioning
        return f"{schema}:system"
    
    def _serialize_event(self, event: Event, schema: str, partition_key: str) -> Dict[str, str]:
        """Serialize event for Redis stream storage.
        
        Args:
            event: Event entity to serialize
            schema: Database schema context
            partition_key: Partition key for the event
            
        Returns:
            Dictionary suitable for Redis XADD
        """
        # Core event data for Redis stream
        payload = {
            "event_id": str(event.id.value),
            "event_type": event.event_type.value,
            "aggregate_id": str(event.aggregate_reference.aggregate_id),
            "aggregate_type": event.aggregate_reference.aggregate_type,
            "schema": schema,
            "partition_key": partition_key,
            
            # Event content
            "event_data": json.dumps(event.event_data),
            "event_metadata": json.dumps(event.event_metadata),
            
            # Processing information
            "status": event.status.value,
            "priority": event.priority.value,
            "retry_count": str(event.retry_count),
            "max_retries": str(event.max_retries),
            
            # Context information
            "correlation_id": str(event.correlation_id) if event.correlation_id else "",
            "causation_id": str(event.causation_id) if event.causation_id else "",
            "tenant_id": str(event.tenant_id) if event.tenant_id else "",
            "organization_id": str(event.organization_id) if event.organization_id else "",
            "user_id": str(event.user_id) if event.user_id else "",
            "source_service": event.source_service or "",
            "source_version": event.source_version or "",
            
            # Timestamps
            "created_at": event.created_at.isoformat(),
            "scheduled_at": event.scheduled_at.isoformat() if event.scheduled_at else "",
            "published_at": datetime.now().isoformat(),
        }
        
        return payload