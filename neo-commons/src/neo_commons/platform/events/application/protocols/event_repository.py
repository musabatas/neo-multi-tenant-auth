"""Event repository protocol for data persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from ...domain.entities.event import Event, EventStatus, EventPriority
from ...domain.value_objects.event_id import EventId
from ...domain.value_objects.event_type import EventType
from ...domain.value_objects.correlation_id import CorrelationId


class EventRepositoryProtocol(ABC):
    """Protocol for event persistence operations."""
    
    @abstractmethod
    async def save(self, event: Event, schema: str) -> Event:
        """
        Save an event to the specified schema.
        
        Args:
            event: Event to save
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Saved event with any database-generated fields
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, event_id: EventId, schema: str) -> Optional[Event]:
        """
        Get event by ID from specified schema.
        
        Args:
            event_id: Event identifier
            schema: Database schema name
            
        Returns:
            Event if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def update(self, event: Event, schema: str) -> Event:
        """
        Update an existing event.
        
        Args:
            event: Event to update
            schema: Database schema name
            
        Returns:
            Updated event
        """
        ...
    
    @abstractmethod
    async def list_events(
        self,
        schema: str,
        event_types: Optional[List[EventType]] = None,
        statuses: Optional[List[EventStatus]] = None,
        priorities: Optional[List[EventPriority]] = None,
        aggregate_id: Optional[UUID] = None,
        aggregate_type: Optional[str] = None,
        correlation_id: Optional[CorrelationId] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Event]:
        """
        List events with filtering options.
        
        Args:
            schema: Database schema name
            event_types: Filter by event types
            statuses: Filter by statuses
            priorities: Filter by priorities
            aggregate_id: Filter by aggregate ID
            aggregate_type: Filter by aggregate type
            correlation_id: Filter by correlation ID
            from_date: Filter events created after this date
            to_date: Filter events created before this date
            limit: Maximum number of events to return
            offset: Number of events to skip
            
        Returns:
            List of events matching criteria
        """
        ...
    
    @abstractmethod
    async def count_events(
        self,
        schema: str,
        event_types: Optional[List[EventType]] = None,
        statuses: Optional[List[EventStatus]] = None,
        priorities: Optional[List[EventPriority]] = None,
        aggregate_id: Optional[UUID] = None,
        aggregate_type: Optional[str] = None,
        correlation_id: Optional[CorrelationId] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> int:
        """
        Count events matching criteria.
        
        Args:
            schema: Database schema name
            event_types: Filter by event types
            statuses: Filter by statuses
            priorities: Filter by priorities
            aggregate_id: Filter by aggregate ID
            aggregate_type: Filter by aggregate type
            correlation_id: Filter by correlation ID
            from_date: Filter events created after this date
            to_date: Filter events created before this date
            
        Returns:
            Number of events matching criteria
        """
        ...
    
    @abstractmethod
    async def get_event_history(
        self,
        correlation_id: CorrelationId,
        schema: str,
        limit: int = 100
    ) -> List[Event]:
        """
        Get complete event history for a correlation ID.
        
        Args:
            correlation_id: Correlation ID to track
            schema: Database schema name
            limit: Maximum number of events to return
            
        Returns:
            List of events in chronological order
        """
        ...
    
    @abstractmethod
    async def get_pending_events(
        self,
        schema: str,
        priority_order: bool = True,
        limit: int = 100
    ) -> List[Event]:
        """
        Get pending events ready for processing.
        
        Args:
            schema: Database schema name
            priority_order: Whether to order by priority (highest first)
            limit: Maximum number of events to return
            
        Returns:
            List of pending events
        """
        ...
    
    @abstractmethod
    async def get_failed_events(
        self,
        schema: str,
        can_retry: bool = True,
        limit: int = 100
    ) -> List[Event]:
        """
        Get failed events for retry processing.
        
        Args:
            schema: Database schema name
            can_retry: Whether to only return events that can be retried
            limit: Maximum number of events to return
            
        Returns:
            List of failed events
        """
        ...
    
    @abstractmethod
    async def delete(self, event_id: EventId, schema: str) -> bool:
        """
        Delete an event (soft delete by setting deleted_at).
        
        Args:
            event_id: Event identifier
            schema: Database schema name
            
        Returns:
            True if event was deleted, False if not found
        """
        ...