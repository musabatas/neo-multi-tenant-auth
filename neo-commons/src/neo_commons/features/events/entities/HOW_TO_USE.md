# HOW_TO_USE.md - Events Entities

Comprehensive guide to using the Events Entities module in neo-commons for building enterprise-grade event-driven systems on the NeoMultiTenant platform.

## Overview

The Events Entities module provides a complete domain model for implementing webhook-based event systems with enterprise-grade features including delivery guarantees, retry mechanisms, event archival, and dynamic action handling. This module follows the Feature-First + Clean Core architecture pattern, providing immutable domain entities and protocol-based abstractions for maximum flexibility and maintainability.

**Key Features:**
- **Event Sourcing**: Complete domain event lifecycle management with validation
- **Webhook System**: Enterprise webhook delivery with retry logic and circuit breakers
- **Dynamic Actions**: Configurable event-driven actions with complex condition matching
- **Event Archival**: Long-term storage and compression for scalability
- **Multi-tenant Support**: Context-aware filtering and isolation
- **Protocol-based Design**: Dependency injection friendly with testable abstractions

## Architecture

The entities module implements a layered domain architecture:

```
entities/
├── domain_event.py         # Core event entity with validation
├── webhook_endpoint.py     # Webhook configuration and security
├── webhook_event_type.py   # Event type definitions and schemas
├── webhook_delivery.py     # Delivery tracking and retry logic
├── webhook_subscription.py # Event-to-endpoint subscriptions
├── event_action.py         # Dynamic action definitions
├── event_archive.py        # Long-term storage entities
└── protocols.py           # Repository and service contracts
```

### Core Design Patterns

1. **Immutable Entities**: All entities are dataclasses with validation in `__post_init__`
2. **Value Objects**: Uses neo-commons core value objects for type safety
3. **Protocol-based Contracts**: Defines clear boundaries between domain and infrastructure
4. **Centralized Validation**: Shared validation rules via utils/validation.py
5. **Event-driven Architecture**: Entities designed for event sourcing and CQRS patterns

## Core Concepts

### 1. Domain Events
**Purpose**: Represent business events that occur in the system and need to be published to external systems.

```python
from neo_commons.features.events.entities import DomainEvent
from neo_commons.core.value_objects import EventId, EventType, UserId
from uuid import uuid4

# Create a domain event
event = DomainEvent(
    id=EventId(uuid4()),
    event_type=EventType("organization.created"),
    event_name="New Organization Created",
    aggregate_id=uuid4(),  # Organization ID
    aggregate_type="organization",
    aggregate_version=1,
    event_data={
        "name": "Acme Corp",
        "plan": "enterprise",
        "region": "us-east"
    },
    event_metadata={
        "source": "admin-api",
        "ip_address": "192.168.1.100",
        "user_agent": "NeoAdmin/1.0"
    },
    triggered_by_user_id=UserId(uuid4()),
    context_id=uuid4(),  # Organization context
    correlation_id=uuid4()  # For tracking related events
)

# Event lifecycle management
event.mark_as_processed()
event.add_metadata("processing_duration_ms", 150)
print(f"Event category: {event.get_event_category()}")  # "organization"
print(f"Event action: {event.get_event_action()}")    # "created"
```

### 2. Webhook Endpoints
**Purpose**: Configure external HTTP endpoints that receive webhook notifications.

```python
from neo_commons.features.events.entities import WebhookEndpoint
from neo_commons.core.value_objects import WebhookEndpointId, UserId
from decimal import Decimal

# Create webhook endpoint with security
endpoint = WebhookEndpoint(
    id=WebhookEndpointId(uuid4()),
    name="Customer Portal Webhook",
    description="Receives organization and user events",
    endpoint_url="https://api.customer.com/webhooks/neofast",
    http_method="POST",
    secret_token="auto-generated-or-provided",
    signature_header="X-Neo-Signature",
    custom_headers={
        "Authorization": "Bearer token123",
        "X-Source": "NeoFast"
    },
    timeout_seconds=30,
    follow_redirects=False,
    verify_ssl=True,
    max_retry_attempts=3,
    retry_backoff_seconds=5,
    retry_backoff_multiplier=Decimal("2.0"),
    is_active=True,
    is_verified=False,
    created_by_user_id=UserId(uuid4()),
    context_id=uuid4()  # Organization context
)

# Security operations
payload = '{"event": "test"}'
signature = endpoint.generate_signature(payload)
is_valid = endpoint.verify_signature(payload, signature)

# Configuration management
endpoint.activate()
endpoint.verify()  # Mark as verified after validation
endpoint.update_url("https://api.customer.com/webhooks/v2/neofast")
old_secret = endpoint.rotate_secret()

# Retry calculation
retry_delay = endpoint.calculate_retry_delay(attempt_number=2)  # Returns exponential backoff
```

