# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the neo-commons shared library.

## Project Overview

**neo-commons** - Enterprise-grade shared library for Python FastAPI applications with advanced Role-Based Access Control (RBAC), Keycloak integration, PostgreSQL operations, and Redis caching. Built for ultra flexibility, modularity, and performance at scale across multiple services.

### Key Features
- **Clean Architecture**: Domain/Application/Infrastructure/Interface layer separation
- **Protocol-Based Dependency Injection**: `@runtime_checkable` Protocol interfaces for maximum flexibility
- **Sub-millisecond Permission Checks** with intelligent caching
- **Multi-tenant Architecture** support with configurable schema isolation
- **Keycloak Integration** with enterprise SSO and JWT validation
- **PostgreSQL with AsyncPG** for high-performance data operations
- **Redis Caching** with automatic invalidation and tenant isolation
- **Comprehensive Middleware Stack** with security headers, rate limiting, and monitoring
- **Generic Utilities** for datetime, encryption, UUID, and database operations

### Technology Stack
- **Core**: Python 3.13+ with Clean Architecture patterns
- **Authentication**: Keycloak integration (external IAM)
- **Database**: PostgreSQL with asyncpg (no ORMs)
- **Caching**: Redis with automatic invalidation
- **Web Framework**: FastAPI integration patterns
- **Type Safety**: Full type hints with Pydantic models

### Essential Practices
1. **Always use Protocol interfaces** - Depend on contracts, not implementations
2. **Follow Clean Architecture boundaries** - Respect domain/application/infrastructure separation
3. **Use asyncpg patterns** - All database operations through repository protocols
4. **Cache aggressively** - Redis for permissions with proper invalidation
5. **Type everything** - Full type hints with Pydantic models
6. **Use UUIDv7** - Time-ordered identifiers for performance and consistency
7. **Protocol-based configuration** - Use config protocols, not concrete implementations
8. **Structured logging** - Include context (tenant_id, user_id, request_id)
9. **Handle errors gracefully** - Never expose internal details in error messages
10. **Test with protocols** - Mock protocol interfaces, not concrete classes

### Architecture Principles
1. **Generic First** - All code must be reusable across different services
2. **Protocol-Based DI** - Use dependency injection with Protocol interfaces
3. **Configuration-Driven** - No hardcoded service-specific values
4. **Performance First** - Sub-millisecond permission checks are critical
5. **Clean Architecture** - Clear separation between layers
6. **Security by Design** - Defense in depth, zero trust
7. **Observable Systems** - Comprehensive logging and monitoring

### Code Quality Standards
1. **File Limits** - Every file ≤ 400 lines (split into logical modules if larger)
2. **Function Limits** - Every function ≤ 80 lines with single responsibility
3. **Protocol Interfaces** - All dependencies must use Protocol interfaces
4. **No Hardcoded Values** - All configuration through dependency injection
5. **Clean Code** - Descriptive naming, consistent formatting, minimal nesting
6. **SOLID Principles** - Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
7. **Testability** - Design for unit testing with protocol interfaces
8. **Documentation** - Self-documenting code with strategic comments explaining "why" not "what"
9. **Error Handling** - Graceful failure with informative error messages
10. **No Service-Specific Code** - Library must be generic and reusable

## Quick Start Guide

### Installation
```bash
# From local development
cd /Users/musabatas/Workspaces/NeoMultiTenant/neo-commons
pip install -e .

# Or from package (when published)
pip install neo-commons
```

### Basic Usage Patterns

#### Protocol-Based Dependency Injection
```python
from neo_commons.auth import AuthService, PermissionService
from neo_commons.auth.protocols import AuthRepository, PermissionRepository
from neo_commons.config import BaseConfigProtocol

# Use protocols, not concrete implementations
class MyService:
    def __init__(
        self,
        auth_service: AuthService,
        permission_service: PermissionService,
        config: BaseConfigProtocol
    ):
        self.auth_service = auth_service
        self.permission_service = permission_service
        self.config = config
```

#### Configuration with Protocols
```python
from neo_commons.config import BaseConfigProtocol, BaseNeoConfig

# Create service-specific config that implements the protocol
class MyAppConfig(BaseNeoConfig):
    app_name: str = Field(default="MyApp", env="APP_NAME")
    # Override defaults with your service values
    
# Use protocol interface in services
def create_service(config: BaseConfigProtocol) -> MyService:
    return MyService(config)
```

