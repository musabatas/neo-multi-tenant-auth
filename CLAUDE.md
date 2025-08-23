# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NeoMultiTenant** - Enterprise-grade multi-tenant platform built with Python FastAPI, PostgreSQL 17+, Redis, and Keycloak. Features ultra-scalability, comprehensive RBAC with custom permissions, and sub-millisecond permission checks.

### Technology Stack
- **API**: Python 3.13+ with FastAPI (async)
- **Authentication**: Keycloak (external IAM) with automatic user ID mapping
- **Database**: PostgreSQL 17+ with asyncpg
- **Caching**: Redis with automatic invalidation
- **RBAC + Permissions**: Custom PostgreSQL-based with intelligent caching. Permission-Based Access Control (PBAC)

### Essential Practices
1. **Always use neo-commons first** - Check shared library before creating new functionality
2. **Protocol-based dependency injection** - Use @runtime_checkable Protocol interfaces
3. **Follow Feature-First + Clean Core** - Feature modules with Clean Core containing only value objects, exceptions, and shared contracts
4. **Use asyncpg** for database operations, never use ORMs for performance paths
5. **Configure schemas dynamically** - Never hardcode database schema names
6. **Use UUIDv7** for all UUID generation (time-ordered)
7. **Handle user ID mapping** - Automatic Keycloak-to-platform user ID resolution
8. **Cache aggressively** - Redis for permissions with proper invalidation
9. **Use structured logging** - Include tenant_id, user_id, request_id context
10. **Never commit to main** - Always work in feature branches and create PRs

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

**neo-commons** is the enterprise-grade shared library providing unified database, authentication, and utilities. **NeoAdminApi is fully integrated** with automatic connection management and password encryption.

### Current Integration Status

- ✅ **Database Service**: Auto-loads connections from admin.database_connections table on startup
- ✅ **Connection Management**: Centralized registry with health monitoring and failover
- ✅ **Password Encryption**: Automatic Fernet encryption/decryption for database passwords
- ✅ **Protocol-Based Design**: @runtime_checkable interfaces for dependency injection
- ⚠️ **Authentication**: Available but not yet integrated (auth disabled in AdminAPI)

### Library Structure (Feature-First + Clean Core Architecture)

```
neo-commons/
├── core/                    # Clean Core - Only value objects, exceptions & shared contracts
│   ├── value_objects/      # Immutable types (UserId, TenantId, PermissionCode)
│   ├── exceptions/         # Domain exceptions and HTTP mapping
│   └── shared/             # Cross-cutting domain objects (RequestContext)
├── features/               # Feature-First - Business capabilities
│   ├── cache/              # Cache management feature
│   │   ├── entities/       # Cache domain entities and protocols
│   │   ├── services/       # Cache business logic
│   │   └── adapters/       # Redis/Memory cache implementations
│   ├── database/           # Database management feature  
│   │   ├── entities/       # Connection entities and protocols
│   │   ├── services/       # Database orchestration
│   │   └── repositories/   # AsyncPG implementations
│   ├── permissions/        # RBAC permission system
│   │   ├── entities/       # Permission/Role domain entities
│   │   ├── services/       # Permission checking logic
│   │   └── repositories/   # Permission data access
│   ├── users/              # User management
│   ├── organizations/      # Organization management
│   ├── tenants/            # Tenant management  
│   └── teams/              # Team management
├── infrastructure/         # Infrastructure-level concerns
│   ├── configuration/      # Application configuration management
│   ├── middleware/         # FastAPI middleware for cross-cutting concerns
│   ├── database/           # Low-level database utilities
│   └── protocols/          # Infrastructure contracts
├── config/                 # Configuration management (legacy - being phased out)
└── utils/                  # Utility functions (UUIDv7, etc.)
```

### Architecture Design Principles

#### Feature-First Organization
- **Feature Modules**: Each business capability (cache, database, permissions) is self-contained
- **Clean Boundaries**: Features communicate through well-defined protocols and shared value objects
- **Domain-Driven**: Features follow DDD patterns with entities, services, and repositories

#### Clean Core Pattern
- **Minimal Core**: Core contains only essential value objects, exceptions, and shared contracts
- **No Business Logic**: Core has no feature-specific logic or external dependencies  
- **Dependency Direction**: Features depend on core, never the reverse

#### Protocol-Based Integration
- **@runtime_checkable Protocols**: Enable flexible dependency injection and testing
- **Contract Separation**: Domain protocols in entities, infrastructure protocols in infrastructure
- **Implementation Independence**: Swap implementations without changing business logic

