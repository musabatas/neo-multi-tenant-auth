# Platform Events Development Plan

## Overview

This document outlines the architectural transformation of the events system from a mixed feature/infrastructure approach to a pure platform infrastructure following enterprise patterns used by Amazon, Google, and Netflix.

## Current Problem

The existing `features/events/` directory serves dual purposes, creating architectural confusion:

1. **Infrastructure Concern**: Event dispatching, webhook delivery, action execution (used by ALL features)
2. **Feature Concern**: Event management APIs, webhook configuration (business functionality)

This mixed responsibility violates clean architecture principles and creates dependency confusion.

## Solution: Pure Platform Architecture

Transform events into **pure platform infrastructure** that provides event dispatching, action execution, and delivery services to all business features.

## Enterprise Patterns Reference

### Google's Architecture Pattern
```
google3/
├── base/events/           # Event infrastructure platform
├── services/
│   ├── gmail/            # Uses base/events
│   ├── search/           # Uses base/events
│   └── ads/              # Uses base/events
```

### Netflix's Microservices Pattern
```
platform/event-platform/  # Core event infrastructure
services/
├── recommendation/       # Uses event platform
├── user-service/        # Uses event platform
```

### Amazon's Architecture Pattern
```
shared-infrastructure/
├── event-bridge/        # Event routing platform
business-services/       # All use event-bridge
```

## Target Architecture

### Complete Platform Structure

