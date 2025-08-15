# CLAUDE.md - NeoAdminApi

This file provides guidance to Claude Code (claude.ai/code) when working with the NeoAdminApi codebase.

## Project Overview

**NeoAdminApi** is the platform administration API service for the NeoMultiTenant platform. It manages global platform operations including tenant provisioning, user management, billing, monitoring, and multi-region orchestration.

### Key Architecture Principles

- **No ORM**: Direct asyncpg usage for maximum performance
- **Feature-Based Structure**: Cohesive feature modules with clear boundaries
- **Cache-First**: Redis caching with automatic invalidation
- **Async Everything**: Full async/await pattern throughout
- **Type Safety**: Pydantic models for validation and serialization
- **Two-Level Architecture**: Platform level (admin DB) vs Tenant level (regional DBs)
- **python-keycloak Integration**: Using official async library for all Keycloak operations

## Current Status

### ✅ Completed Components

1. **Core Infrastructure** (`src/common/`)
   - Database connection management with asyncpg
   - Redis cache client with health checks
   - Base models and API response structures
   - Global exception handling
   - Settings management with environment variables

2. **Authentication Foundation** (`src/features/auth/`)
   - python-keycloak library integration (>=5.7.0)
   - KeycloakClient with async methods (a_token, a_introspect, etc.)
   - TokenManager with dual validation (introspection + local JWT)
   - RealmManager for multi-tenant realm support
   - Two-level permission system (Platform vs Tenant)

3. **API Documentation**
   - Scalar at `/docs` (primary)
   - Swagger at `/swagger` (alternative)
   - ReDoc at `/redoc` (clean format)

4. **Docker Configuration**
   - Multi-stage Dockerfile for optimization
   - Docker Compose for development
   - Health check endpoints

### 🚧 In Progress

- Authentication implementation with python-keycloak
- Platform user management with tenant-scoped permissions
- API routers and endpoints
- Test structure setup

### 📋 Pending

- Organization management
- Tenant provisioning system
- Billing and subscription features
- Regional database routing
- Monitoring and alerts
- Migration management

## Development Commands

### Running the API

```bash
# Always use virtual environment
source .venv/bin/activate

# Run the API
python -m src.main

# Or use the helper script
./run.dev.sh

# Run with specific environment
ENVIRONMENT=development python -m src.main
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific feature tests
pytest tests/features/auth/
```

### Database Operations

```bash
# IMPORTANT: Only admin database in .env
# Connection string is in .env: ADMIN_DATABASE_URL
# Regional databases are in admin.database_connections table

# Check database health
curl http://localhost:8001/health

# Query regional database (through RegionalDatabaseManager)
# This uses dynamic routing from admin.database_connections
```

## Code Architecture

