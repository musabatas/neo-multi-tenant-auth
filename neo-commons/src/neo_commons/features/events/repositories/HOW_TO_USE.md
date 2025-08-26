# Events Repositories - HOW TO USE

This documentation covers the repository layer of the events feature in neo-commons, providing comprehensive guidance on data access patterns, database operations, and integration with the NeoMultiTenant platform.

## Overview

The events repositories implement the data access layer for the NeoMultiTenant platform's event system, following neo-commons Feature-First + Clean Core architecture principles. They provide database operations for domain events, webhooks, subscriptions, event actions, and archival functionality.

## Architecture

### Repository Design Patterns

The repositories follow consistent design patterns established across neo-commons:

- **Protocol-Based Dependency Injection**: All repositories implement `@runtime_checkable` protocols
- **Dynamic Schema Configuration**: Schema names are injected via constructor parameters
- **Database Repository Integration**: Uses existing `DatabaseRepository` from neo-commons
- **DRY Principle Compliance**: Centralized SQL queries and error handling utilities
- **Comprehensive Error Handling**: Consistent exception mapping and logging

### Core Components

```
repositories/
├── __init__.py                           # Public API exports
├── domain_event_repository.py           # Domain event persistence  
├── webhook_endpoint_repository.py       # Webhook endpoint management
├── webhook_delivery_repository.py       # Delivery tracking and attempts
├── webhook_subscription_repository.py   # Event subscriptions
├── webhook_event_type_repository.py     # Event type definitions
├── event_action_repository.py          # Event-triggered actions
├── action_execution_repository.py      # Action execution tracking
└── event_archival_repository.py        # Long-term event storage
```

## Installation/Setup

### 1. Database Service Integration

All repositories require the existing `DatabaseRepository` from neo-commons:

```python
from neo_commons.features.database.entities.protocols import DatabaseRepository
from neo_commons.features.events.repositories import (
    DomainEventDatabaseRepository,
    WebhookEndpointDatabaseRepository
)

# Initialize with database service
def create_event_repository(db_service: DatabaseRepository, schema: str):
    return DomainEventDatabaseRepository(db_service, schema)
```

### 2. Schema Configuration

Repositories are schema-agnostic and configured at runtime:

```python
# Admin schema for platform-wide events
admin_repo = DomainEventDatabaseRepository(db_service, "admin")

# Tenant-specific schema for isolated events
tenant_repo = DomainEventDatabaseRepository(db_service, "tenant_acme")

# Regional schema for multi-region deployments
regional_repo = DomainEventDatabaseRepository(db_service, "shared_us")
```

### 3. Dependency Injection Setup

```python
from neo_commons.features.events.entities.protocols import EventRepository

class EventService:
    def __init__(self, event_repo: EventRepository):
        self._event_repo = event_repo
    
    async def publish_event(self, event: DomainEvent):
        return await self._event_repo.save(event)

# Service configuration with protocol-based injection
async def get_event_service():
    db_service = await get_database_service()
    event_repo = DomainEventDatabaseRepository(db_service, "admin") 
    return EventService(event_repo)
```

## Core Concepts

### 1. Domain Events Repository

Manages the core event sourcing functionality with advanced querying capabilities:

```python
from neo_commons.features.events.repositories import DomainEventDatabaseRepository

class DomainEventDatabaseRepository:
    def __init__(self, database_repository: DatabaseRepository, schema: str)
    
    # Core operations
    async def save(self, event: DomainEvent) -> DomainEvent
    async def get_by_id(self, event_id: EventId) -> Optional[DomainEvent]
    
    # Event sourcing queries
    async def get_by_aggregate(self, aggregate_type: str, aggregate_id: UUID) -> List[DomainEvent]
    async def get_by_correlation_id(self, correlation_id: UUID) -> List[DomainEvent]
    
    # Webhook processing
    async def get_unprocessed(self, limit: int = 100) -> List[DomainEvent]
    async def mark_as_processed(self, event_id: EventId) -> bool
    async def mark_multiple_as_processed(self, event_ids: List[EventId]) -> int
    
    # Performance optimizations
    async def get_unprocessed_for_update(
        self, 
        limit: int = 100,
        skip_locked: bool = False,
        select_columns: Optional[List[str]] = None
    ) -> List[DomainEvent]
```