### 3. Event Types and Subscriptions
**Purpose**: Define available event types and manage endpoint subscriptions.

```python
from neo_commons.features.events.entities import WebhookEventType, WebhookSubscription
from neo_commons.core.value_objects import WebhookEventTypeId, WebhookSubscriptionId

# Define event type
event_type = WebhookEventType(
    id=WebhookEventTypeId(uuid4()),
    event_type="organization.created",
    category="organization",
    display_name="Organization Created",
    description="Triggered when a new organization is created",
    is_enabled=True,
    requires_verification=True,  # Only verified endpoints can subscribe
    payload_schema={
        "type": "object",
        "properties": {
            "id": {"type": "string", "format": "uuid"},
            "name": {"type": "string"},
            "plan": {"type": "string", "enum": ["basic", "pro", "enterprise"]}
        },
        "required": ["id", "name", "plan"]
    },
    example_payload={
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Acme Corp",
        "plan": "enterprise"
    }
)

# Create subscription with filtering
subscription = WebhookSubscription(
    id=WebhookSubscriptionId(uuid4()),
    endpoint_id=endpoint.id,
    event_type_id=event_type.id,
    event_type="organization.created",
    event_filters={
        "plan": ["enterprise", "pro"],  # Only enterprise/pro plans
        "region": {"$in": ["us-east", "us-west"]},  # Specific regions
        "data.user_count": {"$gte": 10}  # Organizations with 10+ users
    },
    is_active=True,
    context_id=uuid4(),  # Organization context
    subscription_name="Enterprise Org Notifications",
    description="Notifies when enterprise/pro organizations are created"
)

# Event matching
event_data = {
    "plan": "enterprise",
    "region": "us-east",
    "data": {"user_count": 15}
}
matches = subscription.matches_event("organization.created", event_data)
```

### 4. Webhook Delivery and Retry Logic
**Purpose**: Track delivery attempts with comprehensive retry mechanisms.

```python
from neo_commons.features.events.entities import (
    WebhookDelivery, 
    WebhookDeliveryAttempt, 
    DeliveryStatus
)
from neo_commons.core.value_objects import WebhookDeliveryId

# Create delivery record
delivery = WebhookDelivery(
    id=WebhookDeliveryId(uuid4()),
    webhook_endpoint_id=endpoint.id,
    webhook_event_id=event.id,
    current_attempt=1,
    overall_status=DeliveryStatus.PENDING,
    max_attempts=3,
    base_backoff_seconds=5,
    backoff_multiplier=2.0
)

# Record delivery attempt
attempt = WebhookDeliveryAttempt(
    attempt_number=1,
    delivery_status=DeliveryStatus.FAILED,
    request_url=endpoint.endpoint_url,
    request_method="POST",
    request_headers=endpoint.get_request_headers(),
    request_body='{"event_type": "organization.created"}',
    request_signature=signature,
    response_status_code=500,
    response_headers={"content-type": "application/json"},
    response_body='{"error": "Internal server error"}',
    response_time_ms=2500,
    error_message="HTTP 500 Internal Server Error",
    error_code="HTTP_500"
)

# Add attempt and handle retry logic
delivery.add_attempt(attempt)
print(f"Can retry: {delivery.can_retry()}")
print(f"Next retry delay: {delivery.get_next_retry_delay_seconds()}s")
print(f"Ready for retry: {delivery.is_ready_for_retry()}")
```

### 5. Dynamic Event Actions
**Purpose**: Configure automated actions that trigger based on events and conditions.

```python
from neo_commons.features.events.entities import (
    EventAction, 
    ActionCondition,
    HandlerType,
    ActionPriority,
    ExecutionMode,
    ActionStatus
)
from neo_commons.core.value_objects import ActionId

# Create dynamic action with conditions
action = EventAction(
    id=ActionId(uuid4()),
    name="Enterprise Welcome Email",
    description="Send welcome email to enterprise organizations",
    handler_type=HandlerType.EMAIL,
    configuration={
        "to": "welcome@company.com",
        "template": "enterprise_welcome",
        "subject": "Welcome to NeoFast Enterprise!"
    },
    event_types=["organization.created", "organization.upgraded"],
    conditions=[
        ActionCondition("data.plan", "in", ["enterprise"]),
        ActionCondition("data.user_count", "gte", 5),
        ActionCondition("metadata.source", "equals", "signup")
    ],
    context_filters={"region": ["us-east", "us-west"]},
    execution_mode=ExecutionMode.ASYNC,
    priority=ActionPriority.HIGH,
    timeout_seconds=60,
    max_retries=3,
    retry_delay_seconds=10,
    status=ActionStatus.ACTIVE,
    is_enabled=True,
    tags={"category": "onboarding", "priority": "high"},
    created_by_user_id=UserId(uuid4()),
    tenant_id="acme-corp"
)

# Event matching and execution
event_data = {
    "event_type": "organization.created",
    "data": {"plan": "enterprise", "user_count": 10},
    "metadata": {"source": "signup"},
    "region": "us-east"
}
should_trigger = action.matches_event("organization.created", event_data)

# Action lifecycle management
action.pause()
action.resume()
action.update_configuration({"template": "enterprise_welcome_v2"})
action.add_condition(ActionCondition("data.industry", "not_in", ["gambling", "crypto"]))
```

