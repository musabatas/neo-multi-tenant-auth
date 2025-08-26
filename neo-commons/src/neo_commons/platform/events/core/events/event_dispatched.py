"""Event dispatched domain event for platform events infrastructure.

This module defines the EventDispatched domain event that represents when
an event has been successfully dispatched by the platform infrastructure.

Following maximum separation architecture - this file contains ONLY EventDispatched.
Pure platform infrastructure event - represents platform operation, not business logic.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from uuid import UUID

from ..entities.domain_event import DomainEvent
from ..value_objects import EventType, EventId
from .....core.value_objects import UserId
from .....utils import generate_uuid_v7


@dataclass
class EventDispatched(DomainEvent):
    """Platform domain event representing when an event has been dispatched.
    
    This is a platform infrastructure event that tracks when the event platform
    successfully dispatches a business domain event to registered action handlers.
    
    Event type: 'platform.event_dispatched'
    Aggregate: The original business domain event that was dispatched
    """
    
    # Original event information (must use field() since parent has default fields)
    original_event_id: EventId = field(default=None)
    original_event_type: str = field(default="")  # The business event type that was dispatched
    dispatch_method: str = field(default="async")  # How it was dispatched (sync, async, queued)
    
    def __init__(self,
                 original_event_id: EventId,
                 original_event_type: str,
                 dispatch_method: str = "async",
                 actions_triggered: int = 0,
                 dispatch_latency_ms: Optional[int] = None,
                 correlation_id: Optional[UUID] = None,
                 triggered_by_user_id: Optional[UserId] = None,
                 **kwargs):
        """Initialize EventDispatched domain event.
        
        Args:
            original_event_id: ID of the original business event that was dispatched
            original_event_type: Type of the original business event (e.g., 'organization.created')
            dispatch_method: Method used for dispatch (sync, async, queued)
            actions_triggered: Number of actions that were triggered by this dispatch
            dispatch_latency_ms: Time taken to dispatch the event in milliseconds
            correlation_id: Correlation ID for event tracing
            triggered_by_user_id: User who triggered the original event
            **kwargs: Additional DomainEvent fields
        """
        # Set platform event data
        event_data = {
            "original_event_id": str(original_event_id.value),
            "original_event_type": original_event_type,
            "dispatch_method": dispatch_method,
            "actions_triggered": actions_triggered,
        }
        
        # Add optional performance data
        if dispatch_latency_ms is not None:
            event_data["dispatch_latency_ms"] = dispatch_latency_ms
        
        # Store additional fields
        self.original_event_id = original_event_id
        self.original_event_type = original_event_type
        self.dispatch_method = dispatch_method
        
        # Initialize base domain event
        super().__init__(
            event_type=EventType("platform.event_dispatched"),
            aggregate_id=original_event_id.value,  # Use original event ID as aggregate
            aggregate_type="domain_event",
            event_data=event_data,
            correlation_id=correlation_id,
            triggered_by_user_id=triggered_by_user_id,
            **kwargs
        )
    
    @property
    def actions_triggered(self) -> int:
        """Get number of actions triggered by this dispatch."""
        return self.event_data.get("actions_triggered", 0)
    
    @property
    def dispatch_latency_ms(self) -> Optional[int]:
        """Get dispatch latency in milliseconds."""
        return self.event_data.get("dispatch_latency_ms")
    
    def is_synchronous_dispatch(self) -> bool:
        """Check if this was a synchronous dispatch."""
        return self.dispatch_method == "sync"
    
    def is_asynchronous_dispatch(self) -> bool:
        """Check if this was an asynchronous dispatch."""
        return self.dispatch_method == "async"
    
    def is_queued_dispatch(self) -> bool:
        """Check if this was a queued dispatch."""
        return self.dispatch_method == "queued"
    
    @classmethod
    def create_for_event(cls,
                        original_event_id: EventId, 
                        original_event_type: str,
                        dispatch_method: str = "async",
                        actions_triggered: int = 0,
                        dispatch_latency_ms: Optional[int] = None,
                        correlation_id: Optional[UUID] = None,
                        triggered_by_user_id: Optional[UserId] = None) -> 'EventDispatched':
        """Factory method to create EventDispatched for a specific event.
        
        This factory ensures consistent creation of EventDispatched events
        with proper UUIDv7 compliance and platform metadata.
        """
        return cls(
            original_event_id=original_event_id,
            original_event_type=original_event_type,
            dispatch_method=dispatch_method,
            actions_triggered=actions_triggered,
            dispatch_latency_ms=dispatch_latency_ms,
            correlation_id=correlation_id or generate_uuid_v7(),
            triggered_by_user_id=triggered_by_user_id
        )