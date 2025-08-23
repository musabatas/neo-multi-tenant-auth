# Neo Admin API

Enterprise-grade multi-tenant platform administration API built with **Feature-First + Clean Core** architecture, following DRY principles with maximum neo-commons integration.

## Overview

Neo Admin API provides comprehensive platform administration capabilities using a feature-based architecture that mirrors neo-commons design patterns:

- **Organizations Management**: CRUD operations for customer organizations
- **Tenants Management**: Multi-tenant lifecycle with database provisioning
- **Users Administration**: Platform user management with RBAC
- **Billing & Subscriptions**: Usage tracking and invoice management
- **Analytics & Monitoring**: Platform metrics and system health
- **System Administration**: Health checks, maintenance, cache management

## Architecture

### Feature-First + Clean Core Design

Following the same pattern as neo-commons and the old NeoAdminApi:

```
NeoAdminApi/
├── src/
│   ├── common/                      # Shared utilities and config
│   │   ├── config/                  # Settings extending neo-commons BaseConfig
│   │   │   ├── __init__.py
│   │   │   └── settings.py
│   │   ├── services/                # Common service factories
│   │   │   ├── __init__.py
│   │   │   └── dependencies_factory.py
│   │   ├── __init__.py
│   │   └── dependencies.py          # FastAPI dependencies
│   ├── features/                    # Feature modules by business domain
│   │   ├── organizations/           # Organization management feature
│   │   │   ├── models/              # Pydantic request/response models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── request.py
│   │   │   │   └── response.py
│   │   │   ├── repositories/        # Data access layer
│   │   │   │   ├── __init__.py
│   │   │   │   └── organization_repository.py
│   │   │   ├── services/            # Business logic layer
│   │   │   │   ├── __init__.py
│   │   │   │   └── organization_service.py
│   │   │   ├── routers/             # API endpoints
│   │   │   │   ├── __init__.py
│   │   │   │   └── v1.py
│   │   │   └── __init__.py
│   │   ├── tenants/                 # Tenant management feature
│   │   ├── users/                   # User management feature
│   │   ├── billing/                 # Billing feature
│   │   ├── analytics/               # Analytics feature
│   │   ├── system/                  # System management feature
│   │   └── __init__.py
│   ├── app.py                       # FastAPI application factory
│   └── main.py                      # Application entry point
├── main.py                          # Development entry point
├── pyproject.toml                   # Project configuration
├── .env.example                     # Environment configuration template
└── README.md                        # This file
```

### Key Design Principles

#### 1. Feature-First Organization
- **Business Domain Focus**: Each feature represents a complete business capability
- **Self-Contained**: Features contain models, repositories, services, and routers
- **Clean Boundaries**: Features communicate through well-defined interfaces
- **Independent Development**: Teams can work on features independently

#### 2. Neo-Commons Integration
- **Maximum DRY**: Reuses authentication, database, caching, and configuration from neo-commons
- **Protocol-Based**: Uses `@runtime_checkable` protocols for dependency injection
- **Shared Value Objects**: Leverages `UserId`, `TenantId`, `OrganizationId` from neo-commons
- **Consistent Patterns**: Follows same architectural patterns as neo-commons

#### 3. Clean Dependencies
- **Common Layer**: Shared utilities, config, and dependencies
- **Features Layer**: Business logic organized by domain
- **No Circular Dependencies**: Clear dependency flow from features to common to neo-commons

## Features

### 🏢 Organizations Feature
**Location**: `src/features/organizations/`

Complete organization lifecycle management:
- **Models**: Request/response Pydantic models with validation
- **Repository**: Data access using neo-commons database service
- **Service**: Business logic with validation and error handling  
- **Router**: REST API endpoints with platform admin authorization

**Key Endpoints**:
- `GET /api/v1/organizations` - List with pagination and search
- `POST /api/v1/organizations` - Create new organization
- `GET /api/v1/organizations/{id}` - Get organization details
- `PUT /api/v1/organizations/{id}` - Update organization
- `DELETE /api/v1/organizations/{id}` - Delete organization
- `GET /api/v1/organizations/{id}/tenants` - List organization tenants

### 🏠 Tenants Feature  
**Location**: `src/features/tenants/`

Multi-tenant lifecycle management:
- Tenant provisioning with database setup
- Multi-region deployment support
- Tenant configuration management
- Database migration orchestration

### 👥 Users Feature
**Location**: `src/features/users/`

Platform user administration:
- Platform admin user management
- Role and permission assignment
- User activity monitoring
- Support user impersonation

### 💳 Billing Feature
**Location**: `src/features/billing/`

Subscription and billing management:
- Usage metrics collection
- Invoice generation and processing
- Plan management and limits
- Payment processing integration

### 📊 Analytics Feature
**Location**: `src/features/analytics/`

Platform metrics and reporting:
- System performance metrics
- Tenant usage analytics
- Business intelligence dashboards
- Data export capabilities

### ⚙️ System Feature
**Location**: `src/features/system/`

System administration and health:
- Health check endpoints (public and detailed)
- Maintenance mode control
- Cache management operations  
- System information and monitoring

## Neo-Commons Integration

### Dependencies Factory Pattern

The `DependenciesFactory` centralizes neo-commons service management:

```python
from src.common.services import get_dependencies_factory

# Get services
factory = get_dependencies_factory()
auth_deps = await factory.get_auth_dependencies()
db_service = await factory.get_database_service()
cache_service = await factory.get_cache_service()
```

### Authentication Integration