### Project Structure
```
NeoAdminApi/
├── src/
│   ├── features/                    # Feature-specific modules
│   │   ├── auth/                    # Authentication module
│   │   ├── users/                   # User management module
│   │   ├── organizations/           # Organization management module
│   │   ├── tenants/                 # Tenant management module
│   │   ├── billing/                 # Billing and subscription module
│   │   ├── regions/                 # Regional database management module
│   ├── common/                      # Shared components
│   │   ├── database/                # Database utilities
│   │   │   ├── connection.py        # Connection management
│   │   │   ├── transaction.py       # Transaction handling
│   │   │   └── migrations.py        # Migration helpers
│   │   ├── cache/                   # Cache utilities
│   │   │   ├── client.py            # Redis client
│   │   │   ├── decorators.py        # Cache decorators
│   │   │   └── keys.py              # Key generation
│   │   ├── exceptions/              # Global exceptions
│   │   │   ├── base.py
│   │   │   ├── http.py
│   │   │   └── domain.py
│   │   ├── models/                  # Shared models
│   │   │   ├── base.py              # Base model classes
│   │   │   ├── responses.py         # API response models
│   │   │   └── pagination.py        # Pagination models
│   │   ├── middleware/              # Global middleware
│   │   │   ├── auth.py              # Auth middleware
│   │   │   ├── logging.py           # Request logging
│   │   │   ├── cors.py              # CORS handling
│   │   │   └── errors.py            # Error handling
│   │   ├── utils/                   # Utilities
│   │   │   ├── datetime.py
│   │   │   ├── validators.py
│   │   │   └── crypto.py
│   │   └── config/                  # Configuration
│   │       ├── settings.py          # App settings
│   │       ├── database.py          # DB config
│   │       ├── cache.py             # Cache config
│   │       └── auth.py              # Auth config
│   │
│   ├── integrations/                # External integrations
│   │   ├── keycloak/                # Keycloak client (python-keycloak)
│   │   │   ├── client.py            # KeycloakClient with async methods
│   │   │   ├── token_manager.py     # TokenManager with introspection
│   │   │   └── realm_manager.py     # RealmManager for multi-tenancy
│   │   ├── payment_gateways/        # Payment providers
│   │   │   ├── stripe/
│   │   │   └── paddle/
│   │   └── notification_services/   # Notification providers
│   │       ├── email/
│   │       └── sms/
│   │
│   ├── app.py                       # FastAPI app factory
│   └── main.py                      # Application entry point
│
├── tests/
│   ├── features/                    # Feature-specific tests
│   │   ├── auth/
│   │   ├── users/
│   │   ├── organizations/
│   │   ├── tenants/
│   │   ├── billing/
│   │   ├── regions/
│   │   ├── monitoring/
│   │   ├── migrations/
│   │   └── security/
│   ├── integration/                 # Integration tests
│   ├── e2e/                        # End-to-end tests
│   └── fixtures/                   # Test fixtures
│
├── scripts/                        # Utility scripts
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Feature Module Pattern

Each feature follows this structure:

```
src/features/[feature_name]/
├── models/              # Pydantic models
│   ├── request.py      # API request schemas
│   ├── response.py     # API response schemas
│   └── domain.py       # Business domain models
├── repositories/        # Data access layer
│   └── [feature]_repository.py
├── services/           # Business logic
│   └── [feature]_service.py
├── routers/            # API endpoints
│   └── v1.py
├── cache/              # Caching strategies
│   ├── strategies.py
│   └── keys.py
├── exceptions.py       # Feature-specific exceptions
└── dependencies.py     # Dependency injection
```

### Database Access Pattern

Always use asyncpg directly through the DatabaseManager:

```python
from src.common.database.connection import get_database

async def get_user(user_id: str):
    db = get_database()
    query = """
        SELECT * FROM admin.platform_users 
        WHERE id = $1 AND is_active = true
    """
    return await db.fetchrow(query, user_id)
```

### Caching Pattern

Use Redis for frequently accessed data:

```python
from src.common.cache.client import get_cache

async def get_cached_permissions(user_id: str):
    cache = get_cache()
    key = f"permissions:{user_id}"
    
    # Try cache first
    cached = await cache.get(key)
    if cached:
        return cached
    
    # Load from database
    permissions = await load_permissions(user_id)
    
    # Cache with TTL
    await cache.set(key, permissions, ttl=600)
    return permissions
```

### Error Handling Pattern

Use custom exceptions for clear error reporting:

```python
from src.common.exceptions.base import NeoAdminException

class TenantNotFoundException(NeoAdminException):
    def __init__(self, tenant_id: str):
        super().__init__(
            status_code=404,
            error_code="TENANT_NOT_FOUND",
            message=f"Tenant {tenant_id} not found"
        )
```

## API Conventions

### Endpoint Structure

```python
# Standard CRUD pattern
GET    /api/v1/{resource}          # List with pagination
POST   /api/v1/{resource}          # Create new
GET    /api/v1/{resource}/{id}     # Get by ID
PUT    /api/v1/{resource}/{id}     # Update
DELETE /api/v1/{resource}/{id}     # Delete

# Actions on resources
POST   /api/v1/{resource}/{id}/{action}  # Perform action
```

### Response Format

All responses use the standardized APIResponse model:

```python
{
    "success": true,
    "data": {...},
    "message": "Operation successful",
    "errors": [],
    "metadata": {
        "timestamp": "2024-01-01T00:00:00Z",
        "request_id": "uuid"
    }
}
```

### Pagination

```python
{
    "data": {
        "items": [...],
        "pagination": {
            "page": 1,
            "page_size": 20,
            "total_pages": 5,
            "total_items": 100,
            "has_next": true,
            "has_previous": false
        }
    }
}
```

### Guest Authentication for Public Endpoints

The API supports guest authentication for public reference data endpoints (currencies, countries, languages). This provides:

- **Session Tracking**: Automatic session creation for unauthenticated users
- **Rate Limiting**: Per-session and per-IP rate limits to prevent abuse
- **Usage Analytics**: Track anonymous usage patterns without requiring authentication
- **Seamless Experience**: Works for both authenticated and unauthenticated users

#### Guest Authentication Flow

1. **Automatic Session Creation**: First request to reference data endpoints creates a guest session
2. **Session Token Return**: New session token returned in response headers or session endpoint
3. **Subsequent Requests**: Include session token via `Authorization` header or `X-Guest-Session` header
4. **Rate Limiting**: 1000 requests per session, 5000 requests per IP per day

#### Usage Examples

**Create Guest Session (Automatic)**:
```bash
# First request automatically creates guest session
curl http://localhost:8001/currencies
# Response includes new_session_token in data
```

**Use Guest Session Token**:
```bash
# Include session token in subsequent requests
curl -H "X-Guest-Session: guest_abc123:token456" http://localhost:8001/countries