#### Database Operations with Repositories
```python
from neo_commons.auth.protocols import PermissionRepository
from neo_commons.database import DatabaseManager

# Use repository protocols for data access
async def check_permission(
    user_id: str,
    resource: str,
    action: str,
    tenant_id: str,
    permission_repo: PermissionRepository,
    schema_name: str = "admin"  # Configurable schema
) -> bool:
    return await permission_repo.check_permission(
        user_id, resource, action, tenant_id, schema_name
    )
```

## Architecture Guide

### Clean Architecture Layers

#### Domain Layer (`neo_commons.*/domain/`)
- **Purpose**: Pure business logic and rules
- **Contains**: Entities, value objects, protocols (interfaces)
- **Dependencies**: None (no external dependencies)
- **Example**: `neo_commons.auth.domain.entities.Permission`

#### Application Layer (`neo_commons.*/application/`)
- **Purpose**: Use cases and workflows
- **Contains**: Service implementations, command/query handlers
- **Dependencies**: Domain layer only
- **Example**: `neo_commons.auth.application.services.PermissionService`

#### Infrastructure Layer (`neo_commons.*/infrastructure/`)
- **Purpose**: External concerns (database, cache, Keycloak)
- **Contains**: Repository implementations, external integrations
- **Dependencies**: Domain and application layers
- **Example**: `neo_commons.auth.infrastructure.repositories.PermissionRepository`

#### Interface Layer (`neo_commons.*/interfaces/`)
- **Purpose**: Framework adapters and external interfaces
- **Contains**: FastAPI dependencies, decorators, middleware
- **Dependencies**: All other layers
- **Example**: `neo_commons.auth.interfaces.decorators.permission_required`

### Protocol-Based Dependency Injection

#### Core Patterns
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AuthRepository(Protocol):
    async def get_user_permissions(
        self, 
        user_id: str, 
        tenant_id: str,
        schema_name: str = "admin"
    ) -> list[Permission]:
        """Get user permissions with configurable schema."""
        
@runtime_checkable
class CacheService(Protocol):
    async def get(self, key: str, tenant_id: str) -> str | None:
        """Get cached value with tenant isolation."""
        
    async def set(self, key: str, value: str, tenant_id: str, ttl: int = 3600) -> None:
        """Set cached value with automatic invalidation."""
```

#### Implementation Registration
```python
# In your service's dependency injection setup
def configure_dependencies(container):
    # Register protocol implementations
    container.register(AuthRepository, PostgreSQLAuthRepository)
    container.register(CacheService, RedisCache)
    container.register(BaseConfigProtocol, MyAppConfig)
```

### Database Operations

#### Repository Pattern with Configurable Schemas
```python
from neo_commons.auth.infrastructure.repositories import PermissionRepository

class CustomPermissionRepository(PermissionRepository):
    def __init__(self, db_manager: DatabaseManager, schema_name: str = "custom"):
        super().__init__(db_manager)
        self.schema_name = schema_name
    
    async def get_permissions(self, user_id: str) -> List[Permission]:
        # Uses configurable schema instead of hardcoded values
        query = f"""
            SELECT * FROM {self.schema_name}.permissions 
            WHERE user_id = $1
        """
        return await self.db_manager.fetch(query, user_id)
```

#### Dynamic Database Connections
```python
from neo_commons.database import DynamicDatabaseManager

# Initialize with custom schema configuration
dynamic_db = DynamicDatabaseManager(
    admin_db_manager=admin_db,
    schema_name="my_app_admin"  # Configurable schema name
)

# Load connections from your schema
connections = await dynamic_db.load_database_connections()
```

### Caching Patterns

#### Intelligent Caching with Tenant Isolation
```python
from neo_commons.cache import CacheService
from neo_commons.auth.application.services import PermissionService

class MyPermissionService(PermissionService):
    def __init__(self, cache: CacheService, auth_repo: AuthRepository):
        self.cache = cache
        self.auth_repo = auth_repo
    
    async def check_permission(
        self, 
        user_id: str, 
        resource: str, 
        action: str, 
        tenant_id: str
    ) -> bool:
        # Check cache first (<0.1ms)
        cache_key = f"perm:{resource}:{action}:{user_id}"
        cached_result = await self.cache.get(cache_key, tenant_id)
        
        if cached_result is not None:
            return cached_result == "true"
            
        # Fallback to database (<0.5ms)
        has_permission = await self.auth_repo.check_permission(
            user_id, resource, action, tenant_id
        )
        await self.cache.set(cache_key, str(has_permission), tenant_id, ttl=300)
        return has_permission
```

### Middleware Integration

#### FastAPI Integration
```python
from fastapi import FastAPI
from neo_commons.middleware import (
    UnifiedContextMiddleware,
    SecurityHeadersMiddleware,
    MiddlewareConfig
)

app = FastAPI()

