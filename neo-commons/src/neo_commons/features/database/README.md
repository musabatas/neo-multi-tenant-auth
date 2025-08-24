# Neo-Commons Database Feature

Enterprise-grade database management feature for the NeoMultiTenant platform. Provides centralized connection management, health monitoring, failover capabilities, and multi-tenant schema resolution.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Core Features](#core-features)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Connection Management](#connection-management)
- [Schema Resolution](#schema-resolution)
- [Health Monitoring](#health-monitoring)
- [Performance & Metrics](#performance--metrics)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

## Overview

The database feature follows **Feature-First + Clean Core** architecture principles, providing:

- **Centralized Connection Management**: Dynamic connection registry with automatic loading from `admin.database_connections`
- **Multi-Tenant Schema Support**: Dynamic schema resolution for tenant isolation
- **Enterprise-Grade Features**: Connection pooling, health monitoring, failover, load balancing
- **Protocol-Based Design**: `@runtime_checkable` interfaces for flexible dependency injection
- **Performance Optimization**: Async operations, connection pooling, intelligent caching

## Architecture

### Directory Structure

```
database/
├── entities/              # Domain objects and protocols
│   ├── config.py         # Database configuration
│   ├── database_connection.py  # Connection entity
│   └── protocols.py      # Domain contracts (@runtime_checkable)
├── services/              # Business logic orchestration
│   └── database_service.py     # Main service facade
├── repositories/          # Data access implementations
│   ├── connection_manager.py   # Connection pool management
│   ├── connection_registry.py  # Dynamic connection registry
│   ├── health_checker.py      # Health monitoring
│   ├── schema_resolver.py     # Multi-tenant schema resolution
│   └── [other implementations]
└── utils/                # Utilities and helpers
    ├── admin_connection.py    # Admin connection utilities
    ├── connection_factory.py  # Connection factory
    ├── queries.py            # Query constants
    └── validation.py         # Input validation
```

### Core Components

1. **DatabaseService**: Main facade orchestrating all database functionality
2. **ConnectionManager**: Manages connection pools with lazy initialization
3. **ConnectionRegistry**: Dynamic registry loading connections from database
4. **SchemaResolver**: Multi-tenant schema resolution and validation
5. **HealthChecker**: Connection health monitoring and recovery

## Core Features

### ✅ Connection Management
- **Dynamic Registry**: Loads connections from `admin.database_connections` table
- **Lazy Initialization**: Connection pools created only when first accessed
- **Connection Pooling**: AsyncPG-based pools with configurable sizing
- **Password Encryption**: Automatic Fernet encryption/decryption

### ✅ Multi-Tenant Support
- **Schema-Based Tenancy**: Each tenant gets a dedicated PostgreSQL schema
- **Dynamic Schema Resolution**: Runtime schema name resolution
- **Tenant Isolation**: Complete data separation between tenants

### ✅ Enterprise Features
- **Health Monitoring**: Real-time connection health checks
- **Failover Support**: Automatic failover to healthy connections
- **Load Balancing**: Intelligent connection selection
- **Metrics & Monitoring**: Comprehensive pool statistics

### ✅ Performance
- **Async Operations**: Full async/await support with asyncpg
- **Connection Pooling**: Configurable min/max pool sizing
- **Efficient Queries**: Parameterized queries with query constants
- **Resource Management**: Automatic connection cleanup and recovery

## Quick Start

### 1. Basic Setup

```python
from neo_commons.features.database import DatabaseService, DatabaseSettings
from neo_commons.features.database.repositories import (
    DatabaseConnectionManager,
    RedisConnectionRegistry,
    ConnectionHealthChecker,
    SchemaResolver
)

# Initialize components
settings = DatabaseSettings()
registry = RedisConnectionRegistry()
health_checker = ConnectionHealthChecker()
connection_manager = DatabaseConnectionManager(registry, health_checker)
schema_resolver = SchemaResolver()

# Create database service
db_service = DatabaseService(
    connection_manager=connection_manager,
    schema_resolver=schema_resolver,
    settings=settings
)
```

### 2. FastAPI Dependency Injection

```python
# dependencies.py
from functools import lru_cache
from neo_commons.features.database import DatabaseService

@lru_cache()
async def get_database_service() -> DatabaseService:
    # Auto-loads connections from admin.database_connections
    return await DatabaseService.create_with_auto_loading()

# router.py
from fastapi import Depends

@router.get("/data")
async def get_data(db_service: DatabaseService = Depends(get_database_service)):
    async with db_service.get_connection("admin") as conn:
        result = await conn.fetchrow("SELECT COUNT(*) FROM admin.tenants")
        return {"tenant_count": result[0]}
```

## Configuration

### Environment Variables

```bash
# Primary admin database connection
ADMIN_DATABASE_URL="postgresql://postgres:password@localhost:5432/neofast_admin?sslmode=disable"

# Database encryption key (32 characters)
DB_ENCRYPTION_KEY="your-32-character-encryption-key-here"

# Optional Redis for connection registry caching
REDIS_URL="redis://localhost:6379/0"
```

### Database Connection Registry

All non-admin connections are managed through the `admin.database_connections` table:

```sql
-- Example connection registration
INSERT INTO admin.database_connections (
    id, connection_name, connection_type, region_id,
    host, port, database_name, username, encrypted_password,
    ssl_mode, pool_min_size, pool_max_size,
    pool_timeout_seconds, is_active
) VALUES (
    gen_random_uuid(), 'tenant-db-us', 'SHARED', 'us-east',
    'tenant-db.example.com', 5432, 'neofast_shared_us',
    'app_user', 'encrypted_password_here',
    'require', 5, 20, 30, true
);
```

## Usage Examples

### Basic Database Operations

```python
# Simple query execution
async with db_service.get_connection("admin") as conn:
    tenants = await conn.fetch("""
        SELECT id, name, slug FROM admin.tenants 
        WHERE is_active = true
    """)

# Using connection manager methods
results = await db_service.connection_manager.execute_query(
    "admin", 
    "SELECT * FROM admin.organizations WHERE id = $1", 
    organization_id
)

# Fetch single row
org_data = await db_service.connection_manager.execute_fetchrow(
    "admin",
    "SELECT name, slug FROM admin.organizations WHERE id = $1",
    org_id
)

# Execute commands (INSERT/UPDATE/DELETE)
status = await db_service.connection_manager.execute_command(
    "admin",
    "UPDATE admin.tenants SET is_active = $1 WHERE id = $2",
    False, tenant_id
)
```

### Multi-Tenant Operations

```python
from neo_commons.core.value_objects import TenantId

# Resolve tenant schema
tenant_id = TenantId("550e8400-e29b-41d4-a716-446655440000")
schema_name = await db_service.schema_resolver.get_tenant_schema(str(tenant_id))

# Execute query in tenant schema  
async with db_service.get_connection("tenant-db-us") as conn:
    users = await conn.fetch(f"""
        SELECT id, email, name FROM {schema_name}.users 
        WHERE is_active = true
    """)

# Using schema-aware repository pattern
from neo_commons.core.shared.context import RequestContext

context = RequestContext(tenant_id=tenant_id, user_id="user123")
async with db_service.get_tenant_connection(context) as conn:
    # Connection is automatically configured for tenant schema
    result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
```

### Health Monitoring

```python
# Check health of specific connection
health_status = await db_service.health_check("admin")
print(f"Admin DB Health: {health_status['admin']}")

# Check all connections
all_health = await db_service.health_check()
for conn_name, status in all_health.items():
    print(f"{conn_name}: {status}")

# Get detailed connection statistics
stats = await db_service.get_connection_stats()
for conn_name, pool_stats in stats.items():
    print(f"{conn_name}: {pool_stats['total_connections']} connections")
```

### Connection Pool Management

```python
# Get pool metrics
metrics = await db_service.connection_manager.get_pool_metrics("admin")
print(f"Active connections: {metrics.active_connections}")
print(f"Pool efficiency: {metrics.pool_efficiency}%")

# Close specific pool
await db_service.connection_manager.close_pool("old-connection")

# Close all pools (cleanup)
await db_service.connection_manager.close_all_pools()
```

## Connection Management

### Connection Lifecycle

1. **Registration**: Connections defined in `admin.database_connections` table
2. **Auto-Loading**: DatabaseService loads connections on startup
3. **Lazy Initialization**: Pools created only on first access
4. **Health Monitoring**: Continuous health checks and automatic recovery
5. **Graceful Shutdown**: Proper connection cleanup on service shutdown

### Pool Configuration

```python
# Pool settings in database_connections table
{
    "pool_min_size": 5,        # Minimum connections maintained
    "pool_max_size": 20,       # Maximum connections allowed
    "pool_timeout_seconds": 30, # Connection acquisition timeout
    "pool_recycle_seconds": 3600, # Connection recycling interval
    "pool_pre_ping": true      # Validate connections before use
}
```

### Connection Types

- **ADMIN**: Platform administration database
- **SHARED**: Tenant shared databases (schema-based multi-tenancy)
- **ANALYTICS**: Analytics and reporting databases
- **DEDICATED**: Tenant-specific dedicated databases

## Schema Resolution

### Multi-Tenant Schema Patterns

```python
# Schema naming conventions
admin_schema = "admin"                    # Platform management
tenant_schema = f"tenant_{tenant_slug}"  # Tenant-specific data
shared_schema = "shared"                  # Cross-tenant shared data
template_schema = "tenant_template"       # New tenant template

# Dynamic schema resolution
schema = await schema_resolver.resolve_schema(
    tenant_id="tenant-123",
    context_type="tenant"  # admin | tenant | shared
)

# Schema validation
is_valid = await schema_resolver.validate_schema_name(schema)
```

## Health Monitoring

### Health Check Strategies

- **Basic Health Check**: Simple `SELECT 1` query
- **Connection Pool Health**: Pool size and connection availability
- **Performance Health**: Query response time monitoring
- **Custom Health Checks**: Application-specific health validation

### Health Status Types

```python
from neo_commons.config.constants import HealthStatus

HealthStatus.HEALTHY     # Connection operational
HealthStatus.DEGRADED    # Connection slow but functional
HealthStatus.UNHEALTHY   # Connection failed or unavailable
HealthStatus.UNKNOWN     # Health status not determined
```

### Automatic Recovery

- **Connection Retry**: Automatic reconnection on transient failures
- **Pool Recreation**: Rebuild connection pools on persistent failures
- **Failover Support**: Switch to backup connections when available
- **Circuit Breaker**: Prevent cascade failures with circuit breaker pattern

## Performance & Metrics

### Pool Metrics

```python
@dataclass
class PoolMetrics:
    # Connection state
    total_connections: int
    active_connections: int
    idle_connections: int
    
    # Performance metrics
    avg_response_time_ms: float
    p95_response_time_ms: float
    connection_acquisition_time_ms: float
    
    # Health metrics
    health_score: float  # 0-100 health score
    query_success_rate: float
    recent_failures: int
    
    # Capacity metrics
    saturation_level: float  # 0.0-1.0
    pool_efficiency: float
```

### Performance Targets

- **Connection Acquisition**: < 10ms average
- **Query Execution**: < 100ms for simple queries
- **Health Checks**: < 5ms response time
- **Pool Efficiency**: > 80% connection utilization

## Error Handling

### Database Exceptions

```python
from neo_commons.core.exceptions import (
    DatabaseError,           # Base database error
    ConnectionNotFoundError, # Connection not in registry
    ConnectionPoolError,     # Pool operation failed
    HealthCheckFailedError,  # Health check failure
    SchemaError,            # Schema resolution error
    QueryError              # Query execution error
)

# Error handling patterns
try:
    async with db_service.get_connection("tenant-db") as conn:
        result = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
except ConnectionNotFoundError:
    # Handle missing connection
    pass
except ConnectionPoolError:
    # Handle pool issues
    pass
except DatabaseError as e:
    # Handle general database errors
    logger.error(f"Database operation failed: {e}")
```

### Retry Patterns

```python
from neo_commons.features.database.utils.error_handling import database_error_handler

@database_error_handler(retries=3, backoff=2.0)
async def execute_with_retry():
    async with db_service.get_connection("admin") as conn:
        return await conn.fetchrow("SELECT * FROM admin.tenants WHERE id = $1", tenant_id)
```

## Best Practices

### Connection Management

- ✅ **Use Context Managers**: Always use `async with` for connections
- ✅ **Pool Sizing**: Configure pools based on application load
- ✅ **Connection Reuse**: Reuse connections within request scope
- ✅ **Graceful Shutdown**: Properly close pools on application shutdown
- ❌ **Long-Lived Connections**: Don't hold connections across requests

### Query Patterns

- ✅ **Parameterized Queries**: Always use `$1, $2` parameters
- ✅ **Query Constants**: Define reusable queries in `queries.py`
- ✅ **Schema Prefixing**: Use dynamic schema resolution
- ✅ **Error Handling**: Wrap database calls in try/catch blocks
- ❌ **String Formatting**: Never format SQL with user input

### Multi-Tenant Considerations

- ✅ **Schema Isolation**: Use separate schemas for tenant data
- ✅ **Connection Routing**: Route tenants to appropriate databases
- ✅ **Resource Limits**: Implement per-tenant resource quotas
- ✅ **Data Privacy**: Ensure complete tenant data isolation
- ❌ **Shared Tables**: Avoid tenant data in shared tables

### Performance Optimization

- ✅ **Connection Pooling**: Use appropriate pool sizing
- ✅ **Query Optimization**: Monitor and optimize slow queries  
- ✅ **Index Usage**: Ensure proper database indexing
- ✅ **Batch Operations**: Group related operations
- ❌ **N+1 Queries**: Avoid repeated single-record queries

## API Reference

### DatabaseService

Main service facade for database operations.

```python
class DatabaseService:
    async def get_connection(self, connection_name: str) -> AsyncContextManager[Connection]
    async def get_tenant_connection(self, context: RequestContext) -> AsyncContextManager[Connection]
    async def health_check(self, connection_name: Optional[str] = None) -> Dict[str, HealthStatus]
    async def get_connection_stats(self) -> Dict[str, Any]
    async def close(self) -> None
    
    @classmethod
    async def create_with_auto_loading(cls) -> "DatabaseService"
```

### ConnectionManager Protocol

```python
@runtime_checkable
class ConnectionManager(Protocol):
    async def get_pool(self, connection_name: str) -> ConnectionPool
    async def get_connection(self, connection_name: str) -> AsyncContextManager[Connection]
    async def execute_query(self, connection_name: str, query: str, *args) -> List[Dict]
    async def execute_fetchrow(self, connection_name: str, query: str, *args) -> Optional[Dict]
    async def execute_fetchval(self, connection_name: str, query: str, *args) -> Any
    async def execute_command(self, connection_name: str, command: str, *args) -> str
    async def health_check(self, connection_name: Optional[str] = None) -> Dict[str, HealthStatus]
```

### SchemaResolver Protocol

```python
@runtime_checkable
class SchemaResolver(Protocol):
    async def resolve_schema(self, tenant_id: Optional[str] = None, context_type: str = "admin") -> str
    async def get_tenant_schema(self, tenant_id: str) -> str
    async def validate_schema_name(self, schema_name: str) -> bool
    async def get_admin_schema(self) -> str
```

---

## 🤝 Contributing

When contributing to the database feature:

1. **Follow Feature-First Architecture**: Place domain logic in appropriate modules
2. **Use Protocol Contracts**: Implement `@runtime_checkable` protocols
3. **Write Tests**: Include unit tests for new functionality
4. **Update Documentation**: Keep README and docstrings current
5. **Performance Testing**: Validate performance impact of changes

## 📝 License

Part of the NeoMultiTenant platform. See main repository license for details.

---

*This README covers the essential aspects of the neo-commons database feature. For specific implementation details, refer to the source code and inline documentation.*