# Coding Standards and Conventions

## Neo-Commons Architecture Rules
1. **Always use neo-commons first** - Check shared library before creating new functionality
2. **Follow Feature-First organization** - Business logic belongs in feature modules, not core
3. **Use Protocol interfaces** - Depend on @runtime_checkable contracts, not implementations
4. **Respect Clean Core boundaries** - Core only contains value objects, exceptions, shared contracts
5. **Import from features** - Import entities and services from feature modules, not core

## Technical Standards
- **Use asyncpg** for database operations, never ORMs for performance paths
- **Configure schemas dynamically** - Never hardcode database schema names
- **Use UUIDv7** for all UUID generation (time-ordered)
- **Follow async patterns** throughout the codebase
- **Implement comprehensive error handling** with appropriate status codes
- **Add structured logging** with tenant_id, user_id, request_id context
- **Write tests** for all new functionality using protocol mocks
- **Validate inputs** using Pydantic models
- **Cache aggressively** but implement proper invalidation

## Feature Development Guidelines
- **Feature Isolation** - Features should be self-contained with minimal cross-feature dependencies
- **Protocol Contracts** - Define protocols in entities/ for domain contracts, infrastructure/ for technical contracts
- **Service Orchestration** - Complex workflows belong in feature services, not repositories
- **Repository Focus** - Repositories handle only data access, no business logic
- **Entity Validation** - Domain validation belongs in entities, technical validation in infrastructure

## Security Requirements
- **NEVER use jwt.decode() with verify_signature=False**
- Use parameterized queries only; never format SQL with user input
- Validate all inputs with Pydantic; enforce strict constraints
- Enforce authorization at repository/service boundary
- Write audit logs for sensitive operations
- Never leak sensitive info in errors or logs

## Performance Targets
- Permission checks: < 1ms with cache
- API p95 latency: < 100ms  
- Simple queries: < 10ms; complex queries: < 50ms
- Cache hit rate for permissions: > 90%