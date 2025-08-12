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

## Important Implementation Notes

### Database Connection Management
Only the admin database connection is configured in environment variables. All other database connections (regional, analytics, tenant-specific) are dynamically managed through the `admin.database_connections` table for:
- Centralized credential management
- Health monitoring and failover
- Dynamic scaling without restarts
- Multi-region intelligent routing

### Migration Execution
Migrations are automatically executed when the deployment API starts:
1. Platform common schema (V0001)
2. Admin database migrations (V1001-V1008)
3. Regional database migrations (V2001, V3001)
4. Tenant schema migrations (dynamically per tenant)

The API provides endpoints for:
- Checking migration status: `GET /api/v1/migrations/status`
- Manual migration triggers: `POST /api/v1/migrations/apply`
- Tenant-specific migrations: `POST /api/v1/tenants/{tenant_id}/migrate`

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
2. **Use UUIDv7** for all UUID generation (time-ordered)
3. **Follow async patterns** throughout the codebase
4. **Implement comprehensive error handling** with appropriate status codes
5. **Add structured logging** with tenant_id, user_id, request_id context
6. **Write tests** for all new functionality
7. **Update migrations** using Flyway naming conventions (V{number}__{description}.sql)
8. **Validate inputs** using Pydantic models
9. **Cache aggressively** but implement proper invalidation
10. **Document API endpoints** with OpenAPI/Swagger

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

# Claude Code Configuration - SPARC Development Environment

## 🚨 CRITICAL: CONCURRENT EXECUTION & FILE MANAGEMENT

**ABSOLUTE RULES**:
1. ALL operations MUST be concurrent/parallel in a single message
2. **NEVER save working files, text/mds and tests to the root folder**
3. ALWAYS organize files in appropriate subdirectories

### ⚡ GOLDEN RULE: "1 MESSAGE = ALL RELATED OPERATIONS"

**MANDATORY PATTERNS:**
- **TodoWrite**: ALWAYS batch ALL todos in ONE call (5-10+ todos minimum)
- **Task tool**: ALWAYS spawn ALL agents in ONE message with full instructions
- **File operations**: ALWAYS batch ALL reads/writes/edits in ONE message
- **Bash commands**: ALWAYS batch ALL terminal operations in ONE message
- **Memory operations**: ALWAYS batch ALL memory store/retrieve in ONE message

### 📁 File Organization Rules

**NEVER save to root folder. Use these directories:**
- `/src` - Source code files
- `/tests` - Test files
- `/docs` - Documentation and markdown files
- `/config` - Configuration files
- `/scripts` - Utility scripts
- `/examples` - Example code

## Project Overview

This project uses SPARC (Specification, Pseudocode, Architecture, Refinement, Completion) methodology with Claude-Flow orchestration for systematic Test-Driven Development.

## SPARC Commands

### Core Commands
- `npx claude-flow sparc modes` - List available modes
- `npx claude-flow sparc run <mode> "<task>"` - Execute specific mode
- `npx claude-flow sparc tdd "<feature>"` - Run complete TDD workflow
- `npx claude-flow sparc info <mode>` - Get mode details

### Batchtools Commands
- `npx claude-flow sparc batch <modes> "<task>"` - Parallel execution
- `npx claude-flow sparc pipeline "<task>"` - Full pipeline processing
- `npx claude-flow sparc concurrent <mode> "<tasks-file>"` - Multi-task processing

### Build Commands
- `npm run build` - Build project
- `npm run test` - Run tests
- `npm run lint` - Linting
- `npm run typecheck` - Type checking

## SPARC Workflow Phases

1. **Specification** - Requirements analysis (`sparc run spec-pseudocode`)
2. **Pseudocode** - Algorithm design (`sparc run spec-pseudocode`)
3. **Architecture** - System design (`sparc run architect`)
4. **Refinement** - TDD implementation (`sparc tdd`)
5. **Completion** - Integration (`sparc run integration`)

## Code Style & Best Practices

- **Modular Design**: Files under 500 lines
- **Environment Safety**: Never hardcode secrets
- **Test-First**: Write tests before implementation
- **Clean Architecture**: Separate concerns
- **Documentation**: Keep updated

## 🚀 Available Agents (54 Total)

### Core Development
`coder`, `reviewer`, `tester`, `planner`, `researcher`

### Swarm Coordination
`hierarchical-coordinator`, `mesh-coordinator`, `adaptive-coordinator`, `collective-intelligence-coordinator`, `swarm-memory-manager`

### Consensus & Distributed
`byzantine-coordinator`, `raft-manager`, `gossip-coordinator`, `consensus-builder`, `crdt-synchronizer`, `quorum-manager`, `security-manager`

### Performance & Optimization
`perf-analyzer`, `performance-benchmarker`, `task-orchestrator`, `memory-coordinator`, `smart-agent`

### GitHub & Repository
`github-modes`, `pr-manager`, `code-review-swarm`, `issue-tracker`, `release-manager`, `workflow-automation`, `project-board-sync`, `repo-architect`, `multi-repo-swarm`

### SPARC Methodology
`sparc-coord`, `sparc-coder`, `specification`, `pseudocode`, `architecture`, `refinement`

