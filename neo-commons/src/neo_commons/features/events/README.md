# Dynamic Event Actions System

A comprehensive event-driven automation system for neo-commons that allows creating flexible, configurable actions triggered by domain events. This system enables building sophisticated workflows, notifications, and integrations without hardcoding business logic.

## Overview

The Dynamic Event Actions system provides:

- **Flexible Event Matching**: Support for exact matches, wildcards, and complex conditions
- **Multiple Handler Types**: Webhook, email, function, workflow, and custom handlers
- **Reliable Execution**: Retry logic, timeout management, and error handling
- **Comprehensive Monitoring**: Real-time metrics, health checks, and alerting
- **Multi-tenant Support**: Tenant isolation and context filtering
- **Priority-based Execution**: Control execution order with priority levels
- **Multiple Execution Modes**: Synchronous, asynchronous, and queued execution

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Domain Event  │───▶│  Event          │───▶│  Action         │
│                 │    │  Dispatcher     │    │  Registry       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Monitoring    │◀───│  Action         │───▶│  Handler        │
│   Service       │    │  Execution      │    │  Registry       │
└─────────────────┘    │  Service        │    └─────────────────┘
                       └─────────────────┘
```

### Core Components

1. **EventAction Entity**: Configurable action definitions with conditions and filters
2. **EventActionRegistry**: Manages action lifecycle and retrieval
3. **ActionExecutionService**: Handles reliable action execution with monitoring
4. **Handler Registry**: Manages different action handler implementations
5. **Monitoring Service**: Collects metrics and provides health checks

## Quick Start

### 1. Basic Webhook Action

```python
from neo_commons.core.value_objects import ActionId
from neo_commons.features.events.entities.event_action import (
    EventAction, HandlerType, ExecutionMode, ActionPriority
)

# Create a webhook action
webhook_action = EventAction(
    id=ActionId.generate(),
    name="User Registration Webhook",
    description="Send webhook when user registers",
    handler_type=HandlerType.WEBHOOK,
    configuration={
        "url": "https://api.example.com/webhooks/user-registered",
        "method": "POST",
        "headers": {"Authorization": "Bearer your-token"},
        "timeout": 30
    },
    event_types=["user.created"],
    execution_mode=ExecutionMode.ASYNC,
    priority=ActionPriority.NORMAL,
    is_enabled=True
)
```

### 2. Email Action with Conditions

```python
from neo_commons.features.events.entities.event_action import ActionCondition

# Create email action with conditions
email_action = EventAction(
    id=ActionId.generate(),
    name="Welcome Email",
    description="Send welcome email to verified users",
    handler_type=HandlerType.EMAIL,
    configuration={
        "to": "{{user.email}}",
        "template": "welcome_email",
        "from": "noreply@example.com",
        "subject": "Welcome to our platform!"
    },
    event_types=["user.created"],
    conditions=[
        ActionCondition("data.user.email_verified", "equals", True),
        ActionCondition("data.user.email", "contains", "@")
    ],
    execution_mode=ExecutionMode.ASYNC,
    priority=ActionPriority.HIGH
)
```

### 3. Complex Conditional Action

```python
# Action with complex conditions and context filtering
premium_notification = EventAction(
    id=ActionId.generate(),
    name="Premium User Activity",
    description="Track premium user activities",
    handler_type=HandlerType.WEBHOOK,
    configuration={
        "url": "https://analytics.example.com/premium-activity",
        "method": "POST"
    },
    event_types=["user.*", "subscription.*"],  # Multiple event types with wildcards
    conditions=[
        ActionCondition("data.user.subscription", "in", ["premium", "enterprise"]),
        ActionCondition("data.user.active", "equals", True),
        ActionCondition("data.activity.value", "gt", 100)
    ],
    context_filters={"tenant_id": "premium_tenant"},
    execution_mode=ExecutionMode.SYNC,
    priority=ActionPriority.HIGH,
    timeout_seconds=15,
    max_retries=3
)
```

## Usage Examples

### Registering Actions

```python
from neo_commons.features.events.services.event_action_registry import EventActionRegistry

# Initialize registry (normally done by dependency injection)
registry = EventActionRegistry(action_repository)

# Register an action
await registry.register_action(webhook_action)

