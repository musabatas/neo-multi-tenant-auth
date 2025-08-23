# Neo-Commons Architecture Overview

## Vision Statement

Neo-Commons is an enterprise-grade shared library designed for true multi-tenancy, providing unified authentication, dynamic database management, and globally reusable components across all NeoMultiTenant services.

## Core Design Principles

### 1. **Enterprise-First Architecture**
- **Protocol-based dependency injection** using `@runtime_checkable` interfaces
- **Clean Architecture** with strict domain/application/infrastructure/interface separation
- **Zero-downtime deployments** with backward compatibility guarantees
- **Sub-millisecond performance** targets for critical paths (permissions, auth)

### 2. **True Multi-Tenancy**
- **Dynamic database connections** managed centrally via `admin.database_connections`
- **Schema-agnostic operations** supporting both admin and tenant template structures
- **Unified auth models** working seamlessly across admin and tenant contexts
- **Tenant isolation** at database, cache, and application levels

### 3. **Dynamic Configuration**
- **Runtime database discovery** from central registry
- **Hot-swappable configurations** without service restarts
- **Environment-aware settings** with secure credential management
- **Feature flag support** for gradual rollouts

### 4. **Global Reusability**
- **Overrideable defaults** for service-specific customization
- **Composable middleware** stack for FastAPI integration
- **Pluggable implementations** via protocol interfaces
- **Standardized error handling** across all services

## High-Level Architecture

```
neo-commons/
├── core/                    # Enterprise domain layer
│   ├── entities/           # Business objects (User, Tenant, Organization)
│   ├── value_objects/      # Immutable types (UserId, TenantId, PermissionCode)
│   ├── protocols/          # Domain contracts and interfaces
│   └── exceptions/         # Domain-specific exceptions
│
├── application/            # Application business rules
│   ├── services/           # Use cases and workflows
│   ├── commands/           # Command handlers (CQRS)
│   ├── queries/            # Query handlers (CQRS)
│   └── events/             # Domain events and handlers
│
├── infrastructure/         # External system integrations
│   ├── database/           # Dynamic connection management
│   │   ├── connection_manager.py    # Central connection registry
│   │   ├── schema_detector.py       # Auto-detect admin vs tenant
│   │   ├── health_monitor.py        # Connection health checking
│   │   └── failover_manager.py      # Automatic failover handling
│   │
│   ├── cache/              # Redis with tenant isolation
│   │   ├── tenant_aware_cache.py    # Tenant-scoped caching
│   │   ├── invalidation_manager.py  # Cache invalidation strategies
│   │   └── performance_monitor.py   # Cache performance tracking
│   │
│   ├── auth/               # Authentication providers
│   │   ├── keycloak/       # Keycloak integration
│   │   ├── unified_auth.py # Unified auth across contexts
│   │   └── user_mapper.py  # External-to-platform user mapping
│   │
│   └── external/           # Third-party integrations
│
├── interfaces/             # Interface adapters
│   ├── fastapi/            # FastAPI-specific adapters
│   │   ├── dependencies/   # Dependency injection
│   │   ├── middleware/     # Request/response middleware
│   │   ├── error_handlers/ # Exception handling
│   │   └── decorators/     # Route decorators
│   │
│   ├── cli/                # Command-line interfaces
│   └── web/                # Web-specific adapters
│
├── config/                 # Configuration management
│   ├── settings.py         # Global settings with overrides
│   ├── database_config.py  # Dynamic database configuration
│   ├── cache_config.py     # Cache configuration
│   └── feature_flags.py    # Feature flag management
│
└── utils/                  # Shared utilities
    ├── uuid.py             # UUIDv7 generation
    ├── datetime.py         # Timezone-aware datetime utilities
    ├── encryption.py       # Encryption/decryption utilities
    └── validation.py       # Input validation helpers
```

## Key Features

### 1. **Dynamic Database Connection Management**
- Central registry in `admin.database_connections` table
- Automatic health monitoring and failover
- Support for multi-region deployments
- Connection pooling with intelligent sizing

### 2. **Unified Authentication System**
- Works seamlessly with both admin and tenant databases
- Automatic user ID mapping (Keycloak ↔ Platform)
- Sub-millisecond permission checking with Redis caching
- Multi-realm support for tenant isolation

### 3. **Schema-Agnostic Operations**
- Auto-detection of admin vs tenant template structures
- Unified repository interfaces for both contexts
- Dynamic schema selection based on operation context
- Backward compatibility with existing schemas

### 4. **Enterprise-Grade Performance**
- Sub-millisecond permission checks (cached)
- Connection pooling with health monitoring
- Intelligent caching with tenant-aware invalidation
- Async-first design throughout

### 5. **Global Configurability**
- Service-specific overrides for all components
- Environment-aware configuration loading
- Feature flags for gradual rollouts
- Secure credential management

## Integration Points

### Service Integration
```python
# Simple integration for any service
from neo_commons import NeoCommonsApp

app = NeoCommonsApp(
    service_name="NeoAdminApi",
    config_overrides={
        "database": {"default_schema": "admin"},
        "auth": {"default_context": "platform"}
    }
)

# Automatic middleware, error handlers, and dependencies
fastapi_app = app.create_fastapi_app()
```

### Repository Usage
```python
# Unified repository pattern
from neo_commons.infrastructure.database import get_unified_repo

@app.get("/users")
async def list_users(
    repo: UserRepository = Depends(get_unified_repo(UserRepository))
):
    # Automatically uses correct schema (admin vs tenant)
    return await repo.list_users()
```

### Authentication
```python
# Unified auth across all contexts
from neo_commons.interfaces.fastapi import RequirePermissions

@app.get("/admin/users")
@RequirePermissions(["users:read"])
async def admin_list_users(user_context: UserContext = Depends()):
    # Works with both admin and tenant users
    # Automatic user ID mapping and permission checking
    pass
```

## Performance Targets

- **Permission checks**: < 1ms (cached), < 10ms (uncached)
- **Database connections**: < 50ms establishment, 99.9% availability
- **Cache operations**: < 0.1ms for gets, < 1ms for sets
- **User ID mapping**: < 5ms with Redis cache
- **Schema detection**: < 1ms cached, < 10ms discovery

## Security Features

- **Zero-trust architecture** with continuous validation
- **Tenant isolation** at all layers (database, cache, application)
- **Secure credential storage** with encryption at rest
- **Audit logging** for all sensitive operations
- **Rate limiting** with tenant-aware quotas
- **Input validation** with sanitization and escaping

## Backward Compatibility

- **Gradual migration** support for existing services
- **Legacy adapter layers** for smooth transitions
- **Version-aware APIs** with deprecation handling
- **Configuration migration** tools and documentation

This architecture provides the foundation for a truly enterprise-grade multi-tenant platform with the flexibility to support diverse deployment scenarios while maintaining security, performance, and operational excellence.