# Or use Authorization header
curl -H "Authorization: Bearer guest_abc123:token456" http://localhost:8001/languages
```

**Check Session Information**:
```bash
curl -H "X-Guest-Session: guest_abc123:token456" http://localhost:8001/session
```

#### Guest Session Data Structure

```json
{
  "session_id": "guest_abc123",
  "user_type": "guest",
  "permissions": ["reference_data:read"],
  "rate_limit": {
    "requests_remaining": 999,
    "reset_time": "2024-01-01T13:00:00Z"
  },
  "request_count": 1,
  "created_at": "2024-01-01T12:00:00Z",
  "expires_at": "2024-01-01T13:00:00Z"
}
```

#### Implementation Pattern for Other Public Endpoints

To add guest authentication to other endpoints:

1. **Import Guest Dependencies**:
```python
from src.features.auth.dependencies.guest_auth import get_reference_data_access
```

2. **Replace Authentication Dependency**:
```python
# Before: Required authentication
@require_permission("resource:read", scope="platform")
async def get_resource(
    current_user: dict = Depends(CheckPermission(["resource:read"]))
):
    pass

# After: Guest or authenticated access
async def get_resource(
    current_user: dict = Depends(get_reference_data_access)
):
    # current_user["user_type"] will be "guest" or "authenticated"
    pass
```

3. **Handle Session Information**:
```python
# Check user type in endpoint
if current_user.get("user_type") == "guest":
    # Handle guest user (limited functionality)
    logger.info(f"Guest session {current_user['session_id']} accessed resource")
else:
    # Handle authenticated user (full functionality)
    logger.info(f"User {current_user['id']} accessed resource")
```

#### Rate Limiting Configuration

Guest authentication includes built-in rate limiting:

- **Session Limits**: 1000 requests per 1-hour session
- **IP Limits**: 5000 requests per IP per 24 hours
- **Error Responses**: HTTP 429 with Retry-After header

#### Security Considerations

- **No Sensitive Data**: Guest sessions only access public reference data
- **Session Expiry**: 1-hour session timeout with automatic cleanup
- **IP Tracking**: Rate limiting prevents abuse from single IP addresses
- **No Persistence**: Guest sessions are cache-only (Redis) with automatic expiration

### OpenAPI Documentation & Nested Tags

The API uses a nested tag system for better organization in Scalar documentation. Tags are organized into groups that create collapsible sections in the API docs.

#### Adding New Feature Tags

When creating new features, ensure the tag groups are updated in `src/common/openapi_config.py`:

1. **Add your feature tags** to the appropriate tag group in the `get_tag_groups()` function
2. **Use consistent tag naming**: 
   - Group name: Descriptive group name (e.g., `"Reference Data"`)
   - Tags: Simple, clear names (e.g., `"Currencies"`, `"Countries"`, `"Languages"`)

Example tag group configuration:
```python
{
    "name": "Reference Data",
    "tags": ["Currencies", "Countries", "Languages"]
}
```

#### Router Tag Patterns

**Single Feature Router** (most features):
```python
router = NeoAPIRouter(tags=["Feature Name"])
```

**Multi-Router Feature** (complex features like regions, reference_data):
```python
# Main router (no tags to avoid duplication)
router = NeoAPIRouter()

# Sub-routers with specific tags and prefixes
currency_router = NeoAPIRouter(prefix="/currencies", tags=["Currencies"])
country_router = NeoAPIRouter(prefix="/countries", tags=["Countries"])