### 2. Webhook Endpoints Repository

Manages webhook endpoint configurations with verification and metrics:

```python
from neo_commons.features.events.repositories import WebhookEndpointDatabaseRepository

class WebhookEndpointDatabaseRepository:
    def __init__(self, database_repository: DatabaseRepository, schema: str)
    
    # CRUD operations
    async def save(self, endpoint: WebhookEndpoint) -> WebhookEndpoint
    async def get_by_id(self, endpoint_id: WebhookEndpointId) -> Optional[WebhookEndpoint]
    async def update(self, endpoint: WebhookEndpoint) -> WebhookEndpoint
    async def delete(self, endpoint_id: WebhookEndpointId) -> bool
    
    # Context-based queries
    async def get_by_context(self, context_id: UUID, active_only: bool = True) -> List[WebhookEndpoint]
    async def get_active_endpoints(self) -> List[WebhookEndpoint]
    
    # Endpoint maintenance
    async def update_last_used(self, endpoint_id: WebhookEndpointId) -> bool
    async def exists(self, endpoint_id: WebhookEndpointId) -> bool
```

### 3. Webhook Deliveries Repository

Tracks delivery attempts with comprehensive retry and monitoring capabilities:

```python
from neo_commons.features.events.repositories import WebhookDeliveryDatabaseRepository

class WebhookDeliveryDatabaseRepository:
    def __init__(self, database_repository: DatabaseRepository, schema: str)
    
    # Delivery tracking
    async def save(self, delivery: WebhookDelivery) -> WebhookDelivery
    async def get_by_id(self, delivery_id: WebhookDeliveryId) -> Optional[WebhookDelivery]
    
    # Retry management  
    async def get_pending_retries(self, limit: int = 100) -> List[WebhookDelivery]
    
    # Monitoring and analytics
    async def get_by_endpoint(self, endpoint_id: WebhookEndpointId, limit: int = 100) -> List[WebhookDelivery]
    async def get_by_event(self, event_id: EventId) -> List[WebhookDelivery]
    async def get_delivery_stats(self, endpoint_id: WebhookEndpointId, days: int = 7) -> Dict[str, Any]
```

### 4. Event Actions Repository

Manages event-triggered actions with conditional execution:

```python
from neo_commons.features.events.repositories.event_action_repository import EventActionPostgresRepository

class EventActionPostgresRepository:
    def __init__(self, connection_manager: ConnectionManager, schema: str = "admin")
    
    # Action management
    async def save(self, action: EventAction) -> EventAction
    async def get_by_id(self, action_id: ActionId) -> Optional[EventAction]
    async def update(self, action: EventAction) -> EventAction
    
    # Event-driven queries
    async def get_actions_for_event(
        self, 
        event_type: str, 
        context_filters: Optional[Dict[str, Any]] = None
    ) -> List[EventAction]
    
    # Statistics tracking
    async def update_statistics(
        self, 
        action_id: ActionId,
        trigger_increment: int = 0,
        success_increment: int = 0, 
        failure_increment: int = 0
    ) -> bool
```

## Usage Examples

### Basic Domain Event Operations

```python
from neo_commons.features.events.entities.domain_event import DomainEvent
from neo_commons.core.value_objects import EventId, EventType, UserId

# Create and save domain event
async def publish_user_created_event(user_id: UUID, user_data: dict):
    event = DomainEvent(
        id=EventId.generate(),
        event_type=EventType("user.created"),
        event_name="User Created",
        aggregate_type="User",
        aggregate_id=user_id,
        aggregate_version=1,
        event_data=user_data,
        triggered_by_user_id=UserId.generate(),
        context_id=organization_id
    )
    
    saved_event = await event_repo.save(event)
    logger.info(f"Published event {saved_event.id.value}")
    return saved_event

# Query events by aggregate
async def get_user_history(user_id: UUID):
    events = await event_repo.get_by_aggregate("User", user_id)
    return [event for event in events]
```

