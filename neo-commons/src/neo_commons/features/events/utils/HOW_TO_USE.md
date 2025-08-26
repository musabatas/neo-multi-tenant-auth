# Events Utilities - HOW TO USE

## Overview

The Events Utilities module (`neo-commons/src/neo_commons/features/events/utils`) provides centralized utility functions, validators, HTTP header builders, error handlers, and SQL query constants for the NeoMultiTenant platform's events feature. This module follows DRY principles by eliminating code duplication across services and providing consistent, reusable patterns for webhook and event processing operations.

## Architecture

The utilities module is organized following the Feature-First + Clean Core architecture:

```
utils/
├── __init__.py              # Public API exports
├── validation.py            # Centralized validation rules with environment-aware policies  
├── error_handling.py        # Consistent error handling and exception mapping
├── queries.py               # SQL query constants for all repositories
└── header_builder.py        # HTTP header construction with context awareness
```

### Design Patterns

- **Centralized Validation**: All validation logic consolidated with environment-specific policies
- **Query Constants**: DRY SQL query management with schema parameterization
- **Error Mapping**: Consistent neo-commons exception handling across all operations
- **Builder Pattern**: Context-aware HTTP header construction for webhook operations
- **Configuration-Driven**: Runtime configuration through environment variables and webhook config service

## Installation/Setup

The utilities are automatically available when importing the events feature:

```python
# Import validation utilities
from neo_commons.features.events.utils import (
    WebhookValidationRules,
    ValidationOrchestrator,
    handle_webhook_error
)

# Import SQL queries
from neo_commons.features.events.utils import (
    WEBHOOK_ENDPOINT_INSERT,
    DOMAIN_EVENT_GET_UNPROCESSED,
    WEBHOOK_DELIVERY_UPDATE
)

# Import header builder
from neo_commons.features.events.utils.header_builder import WebhookHeaderBuilder
```

## Core Concepts

### 1. WebhookValidationRules - Environment-Aware Validation

Centralized validation with configurable thresholds that adapt based on environment (development, staging, production):

```python
from neo_commons.features.events.utils import WebhookValidationRules

# Validate webhook URL with environment-specific policies
try:
    WebhookValidationRules.validate_webhook_url("https://api.example.com/webhooks")
    WebhookValidationRules.validate_endpoint_name("Payment Notifications")
    WebhookValidationRules.validate_event_type("organization.created")
except ValueError as e:
    print(f"Validation failed: {e}")
```

### 2. ValidationOrchestrator - Comprehensive Validation Management

Orchestrates multiple validations with environment awareness and configuration management:

```python
from neo_commons.features.events.utils.validation import ValidationOrchestrator

# Initialize with environment profile override
orchestrator = ValidationOrchestrator(environment_profile="production")

# Complete endpoint validation
warnings = orchestrator.validate_webhook_endpoint_complete(
    endpoint_url="https://secure-api.example.com/webhooks",
    endpoint_name="Secure Payment Webhook",
    custom_headers={"Authorization": "Bearer token"},
    secret_token="secure-webhook-secret-key",
    timeout_seconds=30,
    max_retry_attempts=3,
    retry_backoff_seconds=2.0,
    retry_multiplier=2.0
)

if warnings:
    print(f"Validation warnings: {warnings}")
```

### 3. Error Handling - Consistent Exception Mapping

Maps webhook errors to appropriate neo-commons exceptions with contextual logging:

```python
from neo_commons.features.events.utils import handle_webhook_error
from neo_commons.core.value_objects import WebhookEndpointId

try:
    # Some webhook operation
    pass
except Exception as error:
    handle_webhook_error(
        operation="create",
        entity_type="webhook_endpoint",
        entity_id=WebhookEndpointId.generate(),
        error=error,
        context={"tenant_id": "tenant-123", "user_id": "user-456"}
    )
```

### 4. SQL Query Constants - DRY Database Operations

Parameterized SQL queries for consistent database operations across repositories:

```python
from neo_commons.features.events.utils import (
    WEBHOOK_ENDPOINT_INSERT,
    DOMAIN_EVENT_GET_UNPROCESSED,
    WEBHOOK_DELIVERY_UPDATE
)

# Use in repository
async def create_webhook_endpoint(self, endpoint_data: dict, schema: str = "tenant_template"):
    query = WEBHOOK_ENDPOINT_INSERT.format(schema=schema)
    result = await self.connection.fetchrow(query, *endpoint_data.values())
    return result
```