### Database Usage (Current Implementation)

#### Get Database Service
```python
from ....common.dependencies import get_database_service

@router.get("/data")
async def get_data(db_service = Depends(get_database_service)):
    # Database service is auto-configured with all connections
    connections = await db_service.connection_registry.get_all_connections()
    return {"total_connections": len(connections)}
```

#### Execute Database Queries
```python
# Get specific connection and execute queries
async with db_service.get_connection("admin") as conn:
    result = await conn.fetchrow("SELECT * FROM admin.organizations WHERE id = $1", org_id)
    return dict(result) if result else None

# Use connection manager for multiple operations
connection_manager = db_service.connection_manager
results = await connection_manager.execute_query("admin", "SELECT COUNT(*) FROM admin.tenants")
```

#### Environment Configuration
```bash
# .env file - SSL disabled for development
ADMIN_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/neofast_admin?sslmode=disable"
DB_ENCRYPTION_KEY="your-32-char-encryption-key"
```

#### Available Connections
- **admin**: Main admin database (auto-loaded from environment)
- **neofast-admin-primary**: Docker admin database  
- **neofast-shared-us-primary**: US region shared database
- **neofast-shared-eu-primary**: EU region shared database
- **neofast-analytics-us**: US analytics database
- **neofast-analytics-eu**: EU analytics database

### Current Service Architecture

**NeoAdminApi Services**:
- **Database Service**: Singleton pattern with auto-loading, health monitoring, connection pooling
- **Organization Service**: Uses database dependency injection with repository pattern  
- **System Service**: Health checks, connection management, cache operations

**Implementation Pattern**:
```python
# Service with dependency injection
async def get_organization_service():
    database_service = await get_database_service()
    repository = OrganizationRepository(database_service)
    return OrganizationService(repository)
```

### Neo-Commons Development Patterns

#### Creating New Features
```python
# 1. Create feature directory structure
features/
├── my_feature/
│   ├── entities/          # Domain objects and protocols
│   ├── services/          # Business logic
│   ├── repositories/      # Data access (if needed)
│   └── __init__.py        # Export public interface

# 2. Define domain entities with protocols
@dataclass
class MyEntity:
    id: EntityId
    name: str

@runtime_checkable  
class MyEntityRepository(Protocol):
    async def save(self, entity: MyEntity) -> MyEntity: ...

# 3. Implement service with dependency injection
class MyFeatureService:
    def __init__(self, repository: MyEntityRepository):
        self._repository = repository
```

#### Adding to Existing Features
```python
# Always check existing feature structure first
from neo_commons.features.permissions.entities import Permission
from neo_commons.features.permissions.services import PermissionService

# Extend existing services, don't duplicate
class ExtendedPermissionService(PermissionService):
    async def advanced_check(self, ...): ...
```

#### Core Value Objects
```python
# Use existing value objects from core
from neo_commons.core.value_objects import (
    UserId, TenantId, OrganizationId, 
    PermissionCode, RoleCode
)

# Create new value objects only in core/value_objects/
@dataclass(frozen=True)
class NewValueObject:
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Value cannot be empty")
```

### Architecture Implementation Status

#### ✅ Completed (Clean Core + Feature-First)
- **Core Architecture**: Clean Core with value objects, exceptions, shared contracts
- **Feature Organization**: 6 feature modules (cache, database, permissions, users, organizations, teams)
- **Protocol-Based Design**: @runtime_checkable protocols for dependency injection
- **Import Structure**: Validated import paths and circular dependency prevention

#### 🔄 In Progress  
- **Configuration Migration**: Moving from legacy config/ to infrastructure/configuration/
- **Repository Modernization**: Updating hardcoded schema references to dynamic configuration
- **Service Integration**: Full feature service integration across all APIs

#### 📋 Next Steps
- **NeoTenantApi Integration**: Implement feature-based architecture
- **Performance Validation**: Sub-millisecond permission check targets
- **Legacy Cleanup**: Remove deprecated config patterns


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

### Neo-Commons Architecture Rules
1. **Always use neo-commons first** - Check shared library before creating new functionality
2. **Follow Feature-First organization** - Business logic belongs in feature modules, not core
3. **Use Protocol interfaces** - Depend on @runtime_checkable contracts, not implementations  
4. **Respect Clean Core boundaries** - Core only contains value objects, exceptions, shared contracts
5. **Import from features** - Import entities and services from feature modules, not core
6. **Use infrastructure middleware** - FastAPI apps should use pre-built middleware stack