### Webhook Endpoint Management

```python
from neo_commons.features.events.entities.webhook_endpoint import WebhookEndpoint
from neo_commons.core.value_objects import WebhookEndpointId, UserId

# Create webhook endpoint
async def create_webhook_endpoint(config: dict):
    endpoint = WebhookEndpoint(
        id=WebhookEndpointId.generate(),
        name=config["name"],
        description=config.get("description", ""),
        endpoint_url=config["url"],
        http_method=config.get("method", "POST"),
        secret_token=config.get("secret"),
        is_active=True,
        created_by_user_id=UserId(config["user_id"]),
        context_id=config.get("context_id")
    )
    
    return await webhook_repo.save(endpoint)

# Get endpoints by context
async def get_organization_webhooks(org_id: UUID):
    endpoints = await webhook_repo.get_by_context(org_id, active_only=True)
    return endpoints
```

### Webhook Subscription Management

```python
from neo_commons.features.events.entities.webhook_subscription import WebhookSubscription

# Create subscription with filters
async def subscribe_to_events(endpoint_id: WebhookEndpointId, event_type: str, filters: dict):
    subscription = WebhookSubscription(
        id=WebhookSubscriptionId.generate(),
        endpoint_id=endpoint_id,
        event_type_id=WebhookEventTypeId.generate(),
        event_type=event_type,
        event_filters=filters,
        is_active=True,
        context_id=organization_id,
        subscription_name=f"Subscription to {event_type}"
    )
    
    return await subscription_repo.save(subscription)

# Get matching subscriptions for event dispatch
async def get_event_subscribers(event_type: str, context_id: UUID):
    subscriptions = await subscription_repo.get_matching_subscriptions(
        event_type=event_type,
        context_id=context_id
    )
    return subscriptions
```

### High-Performance Event Processing

```python
# Batch processing with FOR UPDATE locking
async def process_events_batch(batch_size: int = 100):
    # Get events with row-level locking
    events = await event_repo.get_unprocessed_for_update(
        limit=batch_size,
        skip_locked=True,
        select_columns=["id", "event_type", "event_data", "occurred_at"]
    )
    
    # Process events
    processed_ids = []
    for event in events:
        try:
            await dispatch_event(event)
            processed_ids.append(event.id)
        except Exception as e:
            logger.error(f"Failed to process event {event.id}: {e}")
    
    # Bulk mark as processed
    if processed_ids:
        count = await event_repo.mark_multiple_as_processed_bulk(processed_ids)
        logger.info(f"Marked {count} events as processed")
    
    return len(processed_ids)

# Optimized subscription queries
async def get_subscribers_optimized(event_type: str, context_id: UUID):
    return await subscription_repo.get_matching_subscriptions_optimized(
        event_type=event_type,
        context_id=context_id,
        select_columns=["id", "endpoint_id", "event_filters"],
        use_index_only=True
    )
```

### Event Action Configuration

```python
from neo_commons.features.events.entities.event_action import EventAction, HandlerType, ExecutionMode

# Create automated action
async def create_notification_action():
    action = EventAction(
        id=ActionId.generate(),
        name="User Welcome Email",
        description="Send welcome email when user is created",
        handler_type=HandlerType.EMAIL,
        configuration={
            "template": "welcome_email",
            "from_email": "noreply@company.com"
        },
        event_types=["user.created"],
        conditions=[],  # No conditions - trigger for all user.created events
        execution_mode=ExecutionMode.ASYNC,
        priority=ActionPriority.NORMAL,
        timeout_seconds=30,
        is_enabled=True
    )
    
    return await action_repo.save(action)
```

## API Reference

