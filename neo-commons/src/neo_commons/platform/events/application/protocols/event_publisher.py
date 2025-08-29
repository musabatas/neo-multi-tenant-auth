"""Event publisher protocol for queue integration."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ...domain.entities.event import Event


class EventPublisherProtocol(ABC):
    """Protocol for publishing events to message queues."""
    
    @abstractmethod
    async def publish(
        self,
        event: Event,
        schema: str,
        queue_name: Optional[str] = None,
        partition_key: Optional[str] = None
    ) -> str:
        """
        Publish event to message queue.
        
        Args:
            event: Event to publish
            schema: Database schema context 
            queue_name: Optional specific queue name
            partition_key: Optional partition key for queue partitioning
            
        Returns:
            Message ID from the queue system
        """
        ...
    
    @abstractmethod
    async def publish_batch(
        self,
        events: list[Event],
        schema: str,
        queue_name: Optional[str] = None
    ) -> list[str]:
        """
        Publish multiple events in a batch.
        
        Args:
            events: List of events to publish
            schema: Database schema context
            queue_name: Optional specific queue name
            
        Returns:
            List of message IDs from the queue system
        """
        ...
    
    @abstractmethod
    async def get_queue_stats(self, queue_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific queue.
        
        Args:
            queue_name: Queue name to get stats for
            
        Returns:
            Dictionary with queue statistics (pending, processed, failed, etc.)
        """
        ...
    
    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if the publisher is healthy and can publish messages.
        
        Returns:
            True if healthy, False otherwise
        """
        ...