# Get actions for an event type
matching_actions = await registry.get_actions_for_event("user.created", event_data)

# Get all actions
all_actions = await registry.get_all_actions()
```

### Event Dispatching with Actions

```python
from neo_commons.features.events.services.event_dispatcher_service import EventDispatcherService
from neo_commons.features.events.entities.domain_event import DomainEvent, EventType

# Initialize dispatcher (with action support)
dispatcher = EventDispatcherService()
dispatcher._action_registry = registry
dispatcher._execution_service = execution_service

# Create and dispatch event
event = DomainEvent(
    event_type=EventType("user.created"),
    aggregate_id="user_123",
    data={
        "user": {
            "id": "user_123",
            "email": "john@example.com",
            "email_verified": True,
            "subscription": "premium",
            "active": True
        }
    },
    metadata={"tenant_id": "premium_tenant"}
)

# Dispatch event - will trigger matching actions
await dispatcher.dispatch(event)
```

### Monitoring and Health Checks

```python
from neo_commons.features.events.services.action_monitoring_service import (
    ActionMonitoringService, ActionMonitoringConfig
)

# Configure monitoring
config = ActionMonitoringConfig(
    log_level="INFO",
    collect_metrics=True,
    alert_on_error_rate=True,
    error_rate_threshold_percent=10.0
)

# Initialize monitoring service
monitoring = ActionMonitoringService(execution_repository, config)
await monitoring.start_monitoring()

# Get action metrics
metrics = await monitoring.get_action_metrics("action_id")
print(f"Success rate: {metrics.success_rate_percent}%")

# Health check
health = await monitoring.check_action_health("action_id")
print(f"Status: {health['status']}, Message: {health['message']}")
```

## Action Configuration Guide

### Handler Types and Configuration

#### Webhook Handler
```python
configuration = {
    "url": "https://api.example.com/webhook",
    "method": "POST",  # GET, POST, PUT, DELETE
    "headers": {
        "Authorization": "Bearer token",
        "Content-Type": "application/json"
    },
    "timeout": 30,
    "verify_ssl": True
}
```

#### Email Handler
```python
configuration = {
    "to": "recipient@example.com",  # Or template: "{{user.email}}"
    "from": "noreply@example.com",
    "subject": "Email Subject",
    "template": "email_template_name",
    "cc": ["cc@example.com"],
    "bcc": ["bcc@example.com"]
}
```

#### Function Handler
```python
configuration = {
    "module": "my_app.handlers",
    "function": "process_user_event",
    "timeout": 60,
    "args": ["arg1", "arg2"],
    "kwargs": {"param": "value"}
}
```

#### Workflow Handler
```python
configuration = {
    "steps": [
        {"action": "validate", "params": {"required_fields": ["email"]}},
        {"action": "transform", "params": {"format": "json"}},
        {"action": "send", "params": {"destination": "queue"}}
    ],
    "timeout": 120,
    "parallel": False
}
```

### Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match | `"status", "equals", "active"` |
| `contains` | String contains | `"email", "contains", "@company.com"` |
| `gt` | Greater than | `"age", "gt", 18` |
| `lt` | Less than | `"score", "lt", 100` |
| `in` | Value in list | `"status", "in", ["active", "pending"]` |
| `not_in` | Value not in list | `"status", "not_in", ["banned", "deleted"]` |
| `exists` | Field exists | `"optional_field", "exists", True` |
| `not_exists` | Field doesn't exist | `"removed_field", "not_exists", True` |

### Event Type Patterns

```python
# Exact match
event_types = ["user.created"]

# Wildcard matching
event_types = ["user.*"]  # Matches user.created, user.updated, etc.

# Multiple patterns
event_types = ["user.*", "order.created", "payment.processed"]

# Universal wildcard
event_types = ["*"]  # Matches all events
```

## API Management

### REST API Endpoints

The system provides comprehensive REST APIs for managing actions:

```http
# List actions with filtering
GET /api/v1/event-actions?status=active&handler_type=webhook&search=user

# Create action
POST /api/v1/event-actions
Content-Type: application/json
{
  "name": "User Registration Webhook",
  "handler_type": "webhook",
  "configuration": {"url": "https://example.com/webhook"},
  "event_types": ["user.created"],
  "conditions": [
    {"field": "data.user.active", "operator": "equals", "value": true}
  ]
}