### 5. WebhookHeaderBuilder - Context-Aware Header Construction

Builds HTTP headers for different webhook contexts (delivery, verification, health checks):

```python
from neo_commons.features.events.utils.header_builder import WebhookHeaderBuilder, HeaderContext

# Build delivery headers with signature
headers = WebhookHeaderBuilder.build_delivery_headers(
    custom_headers={"X-API-Key": "secret"},
    signature="sha256=abc123def456",
    tenant_id="tenant-123",
    request_id="req-789"
)

# Build verification headers
verification_headers = WebhookHeaderBuilder.build_verification_headers(
    tenant_id="tenant-123",
    verification_level="comprehensive"
)
```

## Usage Examples

### Complete Webhook Endpoint Validation

```python
from neo_commons.features.events.utils.validation import ValidationOrchestrator

# Production-grade validation
orchestrator = ValidationOrchestrator("production")

# Validate complete webhook configuration
try:
    warnings = orchestrator.validate_webhook_endpoint_complete(
        endpoint_url="https://api.customer.com/webhooks/payment",
        endpoint_name="Customer Payment Webhook",
        custom_headers={
            "Authorization": "Bearer customer-api-token",
            "X-Customer-ID": "cust-12345"
        },
        secret_token="webhook-secret-32-chars-minimum",
        timeout_seconds=45,
        max_retry_attempts=5,
        retry_backoff_seconds=3.0,
        retry_multiplier=2.0
    )
    
    if warnings:
        logger.warning(f"Webhook validation warnings: {warnings}")
    
    print("✅ Webhook endpoint validation passed")
    
except ValueError as e:
    print(f"❌ Validation failed: {e}")
```

### Domain Event Validation

```python
from neo_commons.features.events.utils.validation import ValidationOrchestrator

orchestrator = ValidationOrchestrator()

# Validate complete domain event
try:
    warnings = orchestrator.validate_domain_event_complete(
        event_type="organization.member_added",
        aggregate_type="organization", 
        aggregate_version=5,
        event_data={
            "organization_id": "org-123",
            "member_id": "user-456", 
            "role": "admin",
            "added_by": "user-789"
        },
        metadata={
            "source": "admin_api",
            "correlation_id": "corr-abc123"
        }
    )
    
    if warnings:
        logger.warning(f"Event validation warnings: {warnings}")
        
    print("✅ Domain event validation passed")
    
except ValueError as e:
    print(f"❌ Event validation failed: {e}")
```

### Repository Pattern with Query Constants

```python
from neo_commons.features.events.utils import (
    WEBHOOK_ENDPOINT_INSERT,
    WEBHOOK_ENDPOINT_GET_BY_ID,
    WEBHOOK_DELIVERY_INSERT
)

class WebhookEndpointRepository:
    def __init__(self, connection_manager, schema: str = "tenant_template"):
        self.connection_manager = connection_manager
        self.schema = schema
    
    async def create_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Create webhook endpoint using standardized query."""
        query = WEBHOOK_ENDPOINT_INSERT.format(schema=self.schema)
        
        try:
            async with self.connection_manager.get_connection() as conn:
                result = await conn.fetchrow(
                    query,
                    endpoint.id, endpoint.name, endpoint.description,
                    endpoint.endpoint_url, endpoint.http_method,
                    endpoint.secret_token, endpoint.signature_header,
                    endpoint.custom_headers, endpoint.timeout_seconds,
                    endpoint.follow_redirects, endpoint.verify_ssl,
                    endpoint.max_retry_attempts, endpoint.retry_backoff_seconds,
                    endpoint.retry_backoff_multiplier, endpoint.is_active,
                    endpoint.is_verified, endpoint.created_by_user_id,
                    endpoint.context_id, endpoint.created_at, endpoint.updated_at
                )
                
                return WebhookEndpoint.from_db_row(result)
                
        except Exception as error:
            handle_webhook_endpoint_error(
                operation="create",
                endpoint_id=endpoint.id,
                error=error,
                context={"schema": self.schema}
            )
```

### HTTP Header Construction for Different Contexts

