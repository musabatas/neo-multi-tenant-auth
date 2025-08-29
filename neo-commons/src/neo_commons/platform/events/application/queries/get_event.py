"""Get single event query."""

from dataclasses import dataclass
from typing import Optional

from ...domain.entities.event import Event
from ...domain.value_objects.event_id import EventId
from ..protocols.event_repository import EventRepositoryProtocol


@dataclass
class GetEventQuery:
    """Query to get a single event by ID."""
    
    event_id: EventId
    schema: str
    
    def __post_init__(self):
        """Validate query data."""
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")


class GetEventQueryHandler:
    """Handler for GetEventQuery."""
    
    def __init__(self, repository: EventRepositoryProtocol):
        self.repository = repository
    
    async def execute(self, query: GetEventQuery) -> Optional[Event]:
        """
        Execute the get event query.
        
        Args:
            query: Query to execute
            
        Returns:
            Event if found, None otherwise
        """
        return await self.repository.get_by_id(query.event_id, query.schema)