# Configure middleware with your app settings
middleware_config = MiddlewareConfig(
    environment="production",
    unified_context_enabled=True,
    security_headers_enabled=True
)

# Add neo-commons middleware
app.add_middleware(UnifiedContextMiddleware, config=middleware_config)
app.add_middleware(SecurityHeadersMiddleware, config=middleware_config)
```

#### Request Context Usage
```python
from neo_commons.middleware import get_request_context, UnifiedRequestContext

@app.get("/api/users")
async def get_users():
    # Access request context from neo-commons
    context: UnifiedRequestContext = get_request_context()
    
    # Context includes tenant_id, user_id, request_id automatically
    logger.info(
        "Getting users",
        extra={
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "request_id": context.request_id
        }
    )
```

### Keycloak Integration

#### JWT Token Validation
```python
from neo_commons.integrations.keycloak import (
    EnhancedKeycloakAsyncClient,
    DefaultKeycloakConfig
)

# Configure Keycloak with your settings
keycloak_config = DefaultKeycloakConfig(
    server_url="https://your-keycloak.com",
    admin_realm="your-realm",
    client_id="your-client"
)

keycloak_client = EnhancedKeycloakAsyncClient(keycloak_config)

# Validate JWT tokens
async def validate_token(token: str) -> dict:
    return await keycloak_client.validate_token(token)
```

## Development Guidelines

### Creating New Components

#### 1. Define Protocols First
```python
# Always start with protocol definition
from typing import Protocol, runtime_checkable

@runtime_checkable
class MyServiceProtocol(Protocol):
    async def do_something(self, data: str) -> Result:
        """Protocol method with clear contract."""
```

#### 2. Implement with Protocol Interface
```python
# Implement against the protocol
class MyServiceImpl(MyServiceProtocol):
    def __init__(self, dependency: SomeDependencyProtocol):
        self.dependency = dependency
    
    async def do_something(self, data: str) -> Result:
        # Implementation details
        pass
```

#### 3. Use Dependency Injection
```python
# FastAPI dependency injection
from fastapi import Depends

def get_my_service() -> MyServiceProtocol:
    # Configure and return implementation
    # This should be configured in your DI container
    raise NotImplementedError("Configure via DI container")

@app.get("/endpoint")
async def endpoint(service: MyServiceProtocol = Depends(get_my_service)):
    return await service.do_something("data")
```

### Configuration Patterns

#### Service-Specific Configuration
```python
from neo_commons.config import BaseNeoConfig

class MyAppConfig(BaseNeoConfig):
    """Configuration for MyApp service."""
    
    # Override generic defaults with service-specific values
    app_name: str = Field(default="MyApp", env="APP_NAME")
    port: int = Field(default=8001, env="PORT")
    
    # Add service-specific configuration
    my_feature_enabled: bool = Field(default=True, env="MY_FEATURE_ENABLED")
    my_api_key: str = Field(env="MY_API_KEY")
```

#### Environment-Based Configuration
```python
from neo_commons.config import create_config_for_environment

# Automatically selects appropriate config based on environment
config = create_config_for_environment(env="production")

# Or create specific configs
from neo_commons.config import get_admin_config, get_testing_config

admin_config = get_admin_config()  # For admin services
test_config = get_testing_config()  # For testing
```

### Testing Patterns

#### Protocol-Based Testing
```python
import pytest
from unittest.mock import AsyncMock
from neo_commons.auth.protocols import AuthRepository, CacheService

@pytest.fixture
def mock_auth_repository():
    """Mock auth repository using protocol interface."""
    mock = AsyncMock(spec=AuthRepository)
    mock.check_permission.return_value = True
    return mock

@pytest.fixture
def mock_cache_service():
    """Mock cache service using protocol interface."""
    mock = AsyncMock(spec=CacheService)
    mock.get.return_value = None
    mock.set.return_value = None
    return mock

async def test_permission_service(mock_auth_repository, mock_cache_service):
    """Test using protocol mocks."""
    service = PermissionService(mock_cache_service, mock_auth_repository)
    
    result = await service.check_permission("user1", "resource", "read", "tenant1")
    
    assert result is True
    mock_auth_repository.check_permission.assert_called_once()
```

### Migration from Service-Specific Code

#### Before (Service-Specific)
```python
# Tightly coupled to NeoAdminApi
from admin.services.auth_service import AuthService
from admin.repositories.permission_repository import PermissionRepository

class UserController:
    def __init__(self):
        self.auth_service = AuthService()  # Direct instantiation
        self.permission_repo = PermissionRepository()  # Hardcoded