### 6. Event Archival
**Purpose**: Long-term storage and retention management for scalability.

```python
from neo_commons.features.events.entities import (
    EventArchive,
    ArchivalRule,
    ArchivalJob,
    ArchivalPolicy,
    StorageType,
    ArchivalStatus
)

# Define archival rule
archival_rule = ArchivalRule(
    id=uuid4(),
    name="Monthly Event Archival",
    description="Archive events older than 90 days",
    policy=ArchivalPolicy.AGE_BASED,
    storage_type=StorageType.COMPRESSED_ARCHIVE,
    is_enabled=True,
    archive_after_days=90,
    event_types_include=["organization.*", "user.*"],
    event_types_exclude=["system.*"],
    schedule_cron="0 2 1 * *",  # First day of month at 2 AM
    storage_location_template="s3://neo-archives/{year}/{month}/events-{date}.gz",
    compression_enabled=True,
    encryption_enabled=True,
    retention_days=2555,  # 7 years
    auto_delete_after_days=2920,  # 8 years
    created_by_user_id=UserId(uuid4())
)

# Create archive record
archive = EventArchive(
    id=uuid4(),
    archive_name="Events-2024-01",
    description="January 2024 event archive",
    policy=ArchivalPolicy.AGE_BASED,
    storage_type=StorageType.COMPRESSED_ARCHIVE,
    storage_location="s3://neo-archives/2024/01/events-2024-01-31.gz",
    status=ArchivalStatus.COMPLETED,
    event_count=1500000,
    size_bytes=524288000,  # ~500MB
    compression_ratio=0.15,  # 85% compression
    checksum="sha256:abc123...",
    events_from=datetime(2024, 1, 1),
    events_to=datetime(2024, 1, 31, 23, 59, 59),
    context_ids=[uuid4(), uuid4()],
    event_types=["organization.created", "user.updated"],
    retention_days=2555,
    created_by_user_id=UserId(uuid4()),
    tags={"quarter": "Q1", "year": "2024"}
)

# Check archival metrics
efficiency = archive.calculate_storage_efficiency()
print(f"Bytes per event: {efficiency['bytes_per_event']}")
print(f"Storage density: {efficiency['storage_density']} events/MB")
print(f"Archive expired: {archive.is_expired()}")
```

## API Reference

### DomainEvent Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `mark_as_processed()` | Mark event as processed for webhook delivery | None |
| `is_processed()` | Check if event has been processed | bool |
| `get_event_category()` | Get event category (before dot) | str |
| `get_event_action()` | Get event action (after dot) | str |
| `add_metadata(key, value)` | Add metadata key-value pair | None |
| `get_metadata(key, default)` | Get metadata value with default | Any |
| `to_dict()` | Convert to dictionary representation | Dict[str, Any] |
| `from_dict(data)` | Create from dictionary (class method) | DomainEvent |

### WebhookEndpoint Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `generate_signature(payload)` | Generate HMAC signature for payload | str |
| `verify_signature(payload, signature)` | Verify payload signature | bool |
| `activate()` | Activate the endpoint | None |
| `deactivate()` | Deactivate the endpoint | None |
| `verify()` | Mark endpoint as verified | None |
| `unverify()` | Mark endpoint as unverified | None |
| `mark_used()` | Update last used timestamp | None |
| `update_url(new_url)` | Update URL and reset verification | None |
| `rotate_secret()` | Generate new secret token | str (old secret) |
| `update_headers(headers)` | Update custom headers | None |
| `set_retry_config(max, backoff, multiplier)` | Update retry configuration | None |
| `calculate_retry_delay(attempt_number)` | Calculate retry delay for attempt | int (seconds) |
| `can_subscribe_to_verified_events()` | Check if can subscribe to verified events | bool |
| `get_request_headers()` | Get all request headers | Dict[str, str] |

### WebhookSubscription Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `activate()` | Activate subscription | None |
| `deactivate()` | Deactivate subscription | None |
| `update_last_triggered()` | Update last triggered timestamp | None |
| `update_filters(event_filters)` | Update event filters | None |
| `matches_event(event_type, event_data, context_id)` | Check if event matches subscription | bool |
| `to_dict()` | Convert to dictionary | Dict[str, Any] |
| `from_dict(data)` | Create from dictionary (class method) | WebhookSubscription |