```
neo-commons/src/neo_commons/platform/events/
├── __init__.py
├── DEVELOPMENT_PLAN.md                    # This document
├── module.py                              # Event platform module registration
│
├── core/                                  # Event platform engine
│   ├── __init__.py
│   ├── entities/                         # Platform domain entities
│   │   ├── __init__.py
│   │   ├── domain_event.py              # Base event entity
│   │   ├── event_action.py              # Action definition entity
│   │   ├── webhook_endpoint.py          # Webhook infrastructure entity
│   │   ├── action_execution.py          # Execution tracking entity
│   │   └── webhook_delivery.py          # Delivery tracking entity
│   ├── value_objects/                   # Platform value objects
│   │   ├── __init__.py
│   │   ├── event_type.py                # Event type enumeration
│   │   ├── handler_type.py              # Handler type enumeration (webhook, email, sms, etc.)
│   │   ├── execution_mode.py            # Execution mode (sync, async, queued)
│   │   ├── action_priority.py           # Priority levels (low, normal, high, critical)
│   │   ├── action_status.py             # Action status (active, inactive, paused)
│   │   └── action_condition.py          # Condition evaluation logic
│   ├── events/                          # Platform domain events
│   │   ├── __init__.py
│   │   ├── event_dispatched.py          # Event was dispatched
│   │   ├── action_executed.py           # Action was executed
│   │   ├── webhook_delivered.py         # Webhook was delivered
│   │   ├── action_failed.py             # Action execution failed
│   │   └── delivery_failed.py           # Delivery failed
│   ├── exceptions/                      # Platform exceptions
│   │   ├── __init__.py
│   │   ├── event_dispatch_failed.py     # Event dispatch errors
│   │   ├── action_execution_failed.py   # Action execution errors
│   │   ├── webhook_delivery_failed.py   # Webhook delivery errors
│   │   └── invalid_event_configuration.py # Configuration errors
│   └── protocols/                       # Platform contracts
│       ├── __init__.py
│       ├── event_dispatcher.py          # Core dispatcher contract
│       ├── action_executor.py           # Action execution contract
│       ├── delivery_service.py          # Delivery contract
│       ├── event_repository.py          # Event storage contract
│       └── action_repository.py         # Action storage contract
│
├── application/                         # Event platform use cases
│   ├── __init__.py
│   ├── commands/                        # Platform write operations
│   │   ├── __init__.py
│   │   ├── dispatch_event.py            # ONLY event dispatch logic
│   │   ├── create_action.py             # ONLY action creation logic
│   │   ├── execute_action.py            # ONLY action execution logic
│   │   ├── deliver_webhook.py           # ONLY webhook delivery logic
│   │   ├── register_webhook.py          # ONLY webhook registration logic
│   │   ├── configure_handler.py         # ONLY handler configuration logic
│   │   └── archive_event.py             # ONLY event archival logic
│   ├── queries/                         # Platform read operations
│   │   ├── __init__.py
│   │   ├── get_event.py                 # ONLY event retrieval
│   │   ├── get_event_history.py         # ONLY event history
│   │   ├── get_action_status.py         # ONLY action status
│   │   ├── get_delivery_stats.py        # ONLY delivery statistics
│   │   ├── get_webhook_logs.py          # ONLY webhook logs
│   │   └── search_events.py             # ONLY event search
│   ├── validators/                      # Platform validation
│   │   ├── __init__.py
│   │   ├── event_validator.py           # ONLY event validation
│   │   ├── action_validator.py          # ONLY action validation
│   │   ├── webhook_validator.py         # ONLY webhook validation
│   │   ├── payload_validator.py         # ONLY payload validation
│   │   └── condition_validator.py       # ONLY condition validation
│   ├── handlers/                        # Platform event handlers
│   │   ├── __init__.py
│   │   ├── event_dispatched_handler.py  # ONLY dispatch handling
│   │   └── webhook_delivered_handler.py # ONLY delivery handling
│   └── services/                        # Platform orchestration services
│       ├── __init__.py
│       ├── event_dispatcher_service.py  # Main event dispatcher
│       └── webhook_delivery_service.py  # Webhook deliverer
│
├── infrastructure/                      # Platform implementations
│   ├── __init__.py
│   ├── repositories/                    # Data access implementations
│   │   ├── __init__.py
│   │   ├── asyncpg_event_repository.py          # PostgreSQL event storage
│   │   ├── asyncpg_action_repository.py         # PostgreSQL action storage
│   │   ├── redis_event_cache.py                # Redis event caching
│   │   ├── elasticsearch_event_search.py        # Search implementation
│   │   └── event_store_repository.py           # Event sourcing store
│   ├── adapters/                        # External service adapters
│   │   ├── __init__.py
│   │   ├── http_webhook_adapter.py              # HTTP webhook delivery
│   │   ├── email_notification_adapter.py       # Email notifications
│   │   ├── slack_webhook_adapter.py             # Slack integration
│   │   ├── teams_webhook_adapter.py             # Microsoft Teams integration
│   │   ├── sms_notification_adapter.py         # SMS notifications
│   │   ├── function_execution_adapter.py       # Function execution
│   │   └── workflow_execution_adapter.py       # Workflow execution
│   ├── handlers/                        # Action handler implementations
│   │   ├── __init__.py
│   │   ├── webhook_handler.py                   # Webhook action handler
│   │   ├── email_handler.py                    # Email action handler
│   │   ├── sms_handler.py                      # SMS action handler
│   │   ├── slack_handler.py                    # Slack action handler
│   │   ├── function_handler.py                 # Function action handler
│   │   └── workflow_handler.py                 # Workflow action handler
│   ├── queues/                          # Message queue implementations
│   │   ├── __init__.py
│   │   ├── redis_queue.py                      # Redis queue implementation
│   │   ├── memory_queue.py                     # In-memory queue
│   │   └── priority_queue.py                   # Priority queue
│   ├── queries/                         # Raw SQL queries
│   │   ├── __init__.py
│   │   ├── event_select_queries.py             # Event SELECT queries
│   │   ├── event_insert_queries.py             # Event INSERT queries
│   │   ├── action_analytics_queries.py         # Action analytics
│   │   └── delivery_performance_queries.py     # Delivery performance
│   └── factories/                       # Object factories
│       ├── __init__.py
│       ├── event_factory.py                    # Event creation factory
│       ├── action_factory.py                   # Action creation factory
│       └── handler_factory.py                  # Handler creation factory
│
├── api/                                 # Platform management APIs
│   ├── __init__.py
│   ├── models/                          # API models
│   │   ├── __init__.py
│   │   ├── requests/                    # Request models
│   │   │   ├── __init__.py
│   │   │   ├── dispatch_event_request.py       # Event dispatch request
│   │   │   ├── register_webhook_request.py     # Webhook registration request
│   │   │   └── search_events_request.py        # Event search request
│   │   │   # Note: Action-related requests moved to platform/actions module
│   │   └── responses/                   # Response models
│   │       ├── __init__.py
│   │       ├── event_response.py               # Event response
│   │       # Note: Action-related responses moved to platform/actions module
│   │       ├── webhook_response.py             # Webhook response
│   │       ├── delivery_status_response.py     # Delivery status
│   │       └── platform_stats_response.py      # Platform statistics
│   ├── routers/                         # Platform API endpoints
│   │   ├── __init__.py
│   │   ├── admin_events_router.py              # Platform administration (actions, webhooks)
│   │   ├── internal_events_router.py           # Service-to-service dispatch
│   │   ├── monitoring_router.py                # Platform health & metrics
│   │   └── webhook_management_router.py        # Webhook configuration
│   ├── dependencies/                    # API dependencies
│   │   ├── __init__.py
│   │   ├── platform_dependencies.py           # Platform service dependencies
│   │   ├── auth_dependencies.py               # Platform authentication
│   │   └── validation_dependencies.py         # Validation dependencies
│   └── middleware/                      # API middleware
│       ├── __init__.py
│       ├── platform_auth_middleware.py        # Platform authentication
│       ├── rate_limiting_middleware.py        # Rate limiting
│       └── monitoring_middleware.py           # Request monitoring
│
├── monitoring/                          # Platform monitoring & observability
│   ├── __init__.py
│   ├── metrics_collector.py                   # Metrics collection
│   ├── performance_monitor.py                 # Performance monitoring
│   ├── health_checker.py                      # Platform health checks
│   ├── alerting_service.py                    # Alert management
│   └── dashboard_service.py                   # Monitoring dashboard
│
└── extensions/                          # Platform extension points
    ├── __init__.py
    ├── hooks/                           # Platform hooks
    │   ├── __init__.py
    │   ├── pre_dispatch_hooks.py               # Before event dispatch
    │   ├── post_dispatch_hooks.py              # After event dispatch
    │   ├── pre_execution_hooks.py              # Before action execution
    │   └── post_execution_hooks.py             # After action execution
    └── validators/                      # Custom validators
        ├── __init__.py
        ├── custom_event_validators.py          # Custom event validation
        ├── custom_action_validators.py         # Custom action validation
        └── tenant_specific_validators.py       # Tenant-specific validation
```

