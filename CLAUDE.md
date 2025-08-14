# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.


## Project Overview

**NeoFast** - Enterprise-grade Python FastAPI platform with advanced Role-Based Access Control (RBAC), using Keycloak for authentication, PostgreSQL for data persistence, and Redis for caching. Built for ultra flexibility, modularity, and performance at scale.

### Key Features
- **Sub-millisecond permission checks** with intelligent caching
- **Multi-tenant architecture** with complete data isolation
- **Keycloak integration** for enterprise SSO and authentication
- **PostgreSQL with asyncpg** for high-performance data operations
- **Redis caching** with automatic invalidation and tenant isolation
- **Comprehensive audit logging** with tamper-proof design
- **Enterprise middleware stack** with security headers, rate limiting, and monitoring

### Technology Stack
- **API**: Python 3.13+ with FastAPI (async)
- **Authentication**: Keycloak (external IAM)
- **Database**: PostgreSQL 17+ with asyncpg
- **Caching**: Redis with automatic invalidation
- **RBAC**: Custom PostgreSQL-based with JSONB optimization

### Essential Practices
1. **Always use asyncpg** for database operations, never use ORMs for permission checks
2. **Always check Context7 MCP** for latest FastAPI/Keycloak documentation
3. **Follow async patterns** - All I/O operations must be async
4. **Maintain separation** - Keycloak for auth, PostgreSQL for permissions
5. **Use repository pattern** - All database operations through repository classes
6. **Cache aggressively** - Redis for permissions with proper invalidation
7. **Type everything** - Full type hints with Pydantic models
8. **Use UUIDv7** - All UUID generation must use UUIDv7 for time-ordering and consistency with database
9. **Test in tests/ directory** - Never create test files in root directory, always use tests/ or scripts/
10. **Never commit to main** - Always work in feature branches and create PRs
11. **Use structured logging** - All logs must include context (tenant_id, user_id, request_id)
12. **Handle errors gracefully** - Never expose internal details in error messages

### Architecture Principles
1. **Performance First** - Sub-millisecond permission checks are critical
2. **Feature Modularity** - Each feature is completely self-contained
3. **Clean Architecture** - Clear separation between layers
4. **Security by Design** - Defense in depth, zero trust
5. **Observable Systems** - Comprehensive logging and monitoring

### Code Quality Standards
1. **File Limits** - Every file ≤ 400 lines (split into logical modules if larger)
2. **Function Limits** - Every function ≤ 80 lines with single responsibility
3. **DRY Principle** - Eliminate code duplication through abstraction
4. **SOLID Principles** - Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
5. **Clean Code** - Descriptive naming, consistent formatting, minimal nesting
6. **Testability** - Design for unit testing with dependency injection
7. **Documentation** - Self-documenting code with strategic comments explaining "why" not "what"
8. **Error Handling** - Graceful failure with informative error messages
9. **No Hardcoded Secrets** - All credentials must come from environment variables

## Quick Start Guide

### Prerequisites
- Python 3.13+
- PostgreSQL 16+
- Redis 7+
- Keycloak 26+
- Docker & Docker Compose (for easy setup)

**NeoMultiTenant** - Enterprise-grade multi-tenant, multi-region, multi-database platform built with Python FastAPI, PostgreSQL 17+, Redis, and Keycloak. Features ultra-scalability, schema-based and database-based multi-tenancy, comprehensive RBAC with custom permissions, and sub-millisecond permission checks.

### Key Architecture Components

- **NeoInfrastructure**: Database migrations, Docker infrastructure, multi-region PostgreSQL setup
- **neo-commons**: Shared library with authentication, caching, database operations, and utilities
- **NeoAdminApi**: Platform administration API (Port 8001)
- **NeoTenantApi**: Tenant-specific API (Port 8002)
- **NeoAdmin**: Admin dashboard React/Next.js (Port 3001)
- **NeoTenantFrontend**: Tenant frontend React/Next.js (Port 3003)
- **NeoTenantAdmin**: Tenant admin interface React/Next.js (Port 3002)
- **NeoMarketingFrontend**: Marketing website React/Next.js (Port 3000)

### Service Ports Summary

