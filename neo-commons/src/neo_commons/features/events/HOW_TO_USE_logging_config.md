# HOW TO USE: Events Logging Configuration

## Overview

The Events Logging Configuration provides enterprise-grade structured logging capabilities specifically designed for the NeoMultiTenant platform's events feature. It enables comprehensive observability, monitoring, and troubleshooting of event actions, webhook deliveries, and system operations through standardized JSON logging with contextual enrichment.

## Architecture

The logging system follows a multi-layered architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Event Action Logging                        │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┤
│ EventActionLogger│EventActionFormatter│EventActionFilter│ Configuration    │
│ (High-level API) │ (Structured JSON)  │ (Level/Pattern) │ (Setup Utils)   │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                    Python Logging Framework                    │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┤
│   Handlers      │   Formatters    │    Filters      │    Loggers      │
│ Console/File    │ JSON/Standard   │  Level/Pattern  │ Hierarchical    │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

## Core Concepts

### 1. EventActionFormatter
Transforms log records into structured JSON with contextual enrichment:

```json
{
  "timestamp": "2024-12-19T10:30:45.123Z",
  "level": "INFO",
  "logger": "neo_commons.features.events.services",
  "message": "Action execution completed: User Registration Webhook (success)",
  "module": "action_execution_service",
  "function": "log_execution_completed",
  "line": 245,
  "context": {
    "action_id": "01HZ7K8M9N2P3Q4R5S6T7U8V9W",
    "action_name": "User Registration Webhook",
    "execution_id": "01HZ7K8P1A2B3C4D5E6F7G8H9I",
    "status": "success",
    "duration_ms": 150,
    "event_type": "user.created",
    "handler_type": "webhook"
  }
}
```

### 2. EventActionFilter
Provides intelligent log filtering based on levels and patterns:
- **Level Filtering**: Minimum log level enforcement
- **Pattern Matching**: Include/exclude based on logger names or modules
- **Performance Optimization**: Reduces log volume while preserving critical information

### 3. EventActionLogger
High-level utility class providing standardized logging methods for common event action scenarios.

### 4. Configuration Management
Flexible configuration system supporting multiple deployment scenarios:
- **Development**: Console logging with readable formatting
- **Production**: File + structured JSON logging with comprehensive context
- **Observability**: Integration with monitoring systems via structured logs

## Installation & Setup

### Basic Setup

```python
from neo_commons.features.events.logging_config import setup_event_action_logging

# Basic development setup
setup_event_action_logging(
    log_level="INFO",
    enable_structured_logging=True,
    enable_console_logging=True
)
```

### Production Setup

```python
from neo_commons.features.events.logging_config import setup_event_action_logging
import logging.config

# Production configuration with file logging
setup_event_action_logging(
    log_level="INFO",
    enable_structured_logging=True,
    log_file_path="/var/log/neomultitenant/event-actions.jsonl",
    enable_console_logging=False,  # Disable for production
    include_extra_fields=True
)
```

### Advanced Configuration with dictConfig

```python
from neo_commons.features.events.logging_config import get_logging_config_dict
import logging.config

# Generate configuration dictionary
config = get_logging_config_dict(
    log_level="INFO",
    log_file_path="/var/log/event-actions.jsonl",
    enable_structured_logging=True
)

# Apply configuration
logging.config.dictConfig(config)
```

## Usage Examples

### Basic Logging with EventActionLogger