# Include sub-routers in main router
router.include_router(currency_router)
router.include_router(country_router)
```

**⚠️ Important**: 
- If using multiple sub-routers, don't add tags to the main router to avoid duplicate tag assignments
- Use empty tags `[]` in the app router registration to prevent default tag assignment
- Only sub-routers should have tags when using tag groups

**App Router Registration** (in `src/app.py`):
```python
"reference_data": {
    "reference_data": (reference_data_router, "", [])  # Empty tags!
}
```

#### Current Tag Groups

- **Authentication & Authorization**: `["Authentication", "Permissions", "Roles"]`
- **User Management**: `["Platform Users", "User Profile", "User Settings"]`
- **Organization Management**: `["Organizations", "Organization Settings", "Organization Members"]`
- **Tenant Management**: `["Tenants", "Tenant Settings", "Tenant Users"]`
- **Infrastructure**: `["Regions", "Database Connections", "Health"]`
- **Reference Data**: `["Currencies", "Countries", "Languages"]`
- **💳 Billing & Subscriptions**: `["Billing", "Subscriptions", "Invoices", "Payment Methods"]`
- **📊 Analytics & Reports**: `["Analytics", "Reports", "Metrics"]`
- **System**: `["Health", "Configuration", "Migrations", "Monitoring"]`
- **Debug**: `["Debug", "Test", "Root"]`

## Security Considerations

1. **Token Validation**: Use python-keycloak's async methods
   - Introspection for accuracy (checks revocation)
   - Local JWT validation for performance
2. **Two-Level Permission Checking**:
   - Platform: PlatformPermissionChecker for tenant-scoped permissions
   - Tenant: TenantPermissionChecker for team-scoped permissions
3. **Validate tenant isolation** - users should only access their tenant's data
4. **Use parameterized queries** to prevent SQL injection
5. **Mask sensitive data** in logs (passwords, tokens, PII)
6. **Rate limit** API endpoints to prevent abuse
7. **Cache Namespace Separation**: Prevent cross-tenant data leakage

## Performance Guidelines

1. **Use connection pooling** - already configured in DatabaseManager
2. **Batch database operations** when processing multiple items
3. **Cache aggressively** but invalidate properly
4. **Use indexes** - check EXPLAIN ANALYZE for slow queries
5. **Paginate large result sets** - default 20, max 100 items
6. **Async all the way** - never use blocking I/O operations

## Development Tools

### Serena MCP Integration
This project is configured to work with the Serena MCP server for enhanced code navigation and semantic analysis. Serena provides powerful tools for understanding and modifying the codebase efficiently.

## Testing Requirements

### Test Coverage Goals
- Unit tests: 80% minimum
- Integration tests: All API endpoints
- E2E tests: Critical workflows (tenant provisioning, billing)

### Test Patterns

```python
# Repository tests - mock database
async def test_user_repository_get_user(mock_db):
    mock_db.fetchrow.return_value = {"id": "123", "email": "test@example.com"}
    repo = UserRepository(mock_db)
    user = await repo.get_user("123")
    assert user.id == "123"

# Service tests - mock repositories
async def test_user_service_create_user(mock_repo):
    service = UserService(mock_repo)
    user = await service.create_user(...)
    mock_repo.create.assert_called_once()

# API tests - use test client
async def test_create_user_endpoint(client, auth_headers):
    response = await client.post("/api/v1/users", 
                                  json=user_data,
                                  headers=auth_headers)
    assert response.status_code == 201
```

## Common Issues and Solutions

### Issue: ModuleNotFoundError for scalar_fastapi
**Solution**: Ensure virtual environment is activated: `source .venv/bin/activate`

### Issue: Database connection fails
**Solution**: 
1. Check PostgreSQL is running on port 5432
2. Verify database `neofast_admin` exists
3. Check credentials in `.env` file

### Issue: Redis connection fails
**Solution**:
1. Check Redis is running on port 6379
2. Ensure no password is set (for development)
3. Verify `REDIS_URL` in `.env`

### Issue: Port 8001 already in use
**Solution**: `kill $(lsof -t -i:8001)` or change PORT in `.env`

## Critical Implementation Notes

### 🔴 Two-Level Authentication Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PLATFORM LEVEL                            │
│                  (Admin Database)                            │
├─────────────────────────────────────────────────────────────┤
│  • platform_users table (Global administrators)              │
│  • Composite Keys: (user_id, role_id, tenant_id)            │
│  • Tenant-scoped permissions (which tenants can user manage) │
│  • Cache namespace: 'platform:*'                             │
│  • Keycloak realm: Platform admin realm (e.g., neo-admin)    │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                     TENANT LEVEL                             │
│               (Regional Databases)                           │
├─────────────────────────────────────────────────────────────┤
│  • tenant_template.users table (Tenant-specific users)       │
│  • Composite Keys: (user_id, role_id, team_id)              │
│  • Team-scoped permissions (which teams can user work in)    │
│  • Cache namespace: 'tenant:{tenant_id}:*'                   │
│  • Keycloak realm: Individual tenant realms (stored in DB)   │
└─────────────────────────────────────────────────────────────┘
```

