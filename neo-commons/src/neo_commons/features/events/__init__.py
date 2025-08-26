"""Events feature module for neo-commons.

This module provides event publishing and webhook delivery capabilities
following the Feature-First + Clean Core architecture pattern.

Core components:
- Domain entities: DomainEvent, WebhookEndpoint, WebhookEventType, WebhookDelivery
- Services: EventPublisher, WebhookDelivery, EventDispatcher
- Repositories: Event storage and webhook configuration
- Adapters: HTTP delivery, queue integration

Usage:
    from neo_commons.features.events import EventPublisher, DomainEvent
    
    # Publish an event
    event = DomainEvent(...)
    await event_publisher.publish(event)
"""

# Import domain entities
from .entities.domain_event import DomainEvent
from .entities.webhook_endpoint import WebhookEndpoint
from .entities.webhook_event_type import WebhookEventType
from .entities.webhook_delivery import WebhookDelivery, WebhookDeliveryAttempt, DeliveryStatus
from .entities.webhook_subscription import WebhookSubscription
from .entities.event_archive import (
    EventArchive, ArchivalRule, ArchivalJob, 
    ArchivalStatus, ArchivalPolicy, StorageType
)

# Import protocols for dependency injection
from .entities.protocols import (
    EventRepository,
    WebhookEndpointRepository,
    WebhookEventTypeRepository, 
    WebhookDeliveryRepository,
    EventPublisher,
    WebhookDeliveryService,
    EventDispatcher
)

# Import services
from .services.event_publisher_service import EventPublisherService
from .services.webhook_delivery_service import WebhookDeliveryService as WebhookDeliveryServiceImpl
from .services.webhook_endpoint_service import WebhookEndpointService
from .services.webhook_event_type_service import WebhookEventTypeService
from .services.event_dispatcher_service import EventDispatcherService
from .services.webhook_metrics_service import WebhookMetricsService
from .services.webhook_monitoring_service import WebhookMonitoringService
from .services.event_archival_service import EventArchivalService

# Import repositories
from .repositories.domain_event_repository import DomainEventDatabaseRepository
from .repositories.webhook_endpoint_repository import WebhookEndpointDatabaseRepository
from .repositories.webhook_event_type_repository import WebhookEventTypeDatabaseRepository
from .repositories.webhook_delivery_repository import WebhookDeliveryDatabaseRepository
from .repositories.webhook_subscription_repository import WebhookSubscriptionRepository
from .repositories.event_archival_repository import (
    EventArchivalRepository, ArchivalRuleRepository, ArchivalJobRepository,
    EventArchivalRepositoryImpl, ArchivalRuleRepositoryImpl, ArchivalJobRepositoryImpl
)

# Import adapters
from .adapters.http_webhook_adapter import HttpWebhookAdapter

__all__ = [
    # Entities
    "DomainEvent",
    "WebhookEndpoint", 
    "WebhookEventType",
    "WebhookDelivery",
    "WebhookDeliveryAttempt",
    "DeliveryStatus",
    "WebhookSubscription",
    
    # Archival entities
    "EventArchive",
    "ArchivalRule",
    "ArchivalJob", 
    "ArchivalStatus",
    "ArchivalPolicy",
    "StorageType",
    
    # Protocols
    "EventRepository",
    "WebhookEndpointRepository",
    "WebhookEventTypeRepository",
    "WebhookDeliveryRepository", 
    "EventPublisher",
    "WebhookDeliveryService",
    "EventDispatcher",
    
    # Services
    "EventPublisherService",
    "WebhookDeliveryServiceImpl",
    "WebhookEndpointService",
    "WebhookEventTypeService",
    "EventDispatcherService",
    "WebhookMetricsService",
    "WebhookMonitoringService", 
    "EventArchivalService",
    
    # Repositories
    "DomainEventDatabaseRepository",
    "WebhookEndpointDatabaseRepository",
    "WebhookEventTypeDatabaseRepository", 
    "WebhookDeliveryDatabaseRepository",
    "WebhookSubscriptionRepository",
    
    # Archival repositories
    "EventArchivalRepository",
    "ArchivalRuleRepository", 
    "ArchivalJobRepository",
    "EventArchivalRepositoryImpl",
    "ArchivalRuleRepositoryImpl",
    "ArchivalJobRepositoryImpl",
    
    # Adapters
    "HttpWebhookAdapter",
]