# Get specific action
GET /api/v1/event-actions/{action_id}

# Update action
PUT /api/v1/event-actions/{action_id}
Content-Type: application/json
{
  "name": "Updated Action Name",
  "is_enabled": false
}

# Delete action
DELETE /api/v1/event-actions/{action_id}

# Test action with simulated data
POST /api/v1/event-actions/{action_id}/test
Content-Type: application/json
{
  "event_type": "user.created",
  "event_data": {"user": {"id": "123", "active": true}},
  "dry_run": true
}

# Enable/disable actions
POST /api/v1/event-actions/{action_id}/enable
POST /api/v1/event-actions/{action_id}/disable

# Get execution history
GET /api/v1/event-actions/{action_id}/executions?status=failed&limit=20

# Get statistics
GET /api/v1/event-actions/stats/overview
GET /api/v1/event-actions/{action_id}/stats
```

## Advanced Features

### Multi-tenant Support

```python
# Tenant-specific action
tenant_action = EventAction(
    id=ActionId.generate(),
    name="Tenant-Specific Action",
    handler_type=HandlerType.WEBHOOK,
    configuration={"url": "https://tenant.example.com/webhook"},
    event_types=["user.created"],
    tenant_id="tenant_123",  # Restrict to specific tenant
    context_filters={"tenant_id": "tenant_123"}  # Additional filtering
)
```

### Priority-based Execution

```python
# High priority action (executes first)
critical_action = EventAction(
    id=ActionId.generate(),
    name="Critical Alert",
    handler_type=HandlerType.WEBHOOK,
    configuration={"url": "https://alerts.example.com/critical"},
    event_types=["system.error"],
    priority=ActionPriority.CRITICAL,  # CRITICAL > HIGH > NORMAL > LOW
    execution_mode=ExecutionMode.SYNC   # Block until complete
)
```

### Execution Modes

```python
# Synchronous - blocks until complete
sync_action = EventAction(
    execution_mode=ExecutionMode.SYNC,
    # ... other config
)

# Asynchronous - fire and forget
async_action = EventAction(
    execution_mode=ExecutionMode.ASYNC,
    # ... other config
)

# Queued - add to background queue
queued_action = EventAction(
    execution_mode=ExecutionMode.QUEUED,
    # ... other config
)
```

### Error Handling and Retries

```python
# Configure retry behavior
resilient_action = EventAction(
    id=ActionId.generate(),
    name="Resilient Action",
    handler_type=HandlerType.WEBHOOK,
    configuration={"url": "https://unreliable.example.com/webhook"},
    event_types=["important.event"],
    timeout_seconds=30,
    max_retries=5,
    retry_delay_seconds=10
)
```

## Monitoring and Observability

### Structured Logging

```python
from neo_commons.features.events.logging_config import (
    setup_event_action_logging, EventActionLogger
)

# Setup structured logging
setup_event_action_logging(
    log_level="INFO",
    enable_structured_logging=True,
    log_file_path="/var/log/event-actions.json",
    include_extra_fields=True
)

# Use logger utility
logger = EventActionLogger("my_service.events")
logger.log_action_created("My Action", "action_123", "webhook")
logger.log_execution_completed("My Action", "action_123", "exec_456", "success", 150)
```

### Metrics and Health Checks

```python
# Get comprehensive metrics
global_metrics = await monitoring.get_global_metrics()
print(f"Total executions: {global_metrics.total_executions}")
print(f"Success rate: {global_metrics.success_rate_percent}%")
print(f"Average duration: {global_metrics.avg_duration_ms}ms")

# Action-specific health
health = await monitoring.check_action_health("action_123")
if health["status"] == "critical":
    print(f"Action needs attention: {health['message']}")
