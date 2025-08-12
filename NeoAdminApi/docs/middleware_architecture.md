# Middleware Architecture - NeoAdminApi

## Overview

The NeoAdminApi uses a comprehensive middleware stack that provides structured logging, security, performance monitoring, and request tracking. All middleware is organized into dedicated modules for maintainability and configurability.

## Middleware Components

### 1. Structured Logging Middleware (`logging.py`)

**Features:**
- Correlation ID generation and propagation
- Request/response logging with context
- User and tenant ID extraction
- Performance timing
- Comprehensive error logging
- Configurable body and header logging

**Context Variables:**
- `request_id`: Unique identifier for each request (UUIDv7)
- `correlation_id`: Correlation ID for request tracing
- `user_id`: Authenticated user ID (extracted from JWT/headers)
- `tenant_id`: Tenant context ID

**Usage:**
```python
from src.common.middleware.logging import get_request_context, get_correlation_id

# Get current request context
context = get_request_context()
logger.info("Processing request", **context)

# Get just correlation ID
correlation_id = get_correlation_id()
```

### 2. Security Headers Middleware (`security.py`)

**Features:**
- Content Security Policy (CSP)
- HSTS (HTTP Strict Transport Security)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
- Cross-Origin policies

**Configuration:**
- Environment-specific CSP rules
- Production vs development settings
- Customizable security headers
- Path exclusions for docs/health endpoints

### 3. Performance Timing Middleware (`timing.py`)

**Features:**
- Request timing measurement
- Slow request detection and logging
- Performance metrics collection
- Response size tracking
- Optimization suggestions

**Metrics:**
- Process time headers
- Performance classification (fast/normal/slow/very_slow)
- Path pattern grouping
- Response size analysis

### 4. Configuration Management (`config.py`)

**Features:**
- Environment-specific configurations
- Dynamic middleware enabling/disabling
- Centralized configuration management
- Development, production, and testing presets

## Middleware Order

The middleware stack is applied in the following order (first added = last executed):

1. **Trusted Hosts** - Validate request hosts
2. **Security Headers** - Add security headers
3. **CORS** - Handle cross-origin requests
4. **Rate Limiting** - Apply rate limits
5. **Logging** - Structure request/response logging
6. **Timing** - Performance measurement
7. **Response Size** - Size tracking and optimization

## Configuration

### Environment-Based Configuration

```python
# Automatic configuration based on environment
from src.common.middleware import setup_middleware

app = FastAPI()
setup_middleware(app)  # Uses environment-appropriate config
```

### Custom Configuration

```python
from src.common.middleware.config import MiddlewareConfig, MiddlewareManager

# Create custom configuration
config = MiddlewareConfig()
config.logging_config["log_body"] = True
config.security_config["force_https"] = False

# Apply to app
manager = MiddlewareManager(config)
manager.setup_middleware(app)
```

### Development vs Production

#### Development Settings:
- Full request/response logging
- Timing headers exposed
- Response size headers
- Relaxed CSP policies
- Rate limiting disabled

#### Production Settings:
- Reduced logging volume
- No timing/size headers
- Strict security policies
- HSTS enabled
- Rate limiting active

## Endpoints

### Health Check
- **Path:** `/health`
- **Purpose:** Service health monitoring
- **Response:** Service status, latency metrics

### Middleware Status (Development Only)
- **Path:** `/middleware`
- **Purpose:** Middleware configuration debugging
- **Response:** Active middleware status, performance metrics

## Context Variables

The middleware provides context variables that are available throughout the request lifecycle:

```python
from src.common.middleware.logging import (
    request_id_var,
    correlation_id_var,
    user_id_var,
    tenant_id_var
)

# Access in any handler or service
request_id = request_id_var.get()
user_id = user_id_var.get()
```

## Performance Monitoring

### Slow Request Detection
- Configurable thresholds (1s default, 5s very slow)
- Automatic logging with context
- Performance classification
- Path pattern analysis

### Metrics Collection
- Request count by endpoint
- Average response times
- Slow request percentages
- Response size analysis

## Security Features

### Headers Applied
- `Content-Security-Policy`: Prevents XSS attacks
- `Strict-Transport-Security`: Forces HTTPS
- `X-Frame-Options`: Prevents clickjacking
- `X-Content-Type-Options`: Prevents MIME sniffing
- `Permissions-Policy`: Controls browser features

### Rate Limiting
- Per-IP request limits
- Configurable windows (per minute/hour)
- Automatic IP extraction from proxy headers
- Path-based exclusions

## Best Practices

### 1. Context Usage
Always use context variables for logging:
```python
from src.common.middleware.logging import get_request_context

def my_handler():
    context = get_request_context()
    logger.info("Processing", **context)
```

### 2. Performance Monitoring
Check middleware status in development:
```bash
curl http://localhost:8001/middleware
```

### 3. Configuration
Use environment-specific configs:
```python
# Don't do this in production
config.security_config["force_https"] = False
```

### 4. Error Handling
Preserve context in error logs:
```python
try:
    # operation
except Exception as e:
    context = get_request_context()
    logger.error("Operation failed", error=str(e), **context)
    raise
```

## Troubleshooting

### Common Issues

1. **Missing correlation IDs**: Check if logging middleware is enabled
2. **Security headers not applied**: Verify security middleware configuration
3. **Slow requests not logged**: Check timing thresholds in configuration
4. **Rate limiting too aggressive**: Adjust limits or add path exclusions

### Debug Commands

```python
# Check middleware status
from src.common.middleware import get_middleware_status
status = get_middleware_status()

# Get performance metrics
from src.common.middleware.timing import get_performance_summary
metrics = get_performance_summary()