```python
from neo_commons.features.events.logging_config import EventActionLogger
from neo_commons.core.value_objects import ActionId
from neo_commons.utils.uuid import generate_uuid_v7

# Initialize logger for service
logger = EventActionLogger("neo_commons.features.events.services.webhook")

# Log action lifecycle events
action_id = str(generate_uuid_v7())
execution_id = str(generate_uuid_v7())

# Action management
logger.log_action_created(
    action_name="User Registration Webhook",
    action_id=action_id,
    handler_type="webhook"
)

logger.log_action_updated(
    action_name="User Registration Webhook",
    action_id=action_id,
    fields_updated=["configuration", "timeout_seconds"]
)

# Execution tracking
logger.log_execution_started(
    action_name="User Registration Webhook",
    action_id=action_id,
    execution_id=execution_id,
    event_type="user.created"
)

logger.log_execution_completed(
    action_name="User Registration Webhook",
    action_id=action_id,
    execution_id=execution_id,
    status="success",
    duration_ms=150
)

# Error handling
logger.log_execution_failed(
    action_name="User Registration Webhook",
    action_id=action_id,
    execution_id=execution_id,
    error_message="Connection timeout to webhook endpoint",
    retry_count=2
)

# Critical alerts
logger.log_high_error_rate_alert(
    action_name="User Registration Webhook",
    action_id=action_id,
    success_rate=75.5,
    threshold=90.0,
    total_executions=100
)
```

### Integration with Services

```python
import logging
from neo_commons.features.events.logging_config import setup_event_action_logging

# Setup logging for the entire events feature
setup_event_action_logging(
    log_level="INFO",
    enable_structured_logging=True,
    log_file_path="/var/log/event-actions.jsonl"
)

# Use standard Python logging in services
logger = logging.getLogger("neo_commons.features.events.services.execution")

class ActionExecutionService:
    def __init__(self):
        self.logger = logger
    
    async def execute_action(self, action, event_data):
        # Log with contextual information
        self.logger.info(
            f"Starting execution of action: {action.name}",
            extra={
                "action_id": str(action.id.value),
                "action_name": action.name,
                "handler_type": action.handler_type.value,
                "execution_mode": action.execution_mode.value,
                "event_type": event_data.get("event_type"),
                "tenant_id": action.tenant_id,
                "user_id": action.created_by_user_id
            }
        )
        
        try:
            result = await self._perform_execution(action, event_data)
            
            self.logger.info(
                f"Action execution completed: {action.name}",
                extra={
                    "action_id": str(action.id.value),
                    "status": "success",
                    "duration_ms": result.duration_ms
                }
            )
            
        except Exception as e:
            self.logger.error(
                f"Action execution failed: {action.name}",
                extra={
                    "action_id": str(action.id.value),
                    "error_message": str(e),
                    "status": "failed"
                },
                exc_info=True  # Include stack trace
            )
```

### Custom Formatters for Specific Use Cases

```python
from neo_commons.features.events.logging_config import EventActionFormatter
import logging

# Create custom formatter for alerts
class AlertFormatter(EventActionFormatter):
    def format(self, record):
        # Get base structured format
        log_data = super().format(record)
        
        # Parse back to dict for modification
        import json
        data = json.loads(log_data)
        
        # Add alert-specific enrichment
        if hasattr(record, 'alert_type'):
            data['alert'] = {
                'type': record.alert_type,
                'severity': self._calculate_severity(record),
                'requires_action': record.levelno >= logging.ERROR
            }
        
        return json.dumps(data, default=str)
    
    def _calculate_severity(self, record):
        if record.levelno >= logging.CRITICAL:
            return "critical"
        elif record.levelno >= logging.ERROR:
            return "high"
        elif record.levelno >= logging.WARNING:
            return "medium"
        else:
            return "low"

# Use custom formatter
handler = logging.StreamHandler()
handler.setFormatter(AlertFormatter())
```

### Multi-Environment Configuration

```python
import os
from neo_commons.features.events.logging_config import setup_event_action_logging

def configure_logging():
    """Configure logging based on environment."""
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "development":
        setup_event_action_logging(
            log_level="DEBUG",
            enable_structured_logging=False,  # Human-readable for dev
            enable_console_logging=True,
            include_extra_fields=True
        )
    
    elif env == "staging":
        setup_event_action_logging(
            log_level="INFO",
            enable_structured_logging=True,
            log_file_path="/var/log/staging/event-actions.jsonl",
            enable_console_logging=True,
            include_extra_fields=True
        )
    
    elif env == "production":
        setup_event_action_logging(
            log_level="INFO",
            enable_structured_logging=True,
            log_file_path="/var/log/production/event-actions.jsonl",
            enable_console_logging=False,  # File only in production
            include_extra_fields=True
        )
    
    else:
        raise ValueError(f"Unknown environment: {env}")

# Initialize logging
configure_logging()
```