| Service | Port | Description |
|---------|------|-------------|
| Deployment API | 8000 | Migration management API |
| Admin API | 8001 | Platform administration |
| Tenant API | 8002 | Tenant operations |
| Marketing Site | 3000 | Public website |
| Admin Dashboard | 3001 | Platform admin UI |
| Tenant Admin | 3002 | Tenant admin UI |
| Tenant Frontend | 3003 | End-user application |
| PostgreSQL US | 5432 | US region database |
| PostgreSQL EU | 5433 | EU region database |
| pgAdmin | 5050 | Database management UI |
| Redis | 6379 | Cache & sessions |
| Keycloak | 8080 | Identity & access |
| RedisInsight | 8001 | Redis management UI |

## Essential Practices

1. Always implement I/O using async patterns; avoid blocking calls in APIs
2. Use asyncpg for database access in performance paths; follow the repository pattern
3. Keep identity/auth in Keycloak and authorization/permissions in PostgreSQL
4. Cache aggressively with Redis and implement explicit invalidation flows
5. Use Pydantic models and full type hints across services
6. Prefer UUIDv7 for identifiers to improve index locality and ordering
7. Use structured logging with tenant_id, user_id, and request_id context
8. Never expose internal details in error responses; map to safe messages
9. Adhere to feature modularity; keep features self-contained
10. Never commit directly to main; use branches and PRs with checks
11. **Use neo-commons shared library** - Eliminate code duplication across services
12. **Follow Clean Architecture** - Domain/Application/Infrastructure layer separation
13. **Protocol-based dependency injection** - Use @runtime_checkable Protocol interfaces

### Multi-Region Database Architecture

```
US East Region (Primary):
- neofast_admin (Global platform management)
- neofast_shared_us (Tenant templates)
- neofast_analytics_us (Analytics)

EU West Region (GDPR):
- neofast_shared_eu (Tenant templates)
- neofast_analytics_eu (Analytics)
```

## Common Development Commands

### Infrastructure Management

```bash
# Deploy complete infrastructure with migrations
cd NeoInfrastructure
./deploy.sh                    # Deploy infrastructure + run migrations
./deploy.sh --seed            # Deploy + seed initial data

# Alternative deployment from root
./deploy.dev.sh               # Master deployment script

# Infrastructure control
./stop.sh                     # Stop all services
./reset.sh                    # Reset and rebuild everything

# View logs
docker-compose -f docker/docker-compose.infrastructure.yml logs -f
docker-compose -f migrations/docker-compose.api.yml logs -f
```

### Database Migrations

```bash
cd NeoInfrastructure/migrations

# Deploy all migrations (automated via API)
# Migrations run automatically when starting the deployment API

# Manual migration commands (if needed)
docker exec neo-deployment-api python /app/orchestrator/enhanced_migration_manager.py

# Check migration status
curl http://localhost:8000/api/v1/migrations/status

# View Flyway migration history
docker exec neo-postgres-us-east psql -U postgres -d neofast_admin -c "SELECT * FROM flyway_schema_history ORDER BY installed_rank;"
```

### Running Tests

```bash
# Infrastructure tests
cd NeoInfrastructure
pytest migrations/tests/

# API tests (when services are implemented)
cd NeoAdminApi
pytest tests/

cd NeoTenantApi  
pytest tests/

# Frontend tests
cd NeoAdmin
npm test
npm run test:e2e

cd NeoTenantFrontend
npm test
npm run test:e2e
```

## Keycloak Integration (High-Level)

- Prefer multi-realm (one realm per tenant) for strong isolation in enterprise setups
- Never use the master realm for application users
- Cache realm public keys and verify tokens per-tenant context
- Sync basic user data into PostgreSQL upon authentication; keep tenant_id authoritative
- Load permissions from DB (roles, direct, team) and cache in Redis per-tenant

### Deployment API Endpoints

The Deployment API (port 8000) provides programmatic control over migrations:

```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Migration status
curl http://localhost:8000/api/v1/migrations/status

# Apply migrations
curl -X POST http://localhost:8000/api/v1/migrations/apply

# Dynamic migration status
curl http://localhost:8000/api/v1/migrations/dynamic/status

# Apply dynamic migrations
curl -X POST http://localhost:8000/api/v1/migrations/dynamic/apply
```

### API Test Users

Use these users to test the API endpoints:

```bash
Super Admin:
username: test
password: 12345678

Platform Admin:
username: musab
password: 12345678
```


### Development Workflow

