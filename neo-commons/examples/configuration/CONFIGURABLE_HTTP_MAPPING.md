# Configurable HTTP Status Mapping

This document explains how to use the configurable HTTP status mapping system in neo-commons.

## Overview

The configurable HTTP status mapping allows you to customize which HTTP status codes are returned for different exception types through runtime configuration, rather than hardcoded mappings.

## Key Features

- **Runtime Configuration**: Change status codes without code changes
- **Protocol-Based**: Uses `ConfigurationProtocol` for flexibility 
- **Inheritance Support**: Configure parent classes to affect subclasses
- **Performance Optimized**: Results are cached for repeated lookups
- **Backward Compatible**: Falls back to default mappings when not configured

## Basic Usage

### 1. Using Default Mappings (No Configuration)

```python
from neo_commons.core.exceptions import get_http_status_code, UserNotFoundError

# Uses default mapping (401 for UserNotFoundError)
error = UserNotFoundError("User does not exist")
status_code = get_http_status_code(error)  # Returns 401
```

### 2. Setting Up Configuration

```python
from neo_commons.core.exceptions import set_configuration_provider
from neo_commons.core.shared.application import ConfigurationProtocol

class MyConfiguration:
    def __init__(self):
        self._config = {
            # Override UserNotFoundError to return 404 instead of 401
            "http_status_mapping.UserNotFoundError": 404,
            
            # Make all DatabaseError subclasses return 503
            "http_status_mapping.DatabaseError": 503,
        }
    
    def get(self, key: str, default=None):
        return self._config.get(key, default)
    
    def set(self, key: str, value): 
        self._config[key] = value
    
    def get_section(self, section: str):
        return {}

# Set global configuration (typically done at application startup)
config = MyConfiguration()
set_configuration_provider(config)
```

### 3. Using Configured Mappings

```python
from neo_commons.core.exceptions import get_http_status_code
from neo_commons.core.exceptions.domain import UserNotFoundError
from neo_commons.core.exceptions.database import DatabaseError, QueryError

# Now uses configured values
user_error = UserNotFoundError("User not found")
print(get_http_status_code(user_error))  # Returns 404 (configured override)

db_error = DatabaseError("Connection failed") 
print(get_http_status_code(db_error))  # Returns 503 (configured override)

query_error = QueryError("Invalid SQL")
print(get_http_status_code(query_error))  # Returns 503 (inherits from DatabaseError)
```

## Configuration Keys

Configuration keys follow the pattern: `http_status_mapping.{ExceptionClassName}`

### Common Overrides

```python
{
    # Authentication/Authorization
    "http_status_mapping.UserNotFoundError": 404,         # Default: 401
    "http_status_mapping.InvalidCredentialsError": 422,   # Default: 401
    "http_status_mapping.PermissionDeniedError": 451,     # Default: 403
    
    # Database Errors
    "http_status_mapping.DatabaseError": 503,             # Default: 500 (affects all subclasses)
    "http_status_mapping.ConnectionError": 503,           # Default: 500
    
    # Tenant Management
    "http_status_mapping.TenantSuspendedError": 451,      # Default: 403
    "http_status_mapping.TenantNotFoundError": 410,       # Default: 404
    
    # Rate Limiting
    "http_status_mapping.DatabaseRateLimitError": 503,    # Default: 429
}
```

## Advanced Usage

### 1. Inheritance-Based Configuration

Configure parent classes to affect all subclasses:

```python
# Configure base DatabaseError class
"http_status_mapping.DatabaseError": 503

# All database exceptions now return 503:
# - QueryError, ConnectionError, TransactionError, etc.
```

### 2. Cache Management

```python
from neo_commons.core.exceptions import clear_mapping_cache

# Clear cache when configuration changes at runtime
config.set("http_status_mapping.UserNotFoundError", 422)
clear_mapping_cache()  # Force re-evaluation of mappings
```

### 3. Monitoring and Statistics

```python
from neo_commons.core.exceptions import get_mapping_statistics

stats = get_mapping_statistics()
print(f"Cached mappings: {stats['cached_mappings']}")
print(f"Has configuration: {stats['has_config']}")
print(f"Cache entries: {stats['cache_entries']}")
```

### 4. Direct Mapper Usage

```python
from neo_commons.core.exceptions import ConfigurableHttpStatusMapper

# Create mapper with custom configuration
mapper = ConfigurableHttpStatusMapper(my_config)

# Get status codes
status = mapper.get_status_code(exception)

# Get statistics
stats = mapper.get_mapping_stats()
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from neo_commons.core.exceptions import (
    get_http_status_code, 
    set_configuration_provider,
    NeoCommonsError
)

app = FastAPI()

# Configure at startup
@app.on_event("startup")
async def configure_http_mapping():
    config = MyConfigurationProvider()  # Your config implementation
    set_configuration_provider(config)

# Exception handler
@app.exception_handler(NeoCommonsError)
async def neo_commons_exception_handler(request, exc: NeoCommonsError):
    status_code = get_http_status_code(exc)
    return JSONResponse(
        status_code=status_code,
        content={"error": exc.message, "code": exc.error_code}
    )
```

### Environment-Based Configuration

```python
import os

class EnvironmentHttpConfig:
    def get(self, key: str, default=None):
        if not key.startswith("http_status_mapping."):
            return default
        
        # Map to environment variable
        env_key = key.replace(".", "_").upper()
        value = os.environ.get(env_key, default)
        
        # Convert to int if it looks like a status code
        if value and str(value).isdigit():
            return int(value)
        return value
    
    def set(self, key: str, value): pass
    def get_section(self, section: str): return {}

# Usage with environment variables:
# export HTTP_STATUS_MAPPING_USERNOTFOUNDERROR=404
# export HTTP_STATUS_MAPPING_DATABASEERROR=503
```

## Best Practices

1. **Configure at Startup**: Set configuration before handling any exceptions
2. **Use Inheritance**: Configure parent classes to affect multiple exceptions
3. **Cache Awareness**: Clear cache when changing configuration at runtime  
4. **Monitor Usage**: Use statistics to understand mapping performance
5. **Test Configurations**: Validate that overrides work as expected
6. **Document Overrides**: Document why specific overrides were made

## Default Status Code Mappings

The system includes comprehensive default mappings:

- **400**: Validation errors, invalid requests, malformed data
- **401**: Authentication failures, invalid tokens
- **403**: Authorization failures, permission denied, inactive users
- **404**: Resource not found errors
- **409**: Conflicts, duplicate resources
- **422**: Processing errors, provisioning failures
- **429**: Rate limiting, quota exceeded
- **500**: System errors, database failures, encryption errors
- **503**: Service unavailable, external dependencies down

See `http_mapping.py` for the complete default mapping.