```python
from neo_commons.features.events.utils.header_builder import WebhookHeaderBuilder

# 1. Webhook Delivery Headers
delivery_headers = WebhookHeaderBuilder.build_delivery_headers(
    custom_headers={"X-API-Version": "v2"},
    signature="sha256=webhook-payload-signature",
    tenant_id="tenant-abc123",
    request_id="req-def456",
    signature_header_name="X-Webhook-Signature"  # Custom signature header
)

# 2. Endpoint Verification Headers  
verification_headers = WebhookHeaderBuilder.build_verification_headers(
    tenant_id="tenant-abc123",
    verification_level="comprehensive"
)

# 3. Health Check Headers
health_headers = WebhookHeaderBuilder.build_health_check_headers(
    request_id="health-check-789"
)

# 4. Manual Header Construction with Context
from neo_commons.features.events.utils.header_builder import HeaderContext

manual_headers = WebhookHeaderBuilder.build_headers(
    context=HeaderContext.DELIVERY,
    custom_headers={"X-Priority": "high"},
    signature="sha256=signature",
    tenant_id="tenant-123"
)
```

### Error Handling Patterns

```python
from neo_commons.features.events.utils import (
    handle_webhook_error,
    handle_webhook_endpoint_error,
    handle_domain_event_error
)

# Generic webhook error handling
def process_webhook_operation(operation_type: str, entity_id: str):
    try:
        # Webhook operation logic here
        pass
    except Exception as error:
        handle_webhook_error(
            operation=operation_type,
            entity_type="webhook_endpoint",
            entity_id=entity_id,
            error=error,
            context={
                "tenant_id": "tenant-123",
                "user_id": "user-456",
                "operation_context": "batch_processing"
            }
        )

# Specific error handlers
class WebhookService:
    async def create_endpoint(self, endpoint_data: dict):
        try:
            # Create endpoint logic
            pass
        except Exception as error:
            handle_webhook_endpoint_error(
                operation="create",
                endpoint_id=endpoint_data.get("id"),
                error=error,
                context={"data": endpoint_data}
            )
    
    async def process_domain_event(self, event_id: EventId):
        try:
            # Process event logic
            pass
        except Exception as error:
            handle_domain_event_error(
                operation="process",
                event_id=event_id,
                error=error,
                context={"processing_stage": "validation"}
            )
```

## API Reference

### WebhookValidationRules

**Class Methods:**

- `validate_webhook_url(url: str) -> None`: Validate webhook URL with environment-specific policies
- `validate_endpoint_name(name: str) -> None`: Validate endpoint name length and content
- `validate_event_type(event_type: str) -> None`: Validate event type format (category.action)
- `validate_secret_token(token: str) -> None`: Validate HMAC secret token constraints  
- `validate_custom_headers(headers: Dict[str, str]) -> None`: Validate custom headers dictionary
- `validate_retry_config(max_attempts: int, backoff_seconds: int, multiplier: float) -> None`: Validate retry configuration
- `validate_timeout_seconds(timeout: int) -> None`: Validate timeout constraints
- `validate_payload_size(payload_data: Dict[str, Any]) -> None`: Validate payload size limits
- `validate_response_constraints(response_size_bytes: int, response_time_ms: int) -> None`: Validate response constraints
- `validate_environment_specific_constraints(endpoint_url: str, environment_profile: str = None) -> None`: Apply environment-specific validation policies

### ValidationOrchestrator

**Constructor:**
- `ValidationOrchestrator(environment_profile: str = None)`: Initialize with optional environment override

**Methods:**
- `validate_webhook_endpoint_complete(...)`: Complete webhook endpoint validation with all parameters
- `validate_domain_event_complete(...)`: Complete domain event validation
- `get_validation_summary() -> Dict[str, Any]`: Get comprehensive validation configuration summary

### DomainEventValidationRules

**Class Methods:**
- `validate_aggregate_type(aggregate_type: str) -> None`: Validate aggregate type format
- `validate_event_data(event_data: Dict[str, Any]) -> None`: Validate event data payload with depth checks
- `validate_aggregate_version(version: int) -> None`: Validate aggregate version bounds

### Error Handling Functions

- `handle_webhook_error(operation, entity_type, entity_id=None, error=None, context=None)`: Generic webhook error handler
- `handle_webhook_endpoint_error(operation, endpoint_id=None, error=None, context=None)`: Webhook endpoint specific errors
- `handle_domain_event_error(operation, event_id=None, error=None, context=None)`: Domain event specific errors
- `handle_webhook_delivery_error(operation, delivery_id=None, error=None, context=None)`: Webhook delivery specific errors
- `handle_event_type_error(operation, type_id=None, error=None, context=None)`: Event type specific errors

### WebhookHeaderBuilder