### Specialized Development
`backend-dev`, `mobile-dev`, `ml-developer`, `cicd-engineer`, `api-docs`, `system-architect`, `code-analyzer`, `base-template-generator`

### Testing & Validation
`tdd-london-swarm`, `production-validator`

### Migration & Planning
`migration-planner`, `swarm-init`

## 🎯 Claude Code vs MCP Tools

### Claude Code Handles ALL:
- File operations (Read, Write, Edit, MultiEdit, Glob, Grep)
- Code generation and programming
- Bash commands and system operations
- Implementation work
- Project navigation and analysis
- TodoWrite and task management
- Git operations
- Package management
- Testing and debugging

### MCP Tools ONLY:
- Coordination and planning
- Memory management
- Neural features
- Performance tracking
- Swarm orchestration
- GitHub integration

**KEY**: MCP coordinates, Claude Code executes.

## 🚀 Quick Setup

```bash
# Add Claude Flow MCP server
claude mcp add claude-flow npx claude-flow@alpha mcp start
```

## MCP Tool Categories

### Coordination
`swarm_init`, `agent_spawn`, `task_orchestrate`

### Monitoring
`swarm_status`, `agent_list`, `agent_metrics`, `task_status`, `task_results`

### Memory & Neural
`memory_usage`, `neural_status`, `neural_train`, `neural_patterns`

### GitHub Integration
`github_swarm`, `repo_analyze`, `pr_enhance`, `issue_triage`, `code_review`

### System
`benchmark_run`, `features_detect`, `swarm_monitor`

## 📋 Agent Coordination Protocol

### Every Agent MUST:

**1️⃣ BEFORE Work:**
```bash
npx claude-flow@alpha hooks pre-task --description "[task]"
npx claude-flow@alpha hooks session-restore --session-id "swarm-[id]"
```

**2️⃣ DURING Work:**
```bash
npx claude-flow@alpha hooks post-edit --file "[file]" --memory-key "swarm/[agent]/[step]"
npx claude-flow@alpha hooks notify --message "[what was done]"
```

**3️⃣ AFTER Work:**
```bash
npx claude-flow@alpha hooks post-task --task-id "[task]"
npx claude-flow@alpha hooks session-end --export-metrics true
```

## 🎯 Concurrent Execution Examples

### ✅ CORRECT (Single Message):
```javascript
[BatchTool]:
  // Initialize swarm
  mcp__claude-flow__swarm_init { topology: "mesh", maxAgents: 6 }
  mcp__claude-flow__agent_spawn { type: "researcher" }
  mcp__claude-flow__agent_spawn { type: "coder" }
  mcp__claude-flow__agent_spawn { type: "tester" }
  
  // Spawn agents with Task tool
  Task("Research agent: Analyze requirements...")
  Task("Coder agent: Implement features...")
  Task("Tester agent: Create test suite...")
  
  // Batch todos
  TodoWrite { todos: [
    {id: "1", content: "Research", status: "in_progress", priority: "high"},
    {id: "2", content: "Design", status: "pending", priority: "high"},
    {id: "3", content: "Implement", status: "pending", priority: "high"},
    {id: "4", content: "Test", status: "pending", priority: "medium"},
    {id: "5", content: "Document", status: "pending", priority: "low"}
  ]}
  
  // File operations
  Bash "mkdir -p app/{src,tests,docs}"
  Write "app/src/index.js"
  Write "app/tests/index.test.js"
  Write "app/docs/README.md"
```

### ❌ WRONG (Multiple Messages):
```javascript
Message 1: mcp__claude-flow__swarm_init
Message 2: Task("agent 1")
Message 3: TodoWrite { todos: [single todo] }
Message 4: Write "file.js"
// This breaks parallel coordination!
```

## Performance Benefits

- **84.8% SWE-Bench solve rate**
- **32.3% token reduction**
- **2.8-4.4x speed improvement**
- **27+ neural models**

## Hooks Integration

### Pre-Operation
- Auto-assign agents by file type
- Validate commands for safety
- Prepare resources automatically
- Optimize topology by complexity
- Cache searches

### Post-Operation
- Auto-format code
- Train neural patterns
- Update memory
- Analyze performance
- Track token usage

### Session Management
- Generate summaries
- Persist state
- Track metrics
- Restore context
- Export workflows

## Advanced Features (v2.0.0)

- 🚀 Automatic Topology Selection
- ⚡ Parallel Execution (2.8-4.4x speed)
- 🧠 Neural Training
- 📊 Bottleneck Analysis
- 🤖 Smart Auto-Spawning
- 🛡️ Self-Healing Workflows
- 💾 Cross-Session Memory
- 🔗 GitHub Integration

## Integration Tips

1. Start with basic swarm init
2. Scale agents gradually
3. Use memory for context
4. Monitor progress regularly
5. Train patterns from success
6. Enable hooks automation
7. Use GitHub tools first

## Support

- Documentation: https://github.com/ruvnet/claude-flow
- Issues: https://github.com/ruvnet/claude-flow/issues

---

Remember: **Claude Flow coordinates, Claude Code creates!**

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
Never save working files, text/mds and tests to the root folder.