### EventAction Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `matches_event(event_type, event_data)` | Check if action should trigger for event | bool |
| `update_trigger_stats(success)` | Update execution statistics | None |
| `pause()` | Pause the action | None |
| `resume()` | Resume the action | None |
| `disable()` | Disable the action | None |
| `enable()` | Enable the action | None |
| `archive()` | Archive the action | None |
| `update_configuration(new_config)` | Update action configuration | None |
| `add_condition(condition)` | Add filtering condition | None |
| `remove_condition(field, operator)` | Remove filtering condition | bool |
| `to_dict()` | Convert to dictionary | Dict[str, Any] |

### WebhookDelivery Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `add_attempt(attempt)` | Add delivery attempt and update status | None |
| `can_retry()` | Check if more retries are allowed | bool |
| `get_next_retry_delay_seconds()` | Calculate next retry delay | int |
| `schedule_next_retry()` | Schedule next retry attempt | None |
| `cancel(reason)` | Cancel webhook delivery | None |
| `is_ready_for_retry()` | Check if ready for retry now | bool |
| `get_latest_attempt()` | Get most recent attempt | Optional[WebhookDeliveryAttempt] |
| `get_successful_attempt()` | Get first successful attempt | Optional[WebhookDeliveryAttempt] |
| `get_total_duration_ms()` | Get total time spent on attempts | int |
| `get_success_rate()` | Get success rate (0.0 to 1.0) | float |
| `to_dict()` | Convert to dictionary | Dict[str, Any] |

## Configuration

### Validation Configuration

Configure validation rules through the webhook config service:

```python
from neo_commons.features.events.services.webhook_config_service import get_webhook_config

# Get current validation configuration
config = get_webhook_config()
validation_config = config.validation

# Validation settings
print(f"Max URL length: {validation_config.max_url_length}")
print(f"Allowed protocols: {validation_config.allowed_protocols}")
print(f"Block loopback: {validation_config.block_loopback}")
print(f"Block private networks: {validation_config.block_private_networks}")
```

### Event Type Patterns

Event types must follow the `category.action` pattern:

```python
# Valid event types
valid_types = [
    "organization.created",
    "user.updated", 
    "subscription.cancelled",
    "payment.processed",
    "team.member_added"
]

# Invalid event types
invalid_types = [
    "organization",      # Missing action
    "user.updated.now",  # Too many parts
    "User.Created",      # Wrong case
    "org-created"        # Wrong separator
]
```

### Retry Configuration

Configure retry behavior per endpoint:

```python
# Conservative retry (good for critical endpoints)
conservative_config = {
    "max_retry_attempts": 5,
    "retry_backoff_seconds": 10,
    "retry_backoff_multiplier": 2.0,
    "timeout_seconds": 60
}

# Aggressive retry (good for reliable endpoints)
aggressive_config = {
    "max_retry_attempts": 10,
    "retry_backoff_seconds": 2,
    "retry_backoff_multiplier": 1.5,
    "timeout_seconds": 30
}

# Quick fail (good for non-critical endpoints)
quick_fail_config = {
    "max_retry_attempts": 1,
    "retry_backoff_seconds": 5,
    "retry_backoff_multiplier": 1.0,
    "timeout_seconds": 15
}
```

## Best Practices

### 1. DRY Principles

**Reuse Event Types**: Define event types once and reuse across subscriptions.

```python
# ✅ Good: Define event types as constants
class EventTypes:
    ORG_CREATED = "organization.created"
    ORG_UPDATED = "organization.updated"
    USER_INVITED = "user.invited"

# ✅ Good: Use constants in subscriptions
subscription1 = WebhookSubscription(
    event_type=EventTypes.ORG_CREATED,
    # ... other fields
)

# ❌ Avoid: Hardcoding event types
subscription2 = WebhookSubscription(
    event_type="organization.created",  # Duplicate string
    # ... other fields
)
```

**Extract Common Validation**: Use centralized validation rules.

```python
# ✅ Good: Centralized validation
from neo_commons.features.events.utils.validation import WebhookValidationRules

def validate_endpoint_config(endpoint: WebhookEndpoint):
    WebhookValidationRules.validate_webhook_url(endpoint.endpoint_url)
    WebhookValidationRules.validate_endpoint_name(endpoint.name)
    WebhookValidationRules.validate_retry_config(
        endpoint.max_retry_attempts,
        endpoint.retry_backoff_seconds,
        float(endpoint.retry_backoff_multiplier)
    )

# ❌ Avoid: Duplicating validation logic
def custom_validation(endpoint):
    if not endpoint.endpoint_url.startswith('https://'):
        raise ValueError("URL must use HTTPS")
    # Duplicates existing validation
```

