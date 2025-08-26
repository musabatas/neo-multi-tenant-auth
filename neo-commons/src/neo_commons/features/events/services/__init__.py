"""Event services.

Provides business logic services using single-responsibility principle.
Main EventDispatcher acts as orchestrator for specialized services.
"""

# Main orchestrator service
from .event_dispatcher_service import EventDispatcherService

# Specialized single-responsibility services
from .event_publisher_service import EventPublisherService
from .webhook_delivery_service import WebhookDeliveryService
from .webhook_endpoint_service import WebhookEndpointService
from .webhook_event_type_service import WebhookEventTypeService
from .webhook_dead_letter_service import WebhookDeadLetterService

# Metrics and monitoring services
from .webhook_metrics_service import WebhookMetricsService
from .webhook_monitoring_service import WebhookMonitoringService

# Configuration service
from .webhook_config_service import (
    WebhookConfigService,
    WebhookConfig,
    WebhookPerformanceConfig,
    WebhookDatabaseConfig,
    WebhookDeliveryConfig,
    WebhookValidationConfig,
    WebhookMonitoringConfig,
    get_webhook_config_service,
    get_webhook_config
)

# Archival services
from .archival_compression_service import ArchivalCompressionService
from .multi_region_archival_service import MultiRegionArchivalService

# Event sourcing optimization
from .event_sourcing_optimization_service import EventSourcingOptimizationService

__all__ = [
    # Main orchestrator service (use this for full functionality)
    "EventDispatcherService",
    
    # Specialized services (use these for specific operations)
    "EventPublisherService",
    "WebhookDeliveryService", 
    "WebhookEndpointService",
    "WebhookEventTypeService",
    "WebhookDeadLetterService",
    
    # Metrics and monitoring services
    "WebhookMetricsService",
    "WebhookMonitoringService",
    
    # Configuration service
    "WebhookConfigService",
    "WebhookConfig",
    "WebhookPerformanceConfig",
    "WebhookDatabaseConfig",
    "WebhookDeliveryConfig", 
    "WebhookValidationConfig",
    "WebhookMonitoringConfig",
    "get_webhook_config_service",
    "get_webhook_config",
    
    # Archival services
    "ArchivalCompressionService",
    "MultiRegionArchivalService",
    
    # Event sourcing optimization
    "EventSourcingOptimizationService",
]