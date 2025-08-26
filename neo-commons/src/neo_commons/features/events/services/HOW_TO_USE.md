# Event Services - HOW TO USE

Comprehensive guide for using the neo-commons events services in the NeoMultiTenant platform. This directory contains the business logic services that orchestrate event publishing, webhook delivery, and dynamic action execution following the Feature-First + Clean Core architecture.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Concepts](#core-concepts)
- [Service Classes](#service-classes)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Best Practices](#best-practices)
- [Performance Optimization](#performance-optimization)
- [Testing](#testing)
- [Common Pitfalls](#common-pitfalls)
- [Migration Guide](#migration-guide)

## Overview

The events services layer provides enterprise-grade event processing capabilities with:

- **Event Publishing**: Domain event creation and publishing
- **Webhook Delivery**: HTTP webhook delivery with retry mechanisms
- **Event Orchestration**: Comprehensive event dispatching and routing
- **Dynamic Actions**: Runtime-configurable event actions
- **Configuration Management**: Environment-aware configuration with validation
- **Performance Optimization**: High-throughput processing with streaming support

### Key Features

- Sub-millisecond event publishing
- Configurable retry mechanisms with exponential backoff
- Circuit breaker protection for webhook endpoints
- Streaming event processing for memory efficiency
- Dynamic action registry with intelligent caching
- Protocol-based dependency injection
- Comprehensive validation with environment-specific rules

## Architecture

### Service Organization Pattern

```
services/
├── event_dispatcher_service.py         # Main orchestrator (Facade pattern)
├── event_publisher_service.py          # Event publishing (Single responsibility)
├── webhook_delivery_service.py         # Webhook delivery with retries
├── webhook_endpoint_service.py         # Endpoint management
├── webhook_event_type_service.py       # Event type management
├── webhook_config_service.py           # Configuration management
├── event_action_registry.py            # Dynamic action registry
├── action_execution_service.py         # Action execution
├── webhook_metrics_service.py          # Performance metrics
├── webhook_monitoring_service.py       # Health monitoring
└── archival_*.py                       # Event archival services
```

### Design Principles

1. **Single Responsibility**: Each service handles one business concern
2. **Protocol-Based**: All services implement @runtime_checkable protocols
3. **Dependency Injection**: Services accept protocol implementations
4. **Configuration-Driven**: Environment variables control behavior
5. **Performance-First**: Optimized for high-throughput scenarios

## Core Concepts

### Service Hierarchy

- **EventDispatcherService**: Main orchestrator that coordinates all event operations
- **Specialized Services**: Single-responsibility services for specific operations
- **Configuration Services**: Centralized configuration with environment awareness
- **Monitoring Services**: Metrics, health checks, and performance tracking

### Protocol-Based Architecture

```python
from neo_commons.features.events.entities.protocols import (
    EventRepository,
    WebhookEndpointRepository,
    WebhookDeliveryRepository,
    EventPublisher,
    EventDispatcher
)
```

## Service Classes

### EventDispatcherService (Main Orchestrator)

The primary service that coordinates all event operations using the Facade pattern.

**Key Methods:**

- `publish_event(event)` - Publish domain events
- `dispatch_unprocessed_events(limit)` - Process pending events for webhook delivery
- `dispatch_events_parallel()` - High-performance parallel event processing
- `dispatch_unprocessed_events_optimized()` - Ultra-optimized with database techniques
- `dispatch_events_streaming()` - Memory-efficient streaming processing
- `subscribe_endpoint()` / `unsubscribe_endpoint()` - Subscription management
- `create_webhook_endpoint()` - Endpoint creation
- `retry_failed_deliveries()` - Retry failed webhook deliveries

**Dependencies:**
```python
# All repository protocols
event_repository: EventRepository
endpoint_repository: WebhookEndpointRepository  
event_type_repository: WebhookEventTypeRepository
delivery_repository: WebhookDeliveryRepository
subscription_repository: WebhookSubscriptionRepository

# Optional for dynamic actions
action_repository: Optional[EventActionRepository]
execution_repository: Optional[ActionExecutionRepository]
config_service: Optional[WebhookConfigService]
```

### EventPublisherService (Event Publishing)

Specialized service for domain event creation and publishing.

**Key Methods:**
- `publish(event)` - Publish single event
- `publish_batch(events)` - Batch event publishing
- `create_and_publish()` - Create and publish in one operation
- `create_organization_event()` - Convenience method for organization events
- `create_user_event()` - Convenience method for user events

### WebhookDeliveryService (HTTP Delivery)

Handles webhook HTTP delivery with comprehensive retry logic.

**Key Methods:**
- `deliver_to_endpoint(event, endpoint)` - Deliver to specific endpoint
- `retry_failed_deliveries(limit)` - Process retry queue
- `verify_endpoint(endpoint)` - Endpoint verification
- `cancel_delivery(delivery_id)` - Cancel pending delivery

**Features:**
- Circuit breaker protection
- Exponential backoff retry
- Dead letter queue integration
- HMAC signature generation
- HTTP adapter abstraction

### WebhookConfigService (Configuration Management)

Centralized configuration with environment variable support.

**Configuration Sections:**
- `WebhookPerformanceConfig` - Batch sizes, concurrency, timeouts
- `WebhookDatabaseConfig` - Database optimizations, connection pooling
- `WebhookDeliveryConfig` - HTTP client, retry configuration
- `WebhookValidationConfig` - Validation thresholds and rules
- `WebhookMonitoringConfig` - Metrics, health checks, archival

### EventActionRegistryService (Dynamic Actions)

Manages runtime-configurable event actions with intelligent caching.

**Key Methods:**
- `register_action(action)` - Register new action
- `get_actions_for_event(event_type, event_data)` - Find matching actions
- `reload_actions()` - Refresh cache from database
- `get_cache_stats()` - Cache performance metrics

## Usage Examples

### Basic Event Publishing

```python
from neo_commons.features.events.services import EventDispatcherService, EventPublisherService

# Using EventPublisherService directly
publisher = EventPublisherService(event_repository)

# Simple event publishing
event = await publisher.create_and_publish(
    event_type="organization.created",
    aggregate_type="organization", 
    aggregate_id=org_id,
    event_data={
        "name": "ACME Corp",
        "domain": "acme.com",
        "plan": "enterprise"
    },
    triggered_by_user_id=UserId(user_id),
    context_id=org_id
)

# Batch publishing for performance
events = [event1, event2, event3]
published_count = await publisher.publish_batch(events)
print(f"Published {published_count} events successfully")
```

### Full Event Orchestration

```python
# Using EventDispatcherService (recommended)
dispatcher = EventDispatcherService(
    event_repository=event_repo,
    endpoint_repository=endpoint_repo,
    event_type_repository=event_type_repo,
    delivery_repository=delivery_repo,
    subscription_repository=subscription_repo,
    config_service=config_service  # Optional
)

# Create and publish with automatic webhook delivery
event = await dispatcher.create_and_publish_event(
    event_type="user.login",
    aggregate_type="user",
    aggregate_id=user_id,
    event_data={
        "ip_address": "192.168.1.1",
        "user_agent": "Mozilla/5.0...",
        "timestamp": datetime.now().isoformat()
    },
    context_id=organization_id
)

# Process unprocessed events for webhook delivery
processed_count = await dispatcher.dispatch_unprocessed_events(limit=100)
print(f"Processed {processed_count} events for webhook delivery")
```

### High-Performance Parallel Processing

```python
# Ultra-high-performance with database optimizations
performance_metrics = await dispatcher.dispatch_unprocessed_events_optimized(
    limit=500,
    batch_size=50,
    max_concurrent_batches=10,
    concurrent_workers=20
)

print(f"""
Performance Results:
- Processed: {performance_metrics['processed_events']} events
- Deliveries: {performance_metrics['total_deliveries']}  
- Time: {performance_metrics['processing_time_ms']}ms
- Throughput: {performance_metrics['events_per_second']} events/sec
- Optimization: {performance_metrics['optimization_level']}
""")

# Memory-efficient streaming for large volumes
streaming_results = await dispatcher.dispatch_events_streaming(
    event_stream_size_limit=10000,
    memory_threshold_mb=500
)

print(f"Streaming processed {streaming_results['events_processed']} events")
print(f"Memory efficiency: {streaming_results['memory_metrics']['memory_per_event_kb']:.2f} KB/event")
```

### Webhook Subscription Management

```python
# Subscribe endpoint to event types
success = await dispatcher.subscribe_endpoint(
    endpoint_id=WebhookEndpointId(endpoint_uuid),
    event_type="organization.updated", 
    event_filters={
        "changes": ["name", "billing_plan"],
        "organization_type": ["enterprise", "pro"]
    },
    subscription_name="Organization Changes Monitor"
)

# Get subscribed endpoints for event type
endpoints = await dispatcher.get_subscribed_endpoints(
    event_type="user.created",
    context_id=organization_id
)

print(f"Found {len(endpoints)} endpoints subscribed to user.created")
```

### Configuration and Environment Management

```python
from neo_commons.features.events.services import (
    get_webhook_config_service, 
    get_webhook_config
)

# Get configuration service
config_service = get_webhook_config_service()

# Get current configuration
config = get_webhook_config()

# Access specific configuration sections
perf_config = config.performance
print(f"Default batch size: {perf_config.default_batch_size}")
print(f"Max concurrent batches: {perf_config.max_concurrent_batches}")

# Runtime configuration updates
config_service.update_runtime_config(
    max_concurrent_batches=15,
    default_batch_size=25
)

# Get configuration summary for debugging
summary = config_service.get_config_summary()
print(f"Environment: {summary['environment']}")
print(f"Database optimizations: {summary['database']['use_optimizations']}")
```

### Dynamic Event Actions

```python
# Register dynamic action
from neo_commons.features.events.services import EventActionRegistryService

registry = EventActionRegistryService(
    repository=action_repository,
    cache_ttl_seconds=300,
    enable_cache=True
)

# Register action for event types
await registry.register_action(action_entity)

# Get actions for specific event
event_data = {
    "event_type": "organization.created",
    "aggregate_id": str(org_id),
    "event_data": {"plan": "enterprise"},
    "context_id": str(org_id)
}

matching_actions = await registry.get_actions_for_event(
    "organization.created", 
    event_data
)

print(f"Found {len(matching_actions)} actions for organization.created")

# Cache performance metrics
cache_stats = await registry.get_cache_stats()
print(f"Cache hit ratio: {cache_stats['valid_entries']}/{cache_stats['total_entries']}")
```

### Error Handling and Recovery

```python
try:
    # Attempt event processing
    result = await dispatcher.dispatch_unprocessed_events_optimized(limit=100)
    
except Exception as e:
    logger.error(f"Event processing failed: {e}")
    
    # Retry with fallback configuration
    fallback_result = await dispatcher.dispatch_unprocessed_events(
        limit=50,
        batch_size=10,
        max_concurrent_batches=3
    )
    
    print(f"Fallback processing completed: {fallback_result} events")

# Explicit retry of failed deliveries
retry_count = await dispatcher.retry_failed_deliveries(limit=50)
print(f"Retried {retry_count} failed webhook deliveries")

# Cancel specific delivery if needed
cancelled = await dispatcher.cancel_delivery(
    delivery_id=WebhookDeliveryId(delivery_uuid),
    reason="Endpoint maintenance window"
)
```

## Configuration

### Environment Variables

The services use comprehensive environment variable configuration:

#### Performance Configuration
```bash
# Event processing limits
WEBHOOK_DEFAULT_EVENT_LIMIT=100
WEBHOOK_MAX_EVENT_LIMIT=1000

# Batch processing
WEBHOOK_DEFAULT_BATCH_SIZE=10
WEBHOOK_OPTIMAL_BATCH_SIZE=20
WEBHOOK_MAX_BATCH_SIZE=100

# Concurrency controls  
WEBHOOK_MAX_CONCURRENT_BATCHES=5
WEBHOOK_MAX_CONCURRENT_EVENTS=20
WEBHOOK_CONCURRENT_WORKERS=10

# Timeouts
WEBHOOK_EVENT_PROCESSING_TIMEOUT=30.0
WEBHOOK_DELIVERY_TIMEOUT=15.0
```

#### Database Configuration
```bash
# Optimization settings
WEBHOOK_USE_FOR_UPDATE_SKIP_LOCKED=true
WEBHOOK_USE_SELECTIVE_COLUMNS=true
WEBHOOK_USE_BULK_OPERATIONS=true
WEBHOOK_BULK_OPERATION_BATCH_SIZE=50

# Connection settings
WEBHOOK_DB_MAX_CONNECTIONS=20
WEBHOOK_QUERY_TIMEOUT=5.0
```

#### Delivery Configuration
```bash
# HTTP client settings
WEBHOOK_CONNECTION_POOL_SIZE=100
WEBHOOK_KEEP_ALIVE_TIMEOUT=30

# Retry configuration
WEBHOOK_MAX_RETRY_ATTEMPTS=3
WEBHOOK_RETRY_BACKOFF_SECONDS=2.0
WEBHOOK_RETRY_BACKOFF_MULTIPLIER=2.0
WEBHOOK_MAX_RETRY_BACKOFF=60.0

# Delivery constraints
WEBHOOK_DEFAULT_TIMEOUT=30
WEBHOOK_MAX_PAYLOAD_SIZE_MB=10
```

#### Validation Configuration
```bash
# URL validation
WEBHOOK_MAX_URL_LENGTH=2048
WEBHOOK_ALLOWED_PROTOCOLS=http,https
WEBHOOK_BLOCK_LOOPBACK=true
WEBHOOK_BLOCK_PRIVATE_NETWORKS=false

# Validation thresholds
WEBHOOK_MAX_EVENT_DATA_SIZE_KB=100
WEBHOOK_MAX_CUSTOM_HEADERS=20
WEBHOOK_VALIDATION_PROFILE=production  # development, staging, production
```

### Configuration in Code

```python
# Create custom configuration
config = WebhookConfig(
    performance=WebhookPerformanceConfig(
        default_batch_size=25,
        max_concurrent_batches=8
    ),
    validation=WebhookValidationConfig(
        max_url_length=4096,
        strict_validation_mode=True
    )
)

# Use with services
config_service = WebhookConfigService()
config_service._config = config

dispatcher = EventDispatcherService(
    event_repository=event_repo,
    # ... other repositories
    config_service=config_service
)
```

## Best Practices

### Service Usage Patterns

1. **Use EventDispatcherService as the Main Interface**
   ```python
   # ✅ Recommended: Use the orchestrator
   dispatcher = EventDispatcherService(...)
   await dispatcher.create_and_publish_event(...)
   
   # ❌ Not recommended: Direct service usage unless specialized needs
   publisher = EventPublisherService(...)
   delivery = WebhookDeliveryService(...)
   ```

2. **Leverage Protocol-Based Dependency Injection**
   ```python
   # ✅ Inject protocol interfaces
   def create_event_service(
       event_repo: EventRepository,
       delivery_repo: WebhookDeliveryRepository
   ) -> EventDispatcherService:
       return EventDispatcherService(event_repo, delivery_repo, ...)
   
   # ✅ Mock protocols for testing
   class MockEventRepository:
       async def save(self, event): return event
   ```

3. **Use Batch Operations for Performance**
   ```python
   # ✅ Batch publishing for multiple events
   events = [create_event(...) for _ in range(100)]
   count = await publisher.publish_batch(events)
   
   # ✅ Optimized batch processing
   await dispatcher.dispatch_unprocessed_events_optimized(
       batch_size=50,
       max_concurrent_batches=10
   )
   ```

4. **Configure Environment-Specific Settings**
   ```python
   # ✅ Environment-aware configuration
   config = get_webhook_config()
   
   if config.environment == 'production':
       # Use strict validation and higher limits
       batch_size = config.performance.optimal_batch_size
   else:
       # Use relaxed settings for development
       batch_size = config.performance.default_batch_size
   ```

### Error Handling

1. **Implement Graceful Degradation**
   ```python
   try:
       # Try optimized processing first
       result = await dispatcher.dispatch_unprocessed_events_optimized()
   except Exception as e:
       logger.warning(f"Optimized processing failed: {e}, falling back")
       # Fall back to standard processing
       result = await dispatcher.dispatch_unprocessed_events()
   ```

2. **Use Circuit Breaker Pattern**
   ```python
   # Circuit breaker is built into WebhookDeliveryService
   # It automatically prevents calls to failing endpoints
   delivery = await delivery_service.deliver_to_endpoint(event, endpoint)
   # Will raise CircuitBreakerError if endpoint is unhealthy
   ```

3. **Handle Repository Failures**
   ```python
   try:
       await event_repository.save(event)
   except Exception as e:
       # Log error with context
       logger.error(f"Failed to save event {event.id}", extra={
           "event_type": event.event_type.value,
           "aggregate_id": str(event.aggregate_id),
           "error": str(e)
       })
       raise
   ```

### Performance Optimization

1. **Use Appropriate Processing Methods**
   ```python
   # Small batches (< 100 events)
   count = await dispatcher.dispatch_unprocessed_events(limit=50)
   
   # Medium batches (100-1000 events) - use optimized
   metrics = await dispatcher.dispatch_unprocessed_events_optimized(limit=500)
   
   # Large volumes (> 1000 events) - use streaming  
   results = await dispatcher.dispatch_events_streaming(
       event_stream_size_limit=10000
   )
   ```

2. **Monitor Memory Usage**
   ```python
   # Get streaming processing status
   status = await dispatcher.get_streaming_processing_status()
   
   if status['memory_statistics']['system_memory_percent'] > 80:
       # Reduce batch size or enable streaming mode
       batch_size = status['streaming_recommendations']['recommended_batch_size']
   ```

3. **Cache Configuration Access**
   ```python
   # ✅ Cache configuration service
   config_service = get_webhook_config_service()  # Singleton
   config = config_service.get_config()  # LRU cached
   
   # ❌ Don't create new config instances repeatedly
   # config = WebhookConfigService().get_config()  # Inefficient
   ```

## Performance Optimization

### Database Optimizations

The services implement several database optimization techniques:

1. **FOR UPDATE SKIP LOCKED**
   ```python
   # Automatically used in optimized processing
   events = await event_repository.get_unprocessed_for_update(
       limit=100,
       skip_locked=True,  # Prevents blocking on locked rows
       select_columns=["id", "event_type", "event_data"]  # Selective columns
   )
   ```

2. **Bulk Operations**
   ```python
   # Bulk mark as processed for better performance
   await event_repository.mark_multiple_as_processed_bulk(
       event_ids=successful_event_ids,
       batch_size=50  # Optimal batch size
   )
   ```

3. **Index-Only Scans**
   ```python
   # Repository methods use index-optimized queries
   subscriptions = await subscription_repository.get_matching_subscriptions_optimized(
       event_type="organization.created",
       select_columns=["id", "endpoint_id", "event_filters"],
       use_index_only=True
   )
   ```

### Concurrency Patterns

1. **Controlled Parallelism**
   ```python
   # Services use semaphores to control concurrency
   metrics = await dispatcher.dispatch_unprocessed_events_optimized(
       concurrent_workers=20,  # Delivery concurrency
       max_concurrent_batches=10  # Batch concurrency
   )
   ```

2. **Streaming for Memory Efficiency**
   ```python
   # Streaming processing with adaptive batch sizing
   results = await dispatcher.dispatch_events_streaming(
       memory_threshold_mb=500,  # Triggers adaptive sizing
       batch_size=100  # Starting batch size
   )
   ```

### Monitoring and Metrics

1. **Built-in Performance Metrics**
   ```python
   metrics = await dispatcher.dispatch_unprocessed_events_optimized()
   
   print(f"Throughput: {metrics['events_per_second']} events/sec")
   print(f"Efficiency: {metrics['deliveries_per_event']} deliveries/event")
   print(f"Database optimizations: {metrics['database_optimizations']}")
   ```

2. **Cache Performance**
   ```python
   # Monitor action registry cache performance
   cache_stats = await registry.get_cache_stats()
   hit_ratio = cache_stats['valid_entries'] / cache_stats['total_entries']
   
   if hit_ratio < 0.8:
       await registry.reload_actions()  # Refresh cache
   ```

## Testing

### Unit Testing with Protocol Mocks

```python
import pytest
from unittest.mock import AsyncMock
from neo_commons.features.events.services import EventDispatcherService

class MockEventRepository:
    def __init__(self):
        self.events = []
    
    async def save(self, event):
        self.events.append(event)
        return event
    
    async def get_unprocessed(self, limit=100):
        return self.events[:limit]
    
    async def mark_as_processed(self, event_id):
        return True

@pytest.fixture
async def event_dispatcher():
    """Create EventDispatcherService with mock dependencies."""
    mock_event_repo = MockEventRepository()
    mock_endpoint_repo = AsyncMock()
    mock_delivery_repo = AsyncMock()
    mock_subscription_repo = AsyncMock()
    mock_event_type_repo = AsyncMock()
    
    return EventDispatcherService(
        event_repository=mock_event_repo,
        endpoint_repository=mock_endpoint_repo,
        delivery_repository=mock_delivery_repo,
        subscription_repository=mock_subscription_repo,
        event_type_repository=mock_event_type_repo
    )

@pytest.mark.asyncio
async def test_event_publishing(event_dispatcher):
    """Test basic event publishing functionality."""
    event = await event_dispatcher.create_and_publish_event(
        event_type="test.created",
        aggregate_type="test",
        aggregate_id=uuid4(),
        event_data={"test": True}
    )
    
    assert event.event_type.value == "test.created"
    assert event.event_data["test"] is True
    
    # Verify event was saved
    assert len(event_dispatcher._event_repository.events) == 1

@pytest.mark.asyncio  
async def test_batch_processing(event_dispatcher):
    """Test batch event processing."""
    # Setup mock data
    event_dispatcher._subscription_repository.get_matching_subscriptions_optimized.return_value = []
    
    # Process unprocessed events
    processed_count = await event_dispatcher.dispatch_unprocessed_events(limit=10)
    
    # Should handle empty case gracefully
    assert processed_count >= 0
```

### Integration Testing

```python
@pytest.mark.integration
async def test_full_webhook_flow(real_database_repositories):
    """Integration test with real database repositories."""
    
    # Setup with real repositories
    dispatcher = EventDispatcherService(
        event_repository=real_database_repositories['event'],
        endpoint_repository=real_database_repositories['endpoint'],
        delivery_repository=real_database_repositories['delivery'],
        subscription_repository=real_database_repositories['subscription'],
        event_type_repository=real_database_repositories['event_type']
    )
    
    # Create webhook endpoint
    endpoint = await dispatcher.create_webhook_endpoint(
        name="Test Endpoint",
        endpoint_url="https://webhook.site/test",
        context_id=uuid4()
    )
    
    # Subscribe to event type
    success = await dispatcher.subscribe_endpoint(
        endpoint_id=endpoint.id,
        event_type="integration.test"
    )
    assert success is True
    
    # Publish event
    event = await dispatcher.create_and_publish_event(
        event_type="integration.test",
        aggregate_type="test",
        aggregate_id=uuid4(),
        event_data={"integration": True}
    )
    
    # Process for webhook delivery
    processed_count = await dispatcher.dispatch_unprocessed_events()
    assert processed_count >= 1
```

### Performance Testing

```python
@pytest.mark.performance
async def test_high_throughput_processing(event_dispatcher):
    """Performance test for high-throughput scenarios."""
    import time
    
    # Create multiple events
    events = []
    for i in range(1000):
        event_data = {"batch_id": i, "timestamp": time.time()}
        events.append(create_test_event(event_data))
    
    # Batch publish
    start_time = time.time()
    published_count = await event_dispatcher._publisher_service.publish_batch(events)
    publish_time = time.time() - start_time
    
    assert published_count == 1000
    assert publish_time < 5.0  # Should complete within 5 seconds
    
    # Test optimized processing
    start_time = time.time()
    metrics = await event_dispatcher.dispatch_unprocessed_events_optimized(
        limit=1000,
        batch_size=50,
        concurrent_workers=10
    )
    process_time = time.time() - start_time
    
    assert metrics['processed_events'] == 1000
    assert metrics['events_per_second'] > 100  # Performance threshold
    assert process_time < 10.0
```

## Common Pitfalls

### 1. Repository Protocol Compliance

❌ **Wrong**: Not implementing required protocol methods
```python
class IncompleteEventRepository:
    async def save(self, event):
        return event
    # Missing required methods like get_unprocessed, mark_as_processed
```

✅ **Correct**: Implement all protocol methods
```python
@runtime_checkable
class EventRepository(Protocol):
    # Must implement ALL methods from the protocol
    async def save(self, event): ...
    async def get_unprocessed(self, limit): ...
    async def mark_as_processed(self, event_id): ...
    # ... all other required methods
```

### 2. Configuration Management

❌ **Wrong**: Hardcoding configuration values
```python
# Don't hardcode values
batch_size = 50
max_retries = 3
```

✅ **Correct**: Use configuration service
```python
config = get_webhook_config()
batch_size = config.performance.default_batch_size
max_retries = config.delivery.max_retry_attempts
```

### 3. Error Handling in Batch Operations

❌ **Wrong**: Not handling individual failures in batch
```python
# This will fail entire batch if one event fails
for event in events:
    await publisher.publish(event)  # One failure stops all
```

✅ **Correct**: Use batch methods with error handling
```python
# This handles individual failures gracefully  
published_count = await publisher.publish_batch(events)
print(f"Published {published_count}/{len(events)} events")
```

### 4. Memory Management in Large Operations

❌ **Wrong**: Loading all events into memory
```python
# This can cause memory issues with large datasets
all_events = await repository.get_unprocessed(limit=100000)
for event in all_events:
    await process_event(event)
```

✅ **Correct**: Use streaming processing
```python
# This processes events in memory-efficient chunks
results = await dispatcher.dispatch_events_streaming(
    event_stream_size_limit=100000,
    memory_threshold_mb=500
)
```

### 5. Circuit Breaker Misuse

❌ **Wrong**: Bypassing circuit breaker protection
```python
# Direct HTTP calls bypass circuit breaker
async with httpx.AsyncClient() as client:
    response = await client.post(endpoint.url, json=payload)
```

✅ **Correct**: Use delivery service with circuit breaker
```python
# Circuit breaker protection is built-in
delivery = await delivery_service.deliver_to_endpoint(event, endpoint)
```

### 6. Synchronous Operations in Async Context

❌ **Wrong**: Blocking operations in async code
```python
async def process_events():
    events = await get_events()
    # This blocks the event loop
    processed = [sync_process(event) for event in events]
    return processed
```

✅ **Correct**: Use async operations
```python
async def process_events():
    events = await get_events()
    # This maintains async concurrency
    tasks = [async_process(event) for event in events]
    return await asyncio.gather(*tasks)
```

## Migration Guide

### From Direct Repository Usage

**Before** (anti-pattern):
```python
# Direct repository usage
event_repo = PostgreSQLEventRepository(connection)
endpoint_repo = PostgreSQLWebhookEndpointRepository(connection)

# Manual event processing
events = await event_repo.get_unprocessed()
for event in events:
    endpoints = await endpoint_repo.get_active_endpoints()
    for endpoint in endpoints:
        # Manual delivery logic
        await deliver_webhook(event, endpoint)
    await event_repo.mark_as_processed(event.id)
```

**After** (recommended):
```python
# Use EventDispatcherService
dispatcher = EventDispatcherService(
    event_repository=event_repo,
    endpoint_repository=endpoint_repo,
    # ... other dependencies
)

# Automated processing with optimizations
processed_count = await dispatcher.dispatch_unprocessed_events_optimized()
```

### From Synchronous to Asynchronous

**Before**:
```python
def publish_event(event_data):
    event = create_event(event_data)
    repository.save(event)
    return event
```

**After**:
```python
async def publish_event(event_data):
    event = await dispatcher.create_and_publish_event(
        event_type=event_data["type"],
        aggregate_type=event_data["aggregate_type"],
        aggregate_id=event_data["aggregate_id"],
        event_data=event_data["data"]
    )
    return event
```

### Configuration Migration

**Before** (hardcoded):
```python
class WebhookProcessor:
    def __init__(self):
        self.batch_size = 10
        self.max_retries = 3
        self.timeout = 30
```

**After** (configuration-driven):
```python
class WebhookProcessor:
    def __init__(self, config_service: WebhookConfigService):
        self.config = config_service.get_config()
        self.batch_size = self.config.performance.default_batch_size
        self.max_retries = self.config.delivery.max_retry_attempts
        self.timeout = self.config.delivery.default_timeout_seconds
```

### Protocol-Based Migration

**Before** (concrete dependencies):
```python
class EventService:
    def __init__(self, db_connection):
        self.event_repo = PostgreSQLEventRepository(db_connection)
```

**After** (protocol-based):
```python
class EventService:
    def __init__(self, event_repository: EventRepository):
        self.event_repo = event_repository  # Any implementation
```

---

## Related Components

- **[Entities](../entities/HOW_TO_USE.md)**: Domain entities and protocols
- **[Repositories](../repositories/)**: Data access layer implementations
- **[Utils](../utils/)**: Validation, error handling, and utility functions
- **[Adapters](../adapters/)**: External service integrations (HTTP, etc.)

## Support and Troubleshooting

For issues with the events services:

1. Check configuration using `get_webhook_config_service().get_config_summary()`
2. Monitor performance with built-in metrics from optimization methods
3. Use streaming processing status for memory-related issues
4. Review logs with structured context (event_id, endpoint_id, etc.)
5. Verify protocol implementations include all required methods

The events services are designed for enterprise-scale event processing with comprehensive monitoring, validation, and optimization capabilities. Follow the patterns and practices outlined in this guide for optimal performance and maintainability.