"""
Events Domain Layer

Contains pure business logic for event sourcing and processing.
All domain entities, value objects, and events are defined here.

This layer is completely independent of infrastructure concerns
and contains only the core business rules for event management.
"""

from .entities.event import Event
from .entities.event_metadata import EventMetadata
from .value_objects.event_id import EventId
from .value_objects.event_type import EventType
from .value_objects.correlation_id import CorrelationId
from .value_objects.aggregate_reference import AggregateReference

__all__ = [
    "Event",
    "EventMetadata", 
    "EventId",
    "EventType",
    "CorrelationId",
    "AggregateReference",
]