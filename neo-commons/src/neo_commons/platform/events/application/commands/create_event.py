"""Create event command for event sourcing."""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from ...domain.entities.event import Event, EventPriority
from ...domain.entities.event_metadata import EventMetadata
from ...domain.value_objects.event_id import EventId
from ...domain.value_objects.event_type import EventType
from ...domain.value_objects.correlation_id import CorrelationId
from ..protocols.event_repository import EventRepositoryProtocol
from ..protocols.event_publisher import EventPublisherProtocol


@dataclass
class CreateEventCommand:
    """Command to create and store a new event."""
    
    # Required fields
    event_type: str
    aggregate_id: UUID
    aggregate_type: str
    event_data: Dict[str, Any]
    schema: str
    
    # Optional fields
    event_metadata: Optional[EventMetadata] = None
    correlation_id: Optional[CorrelationId] = None
    causation_id: Optional[EventId] = None
    priority: EventPriority = EventPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    publish_to_queue: bool = True
    queue_name: Optional[str] = None
    partition_key: Optional[str] = None
    
    def __post_init__(self):
        """Validate command data."""
        if not self.event_type or not self.event_type.strip():
            raise ValueError("event_type is required")
        
        if not self.aggregate_type or not self.aggregate_type.strip():
            raise ValueError("aggregate_type is required")
        
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")
        
        if not isinstance(self.aggregate_id, UUID):
            try:
                self.aggregate_id = UUID(str(self.aggregate_id))
            except (ValueError, TypeError):
                raise ValueError(f"aggregate_id must be a valid UUID, got: {self.aggregate_id}")


class CreateEventCommandHandler:
    """Handler for CreateEventCommand."""
    
    def __init__(
        self,
        repository: EventRepositoryProtocol,
        publisher: Optional[EventPublisherProtocol] = None
    ):
        self.repository = repository
        self.publisher = publisher
    
    async def execute(self, command: CreateEventCommand) -> Event:
        """
        Execute the create event command.
        
        Args:
            command: Command to execute
            
        Returns:
            Created event
            
        Raises:
            ValueError: If command validation fails
            Exception: If event creation or publishing fails
        """
        # Create the event
        event = Event.create(
            event_type=command.event_type,
            aggregate_id=command.aggregate_id,
            aggregate_type=command.aggregate_type,
            event_data=command.event_data,
            event_metadata=command.event_metadata,
            correlation_id=command.correlation_id,
            causation_id=command.causation_id,
            priority=command.priority,
            scheduled_at=command.scheduled_at
        )
        
        # Save to repository
        saved_event = await self.repository.save(event, command.schema)
        
        # Publish to queue if requested and publisher available
        if command.publish_to_queue and self.publisher:
            try:
                message_id = await self.publisher.publish(
                    event=saved_event,
                    schema=command.schema,
                    queue_name=command.queue_name,
                    partition_key=command.partition_key
                )
                
                # Update event with queue info
                saved_event.message_id = message_id
                saved_event.queue_name = command.queue_name or f"events:{command.schema}"
                saved_event.partition_key = command.partition_key
                
                # Save updated event
                saved_event = await self.repository.update(saved_event, command.schema)
                
            except Exception as e:
                # Log error but don't fail the command
                # Event was created successfully, queue publishing failed
                saved_event.error_message = f"Failed to publish to queue: {str(e)}"
                saved_event = await self.repository.update(saved_event, command.schema)
        
        return saved_event