```

#### After (Protocol-Based)
```python
# Generic with neo-commons
from neo_commons.auth import AuthService, PermissionService
from neo_commons.auth.protocols import AuthRepository

class UserController:
    def __init__(
        self,
        auth_service: AuthService,
        permission_service: PermissionService
    ):
        self.auth_service = auth_service
        self.permission_service = permission_service

# Dependency injection configuration
def get_auth_service() -> AuthService:
    # Configured via DI container in your app
    return container.resolve(AuthService)
```

## Critical Issues to Address

### 🚨 Repository Schema Configuration
**Status**: CRITICAL - Must be fixed before production use

**Problem**: Auth repositories contain hardcoded schema names
```python
# PROBLEMATIC (current state)
query = "SELECT * FROM admin.permissions WHERE user_id = $1"
```

**Solution**: Make schemas configurable
```python
# CORRECT (target state)
query = f"SELECT * FROM {self.schema_name}.permissions WHERE user_id = $1"
```

**Implementation**: 
1. Add `schema_name` parameter to all repository constructors
2. Update all SQL queries to use dynamic schema names
3. Configure schemas via dependency injection

### ⚠️ Configuration Hardcoded Values
**Status**: HIGH - Reduces reusability

**Problem**: Config base classes contain service-specific defaults
```python
# PROBLEMATIC
app_name: str = Field(default="NeoAdminApi", env="APP_NAME")
```

**Solution**: Use generic defaults
```python
# CORRECT
app_name: str = Field(default="Neo Application", env="APP_NAME")
```

## Performance Targets

- Permission checks: < 1ms with cache
- API p95 latency: < 100ms
- Simple queries: < 10ms; complex queries: < 50ms
- Cache hit rate for permissions: > 90%

## Security Checklist

- [ ] Validate all inputs with Pydantic models and protocol interfaces
- [ ] Use parameterized queries only; never format SQL with user input
- [ ] Enforce authorization through protocol-based permission services
- [ ] Rate limit endpoints using neo-commons middleware
- [ ] Implement audit logging through structured logging utilities
- [ ] Never expose sensitive info in errors; use generic error handlers
- [ ] Implement cache invalidation for write operations
- [ ] Use protocol-based dependency injection for security services

## UUIDv7 Guidance

- Use `neo_commons.utils.uuid.generate_uuid_v7()` for all new identifiers
- Provides time-ordered IDs improving index performance
- Includes utilities for timestamp extraction and validation
- Avoid using uuid4 directly in new code paths

## Integration Examples

### FastAPI Service Integration
```python
from fastapi import FastAPI, Depends
from neo_commons.auth import AuthService
from neo_commons.config import BaseConfigProtocol, MyAppConfig
from neo_commons.middleware import UnifiedContextMiddleware

app = FastAPI()

# Configuration
app_config = MyAppConfig()

# Middleware
app.add_middleware(UnifiedContextMiddleware, config=app_config)

# Dependencies
def get_auth_service() -> AuthService:
    # Configure with your DI container
    return container.resolve(AuthService)

@app.get("/protected")
async def protected_endpoint(
    auth_service: AuthService = Depends(get_auth_service)
):
    # Use neo-commons services
    pass
```

### Database Repository Integration
```python
from neo_commons.auth.infrastructure.repositories import PermissionRepository
from neo_commons.database import DatabaseManager

# Configure with your schema
class MyPermissionRepository(PermissionRepository):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__(db_manager, schema_name="my_app_schema")

# Register in DI container
container.register(PermissionRepository, MyPermissionRepository)
```

## Best Practices Summary

1. **Always use Protocol interfaces** - Never depend on concrete implementations
2. **Configure everything** - No hardcoded service-specific values
3. **Follow Clean Architecture** - Respect layer boundaries strictly
4. **Test with protocols** - Mock interfaces, not implementations
5. **Use provided utilities** - Leverage datetime, UUID, encryption utilities
6. **Cache intelligently** - Use Redis patterns with tenant isolation
7. **Log structurally** - Include context via middleware
8. **Handle errors gracefully** - Use generic error patterns
9. **Performance first** - Target sub-millisecond permission checks
10. **Security by design** - Use protocol-based security services

---

# important-instruction-reminders
**CRITICAL**: When integrating neo-commons into services:
1. **Always implement Protocol interfaces** - Never use concrete dependencies
2. **Configure schemas dynamically** - Never hardcode database schema names
3. **Use dependency injection** - Configure implementations via DI containers
4. **Test with protocol mocks** - Mock interfaces for unit testing
5. **Follow Clean Architecture** - Respect domain/application/infrastructure boundaries
6. **Make everything configurable** - No service-specific hardcoded values