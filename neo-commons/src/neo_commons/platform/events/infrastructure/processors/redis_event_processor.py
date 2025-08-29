"""Redis-based event processor for consuming events from Redis Streams.

This implementation provides event consumption and processing capabilities
using Redis Streams with consumer groups for scalable event handling.
Supports high-throughput event processing with proper acknowledgment.
"""

import json
import logging
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
from datetime import datetime, timezone
from uuid import UUID

from ....application.protocols.event_processor import EventProcessorProtocol, EventHandler
from ....domain.entities.event import Event, EventStatus, EventPriority
from ....domain.value_objects.event_id import EventId
from ....domain.value_objects.event_type import EventType
from ....domain.value_objects.aggregate_reference import AggregateReference
from ....domain.value_objects.correlation_id import CorrelationId
from .....core.exceptions import EventHandlingError


logger = logging.getLogger(__name__)


class RedisEventProcessor(EventProcessorProtocol):
    """Redis Streams-based event processor implementation.
    
    Follows the development plan Redis architecture:
    - Consumes from: events:admin:*, events:tenant:*
    - Consumer Groups for concurrent processing
    - Acknowledgment and retry logic
    - High-performance concurrent event handling
    """
    
    def __init__(self, redis_client, max_retries: int = 3, retry_delay: float = 1.0):
        """Initialize Redis event processor.
        
        Args:
            redis_client: Async Redis client (e.g., aioredis.Redis)
            max_retries: Maximum retry attempts for failed events
            retry_delay: Delay between retry attempts in seconds
        """
        self._redis = redis_client
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._consumers = {}  # Track running consumers
        self._stop_flags = {}  # Stop flags for consumers
    
    async def consume(
        self,
        queue_name: str,
        consumer_group: str,
        handler: EventHandler,
        max_events: int = 10,
        timeout_ms: int = 5000
    ) -> None:
        """Consume events from Redis stream and process with handler.
        
        Args:
            queue_name: Redis stream name to consume from
            consumer_group: Consumer group identifier
            handler: Async function to handle each event
            max_events: Maximum events to process per batch
            timeout_ms: Timeout for waiting for events
        """
        try:
            # Ensure consumer group exists
            await self._ensure_consumer_group(queue_name, consumer_group)
            
            # Create unique consumer name
            consumer_name = f"{consumer_group}-{id(self)}"
            
            # Read pending messages first (unacknowledged)
            pending_messages = await self._redis.xreadgroup(
                consumer_group,
                consumer_name,
                {queue_name: "0"},
                count=max_events,
                block=0
            )
            
            # Process pending messages
            for stream, messages in pending_messages:
                for message_id, fields in messages:
                    await self._process_message(
                        queue_name, message_id, fields, handler, consumer_group, consumer_name
                    )
            
            # Read new messages
            new_messages = await self._redis.xreadgroup(
                consumer_group,
                consumer_name,
                {queue_name: ">"},
                count=max_events,
                block=timeout_ms
            )
            
            # Process new messages
            for stream, messages in new_messages:
                for message_id, fields in messages:
                    await self._process_message(
                        queue_name, message_id, fields, handler, consumer_group, consumer_name
                    )
                    
        except Exception as e:
            logger.error(f"Failed to consume events from '{queue_name}': {e}")
            raise EventHandlingError(f"Event consumption failed: {e}")
    
    async def consume_batch(
        self,
        queue_name: str,
        consumer_group: str,
        batch_handler,
        batch_size: int = 10,
        timeout_ms: int = 5000
    ) -> None:
        """Consume events in batches and process them.
        
        Args:
            queue_name: Redis stream name to consume from
            consumer_group: Consumer group identifier
            batch_handler: Async function to handle event batches
            batch_size: Number of events per batch
            timeout_ms: Timeout for waiting for events
        """
        try:
            # Ensure consumer group exists
            await self._ensure_consumer_group(queue_name, consumer_group)
            
            # Create unique consumer name
            consumer_name = f"{consumer_group}-batch-{id(self)}"
            
            # Read messages from stream
            messages = await self._redis.xreadgroup(
                consumer_group,
                consumer_name,
                {queue_name: ">"},
                count=batch_size,
                block=timeout_ms
            )
            
            if not messages:
                return
            
            # Process messages in batch
            events = []
            message_ids = []
            
            for stream, stream_messages in messages:
                for message_id, fields in stream_messages:
                    try:
                        event = self._deserialize_event(fields)
                        events.append(event)
                        message_ids.append(message_id)
                    except Exception as e:
                        logger.error(f"Failed to deserialize event {message_id}: {e}")
                        # Acknowledge malformed message to remove from queue
                        await self._redis.xack(queue_name, consumer_group, message_id)
            
            if events:
                try:
                    # Process batch with handler
                    await batch_handler(events, queue_name)
                    
                    # Acknowledge all successful messages
                    if message_ids:
                        await self._redis.xack(queue_name, consumer_group, *message_ids)
                    
                    logger.info(f"Successfully processed batch of {len(events)} events")
                    
                except Exception as e:
                    logger.error(f"Batch handler failed for {len(events)} events: {e}")
                    raise EventHandlingError(f"Batch processing failed: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to consume event batch from '{queue_name}': {e}")
            raise EventHandlingError(f"Batch consumption failed: {e}")
    
    async def ack(self, event: Event, message_id: str) -> None:
        """Acknowledge successful processing of an event.
        
        Args:
            event: Event that was processed
            message_id: Message ID from the queue
        """
        try:
            queue_name = event.queue_name
            if not queue_name:
                logger.warning(f"Event {event.id} has no queue_name for acknowledgment")
                return
                
            # Find consumer group from event context or use default
            consumer_group = self._extract_consumer_group(event)
            
            # Acknowledge the message
            result = await self._redis.xack(queue_name, consumer_group, message_id)
            
            if result:
                logger.debug(f"Acknowledged event {event.id} with message_id {message_id}")
            else:
                logger.warning(f"Failed to acknowledge message {message_id} - may already be acked")
                
        except Exception as e:
            logger.error(f"Failed to acknowledge event {event.id}: {e}")
            raise EventHandlingError(f"Event acknowledgment failed: {e}")
    
    async def nack(
        self,
        event: Event,
        message_id: str,
        error_message: str,
        retry: bool = True
    ) -> None:
        """Negative acknowledge - event processing failed.
        
        Args:
            event: Event that failed processing
            message_id: Message ID from the queue
            error_message: Error description
            retry: Whether to retry the event
        """
        try:
            logger.warning(f"Processing failed for event {event.id}: {error_message}")
            
            if retry and event.retry_count < event.max_retries:
                # Increment retry count and schedule retry
                event.retry_count += 1
                event.status = EventStatus.PENDING
                
                # Add delay before retry (exponential backoff)
                delay = self._retry_delay * (2 ** (event.retry_count - 1))
                await asyncio.sleep(delay)
                
                logger.info(f"Retrying event {event.id} (attempt {event.retry_count}/{event.max_retries})")
                
                # Event will remain in pending list for next consumer read
                
            else:
                # Max retries reached or retry disabled - mark as failed
                event.status = EventStatus.FAILED
                event.error_message = error_message
                
                # Acknowledge to remove from queue (move to dead letter or log)
                queue_name = event.queue_name
                if queue_name:
                    consumer_group = self._extract_consumer_group(event)
                    await self._redis.xack(queue_name, consumer_group, message_id)
                    
                logger.error(f"Event {event.id} failed permanently: {error_message}")
                
        except Exception as e:
            logger.error(f"Failed to handle event failure for {event.id}: {e}")
            raise EventHandlingError(f"Event nack handling failed: {e}")
    
    async def start_consumer(
        self,
        queue_name: str,
        consumer_group: str,
        handler: EventHandler,
        **kwargs
    ) -> None:
        """Start a long-running consumer for a queue.
        
        Args:
            queue_name: Queue to consume from
            consumer_group: Consumer group identifier
            handler: Event handler function
            **kwargs: Additional consumer configuration
        """
        consumer_key = f"{queue_name}:{consumer_group}"
        
        if consumer_key in self._consumers:
            logger.warning(f"Consumer for {consumer_key} is already running")
            return
        
        # Create stop flag
        stop_flag = asyncio.Event()
        self._stop_flags[consumer_key] = stop_flag
        
        # Start consumer task
        consumer_task = asyncio.create_task(
            self._run_consumer(queue_name, consumer_group, handler, stop_flag, **kwargs)
        )
        
        self._consumers[consumer_key] = consumer_task
        
        logger.info(f"Started consumer for {consumer_key}")
    
    async def stop_consumer(self, queue_name: str, consumer_group: str) -> None:
        """Stop a running consumer.
        
        Args:
            queue_name: Queue name
            consumer_group: Consumer group identifier
        """
        consumer_key = f"{queue_name}:{consumer_group}"
        
        if consumer_key not in self._consumers:
            logger.warning(f"No running consumer found for {consumer_key}")
            return
        
        # Set stop flag
        if consumer_key in self._stop_flags:
            self._stop_flags[consumer_key].set()
        
        # Wait for consumer task to finish
        try:
            consumer_task = self._consumers[consumer_key]
            await asyncio.wait_for(consumer_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Consumer {consumer_key} did not stop gracefully, cancelling")
            consumer_task.cancel()
        except Exception as e:
            logger.error(f"Error stopping consumer {consumer_key}: {e}")
        
        # Cleanup
        del self._consumers[consumer_key]
        if consumer_key in self._stop_flags:
            del self._stop_flags[consumer_key]
        
        logger.info(f"Stopped consumer for {consumer_key}")
    
    async def get_consumer_stats(
        self,
        queue_name: str,
        consumer_group: str
    ) -> Dict[str, Any]:
        """Get statistics for a consumer.
        
        Args:
            queue_name: Queue name
            consumer_group: Consumer group identifier
            
        Returns:
            Dictionary with consumer statistics
        """
        try:
            # Get stream info
            stream_info = await self._redis.xinfo_stream(queue_name)
            
            # Get consumer group info
            try:
                group_info = await self._redis.xinfo_groups(queue_name)
                consumer_info = await self._redis.xinfo_consumers(queue_name, consumer_group)
            except Exception:
                group_info = []
                consumer_info = []
            
            # Find our consumer group stats
            group_stats = None
            for group in group_info:
                if group.get("name") == consumer_group:
                    group_stats = group
                    break
            
            return {
                "queue_name": queue_name,
                "consumer_group": consumer_group,
                "stream_length": stream_info.get("length", 0),
                "consumers_count": len(consumer_info),
                "pending_messages": group_stats.get("pending", 0) if group_stats else 0,
                "last_delivered_id": group_stats.get("last-delivered-id") if group_stats else None,
                "consumer_details": consumer_info,
                "is_running": f"{queue_name}:{consumer_group}" in self._consumers
            }
            
        except Exception as e:
            logger.error(f"Failed to get consumer stats for {queue_name}:{consumer_group}: {e}")
            return {
                "queue_name": queue_name,
                "consumer_group": consumer_group,
                "error": str(e),
                "is_running": f"{queue_name}:{consumer_group}" in self._consumers
            }
    
    async def is_healthy(self) -> bool:
        """Check if the processor is healthy and can consume messages.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple ping to check Redis connectivity
            pong = await self._redis.ping()
            return pong == True or pong == b"PONG"
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    # Private helper methods
    
    async def _ensure_consumer_group(self, stream_name: str, group_name: str) -> None:
        """Ensure consumer group exists for the stream."""
        try:
            # Try to create consumer group (will fail if already exists)
            await self._redis.xgroup_create(stream_name, group_name, id="0", mkstream=True)
            logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
        except Exception as e:
            # Consumer group likely already exists, which is fine
            if "BUSYGROUP" not in str(e):
                logger.warning(f"Failed to create consumer group '{group_name}': {e}")
    
    async def _process_message(
        self,
        queue_name: str,
        message_id: str,
        fields: Dict,
        handler: EventHandler,
        consumer_group: str,
        consumer_name: str
    ) -> None:
        """Process a single message from Redis stream."""
        try:
            # Deserialize event from Redis fields
            event = self._deserialize_event(fields)
            
            # Set queue context
            event.queue_name = queue_name
            event.message_id = str(message_id)
            
            # Process event with handler
            await handler(event, queue_name)
            
            # Acknowledge successful processing
            await self._redis.xack(queue_name, consumer_group, message_id)
            
            logger.debug(f"Successfully processed event {event.id}")
            
        except Exception as e:
            logger.error(f"Failed to process message {message_id}: {e}")
            
            # Try to deserialize event for nack handling
            try:
                event = self._deserialize_event(fields)
                await self.nack(event, str(message_id), str(e))
            except Exception as nack_error:
                logger.error(f"Failed to handle processing error: {nack_error}")
                # Acknowledge to prevent infinite retry of malformed message
                await self._redis.xack(queue_name, consumer_group, message_id)
    
    def _deserialize_event(self, fields: Dict) -> Event:
        """Deserialize event from Redis stream fields."""
        try:
            # Convert bytes to strings if needed
            if isinstance(fields, dict):
                fields = {k.decode() if isinstance(k, bytes) else k: 
                         v.decode() if isinstance(v, bytes) else v 
                         for k, v in fields.items()}
            
            # Parse event data
            event_data = json.loads(fields.get("event_data", "{}"))
            event_metadata = json.loads(fields.get("event_metadata", "{}"))
            
            # Create aggregate reference
            aggregate_ref = AggregateReference(
                aggregate_id=fields["aggregate_id"],
                aggregate_type=fields["aggregate_type"]
            )
            
            # Parse optional fields
            correlation_id = CorrelationId(fields["correlation_id"]) if fields.get("correlation_id") else None
            causation_id = CorrelationId(fields["causation_id"]) if fields.get("causation_id") else None
            
            # Parse timestamps
            created_at = datetime.fromisoformat(fields["created_at"])
            scheduled_at = datetime.fromisoformat(fields["scheduled_at"]) if fields.get("scheduled_at") else None
            
            # Create event entity
            event = Event(
                id=EventId(fields["event_id"]),
                event_type=EventType(fields["event_type"]),
                aggregate_reference=aggregate_ref,
                event_data=event_data,
                event_metadata=event_metadata,
                created_at=created_at,
                scheduled_at=scheduled_at,
                status=EventStatus(fields["status"]),
                priority=EventPriority(fields["priority"]),
                retry_count=int(fields.get("retry_count", 0)),
                max_retries=int(fields.get("max_retries", 3)),
                correlation_id=correlation_id,
                causation_id=causation_id,
                tenant_id=UUID(fields["tenant_id"]) if fields.get("tenant_id") else None,
                organization_id=UUID(fields["organization_id"]) if fields.get("organization_id") else None,
                user_id=UUID(fields["user_id"]) if fields.get("user_id") else None,
                source_service=fields.get("source_service") or None,
                source_version=fields.get("source_version") or None,
            )
            
            # Set partition key
            event.partition_key = fields.get("partition_key")
            
            return event
            
        except Exception as e:
            raise EventHandlingError(f"Failed to deserialize event: {e}")
    
    def _extract_consumer_group(self, event: Event) -> str:
        """Extract consumer group from event context."""
        # Use partition key or schema information to determine consumer group
        if event.partition_key:
            parts = event.partition_key.split(":")
            if len(parts) >= 2:
                return f"consumers-{parts[0]}"  # e.g., "consumers-admin"
        
        # Default consumer group
        return "default-consumers"
    
    async def _run_consumer(
        self,
        queue_name: str,
        consumer_group: str,
        handler: EventHandler,
        stop_flag: asyncio.Event,
        **kwargs
    ) -> None:
        """Run long-running consumer loop."""
        logger.info(f"Starting consumer loop for {queue_name}:{consumer_group}")
        
        # Extract configuration
        batch_size = kwargs.get("batch_size", 10)
        timeout_ms = kwargs.get("timeout_ms", 5000)
        
        try:
            while not stop_flag.is_set():
                try:
                    # Consume batch of events
                    await self.consume(
                        queue_name=queue_name,
                        consumer_group=consumer_group,
                        handler=handler,
                        max_events=batch_size,
                        timeout_ms=timeout_ms
                    )
                    
                except asyncio.TimeoutError:
                    # Normal timeout, continue loop
                    continue
                    
                except Exception as e:
                    logger.error(f"Error in consumer loop for {queue_name}:{consumer_group}: {e}")
                    # Sleep before retrying to avoid busy loop
                    await asyncio.sleep(1.0)
                    
        except asyncio.CancelledError:
            logger.info(f"Consumer loop cancelled for {queue_name}:{consumer_group}")
        except Exception as e:
            logger.error(f"Consumer loop failed for {queue_name}:{consumer_group}: {e}")
        finally:
            logger.info(f"Consumer loop ended for {queue_name}:{consumer_group}")