## Usage Pattern: Features Use Platform

### How Business Features Use Event Platform

#### 1. Feature Defines Domain Events
```python
# features/organizations/domain/events/organization_created.py
from neo_commons.platform.events.core.entities import DomainEvent

class OrganizationCreatedEvent(DomainEvent):
    def __init__(self, org_id: str, org_name: str, tenant_id: str):
        super().__init__(
            event_type="organization.created",
            source="organizations-service",
            payload={
                "organization_id": org_id,
                "name": org_name,
                "tenant_id": tenant_id
            }
        )
```

#### 2. Feature Uses Platform to Dispatch
```python
# features/organizations/application/commands/create_organization.py
from neo_commons.platform.events.core.protocols import EventDispatcher

class CreateOrganizationCommand:
    def __init__(self, 
                 repository: OrganizationRepository,
                 event_dispatcher: EventDispatcher):  # Platform service
        self._repository = repository
        self._events = event_dispatcher

    async def execute(self, data: CreateOrganizationData) -> Organization:
        org = Organization.create(data)
        await self._repository.save(org)
        
        # Use platform to dispatch event
        await self._events.dispatch(
            OrganizationCreatedEvent(
                org_id=str(org.id),
                org_name=org.name,
                tenant_id=str(org.tenant_id)
            )
        )
        
        return org
```

#### 3. Services Configure Event Actions
```python
# NeoAdminApi startup configuration
from neo_commons.platform.events.application.commands import CreateActionCommand

async def setup_organization_webhooks():
    create_action = await container.get(CreateActionCommand)
    
    # Configure platform to send webhook when org is created
    await create_action.execute({
        "event_type": "organization.created",
        "handler_type": "webhook",
        "priority": "normal",
        "execution_mode": "async",
        "config": {
            "url": "https://external-service.com/organization-webhook",
            "method": "POST",
            "headers": {"Authorization": "Bearer token"},
            "timeout": 30
        },
        "conditions": {
            "tenant_id": {"operator": "equals", "value": "enterprise-tenant"}
        }
    })
```

## API Exposure Strategy

### Platform Management APIs (Limited)
```python
# Only platform administration APIs exposed
GET  /api/platform/events/health          # Platform health
GET  /api/platform/events/metrics         # Platform metrics  
POST /api/platform/events/actions         # Configure actions
GET  /api/platform/events/actions         # List actions
PUT  /api/platform/events/actions/{id}    # Update action
POST /api/platform/events/webhooks        # Configure webhooks
GET  /api/platform/events/delivery-logs   # Delivery logs
```

### Business Feature APIs (Normal Business Operations)
```python
# Features expose business operations, events happen automatically
POST /api/v1/organizations                 # Creates org → dispatches OrganizationCreatedEvent
PUT  /api/v1/organizations/{id}            # Updates org → dispatches OrganizationUpdatedEvent
POST /api/v1/users                         # Creates user → dispatches UserRegisteredEvent
POST /api/v1/billing/payments              # Processes payment → dispatches PaymentProcessedEvent
```

## Benefits of Pure Platform Architecture

### 1. Perfect Conceptual Clarity
- **Platform/Events**: Infrastructure used by everyone
- **Features**: Business logic that uses infrastructure
- **No Confusion**: Events is not a "feature" - it's infrastructure

### 2. Clean Dependency Direction
```python
# Clean dependencies (✅)
features/organizations → platform/events
features/users → platform/events
features/billing → platform/events

# No circular dependencies (✅)
platform/events ↛ features/anything
```