## API Reference

### setup_event_action_logging()

**Purpose**: Configure logging for the entire events feature with sensible defaults.

```python
def setup_event_action_logging(
    log_level: str = "INFO",
    enable_structured_logging: bool = True,
    log_file_path: Optional[str] = None,
    enable_console_logging: bool = True,
    include_extra_fields: bool = True
) -> None
```

**Parameters**:
- `log_level`: Minimum logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
- `enable_structured_logging`: Use JSON formatting vs. standard text formatting
- `log_file_path`: Optional file path for persistent logging
- `enable_console_logging`: Enable console output (useful for development)
- `include_extra_fields`: Include contextual fields in structured logs

**Loggers Configured**:
- `neo_commons.features.events`
- `neo_commons.features.events.services`
- `neo_commons.features.events.handlers`
- `neo_commons.features.events.repositories`

### get_logging_config_dict()

**Purpose**: Generate logging configuration dictionary for `logging.config.dictConfig()`.

```python
def get_logging_config_dict(
    log_level: str = "INFO",
    log_file_path: Optional[str] = None,
    enable_structured_logging: bool = True
) -> Dict[str, Any]
```

**Returns**: Complete logging configuration dictionary compatible with Python's `dictConfig`.

### EventActionLogger Class

**Purpose**: High-level logging utility with predefined methods for common scenarios.

```python
class EventActionLogger:
    def __init__(self, logger_name: str)
    
    # Action lifecycle
    def log_action_created(self, action_name: str, action_id: str, handler_type: str) -> None
    def log_action_updated(self, action_name: str, action_id: str, fields_updated: list) -> None
    def log_action_deleted(self, action_name: str, action_id: str) -> None
    
    # Execution tracking
    def log_execution_started(self, action_name: str, action_id: str, execution_id: str, event_type: str) -> None
    def log_execution_completed(self, action_name: str, action_id: str, execution_id: str, status: str, duration_ms: int) -> None
    def log_execution_failed(self, action_name: str, action_id: str, execution_id: str, error_message: str, retry_count: int = 0) -> None
    
    # Alerts and monitoring
    def log_high_error_rate_alert(self, action_name: str, action_id: str, success_rate: float, threshold: float, total_executions: int) -> None
```

### EventActionFormatter Class

**Purpose**: JSON formatter with contextual field extraction.

```python
class EventActionFormatter(logging.Formatter):
    def __init__(self, include_extra_fields: bool = True)
    def format(self, record: logging.LogRecord) -> str
```

**Extracted Fields**:
- **Event Action Fields**: `action_id`, `action_name`, `execution_id`, `event_type`, `handler_type`, `execution_mode`, `status`, `duration_ms`, `retry_count`, `error_message`, `tenant_id`, `user_id`
- **Alert Fields**: `alert_type`, `threshold`, `success_rate`, `total_executions`

### EventActionFilter Class

**Purpose**: Intelligent log filtering based on levels and patterns.

```python
class EventActionFilter(logging.Filter):
    def __init__(self, min_level: str = "INFO", include_patterns: Optional[list] = None)
    def filter(self, record: logging.LogRecord) -> bool
```

## Configuration Options

### Log Levels

| Level | Description | Use Cases |
|-------|-------------|-----------|
| `DEBUG` | Detailed diagnostic information | Development, troubleshooting |
| `INFO` | General operational messages | Production monitoring, audit trails |
| `WARNING` | Warning messages for unusual but not error conditions | Performance degradation, retries |
| `ERROR` | Error conditions that don't stop the application | Handler failures, validation errors |
| `CRITICAL` | Critical errors requiring immediate attention | System failures, high error rates |