```bash
# Start only infrastructure
cd NeoInfrastructure
./scripts/start-infrastructure.sh

# Fix common issues
./scripts/keycloak/fix-keycloak-ssl.sh       # SSL issues
./scripts/keycloak/keycloak-disable-ssl.sh   # Disable SSL for dev

# Health checks
./scripts/utilities/health-check.sh
./scripts/utilities/verify-schema-separation.sh

# Run seed data separately
./scripts/deployment/run-seeds.sh

# Check container logs
docker logs neo-deployment-api -f
docker logs neo-postgres-us-east -f
docker logs neo-keycloak -f
```

## Code Architecture

### Database Structure

The platform uses Flyway for enterprise-grade migration management with Python orchestration:

#### Migration Organization
- **Admin Migrations** (`flyway/admin/`): Platform-wide admin database (V1001-V1008)
- **Platform Common** (`flyway/platform/`): Common functions and types (V0001)
- **Regional Migrations** (`flyway/regional/`): Region-specific databases
  - `shared/`: Tenant template schemas (V2001)
  - `analytics/`: Analytics databases (V3001)

#### Key Admin Tables
- `admin.regions`: Geographic deployment regions
- `admin.database_connections`: Central database registry
- `admin.organizations`: Customer organizations
- `admin.tenants`: Tenant instances with region assignment
- `admin.subscription_plans`: Available plans and features
- `admin.platform_users`: Platform administrators
- `admin.platform_roles`: System-wide roles and permissions

#### Tenant Template Schema
- `tenant_template.users`: Tenant users with Keycloak integration
- `tenant_template.roles`: Tenant-specific roles
- `tenant_template.permissions`: Fine-grained permissions
- `tenant_template.teams`: Hierarchical team structure

### Service Architecture Patterns

#### API Services (FastAPI)
- Use asyncpg for database operations (no ORMs for performance)
- Repository pattern for data access
- Service layer for business logic
- Comprehensive error handling
- Structured logging with context

#### Frontend Services (React/Next.js)
- TypeScript for type safety
- Component-based architecture
- State management (Redux/Zustand)
- API client with interceptors
- Responsive design with Tailwind CSS

### Security Considerations

- **Never use Keycloak master realm** for application users
- **All database connections** managed via admin.database_connections table
- **Tenant isolation** enforced at database and API levels
- **JWT validation** with realm-specific public keys
- **Audit logging** for all sensitive operations

## Neo-Commons Shared Library

**neo-commons** is the enterprise-grade shared library that eliminates code duplication across all NeoMultiTenant services. It implements Clean Architecture principles, SOLID design patterns, and protocol-based dependency injection for maximum reusability and performance.

### Core Purpose & Benefits

- **Code Reusability**: Single source of truth for authentication, caching, database operations, and utilities
- **Performance First**: Sub-millisecond permission checks with intelligent caching
- **Clean Architecture**: Domain/Application/Infrastructure layer separation with clear boundaries
- **Protocol-Based Design**: @runtime_checkable Protocol interfaces for maximum flexibility
- **Enterprise Standards**: Follows all CLAUDE.md requirements for file size, function size, and type coverage

### Library Structure

```
neo-commons/
├── domain/                  # Enterprise business rules
│   ├── entities/           # Core business objects (User, Tenant, Permission)
│   ├── value_objects/      # Immutable value types (UserId, TenantId)
│   └── protocols/          # Domain contracts and interfaces
├── application/            # Application business rules
│   ├── services/           # Use cases and workflows
│   ├── commands/           # Command handlers (CQRS pattern)
│   └── queries/            # Query handlers (CQRS pattern)  
├── infrastructure/         # External concerns
│   ├── database/           # AsyncPG repository implementations
│   ├── cache/              # Redis caching with tenant isolation
│   ├── external/           # Keycloak and third-party integrations
│   └── messaging/          # Event and messaging systems
└── interfaces/             # Interface adapters
    ├── api/                # FastAPI dependency injection
    ├── cli/                # Command-line interfaces
    └── web/                # Web-specific adapters
```

### Key Features & Patterns

#### 1. Protocol-Based Dependency Injection
```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AuthRepository(Protocol):
    async def get_user_permissions(self, user_id: str, tenant_id: str) -> list[Permission]:
        """Get user permissions with sub-millisecond caching."""
        
@runtime_checkable
class CacheService(Protocol):
    async def get(self, key: str, tenant_id: str) -> str | None:
        """Get cached value with tenant isolation."""
        
    async def set(self, key: str, value: str, tenant_id: str, ttl: int = 3600) -> None:
        """Set cached value with automatic invalidation."""
```