**Class Methods:**
- `build_headers(context, custom_headers=None, signature=None, tenant_id=None, request_id=None, **kwargs)`: Generic header builder
- `build_delivery_headers(...)`: Headers for webhook delivery
- `build_verification_headers(...)`: Headers for endpoint verification
- `build_health_check_headers(...)`: Headers for health checks
- `build_connectivity_test_headers(...)`: Headers for connectivity testing
- `merge_headers(base_headers, additional_headers, allow_override=False)`: Merge header dictionaries
- `get_protected_headers() -> set`: Get protected headers that shouldn't be overridden
- `validate_headers(headers) -> tuple[bool, list[str]]`: Validate headers for common issues

### SQL Query Constants

**Webhook Endpoints:**
- `WEBHOOK_ENDPOINT_INSERT`: Create new webhook endpoint
- `WEBHOOK_ENDPOINT_UPDATE`: Update existing endpoint
- `WEBHOOK_ENDPOINT_GET_BY_ID`: Get endpoint by ID
- `WEBHOOK_ENDPOINT_LIST_ACTIVE`: List active endpoints
- `WEBHOOK_ENDPOINT_DELETE`: Delete endpoint

**Domain Events:**
- `DOMAIN_EVENT_INSERT`: Create new domain event
- `DOMAIN_EVENT_GET_BY_ID`: Get event by ID
- `DOMAIN_EVENT_GET_UNPROCESSED`: Get unprocessed events for batch processing
- `DOMAIN_EVENT_MARK_PROCESSED`: Mark event as processed

**Webhook Deliveries:**
- `WEBHOOK_DELIVERY_INSERT`: Create new delivery attempt
- `WEBHOOK_DELIVERY_UPDATE`: Update delivery status
- `WEBHOOK_DELIVERY_GET_PENDING_RETRIES`: Get deliveries pending retry

**Event Subscriptions:**
- `WEBHOOK_SUBSCRIPTION_INSERT_DETAILED`: Create detailed subscription
- `WEBHOOK_SUBSCRIPTION_GET_MATCHING_SUBSCRIPTIONS`: Find matching subscriptions for event type

## Configuration

All utilities support runtime configuration through the webhook configuration service and environment variables:

### Environment Variables

**Validation Configuration:**
```bash
# URL validation
WEBHOOK_MAX_URL_LENGTH=2048
WEBHOOK_ALLOWED_PROTOCOLS="http,https"
WEBHOOK_BLOCK_LOOPBACK=true
WEBHOOK_BLOCK_PRIVATE_NETWORKS=false

# Endpoint validation
WEBHOOK_MAX_ENDPOINT_NAME_LENGTH=255
WEBHOOK_MAX_DESCRIPTION_LENGTH=1000

# Security validation
WEBHOOK_MIN_SECRET_TOKEN_LENGTH=16
WEBHOOK_MAX_SECRET_TOKEN_LENGTH=512

# Headers validation
WEBHOOK_MAX_CUSTOM_HEADERS=20
WEBHOOK_MAX_HEADER_NAME_LENGTH=100
WEBHOOK_MAX_HEADER_VALUE_LENGTH=1000

# Performance limits
WEBHOOK_MAX_PAYLOAD_SIZE_MB=10
WEBHOOK_MAX_RESPONSE_SIZE_MB=5
WEBHOOK_MAX_RESPONSE_TIME_MS=30000

# Environment-specific settings
WEBHOOK_VALIDATION_PROFILE=production  # development, staging, production
WEBHOOK_STRICT_VALIDATION_MODE=true
WEBHOOK_ALLOW_TEST_ENDPOINTS=false
WEBHOOK_VALIDATE_SSL_CERTIFICATES=true
```

### Configuration Access

```python
from neo_commons.features.events.services.webhook_config_service import get_webhook_config

# Get validation configuration
config = get_webhook_config()
validation_config = config.validation

# Check environment-specific settings
environment_profile = validation_config.get_environment_profile()
is_production = validation_config.is_production_environment()
adjusted_limits = validation_config.get_adjusted_limits_for_environment()
```

## Best Practices

### 1. Use Environment-Specific Validation

Always use the `ValidationOrchestrator` for production systems as it provides environment-aware validation:

```python
# ✅ Good - Environment-aware validation
orchestrator = ValidationOrchestrator()
warnings = orchestrator.validate_webhook_endpoint_complete(...)

# ❌ Avoid - Direct rule usage without environment context
WebhookValidationRules.validate_webhook_url(url)  # Doesn't consider environment
```

### 2. Comprehensive Error Context

Always provide rich context when handling errors:

```python
# ✅ Good - Rich error context
handle_webhook_error(
    operation="create",
    entity_type="webhook_endpoint",
    entity_id=endpoint_id,
    error=error,
    context={
        "tenant_id": tenant_id,
        "user_id": user_id,
        "endpoint_url": endpoint_url,
        "request_id": request_id,
        "validation_stage": "url_verification"
    }
)

# ❌ Avoid - Minimal context
handle_webhook_error("create", "webhook_endpoint", error=error)
```

### 3. Schema Parameterization

Always parameterize SQL queries for multi-tenant flexibility:

```python
# ✅ Good - Parameterized schema
query = WEBHOOK_ENDPOINT_INSERT.format(schema=tenant_schema)
await conn.fetchrow(query, *params)

# ❌ Avoid - Hardcoded schema
hardcoded_query = "INSERT INTO tenant_template.webhook_endpoints ..."
```

### 4. Context-Appropriate Headers

Use specific header builders for different contexts:

```python
# ✅ Good - Context-specific builders
delivery_headers = WebhookHeaderBuilder.build_delivery_headers(...)
verification_headers = WebhookHeaderBuilder.build_verification_headers(...)

# ❌ Avoid - Generic headers for all contexts
generic_headers = {"Content-Type": "application/json"}  # Missing context
```

### 5. Validation Before Operations

Always validate inputs before performing operations:

```python
# ✅ Good - Validation first
try:
    orchestrator.validate_webhook_endpoint_complete(...)
    # Proceed with operation
    result = await create_webhook_endpoint(...)
except ValueError as validation_error:
    logger.error(f"Validation failed: {validation_error}")
    return error_response
```

## Common Pitfalls

### 1. Ignoring Environment-Specific Policies

**Problem**: Using static validation rules without considering environment context.

**Solution**: Always use `ValidationOrchestrator` which adapts to environment profiles:

```python
# ❌ Problem - Static validation
WebhookValidationRules.validate_webhook_url("http://localhost:3000/webhook")  # Fails in production

# ✅ Solution - Environment-aware
orchestrator = ValidationOrchestrator("development")  # Allows localhost in dev
orchestrator.validate_webhook_endpoint_complete(endpoint_url="http://localhost:3000/webhook", ...)
```

### 2. Not Using Query Constants

**Problem**: Duplicating SQL queries across repositories.

**Solution**: Use centralized query constants:

```python
# ❌ Problem - Duplicated SQL
query1 = "SELECT * FROM admin.webhook_endpoints WHERE id = $1"      # In repo 1
query2 = "SELECT * FROM tenant_template.webhook_endpoints WHERE id = $1"  # In repo 2

# ✅ Solution - Shared constants
from neo_commons.features.events.utils import WEBHOOK_ENDPOINT_GET_BY_ID
query = WEBHOOK_ENDPOINT_GET_BY_ID.format(schema=schema)
```

### 3. Insufficient Error Context

**Problem**: Generic error handling without context.

**Solution**: Provide comprehensive context for debugging:

```python
# ❌ Problem - Generic error
try:
    result = process_webhook()
except Exception as e:
    logger.error(f"Error: {e}")  # No context

# ✅ Solution - Rich context
try:
    result = process_webhook()
except Exception as e:
    handle_webhook_error(
        operation="process",
        entity_type="webhook_delivery",
        entity_id=delivery_id,
        error=e,
        context={
            "tenant_id": tenant_id,
            "endpoint_url": endpoint_url,
            "attempt_number": attempt_number
        }
    )
```

### 4. Header Conflicts

**Problem**: Custom headers overriding protected system headers.

**Solution**: Use proper header merging with conflict resolution:

```python
# ❌ Problem - Header conflicts
headers = {"User-Agent": "Custom Agent"}  # Overrides system user agent

# ✅ Solution - Proper header building
headers = WebhookHeaderBuilder.build_delivery_headers(
    custom_headers={"X-Custom-Header": "value"}  # Non-conflicting
)
```

### 5. Missing Validation Configuration

**Problem**: Hardcoded validation limits not adaptable to different environments.

**Solution**: Use configurable validation through environment variables:

```python
# ❌ Problem - Hardcoded limits
if len(webhook_url) > 2048:  # Fixed limit
    raise ValueError("URL too long")

# ✅ Solution - Configurable limits
WebhookValidationRules.validate_webhook_url(webhook_url)  # Uses config
```

## Testing

### Unit Testing Utilities