### Structured Logging Fields

#### Base Fields (Always Present)
- `timestamp`: ISO 8601 formatted timestamp
- `level`: Log level name
- `logger`: Logger name hierarchy
- `message`: Human-readable message
- `module`: Python module name
- `function`: Function name where log was generated
- `line`: Line number

#### Context Fields (When Available)
- `action_id`: Unique action identifier
- `action_name`: Human-readable action name
- `execution_id`: Specific execution instance
- `event_type`: Domain event type that triggered action
- `handler_type`: Action handler type (webhook, email, etc.)
- `execution_mode`: Sync/async/queued execution mode
- `status`: Execution status
- `duration_ms`: Execution duration in milliseconds
- `retry_count`: Number of retries attempted
- `error_message`: Error details for failed executions
- `tenant_id`: Multi-tenant isolation identifier
- `user_id`: User context for audit trails

#### Alert Fields (For Monitoring Events)
- `alert_type`: Type of alert (high_error_rate, etc.)
- `threshold`: Configured threshold value
- `success_rate`: Current success rate percentage
- `total_executions`: Total execution count

### File Output Configuration

```python
# Log rotation with TimedRotatingFileHandler
import logging.handlers

def setup_rotating_logs():
    handler = logging.handlers.TimedRotatingFileHandler(
        filename="/var/log/event-actions.jsonl",
        when="midnight",
        interval=1,
        backupCount=30,  # Keep 30 days
        encoding="utf-8"
    )
    
    formatter = EventActionFormatter(include_extra_fields=True)
    handler.setFormatter(formatter)
    
    logger = logging.getLogger("neo_commons.features.events")
    logger.addHandler(handler)
```

## Best Practices

### 1. Development Environment

```python
# Use human-readable logging for development
setup_event_action_logging(
    log_level="DEBUG",
    enable_structured_logging=False,  # More readable during development
    enable_console_logging=True,
    include_extra_fields=True
)
```

### 2. Production Environment

```python
# Use structured logging with file output for production
setup_event_action_logging(
    log_level="INFO",
    enable_structured_logging=True,
    log_file_path="/var/log/neomultitenant/event-actions.jsonl",
    enable_console_logging=False,  # Reduce noise in production logs
    include_extra_fields=True
)
```

### 3. Contextual Logging

Always include relevant context when logging:

```python
logger.info(
    "Processing webhook delivery",
    extra={
        "action_id": action_id,
        "webhook_url": webhook_config.url,
        "event_type": event.event_type,
        "tenant_id": event.tenant_id,
        "retry_count": delivery_attempt.retry_count
    }
)
```

### 4. Error Handling with Structured Context

```python
try:
    await webhook_client.deliver(payload, webhook_config.url)
except aiohttp.ClientTimeout as e:
    logger.error(
        "Webhook delivery timeout",
        extra={
            "action_id": action_id,
            "webhook_url": webhook_config.url,
            "timeout_seconds": webhook_config.timeout,
            "error_type": "timeout"
        },
        exc_info=True  # Include stack trace
    )
except aiohttp.ClientError as e:
    logger.error(
        "Webhook delivery client error",
        extra={
            "action_id": action_id,
            "webhook_url": webhook_config.url,
            "status_code": getattr(e, 'status', None),
            "error_type": "client_error"
        },
        exc_info=True
    )
```

### 5. Performance Considerations

- **Use appropriate log levels**: Don't use DEBUG in production unless troubleshooting
- **Batch log operations**: Avoid excessive logging in tight loops
- **Monitor log volume**: Set up alerts for unusually high log volumes
- **Optimize formatters**: Custom formatters should be efficient

### 6. Security and Privacy

