"""Retry event command for failed event processing."""

from dataclasses import dataclass

from ...domain.entities.event import Event
from ...domain.value_objects.event_id import EventId
from ..protocols.event_repository import EventRepositoryProtocol
from ..protocols.event_publisher import EventPublisherProtocol


@dataclass
class RetryEventCommand:
    """Command to retry a failed event."""
    
    event_id: EventId
    schema: str
    republish_to_queue: bool = True
    
    def __post_init__(self):
        """Validate command data."""
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")


class RetryEventCommandHandler:
    """Handler for RetryEventCommand."""
    
    def __init__(
        self,
        repository: EventRepositoryProtocol,
        publisher: EventPublisherProtocol = None
    ):
        self.repository = repository
        self.publisher = publisher
    
    async def execute(self, command: RetryEventCommand) -> Event:
        """
        Execute the retry event command.
        
        Args:
            command: Command to execute
            
        Returns:
            Updated event ready for retry
            
        Raises:
            ValueError: If event not found or cannot be retried
        """
        # Get the event
        event = await self.repository.get_by_id(command.event_id, command.schema)
        if not event:
            raise ValueError(f"Event not found: {command.event_id}")
        
        # Check if event can be retried
        if not event.can_be_retried():
            raise ValueError(
                f"Event cannot be retried. Status: {event.status.value}, "
                f"Retry count: {event.retry_count}/{event.max_retries}"
            )
        
        # Retry the event
        event.retry_processing()
        
        # Save updated event
        updated_event = await self.repository.update(event, command.schema)
        
        # Republish to queue if requested and publisher available
        if command.republish_to_queue and self.publisher:
            try:
                message_id = await self.publisher.publish(
                    event=updated_event,
                    schema=command.schema,
                    queue_name=updated_event.queue_name
                )
                
                # Update event with new message ID
                updated_event.message_id = message_id
                updated_event = await self.repository.update(updated_event, command.schema)
                
            except Exception as e:
                # Mark as failed again if republishing fails
                updated_event.fail_processing(
                    error_message=f"Failed to republish for retry: {str(e)}",
                    error_details={"retry_republish_error": True}
                )
                updated_event = await self.repository.update(updated_event, command.schema)
                raise
        
        return updated_event