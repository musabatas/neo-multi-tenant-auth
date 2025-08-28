"""Message queue protocol for platform events infrastructure.

This module defines the MessageQueue protocol contract following maximum separation architecture.
Single responsibility: Message queue operations for event processing and delivery.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from datetime import datetime

from .....core.value_objects import UserId
from ..value_objects import EventId
from ..entities.domain_event import DomainEvent


@runtime_checkable
class MessageQueue(Protocol):
    """Message queue protocol for event processing and delivery.
    
    This protocol defines the contract for message queue operations following
    maximum separation architecture. Single responsibility: queue operations
    for event processing, action execution, and delivery coordination.
    
    Pure platform infrastructure protocol - implementations handle:
    - Message queuing and dequeuing
    - Priority-based ordering  
    - Dead letter queue management
    - Queue performance metrics
    - Persistence and reliability
    - Concurrency control
    """

    # ===========================================
    # Core Queue Operations
    # ===========================================
    
    @abstractmethod
    async def enqueue(
        self,
        message: Dict[str, Any],
        queue_name: str,
        priority: int = 100,
        delay_seconds: Optional[float] = None,
        correlation_id: Optional[str] = None,
        user_id: Optional[UserId] = None
    ) -> str:
        """Enqueue a message for processing.
        
        Args:
            message: Message data to queue
            queue_name: Target queue identifier
            priority: Message priority (lower numbers processed first)
            delay_seconds: Optional delay before message becomes available
            correlation_id: For tracking related messages
            user_id: User who triggered the message
            
        Returns:
            Message ID for tracking
            
        Raises:
            QueueError: If enqueue operation fails
        """
        ...
    
    @abstractmethod
    async def dequeue(
        self,
        queue_name: str,
        batch_size: int = 1,
        visibility_timeout_seconds: float = 30.0,
        wait_timeout_seconds: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Dequeue messages from queue for processing.
        
        Args:
            queue_name: Queue to dequeue from
            batch_size: Maximum messages to retrieve
            visibility_timeout_seconds: Time message is invisible to other consumers
            wait_timeout_seconds: Long polling timeout (None for immediate return)
            
        Returns:
            List of message objects with metadata:
            - message_id: Unique message identifier
            - message_data: Original message content
            - enqueued_at: When message was enqueued
            - dequeue_count: Number of times dequeued
            - priority: Message priority
            - correlation_id: Optional correlation identifier
            
        Raises:
            QueueError: If dequeue operation fails
        """
        ...
    
    @abstractmethod
    async def acknowledge(
        self,
        queue_name: str,
        message_id: str,
        processing_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Acknowledge successful message processing.
        
        Args:
            queue_name: Queue the message came from
            message_id: Message identifier to acknowledge
            processing_result: Optional processing result metadata
            
        Returns:
            True if acknowledgment was successful
            
        Raises:
            QueueError: If acknowledgment fails
        """
        ...
    
    @abstractmethod
    async def reject(
        self,
        queue_name: str,
        message_id: str,
        reason: str,
        retry: bool = True,
        delay_seconds: Optional[float] = None
    ) -> bool:
        """Reject message processing with retry or dead letter handling.
        
        Args:
            queue_name: Queue the message came from
            message_id: Message identifier to reject
            reason: Reason for rejection
            retry: Whether message should be retried
            delay_seconds: Optional delay before retry
            
        Returns:
            True if rejection was processed successfully
            
        Raises:
            QueueError: If rejection handling fails
        """
        ...

    # ===========================================
    # Queue Management Operations
    # ===========================================
    
    @abstractmethod
    async def create_queue(
        self,
        queue_name: str,
        configuration: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create a new queue with specified configuration.
        
        Args:
            queue_name: Name for the new queue
            configuration: Queue configuration options:
                - max_size: Maximum queue size (None for unlimited)
                - ttl_seconds: Message TTL (None for no expiration)
                - dead_letter_queue: Dead letter queue name
                - max_retries: Maximum retry attempts
                - priority_enabled: Whether to support priority ordering
                
        Returns:
            True if queue was created successfully
            
        Raises:
            QueueError: If queue creation fails
        """
        ...
    
    @abstractmethod
    async def delete_queue(
        self,
        queue_name: str,
        force: bool = False
    ) -> bool:
        """Delete a queue and optionally its messages.
        
        Args:
            queue_name: Queue to delete
            force: Whether to delete even if queue contains messages
            
        Returns:
            True if queue was deleted successfully
            
        Raises:
            QueueError: If queue deletion fails
        """
        ...
    
    @abstractmethod
    async def purge_queue(
        self,
        queue_name: str
    ) -> int:
        """Remove all messages from a queue.
        
        Args:
            queue_name: Queue to purge
            
        Returns:
            Number of messages removed
            
        Raises:
            QueueError: If purge operation fails
        """
        ...
    
    @abstractmethod
    async def list_queues(self) -> List[str]:
        """List all available queues.
        
        Returns:
            List of queue names
            
        Raises:
            QueueError: If queue listing fails
        """
        ...

    # ===========================================
    # Queue Information Operations
    # ===========================================
    
    @abstractmethod
    async def get_queue_size(self, queue_name: str) -> int:
        """Get the current number of messages in queue.
        
        Args:
            queue_name: Queue to check
            
        Returns:
            Number of messages currently in queue
            
        Raises:
            QueueError: If size check fails
        """
        ...
    
    @abstractmethod
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """Get comprehensive queue statistics.
        
        Args:
            queue_name: Queue to analyze
            
        Returns:
            Dict with queue statistics:
            - total_messages: Current message count
            - in_flight_messages: Messages currently being processed
            - dead_letter_messages: Messages in dead letter queue
            - enqueue_rate: Messages per second enqueue rate
            - dequeue_rate: Messages per second dequeue rate
            - average_processing_time: Average message processing time
            - oldest_message_age: Age of oldest message in seconds
            - failed_processing_count: Count of failed message processing
            
        Raises:
            QueueError: If statistics retrieval fails
        """
        ...
    
    @abstractmethod
    async def peek_messages(
        self,
        queue_name: str,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Peek at messages without dequeuing them.
        
        Args:
            queue_name: Queue to peek into
            count: Maximum messages to peek
            
        Returns:
            List of message objects (same format as dequeue)
            
        Raises:
            QueueError: If peek operation fails
        """
        ...

    # ===========================================
    # Dead Letter Queue Operations
    # ===========================================
    
    @abstractmethod
    async def get_dead_letter_messages(
        self,
        queue_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get messages from dead letter queue for analysis.
        
        Args:
            queue_name: Main queue name (dead letter queue derived)
            limit: Maximum messages to retrieve
            
        Returns:
            List of dead letter message objects with failure information
            
        Raises:
            QueueError: If retrieval fails
        """
        ...
    
    @abstractmethod
    async def requeue_dead_letter_message(
        self,
        queue_name: str,
        message_id: str,
        target_queue: Optional[str] = None
    ) -> bool:
        """Move message from dead letter queue back to main queue.
        
        Args:
            queue_name: Original queue name
            message_id: Dead letter message to requeue
            target_queue: Optional different target queue
            
        Returns:
            True if requeue was successful
            
        Raises:
            QueueError: If requeue operation fails
        """
        ...
    
    @abstractmethod
    async def clear_dead_letter_queue(
        self,
        queue_name: str,
        older_than_hours: Optional[int] = None
    ) -> int:
        """Clear messages from dead letter queue.
        
        Args:
            queue_name: Main queue name (dead letter queue derived)
            older_than_hours: Only clear messages older than specified hours
            
        Returns:
            Number of messages cleared
            
        Raises:
            QueueError: If clear operation fails
        """
        ...

    # ===========================================
    # Connection and Health Operations
    # ===========================================
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check queue system health status.
        
        Returns:
            Dict with health information:
            - healthy: Boolean overall health status
            - connection_status: Queue backend connection status
            - total_queues: Number of queues
            - total_messages: Total messages across all queues
            - response_time_ms: Health check response time
            - last_check_at: Timestamp of health check
            
        Raises:
            QueueError: If health check fails
        """
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Close queue connections and cleanup resources.
        
        Gracefully closes all connections and releases resources.
        After calling this method, the queue instance should not be used.
        
        Raises:
            QueueError: If cleanup fails
        """
        ...


# ===========================================
# Queue-Specific Exceptions  
# ===========================================

class QueueError(Exception):
    """Base exception for queue operations."""
    pass


class QueueConnectionError(QueueError):
    """Queue backend connection failed."""
    pass


class QueueNotFoundError(QueueError):
    """Specified queue does not exist."""
    pass


class QueueFullError(QueueError):
    """Queue has reached maximum capacity."""
    pass


class MessageNotFoundError(QueueError):
    """Specified message was not found in queue."""
    pass


class DuplicateQueueError(QueueError):
    """Attempted to create queue that already exists."""
    pass