**Abstract Common Patterns**: Create reusable configuration templates.

```python
# ✅ Good: Configuration templates
class EndpointTemplates:
    @staticmethod
    def create_standard_webhook(name: str, url: str, user_id: UserId) -> WebhookEndpoint:
        return WebhookEndpoint(
            id=WebhookEndpointId(uuid4()),
            name=name,
            endpoint_url=url,
            http_method="POST",
            secret_token="",  # Auto-generated
            timeout_seconds=30,
            max_retry_attempts=3,
            retry_backoff_seconds=5,
            retry_backoff_multiplier=Decimal("2.0"),
            is_active=True,
            created_by_user_id=user_id
        )
    
    @staticmethod
    def create_enterprise_webhook(name: str, url: str, user_id: UserId) -> WebhookEndpoint:
        endpoint = EndpointTemplates.create_standard_webhook(name, url, user_id)
        endpoint.timeout_seconds = 60
        endpoint.max_retry_attempts = 5
        endpoint.custom_headers["X-Priority"] = "high"
        return endpoint
```

### 2. Dynamic Configuration

**Runtime Configuration**: Allow configuration injection at runtime.

```python
from typing import Protocol

class EventConfigurationProtocol(Protocol):
    def get_retry_config(self) -> Dict[str, Any]: ...
    def get_validation_rules(self) -> Dict[str, Any]: ...
    def get_archival_policy(self) -> Dict[str, Any]: ...

class DynamicEventService:
    def __init__(self, config: EventConfigurationProtocol):
        self._config = config
    
    def create_endpoint_with_config(self, name: str, url: str) -> WebhookEndpoint:
        retry_config = self._config.get_retry_config()
        
        return WebhookEndpoint(
            id=WebhookEndpointId(uuid4()),
            name=name,
            endpoint_url=url,
            timeout_seconds=retry_config["timeout_seconds"],
            max_retry_attempts=retry_config["max_attempts"],
            retry_backoff_seconds=retry_config["base_backoff"],
            # ... other fields
        )

# ✅ Usage with dependency injection
def create_service(config: EventConfigurationProtocol) -> DynamicEventService:
    return DynamicEventService(config)
```

**Environment-based Configuration**: Support multiple environments.

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class EnvironmentConfig:
    environment: str
    webhook_timeout: int
    max_retries: int
    enable_verification: bool
    archival_days: int

class EnvironmentAwareEventFactory:
    def __init__(self, env_config: EnvironmentConfig):
        self._config = env_config
    
    def create_event_type(self, event_type: str, display_name: str) -> WebhookEventType:
        return WebhookEventType(
            id=WebhookEventTypeId(uuid4()),
            event_type=event_type,
            category=event_type.split('.')[0],
            display_name=display_name,
            is_enabled=True,
            requires_verification=self._config.enable_verification
        )

# ✅ Environment-specific configurations
dev_config = EnvironmentConfig(
    environment="development",
    webhook_timeout=15,
    max_retries=1,
    enable_verification=False,
    archival_days=30
)

prod_config = EnvironmentConfig(
    environment="production",
    webhook_timeout=60,
    max_retries=5,
    enable_verification=True,
    archival_days=90
)
```

### 3. Flexible and Override-Capable Design

**Protocol-based Overrides**: Enable custom implementations.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SignatureGeneratorProtocol(Protocol):
    def generate_signature(self, payload: str, secret: str) -> str: ...
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool: ...

class CustomWebhookEndpoint(WebhookEndpoint):
    def __init__(self, *args, signature_generator: SignatureGeneratorProtocol = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._signature_generator = signature_generator
    
    def generate_signature(self, payload: str) -> str:
        if self._signature_generator:
            return self._signature_generator.generate_signature(payload, self.secret_token)
        return super().generate_signature(payload)

# ✅ Custom signature implementation
class HSMSignatureGenerator:
    def generate_signature(self, payload: str, secret: str) -> str:
        # Custom HSM-based signing
        return "hsm-" + hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()

# Override default behavior
custom_endpoint = CustomWebhookEndpoint(
    # ... standard parameters
    signature_generator=HSMSignatureGenerator()
)
```

**Pluggable Validation**: Allow custom validation rules.