### Technical Standards
6. **Configure schemas dynamically** - Never hardcode database schema names
7. **Use UUIDv7** for all UUID generation (time-ordered)
8. **Follow async patterns** throughout the codebase
9. **Implement comprehensive error handling** with appropriate status codes
10. **Add structured logging** with tenant_id, user_id, request_id context
11. **Write tests** for all new functionality using protocol mocks
12. **Update migrations** using Flyway naming conventions (V{number}__{description}.sql)
13. **Validate inputs** using Pydantic models
14. **Cache aggressively** but implement proper invalidation
15. **Document API endpoints** with OpenAPI/Scalar following tag naming conventions
16. **Use consistent OpenAPI tag naming** - Follow standardized tag organization and naming
17. **Enforce file size limits** - Split files exceeding 400 lines using SOLID principles
18. **Validate performance requirements** - Monitor sub-millisecond permission check targets

### Feature Development Guidelines
19. **Feature Isolation** - Features should be self-contained with minimal cross-feature dependencies
20. **Protocol Contracts** - Define protocols in entities/ for domain contracts, infrastructure/ for technical contracts  
21. **Service Orchestration** - Complex workflows belong in feature services, not repositories
22. **Repository Focus** - Repositories handle only data access, no business logic
23. **Entity Validation** - Domain validation belongs in entities, technical validation in infrastructure

### OpenAPI Tag Naming & Organization Standards

**Tag Naming Convention:**
- **First letter capitalized** for all tags (e.g., "System", "Database", "Authentication")
- **Use singular form** unless referring to collections (e.g., "User" not "Users", but "Organizations" for multiple orgs)
- **Be descriptive and specific** (e.g., "Database Management" not just "DB")
- **Follow domain-driven naming** aligned with feature boundaries

**Tag Organization Hierarchy:**
```yaml
# Core Platform Tags (Administrative)
- System           # Health, info, maintenance endpoints
- Database         # Connection management, stats
- Cache            # Cache management and operations  
- Authentication   # Auth, tokens, session management
- Authorization    # Permissions, roles, RBAC

# Business Domain Tags  
- Organizations    # Organization management
- Tenants         # Tenant administration and operations
- Users           # User management (platform and tenant)
- Teams           # Team structures and hierarchies
- Subscriptions   # Billing, plans, quotas

# Integration Tags
- Webhooks        # Webhook management and delivery
- Notifications   # Email, SMS, push notifications
- Reports         # Analytics and reporting
- Audit           # Audit logs and compliance
```

**Tag Grouping with x-tag-groups Extension:**
```yaml
x-tag-groups:
  - name: "Platform Administration"
    tags: ["System", "Database", "Cache", "Authentication", "Authorization"]
  - name: "Business Operations" 
    tags: ["Organizations", "Tenants", "Users", "Teams", "Subscriptions"]
  - name: "Integrations & Monitoring"
    tags: ["Webhooks", "Notifications", "Reports", "Audit"]
```

**Implementation Rules:**
- Router files define tags using `tags=["TagName"]` parameter
- Main API includes `x-tag-groups` in OpenAPI configuration
- Tag descriptions should be clear and concise
- Related endpoints grouped under same tag for logical organization

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
KEYCLOAK_PASSWORD=admin

