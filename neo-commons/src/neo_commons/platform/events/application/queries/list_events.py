"""List events query with filtering."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from ...domain.entities.event import Event, EventStatus, EventPriority
from ...domain.value_objects.event_type import EventType
from ...domain.value_objects.correlation_id import CorrelationId
from ..protocols.event_repository import EventRepositoryProtocol


@dataclass
class ListEventsQuery:
    """Query to list events with filtering options."""
    
    schema: str
    
    # Filtering options
    event_types: Optional[List[str]] = None
    statuses: Optional[List[str]] = None
    priorities: Optional[List[str]] = None
    aggregate_id: Optional[UUID] = None
    aggregate_type: Optional[str] = None
    correlation_id: Optional[CorrelationId] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    
    # Pagination
    limit: int = 100
    offset: int = 0
    
    # Include count
    include_count: bool = False
    
    def __post_init__(self):
        """Validate and convert query data."""
        if not self.schema or not self.schema.strip():
            raise ValueError("schema is required")
        
        if self.limit <= 0:
            raise ValueError("limit must be positive")
        
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        
        # Convert string lists to enum lists
        if self.event_types:
            self.event_types = [EventType(et) for et in self.event_types]
        
        if self.statuses:
            self.statuses = [EventStatus(s) for s in self.statuses]
        
        if self.priorities:
            self.priorities = [EventPriority(p) for p in self.priorities]


@dataclass
class ListEventsResult:
    """Result of list events query."""
    
    events: List[Event]
    total_count: Optional[int] = None
    
    @property
    def has_more(self) -> bool:
        """Check if there are more events available."""
        if self.total_count is None:
            return len(self.events) > 0
        return len(self.events) < self.total_count


class ListEventsQueryHandler:
    """Handler for ListEventsQuery."""
    
    def __init__(self, repository: EventRepositoryProtocol):
        self.repository = repository
    
    async def execute(self, query: ListEventsQuery) -> ListEventsResult:
        """
        Execute the list events query.
        
        Args:
            query: Query to execute
            
        Returns:
            List of events with optional total count
        """
        # Get events
        events = await self.repository.list_events(
            schema=query.schema,
            event_types=query.event_types,
            statuses=query.statuses,
            priorities=query.priorities,
            aggregate_id=query.aggregate_id,
            aggregate_type=query.aggregate_type,
            correlation_id=query.correlation_id,
            from_date=query.from_date,
            to_date=query.to_date,
            limit=query.limit,
            offset=query.offset
        )
        
        # Get count if requested
        total_count = None
        if query.include_count:
            total_count = await self.repository.count_events(
                schema=query.schema,
                event_types=query.event_types,
                statuses=query.statuses,
                priorities=query.priorities,
                aggregate_id=query.aggregate_id,
                aggregate_type=query.aggregate_type,
                correlation_id=query.correlation_id,
                from_date=query.from_date,
                to_date=query.to_date
            )
        
        return ListEventsResult(
            events=events,
            total_count=total_count
        )