```python
# Sanitize sensitive data before logging
def sanitize_log_data(data: dict) -> dict:
    """Remove or mask sensitive fields before logging."""
    sensitive_fields = ['password', 'token', 'api_key', 'secret']
    
    sanitized = data.copy()
    for field in sensitive_fields:
        if field in sanitized:
            sanitized[field] = "***REDACTED***"
    
    return sanitized

# Use in logging calls
logger.info(
    "Action configuration updated",
    extra=sanitize_log_data({
        "action_id": action_id,
        "configuration": action.configuration
    })
)
```

## Common Pitfalls

### 1. Missing Context Setup
**Problem**: Logs lack contextual information making debugging difficult.

**Solution**: Always call `setup_event_action_logging()` during application initialization:

```python
# In your application startup (main.py, app.py, etc.)
from neo_commons.features.events.logging_config import setup_event_action_logging

async def startup():
    # Configure logging first
    setup_event_action_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        enable_structured_logging=True,
        log_file_path=os.getenv("LOG_FILE_PATH")
    )
    
    # Then initialize other services
    await initialize_services()
```

### 2. Logger Name Inconsistency
**Problem**: Using inconsistent logger names breaks filtering and hierarchy.

**Solution**: Use consistent, hierarchical logger names:

```python
# Good: Hierarchical naming
logger = logging.getLogger("neo_commons.features.events.services.webhook")
action_logger = EventActionLogger("neo_commons.features.events.services.execution")

# Bad: Inconsistent naming
logger = logging.getLogger("webhook_service")
action_logger = EventActionLogger("my_service")
```

### 3. Excessive Debug Logging in Production
**Problem**: DEBUG level logging in production creates log noise and performance issues.

**Solution**: Use environment-based configuration:

```python
import os

def get_log_level():
    env = os.getenv("ENVIRONMENT", "development")
    if env == "production":
        return "INFO"
    elif env == "staging":
        return "INFO"
    else:
        return "DEBUG"

setup_event_action_logging(log_level=get_log_level())
```

### 4. Ignoring Log Filters
**Problem**: Not configuring filters leads to excessive log volume.

**Solution**: Use EventActionFilter with appropriate patterns:

```python
from neo_commons.features.events.logging_config import EventActionFilter

# Configure filter to only log events-related modules
filter = EventActionFilter(
    min_level="INFO",
    include_patterns=["neo_commons.features.events"]
)

handler = logging.StreamHandler()
handler.addFilter(filter)
```

### 5. Not Handling Log Rotation
**Problem**: Log files grow indefinitely in production.

**Solution**: Use rotating file handlers:

```python
import logging.handlers
from neo_commons.features.events.logging_config import EventActionFormatter

# Configure rotating log handler
rotating_handler = logging.handlers.RotatingFileHandler(
    "/var/log/event-actions.log",
    maxBytes=100_000_000,  # 100MB
    backupCount=10,
    encoding="utf-8"
)
rotating_handler.setFormatter(EventActionFormatter())
```

## Testing

### Unit Testing with Logging

