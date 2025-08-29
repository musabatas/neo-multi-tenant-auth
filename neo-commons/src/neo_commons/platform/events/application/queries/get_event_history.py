"""Get event history query for correlation tracking."""

from dataclasses import dataclass
from typing import List

from ...domain.entities.event import Event
from ...domain.value_objects.correlation_id import CorrelationId
from ..protocols.event_repository import EventRepositoryProtocol


@dataclass
class GetEventHistoryQuery:
    """Query to get complete event history for a correlation ID."""
    
    correlation_id: CorrelationId
    schema: str
    limit: int = 100
    
    def __post_init__(self):
        """Validate query data."""
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")
        
        if self.limit <= 0:
            raise ValueError("limit must be positive")


class GetEventHistoryQueryHandler:
    """Handler for GetEventHistoryQuery."""
    
    def __init__(self, repository: EventRepositoryProtocol):
        self.repository = repository
    
    async def execute(self, query: GetEventHistoryQuery) -> List[Event]:
        """
        Execute the get event history query.
        
        Args:
            query: Query to execute
            
        Returns:
            List of events in chronological order
        """
        return await self.repository.get_event_history(
            correlation_id=query.correlation_id,
            schema=query.schema,
            limit=query.limit
        )