# Task Completion Checklist

## Before Implementation
1. **Use codebase-db-investigator agent** to analyze existing code patterns and understand current implementation
2. **Verify neo-commons availability** - Check if functionality already exists in shared library before creating new code
3. **Understand database structures** - Review relevant schema files, migrations, and table relationships
4. **Check related imports and dependencies** - Ensure compatibility with existing codebase patterns
5. **Validate file structure** - Understand where new code should be placed following Feature-First + Clean Core architecture

## After Implementation  
1. **Verify integration works** - Check that new code integrates properly with existing systems
2. **Validate imports and dependencies** - Ensure all imports resolve correctly and follow project patterns
3. **Test database connectivity** - If database operations were added, verify connections work correctly
4. **Check file organization** - Ensure code is placed in correct feature modules and follows architecture
5. **Validate critical functionality** - Run basic tests to ensure implementation works as expected

## Code Quality Checks
- [ ] Run tests: `pytest tests/`
- [ ] Run linting: `black .` and `isort .`
- [ ] Type checking: `mypy .`
- [ ] Security scan: Check for SQL injection prevention, input validation
- [ ] Performance validation: Monitor response times, check for N+1 queries
- [ ] Documentation: Ensure docstrings and comments are accurate

## Git Workflow
1. Never work directly on `main`; create feature branches: `[type]/[description]-[ticket]`
2. Run tests, lint, and type checks before committing
3. Use conventional commits (feat, fix, refactor, docs, test, chore)
4. Keep commits small and focused; include context in body when needed
5. Rebase feature branches on latest main before PR; resolve conflicts locally
6. PRs must include change summary, tests, and any breaking change notes

## Critical Implementation Rules
1. **Never duplicate existing functionality** - Always check neo-commons first
2. **Implement generic/reusable functionality in neo-commons** - If task is generic or reusable across services
3. **Follow existing patterns** - Use codebase analysis to understand current implementation patterns
4. **Respect architecture boundaries** - Features in feature modules, core only for value objects/exceptions
5. **Validate database operations** - Ensure schema names are dynamic, use UUIDv7, follow asyncpg patterns