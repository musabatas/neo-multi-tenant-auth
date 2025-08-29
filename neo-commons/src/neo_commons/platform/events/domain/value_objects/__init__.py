"""Value objects for events domain."""

from .event_id import EventId
from .event_type import EventType
from .correlation_id import CorrelationId
from .aggregate_reference import AggregateReference

__all__ = [
    "EventId",
    "EventType", 
    "CorrelationId",
    "AggregateReference",
]