### DomainEventDatabaseRepository

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `save` | `event: DomainEvent` | `DomainEvent` | Saves new domain event |
| `get_by_id` | `event_id: EventId` | `Optional[DomainEvent]` | Retrieves event by ID |
| `get_by_aggregate` | `aggregate_type: str, aggregate_id: UUID` | `List[DomainEvent]` | Gets all events for aggregate |
| `get_unprocessed` | `limit: int = 100` | `List[DomainEvent]` | Gets unprocessed events |
| `get_unprocessed_for_update` | `limit: int, skip_locked: bool, select_columns: List[str]` | `List[DomainEvent]` | Gets events with locking |
| `mark_as_processed` | `event_id: EventId` | `bool` | Marks single event processed |
| `mark_multiple_as_processed` | `event_ids: List[EventId]` | `int` | Marks multiple events processed |
| `get_by_correlation_id` | `correlation_id: UUID` | `List[DomainEvent]` | Gets related events |
| `count_unprocessed` | None | `int` | Counts pending events |

#### Performance Optimizations

- **Bulk Processing**: `mark_multiple_as_processed_bulk` for high-throughput scenarios
- **Row Locking**: `get_unprocessed_for_update` with `SKIP LOCKED` for concurrent processing
- **Column Selection**: Specify `select_columns` to reduce I/O overhead
- **Pagination**: Built-in pagination support for streaming processing

### WebhookEndpointDatabaseRepository

#### Key Features

- **Context Isolation**: Endpoints scoped by `context_id` for multi-tenant security
- **Verification Tracking**: Built-in endpoint verification status and timestamps
- **Usage Monitoring**: Automatic `last_used_at` timestamp updates
- **JSON Configuration**: Support for custom headers and complex configurations

### WebhookDeliveryDatabaseRepository  

#### Delivery Tracking

- **Attempt Aggregation**: Each delivery contains multiple attempts as separate rows
- **Retry Management**: Automatic retry scheduling with exponential backoff
- **Comprehensive Metrics**: Response time, status codes, error tracking
- **Statistics**: Built-in delivery success rate and performance analytics

### EventActionPostgresRepository

#### Action Management

- **Conditional Execution**: Support for complex event matching conditions
- **Handler Types**: Pluggable handler system (EMAIL, WEBHOOK, FUNCTION)
- **Statistics Tracking**: Built-in trigger/success/failure counters
- **Tenant Isolation**: Multi-tenant action scoping

## Configuration

### Schema Selection Strategy

```python
# Platform-wide events
ADMIN_SCHEMA = "admin"

# Tenant-specific events
TENANT_SCHEMA = f"tenant_{tenant_slug}"

# Regional events
REGIONAL_SCHEMA = f"shared_{region}"

# Choose schema based on event scope
def get_event_schema(context_type: str, context_id: str) -> str:
    if context_type == "platform":
        return ADMIN_SCHEMA
    elif context_type == "tenant":
        return f"tenant_{context_id}"
    elif context_type == "region":
        return f"shared_{context_id}"
    else:
        raise ValueError(f"Unknown context type: {context_type}")
```

### Connection Pool Configuration

```python
from neo_commons.features.database.services.database_service import DatabaseService

# Repository initialization with connection pooling
async def create_repositories(schema: str):
    # Get shared database service (pooled connections)
    db_service = await get_database_service()
    
    return {
        'events': DomainEventDatabaseRepository(db_service, schema),
        'webhooks': WebhookEndpointDatabaseRepository(db_service, schema),
        'deliveries': WebhookDeliveryDatabaseRepository(db_service, schema),
        'subscriptions': WebhookSubscriptionDatabaseRepository(db_service, schema),
        'actions': EventActionPostgresRepository(db_service.connection_manager, schema)
    }
```

## Best Practices

### 1. Schema Design Patterns

```python
# ✅ Good: Schema injection for flexibility
class EventService:
    def __init__(self, event_repo: EventRepository, schema: str):
        self._event_repo = event_repo
        self._schema = schema

# ❌ Bad: Hard-coded schema names
class EventService:
    def __init__(self, event_repo: EventRepository):
        self._event_repo = event_repo  # Assumes 'admin' schema
```

### 2. Error Handling Patterns