```

### Alerting

The monitoring system automatically generates alerts for:

- **High Error Rates**: When success rate drops below threshold
- **Slow Executions**: When execution time exceeds threshold
- **Handler Failures**: When handlers become unavailable
- **Resource Exhaustion**: When system resources are under pressure

## Best Practices

### 1. Action Design

- **Single Responsibility**: Each action should have one clear purpose
- **Idempotent Operations**: Actions should be safe to retry
- **Timeout Configuration**: Set appropriate timeouts for external calls
- **Error Recovery**: Design handlers to gracefully handle failures

### 2. Event Matching

- **Specific Patterns**: Use specific event types when possible
- **Efficient Conditions**: Order conditions by selectivity (most selective first)
- **Context Filtering**: Use context filters for tenant isolation
- **Avoid Over-matching**: Don't use overly broad wildcards

### 3. Performance

- **Async by Default**: Use async execution mode unless ordering is critical
- **Batch Operations**: Group related actions when possible
- **Monitor Resources**: Set up alerting for high error rates
- **Cache Handler Results**: Implement caching in custom handlers

### 4. Security

- **Validate Inputs**: Always validate event data in handlers
- **Secure Credentials**: Use secure credential management for webhooks
- **Rate Limiting**: Implement rate limiting for external calls
- **Audit Logging**: Enable comprehensive audit logging

### 5. Testing

- **Unit Tests**: Test individual actions and conditions
- **Integration Tests**: Test complete event-to-action workflows
- **Load Testing**: Verify performance under expected load
- **Failure Testing**: Test error handling and retry logic

## Troubleshooting

### Common Issues

#### Actions Not Triggering
1. Check action is enabled: `action.is_enabled == True`
2. Verify event type matching: Use action testing API
3. Check conditions: Review condition evaluation in logs
4. Validate context filters: Ensure tenant_id and filters match

#### High Error Rates
1. Check handler availability: Verify webhook endpoints are reachable
2. Review timeout settings: Increase timeout for slow handlers
3. Check retry configuration: Adjust retry count and delay
4. Monitor resource usage: Ensure adequate system resources

#### Poor Performance
1. Review execution mode: Consider async for non-critical actions
2. Optimize handlers: Reduce handler execution time
3. Check concurrency: Adjust max concurrent executions
4. Monitor bottlenecks: Use execution metrics to identify issues

### Debug Commands

```python
# Test action against specific event
test_result = await admin_service.test_action("action_id", ActionTestRequest(
    event_type="user.created",
    event_data={"user": {"id": "123", "active": True}},
    dry_run=True
))
print(f"Would trigger: {test_result.matched}")
print(f"Reason: {test_result.reason}")

# Get execution history
executions, total = await admin_service.get_action_executions(
    "action_id", status="failed", limit=10
)
for execution in executions:
    print(f"Failed: {execution.error_message}")

# Check action health
health = await execution_service.check_action_health("action_id")
print(f"Health: {health}")
```

## Migration Guide

### From Hardcoded Event Handlers

If you currently have hardcoded event handlers, migrate them to dynamic actions:

1. **Identify Handler Logic**: Extract the handler logic into separate functions
2. **Create Actions**: Use the API or code to create corresponding actions
3. **Test Matching**: Use the test API to verify event matching works correctly
4. **Enable Monitoring**: Set up monitoring and alerting
5. **Gradual Migration**: Migrate one handler at a time

### Database Schema Updates

The system requires these database tables:
- `event_actions`: Main action definitions
- `action_executions`: Execution history and results

Run the provided Flyway migrations:
- `V1013__create_event_actions_infrastructure.sql` (admin schema)
- `V2005__create_tenant_event_actions_infrastructure.sql` (tenant schemas)

## Contributing

When adding new features to the event actions system:

1. **Follow Patterns**: Use existing patterns for new handler types
2. **Add Tests**: Include comprehensive unit and integration tests
3. **Update Documentation**: Update this README with new features
4. **Monitor Impact**: Add appropriate monitoring for new components

### Adding Custom Handler Types

```python
from neo_commons.features.events.entities.action_handlers import EventActionHandler

class CustomHandler(EventActionHandler):
    def __init__(self):
        super().__init__("custom", "Custom Handler for specialized operations")
    
    def can_handle(self, action: EventAction) -> bool:
        return action.handler_type == HandlerType.CUSTOM
    
    async def handle(self, action: EventAction, event_data: Dict[str, Any]) -> Dict[str, Any]:
        # Implement custom logic
        return {"success": True, "processed_at": datetime.now().isoformat()}

# Register the handler
registry.register_handler("custom", CustomHandler())
```

## License

This dynamic event actions system is part of neo-commons and follows the same licensing terms as the parent project.