#### 2. Sub-Millisecond Performance Patterns
```python
# Intelligent permission caching with Redis
class PermissionService:
    async def check_permission(self, user_id: str, resource: str, action: str, tenant_id: str) -> bool:
        # Check cache first (<0.1ms)
        cache_key = f"perm:{tenant_id}:{user_id}:{resource}:{action}"
        cached_result = await self.cache.get(cache_key, tenant_id)
        
        if cached_result is not None:
            return cached_result == "true"
            
        # Fallback to database with prepared statements (<0.5ms)
        has_permission = await self.auth_repo.check_permission(user_id, resource, action, tenant_id)
        await self.cache.set(cache_key, str(has_permission), tenant_id, ttl=300)
        return has_permission
```

#### 3. Clean Architecture Layers
- **Domain Layer**: Pure business logic with no external dependencies
- **Application Layer**: Orchestrates domain objects and implements use cases
- **Infrastructure Layer**: Implements external concerns (database, cache, Keycloak)
- **Interface Layer**: Adapters for web frameworks, CLI tools, and external systems

#### 4. Feature Modularity
Each domain is completely self-contained:
```python
# Authentication domain
from neo_commons.auth import AuthService, AuthRepository, TokenValidator
from neo_commons.auth.dependencies import get_auth_service

# Caching domain  
from neo_commons.cache import CacheService, RedisCache
from neo_commons.cache.dependencies import get_cache_service

# Database domain
from neo_commons.database import Repository, AsyncPGRepository
from neo_commons.database.dependencies import get_db_connection
```

### Migration & Integration Guidelines

#### From NeoAdminApi to neo-commons Pattern
```python
# Before (tightly coupled)
from auth.services.auth_service import AuthService
from cache.redis_client import RedisClient

# After (protocol-based)  
from neo_commons.auth import AuthService
from neo_commons.cache import CacheService
from neo_commons.dependencies import get_auth_service, get_cache_service

# Dependency injection in FastAPI
@app.get("/users/{user_id}/permissions")
async def get_permissions(
    user_id: str,
    auth_service: AuthService = Depends(get_auth_service),
    cache_service: CacheService = Depends(get_cache_service)
):
    return await auth_service.get_user_permissions(user_id, tenant_id)
```

#### Performance Integration Patterns
```python
# Sub-millisecond permission decorator
@permission_required("users:read", cache_ttl=300)
async def get_user(user_id: str, context: RequestContext):
    # Permission check happens in <1ms via cache
    return await user_service.get_user(user_id, context.tenant_id)

# Intelligent caching with invalidation
@cache_result(key_pattern="user:{tenant_id}:{user_id}", ttl=3600)
async def get_user_profile(user_id: str, tenant_id: str):
    # Automatic cache invalidation on user updates
    return await user_repository.get_user_profile(user_id, tenant_id)
```

### CLAUDE.md Compliance Audit Results

**File Size Compliance (Critical)**:
- ✅ **Target**: All files ≤ 400 lines  
- ❌ **Current**: 14 files exceed limit (largest: 1331 lines)
- 🔧 **Action Required**: Split oversized files using Clean Architecture patterns

**Function Size Compliance**:
- ✅ **Target**: All functions ≤ 80 lines
- 🔍 **Status**: Audit in progress
- 📊 **Quality Score**: 85-98/100 across migrated files

**Architecture Compliance**:
- ✅ **Protocol-based dependency injection**: Implemented throughout
- ✅ **Clean Architecture layers**: Domain/Application/Infrastructure separation  
- ✅ **SOLID Principles**: Single Responsibility enforced per module
- ✅ **Type Coverage**: 100% type hints with Pydantic models
- ✅ **Async Patterns**: All I/O operations are async
- ✅ **UUIDv7 Usage**: Time-ordered identifiers for performance

### Specialized Neo-Commons Reorganizer Agent

The platform includes a specialized agent (`.claude/agents/analysis/neo-commons-reorganizer.md`) that:

- **Analyzes file size violations** and creates splitting strategies
- **Enforces SOLID principles** through automated refactoring suggestions  
- **Implements Clean Architecture** with proper layer separation
- **Validates performance requirements** for sub-millisecond operations
- **Coordinates with other agents** for comprehensive code quality