```python
# ✅ Good: Protocol-based error handling
try:
    event = await event_repo.save(domain_event)
except EntityAlreadyExistsError:
    logger.warning(f"Event {domain_event.id} already exists")
    return await event_repo.get_by_id(domain_event.id)
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise ServiceError("Failed to save event")

# ❌ Bad: Generic exception handling
try:
    event = await event_repo.save(domain_event)
except Exception as e:
    logger.error(f"Error: {e}")
    raise e
```

### 3. Batch Processing Optimization

```python
# ✅ Good: Batch processing with proper locking
async def process_events_efficiently():
    events = await event_repo.get_unprocessed_for_update(
        limit=100,
        skip_locked=True,
        select_columns=["id", "event_type", "aggregate_id", "event_data"]
    )
    
    # Process in chunks
    processed_ids = []
    for event in events:
        # ... process event
        processed_ids.append(event.id)
    
    # Bulk update
    await event_repo.mark_multiple_as_processed_bulk(processed_ids)

# ❌ Bad: Individual processing without locking
async def process_events_inefficiently():
    events = await event_repo.get_unprocessed(100)
    for event in events:
        # ... process event
        await event_repo.mark_as_processed(event.id)  # Individual updates
```

### 4. Repository Composition

```python
# ✅ Good: Repository aggregation for related operations
class WebhookService:
    def __init__(self, 
                 event_repo: EventRepository,
                 webhook_repo: WebhookEndpointRepository, 
                 delivery_repo: WebhookDeliveryRepository):
        self._event_repo = event_repo
        self._webhook_repo = webhook_repo
        self._delivery_repo = delivery_repo
    
    async def deliver_event(self, event_id: EventId):
        event = await self._event_repo.get_by_id(event_id)
        endpoints = await self._webhook_repo.get_active_endpoints()
        
        deliveries = []
        for endpoint in endpoints:
            delivery = await self.create_delivery(event, endpoint)
            deliveries.append(await self._delivery_repo.save(delivery))
        
        return deliveries
```

## Common Pitfalls

### 1. Schema Name Hard-coding

```python
# ❌ Avoid: Hard-coded schema names
query = "SELECT * FROM admin.webhook_events WHERE id = $1"

# ✅ Correct: Parameterized schema names
query = "SELECT * FROM {schema}.webhook_events WHERE id = $1".format(schema=self._schema)
```

### 2. Missing Transaction Boundaries

```python
# ❌ Avoid: Operations without transaction context
await event_repo.save(event)
await webhook_repo.update_last_used(endpoint_id)

# ✅ Correct: Use database service transaction context
async with db_service.get_connection(schema) as conn:
    async with conn.transaction():
        await event_repo.save(event)
        await webhook_repo.update_last_used(endpoint_id)
```

### 3. Inefficient Bulk Operations

```python
# ❌ Avoid: Individual database calls in loops
for event_id in event_ids:
    await event_repo.mark_as_processed(event_id)

# ✅ Correct: Bulk operations
await event_repo.mark_multiple_as_processed_bulk(event_ids)
```

### 4. JSON Serialization Issues

```python
# ❌ Avoid: Direct JSON manipulation
event_data = json.dumps(data)  # May have serialization issues

# ✅ Correct: Let repository handle JSON serialization
event.event_data = data  # Repository handles JSON conversion
```

## Testing

### Unit Testing with Protocol Mocks

```python
import pytest
from unittest.mock import AsyncMock
from neo_commons.features.events.entities.protocols import EventRepository

@pytest.fixture
def mock_event_repo():
    mock = AsyncMock(spec=EventRepository)
    return mock

async def test_event_service_publish(mock_event_repo):
    # Arrange
    event = create_test_event()
    mock_event_repo.save.return_value = event
    service = EventService(mock_event_repo)
    
    # Act
    result = await service.publish(event)
    
    # Assert
    assert result == event
    mock_event_repo.save.assert_called_once_with(event)
```

### Integration Testing with Database

```python
@pytest.mark.integration
async def test_event_repository_save(db_service):
    # Arrange
    repo = DomainEventDatabaseRepository(db_service, "test_schema")
    event = create_test_event()
    
    # Act
    saved_event = await repo.save(event)
    
    # Assert
    assert saved_event.id == event.id
    
    # Verify persistence
    retrieved_event = await repo.get_by_id(event.id)
    assert retrieved_event is not None
    assert retrieved_event.event_type == event.event_type
```