```python
import logging
import unittest
from unittest.mock import MagicMock
from neo_commons.features.events.logging_config import EventActionLogger

class TestEventActionLogging(unittest.TestCase):
    def setUp(self):
        self.mock_logger = MagicMock()
        self.event_logger = EventActionLogger("test.logger")
        self.event_logger.logger = self.mock_logger
    
    def test_log_action_created(self):
        # Test logging action creation
        self.event_logger.log_action_created(
            "Test Action",
            "action_123",
            "webhook"
        )
        
        # Verify logging call
        self.mock_logger.info.assert_called_once()
        args, kwargs = self.mock_logger.info.call_args
        
        self.assertIn("Test Action", args[0])
        self.assertEqual(kwargs["extra"]["action_id"], "action_123")
        self.assertEqual(kwargs["extra"]["handler_type"], "webhook")
    
    def test_structured_logging_format(self):
        # Test structured format output
        from neo_commons.features.events.logging_config import EventActionFormatter
        
        formatter = EventActionFormatter(include_extra_fields=True)
        
        # Create mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=100,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.action_id = "test_action_123"
        record.status = "success"
        
        # Format record
        formatted = formatter.format(record)
        
        # Verify JSON structure
        import json
        data = json.loads(formatted)
        
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["message"], "Test message")
        self.assertEqual(data["context"]["action_id"], "test_action_123")
        self.assertEqual(data["context"]["status"], "success")

class TestLoggingIntegration(unittest.TestCase):
    def setUp(self):
        # Setup test logging configuration
        from neo_commons.features.events.logging_config import setup_event_action_logging
        import tempfile
        
        self.temp_log_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
        setup_event_action_logging(
            log_level="INFO",
            enable_structured_logging=True,
            log_file_path=self.temp_log_file.name,
            enable_console_logging=False
        )
    
    def tearDown(self):
        import os
        os.unlink(self.temp_log_file.name)
    
    def test_end_to_end_logging(self):
        # Test actual logging output
        logger = logging.getLogger("neo_commons.features.events.services")
        
        logger.info(
            "Test execution completed",
            extra={
                "action_id": "test_123",
                "status": "success",
                "duration_ms": 100
            }
        )
        
        # Read log file
        with open(self.temp_log_file.name, 'r') as f:
            log_content = f.read()
        
        # Verify structured log content
        import json
        log_data = json.loads(log_content.strip())
        
        self.assertEqual(log_data["level"], "INFO")
        self.assertEqual(log_data["context"]["action_id"], "test_123")
        self.assertEqual(log_data["context"]["status"], "success")
```

## Migration Guide

### From Standard Python Logging

If you're currently using standard Python logging in events-related code:

```python
# Before: Standard logging
import logging
logger = logging.getLogger(__name__)

logger.info(f"Action {action_name} completed")

# After: Structured logging with context
from neo_commons.features.events.logging_config import setup_event_action_logging

# Setup during application initialization
setup_event_action_logging(enable_structured_logging=True)

# Use with contextual information
logger.info(
    f"Action {action_name} completed",
    extra={
        "action_id": str(action.id.value),
        "action_name": action_name,
        "status": "success",
        "duration_ms": execution_time
    }
)
```

### From Custom Logging Solutions

Replace custom logging with the standardized events logging:

```python
# Before: Custom logging utility
class MyCustomLogger:
    def log_action_event(self, action_id, event, details):
        print(f"{datetime.now()}: Action {action_id} - {event}: {details}")

# After: Use EventActionLogger
from neo_commons.features.events.logging_config import EventActionLogger

logger = EventActionLogger("neo_commons.features.events.services.my_service")

# Structured, standardized logging
logger.log_execution_completed(
    action_name="My Action",
    action_id=action_id,
    execution_id=execution_id,
    status="success",
    duration_ms=150
)
```

## Related Components

### Integration with Monitoring Services

```python
from neo_commons.features.events.services.action_monitoring_service import ActionMonitoringService
from neo_commons.features.events.logging_config import setup_event_action_logging

# Configure logging and monitoring together
setup_event_action_logging(
    log_level="INFO",
    enable_structured_logging=True,
    log_file_path="/var/log/event-actions.jsonl"
)

# Monitoring service will use configured loggers
monitoring_service = ActionMonitoringService(
    execution_repository,
    monitoring_config
)
```

### Integration with Event Dispatcher

```python
from neo_commons.features.events.services.event_dispatcher_service import EventDispatcherService

# EventDispatcherService will automatically use configured logging
dispatcher = EventDispatcherService(
    event_repository,
    webhook_delivery_service,
    action_execution_service  # Uses configured logging internally
)
```

### Integration with Action Execution Service

```python
from neo_commons.features.events.services.action_execution_service import ActionExecutionService

# Service uses configured logging automatically
execution_service = ActionExecutionService(
    execution_repository,
    handler_registry
)

# Logging is handled internally with proper context
await execution_service.execute_action(action, event_data)
```

This logging configuration system provides enterprise-grade observability for the NeoMultiTenant platform's events feature, enabling comprehensive monitoring, troubleshooting, and audit capabilities through standardized structured logging.