### 🔴 Database Connection Strategy
- **Admin Database ONLY**: Connection string in environment variables
- **ALL Other Databases**: Managed via `admin.database_connections` table
- **Dynamic Routing**: No service restart needed for new connections
- **Regional Databases**: Use RegionalDatabaseManager for routing

### 🔴 Keycloak Realm Management (NO PATTERN ASSUMPTION)
- **Storage**: Actual realm names stored in `tenants.external_auth_realm` column
- **Flexibility**: Each tenant can have ANY realm name
- **DO NOT**: Assume "tenant-{slug}" pattern - this is WRONG
- **ALWAYS**: Read realm name from database column

### 🔴 Enum Type Awareness
Be careful with enum types - they exist in different schemas:
- **admin.auth_provider**: Platform-level auth providers
- **admin.permission_scope_level**: ('platform', 'tenant', 'user') - Platform permissions
- **admin.platform_role_level**: Platform-wide role levels
- **platform_common.auth_provider**: Shared auth provider types
- **platform_common.permission_scopes**: ('tenant', 'team', 'user') - Tenant permissions
- **platform_common.user_role_level**: ('owner', 'admin', 'manager', 'member', 'viewer', 'guest')

### Multi-Region Database Routing
The RegionalDatabaseManager handles connections to regional databases:
```python
async def execute_in_tenant_schema(
    self, region_id: str, schema_name: str, query: str, *args
):
    async with self.get_connection(region_id) as conn:
        await conn.execute(f"SET search_path TO {schema_name}, platform_common")
        return await conn.fetch(query, *args)
```

### Tenant Provisioning Workflow
1. Validate organization and subscription
2. Select optimal region based on requirements
3. Create Keycloak realm with CUSTOM name (store in external_auth_realm)
4. Create database schema in REGIONAL database (not admin)
5. Set up initial permissions and quotas
6. Send provisioning notifications

### Permission Caching Strategy
- **Platform Level**: Cache with 'platform:' prefix
  - Key pattern: `platform:perms:user:{user_id}:tenant:{tenant_id}`
  - TTL: 10 minutes
- **Tenant Level**: Cache with 'tenant:' prefix  
  - Key pattern: `tenant:{tenant_id}:perms:user:{user_id}:team:{team_id}`
  - TTL: 10 minutes
- **CRITICAL**: Never mix platform and tenant cache keys
- Invalidate on role changes
- Use hierarchical cache keys for bulk invalidation
- Warm cache on login for better performance

### Subscription State Machine
- TRIAL → ACTIVE → SUSPENDED → CANCELLED
- TRIAL → ACTIVE → PAST_DUE → ACTIVE
- Automated transitions based on payment status
- Webhook handlers for payment gateway events

## Architectural Principles & Common Patterns

### DRY (Don't Repeat Yourself) Implementation

**Core Philosophy**: Every piece of knowledge should have a single, unambiguous representation in the system.

#### Base Repository Pattern
All data access should extend `BaseRepository` for consistent patterns:

```python
from src.common.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(table_name="platform_users", schema="admin")
    
    # Leverage inherited methods:
    # - paginated_list()
    # - build_where_clause() 
    # - count_with_filters()
    # - get_by_id()
```

**Benefits**:
- Consistent pagination across all features
- Standardized WHERE clause building
- Automatic soft delete handling
- Reduced code duplication by ~40%

#### Base Service Pattern
All business logic should extend `BaseService` for consistent error handling:

```python
from src.common.services.base import BaseService

class UserService(BaseService[User]):
    def __init__(self):
        super().__init__()
        self.repository = UserRepository()
    
    # Use inherited methods:
    # - create_pagination_metadata()
    # - handle_not_found() 
    # - handle_validation_error()
    # - validate_pagination_params()
```