### Performance Testing

```python
@pytest.mark.performance
async def test_bulk_event_processing_performance():
    # Create 1000 test events
    events = [create_test_event() for _ in range(1000)]
    
    # Save events
    start_time = time.time()
    for event in events:
        await event_repo.save(event)
    save_time = time.time() - start_time
    
    # Bulk mark as processed
    event_ids = [event.id for event in events]
    start_time = time.time()
    count = await event_repo.mark_multiple_as_processed_bulk(event_ids)
    bulk_time = time.time() - start_time
    
    # Assertions
    assert count == 1000
    assert bulk_time < save_time / 10  # Bulk operations should be much faster
```

## Migration Guide

### From Basic Event Storage to Advanced Event Sourcing

```python
# Before: Simple event logging
class OldEventService:
    async def log_event(self, event_type: str, data: dict):
        await db.execute("INSERT INTO events (type, data) VALUES ($1, $2)", event_type, json.dumps(data))

# After: Full event sourcing with aggregates
class NewEventService:
    def __init__(self, event_repo: EventRepository):
        self._event_repo = event_repo
    
    async def publish_domain_event(self, aggregate_type: str, aggregate_id: UUID, event_data: dict):
        event = DomainEvent(
            id=EventId.generate(),
            event_type=EventType(event_type),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_data=event_data,
            aggregate_version=await self.get_next_version(aggregate_type, aggregate_id)
        )
        return await self._event_repo.save(event)
```

### Protocol Migration Pattern

```python
# Step 1: Define protocol interface
@runtime_checkable
class EventRepository(Protocol):
    async def save(self, event: DomainEvent) -> DomainEvent: ...

# Step 2: Implement concrete repository
class DomainEventDatabaseRepository:
    def __init__(self, database_repository: DatabaseRepository, schema: str):
        self._db = database_repository
        self._schema = schema

# Step 3: Update service to use protocol
class EventService:
    def __init__(self, event_repo: EventRepository):  # Protocol, not concrete class
        self._event_repo = event_repo
```

## Related Components

### Neo-Commons Integration

- **Database Service**: [`neo_commons.features.database`] - Connection management and pooling
- **Cache Service**: [`neo_commons.features.cache`] - Event caching and invalidation
- **Value Objects**: [`neo_commons.core.value_objects`] - EventId, UserId, TenantId types
- **Exceptions**: [`neo_commons.core.exceptions`] - Standardized error handling

### Event Feature Components

- **Entities**: [`neo_commons.features.events.entities`] - Domain objects and protocols
- **Services**: [`neo_commons.features.events.services`] - Business logic and orchestration
- **Adapters**: [`neo_commons.features.events.adapters`] - External system integrations

### NeoMultiTenant APIs

- **NeoAdminApi**: Platform administration using admin schema repositories
- **NeoTenantApi**: Tenant-specific operations using tenant schema repositories

## Performance Considerations

### Database Optimization

1. **Index Strategy**: Ensure proper indexes on `occurred_at`, `aggregate_id`, `event_type`, `context_id`
2. **Partitioning**: Consider table partitioning for high-volume event storage
3. **Archival**: Implement event archival for long-term storage and performance
4. **Connection Pooling**: Leverage neo-commons database service connection pooling

### Query Optimization

1. **Column Selection**: Use `select_columns` parameter for large tables
2. **Batch Operations**: Prefer bulk operations for multiple record updates
3. **Row Locking**: Use `skip_locked` for high-concurrency scenarios
4. **Pagination**: Implement proper pagination for large result sets

### Memory Management

1. **Streaming Processing**: Process events in batches rather than loading all at once
2. **JSON Optimization**: Be mindful of large JSON payloads in event_data
3. **Connection Management**: Properly close database connections and transactions

This documentation provides comprehensive guidance for using the events repositories effectively while following neo-commons architectural patterns and maintaining high performance in multi-tenant environments.