Uses neo-commons auth features directly:

```python
from src.common.dependencies import get_current_user, require_platform_admin

@router.get("/protected")
async def protected_endpoint(
    current_user = Depends(get_current_user)  # JWT validation via neo-commons
):
    return {"user_id": current_user.user_id.value}

@router.post("/admin-only")
async def admin_endpoint(
    current_user = Depends(require_platform_admin())  # Role-based authorization
):
    return {"message": "Platform admin access"}
```

### Configuration Inheritance

Extends neo-commons BaseConfig:

```python
from neo_commons.infrastructure.configuration import BaseConfig

class Settings(BaseConfig):  # Inherits Keycloak, Redis, JWT config
    # Admin-specific settings
    admin_database_url: str
    platform_admin_role: str = "platform_admin"
    billing_enabled: bool = True
```

## Quick Start

### Prerequisites

- Python 3.13+
- Neo Infrastructure running (PostgreSQL, Redis, Keycloak)
- neo-commons package installed and available

### Installation

1. **Install Dependencies**:
```bash
cd NeoAdminApi
pip install -e .
# Or for development
pip install -e ".[dev]"
```

2. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env with your Neo infrastructure settings
```

3. **Run the Application**:
```bash
# Development mode
python main.py

# Or with uvicorn directly  
uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```

4. **Access the API**:
- API Documentation: http://localhost:8001/docs
- Health Check: http://localhost:8001/health
- System Health: http://localhost:8001/api/v1/system/health

## Configuration

### Environment Variables

All configuration uses the `NEO_ADMIN_` prefix and extends neo-commons BaseConfig:

```bash
# Application
NEO_ADMIN_APP_NAME="Neo Admin API"
NEO_ADMIN_DEBUG=false
NEO_ADMIN_PORT=8001

# Admin Database (separate from tenant databases)
NEO_ADMIN_ADMIN_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/neofast_admin"

# Neo-Commons Configuration (inherited)
NEO_ADMIN_KEYCLOAK_SERVER_URL="http://localhost:8080"
NEO_ADMIN_KEYCLOAK_ADMIN="admin"
NEO_ADMIN_KEYCLOAK_PASSWORD="admin"
NEO_ADMIN_REDIS_URL="redis://localhost:6379"
NEO_ADMIN_REDIS_PASSWORD="redis"

# Platform Settings
NEO_ADMIN_PLATFORM_ADMIN_ROLE="platform_admin"
NEO_ADMIN_TENANT_CREATION_ENABLED=true

# Feature Flags
NEO_ADMIN_BILLING_ENABLED=true
NEO_ADMIN_ANALYTICS_ENABLED=true
```

## Development

### Adding New Features

Follow the feature-first pattern:

1. **Create Feature Directory**:
```bash
mkdir -p src/features/my_feature/{models,repositories,services,routers}
```

2. **Implement Feature Layers**:
- `models/`: Pydantic request/response models
- `repositories/`: Data access using neo-commons database service
- `services/`: Business logic with validation
- `routers/`: FastAPI endpoints with authorization

3. **Register in App**:
```python
# In src/app.py
from .features.my_feature.routers import router as my_feature_router

app.include_router(
    my_feature_router,
    prefix=f"{settings.api_prefix}/my-feature",
    tags=["my-feature"],
)
```

### Code Style

- **Feature Independence**: Features should be self-contained
- **Neo-Commons First**: Always check neo-commons for existing functionality
- **Protocol-Based**: Use interfaces for dependency injection
- **Type Safety**: Full type hints with mypy validation
- **Error Handling**: Proper HTTP status codes and detailed error messages

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src

# Feature-specific tests
pytest tests/features/organizations/
```

## Deployment

### Production Checklist

- [ ] Set `NEO_ADMIN_DEBUG=false`
- [ ] Configure production database URLs
- [ ] Set secure JWT secret keys
- [ ] Configure CORS origins appropriately
- [ ] Set up monitoring and health checks
- [ ] Configure rate limiting and security headers
- [ ] Set up SSL/TLS termination

### Docker Deployment

```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install .

COPY src/ src/
COPY main.py .

EXPOSE 8001
CMD ["python", "main.py"]
```

## Integration with Neo Infrastructure

### Database Architecture

- **Admin Database**: `neofast_admin` - Organization, tenant, user, billing data
- **Regional Databases**: Managed through admin API for tenant provisioning
- **Neo-Commons**: Provides connection management and query utilities

### Keycloak Integration

- **Platform Realm**: Admin users authenticate against platform realm
- **Tenant Realms**: Managed through admin API for tenant provisioning
- **Role Hierarchy**: Platform admins > Organization admins > Tenant admins

### Multi-Region Support

- **Region Management**: Create and manage deployment regions
- **Tenant Placement**: Assign tenants to specific regions for compliance
- **Database Provisioning**: Automated tenant database creation in target regions

## API Documentation

Complete API documentation is available at `/docs` when running the application.

### Key API Patterns

- **Pagination**: Standard `skip`/`limit` parameters with `total` count
- **Filtering**: Search and filter parameters for list endpoints
- **Authorization**: Platform admin role required for most operations
- **Error Handling**: Consistent error response format with details
- **Audit Logging**: Request tracing with unique request IDs

## Support

For development questions and issues:

1. Check neo-commons documentation for shared functionality
2. Review the Neo Infrastructure setup guide
3. Check API documentation at `/docs` when running
4. Review application logs for detailed error information

## License

MIT License - See LICENSE file for details.