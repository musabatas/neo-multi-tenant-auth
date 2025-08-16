# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**NeoMultiTenant** - Enterprise-grade multi-tenant platform built with Python FastAPI, PostgreSQL 17+, Redis, and Keycloak. Features ultra-scalability, comprehensive RBAC with custom permissions, and sub-millisecond permission checks.

### Technology Stack
- **API**: Python 3.13+ with FastAPI (async)
- **Authentication**: Keycloak (external IAM) with automatic user ID mapping
- **Database**: PostgreSQL 17+ with asyncpg
- **Caching**: Redis with automatic invalidation
- **RBAC**: Custom PostgreSQL-based with intelligent caching

### Essential Practices
1. **Always use neo-commons first** - Check shared library before creating new functionality
2. **Protocol-based dependency injection** - Use @runtime_checkable Protocol interfaces
3. **Follow Clean Architecture** - Domain/Application/Infrastructure/Interface layer separation
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

**neo-commons** is the enterprise-grade shared library providing unified authentication, caching, and utilities across all services. **NeoAdminApi is fully integrated** with automatic Keycloak-to-platform user ID mapping.

### Key Integration Features

- ✅ **Automatic User ID Mapping**: Seamless bridge between Keycloak and platform identities
- ✅ **Multi-layer Fallback**: Works with both Keycloak and platform user IDs  
- ✅ **Sub-millisecond Performance**: Intelligent caching with tenant isolation
- ✅ **Protocol-Based Design**: @runtime_checkable interfaces for flexibility
- ✅ **FastAPI Integration**: Direct dependency injection for route protection

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

### Implementation Examples

#### User ID Mapping Architecture
```python
# Automatic Keycloak-to-platform user ID mapping
class NeoAdminPermissionChecker:
    async def _resolve_user_id(self, user_id: str) -> str:
        # Try platform user ID first
        try:
            await self.auth_repo.get_user_by_id(user_id)
            return user_id
        except:
            # Map from Keycloak ID
            platform_user = await self.auth_repo.get_user_by_external_id(
                provider="keycloak", external_id=user_id
            )
            return platform_user['id']
```

#### FastAPI Route Protection
```python
from src.features.auth.dependencies import CheckPermission

@router.get("/users")
async def list_users(
    current_user: dict = Depends(CheckPermission(["users:list"]))
):
    # Automatic user ID resolution and permission checking
    return await user_service.list_users()
```

### Current Issues & Next Steps

#### Critical Issues to Fix
- ❌ **Repository Layer**: 100+ hardcoded schema references need dynamic configuration
- ❌ **Config Module**: Service-specific values need to be removed

#### Integration Status
- ✅ **NeoAdminApi**: Fully integrated with user ID mapping
- 📋 **NeoTenantApi**: Pending integration
- 📋 **Performance**: Sub-millisecond targets validated


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

1. **Always use neo-commons first** - Check shared library before creating new functionality
2. **Use Protocol interfaces** - Depend on contracts, not implementations
3. **Configure schemas dynamically** - Never hardcode database schema names
4. **Follow Clean Architecture** - Respect domain/application/infrastructure/interface boundaries
5. **Use UUIDv7** for all UUID generation (time-ordered)
6. **Follow async patterns** throughout the codebase
7. **Implement comprehensive error handling** with appropriate status codes
8. **Add structured logging** with tenant_id, user_id, request_id context
9. **Write tests** for all new functionality using protocol mocks
10. **Update migrations** using Flyway naming conventions (V{number}__{description}.sql)
11. **Validate inputs** using Pydantic models
12. **Cache aggressively** but implement proper invalidation
13. **Document API endpoints** with OpenAPI/Swagger
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

## Important Reminders

**CRITICAL**: Always use neo-commons first before creating new functionality.

### Development Standards
- Do what has been asked; nothing more, nothing less
- NEVER create files unless they're absolutely necessary
- ALWAYS prefer editing existing files over creating new ones
- NEVER proactively create documentation files (*.md)
- Never save working files to the root folder
- Always check neo-commons first before implementing new functionality

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
- When checking implementations, be specific about what you're looking for to get accurate results # Using Gemini CLI for Large Codebase Analysis


When analyzing large codebases or multiple files that might exceed context limits, use the Gemini CLI with its massive context window. Use `gemini -p` to leverage Google Gemini's large context capacity.


  ## File and Directory Inclusion Syntax


  Use the `@` syntax to include files and directories in your Gemini prompts. The paths should be relative to WHERE you run the
   gemini command:


  ### Examples:


  **Single file analysis:**
  ```bash
  gemini -p "@src/main.py Explain this file's purpose and structure"


  Multiple files:
  gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"


  Entire directory:
  gemini -p "@src/ Summarize the architecture of this codebase"


  Multiple directories:
  gemini -p "@src/ @tests/ Analyze test coverage for the source code"


  Current directory and subdirectories:
  gemini -p "@./ Give me an overview of this entire project"
  # Or use --all_files flag:
  gemini --all_files -p "Analyze the project structure and dependencies"


  Implementation Verification Examples


  Check if a feature is implemented:
  gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"


  Verify authentication implementation:
  gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"


  Check for specific patterns:
  gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"


  Verify error handling:
  gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"


  Check for rate limiting:
  gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"


  Verify caching strategy:
  gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"


  Check for specific security measures:
  gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"


  Verify test coverage for features:
  gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"


  When to Use Gemini CLI


  Use gemini -p when:
  - Analyzing entire codebases or large directories
  - Comparing multiple large files
  - Need to understand project-wide patterns or architecture
  - Current context window is insufficient for the task
  - Working with files totaling more than 100KB
  - Verifying if specific features, patterns, or security measures are implemented
  - Checking for the presence of certain coding patterns across the entire codebase


  Important Notes


  - Paths in @ syntax are relative to your current working directory when invoking gemini
  - The CLI will include file contents directly in the context
  - No need for --yolo flag for read-only analysis
  - Gemini's context window can handle entire codebases that would overflow Claude's context
  - When checking implementations, be specific about what you're looking for to get accurate results