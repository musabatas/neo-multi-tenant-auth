"""In-memory message queue implementation for platform events infrastructure.

This module implements in-memory message queue for fast event processing in development/testing.
Single responsibility: In-memory queue operations with high performance and no persistence.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import time
import asyncio
import threading
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque
from dataclasses import dataclass, field
from heapq import heappush, heappop
from contextlib import asynccontextmanager

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


@dataclass
class QueueMessage:
    """Internal message representation."""
    message_id: str
    message_data: Dict[str, Any]
    priority: int
    enqueued_at: datetime
    dequeue_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    visibility_timeout: Optional[datetime] = None
    
    def __lt__(self, other):
        """Compare messages for priority queue (lower priority number = higher priority)."""
        if self.priority != other.priority:
            return self.priority < other.priority
        # Use enqueue time as tiebreaker
        return self.enqueued_at < other.enqueued_at


@dataclass
class QueueConfiguration:
    """Queue configuration settings."""
    max_size: Optional[int] = None
    ttl_seconds: int = 86400  # 24 hours
    dead_letter_queue: Optional[str] = None
    max_retries: int = 3
    priority_enabled: bool = True
    created_at: datetime = field(default_factory=utc_now)


@dataclass  
class QueueStats:
    """Queue statistics tracking."""
    total_enqueued: int = 0
    total_dequeued: int = 0
    total_acknowledged: int = 0
    total_retried: int = 0
    total_dead_lettered: int = 0
    total_purged: int = 0
    created_at: datetime = field(default_factory=utc_now)
    last_enqueue: Optional[datetime] = None
    last_dequeue: Optional[datetime] = None
    last_ack: Optional[datetime] = None


class MemoryEventQueue(MessageQueue):
    """In-memory implementation of MessageQueue protocol.
    
    ONLY handles in-memory queue operations with high performance and no persistence.
    Single responsibility: Bridge between queue operations and in-memory data structures.
    NO business logic, NO validation, NO external dependencies beyond Python stdlib.
    
    Features:
    - Priority queue support using heapq
    - Dead letter queue automatic handling  
    - Message TTL with automatic cleanup
    - High performance for development/testing
    - Thread-safe operations using locks
    - Comprehensive metrics and monitoring
    - No persistence (data lost on restart)
    """
    
    def __init__(
        self,
        default_ttl_seconds: int = 86400,  # 24 hours
        max_retries: int = 3,
        dead_letter_suffix: str = "_dlq",
        cleanup_interval_seconds: int = 60  # TTL cleanup every minute
    ):
        """Initialize memory queue with configuration.
        
        Args:
            default_ttl_seconds: Default message TTL
            max_retries: Default maximum retry attempts
            dead_letter_suffix: Suffix for dead letter queues
            cleanup_interval_seconds: Interval for TTL cleanup task
        """
        self._default_ttl = default_ttl_seconds
        self._max_retries = max_retries
        self._dlq_suffix = dead_letter_suffix
        self._cleanup_interval = cleanup_interval_seconds
        
        # Thread-safe data structures
        self._lock = threading.RLock()  # Reentrant lock for nested operations
        
        # Queue storage: queue_name -> list of QueueMessage (heapq)
        self._queues: Dict[str, List[QueueMessage]] = {}
        
        # Processing messages: queue_name -> dict of message_id -> QueueMessage
        self._processing: Dict[str, Dict[str, QueueMessage]] = defaultdict(dict)
        
        # Dead letter queues: queue_name -> list of QueueMessage
        self._dead_letters: Dict[str, List[QueueMessage]] = {}
        
        # Queue configurations: queue_name -> QueueConfiguration
        self._configurations: Dict[str, QueueConfiguration] = {}
        
        # Queue statistics: queue_name -> QueueStats
        self._statistics: Dict[str, QueueStats] = defaultdict(QueueStats)
        
        # Message lookup: message_id -> QueueMessage (for fast lookup)
        self._messages: Dict[str, QueueMessage] = {}
        
        # Control
        self._closed = False
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Start TTL cleanup task
        asyncio.create_task(self._start_cleanup_task())

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
        """Enqueue message to priority queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            # Ensure queue exists
            if queue_name not in self._queues:
                await self._create_default_queue(queue_name)
            
            # Check queue size limit
            config = self._configurations.get(queue_name, QueueConfiguration())
            if config.max_size and len(self._queues[queue_name]) >= config.max_size:
                raise QueueFullError(f"Queue {queue_name} has reached maximum size")
            
            # Create message
            message_id = generate_uuid_v7()
            enqueue_time = utc_now()
            
            # Apply delay if specified
            if delay_seconds:
                enqueue_time = datetime.fromtimestamp(
                    enqueue_time.timestamp() + delay_seconds,
                    tz=timezone.utc
                )
            
            queue_message = QueueMessage(
                message_id=message_id,
                message_data=message.copy(),
                priority=priority,
                enqueued_at=enqueue_time,
                max_retries=config.max_retries,
                correlation_id=correlation_id,
                user_id=str(user_id.value) if user_id else None
            )
            
            # Add to queue (heapq maintains priority order)
            heappush(self._queues[queue_name], queue_message)
            
            # Store message for lookup
            self._messages[message_id] = queue_message
            
            # Update statistics
            stats = self._statistics[queue_name]
            stats.total_enqueued += 1
            stats.last_enqueue = utc_now()
            
            return message_id
    
    async def dequeue(
        self,
        queue_name: str,
        batch_size: int = 1,
        visibility_timeout_seconds: float = 30.0,
        wait_timeout_seconds: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Dequeue messages with visibility timeout."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        if queue_name not in self._queues:
            return []
        
        messages = []
        
        # Handle wait timeout with polling
        start_time = time.time()
        while len(messages) == 0:
            with self._lock:
                # Get messages that are ready (past delay time)
                current_time = utc_now()
                ready_messages = []
                temp_queue = []
                
                # Extract ready messages from heap
                while self._queues[queue_name] and len(ready_messages) < batch_size:
                    msg = heappop(self._queues[queue_name])
                    
                    if msg.enqueued_at <= current_time:
                        # Message is ready
                        ready_messages.append(msg)
                    else:
                        # Message not ready yet, put back
                        temp_queue.append(msg)
                
                # Put delayed messages back
                for msg in temp_queue:
                    heappush(self._queues[queue_name], msg)
                
                if ready_messages:
                    # Move to processing with visibility timeout
                    visibility_expiry = datetime.fromtimestamp(
                        current_time.timestamp() + visibility_timeout_seconds,
                        tz=timezone.utc
                    )
                    
                    for msg in ready_messages:
                        msg.dequeue_count += 1
                        msg.visibility_timeout = visibility_expiry
                        
                        # Move to processing
                        self._processing[queue_name][msg.message_id] = msg
                        
                        # Prepare response format
                        message_dict = {
                            "message_id": msg.message_id,
                            "message_data": msg.message_data.copy(),
                            "enqueued_at": msg.enqueued_at.isoformat(),
                            "dequeue_count": msg.dequeue_count,
                            "priority": msg.priority,
                            "correlation_id": msg.correlation_id,
                            "user_id": msg.user_id
                        }
                        messages.append(message_dict)
                    
                    # Update statistics
                    stats = self._statistics[queue_name]
                    stats.total_dequeued += len(ready_messages)
                    stats.last_dequeue = utc_now()
                    
                    break
            
            # Check wait timeout
            if wait_timeout_seconds is None or wait_timeout_seconds <= 0:
                break
            
            if time.time() - start_time >= wait_timeout_seconds:
                break
            
            # Brief pause before retry
            await asyncio.sleep(0.1)
        
        return messages
    
    async def acknowledge(
        self,
        queue_name: str,
        message_id: str,
        processing_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Acknowledge successful message processing."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            # Remove from processing
            if (queue_name in self._processing and 
                message_id in self._processing[queue_name]):
                
                msg = self._processing[queue_name].pop(message_id)
                
                # Remove from message lookup
                if message_id in self._messages:
                    del self._messages[message_id]
                
                # Update statistics
                stats = self._statistics[queue_name]
                stats.total_acknowledged += 1
                stats.last_ack = utc_now()
                
                return True
        
        return False
    
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
        
        with self._lock:
            # Find message in processing
            if (queue_name not in self._processing or 
                message_id not in self._processing[queue_name]):
                raise MessageNotFoundError(f"Message {message_id} not found in processing")
            
            msg = self._processing[queue_name].pop(message_id)
            
            if retry and msg.dequeue_count < msg.max_retries:
                # Retry with exponential backoff
                exponential_delay = (2 ** msg.dequeue_count) * 1.0  # 1s, 2s, 4s, 8s...
                if delay_seconds:
                    exponential_delay += delay_seconds
                
                # Reset visibility timeout and update enqueue time
                msg.visibility_timeout = None
                msg.enqueued_at = datetime.fromtimestamp(
                    utc_now().timestamp() + exponential_delay,
                    tz=timezone.utc
                )
                
                # Put back in queue
                heappush(self._queues[queue_name], msg)
                
                # Update statistics
                stats = self._statistics[queue_name]
                stats.total_retried += 1
                
            else:
                # Move to dead letter queue
                dlq_name = f"{queue_name}{self._dlq_suffix}"
                
                # Ensure dead letter queue exists
                if dlq_name not in self._dead_letters:
                    self._dead_letters[dlq_name] = []
                
                # Add failure info to message
                msg.message_data["_failure_info"] = {
                    "failed_at": utc_now().isoformat(),
                    "failure_reason": reason,
                    "final_dequeue_count": msg.dequeue_count
                }
                
                self._dead_letters[dlq_name].append(msg)
                
                # Remove from message lookup
                if message_id in self._messages:
                    del self._messages[message_id]
                
                # Update statistics
                stats = self._statistics[queue_name]
                stats.total_dead_lettered += 1
        
        return True

    # ===========================================
    # Queue Management Operations
    # ===========================================
    
    async def create_queue(
        self,
        queue_name: str,
        configuration: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create queue with configuration."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            if queue_name in self._queues:
                raise DuplicateQueueError(f"Queue {queue_name} already exists")
            
            # Create configuration
            config_dict = {
                "max_size": None,
                "ttl_seconds": self._default_ttl,
                "dead_letter_queue": f"{queue_name}{self._dlq_suffix}",
                "max_retries": self._max_retries,
                "priority_enabled": True
            }
            
            if configuration:
                config_dict.update(configuration)
            
            config = QueueConfiguration(**config_dict)
            
            # Initialize queue structures
            self._queues[queue_name] = []
            self._processing[queue_name] = {}
            self._configurations[queue_name] = config
            self._statistics[queue_name] = QueueStats()
            
            return True
    
    async def delete_queue(
        self,
        queue_name: str,
        force: bool = False
    ) -> bool:
        """Delete queue and its messages."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            if queue_name not in self._queues:
                raise QueueNotFoundError(f"Queue {queue_name} not found")
            
            if not force and len(self._queues[queue_name]) > 0:
                raise QueueError(f"Queue {queue_name} contains messages. Use force=True to delete.")
            
            # Remove message references
            for msg in self._queues[queue_name]:
                if msg.message_id in self._messages:
                    del self._messages[msg.message_id]
            
            for msg in self._processing[queue_name].values():
                if msg.message_id in self._messages:
                    del self._messages[msg.message_id]
            
            # Remove queue structures
            del self._queues[queue_name]
            del self._processing[queue_name]
            del self._configurations[queue_name]
            del self._statistics[queue_name]
            
            # Remove dead letter queue if exists
            dlq_name = f"{queue_name}{self._dlq_suffix}"
            if dlq_name in self._dead_letters:
                del self._dead_letters[dlq_name]
            
            return True
    
    async def purge_queue(self, queue_name: str) -> int:
        """Remove all messages from queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            if queue_name not in self._queues:
                raise QueueNotFoundError(f"Queue {queue_name} not found")
            
            # Count messages to purge
            message_count = len(self._queues[queue_name]) + len(self._processing[queue_name])
            
            # Remove message references
            for msg in self._queues[queue_name]:
                if msg.message_id in self._messages:
                    del self._messages[msg.message_id]
                    
            for msg in self._processing[queue_name].values():
                if msg.message_id in self._messages:
                    del self._messages[msg.message_id]
            
            # Clear queues
            self._queues[queue_name].clear()
            self._processing[queue_name].clear()
            
            # Update statistics
            stats = self._statistics[queue_name]
            stats.total_purged += message_count
            
            return message_count
    
    async def list_queues(self) -> List[str]:
        """List all queue names."""
        with self._lock:
            return list(self._queues.keys())

    # ===========================================
    # Queue Information Operations
    # ===========================================
    
    async def get_queue_size(self, queue_name: str) -> int:
        """Get current message count in queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            if queue_name not in self._queues:
                return 0
            return len(self._queues[queue_name])
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get comprehensive queue statistics."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            if queue_name not in self._queues:
                raise QueueNotFoundError(f"Queue {queue_name} not found")
            
            stats = self._statistics[queue_name]
            dlq_name = f"{queue_name}{self._dlq_suffix}"
            
            # Calculate oldest message age
            oldest_message_age = 0
            if self._queues[queue_name]:
                oldest_msg = min(self._queues[queue_name], key=lambda m: m.enqueued_at)
                oldest_message_age = (utc_now() - oldest_msg.enqueued_at).total_seconds()
            
            return {
                "total_messages": len(self._queues[queue_name]),
                "in_flight_messages": len(self._processing[queue_name]),
                "dead_letter_messages": len(self._dead_letters.get(dlq_name, [])),
                "total_enqueued": stats.total_enqueued,
                "total_dequeued": stats.total_dequeued,
                "total_acknowledged": stats.total_acknowledged,
                "total_retried": stats.total_retried,
                "total_dead_lettered": stats.total_dead_lettered,
                "total_purged": stats.total_purged,
                "oldest_message_age": max(0, oldest_message_age),
                "created_at": stats.created_at.isoformat(),
                "last_enqueue": stats.last_enqueue.isoformat() if stats.last_enqueue else None,
                "last_dequeue": stats.last_dequeue.isoformat() if stats.last_dequeue else None,
                "last_ack": stats.last_ack.isoformat() if stats.last_ack else None
            }
    
    async def peek_messages(
        self,
        queue_name: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Peek at messages without dequeuing."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            if queue_name not in self._queues:
                return []
            
            # Get top messages without modifying heap
            messages = []
            queue_copy = self._queues[queue_name].copy()
            
            for _ in range(min(count, len(queue_copy))):
                if not queue_copy:
                    break
                    
                msg = heappop(queue_copy)
                message_dict = {
                    "message_id": msg.message_id,
                    "message_data": msg.message_data.copy(),
                    "enqueued_at": msg.enqueued_at.isoformat(),
                    "dequeue_count": msg.dequeue_count,
                    "priority": msg.priority,
                    "correlation_id": msg.correlation_id,
                    "user_id": msg.user_id
                }
                messages.append(message_dict)
            
            return messages

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
        
        with self._lock:
            dlq_name = f"{queue_name}{self._dlq_suffix}"
            if dlq_name not in self._dead_letters:
                return []
            
            messages = []
            for msg in self._dead_letters[dlq_name][:limit]:
                message_dict = {
                    "message_id": msg.message_id,
                    "message_data": msg.message_data.copy(),
                    "enqueued_at": msg.enqueued_at.isoformat(),
                    "dequeue_count": msg.dequeue_count,
                    "priority": msg.priority,
                    "correlation_id": msg.correlation_id,
                    "user_id": msg.user_id
                }
                messages.append(message_dict)
            
            return messages
    
    async def requeue_dead_letter_message(
        self,
        queue_name: str,
        message_id: str,
        target_queue: Optional[str] = None
    ) -> bool:
        """Move message from dead letter queue back to main queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            dlq_name = f"{queue_name}{self._dlq_suffix}"
            if dlq_name not in self._dead_letters:
                raise MessageNotFoundError(f"Dead letter queue {dlq_name} not found")
            
            # Find message in dead letter queue
            msg_to_requeue = None
            for i, msg in enumerate(self._dead_letters[dlq_name]):
                if msg.message_id == message_id:
                    msg_to_requeue = self._dead_letters[dlq_name].pop(i)
                    break
            
            if msg_to_requeue is None:
                raise MessageNotFoundError(f"Message {message_id} not found in dead letter queue")
            
            # Reset message state
            msg_to_requeue.dequeue_count = 0
            msg_to_requeue.visibility_timeout = None
            msg_to_requeue.enqueued_at = utc_now()
            
            # Remove failure info
            if "_failure_info" in msg_to_requeue.message_data:
                del msg_to_requeue.message_data["_failure_info"]
            
            # Add requeue info
            msg_to_requeue.message_data["_requeue_info"] = {
                "requeued_at": utc_now().isoformat(),
                "original_queue": queue_name
            }
            
            # Add to target queue
            target_queue_name = target_queue or queue_name
            if target_queue_name not in self._queues:
                await self._create_default_queue(target_queue_name)
            
            heappush(self._queues[target_queue_name], msg_to_requeue)
            self._messages[message_id] = msg_to_requeue
            
            return True
    
    async def clear_dead_letter_queue(
        self,
        queue_name: str,
        older_than_hours: Optional[int] = None
    ) -> int:
        """Clear messages from dead letter queue."""
        if self._closed:
            raise QueueConnectionError("Queue connection is closed")
        
        with self._lock:
            dlq_name = f"{queue_name}{self._dlq_suffix}"
            if dlq_name not in self._dead_letters:
                return 0
            
            if older_than_hours:
                # Clear only old messages
                cutoff_time = datetime.fromtimestamp(
                    utc_now().timestamp() - (older_than_hours * 3600),
                    tz=timezone.utc
                )
                
                messages_to_remove = []
                for i, msg in enumerate(self._dead_letters[dlq_name]):
                    failure_info = msg.message_data.get("_failure_info", {})
                    if failure_info.get("failed_at"):
                        try:
                            failed_at = datetime.fromisoformat(failure_info["failed_at"].replace('Z', '+00:00'))
                            if failed_at < cutoff_time:
                                messages_to_remove.append(i)
                        except (ValueError, TypeError):
                            # If we can't parse the date, include it for removal
                            messages_to_remove.append(i)
                
                # Remove in reverse order to maintain indices
                for i in reversed(messages_to_remove):
                    del self._dead_letters[dlq_name][i]
                
                return len(messages_to_remove)
            else:
                # Clear all messages
                count = len(self._dead_letters[dlq_name])
                self._dead_letters[dlq_name].clear()
                return count

    # ===========================================
    # Connection and Health Operations
    # ===========================================
    
    async def health_check(self) -> Dict[str, Any]:
        """Check memory queue system health."""
        start_time = time.time()
        
        with self._lock:
            total_messages = sum(len(queue) for queue in self._queues.values())
            total_processing = sum(len(processing) for processing in self._processing.values())
            total_dead_letters = sum(len(dlq) for dlq in self._dead_letters.values())
            
            response_time = (time.time() - start_time) * 1000
            
            return {
                "healthy": not self._closed,
                "connection_status": "connected" if not self._closed else "closed",
                "total_queues": len(self._queues),
                "total_messages": total_messages,
                "total_processing": total_processing,
                "total_dead_letters": total_dead_letters,
                "response_time_ms": round(response_time, 2),
                "last_check_at": utc_now().isoformat()
            }
    
    async def close(self) -> None:
        """Close queue and cleanup resources."""
        if not self._closed:
            self._closed = True
            
            # Cancel cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            # Clear all data
            with self._lock:
                self._queues.clear()
                self._processing.clear()
                self._dead_letters.clear()
                self._configurations.clear()
                self._statistics.clear()
                self._messages.clear()

    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    async def _create_default_queue(self, queue_name: str) -> None:
        """Create queue with default configuration."""
        config = QueueConfiguration(
            max_retries=self._max_retries,
            ttl_seconds=self._default_ttl,
            dead_letter_queue=f"{queue_name}{self._dlq_suffix}"
        )
        
        self._queues[queue_name] = []
        self._processing[queue_name] = {}
        self._configurations[queue_name] = config
        self._statistics[queue_name] = QueueStats()
    
    async def _start_cleanup_task(self) -> None:
        """Start the TTL cleanup background task."""
        if self._cleanup_interval > 0:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
    
    async def _cleanup_expired_messages(self) -> None:
        """Background task to cleanup expired messages and visibility timeouts."""
        while not self._closed:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                if self._closed:
                    break
                
                current_time = utc_now()
                
                with self._lock:
                    # Check for expired visibility timeouts
                    for queue_name in list(self._processing.keys()):
                        expired_messages = []
                        
                        for msg_id, msg in self._processing[queue_name].items():
                            if (msg.visibility_timeout and 
                                msg.visibility_timeout <= current_time):
                                expired_messages.append((msg_id, msg))
                        
                        # Move expired messages back to main queue
                        for msg_id, msg in expired_messages:
                            del self._processing[queue_name][msg_id]
                            msg.visibility_timeout = None
                            
                            # Put back in queue if not past TTL
                            config = self._configurations.get(queue_name, QueueConfiguration())
                            message_age = (current_time - msg.enqueued_at).total_seconds()
                            
                            if message_age < config.ttl_seconds:
                                heappush(self._queues[queue_name], msg)
                            else:
                                # Message expired, remove from lookup
                                if msg_id in self._messages:
                                    del self._messages[msg_id]
                    
                    # Cleanup TTL expired messages from main queues
                    for queue_name in list(self._queues.keys()):
                        config = self._configurations.get(queue_name, QueueConfiguration())
                        cutoff_time = datetime.fromtimestamp(
                            current_time.timestamp() - config.ttl_seconds,
                            tz=timezone.utc
                        )
                        
                        # Filter out expired messages
                        unexpired_messages = []
                        expired_count = 0
                        
                        for msg in self._queues[queue_name]:
                            if msg.enqueued_at >= cutoff_time:
                                unexpired_messages.append(msg)
                            else:
                                # Remove from lookup
                                if msg.message_id in self._messages:
                                    del self._messages[msg.message_id]
                                expired_count += 1
                        
                        # Rebuild heap if messages were removed
                        if expired_count > 0:
                            self._queues[queue_name] = unexpired_messages
                            # Re-heapify
                            import heapq
                            heapq.heapify(self._queues[queue_name])
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue cleanup task
                print(f"Error in cleanup task: {e}")


def create_memory_queue(
    default_ttl_seconds: int = 86400,
    max_retries: int = 3,
    dead_letter_suffix: str = "_dlq",
    cleanup_interval_seconds: int = 60
) -> MemoryEventQueue:
    """Factory function to create memory queue.
    
    Args:
        default_ttl_seconds: Default message TTL
        max_retries: Default maximum retry attempts  
        dead_letter_suffix: Suffix for dead letter queues
        cleanup_interval_seconds: Interval for TTL cleanup
        
    Returns:
        MemoryEventQueue: Configured queue instance
    """
    return MemoryEventQueue(
        default_ttl_seconds=default_ttl_seconds,
        max_retries=max_retries,
        dead_letter_suffix=dead_letter_suffix,
        cleanup_interval_seconds=cleanup_interval_seconds
    )