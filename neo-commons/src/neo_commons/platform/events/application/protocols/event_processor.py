"""Event processor protocol for queue consumption."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional, Callable, Awaitable, Dict, Any

from ...domain.entities.event import Event


EventHandler = Callable[[Event, str], Awaitable[None]]


class EventProcessorProtocol(ABC):
    """Protocol for processing events from message queues."""
    
    @abstractmethod
    async def consume(
        self,
        queue_name: str,
        consumer_group: str,
        handler: EventHandler,
        max_events: int = 10,
        timeout_ms: int = 5000
    ) -> None:
        """
        Consume events from queue and process them with handler.
        
        Args:
            queue_name: Queue to consume from
            consumer_group: Consumer group identifier
            handler: Async function to handle each event
            max_events: Maximum events to process per batch
            timeout_ms: Timeout for waiting for events
        """
        ...
    
    @abstractmethod
    async def consume_batch(
        self,
        queue_name: str,
        consumer_group: str,
        batch_handler: Callable[[List[Event], str], Awaitable[None]],
        batch_size: int = 10,
        timeout_ms: int = 5000
    ) -> None:
        """
        Consume events in batches and process them.
        
        Args:
            queue_name: Queue to consume from
            consumer_group: Consumer group identifier
            batch_handler: Async function to handle event batches
            batch_size: Number of events per batch
            timeout_ms: Timeout for waiting for events
        """
        ...
    
    @abstractmethod
    async def ack(self, event: Event, message_id: str) -> None:
        """
        Acknowledge successful processing of an event.
        
        Args:
            event: Event that was processed
            message_id: Message ID from the queue
        """
        ...
    
    @abstractmethod
    async def nack(
        self,
        event: Event,
        message_id: str,
        error_message: str,
        retry: bool = True
    ) -> None:
        """
        Negative acknowledge - event processing failed.
        
        Args:
            event: Event that failed processing
            message_id: Message ID from the queue
            error_message: Error description
            retry: Whether to retry the event
        """
        ...
    
    @abstractmethod
    async def start_consumer(
        self,
        queue_name: str,
        consumer_group: str,
        handler: EventHandler,
        **kwargs
    ) -> None:
        """
        Start a long-running consumer for a queue.
        
        Args:
            queue_name: Queue to consume from
            consumer_group: Consumer group identifier
            handler: Event handler function
            **kwargs: Additional consumer configuration
        """
        ...
    
    @abstractmethod
    async def stop_consumer(self, queue_name: str, consumer_group: str) -> None:
        """
        Stop a running consumer.
        
        Args:
            queue_name: Queue name
            consumer_group: Consumer group identifier
        """
        ...
    
    @abstractmethod
    async def get_consumer_stats(
        self,
        queue_name: str,
        consumer_group: str
    ) -> Dict[str, Any]:
        """
        Get statistics for a consumer.
        
        Args:
            queue_name: Queue name
            consumer_group: Consumer group identifier
            
        Returns:
            Dictionary with consumer statistics
        """
        ...
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if the processor is healthy and can consume messages.
        
        Returns:
            True if healthy, False otherwise
        """
        ...