#### Agent Integration Commands
```bash
# Trigger reorganization analysis
claude-flow agent activate neo-commons-reorganizer "analyze file size violations"

# Run comprehensive CLAUDE.md compliance audit  
claude-flow agent activate neo-commons-reorganizer "audit SOLID principles compliance"

# Execute Clean Architecture migration
claude-flow agent activate neo-commons-reorganizer "implement Clean Architecture layers"
```

### Integration Timeline & Milestones

#### Phase 1: Foundation (Completed)
- ✅ Created neo-commons package structure
- ✅ Migrated 29 core modules with protocol-based interfaces  
- ✅ Implemented packaging (pyproject.toml, setup.py)
- ✅ Created comprehensive documentation

#### Phase 2: Compliance & Optimization (Current)
- 🔄 **File Size Compliance**: Split 14 oversized files into focused modules
- 🔄 **Function Size Audit**: Ensure all functions ≤ 80 lines
- 🔄 **Clean Architecture**: Implement domain/application/infrastructure layers
- 🔄 **Performance Validation**: Ensure sub-millisecond permission checks

#### Phase 3: Service Integration (Planned)  
- 📋 **NeoAdminApi Integration**: Replace internal modules with neo-commons
- 📋 **NeoTenantApi Integration**: Unified authentication and caching
- 📋 **Testing & Validation**: Comprehensive test coverage
- 📋 **Performance Benchmarking**: Validate <1ms permission check requirements

### Best Practices for neo-commons Usage

1. **Always import from public interfaces**: Use domain-specific imports, not internal modules
2. **Follow protocol-based patterns**: Depend on Protocol interfaces, not concrete implementations  
3. **Respect Clean Architecture boundaries**: Don't import infrastructure from domain layer
4. **Cache aggressively with tenant isolation**: Use provided caching decorators and patterns
5. **Validate performance requirements**: Monitor sub-millisecond permission check targets
6. **Use provided dependency injection**: Leverage FastAPI dependencies for loose coupling
7. **Follow UUIDv7 patterns**: Use library utilities for time-ordered identifiers
8. **Implement structured logging**: Include tenant_id, user_id, request_id context

## Important Implementation Notes

### Database Connection Management
Only the admin database connection is configured in environment variables. All other database connections (regional, analytics, tenant-specific) are dynamically managed through the `admin.database_connections` table for:
- Centralized credential management
- Health monitoring and failover
- Dynamic scaling without restarts
- Multi-region intelligent routing

### Migration Execution
The system uses a **two-phase migration approach**:

**Phase 1 - Startup Migrations (Automatic)**:
- Runs automatically when deployment API starts
- Handles admin database only: platform_common + admin schemas
- Uses Flyway configuration files in `/app/flyway/conf/`

**Phase 2 - Dynamic Migrations (API-triggered)**:
- Handles ALL regional databases (shared + analytics)
- Uses dynamic configuration from `admin.database_connections` table
- Dependency resolver ensures correct order: platform_common → tenant_template
- Triggered via: `POST /api/v1/migrations/dynamic`

**Key API Endpoints**:
- Admin migrations status: `GET /api/v1/migrations/status`
- Dynamic migrations: `POST /api/v1/migrations/dynamic`
- Migration status: `GET /api/v1/migrations/dynamic/status`
- Tenant migrations: `POST /api/v1/tenants/{tenant_id}/migrate`

### Migration Files Naming Convention
- **V0001-V0999**: Platform common schemas and functions
- **V1001-V1999**: Admin database schemas
- **V2001-V2999**: Regional shared databases
- **V3001-V3999**: Analytics databases
- **V4001+**: Future expansion

### Multi-Tenancy Strategies
1. **Schema-based**: Each tenant gets a PostgreSQL schema in shared database
2. **Database-based**: Each tenant gets dedicated database
3. **Hybrid**: Mix based on tenant tier and requirements

### Keycloak Integration
- **Multi-Realm Mode**: One realm per tenant (enterprise)
- **Realm Pattern**: `tenant-{slug}` (e.g., tenant-acme)
- **User Sync**: Automatic sync to PostgreSQL on authentication
- **Permission Loading**: Cached in Redis with tenant isolation

## Development Best Practices