# API Services (when deployed)
ADMIN_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/neofast_admin
```

## Security Checklist

- [ ] **CRITICAL: NEVER use `jwt.decode()` with `verify_signature=False`** - always validate JWT tokens using auth service's `validate_token()` method which checks signature, expiration, and audience against Keycloak
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

## Important Reminders

**CRITICAL**: Always use neo-commons first before creating new functionality.

### Development Standards
- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary
- ALWAYS prefer editing existing files over creating new ones
- NEVER proactively create documentation files (*.md)
- Never save working files to the root folder
- Always check neo-commons first before implementing new functionality

### Neo-Commons Architecture Reminders
- **Feature-First**: Business logic goes in feature modules (cache, database, permissions, etc.)
- **Clean Core**: Core only contains value objects, exceptions, and shared contracts
- **Protocol-Based**: Use @runtime_checkable protocols for dependency injection
- **Import Validation**: Import from features, not core (except value objects and exceptions)
- **Configuration**: Use infrastructure/configuration, not legacy config/ module

## AI Agent Guidelines

### Pre-Task Verification (MANDATORY)
**Before starting any implementation task, AI agents MUST:**

1. **Use codebase-db-investigator agent** to analyze existing code patterns and understand current implementation
2. **Verify neo-commons availability** - Check if functionality already exists in shared library before creating new code
3. **Understand database structures** - Review relevant schema files, migrations, and table relationships
4. **Check related imports and dependencies** - Ensure compatibility with existing codebase patterns
5. **Validate file structure** - Understand where new code should be placed following Feature-First + Clean Core architecture

### Post-Task Verification (MANDATORY)
**After completing any implementation, AI agents MUST:**

1. **Verify integration works** - Check that new code integrates properly with existing systems
2. **Validate imports and dependencies** - Ensure all imports resolve correctly and follow project patterns
3. **Test database connectivity** - If database operations were added, verify connections work correctly
4. **Check file organization** - Ensure code is placed in correct feature modules and follows architecture
5. **Validate critical functionality** - Run basic tests to ensure implementation works as expected

### Using codebase-db-investigator Agent

**When to use:**
- Before implementing any new feature or service
- When modifying existing database operations
- When adding new routes or API endpoints
- When refactoring or changing architecture patterns
- When uncertain about existing implementations

**Example usage:**
```bash
# Before implementing user management feature
Task: "Use codebase-db-investigator to analyze existing user-related code in neo-commons and NeoAdminApi. Find all user entities, services, repositories, and database schemas. Identify what's already implemented and what needs to be created."

# Before adding new database connection
Task: "Use codebase-db-investigator to analyze how database connections are currently managed in neo-commons. Show me the connection management patterns, encryption handling, and repository implementations."
```

### Critical Implementation Rules

1. **Never duplicate existing functionality** - Always check neo-commons first
2. **Implement generic/reusable functionality in neo-commons** - If requested task is generic or reusable across services, implement it in neo-commons and use it in the service
3. **Follow existing patterns** - Use codebase-db-investigator to understand current implementation patterns
4. **Respect architecture boundaries** - Features in feature modules, core only for value objects/exceptions
5. **Validate database operations** - Ensure schema names are dynamic, use UUIDv7, follow asyncpg patterns
6. **Update CLAUDE.md only for critical findings** - Add important architectural decisions or patterns that will guide future development

### Knowledge Documentation Rules

**Update CLAUDE.md when discovering:**
- Critical architectural patterns that must be followed
- Important security considerations or constraints
- Database schema relationships that affect multiple features
- Neo-commons integration patterns that weren't documented
- Performance requirements or optimization patterns

**Do NOT update CLAUDE.md for:**
- Routine implementation details
- Temporary workarounds or fixes
- Personal preferences or opinions
- Non-critical code organization choices

 # Using Gemini CLI for Large Codebase Analysis

  When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive
  context window. Use `gemini -p` to leverage Google Gemini's large context capacity.

  ## File and Directory Inclusion Syntax

  Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
   gemini command:

  ### Examples:

  **Single file analysis:**
```bash
gemini -p "@src/main.py Explain this file's purpose and structure"
```
**Multiple files:**
```bash
gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"
```

**Entire directory:**
```bash
gemini -p "@src/ Summarize the architecture of this codebase"
```

**Multiple directories:**
```bash
gemini -p "@src/ @tests/ Analyze test coverage for the source code"
```

**Current directory and subdirectories:**
```bash
gemini -p "@./ Give me an overview of this entire project"
```

Or use --all_files flag:
```bash
gemini --all_files -p "Analyze the project structure and dependencies"
```

**Implementation Verification Examples**

**Check if a feature is implemented:**
```bash
gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"
```

**Verify authentication implementation:**
```bash
gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"
```

**Check for specific patterns:**
```bash
gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"
```

**Verify error handling:**
```bash
gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"
```

**Check for rate limiting:**
```bash
gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"
```

**Verify caching strategy:**
```bash
gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"
```

**Check for specific security measures:**
```bash
gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"
```

**Verify test coverage for features:**
```bash
gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"
```

**When to Use Gemini CLI**

**Use gemini -p when:**
  - Analyzing entire codebases or large directories
  - Comparing multiple large files
  - Need to understand project-wide patterns or architecture
  - Current context window is insufficient for the task
  - Working with files totaling more than 100KB
  - Verifying if specific features, patterns, or security measures are implemented
  - Checking for the presence of certain coding patterns across the entire codebase

**Important Notes**

- Paths in @ syntax are relative to your current working directory when invoking gemini
- The CLI will include file contents directly in the context
- No need for --yolo flag for read-only analysis
- Gemini's context window can handle entire codebases that would overflow Claude's context
- When checking implementations, be specific about what you're looking for to get accurate results