# Neo-Commons

Enterprise-grade shared infrastructure library for the NeoMultiTenant platform.

## Overview

Neo-Commons is a Python package that provides reusable infrastructure components for the NeoMultiTenant ecosystem. It implements Clean Architecture principles, protocol-based dependency injection, and enterprise-grade patterns for authentication, caching, database operations, and utilities.

## Key Features

- **Protocol-Based Design**: All dependencies use `@runtime_checkable` Protocol interfaces
- **Sub-Millisecond Performance**: Intelligent caching with permission checks <1ms
- **Multi-Tenant Architecture**: Built-in tenant isolation and dynamic schema configuration
- **Clean Architecture**: Domain/Application/Infrastructure/Interface layer separation
- **Enterprise Security**: Keycloak integration, RBAC, audit logging
- **Type Safety**: 100% type coverage with Pydantic models

## Quick Start

### Installation

```bash
pip install neo-commons
```

### Basic Usage

```python
from neo_commons.auth import AuthService
from neo_commons.cache import CacheService
from neo_commons.database import DatabaseService

# Protocol-based dependency injection
async def example_usage(
    auth_service: AuthService,
    cache_service: CacheService,
    db_service: DatabaseService
):
    # Authenticate user
    user = await auth_service.get_current_user(token)
    
    # Check permissions with sub-millisecond caching
    has_permission = await auth_service.check_permission(
        user_id=user.id,
        resource="users",
        action="read",
        tenant_id=user.tenant_id
    )
    
    # Database operations with dynamic schema
    if has_permission:
        return await db_service.fetch(
            "SELECT * FROM users WHERE id = $1",
            user.id,
            schema=user.tenant_schema
        )
```

## Architecture

### Clean Architecture Layers

```
src/neo_commons/
├── domain/           # Enterprise business rules
│   ├── entities/     # Core business objects
│   ├── value_objects/    # Immutable value types
│   └── protocols/    # Domain contracts
├── application/      # Application business rules
│   ├── services/     # Use cases and workflows
│   ├── commands/     # Command handlers (CQRS)
│   └── queries/      # Query handlers (CQRS)
├── infrastructure/   # External concerns
│   ├── database/     # AsyncPG implementations
│   ├── cache/        # Redis caching
│   ├── external/     # Keycloak, third-party
│   └── messaging/    # Event systems
└── interfaces/       # Interface adapters
    ├── api/          # FastAPI dependencies
    ├── cli/          # Command-line tools
    └── web/          # Web adapters
```

### Protocol-Based Patterns

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AuthRepository(Protocol):
    async def get_user_permissions(
        self, user_id: str, tenant_id: str
    ) -> list[Permission]:
        """Get user permissions with sub-millisecond caching."""

@runtime_checkable
class CacheService(Protocol):
    async def get(self, key: str, tenant_id: str) -> str | None:
        """Get cached value with tenant isolation."""
```

## Core Components

### Authentication & Authorization
- **Keycloak Integration**: Multi-realm, token management
- **RBAC System**: Role-based access control with caching
- **Permission Management**: Sub-millisecond permission checks
- **Multi-Tenant Support**: Tenant-aware authentication

### Database & Caching
- **AsyncPG Integration**: High-performance PostgreSQL operations
- **Dynamic Schema Support**: Tenant-specific schema injection
- **Redis Caching**: Intelligent caching with tenant isolation
- **Connection Management**: Pool management and health monitoring

### Utilities & Infrastructure
- **Structured Logging**: Context-aware logging with tenant/user context
- **Configuration Management**: Environment-based configuration
- **Middleware Components**: Security, timing, request context
- **Error Handling**: Comprehensive exception management

## Development

### Setup Development Environment

```bash
git clone https://github.com/neomultitenant/neo-commons.git
cd neo-commons
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
pytest
pytest --cov=src/neo_commons --cov-report=html
```

### Code Quality

```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname
REDIS_URL=redis://host:port/db

# Keycloak
KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_REALM=master
KEYCLOAK_CLIENT_ID=neo-commons
KEYCLOAK_CLIENT_SECRET=secret

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### FastAPI Integration

```python
from fastapi import FastAPI, Depends
from neo_commons.interfaces.api import get_auth_service, get_cache_service

app = FastAPI()

@app.get("/users/me")
async def get_current_user(
    auth_service=Depends(get_auth_service),
    cache_service=Depends(get_cache_service)
):
    return await auth_service.get_current_user(token)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- Documentation: [https://neo-commons.readthedocs.io](https://neo-commons.readthedocs.io)
- Issues: [GitHub Issues](https://github.com/neomultitenant/neo-commons/issues)
- Discussions: [GitHub Discussions](https://github.com/neomultitenant/neo-commons/discussions)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes and version history.