1. **Always check existing patterns** before implementing new features
2. **Use neo-commons first** - Check if functionality exists in shared library before creating new code
3. **Use UUIDv7** for all UUID generation (time-ordered)
4. **Follow async patterns** throughout the codebase
5. **Implement comprehensive error handling** with appropriate status codes
6. **Add structured logging** with tenant_id, user_id, request_id context
7. **Write tests** for all new functionality
8. **Update migrations** using Flyway naming conventions (V{number}__{description}.sql)
9. **Validate inputs** using Pydantic models
10. **Cache aggressively** but implement proper invalidation
11. **Document API endpoints** with OpenAPI/Swagger
12. **Follow Clean Architecture** - Respect domain/application/infrastructure boundaries
13. **Use Protocol interfaces** - Depend on contracts, not implementations
14. **Enforce file size limits** - Split files exceeding 400 lines using SOLID principles
15. **Validate performance requirements** - Monitor sub-millisecond permission check targets

## Quick Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL status
docker ps | grep postgres
docker exec neo-postgres-us-east pg_isready -U postgres

# View connection logs
docker logs neo-postgres-us-east
```

### Migration Issues
```bash
# Check migration status via API
curl http://localhost:8000/api/v1/migrations/status

# View Flyway history
docker exec neo-postgres-us-east psql -U postgres -d neofast_admin \
  -c "SELECT version, description, success FROM flyway_schema_history ORDER BY installed_rank DESC LIMIT 10;"

# Check API logs
docker logs neo-deployment-api
```

### Redis Issues
```bash
# Test Redis connection
docker exec neo-redis redis-cli -a redis ping

# Clear cache if needed
docker exec neo-redis redis-cli -a redis FLUSHDB
```

### Keycloak Issues
```bash
# Check Keycloak status
curl http://localhost:8080/health/ready

# Fix SSL issues
cd NeoInfrastructure
./scripts/keycloak/fix-keycloak-ssl.sh
```

### Deployment API Issues
```bash
# Check API status
curl http://localhost:8000/health

# View API logs
docker logs neo-deployment-api -f

# Restart API if needed
cd NeoInfrastructure/migrations
docker-compose -f docker-compose.api.yml restart
```

## Environment Variables

The infrastructure uses the following key environment variables (set in `.env`):

```bash
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_US_PORT=5432
POSTGRES_EU_PORT=5433

# Redis
REDIS_PORT=6379
REDIS_PASSWORD=redis

# Keycloak
KEYCLOAK_PORT=8080
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=admin

# API Services (when deployed)
ADMIN_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/neofast_admin
```

## Security Checklist

- [ ] Validate all inputs with Pydantic; enforce strict constraints
- [ ] Use parameterized queries only; never format SQL with user input
- [ ] Enforce authorization at repository/service boundary
- [ ] Rate limit public endpoints where appropriate
- [ ] Write audit logs for sensitive operations (creation, deletion, access changes)
- [ ] Avoid leaking sensitive info in errors or logs; no PII in logs
- [ ] Implement cache invalidation for any write path affecting cached reads
- [ ] Define transaction boundaries; rollback on exceptions

## Performance Targets

- Permission checks: < 1ms with cache
- API p95 latency: < 100ms
- Simple queries: < 10ms; complex queries: < 50ms
- Cache hit rate for permissions: > 90%

## UUIDv7 Guidance

- Use UUIDv7 for identifiers to achieve time-ordered IDs improving index performance
- Provide centralized utilities for generating UUIDv7 and extracting timestamps
- Avoid using uuid4 directly in new code paths

## Git Usage Rules

1. Never work directly on `main`; create feature branches: `[type]/[description]-[ticket]`
   - Examples: `feat/user-auth-JIRA-123`, `fix/cache-invalidation-JIRA-456`, `refactor/db-ops-JIRA-789`
2. Run tests, lint, and type checks before committing
3. Use conventional commits (feat, fix, refactor, docs, test, chore)
4. Keep commits small and focused; include context in body when needed
5. Rebase feature branches on latest main before PR; resolve conflicts locally
6. PRs must include change summary, tests, and any breaking change notes
7. Forbidden: force-push to main, merge without review, committing secrets/large binaries

## Production Checklist (High-Level)

- [ ] All Flyway migrations applied (admin, regional, tenant template)
- [ ] Keycloak realms configured per-tenant; master realm not used
- [ ] Public keys caching/rotation strategy established
- [ ] Redis configured with persistence and appropriate eviction policy
- [ ] Backups and disaster recovery plans tested (DB + Keycloak)
- [ ] Monitoring (metrics/logging/health) wired and alerting configured
- [ ] Security scans and load tests completed for expected scale

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
Never save working files, text/mds and tests to the root folder.