```python
import pytest
from neo_commons.features.events.utils.validation import ValidationOrchestrator, WebhookValidationRules

class TestWebhookValidation:
    def test_url_validation_development_environment(self):
        """Test that development environment allows localhost."""
        orchestrator = ValidationOrchestrator("development")
        
        # Should not raise in development
        warnings = orchestrator.validate_webhook_endpoint_complete(
            endpoint_url="http://localhost:3000/webhook",
            endpoint_name="Dev Webhook"
        )
        assert isinstance(warnings, list)
    
    def test_url_validation_production_environment(self):
        """Test that production environment blocks localhost."""
        orchestrator = ValidationOrchestrator("production")
        
        with pytest.raises(ValueError, match="Loopback addresses not allowed"):
            orchestrator.validate_webhook_endpoint_complete(
                endpoint_url="http://localhost:3000/webhook", 
                endpoint_name="Prod Webhook"
            )
    
    def test_event_type_validation(self):
        """Test event type format validation."""
        # Valid event types
        WebhookValidationRules.validate_event_type("organization.created")
        WebhookValidationRules.validate_event_type("user.updated")
        
        # Invalid event types
        with pytest.raises(ValueError):
            WebhookValidationRules.validate_event_type("invalid_format")
        
        with pytest.raises(ValueError):
            WebhookValidationRules.validate_event_type("too.many.dots")
```

### Integration Testing with Headers

```python
from neo_commons.features.events.utils.header_builder import WebhookHeaderBuilder

class TestHeaderBuilder:
    def test_delivery_headers_with_signature(self):
        """Test delivery header construction with signature."""
        headers = WebhookHeaderBuilder.build_delivery_headers(
            signature="sha256=test-signature",
            tenant_id="tenant-123",
            custom_headers={"X-API-Key": "secret"}
        )
        
        assert headers["User-Agent"] == "NeoMultiTenant-Webhooks/1.0"
        assert headers["X-Neo-Signature"] == "sha256=test-signature"
        assert headers["X-Neo-Tenant-ID"] == "tenant-123"
        assert headers["X-API-Key"] == "secret"
    
    def test_protected_header_handling(self):
        """Test that protected headers are handled correctly."""
        headers = WebhookHeaderBuilder.build_delivery_headers(
            custom_headers={"Content-Type": "text/plain"}  # Protected header
        )
        
        # Should preserve system content-type and prefix custom one
        assert headers["Content-Type"] == "application/json"
        assert "X-Endpoint-Content-Type" in headers
```

## Migration Guide

### From Direct SQL to Query Constants

**Before (Hardcoded SQL):**
```python
class WebhookRepository:
    async def create_endpoint(self, endpoint_data):
        query = """
            INSERT INTO tenant_template.webhook_endpoints 
            (id, name, endpoint_url, ...) 
            VALUES ($1, $2, $3, ...)
        """
        return await self.conn.fetchrow(query, *values)
```

**After (Query Constants):**
```python
from neo_commons.features.events.utils import WEBHOOK_ENDPOINT_INSERT

class WebhookRepository:
    def __init__(self, connection, schema="tenant_template"):
        self.connection = connection
        self.schema = schema
    
    async def create_endpoint(self, endpoint_data):
        query = WEBHOOK_ENDPOINT_INSERT.format(schema=self.schema)
        return await self.connection.fetchrow(query, *values)
```

### From Custom Validation to Centralized Rules

**Before (Custom Validation):**
```python
def validate_webhook_url(url):
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Invalid protocol")
    if len(url) > 2048:
        raise ValueError("URL too long")
    # More custom validation...
```

**After (Centralized Validation):**
```python
from neo_commons.features.events.utils.validation import ValidationOrchestrator

orchestrator = ValidationOrchestrator()
warnings = orchestrator.validate_webhook_endpoint_complete(
    endpoint_url=url,
    endpoint_name=name,
    # ... other parameters
)
```

## Related Components

- **Events Entities** (`../entities/`): Domain objects validated by these utilities
- **Events Services** (`../services/`): Business logic that uses validation and error handling
- **Events Repositories** (`../repositories/`): Data access using SQL query constants  
- **Events Adapters** (`../adapters/`): External integrations using header builders
- **Webhook Config Service** (`../services/webhook_config_service.py`): Configuration management for all utilities
- **Neo-Commons Core** (`../../core/`): Base exceptions and value objects used in error handling

The utilities module serves as the foundation for all events feature operations, providing consistent, reusable patterns that eliminate code duplication while maintaining flexibility through configuration and environment-specific policies.