**Benefits**:
- Standardized error handling
- Consistent pagination metadata
- Validation helpers
- Unified exception patterns

#### Database Utilities
Common database operations centralized in utilities:

```python
from src.common.database.utils import process_database_record

# Automatically handles UUID → string and JSONB → dict conversion
processed_data = process_database_record(
    raw_record,
    uuid_fields=['id', 'region_id'],
    jsonb_fields=['metadata', 'settings']
)
domain_model = MyModel(**processed_data)
```

#### DateTime Utilities
Consistent datetime handling across the application:

```python
from src.common.utils.datetime import format_iso8601, utc_now

# Always use timezone-aware UTC
created_at = utc_now()

# Consistent ISO format in responses
formatted_time = format_iso8601(created_at)  # "2024-01-01T12:00:00+00:00"
```

### SOLID Principles Enforcement

#### Single Responsibility Principle
- **Repositories**: Only handle data access
- **Services**: Only handle business logic  
- **Controllers**: Only handle HTTP concerns
- **Models**: Only define data structure

#### Open/Closed Principle
- Base classes extensible via inheritance
- Plugin architecture for external integrations
- Strategy pattern for different implementations

#### Liskov Substitution Principle
- All repositories interchangeable via BaseRepository
- All services follow same interface patterns
- Type hints ensure compatibility

#### Interface Segregation
- Separate read/write repository interfaces
- Minimal service interfaces per feature
- Optional dependencies via dependency injection

#### Dependency Inversion
- Depend on abstractions (base classes)
- Inject dependencies via constructors
- Use dependency injection for testing

### Common Error Handling Patterns

#### Standardized Exceptions
Use specific exception types for different error scenarios:

```python
from src.common.exceptions.base import (
    NotFoundError, ValidationError, ConflictError
)

# Resource not found
raise NotFoundError(resource="User", identifier=user_id)

# Validation failures  
raise ValidationError(
    message="Invalid email format",
    errors=[{"field": "email", "value": email, "requirement": "Valid email"}]
)

# Resource conflicts
raise ConflictError(
    message="Email already exists",
    conflicting_field="email",
    conflicting_value=email
)
```

#### Error Response Format
All API errors follow consistent format:
```json
{
  "detail": "User with id '123' not found",
  "error": "NotFoundError", 
  "details": {
    "resource": "User",
    "identifier": "123"
  }
}
```

### Performance Optimization Patterns

#### Query Optimization
- **Pagination**: Always use LIMIT/OFFSET with COUNT
- **Joins**: Prefer single query with joins over N+1
- **Indexes**: Verify with EXPLAIN ANALYZE
- **Batching**: Use executemany() for bulk operations

#### Caching Strategy
```python
# Namespace separation prevents collisions
CACHE_KEYS = {
    'user': 'user:{user_id}',
    'permissions': 'perms:user:{user_id}:tenant:{tenant_id}',
    'tenant_data': 'tenant:{tenant_id}:data:{data_type}'
}

# TTL based on data volatility
TTL_CONFIG = {
    'static_data': 3600,      # 1 hour
    'permissions': 600,       # 10 minutes  
    'dynamic_data': 300       # 5 minutes
}
```

#### Database Connection Management
- Use connection pooling (configured in DatabaseManager)
- Prefer single connections over multiple round trips
- Use transactions for multi-step operations
- Monitor connection health automatically

### Security Patterns

#### Input Validation
```python
# Always validate at API boundary
@router.post("/users")
async def create_user(user_data: UserCreateRequest):
    # Pydantic automatically validates
    validated_data = user_data.model_dump()
```

#### Password Security
```python
from src.common.utils.encryption import encrypt_password, decrypt_password

# Never store plaintext passwords
encrypted = encrypt_password(plaintext_password)

# Only decrypt when absolutely necessary (e.g., health checks)
if is_encrypted(stored_password):
    plaintext = decrypt_password(stored_password)
```

#### SQL Injection Prevention
```python
# Always use parameterized queries
query = "SELECT * FROM users WHERE email = $1 AND active = $2"
result = await db.fetchrow(query, email, True)

# Never concatenate user input
# BAD: f"SELECT * FROM users WHERE email = '{email}'"
```

### Testing Patterns