### 3. Platform Evolution Independence
```python
# Platform can evolve delivery mechanisms
platform/events/infrastructure/adapters/microsoft_teams_adapter.py

# Features don't change at all
features/organizations/  # Unchanged ✅
features/users/          # Unchanged ✅
features/billing/        # Unchanged ✅
```

### 4. Perfect Reusability
```python
# ALL services use the same event platform
NeoAdminApi → platform/events      # Administrative operations
NeoTenantApi → platform/events     # Tenant events
NeoInternalApi → platform/events   # Service-to-service
NeoPublicApi → platform/events     # Public webhooks
```

### 5. Single Source of Truth
```python
# Event infrastructure lives in ONE place
platform/events/

# Every feature just imports and uses it
from neo_commons.platform.events.core.protocols import EventDispatcher
from neo_commons.platform.events.core.entities import DomainEvent
```

## Migration Strategy

### Phase 1: Create Platform Structure (Foundation)
1. Create `platform/events/` directory structure
2. Implement `module.py` with platform registration
3. Move core entities to `platform/events/core/entities/`
4. Move value objects to `platform/events/core/value_objects/`
5. Define platform protocols in `platform/events/core/protocols/`

### Phase 2: Implement Platform Services (Engine)
1. Implement command/query separation in `application/`
2. Move services to `application/services/` with single responsibility
3. Create platform validators in `application/validators/`
4. Implement platform event handlers in `application/handlers/`

### Phase 3: Infrastructure Layer (Adapters)
1. Move repositories to `infrastructure/repositories/`
2. Separate adapters in `infrastructure/adapters/`
3. Create action handlers in `infrastructure/handlers/`
4. Implement message queues in `infrastructure/queues/`

### Phase 4: API Layer (Management)
1. Create platform management APIs in `api/routers/`
2. Implement platform-specific models in `api/models/`
3. Add platform dependencies in `api/dependencies/`
4. Create platform middleware in `api/middleware/`

### Phase 5: Integration & Testing
1. Update existing features to use platform services
2. Implement comprehensive platform testing
3. Add monitoring and observability
4. Create extension points for customization

### Phase 6: Cleanup Legacy
1. Remove old `features/events/` directory
2. Update documentation and guides
3. Verify all services use platform correctly
4. Performance validation and optimization

## Testing Strategy

### Platform Testing (Infrastructure)
```python
# Test platform components in isolation
def test_event_dispatcher():
    dispatcher = EventDispatcherService()
    # Test ONLY dispatching logic

def test_webhook_delivery():
    delivery = WebhookDeliveryService()
    # Test ONLY delivery logic

def test_action_execution():
    executor = ActionExecutionService()
    # Test ONLY execution logic
```

### Feature Integration Testing
```python
# Test features use platform correctly
def test_organization_creates_event():
    # Create organization
    org = await create_organization_command.execute(data)
    
    # Verify platform received event
    events = await event_repository.get_by_type("organization.created")
    assert len(events) == 1
    assert events[0].payload["organization_id"] == str(org.id)
```

### End-to-End Testing
```python
# Test complete event flow
def test_webhook_delivery_end_to_end():
    # Configure webhook action
    await create_action_command.execute(webhook_config)
    
    # Trigger business operation
    org = await create_organization_command.execute(org_data)
    
    # Verify webhook was delivered
    deliveries = await delivery_repository.get_by_event_type("organization.created")
    assert len(deliveries) == 1
    assert deliveries[0].status == "delivered"
```

## Performance Requirements

- **Event Dispatch**: < 1ms latency for event dispatch
- **Webhook Delivery**: < 5s for webhook delivery attempts
- **Action Execution**: < 100ms for synchronous actions
- **Platform Throughput**: 10,000+ events/second
- **Availability**: 99.9% uptime for platform services

## Monitoring & Observability

### Platform Metrics
- Events dispatched per second
- Action execution success rate
- Webhook delivery latency
- Failed delivery rate
- Platform resource usage

### Business Metrics
- Events by feature (organizations, users, billing)
- Action types usage (webhook, email, sms)
- Tenant-specific event volume
- Error rates by event type

## Security Considerations

### Platform Security
- Event payload encryption for sensitive data
- Webhook endpoint verification and authentication
- Rate limiting for event dispatch
- Audit logging for platform operations

### Feature Integration Security
- Features cannot access other tenant events
- Secure event payload validation
- Encrypted webhook delivery
- Authentication required for platform APIs

This development plan transforms the events system into enterprise-grade platform infrastructure following patterns used by Amazon, Google, and Netflix, providing a solid foundation for all business features to use event-driven architecture.