```python
from typing import List, Callable

class ExtensibleEventAction(EventAction):
    def __init__(self, *args, custom_validators: List[Callable] = None, **kwargs):
        self._custom_validators = custom_validators or []
        super().__init__(*args, **kwargs)
    
    def matches_event(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        # Standard matching
        if not super().matches_event(event_type, event_data):
            return False
        
        # Custom validation
        for validator in self._custom_validators:
            if not validator(event_type, event_data):
                return False
        
        return True

# ✅ Custom business rules
def business_hours_validator(event_type: str, event_data: Dict[str, Any]) -> bool:
    """Only trigger actions during business hours."""
    import datetime
    now = datetime.datetime.now()
    return 9 <= now.hour <= 17

def high_value_customer_validator(event_type: str, event_data: Dict[str, Any]) -> bool:
    """Only trigger for high-value customers."""
    customer_value = event_data.get("customer", {}).get("lifetime_value", 0)
    return customer_value > 10000

action_with_custom_rules = ExtensibleEventAction(
    # ... standard parameters
    custom_validators=[business_hours_validator, high_value_customer_validator]
)
```

### 4. Error Handling and Validation

**Comprehensive Validation**: Validate all inputs with clear error messages.

```python
def create_webhook_endpoint_safely(
    name: str,
    url: str,
    created_by: UserId,
    **kwargs
) -> WebhookEndpoint:
    """Create webhook endpoint with comprehensive validation."""
    
    # Pre-validation
    if not name or not name.strip():
        raise ValueError("Endpoint name is required and cannot be empty")
    
    if len(name) > 200:
        raise ValueError(f"Endpoint name too long: {len(name)} characters (max 200)")
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")
    except Exception as e:
        raise ValueError(f"URL validation failed: {str(e)}")
    
    # Create with validation
    try:
        return WebhookEndpoint(
            id=WebhookEndpointId(uuid4()),
            name=name.strip(),
            endpoint_url=url,
            created_by_user_id=created_by,
            **kwargs
        )
    except ValueError as e:
        raise ValueError(f"Failed to create webhook endpoint: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error creating webhook endpoint: {str(e)}")

# ✅ Usage with proper error handling
try:
    endpoint = create_webhook_endpoint_safely(
        name="Customer Webhook",
        url="https://api.customer.com/webhooks",
        created_by=UserId(uuid4())
    )
    print("Endpoint created successfully")
except ValueError as e:
    print(f"Validation error: {e}")
except RuntimeError as e:
    print(f"System error: {e}")
```

**Graceful Degradation**: Handle partial failures gracefully.

```python
def create_subscription_with_fallback(
    endpoint_id: WebhookEndpointId,
    event_type: str,
    event_filters: Dict[str, Any] = None
) -> WebhookSubscription:
    """Create subscription with fallback to basic configuration."""
    
    try:
        # Try full configuration
        return WebhookSubscription(
            id=WebhookSubscriptionId(uuid4()),
            endpoint_id=endpoint_id,
            event_type_id=WebhookEventTypeId(uuid4()),  # Would be looked up
            event_type=event_type,
            event_filters=event_filters or {},
            is_active=True
        )
    except ValueError as e:
        if "event_filters" in str(e):
            # Fallback: Create without filters
            print(f"Warning: Invalid event filters, creating basic subscription: {e}")
            return WebhookSubscription(
                id=WebhookSubscriptionId(uuid4()),
                endpoint_id=endpoint_id,
                event_type_id=WebhookEventTypeId(uuid4()),
                event_type=event_type,
                event_filters={},  # Empty filters
                is_active=True
            )
        else:
            # Re-raise if not filter-related
            raise
```

## Common Pitfalls

### ❌ What to Avoid

**1. Hardcoding Configuration Values**
```python
# ❌ Bad: Hardcoded values
endpoint = WebhookEndpoint(
    timeout_seconds=30,      # Hardcoded
    max_retry_attempts=3,    # Hardcoded
    verify_ssl=True         # Hardcoded
)

# ✅ Good: Configuration-driven
endpoint = WebhookEndpoint(
    timeout_seconds=config.webhook_timeout,
    max_retry_attempts=config.max_retries,
    verify_ssl=config.verify_ssl_certificates
)
```

**2. Ignoring Timezone Handling**
```python
# ❌ Bad: Naive datetime
event = DomainEvent(
    occurred_at=datetime.now(),  # No timezone!
    # ... other fields
)

# ✅ Good: Timezone-aware datetime
event = DomainEvent(
    occurred_at=datetime.now(timezone.utc),
    # ... other fields
)
```

**3. Not Using Value Objects**
```python
# ❌ Bad: Raw UUIDs
def get_event(event_id: str) -> DomainEvent:
    # Lost type safety
    pass

# ✅ Good: Value objects
def get_event(event_id: EventId) -> DomainEvent:
    # Type safety guaranteed
    pass
```

**4. Coupling to Infrastructure**
```python
# ❌ Bad: Direct database calls in entities
class WebhookEndpoint:
    def save_to_database(self):
        # Violates Clean Architecture
        connection = psycopg2.connect(...)
        # ...

# ✅ Good: Repository pattern
class WebhookEndpointRepository:
    async def save(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        # Infrastructure concerns isolated
        pass
```

