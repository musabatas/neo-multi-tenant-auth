"""
Events Feature Module

Provides comprehensive event-driven architecture for the NeoMultiTenant platform.
Designed for ultimate flexibility with runtime schema discovery, dynamic event routing, 
and unlimited extensibility.

Core Components:
- Event Sourcing with full audit trail and replay capability
- Multi-Schema support (Admin + tenant template schemas)
- Queue Integration with Redis streams/queues
- Dynamic Event-Action mapping via subscriptions
- Performance monitoring and error tracking
- Retry logic with exponential backoff

Usage:
    from neo_commons.features.events import Event, EventRepository
    
    # Create and store an event
    event = Event.create(
        event_type="tenants.created",
        aggregate_id=tenant_id,
        aggregate_type="tenant",
        event_data={"name": "Acme Corp"}
    )
    await event_repository.save(event, schema="admin")
"""

from .domain.entities.event import Event, EventStatus, EventPriority
from .domain.entities.event_metadata import EventMetadata  
from .domain.value_objects.event_id import EventId
from .domain.value_objects.event_type import EventType
from .domain.value_objects.correlation_id import CorrelationId
from .domain.value_objects.aggregate_reference import AggregateReference
from .application.protocols.event_repository import EventRepositoryProtocol
from .application.protocols.event_publisher import EventPublisherProtocol
from .application.protocols.event_processor import EventProcessorProtocol
from .infrastructure import AsyncPGEventRepository, RedisEventPublisher, RedisEventProcessor
from .api import CreateEventRequest, EventResponse

__all__ = [
    # Domain layer
    "Event",
    "EventStatus",
    "EventPriority", 
    "EventMetadata",
    "EventId", 
    "EventType",
    "CorrelationId",
    "AggregateReference",
    # Application layer
    "EventRepositoryProtocol",
    "EventPublisherProtocol",
    "EventProcessorProtocol",
    # Infrastructure layer
    "AsyncPGEventRepository",
    "RedisEventPublisher",
    "RedisEventProcessor",
    # API layer
    "CreateEventRequest",
    "EventResponse",
]