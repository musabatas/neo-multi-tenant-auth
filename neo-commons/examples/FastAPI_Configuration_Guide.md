# FastAPI Configuration Guide for neo-commons

This guide demonstrates how to use the neo-commons FastAPI infrastructure to create standardized FastAPI applications with minimal boilerplate code and **Scalar API documentation** by default.

## 🚀 Scalar API Documentation

Neo-commons uses [Scalar](https://github.com/scalar/scalar) as the default API documentation interface instead of traditional Swagger UI. Scalar provides:

- **Modern UI**: Beautiful, fast, and responsive design
- **Better Performance**: Faster loading and rendering than Swagger UI
- **Interactive Testing**: Built-in API testing capabilities
- **Multiple Themes**: purple, default, moon, saturn, kepler, mars, blueprint, alternate
- **Custom Styling**: CSS customization support
- **Mobile-Friendly**: Optimized for mobile devices

### Quick Scalar Setup

```bash
# Install scalar-fastapi (optional - falls back to Swagger UI if not available)
pip install scalar-fastapi
```

By default, your API will have:
- **Scalar Documentation**: `/docs` (primary)
- **Swagger UI**: `/swagger` (fallback)  
- **ReDoc**: `/redoc` (alternative)

## Quick Start

### 1. Simple Development API

```python
from neo_commons.infrastructure.fastapi import create_development_api, ServiceType

# Create a simple development API
app = create_development_api(
    service_type=ServiceType.CUSTOM,
    title="My API",
    description="Quick development setup",
    port=8000
)

@app.get("/")
async def root():
    return {"message": "Hello World!"}
```

### 2. Production-Ready API

```python
from neo_commons.infrastructure.fastapi import (
    create_production_api,
    ServiceType
)
from neo_commons.features.users.services import UserService
from neo_commons.features.cache.services import CacheService

# Initialize your services
user_service = UserService()
cache_service = CacheService()
database_service = DatabaseService()

# Create production API with full middleware stack
app = create_production_api(
    service_type=ServiceType.ADMIN_API,
    user_service=user_service,
    cache_service=cache_service,
    database_service=database_service,
    jwt_secret="your-secure-jwt-secret"
)
```

## Service-Specific APIs

### Admin API

```python
from neo_commons.infrastructure.fastapi import (
    create_admin_api,
    create_fastapi_factory,
    Environment
)

# Create factory with services
factory = create_fastapi_factory(
    user_service=user_service,
    cache_service=cache_service,
    database_service=database_service
)

# Create Admin API
app = create_admin_api(
    factory,
    config_overrides={
        "environment": Environment.PRODUCTION,
        "jwt_secret": "your-jwt-secret",
        "enable_audit_logging": True
    }
)
```

### Tenant API with Multi-tenancy

```python
from neo_commons.infrastructure.fastapi import (
    create_tenant_api,
    create_fastapi_factory
)

# Create factory with tenant service
factory = create_fastapi_factory(
    user_service=user_service,
    cache_service=cache_service,
    tenant_service=tenant_service,
    database_service=database_service
)

# Create Tenant API with multi-tenancy
app = create_tenant_api(
    factory,
    config_overrides={
        "tenant_header": "X-Tenant-ID",
        "subdomain_extraction": True,
        "enable_tenant_context": True
    }
)
```

### Deployment API

```python
from neo_commons.infrastructure.fastapi import create_deployment_api

# Create deployment API (typically internal service)
app = create_deployment_api(
    factory,
    config_overrides={
        "enable_auth": False,  # Internal service
        "enable_migration_endpoints": True
    }
)
```

## Scalar Documentation Configuration

### Basic Scalar Setup

```python
from neo_commons.infrastructure.fastapi import DocsConfig, AdminAPIConfig

# Default Scalar configuration (automatic)
config = AdminAPIConfig()  # Scalar enabled by default

# Custom Scalar configuration
custom_docs = DocsConfig(
    title="My API",
    description="API with custom Scalar docs",
    use_scalar=True,  # Enable Scalar (default: True)
    docs_url="/docs",  # Scalar endpoint
    swagger_url="/swagger",  # Swagger UI fallback
    scalar_config={
        "theme": "purple",  # purple, default, moon, saturn, etc.
        "layout": "modern",
        "show_sidebar": True,
        "hide_download_button": False,
        "hide_test_request_button": False,
        "custom_css": """
            .scalar-api-reference {
                --scalar-color-1: #2a2f45;
                --scalar-radius: 8px;
            }
        """
    }
)

config = AdminAPIConfig(docs_config=custom_docs)
```

### Available Scalar Themes

```python
scalar_themes = [
    "purple",      # Default neo-commons theme
    "default",     # Scalar default
    "moon",        # Dark theme
    "saturn",      # Space theme
    "kepler",      # Scientific theme
    "mars",        # Red theme
    "blueprint",   # Technical theme
    "alternate",   # Alternative styling
    "none"         # No theme (custom CSS only)
]

# Apply theme
config.docs_config.scalar_config["theme"] = "moon"
```

### Environment-Specific Scalar Configuration

```python
# Development: Full-featured Scalar
dev_config = DocsConfig.from_environment(Environment.DEVELOPMENT, ServiceType.ADMIN_API)
# Automatically enables Scalar with purple theme and all features

# Staging: Limited Scalar
staging_config = DocsConfig.from_environment(Environment.STAGING, ServiceType.ADMIN_API)  
# Enables Scalar with default theme and limited features

# Production: No documentation (security)
prod_config = DocsConfig.from_environment(Environment.PRODUCTION, ServiceType.ADMIN_API)
# Automatically disables all documentation
```

### Scalar Server Configuration

```python
config.docs_config.scalar_config.update({
    "servers": [
        {"url": "https://api.production.com", "description": "Production"},
        {"url": "https://api.staging.com", "description": "Staging"},
        {"url": "http://localhost:8000", "description": "Local Development"}
    ]
})
```

### Disable Scalar (Use Swagger UI)

```python
# Disable Scalar, use traditional Swagger UI
config = AdminAPIConfig(
    docs_config=DocsConfig(
        use_scalar=False,
        docs_url="/docs"  # Will use Swagger UI
    )
)
```

## Custom Configuration

### Manual Configuration

```python
from neo_commons.infrastructure.fastapi import (
    FastAPIFactory,
    AdminAPIConfig,
    Environment,
    CORSConfig,
    SecurityConfig
)

# Create custom configuration
config = AdminAPIConfig(
    title="Custom API",
    environment=Environment.STAGING,
    port=8080,
    enable_auth=True,
    cors_config=CORSConfig(
        allow_origins=["https://yourdomain.com"],
        allow_credentials=True
    ),
    security_config=SecurityConfig(
        rate_limit="500/minute",
        enable_https_redirect=True
    )
)

# Create factory and app
factory = FastAPIFactory(user_service=user_service)
app = factory.create_app(config)
```

### Environment-Based Configuration

```python
from neo_commons.infrastructure.fastapi import FastAPIConfig, ServiceType

# Automatically configures based on ENVIRONMENT variable
config = FastAPIConfig.from_environment(
    ServiceType.ADMIN_API,
    custom_option="value"
)
```

## Dependency Injection

### Basic Service Dependencies

```python
from fastapi import Depends
from neo_commons.infrastructure.fastapi import (
    create_user_service_dependency,
    create_cache_service_dependency,
    setup_service_dependencies
)

# Setup services for dependency injection
setup_service_dependencies(
    user_service=user_service,
    cache_service=cache_service
)

# Use in routes
get_user_service = create_user_service_dependency()
get_cache_service = create_cache_service_dependency()

@app.get("/users")
async def list_users(
    user_service: UserService = Depends(get_user_service)
):
    return await user_service.list_users()
```

### Optional Dependencies

```python
from neo_commons.infrastructure.fastapi import (
    create_optional_cache_service_dependency
)

get_optional_cache = create_optional_cache_service_dependency()

@app.get("/data")
async def get_data(
    cache_service: Optional[CacheService] = Depends(get_optional_cache)
):
    if cache_service:
        return await cache_service.get("data")
    return {"data": "from database"}
```

### Application Configuration Access

```python
from neo_commons.infrastructure.fastapi import get_app_config

@app.get("/config")
async def get_config(config = Depends(get_app_config)):
    return {
        "service_type": config.service_type.value,
        "environment": config.environment.value,
        "debug": config.debug
    }
```

## Middleware Configuration

### Automatic Middleware

The factory automatically configures middleware based on service type:

- **Admin API**: Platform-level auth, audit logging, security headers
- **Tenant API**: Multi-tenant context, tenant-based rate limiting
- **Deployment API**: Minimal middleware, IP-based rate limiting

### Custom Middleware Setup

```python
from neo_commons.infrastructure.fastapi import (
    FastAPIFactory,
    setup_minimal_middleware,
    setup_api_only_middleware
)

factory = FastAPIFactory()
app = factory.create_app(config)

# Setup minimal middleware for development
setup_minimal_middleware(app, config, factory._middleware_factory)

# Or API-only middleware
setup_api_only_middleware(
    app, 
    config, 
    factory._middleware_factory,
    require_auth=True
)
```

## Health Checks

### Built-in Health Endpoints

Every FastAPI app gets these endpoints automatically:

- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check with service dependencies
- `GET /health/live` - Liveness check

### Custom Health Checks

```python
from neo_commons.infrastructure.fastapi import get_health_status

@app.get("/health/detailed")
async def detailed_health(
    health_status = Depends(get_health_status)
):
    return health_status
```

## Application Lifecycle

### Startup and Shutdown Handlers

```python
from neo_commons.infrastructure.fastapi import (
    create_startup_handler,
    create_shutdown_handler
)
from contextlib import asynccontextmanager

# Define tasks
async def initialize_services():
    await database_service.initialize()

async def cleanup_services():
    await database_service.cleanup()

# Create handlers
startup = create_startup_handler(initialize_services)
shutdown = create_shutdown_handler(cleanup_services)

# Create lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()

# Use with factory
app = factory.create_app(config, lifespan=lifespan)
```

## Testing

### Test Setup with Mocks

```python
from unittest.mock import AsyncMock
from neo_commons.infrastructure.fastapi import (
    create_development_api,
    create_user_service_dependency,
    clear_dependencies
)

# Create mock services
mock_user_service = AsyncMock(spec=UserService)
mock_user_service.list_users.return_value = []

# Create test app
app = create_development_api(
    service_type=ServiceType.CUSTOM,
    title="Test API"
)

# Override dependencies
app.dependency_overrides[create_user_service_dependency()] = lambda: mock_user_service

# Clean up after tests
def teardown():
    clear_dependencies()
    app.dependency_overrides.clear()
```

## Scalar Installation & Requirements

### Installation

```bash
# Install scalar-fastapi for Scalar documentation
pip install scalar-fastapi

# Or add to your requirements.txt
echo "scalar-fastapi" >> requirements.txt
pip install -r requirements.txt
```

### Automatic Fallback

If `scalar-fastapi` is not installed, neo-commons automatically falls back to traditional Swagger UI:

```python
# This works whether scalar-fastapi is installed or not
app = create_development_api(
    service_type=ServiceType.CUSTOM,
    title="My API"
)
# - With scalar-fastapi: /docs shows Scalar, /swagger shows Swagger UI
# - Without scalar-fastapi: /docs shows Swagger UI
```

### Checking Scalar Availability

```python
from neo_commons.infrastructure.fastapi.factory import SCALAR_AVAILABLE

if SCALAR_AVAILABLE:
    print("Scalar documentation is available")
else:
    print("Using Swagger UI fallback")
```

## Environment Variables

The configuration system reads these environment variables:

### Basic Configuration
- `ENVIRONMENT` - development, staging, production, testing
- `DEBUG` - true/false
- `HOST` - Host to bind to (default: 0.0.0.0)
- `PORT` - Port to bind to (service-specific defaults)
- `WORKERS` - Number of worker processes

### Database and Cache
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### Authentication
- `JWT_SECRET` - JWT signing secret (required in production)
- `JWT_ALGORITHM` - JWT algorithm (default: RS256)

### Service-Specific Ports
- `ADMIN_API_PORT` - Admin API port (default: 8001)
- `TENANT_API_PORT` - Tenant API port (default: 8002)
- `DEPLOYMENT_API_PORT` - Deployment API port (default: 8000)

### Security
- `RATE_LIMIT` - Rate limit per minute (default: 1000/minute)
- `BURST_RATE_LIMIT` - Burst rate limit (default: 50/second)
- `MAX_REQUEST_SIZE` - Maximum request size in bytes
- `TRUSTED_PROXIES` - Comma-separated list of trusted proxy IPs

### CORS
- `CORS_ORIGIN_REGEX` - Regex pattern for allowed origins
- `ADMIN_FRONTEND_URL` - Admin frontend URL
- `TENANT_FRONTEND_URL` - Tenant frontend URL
- `MARKETING_URL` - Marketing site URL

## Best Practices

### 1. Use Service-Specific Factories

```python
# Good: Use specific factory functions
app = create_admin_api(factory, config_overrides={})

# Avoid: Manual configuration for standard services
config = FastAPIConfig(...)  # Too much boilerplate
```

### 2. Environment-Based Configuration

```python
# Good: Let environment determine configuration
config = AdminAPIConfig.from_environment(ServiceType.ADMIN_API)

# Good: Override specific values
config = AdminAPIConfig.from_environment(
    ServiceType.ADMIN_API,
    jwt_secret="custom-secret"
)
```

### 3. Proper Service Initialization

```python
# Good: Initialize services with proper configuration
user_service = UserService(database_url=config.database_url)
cache_service = CacheService(redis_url=config.redis_url)

# Good: Use factory pattern
factory = create_fastapi_factory(
    user_service=user_service,
    cache_service=cache_service
)
```

### 4. Testing with Mocks

```python
# Good: Use dependency overrides for testing
app.dependency_overrides[get_user_service] = lambda: mock_user_service

# Good: Clear overrides after tests
def cleanup():
    app.dependency_overrides.clear()
    clear_dependencies()
```

### 5. Production Security

```python
# Good: Enable all security features in production
if config.environment == Environment.PRODUCTION:
    assert config.jwt_secret, "JWT secret required in production"
    assert config.database_url, "Database URL required in production"
    assert not config.debug, "Debug must be disabled in production"
```

## Error Handling

The FastAPI configuration includes automatic error handling:

- **Authentication errors**: 401 Unauthorized
- **Authorization errors**: 403 Forbidden  
- **Validation errors**: 422 Unprocessable Entity
- **Rate limiting**: 429 Too Many Requests
- **Server errors**: 500 Internal Server Error

### Custom Error Handlers

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "service": "my-api",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    )
```

## Migration from Existing FastAPI Apps

### Step 1: Install neo-commons

```bash
pip install neo-commons
```

### Step 2: Replace FastAPI Creation

```python
# Before
from fastapi import FastAPI
app = FastAPI(title="My API")