#### Repository Testing
```python
async def test_user_repository_get_user(mock_db):
    mock_db.fetchrow.return_value = {"id": "123", "email": "test@example.com"}
    
    repo = UserRepository()
    repo.db = mock_db  # Inject mock
    
    user = await repo.get_by_id("123") 
    assert user.id == "123"
```

#### Service Testing  
```python
async def test_user_service_create_user(mock_repo):
    service = UserService()
    service.repository = mock_repo  # Inject mock
    
    result = await service.create_user(user_data)
    mock_repo.create.assert_called_once()
```

#### API Testing
```python
async def test_create_user_endpoint(client, auth_headers):
    response = await client.post(
        "/api/v1/users",
        json={"email": "test@example.com"},
        headers=auth_headers
    )
    assert response.status_code == 201
```

### Monitoring & Observability

#### Structured Logging
```python
import logging
logger = logging.getLogger(__name__)

# Include context for traceability
logger.info(
    "User created successfully",
    extra={
        "user_id": user.id,
        "tenant_id": tenant.id,
        "request_id": request.headers.get("x-request-id")
    }
)
```

#### Health Checks
```python
# Every service should have health endpoint
@router.get("/health")
async def health_check():
    db_healthy = await db.health_check()
    cache_healthy = await cache.health_check()
    
    return {
        "status": "healthy" if all([db_healthy, cache_healthy]) else "unhealthy",
        "checks": {
            "database": db_healthy,
            "cache": cache_healthy
        }
    }
```

#### Performance Metrics
```python
import time
from src.common.utils import utc_now

async def with_timing(operation_name: str, func):
    start_time = time.time()
    try:
        result = await func()
        duration = (time.time() - start_time) * 1000
        logger.info(f"{operation_name} completed", extra={"duration_ms": duration})
        return result
    except Exception as e:
        duration = (time.time() - start_time) * 1000
        logger.error(f"{operation_name} failed", extra={"duration_ms": duration, "error": str(e)})
        raise
```

### Code Organization Principles

#### Common Patterns Directory Structure
```
src/common/
├── repositories/           # Base repository patterns
│   ├── __init__.py        # Exports BaseRepository
│   └── base.py           # BaseRepository implementation
├── services/              # Base service patterns  
│   ├── __init__.py        # Exports BaseService
│   └── base.py           # BaseService implementation
├── database/              # Database utilities
│   ├── connection.py     # DatabaseManager, DynamicDatabaseManager
│   └── utils.py          # process_database_record, build_filter_conditions
├── utils/                 # Common utilities
│   ├── datetime.py       # format_iso8601, utc_now
│   ├── encryption.py     # encrypt_password, decrypt_password
│   └── validators.py     # Common validation functions
├── exceptions/            # Exception hierarchy
│   └── base.py           # NeoAdminException, NotFoundError, etc.
├── models/               # Shared models
│   ├── base.py           # Base Pydantic models
│   ├── pagination.py     # PaginationMetadata, PaginationParams
│   └── responses.py      # APIResponse standard format
├── middleware/           # Global middleware
├── cache/                # Cache utilities
└── config/               # Configuration management
```

#### Feature Module Organization
```
src/features/{feature}/
├── __init__.py           # Export main router
├── models/               # Feature-specific models
│   ├── __init__.py
│   ├── domain.py        # Business domain models
│   ├── request.py       # API request schemas
│   └── response.py      # API response schemas  
├── repositories/         # Data access layer
│   ├── __init__.py
│   └── {feature}_repository.py  # Extends BaseRepository
├── services/             # Business logic layer
│   ├── __init__.py  
│   └── {feature}_service.py     # Extends BaseService
├── routers/              # API endpoints
│   ├── __init__.py
│   └── v1.py            # API routes
├── cache/                # Feature-specific caching
│   └── __init__.py
├── exceptions.py         # Feature-specific exceptions
└── dependencies.py       # Dependency injection
```

#### Import Patterns
```python
# Use absolute imports for clarity
from src.common.repositories.base import BaseRepository
from src.common.services.base import BaseService
from src.common.utils.datetime import format_iso8601

# Feature imports
from ..models.domain import DatabaseConnection
from ..repositories.database_repository import DatabaseConnectionRepository
```

#### Package Initialization
Every directory should have `__init__.py` with appropriate exports:

```python
# src/common/repositories/__init__.py
"""Common repository patterns and base classes."""
from .base import BaseRepository
__all__ = ["BaseRepository"]

# src/features/regions/__init__.py  
"""Regions feature module."""
from .routers.v1 import router as regions_router
__all__ = ["regions_router"]
```

