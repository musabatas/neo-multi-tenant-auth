# NeoCommons

Common utilities and shared components for NeoMultiTenant microservices.

## Overview

NeoCommons is a shared Python library that provides common utilities, authentication, database connections, caching, and other shared components used across NeoMultiTenant API services (NeoAdminApi, NeoTenantApi, etc.).

## Features

### 🔐 Authentication & Authorization
- Keycloak integration with multi-realm support
- JWT token validation and management
- Role-based access control (RBAC)
- Permission decorators and middleware
- Multi-level authentication (Platform & Tenant)

### 🗄️ Database Utilities
- AsyncPG connection management
- Base repository patterns
- Dynamic database routing
- Regional database management
- Connection pooling and health checks

### ⚡ Caching
- Redis client integration
- Cache decorators and utilities
- Namespace separation for multi-tenancy
- Automatic cache invalidation

### 🛠️ Base Components
- Base models with Pydantic
- Standard exception classes
- Base service patterns
- Middleware components
- Utility functions

### 🔌 External Integrations
- Keycloak async client
- Token manager with dual validation
- Realm manager for multi-tenancy

## Installation

### Development (Editable Install)
```bash
# From your service directory (e.g., NeoAdminApi/)
pip install -e ../neo-commons
```

### Production (Package Install)
```bash
pip install neo-commons
```

### With Development Dependencies
```bash
pip install -e ../neo-commons[dev]
```

## Quick Start

### Basic Usage
```python
from neo_commons.database.connection import get_database
from neo_commons.cache.client import get_cache
from neo_commons.auth.decorators.permissions import require_permission

# Database operations
db = get_database()
result = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

# Caching
cache = get_cache()
await cache.set("key", "value", ttl=300)

# Authentication
@require_permission("users:read", scope="tenant")
async def get_users():
    return await user_service.list_users()
```

### Extending Base Classes
```python
from neo_commons.repositories.base import BaseRepository
from neo_commons.services.base import BaseService

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(table_name="users", schema="tenant")

class UserService(BaseService[User]):
    def __init__(self):
        super().__init__()
        self.repository = UserRepository()
```

## Architecture

### Package Structure
```
neo_commons/
├── auth/                   # Authentication & authorization
├── cache/                  # Caching utilities
├── database/               # Database connections & utilities
├── exceptions/             # Exception classes
├── middleware/             # FastAPI middleware
├── models/                 # Base models
├── repositories/           # Base repository patterns
├── services/              # Base service patterns
├── utils/                 # Utility functions
└── integrations/          # External integrations
    └── keycloak/          # Keycloak integration
```

### Design Principles
- **DRY (Don't Repeat Yourself)**: Single source of truth for common code
- **SOLID Principles**: Well-structured, maintainable code
- **Async-First**: Full async/await support
- **Type Safety**: Complete type hints with Pydantic
- **Testability**: Dependency injection and mocking support

## Configuration

### Environment Variables
NeoCommons respects these environment variables:

```bash
# Database
ADMIN_DATABASE_URL="postgresql://user:pass@host:port/db"

# Redis
REDIS_URL="redis://host:port/db"
REDIS_PASSWORD="password"

# Keycloak
KEYCLOAK_URL="http://localhost:8080"
KEYCLOAK_ADMIN_REALM="neo-admin"

# Security
SECRET_KEY="your-secret-key"
ALGORITHM="HS256"
```

### Service Integration
Add to your service's requirements.txt:
```txt
# For development
-e ../neo-commons

# For production
neo-commons==1.0.0
```

## Development

### Setup Development Environment
```bash
cd neo-commons
pip install -e .[dev]
pre-commit install
```

### Running Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test category
pytest -m unit
pytest -m integration
```

### Code Quality
```bash
# Format code
black src tests

# Lint
ruff check src tests

# Type checking
mypy src
```

## Testing

### Test Structure
```
tests/
├── unit/              # Unit tests (mocked dependencies)
├── integration/       # Integration tests (real services)
├── fixtures/          # Test data and utilities
└── conftest.py        # Pytest configuration
```

### Writing Tests
```python
import pytest
from neo_commons.database.connection import DatabaseManager

@pytest.mark.unit
async def test_database_health_check(mock_db):
    """Test database health check."""
    manager = DatabaseManager(mock_db)
    health = await manager.health_check()
    assert health is True

@pytest.mark.integration  
async def test_real_database_connection():
    """Test real database connection."""
    db = get_database()
    result = await db.fetchval("SELECT 1")
    assert result == 1
```

## Migration Guide

### From Service-Specific Common Code
If you're migrating from service-specific common code:

1. **Update imports**:
   ```python
   # Before
   from src.common.database.connection import get_database
   
   # After  
   from neo_commons.database.connection import get_database
   ```

2. **Update requirements.txt**:
   ```txt
   # Add this line
   -e ../neo-commons
   ```

3. **Remove duplicate code** from your service's common directory

4. **Update tests** to use neo_commons imports

## Contributing

### Development Workflow
1. Create feature branch
2. Make changes with tests
3. Run quality checks: `black`, `ruff`, `mypy`, `pytest`
4. Submit pull request

### Code Standards
- Follow existing patterns and conventions
- Add comprehensive tests for new features
- Update documentation for public APIs
- Use type hints throughout

## Versioning

NeoCommons follows semantic versioning:
- **Major version**: Breaking changes
- **Minor version**: New features (backward compatible)  
- **Patch version**: Bug fixes

## License

MIT License - see LICENSE file for details.

## Support

For questions about NeoCommons:
1. Check this README and code documentation
2. Review existing patterns in the codebase
3. Create an issue for bugs or feature requests