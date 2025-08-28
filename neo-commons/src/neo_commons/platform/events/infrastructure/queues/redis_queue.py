"""Redis message queue implementation for platform events infrastructure.

This module implements Redis-backed message queue for event processing and delivery.
Single responsibility: Redis queue operations with persistence and distributed support.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import json
import time
import asyncio
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from .....core.value_objects import UserId
from .....utils import utc_now, generate_uuid_v7
from ...core.protocols.message_queue import (
    MessageQueue, 
    QueueError, 
    QueueConnectionError, 
    QueueNotFoundError, 
    QueueFullError,
    MessageNotFoundError,
    DuplicateQueueError
)


class RedisEventQueue(MessageQueue):
    """Redis implementation of MessageQueue protocol.
    
    ONLY handles Redis-backed queue operations with persistence and distributed support.
    Single responsibility: Bridge between queue operations and Redis backend.
    NO business logic, NO validation, NO external dependencies beyond Redis.
    
    Features:
    - Priority queue support using Redis sorted sets
    - Dead letter queue automatic handling
    - Message persistence and durability
    - Distributed queue support across multiple instances  
    - Automatic retry with exponential backoff
    - Comprehensive metrics and monitoring
    """
    
    def __init__(
        self,
        redis_client: Redis,
        queue_prefix: str = "events_queue",
        default_ttl_seconds: int = 86400,  # 24 hours
        max_retries: int = 3,
        dead_letter_suffix: str = "_dlq"
    ):
        """Initialize Redis queue with configuration.
        
        Args:
            redis_client: Redis async client instance
            queue_prefix: Prefix for all queue keys
            default_ttl_seconds: Default message TTL
            max_retries: Default maximum retry attempts
            dead_letter_suffix: Suffix for dead letter queues
        """
        self._redis = redis_client
        self._queue_prefix = queue_prefix
        self._default_ttl = default_ttl_seconds
        self._max_retries = max_retries
        self._dlq_suffix = dead_letter_suffix
        self._closed = False

    # ===========================================
    # Core Queue Operations
    # ===========================================
    
    async def enqueue(
        self,
        message: Dict[str, Any],
        queue_name: str,
        priority: int = 100,
        delay_seconds: Optional[float] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[UserId] = None
    ) -> str:
        """Enqueue message to Redis sorted set with priority ordering."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            # Generate unique message ID
            message_id = generate_uuid_v7()
            
            # Calculate score for priority ordering
            # Lower priority numbers get processed first
            # Use timestamp as tiebreaker for same priority
            timestamp = time.time()
            if delay_seconds:
                timestamp += delay_seconds
                
            score = priority * 1000000 + timestamp  # Priority dominant, timestamp secondary
            
            # Prepare message data
            message_data = {
                "message_id": message_id,
                "message_data": message,
                "enqueued_at": utc_now().isoformat(),
                "priority": priority,
                "dequeue_count": 0,
                "correlation_id": correlation_id,
                "user_id": str(user_id.value) if user_id else None,
                "max_retries": self._max_retries,
                "ttl_seconds": self._default_ttl
            }
            
            # Get queue key
            queue_key = self._get_queue_key(queue_name)
            
            # Check queue size limit if configured
            queue_config = await self._get_queue_config(queue_name)
            if queue_config.get("max_size"):
                current_size = await self._redis.zcard(queue_key)
                if current_size >= queue_config["max_size"]:
                    raise QueueFullError(f"Queue {queue_name} has reached maximum size")
            
            # Store message with TTL
            message_key = f"{queue_key}:msg:{message_id}"
            pipe = self._redis.pipeline()
            pipe.hset(message_key, mapping={k: json.dumps(v) if v is not None else "" for k, v in message_data.items()})
            pipe.expire(message_key, self._default_ttl)
            
            # Add to priority queue
            pipe.zadd(queue_key, {message_id: score})
            
            # Update queue stats
            stats_key = f"{queue_key}:stats"
            pipe.hincrby(stats_key, "total_enqueued", 1)
            pipe.hset(stats_key, "last_enqueue", utc_now().isoformat())
            
            await pipe.execute()
            
            return message_id
            
        except RedisError as e:
            raise QueueError(f"Failed to enqueue message to {queue_name}: {str(e)}")
    
    async def dequeue(
        self,
        queue_name: str,
        batch_size: int = 1,
        visibility_timeout_seconds: float = 30.0,
        wait_timeout_seconds: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Dequeue messages from Redis sorted set with visibility timeout."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = f"{queue_key}:processing"
            
            messages = []
            
            # Use BLPOP for wait timeout if specified
            if wait_timeout_seconds and wait_timeout_seconds > 0:
                # For Redis sorted sets, we need to poll
                start_time = time.time()
                while time.time() - start_time < wait_timeout_seconds:
                    messages = await self._dequeue_batch(queue_key, processing_key, batch_size, visibility_timeout_seconds)
                    if messages:
                        break
                    await asyncio.sleep(0.1)  # Brief pause before retry
            else:
                messages = await self._dequeue_batch(queue_key, processing_key, batch_size, visibility_timeout_seconds)
            
            # Update queue stats
            if messages:
                stats_key = f"{queue_key}:stats"
                pipe = self._redis.pipeline()
                pipe.hincrby(stats_key, "total_dequeued", len(messages))
                pipe.hset(stats_key, "last_dequeue", utc_now().isoformat())
                await pipe.execute()
            
            return messages
            
        except RedisError as e:
            raise QueueError(f"Failed to dequeue from {queue_name}: {str(e)}")
    
    async def _dequeue_batch(
        self, 
        queue_key: str, 
        processing_key: str, 
        batch_size: int, 
        visibility_timeout: float
    ) -> List[Dict[str, Any]]:
        """Internal batch dequeue with atomic operations."""
        # Get messages by lowest score (highest priority)
        message_ids = await self._redis.zrange(queue_key, 0, batch_size - 1)
        if not message_ids:
            return []
        
        messages = []
        pipe = self._redis.pipeline()
        visibility_score = time.time() + visibility_timeout
        
        for message_id in message_ids:
            message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
            
            # Remove from main queue and add to processing set
            pipe.zrem(queue_key, message_id_str)
            pipe.zadd(processing_key, {message_id_str: visibility_score})
            
            # Get message data
            message_key = f"{queue_key}:msg:{message_id_str}"
            pipe.hgetall(message_key)
            
        results = await pipe.execute()
        
        # Process results
        for i, message_id in enumerate(message_ids):
            message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
            message_data = results[i * 3 + 2]  # Every 3rd result is the message data
            
            if message_data:
                # Parse message data
                parsed_data = {}
                for k, v in message_data.items():
                    key = k.decode() if isinstance(k, bytes) else k
                    value = v.decode() if isinstance(v, bytes) else v
                    try:
                        parsed_data[key] = json.loads(value) if value else None
                    except json.JSONDecodeError:
                        parsed_data[key] = value
                
                # Increment dequeue count
                parsed_data["dequeue_count"] = parsed_data.get("dequeue_count", 0) + 1
                
                # Update message data
                message_key = f"{queue_key}:msg:{message_id_str}"
                await self._redis.hset(message_key, "dequeue_count", parsed_data["dequeue_count"])
                
                messages.append(parsed_data)
        
        return messages
    
    async def acknowledge(
        self,
        queue_name: str,
        message_id: str,
        processing_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Acknowledge message processing by removing from processing set."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = f"{queue_key}:processing"
            message_key = f"{queue_key}:msg:{message_id}"
            
            pipe = self._redis.pipeline()
            
            # Remove from processing set
            pipe.zrem(processing_key, message_id)
            
            # Delete message data
            pipe.delete(message_key)
            
            # Update stats
            stats_key = f"{queue_key}:stats"
            pipe.hincrby(stats_key, "total_acknowledged", 1)
            pipe.hset(stats_key, "last_ack", utc_now().isoformat())
            
            if processing_result:
                # Store processing result for analytics
                result_key = f"{queue_key}:results:{message_id}"
                pipe.hset(result_key, mapping={
                    "result": json.dumps(processing_result),
                    "processed_at": utc_now().isoformat()
                })
                pipe.expire(result_key, 3600)  # Keep results for 1 hour
            
            results = await pipe.execute()
            return results[0] > 0  # True if message was removed from processing
            
        except RedisError as e:
            raise QueueError(f"Failed to acknowledge message {message_id}: {str(e)}")
    
    async def reject(
        self,
        queue_name: str,
        message_id: str,
        reason: str,
        retry: bool = True,
        delay_seconds: Optional[float] = None
    ) -> bool:
        """Reject message with retry or dead letter handling."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            processing_key = f"{queue_key}:processing"
            message_key = f"{queue_key}:msg:{message_id}"
            
            # Get message data
            message_data = await self._redis.hgetall(message_key)
            if not message_data:
                raise MessageNotFoundError(f"Message {message_id} not found")
            
            # Parse message data
            parsed_data = {}
            for k, v in message_data.items():
                key = k.decode() if isinstance(k, bytes) else k
                value = v.decode() if isinstance(v, bytes) else v
                try:
                    parsed_data[key] = json.loads(value) if value else None
                except json.JSONDecodeError:
                    parsed_data[key] = value
            
            dequeue_count = parsed_data.get("dequeue_count", 0)
            max_retries = parsed_data.get("max_retries", self._max_retries)
            
            pipe = self._redis.pipeline()
            
            # Remove from processing set
            pipe.zrem(processing_key, message_id)
            
            if retry and dequeue_count < max_retries:
                # Retry: Add back to main queue with exponential backoff delay
                exponential_delay = (2 ** dequeue_count) * 1.0  # 1s, 2s, 4s, 8s...
                if delay_seconds:
                    exponential_delay += delay_seconds
                    
                retry_score = parsed_data.get("priority", 100) * 1000000 + time.time() + exponential_delay
                pipe.zadd(queue_key, {message_id: retry_score})
                
                # Update retry count
                pipe.hset(message_key, "retry_count", dequeue_count)
                
                # Update stats
                stats_key = f"{queue_key}:stats"
                pipe.hincrby(stats_key, "total_retried", 1)
                
            else:
                # Move to dead letter queue
                dlq_key = f"{queue_key}{self._dlq_suffix}"
                dlq_score = time.time()  # FIFO for dead letter
                
                pipe.zadd(dlq_key, {message_id: dlq_score})
                
                # Add failure information
                failure_info = {
                    "failed_at": utc_now().isoformat(),
                    "failure_reason": reason,
                    "final_dequeue_count": dequeue_count
                }
                pipe.hset(message_key, mapping={k: json.dumps(v) for k, v in failure_info.items()})
                
                # Update stats
                stats_key = f"{queue_key}:stats"
                pipe.hincrby(stats_key, "total_dead_lettered", 1)
            
            results = await pipe.execute()
            return results[0] > 0  # True if message was removed from processing
            
        except RedisError as e:
            raise QueueError(f"Failed to reject message {message_id}: {str(e)}")

    # ===========================================
    # Queue Management Operations
    # ===========================================
    
    async def create_queue(
        self,
        queue_name: str,
        configuration: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create queue by storing its configuration."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            config_key = f"{self._queue_prefix}:config:{queue_name}"
            
            # Check if queue already exists
            if await self._redis.exists(config_key):
                raise DuplicateQueueError(f"Queue {queue_name} already exists")
            
            # Default configuration
            default_config = {
                "created_at": utc_now().isoformat(),
                "max_size": None,
                "ttl_seconds": self._default_ttl,
                "dead_letter_queue": f"{queue_name}{self._dlq_suffix}",
                "max_retries": self._max_retries,
                "priority_enabled": True
            }
            
            if configuration:
                default_config.update(configuration)
            
            # Store configuration
            await self._redis.hset(config_key, mapping={
                k: json.dumps(v) if v is not None else "" 
                for k, v in default_config.items()
            })
            
            # Initialize stats
            queue_key = self._get_queue_key(queue_name)
            stats_key = f"{queue_key}:stats"
            await self._redis.hset(stats_key, mapping={
                "total_enqueued": "0",
                "total_dequeued": "0", 
                "total_acknowledged": "0",
                "total_retried": "0",
                "total_dead_lettered": "0",
                "created_at": utc_now().isoformat()
            })
            
            return True
            
        except RedisError as e:
            raise QueueError(f"Failed to create queue {queue_name}: {str(e)}")
    
    async def delete_queue(
        self,
        queue_name: str,
        force: bool = False
    ) -> bool:
        """Delete queue and optionally its messages."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            
            if not force:
                # Check if queue has messages
                message_count = await self._redis.zcard(queue_key)
                if message_count > 0:
                    raise QueueError(f"Queue {queue_name} contains {message_count} messages. Use force=True to delete.")
            
            # Get all message IDs to delete message data
            message_ids = await self._redis.zrange(queue_key, 0, -1)
            
            pipe = self._redis.pipeline()
            
            # Delete message data
            for message_id in message_ids:
                message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
                message_key = f"{queue_key}:msg:{message_id_str}"
                pipe.delete(message_key)
            
            # Delete queue structures
            pipe.delete(queue_key)  # Main queue
            pipe.delete(f"{queue_key}:processing")  # Processing set
            pipe.delete(f"{queue_key}:stats")  # Stats
            pipe.delete(f"{queue_key}{self._dlq_suffix}")  # Dead letter queue
            pipe.delete(f"{self._queue_prefix}:config:{queue_name}")  # Configuration
            
            await pipe.execute()
            return True
            
        except RedisError as e:
            raise QueueError(f"Failed to delete queue {queue_name}: {str(e)}")
    
    async def purge_queue(self, queue_name: str) -> int:
        """Remove all messages from queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            
            # Get all message IDs
            message_ids = await self._redis.zrange(queue_key, 0, -1)
            message_count = len(message_ids)
            
            if message_count == 0:
                return 0
            
            pipe = self._redis.pipeline()
            
            # Delete message data
            for message_id in message_ids:
                message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
                message_key = f"{queue_key}:msg:{message_id_str}"
                pipe.delete(message_key)
            
            # Clear queue
            pipe.delete(queue_key)
            pipe.delete(f"{queue_key}:processing")
            
            # Update stats
            stats_key = f"{queue_key}:stats"
            pipe.hset(stats_key, "purged_at", utc_now().isoformat())
            pipe.hincrby(stats_key, "total_purged", message_count)
            
            await pipe.execute()
            return message_count
            
        except RedisError as e:
            raise QueueError(f"Failed to purge queue {queue_name}: {str(e)}")
    
    async def list_queues(self) -> List[str]:
        """List all configured queues."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            config_pattern = f"{self._queue_prefix}:config:*"
            config_keys = await self._redis.keys(config_pattern)
            
            queue_names = []
            for key in config_keys:
                key_str = key.decode() if isinstance(key, bytes) else key
                queue_name = key_str.replace(f"{self._queue_prefix}:config:", "")
                queue_names.append(queue_name)
            
            return sorted(queue_names)
            
        except RedisError as e:
            raise QueueError(f"Failed to list queues: {str(e)}")

    # ===========================================
    # Queue Information Operations
    # ===========================================
    
    async def get_queue_size(self, queue_name: str) -> int:
        """Get current message count in queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            return await self._redis.zcard(queue_key)
            
        except RedisError as e:
            raise QueueError(f"Failed to get queue size for {queue_name}: {str(e)}")
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            stats_key = f"{queue_key}:stats"
            processing_key = f"{queue_key}:processing"
            dlq_key = f"{queue_key}{self._dlq_suffix}"
            
            # Get all stats in parallel
            pipe = self._redis.pipeline()
            pipe.hgetall(stats_key)
            pipe.zcard(queue_key)  # Current messages
            pipe.zcard(processing_key)  # In-flight messages
            pipe.zcard(dlq_key)  # Dead letter messages
            
            # Get oldest message timestamp
            pipe.zrange(queue_key, 0, 0, withscores=True)
            
            results = await pipe.execute()
            
            stats_data = results[0]
            current_messages = results[1]
            in_flight_messages = results[2]
            dead_letter_messages = results[3]
            oldest_message_data = results[4]
            
            # Parse stats data
            parsed_stats = {}
            for k, v in stats_data.items():
                key = k.decode() if isinstance(k, bytes) else k
                value = v.decode() if isinstance(v, bytes) else v
                try:
                    parsed_stats[key] = json.loads(value) if value else 0
                except (json.JSONDecodeError, ValueError):
                    parsed_stats[key] = value
            
            # Calculate oldest message age
            oldest_message_age = 0
            if oldest_message_data:
                oldest_score = oldest_message_data[0][1] if oldest_message_data else 0
                if oldest_score > 0:
                    # Extract timestamp from score (priority * 1000000 + timestamp)
                    oldest_timestamp = oldest_score % 1000000
                    oldest_message_age = time.time() - oldest_timestamp
            
            return {
                "total_messages": current_messages,
                "in_flight_messages": in_flight_messages,
                "dead_letter_messages": dead_letter_messages,
                "total_enqueued": parsed_stats.get("total_enqueued", 0),
                "total_dequeued": parsed_stats.get("total_dequeued", 0),
                "total_acknowledged": parsed_stats.get("total_acknowledged", 0),
                "total_retried": parsed_stats.get("total_retried", 0),
                "total_dead_lettered": parsed_stats.get("total_dead_lettered", 0),
                "oldest_message_age": max(0, oldest_message_age),
                "created_at": parsed_stats.get("created_at"),
                "last_enqueue": parsed_stats.get("last_enqueue"),
                "last_dequeue": parsed_stats.get("last_dequeue"),
                "last_ack": parsed_stats.get("last_ack")
            }
            
        except RedisError as e:
            raise QueueError(f"Failed to get queue stats for {queue_name}: {str(e)}")
    
    async def peek_messages(
        self,
        queue_name: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Peek at messages without dequeuing."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            
            # Get message IDs by score (priority)
            message_ids = await self._redis.zrange(queue_key, 0, count - 1, withscores=True)
            
            messages = []
            for message_id, score in message_ids:
                message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
                message_key = f"{queue_key}:msg:{message_id_str}"
                
                message_data = await self._redis.hgetall(message_key)
                if message_data:
                    # Parse message data
                    parsed_data = {"score": score}  # Include queue score
                    for k, v in message_data.items():
                        key = k.decode() if isinstance(k, bytes) else k
                        value = v.decode() if isinstance(v, bytes) else v
                        try:
                            parsed_data[key] = json.loads(value) if value else None
                        except json.JSONDecodeError:
                            parsed_data[key] = value
                    
                    messages.append(parsed_data)
            
            return messages
            
        except RedisError as e:
            raise QueueError(f"Failed to peek messages in {queue_name}: {str(e)}")

    # ===========================================
    # Dead Letter Queue Operations
    # ===========================================
    
    async def get_dead_letter_messages(
        self,
        queue_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get messages from dead letter queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            dlq_key = f"{queue_key}{self._dlq_suffix}"
            
            # Get message IDs from dead letter queue
            message_ids = await self._redis.zrange(dlq_key, 0, limit - 1, withscores=True)
            
            messages = []
            for message_id, score in message_ids:
                message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
                message_key = f"{queue_key}:msg:{message_id_str}"
                
                message_data = await self._redis.hgetall(message_key)
                if message_data:
                    # Parse message data
                    parsed_data = {"dlq_score": score}
                    for k, v in message_data.items():
                        key = k.decode() if isinstance(k, bytes) else k
                        value = v.decode() if isinstance(v, bytes) else v
                        try:
                            parsed_data[key] = json.loads(value) if value else None
                        except json.JSONDecodeError:
                            parsed_data[key] = value
                    
                    messages.append(parsed_data)
            
            return messages
            
        except RedisError as e:
            raise QueueError(f"Failed to get dead letter messages for {queue_name}: {str(e)}")
    
    async def requeue_dead_letter_message(
        self,
        queue_name: str,
        message_id: str,
        target_queue: Optional[str] = None
    ) -> bool:
        """Move message from dead letter queue back to main queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            source_queue_key = self._get_queue_key(queue_name)
            dlq_key = f"{source_queue_key}{self._dlq_suffix}"
            
            target_queue_key = self._get_queue_key(target_queue) if target_queue else source_queue_key
            
            # Get message data
            message_key = f"{source_queue_key}:msg:{message_id}"
            message_data = await self._redis.hgetall(message_key)
            
            if not message_data:
                raise MessageNotFoundError(f"Message {message_id} not found in dead letter queue")
            
            # Parse priority
            priority_str = message_data.get(b"priority", b"100")
            if isinstance(priority_str, bytes):
                priority_str = priority_str.decode()
            try:
                priority = json.loads(priority_str) if priority_str else 100
            except (json.JSONDecodeError, ValueError):
                priority = 100
            
            pipe = self._redis.pipeline()
            
            # Remove from dead letter queue
            pipe.zrem(dlq_key, message_id)
            
            # Add to target queue with current timestamp
            score = priority * 1000000 + time.time()
            pipe.zadd(target_queue_key, {message_id: score})
            
            # Reset dequeue count and remove failure info
            pipe.hset(message_key, mapping={
                "dequeue_count": "0",
                "requeued_at": json.dumps(utc_now().isoformat())
            })
            pipe.hdel(message_key, "failed_at", "failure_reason", "final_dequeue_count")
            
            # Update stats
            stats_key = f"{source_queue_key}:stats"
            pipe.hincrby(stats_key, "total_requeued", 1)
            
            results = await pipe.execute()
            return results[0] > 0  # True if message was removed from DLQ
            
        except RedisError as e:
            raise QueueError(f"Failed to requeue dead letter message {message_id}: {str(e)}")
    
    async def clear_dead_letter_queue(
        self,
        queue_name: str,
        older_than_hours: Optional[int] = None
    ) -> int:
        """Clear messages from dead letter queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
            
        try:
            queue_key = self._get_queue_key(queue_name)
            dlq_key = f"{queue_key}{self._dlq_suffix}"
            
            if older_than_hours:
                # Clear only old messages
                cutoff_score = time.time() - (older_than_hours * 3600)
                message_ids = await self._redis.zrangebyscore(dlq_key, 0, cutoff_score)
            else:
                # Clear all messages
                message_ids = await self._redis.zrange(dlq_key, 0, -1)
            
            if not message_ids:
                return 0
            
            pipe = self._redis.pipeline()
            
            # Delete message data
            for message_id in message_ids:
                message_id_str = message_id.decode() if isinstance(message_id, bytes) else message_id
                message_key = f"{queue_key}:msg:{message_id_str}"
                pipe.delete(message_key)
                
                # Remove from dead letter queue
                pipe.zrem(dlq_key, message_id_str)
            
            await pipe.execute()
            return len(message_ids)
            
        except RedisError as e:
            raise QueueError(f"Failed to clear dead letter queue for {queue_name}: {str(e)}")

    # ===========================================
    # Connection and Health Operations
    # ===========================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection and queue system health."""
        health_info = {
            "healthy": False,
            "connection_status": "disconnected",
            "total_queues": 0,
            "total_messages": 0,
            "response_time_ms": 0,
            "last_check_at": utc_now().isoformat()
        }
        
        try:
            start_time = time.time()
            
            # Test connection with PING
            await self._redis.ping()
            
            # Count queues and messages
            queue_names = await self.list_queues()
            total_messages = 0
            
            for queue_name in queue_names:
                queue_size = await self.get_queue_size(queue_name)
                total_messages += queue_size
            
            response_time = (time.time() - start_time) * 1000
            
            health_info.update({
                "healthy": True,
                "connection_status": "connected",
                "total_queues": len(queue_names),
                "total_messages": total_messages,
                "response_time_ms": round(response_time, 2)
            })
            
        except (RedisError, ConnectionError, TimeoutError) as e:
            health_info.update({
                "connection_status": "error",
                "error_message": str(e)
            })
        
        return health_info
    
    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if not self._closed:
            self._closed = True
            if self._redis:
                await self._redis.close()

    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    def _get_queue_key(self, queue_name: str) -> str:
        """Get Redis key for queue."""
        return f"{self._queue_prefix}:{queue_name}"
    
    async def _get_queue_config(self, queue_name: str) -> Dict[str, Any]:
        """Get queue configuration."""
        config_key = f"{self._queue_prefix}:config:{queue_name}"
        config_data = await self._redis.hgetall(config_key)
        
        if not config_data:
            return {}
        
        # Parse configuration
        config = {}
        for k, v in config_data.items():
            key = k.decode() if isinstance(k, bytes) else k
            value = v.decode() if isinstance(v, bytes) else v
            try:
                config[key] = json.loads(value) if value else None
            except json.JSONDecodeError:
                config[key] = value
        
        return config


def create_redis_queue(
    redis_url: str = "redis://localhost:6379",
    queue_prefix: str = "events_queue",
    default_ttl_seconds: int = 86400,
    max_retries: int = 3,
    **redis_kwargs
) -> RedisEventQueue:
    """Factory function to create Redis queue with connection.
    
    Args:
        redis_url: Redis connection URL
        queue_prefix: Prefix for all queue keys
        default_ttl_seconds: Default message TTL
        max_retries: Default maximum retry attempts
        **redis_kwargs: Additional Redis client configuration
        
    Returns:
        RedisEventQueue: Configured queue instance
    """
    redis_client = redis.from_url(
        redis_url,
        decode_responses=False,  # Keep binary for better performance
        **redis_kwargs
    )
    
    return RedisEventQueue(
        redis_client=redis_client,
        queue_prefix=queue_prefix,
        default_ttl_seconds=default_ttl_seconds,
        max_retries=max_retries
    )