### Migration Patterns

#### From Legacy Code
When migrating existing features to use common patterns:

1. **Step 1**: Identify repeated code patterns
2. **Step 2**: Create base utility/class in `src/common/`
3. **Step 3**: Update existing feature to inherit/use common pattern
4. **Step 4**: Verify functionality with existing tests
5. **Step 5**: Update other features to use same pattern

#### Example Migration
```python
# Before: Repeated pagination logic
class UserService:
    async def list_users(self, page: int, page_size: int):
        total_pages = (total_count + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size, 
            "total_pages": total_pages,
            "total_items": total_count,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
        
# After: Using common pattern
class UserService(BaseService[User]):
    async def list_users(self, page: int, page_size: int):
        # Leverage inherited pagination method
        pagination = self.create_pagination_metadata(page, page_size, total_count)
```

### Quality Assurance Patterns

#### Pre-Implementation Checklist
- [ ] Check if similar functionality exists in `src/common/`
- [ ] Identify opportunities to extend base patterns
- [ ] Plan for reusability across other features
- [ ] Consider security implications early
- [ ] Design for testability from the start

#### Code Review Checklist  
- [ ] Uses base repository/service patterns where applicable
- [ ] No repeated UUID/JSONB processing logic
- [ ] Consistent error handling with proper exception types
- [ ] Proper input validation at API boundaries
- [ ] No plaintext passwords or secrets
- [ ] Structured logging with appropriate context
- [ ] Performance considerations (N+1 queries, etc.)
- [ ] Test coverage for new patterns

#### Refactoring Guidelines
1. **Identify Duplication**: Look for repeated patterns across features
2. **Extract Commons**: Move repeated logic to `src/common/`
3. **Update Features**: Migrate existing features to use commons
4. **Test Thoroughly**: Ensure no regressions during refactoring
5. **Document Changes**: Update CLAUDE.md with new patterns

## Development Best Practices

1. **Follow DRY Principles** - Use base classes and common utilities
2. **Extend Base Patterns** - Always inherit from BaseRepository/BaseService  
3. **Centralize Common Logic** - Use utilities for repeated operations
4. **Standardize Error Handling** - Use specific exception types
5. **Validate Input Early** - Use Pydantic models at API boundaries
6. **Secure by Default** - Never store plaintext passwords/secrets
7. **Test Systematically** - Unit → Integration → E2E testing
8. **Monitor Everything** - Structured logging, health checks, metrics
9. **Document Decisions** - Update CLAUDE.md with new patterns
10. **Review for Patterns** - Look for repetition in code reviews
11. **Organize Consistently** - Follow established directory structure
12. **Import Explicitly** - Use absolute imports with clear paths

## Quick Troubleshooting

```bash
# Check API health
curl http://localhost:8001/health

# View API documentation
open http://localhost:8001/docs      # Scalar (recommended)
open http://localhost:8001/swagger   # Swagger UI
open http://localhost:8001/redoc     # ReDoc

# Check logs
tail -f logs/app.log  # If file logging is enabled

# Test database connection
python -c "import asyncio; from src.common.database.connection import get_database; asyncio.run(get_database().health_check())"

# Test Redis connection
python -c "import asyncio; from src.common.cache.client import get_cache; asyncio.run(get_cache().health_check())"
```

## Contact & Support

For questions about the Admin API architecture or implementation:
1. Check this CLAUDE.md file first
2. Review the ADMIN_API_PLAN.md for detailed specifications
3. Check existing code patterns in implemented features
4. Follow the established patterns for consistency

## Next Implementation Priority

Based on the current state and AUTH_IMPLEMENTATION_PLAN_FINAL.md:

1. **Complete Auth Feature with python-keycloak**:
   - Implement KeycloakClient with async methods
   - Create TokenManager with dual validation
   - Build RealmManager for multi-tenancy
   - Implement two-level permission system

2. **Platform Users Feature** - Complete with tenant-scoped permissions
3. **Organizations Feature** - Basic CRUD for organizations  
4. **Tenants Feature** - Core tenant management (store realm names correctly)
5. **RegionalDatabaseManager** - Dynamic routing to regional databases

Always refer to:
- ADMIN_API_PLAN.md for detailed feature requirements
- AUTH_IMPLEMENTATION_PLAN_FINAL.md for authentication details