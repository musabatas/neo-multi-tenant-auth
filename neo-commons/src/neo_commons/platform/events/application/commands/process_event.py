"""Process event command for event processing."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from ...domain.entities.event import Event, EventStatus
from ...domain.value_objects.event_id import EventId
from ..protocols.event_repository import EventRepositoryProtocol


@dataclass
class ProcessEventCommand:
    """Command to process an event."""
    
    event_id: EventId
    schema: str
    start_processing: bool = True
    
    def __post_init__(self):
        """Validate command data."""
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")


@dataclass
class CompleteEventProcessingCommand:
    """Command to mark event processing as completed."""
    
    event_id: EventId
    schema: str
    
    def __post_init__(self):
        """Validate command data."""
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")


@dataclass
class FailEventProcessingCommand:
    """Command to mark event processing as failed."""
    
    event_id: EventId
    schema: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Validate command data."""
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")
        
        if not self.error_message or not self.error_message.strip():
            raise ValueError("error_message is required")


class ProcessEventCommandHandler:
    """Handler for event processing commands."""
    
    def __init__(self, repository: EventRepositoryProtocol):
        self.repository = repository
    
    async def start_processing(self, command: ProcessEventCommand) -> Event:
        """
        Start processing an event.
        
        Args:
            command: Command to execute
            
        Returns:
            Updated event
            
        Raises:
            ValueError: If event not found or cannot be processed
        """
        event = await self.repository.get_by_id(command.event_id, command.schema)
        if not event:
            raise ValueError(f"Event not found: {command.event_id}")
        
        if command.start_processing:
            event.start_processing()
        
        return await self.repository.update(event, command.schema)
    
    async def complete_processing(self, command: CompleteEventProcessingCommand) -> Event:
        """
        Complete event processing successfully.
        
        Args:
            command: Command to execute
            
        Returns:
            Updated event
            
        Raises:
            ValueError: If event not found or not in processing state
        """
        event = await self.repository.get_by_id(command.event_id, command.schema)
        if not event:
            raise ValueError(f"Event not found: {command.event_id}")
        
        event.complete_processing()
        return await self.repository.update(event, command.schema)
    
    async def fail_processing(self, command: FailEventProcessingCommand) -> Event:
        """
        Fail event processing.
        
        Args:
            command: Command to execute
            
        Returns:
            Updated event
            
        Raises:
            ValueError: If event not found or not in processing state
        """
        event = await self.repository.get_by_id(command.event_id, command.schema)
        if not event:
            raise ValueError(f"Event not found: {command.event_id}")
        
        event.fail_processing(command.error_message, command.error_details)
        return await self.repository.update(event, command.schema)