# After
from neo_commons.infrastructure.fastapi import create_development_api, ServiceType
app = create_development_api(
    service_type=ServiceType.CUSTOM,
    title="My API"
)
```

### Step 3: Move Middleware to Configuration

```python
# Before
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# After
# CORS is handled automatically by the configuration
```

### Step 4: Use Dependency Injection

```python
# Before
user_service = UserService()  # Global instance

@app.get("/users")
async def get_users():
    return await user_service.list_users()

# After
from neo_commons.infrastructure.fastapi import create_user_service_dependency

setup_service_dependencies(user_service=UserService())
get_user_service = create_user_service_dependency()

@app.get("/users")
async def get_users(user_service = Depends(get_user_service)):
    return await user_service.list_users()
```

## Troubleshooting

### Common Issues

1. **JWT Secret Missing**
   ```
   ValueError: JWT_SECRET must be set in production
   ```
   Set the `JWT_SECRET` environment variable or pass it in config overrides.

2. **Service Not Registered**
   ```
   RuntimeError: UserService not registered
   ```
   Call `setup_service_dependencies()` or register the service manually.

3. **Middleware Order Issues**
   ```
   RuntimeError: CORS middleware must be the last middleware
   ```
   Let the factory handle middleware order automatically.

4. **Database Connection Failed**
   ```
   Connection refused: localhost:5432
   ```
   Ensure database is running and `DATABASE_URL` is correct.

5. **Scalar Not Working**
   ```
   ModuleNotFoundError: No module named 'scalar_fastapi'
   ```
   Install scalar-fastapi: `pip install scalar-fastapi`

6. **Scalar Falls Back to Swagger**
   ```
   WARNING: Failed to setup Scalar documentation
   ```
   Check that scalar-fastapi is installed and `use_scalar=True` in config.

7. **Documentation Not Appearing**
   ```
   404 Not Found at /docs
   ```
   Check that you're not in production environment (docs disabled by default).

### Debug Mode

Enable debug mode to see detailed configuration:

```python
config = FastAPIConfig(debug=True)
# Logs will show middleware configuration, service registration, etc.
```

## Examples

See `examples/fastapi_usage_examples.py` for complete working examples of:

- Development API setup
- Production API with full middleware
- Multi-tenant API configuration  
- Custom configuration examples
- Testing with mocks
- Lifecycle management
- Environment-specific configurations

Run the examples:

```bash
cd neo-commons/examples
python fastapi_usage_examples.py
```