**5. Insufficient Validation**
```python
# ❌ Bad: Minimal validation
event_filters = {"user_id": user_input}  # No validation!

# ✅ Good: Comprehensive validation
def validate_event_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(filters, dict):
        raise ValueError("Filters must be a dictionary")
    
    validated = {}
    for key, value in filters.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"Filter key must be non-empty string: {key}")
        
        # Validate value based on type
        validated[key.strip()] = value
    
    return validated
```

## Testing

### Unit Testing Entities

```python
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from decimal import Decimal

from neo_commons.features.events.entities import WebhookEndpoint
from neo_commons.core.value_objects import WebhookEndpointId, UserId

class TestWebhookEndpoint:
    def test_create_valid_endpoint(self):
        """Test creating a valid webhook endpoint."""
        endpoint = WebhookEndpoint(
            id=WebhookEndpointId(uuid4()),
            name="Test Endpoint",
            endpoint_url="https://api.example.com/webhook",
            secret_token="test-secret",
            created_by_user_id=UserId(uuid4())
        )
        
        assert endpoint.name == "Test Endpoint"
        assert endpoint.is_active is True
        assert endpoint.is_verified is False
        assert endpoint.http_method == "POST"
    
    def test_invalid_url_raises_error(self):
        """Test that invalid URL raises ValueError."""
        with pytest.raises(ValueError, match="Invalid endpoint URL"):
            WebhookEndpoint(
                id=WebhookEndpointId(uuid4()),
                name="Test Endpoint",
                endpoint_url="not-a-url",
                secret_token="test-secret",
                created_by_user_id=UserId(uuid4())
            )
    
    def test_signature_generation_and_verification(self):
        """Test HMAC signature generation and verification."""
        endpoint = WebhookEndpoint(
            id=WebhookEndpointId(uuid4()),
            name="Test Endpoint",
            endpoint_url="https://api.example.com/webhook",
            secret_token="test-secret-key",
            created_by_user_id=UserId(uuid4())
        )
        
        payload = '{"test": "data"}'
        signature = endpoint.generate_signature(payload)
        
        assert signature.startswith("sha256=")
        assert endpoint.verify_signature(payload, signature) is True
        assert endpoint.verify_signature(payload, "invalid-signature") is False
    
    def test_retry_delay_calculation(self):
        """Test exponential backoff retry delay calculation."""
        endpoint = WebhookEndpoint(
            id=WebhookEndpointId(uuid4()),
            name="Test Endpoint",
            endpoint_url="https://api.example.com/webhook",
            secret_token="test-secret",
            retry_backoff_seconds=2,
            retry_backoff_multiplier=Decimal("2.0"),
            created_by_user_id=UserId(uuid4())
        )
        
        assert endpoint.calculate_retry_delay(0) == 0
        assert endpoint.calculate_retry_delay(1) == 2    # 2 * (2^0)
        assert endpoint.calculate_retry_delay(2) == 4    # 2 * (2^1)
        assert endpoint.calculate_retry_delay(3) == 8    # 2 * (2^2)
        assert endpoint.calculate_retry_delay(15) == 3600  # Capped at 1 hour

class TestEventAction:
    def test_event_matching(self):
        """Test event matching with conditions and filters."""
        action = EventAction(
            id=ActionId(uuid4()),
            name="Test Action",
            event_types=["organization.created"],
            conditions=[
                ActionCondition("data.plan", "equals", "enterprise")
            ],
            context_filters={"region": "us-east"},
            created_by_user_id=UserId(uuid4())
        )
        
        # Matching event
        event_data = {
            "data": {"plan": "enterprise"},
            "region": "us-east"
        }
        assert action.matches_event("organization.created", event_data) is True
        
        # Non-matching event (wrong plan)
        event_data = {
            "data": {"plan": "basic"},
            "region": "us-east"
        }
        assert action.matches_event("organization.created", event_data) is False

# Mock implementations for testing
class MockEventRepository:
    def __init__(self):
        self._events: List[DomainEvent] = []
    
    async def save(self, event: DomainEvent) -> DomainEvent:
        self._events.append(event)
        return event
    
    async def get_by_id(self, event_id: EventId) -> Optional[DomainEvent]:
        for event in self._events:
            if event.id == event_id:
                return event
        return None
    
    async def get_unprocessed(self, limit: int = 100) -> List[DomainEvent]:
        return [e for e in self._events if not e.is_processed()][:limit]

# Integration test example
class TestEventIntegration:
    @pytest.fixture
    def event_repository(self):
        return MockEventRepository()
    
    async def test_event_publishing_workflow(self, event_repository):
        """Test complete event publishing workflow."""
        # Create event
        event = DomainEvent(
            id=EventId(uuid4()),
            event_type=EventType("organization.created"),
            aggregate_id=uuid4(),
            aggregate_type="organization",
            event_data={"name": "Test Org", "plan": "enterprise"},
            triggered_by_user_id=UserId(uuid4())
        )
        
        # Save event
        saved_event = await event_repository.save(event)
        assert saved_event.id == event.id
        
        # Retrieve unprocessed events
        unprocessed = await event_repository.get_unprocessed()
        assert len(unprocessed) == 1
        assert unprocessed[0].id == event.id
        
        # Mark as processed
        event.mark_as_processed()
        assert event.is_processed() is True
```

### Integration Testing

```python
import asyncio
from neo_commons.features.events.entities import *
from neo_commons.core.value_objects import *

async def test_complete_webhook_flow():
    """Test complete webhook delivery flow."""
    
    # Create entities
    event_type = WebhookEventType(
        id=WebhookEventTypeId(uuid4()),
        event_type="organization.created",
        category="organization",
        display_name="Organization Created"
    )
    
    endpoint = WebhookEndpoint(
        id=WebhookEndpointId(uuid4()),
        name="Test Webhook",
        endpoint_url="https://httpbin.org/post",
        secret_token="test-secret",
        created_by_user_id=UserId(uuid4())
    )
    
    subscription = WebhookSubscription(
        id=WebhookSubscriptionId(uuid4()),
        endpoint_id=endpoint.id,
        event_type_id=event_type.id,
        event_type="organization.created",
        is_active=True
    )
    
    event = DomainEvent(
        id=EventId(uuid4()),
        event_type=EventType("organization.created"),
        aggregate_id=uuid4(),
        aggregate_type="organization",
        event_data={"name": "Test Organization"},
        triggered_by_user_id=UserId(uuid4())
    )
    
    # Test subscription matching
    assert subscription.matches_event(
        "organization.created",
        event.event_data
    ) is True
    
    # Create delivery
    delivery = WebhookDelivery(
        id=WebhookDeliveryId(uuid4()),
        webhook_endpoint_id=endpoint.id,
        webhook_event_id=event.id,
        max_attempts=3
    )
    
    # Simulate delivery attempt
    attempt = WebhookDeliveryAttempt(
        attempt_number=1,
        delivery_status=DeliveryStatus.SUCCESS,
        request_url=endpoint.endpoint_url,
        request_method="POST",
        response_status_code=200,
        response_time_ms=250
    )
    
    delivery.add_attempt(attempt)
    
    # Verify results
    assert delivery.overall_status == DeliveryStatus.SUCCESS
    assert delivery.get_success_rate() == 1.0
    assert delivery.can_retry() is True  # Still can retry if needed
    
    print("✅ Complete webhook flow test passed")

# Run integration test
if __name__ == "__main__":
    asyncio.run(test_complete_webhook_flow())
```

## Migration Guide

### From Legacy Event Systems

If migrating from a legacy event system, follow this pattern:

```python
# 1. Create mapping functions
def migrate_legacy_event(legacy_event: Dict[str, Any]) -> DomainEvent:
    """Convert legacy event to DomainEvent."""
    return DomainEvent(
        id=EventId(uuid4()),  # Generate new ID
        event_type=EventType(legacy_event["type"]),
        aggregate_id=UUID(legacy_event["entity_id"]),
        aggregate_type=legacy_event["entity_type"].lower(),
        event_data=legacy_event.get("payload", {}),
        event_metadata=legacy_event.get("metadata", {}),
        occurred_at=datetime.fromisoformat(legacy_event["timestamp"]),
        triggered_by_user_id=UserId(UUID(legacy_event["user_id"])) if legacy_event.get("user_id") else None
    )

# 2. Batch migration utility
def migrate_legacy_events(legacy_events: List[Dict[str, Any]]) -> List[DomainEvent]:
    """Migrate batch of legacy events."""
    migrated = []
    for legacy_event in legacy_events:
        try:
            domain_event = migrate_legacy_event(legacy_event)
            migrated.append(domain_event)
        except Exception as e:
            print(f"Failed to migrate event {legacy_event.get('id', 'unknown')}: {e}")
    
    return migrated
```

## Related Components

- **[Services](../services/README.md)**: Business logic layer using these entities
- **[Repositories](../repositories/README.md)**: Data persistence implementations
- **[Utils](../utils/README.md)**: Validation and utility functions
- **[Core Value Objects](../../../../core/value_objects/README.md)**: Type-safe identifiers
- **[Database Feature](../../database/README.md)**: Database connection management
- **[Cache Feature](../../cache/README.md)**: Redis caching for performance

This documentation provides the foundation for building robust, scalable event-driven systems using the neo-commons events entities module. Follow the patterns and practices outlined here to ensure maintainable, DRY-compliant code that leverages the full power of the NeoMultiTenant platform.