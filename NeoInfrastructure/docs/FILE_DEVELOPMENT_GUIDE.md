# File-by-File Development Guide

This guide provides detailed instructions for developing each file in the Infrastructure API restructuring project.

## 📁 Project Structure Reference

```
src/
├── app.py                           # FastAPI application factory
├── main.py                          # Application entry point
│
├── common/                          # Shared utilities
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # Infrastructure-specific settings
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py            # Database connection management
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── config.py                # Middleware configuration
│   ├── exceptions/
│   │   ├── __init__.py
│   │   └── base.py                  # Custom exceptions
│   └── models/
│       ├── __init__.py
│       ├── base.py                  # Base Pydantic models
│       └── responses.py             # Standard API responses
│
├── features/
│   ├── __init__.py
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── dependencies.py          # Authentication dependencies
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── auth.py              # Authentication endpoints
│   │
│   ├── migrations/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── domain.py            # Migration domain models
│   │   │   ├── request.py           # Migration request schemas
│   │   │   └── response.py          # Migration response schemas
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── migration_repository.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── migration_service.py
│   │   │   └── dynamic_migration_service.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── migrations.py        # Core migration endpoints
│   │   │   ├── dynamic.py           # Dynamic migration endpoints
│   │   │   └── tenant.py            # Tenant migration endpoints
│   │   └── engines/                 # Refactored migration engines
│   │       ├── __init__.py
│   │       ├── dynamic_migration_engine.py
│   │       ├── enhanced_migration_manager.py
│   │       └── migration_dependency_resolver.py
│   │
│   ├── databases/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── domain.py
│   │   │   ├── request.py
│   │   │   └── response.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   └── database_repository.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── database_service.py
│   │   └── routers/
│   │       ├── __init__.py
│   │       └── connections.py
│   │
│   └── health/
│       ├── __init__.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── health.py
│       ├── services/
│       │   ├── __init__.py
│       │   └── health_service.py
│       └── routers/
│           ├── __init__.py
│           └── system.py
│
└── integrations/
    ├── __init__.py
    └── keycloak/
        ├── __init__.py
        ├── async_client.py
        ├── token_manager.py
        └── realm_manager.py
```

---

## 🏗️ Core Application Files

### `src/main.py`
**Purpose**: Application entry point and CLI runner
**Dependencies**: None
**Priority**: High

```python
"""
Application entry point for Infrastructure API.
"""
import uvicorn
from loguru import logger

from src.common.config.settings import settings
from src.app import create_app

# Create the FastAPI application
app = create_app()

def main():
    """Run the application."""
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        workers=1 if settings.reload else settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True,
        use_colors=True
    )

if __name__ == "__main__":
    main()
```

**Development Notes:**
- Copy structure from Admin API `main.py`
- Ensure port differs from Admin API (use 8000 for Infrastructure)
- Configure logging level from environment

---

### `src/app.py`
**Purpose**: FastAPI application factory with lifespan management
**Dependencies**: `common/config`, `common/middleware`, `common/database`
**Priority**: High

```python
"""
FastAPI application factory and configuration.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from src.common.config.settings import settings
from src.common.database.connection import init_database, close_database
from src.common.middleware.config import setup_middleware
from src.common.exceptions.base import register_exception_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    try:
        # Initialize database connections
        await init_database()
        
        # Initialize migration engines
        from src.features.migrations.services.migration_service import init_migration_services
        await init_migration_services()
        
        logger.info("Infrastructure API startup complete")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Infrastructure API...")
    
    try:
        await close_database()
        logger.info("Infrastructure API shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Infrastructure Management API for NeoMultiTenant",
        docs_url="/swagger" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan
    )
    
    # Setup middleware stack
    setup_middleware(app)
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register routers
    register_routers(app)
    
    return app

def register_routers(app: FastAPI) -> None:
    """Register all application routers."""
    
    # Health endpoints (no auth required)
    from src.features.health.routers.system import router as health_router
    app.include_router(health_router, prefix="/health", tags=["Health"])
    
    # Authentication endpoints
    from src.features.auth.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    
    # Migration endpoints (auth required)
    from src.features.migrations.routers.migrations import router as migrations_router
    from src.features.migrations.routers.dynamic import router as dynamic_router
    from src.features.migrations.routers.tenant import router as tenant_router
    
    app.include_router(migrations_router, prefix="/migrations", tags=["Migrations"])
    app.include_router(dynamic_router, prefix="/migrations/dynamic", tags=["Dynamic Migrations"])
    app.include_router(tenant_router, prefix="/tenants", tags=["Tenant Migrations"])
    
    # Database endpoints (auth required)
    from src.features.databases.routers.connections import router as db_router
    app.include_router(db_router, prefix="/databases", tags=["Database Connections"])
    
    logger.info("All routers registered successfully")
```

**Development Notes:**
- Follow Admin API pattern for application factory
- Ensure proper lifespan management for resources
- Register routers in logical order
- Include comprehensive error handling

---

## 🔧 Common Utilities

### `src/common/config/settings.py`
**Purpose**: Infrastructure-specific configuration management
**Dependencies**: None
**Priority**: High

```python
"""
Infrastructure API configuration settings.
"""
from typing import List, Optional, Dict, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Infrastructure API settings."""
    
    # Application settings
    app_name: str = "NeoMultiTenant Infrastructure API"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")  # Different from Admin API
    reload: bool = Field(default=False, env="RELOAD")
    workers: int = Field(default=1, env="WORKERS")
    
    # Database settings
    admin_database_url: str = Field(env="ADMIN_DATABASE_URL")
    database_pool_min_size: int = Field(default=5, env="DB_POOL_MIN_SIZE")
    database_pool_max_size: int = Field(default=20, env="DB_POOL_MAX_SIZE")
    
    # Keycloak settings
    keycloak_url: str = Field(env="KEYCLOAK_URL")
    keycloak_admin_realm: str = Field(default="master", env="KEYCLOAK_ADMIN_REALM")
    keycloak_admin_client_id: str = Field(env="KEYCLOAK_CLIENT_ID")
    keycloak_admin_client_secret: str = Field(env="KEYCLOAK_CLIENT_SECRET")
    
    # Infrastructure-specific settings
    migration_timeout: int = Field(default=300, env="MIGRATION_TIMEOUT")  # 5 minutes
    migration_batch_size: int = Field(default=10, env="MIGRATION_BATCH_SIZE")
    migration_retry_attempts: int = Field(default=3, env="MIGRATION_RETRY_ATTEMPTS")
    
    # Encryption settings
    app_encryption_key: str = Field(env="APP_ENCRYPTION_KEY")
    
    # Security settings
    cors_allow_origins: List[str] = Field(default=["*"], env="CORS_ALLOW_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_RPM")
    
    @validator("environment")
    def validate_environment(cls, v):
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()
```

**Development Notes:**
- Adapt from Admin API settings but focus on infrastructure needs
- Add migration-specific configuration options
- Ensure port differs from other services
- Include validation for critical settings

---

### `src/common/database/connection.py`
**Purpose**: Database connection pool management
**Dependencies**: `common/config`
**Priority**: High

```python
"""
Database connection management for Infrastructure API.
"""
import asyncpg
from typing import Optional
from loguru import logger

from src.common.config.settings import settings

# Global connection pool
admin_pool: Optional[asyncpg.Pool] = None

async def init_db_connection(conn):
    """Initialize database connection with encryption key."""
    # Set the encryption key as a session parameter
    await conn.execute(f"SET app.encryption_key = '{settings.app_encryption_key}'")

async def init_database():
    """Initialize database connection pool."""
    global admin_pool
    
    logger.info("Initializing database connection pool...")
    
    admin_pool = await asyncpg.create_pool(
        dsn=settings.admin_database_url,
        min_size=settings.database_pool_min_size,
        max_size=settings.database_pool_max_size,
        init=init_db_connection,
        command_timeout=60
    )
    
    # Test connection
    async with admin_pool.acquire() as conn:
        version = await conn.fetchval("SELECT version()")
        logger.info(f"Connected to PostgreSQL: {version[:50]}...")
    
    logger.info("Database connection pool initialized successfully")

async def close_database():
    """Close database connection pool."""
    global admin_pool
    
    if admin_pool:
        logger.info("Closing database connection pool...")
        await admin_pool.close()
        admin_pool = None
        logger.info("Database connection pool closed")

def get_admin_pool() -> asyncpg.Pool:
    """Get the admin database connection pool."""
    if admin_pool is None:
        raise RuntimeError("Database pool not initialized")
    return admin_pool
```

**Development Notes:**
- Copy pattern from existing deployment API
- Ensure encryption key is set for all connections
- Add proper error handling and logging
- Include connection testing on startup

---

### `src/common/exceptions/base.py`
**Purpose**: Infrastructure-specific exceptions
**Dependencies**: None
**Priority**: Medium

```python
"""
Infrastructure API custom exceptions.
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from loguru import logger

class InfrastructureException(Exception):
    """Base exception for infrastructure operations."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

class MigrationException(InfrastructureException):
    """Exception for migration operations."""
    pass

class DatabaseConnectionException(InfrastructureException):
    """Exception for database connection issues."""
    pass

class AuthenticationException(InfrastructureException):
    """Exception for authentication issues."""
    pass

class ValidationException(InfrastructureException):
    """Exception for validation errors."""
    pass

# Exception handlers
async def infrastructure_exception_handler(request: Request, exc: InfrastructureException):
    """Handle infrastructure-specific exceptions."""
    logger.error(f"Infrastructure error: {exc.message}", extra=exc.details)
    
    return JSONResponse(
        status_code=400,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )

async def migration_exception_handler(request: Request, exc: MigrationException):
    """Handle migration-specific exceptions."""
    logger.error(f"Migration error: {exc.message}", extra=exc.details)
    
    return JSONResponse(
        status_code=422,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )

def register_exception_handlers(app):
    """Register all exception handlers."""
    app.add_exception_handler(InfrastructureException, infrastructure_exception_handler)
    app.add_exception_handler(MigrationException, migration_exception_handler)
    app.add_exception_handler(DatabaseConnectionException, infrastructure_exception_handler)
    app.add_exception_handler(AuthenticationException, infrastructure_exception_handler)
    app.add_exception_handler(ValidationException, infrastructure_exception_handler)
```

**Development Notes:**
- Create infrastructure-specific exception hierarchy
- Include detailed error information for debugging
- Follow FastAPI exception handling patterns
- Log all errors with appropriate levels

---

## 🔐 Authentication System

### `src/integrations/keycloak/async_client.py`
**Purpose**: Async Keycloak client for infrastructure operations
**Dependencies**: `common/config`
**Priority**: High

```python
"""
Async Keycloak client for Infrastructure API.
"""
from typing import Optional, Dict, Any
import aiohttp
from python_keycloak import KeycloakOpenIDAsync
from loguru import logger

from src.common.config.settings import settings
from src.common.exceptions.base import AuthenticationException

class InfrastructureKeycloakClient:
    """Async Keycloak client for infrastructure operations."""
    
    def __init__(self):
        self.client = KeycloakOpenIDAsync(
            server_url=settings.keycloak_url,
            client_id=settings.keycloak_admin_client_id,
            realm_name=settings.keycloak_admin_realm,
            client_secret_key=settings.keycloak_admin_client_secret,
            verify=not settings.is_development
        )
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return claims."""
        try:
            # Validate token and get user info
            token_info = await self.client.introspect(token)
            
            if not token_info.get("active"):
                raise AuthenticationException("Token is not active")
            
            # Get user info
            userinfo = await self.client.userinfo(token)
            
            return {
                **token_info,
                **userinfo
            }
            
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            raise AuthenticationException(f"Token validation failed: {str(e)}")
    
    async def get_user_permissions(self, user_id: str) -> list:
        """Get user permissions from Keycloak."""
        try:
            # This would be implemented based on your Keycloak setup
            # For now, return basic permissions
            return ["infrastructure:read", "migrations:execute"]
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return []

# Global client instance
keycloak_client: Optional[InfrastructureKeycloakClient] = None

def get_keycloak_client() -> InfrastructureKeycloakClient:
    """Get the Keycloak client instance."""
    global keycloak_client
    
    if keycloak_client is None:
        keycloak_client = InfrastructureKeycloakClient()
    
    return keycloak_client
```

**Development Notes:**
- Adapt from Admin API Keycloak integration
- Focus on infrastructure-specific permissions
- Include proper error handling for token validation
- Add caching for frequently accessed data

---

### `src/features/auth/dependencies.py`
**Purpose**: Authentication dependencies for infrastructure endpoints
**Dependencies**: `integrations/keycloak`
**Priority**: High

```python
"""
Authentication dependencies for Infrastructure API endpoints.
"""
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from loguru import logger

from src.integrations.keycloak.async_client import get_keycloak_client
from src.common.exceptions.base import AuthenticationException

# Security scheme
security = HTTPBearer(
    description="JWT token from Keycloak",
    auto_error=False
)

class InfrastructureAuth:
    """Authentication dependency for infrastructure operations."""
    
    def __init__(self, required_permissions: Optional[List[str]] = None):
        self.required_permissions = required_permissions or []
    
    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ) -> Dict[str, Any]:
        """Validate token and check permissions."""
        
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        try:
            keycloak_client = get_keycloak_client()
            user_info = await keycloak_client.validate_token(credentials.credentials)
            
            # Check required permissions
            if self.required_permissions:
                user_permissions = user_info.get("permissions", [])
                missing_permissions = set(self.required_permissions) - set(user_permissions)
                
                if missing_permissions:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing permissions: {', '.join(missing_permissions)}"
                    )
            
            return user_info
            
        except AuthenticationException as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )

# Common permission dependencies
require_migration_read = InfrastructureAuth(["migrations:read"])
require_migration_execute = InfrastructureAuth(["migrations:execute"])
require_migration_manage = InfrastructureAuth(["migrations:manage"])
require_infrastructure_admin = InfrastructureAuth(["infrastructure:admin"])
require_database_read = InfrastructureAuth(["databases:read"])
require_database_manage = InfrastructureAuth(["databases:manage"])

# Optional authentication
get_current_user_optional = InfrastructureAuth()
```

**Development Notes:**
- Create infrastructure-specific permission system
- Follow Admin API patterns for authentication
- Include proper error handling and logging
- Define permission hierarchy for different operations

---

## 🔄 Migration System

### `src/features/migrations/models/domain.py`
**Purpose**: Domain models for migration operations
**Dependencies**: `common/models`
**Priority**: High

```python
"""
Migration domain models.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID

class MigrationStatus(str, Enum):
    """Migration execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class MigrationScope(str, Enum):
    """Migration scope definition."""
    ALL = "all"
    ADMIN = "admin"
    REGIONAL = "regional"
    TENANT = "tenant"
    SINGLE = "single"

class DatabaseType(str, Enum):
    """Database type for migration targeting."""
    ADMIN = "admin"
    SHARED = "shared"
    ANALYTICS = "analytics"
    TENANT = "tenant"

class MigrationTarget(BaseModel):
    """Migration target definition."""
    database_id: str
    database_name: str
    schema_name: str
    database_type: DatabaseType
    region: Optional[str] = None

class MigrationProgress(BaseModel):
    """Migration progress tracking."""
    total_targets: int
    completed_targets: int
    failed_targets: int
    current_target: Optional[str] = None
    estimated_completion: Optional[datetime] = None
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_targets == 0:
            return 0.0
        return (self.completed_targets / self.total_targets) * 100

class MigrationExecution(BaseModel):
    """Migration execution record."""
    id: UUID
    batch_id: Optional[str] = None
    scope: MigrationScope
    status: MigrationStatus
    targets: List[MigrationTarget]
    progress: MigrationProgress
    started_at: datetime
    completed_at: Optional[datetime] = None
    executed_by: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MigrationSchedule(BaseModel):
    """Scheduled migration definition."""
    id: UUID
    name: str
    scope: MigrationScope
    cron_expression: Optional[str] = None
    run_at: Optional[datetime] = None
    enabled: bool = True
    created_by: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

**Development Notes:**
- Define comprehensive domain models for all migration concepts
- Include validation rules and business logic
- Add computed properties for derived values
- Follow Pydantic best practices for serialization

---

### `src/features/migrations/services/migration_service.py`
**Purpose**: Core migration service orchestrating all migration operations
**Dependencies**: `engines/`, `repositories/`, `models/`
**Priority**: High

```python
"""
Core migration service for Infrastructure API.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from loguru import logger

from src.features.migrations.models.domain import (
    MigrationExecution, MigrationScope, MigrationStatus, 
    MigrationTarget, MigrationProgress
)
from src.features.migrations.engines.dynamic_migration_engine import DynamicMigrationEngine
from src.features.migrations.repositories.migration_repository import MigrationRepository
from src.common.exceptions.base import MigrationException

class MigrationService:
    """Core service for migration operations."""
    
    def __init__(self):
        self.engine = DynamicMigrationEngine()
        self.repository = MigrationRepository()
    
    async def execute_dynamic_migration(
        self,
        scope: MigrationScope = MigrationScope.ALL,
        dry_run: bool = False,
        executed_by: str = "api"
    ) -> MigrationExecution:
        """Execute dynamic migration based on database connections."""
        
        execution_id = uuid4()
        logger.info(f"Starting dynamic migration execution {execution_id}")
        
        try:
            # Get migration plan from engine
            plan = await self.engine.get_migration_plan()
            
            # Create execution record
            targets = self._plan_to_targets(plan)
            execution = MigrationExecution(
                id=execution_id,
                scope=scope,
                status=MigrationStatus.PENDING,
                targets=targets,
                progress=MigrationProgress(
                    total_targets=len(targets),
                    completed_targets=0,
                    failed_targets=0
                ),
                started_at=datetime.utcnow(),
                executed_by=executed_by
            )
            
            # Save execution record
            await self.repository.create_execution(execution)
            
            # Execute migration plan
            if not dry_run:
                execution.status = MigrationStatus.IN_PROGRESS
                await self.repository.update_execution(execution)
                
                batch_id = await self.engine.execute_migration_plan(
                    plan, 
                    dry_run=False,
                    progress_callback=lambda p: self._update_progress(execution_id, p)
                )
                
                execution.batch_id = batch_id
                execution.status = MigrationStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
            else:
                execution.status = MigrationStatus.COMPLETED
                execution.completed_at = datetime.utcnow()
            
            await self.repository.update_execution(execution)
            return execution
            
        except Exception as e:
            logger.error(f"Migration execution {execution_id} failed: {e}")
            
            # Update execution with error
            execution.status = MigrationStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.utcnow()
            await self.repository.update_execution(execution)
            
            raise MigrationException(
                f"Migration execution failed: {str(e)}",
                details={"execution_id": str(execution_id)}
            )
    
    async def get_execution_status(self, execution_id: UUID) -> Optional[MigrationExecution]:
        """Get migration execution status."""
        return await self.repository.get_execution(execution_id)
    
    async def list_executions(
        self,
        limit: int = 50,
        status: Optional[MigrationStatus] = None
    ) -> List[MigrationExecution]:
        """List recent migration executions."""
        return await self.repository.list_executions(limit=limit, status=status)
    
    async def rollback_migration(
        self,
        execution_id: UUID,
        executed_by: str = "api"
    ) -> MigrationExecution:
        """Rollback a completed migration."""
        
        # Get original execution
        original = await self.repository.get_execution(execution_id)
        if not original:
            raise MigrationException(f"Execution {execution_id} not found")
        
        if original.status != MigrationStatus.COMPLETED:
            raise MigrationException(f"Cannot rollback execution with status {original.status}")
        
        # Create rollback execution
        rollback_id = uuid4()
        rollback = MigrationExecution(
            id=rollback_id,
            scope=original.scope,
            status=MigrationStatus.PENDING,
            targets=original.targets,
            progress=MigrationProgress(
                total_targets=len(original.targets),
                completed_targets=0,
                failed_targets=0
            ),
            started_at=datetime.utcnow(),
            executed_by=executed_by,
            metadata={"rollback_of": str(execution_id)}
        )
        
        await self.repository.create_execution(rollback)
        
        # Execute rollback (implementation depends on rollback strategy)
        # This would involve coordinating with the migration engine
        # to perform safe rollback operations
        
        return rollback
    
    def _plan_to_targets(self, plan) -> List[MigrationTarget]:
        """Convert migration plan to target list."""
        targets = []
        
        # Convert plan configurations to targets
        # Implementation depends on plan structure
        
        return targets
    
    async def _update_progress(self, execution_id: UUID, progress_data: Dict[str, Any]):
        """Update execution progress."""
        execution = await self.repository.get_execution(execution_id)
        if execution:
            # Update progress based on progress_data
            execution.progress.completed_targets = progress_data.get("completed", 0)
            execution.progress.failed_targets = progress_data.get("failed", 0)
            execution.progress.current_target = progress_data.get("current")
            
            await self.repository.update_execution(execution)

# Global service instance
migration_service: Optional[MigrationService] = None

async def init_migration_services():
    """Initialize migration services."""
    global migration_service
    migration_service = MigrationService()
    await migration_service.engine.initialize()

def get_migration_service() -> MigrationService:
    """Get migration service instance."""
    if migration_service is None:
        raise RuntimeError("Migration service not initialized")
    return migration_service
```

**Development Notes:**
- Implement comprehensive migration orchestration
- Include proper error handling and recovery
- Add progress tracking and status updates
- Follow async/await patterns throughout

---

### `src/features/migrations/routers/migrations.py`
**Purpose**: Core migration API endpoints
**Dependencies**: `services/`, `models/`, `auth/dependencies`
**Priority**: High

```python
"""
Core migration API endpoints.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from loguru import logger

from src.features.migrations.models.request import (
    MigrationExecutionRequest, MigrationRollbackRequest
)
from src.features.migrations.models.response import (
    MigrationExecutionResponse, MigrationStatusResponse, MigrationListResponse
)
from src.features.migrations.models.domain import MigrationStatus, MigrationScope
from src.features.migrations.services.migration_service import get_migration_service
from src.features.auth.dependencies import require_migration_read, require_migration_execute

router = APIRouter()

@router.post("/execute", response_model=MigrationExecutionResponse)
async def execute_migration(
    request: MigrationExecutionRequest,
    user_info = Depends(require_migration_execute)
):
    """Execute migration based on scope and parameters."""
    
    logger.info(
        f"Migration execution requested by {user_info.get('sub')}",
        extra={
            "scope": request.scope,
            "dry_run": request.dry_run,
            "user_id": user_info.get("sub")
        }
    )
    
    try:
        migration_service = get_migration_service()
        execution = await migration_service.execute_dynamic_migration(
            scope=request.scope,
            dry_run=request.dry_run,
            executed_by=user_info.get("sub", "unknown")
        )
        
        return MigrationExecutionResponse.from_domain(execution)
        
    except Exception as e:
        logger.error(f"Migration execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration execution failed: {str(e)}"
        )

@router.get("/status/{execution_id}", response_model=MigrationStatusResponse)
async def get_migration_status(
    execution_id: UUID,
    user_info = Depends(require_migration_read)
):
    """Get status of specific migration execution."""
    
    migration_service = get_migration_service()
    execution = await migration_service.get_execution_status(execution_id)
    
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Migration execution {execution_id} not found"
        )
    
    return MigrationStatusResponse.from_domain(execution)

@router.get("/", response_model=MigrationListResponse)
async def list_migrations(
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: Optional[MigrationStatus] = Query(None, alias="status"),
    user_info = Depends(require_migration_read)
):
    """List recent migration executions."""
    
    migration_service = get_migration_service()
    executions = await migration_service.list_executions(
        limit=limit,
        status=status_filter
    )
    
    return MigrationListResponse(
        executions=[MigrationExecutionResponse.from_domain(e) for e in executions],
        total=len(executions)
    )

@router.post("/rollback", response_model=MigrationExecutionResponse)
async def rollback_migration(
    request: MigrationRollbackRequest,
    user_info = Depends(require_migration_execute)
):
    """Rollback a completed migration."""
    
    logger.warning(
        f"Migration rollback requested by {user_info.get('sub')}",
        extra={
            "execution_id": str(request.execution_id),
            "user_id": user_info.get("sub")
        }
    )
    
    try:
        migration_service = get_migration_service()
        rollback_execution = await migration_service.rollback_migration(
            execution_id=request.execution_id,
            executed_by=user_info.get("sub", "unknown")
        )
        
        return MigrationExecutionResponse.from_domain(rollback_execution)
        
    except Exception as e:
        logger.error(f"Migration rollback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration rollback failed: {str(e)}"
        )

@router.get("/health")
async def migration_health():
    """Check migration system health."""
    
    try:
        migration_service = get_migration_service()
        # Perform basic health checks
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "migration_engine": "operational"
        }
        
    except Exception as e:
        logger.error(f"Migration health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Migration system unavailable"
        )
```

**Development Notes:**
- Implement all core migration endpoints with proper authentication
- Include comprehensive error handling and logging
- Follow FastAPI best practices for request/response models
- Add proper status codes and error messages

---

## 🗄️ Database Management

### `src/features/databases/services/database_service.py`
**Purpose**: Database connection management service
**Dependencies**: `repositories/`, `models/`
**Priority**: Medium

```python
"""
Database connection management service.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from loguru import logger

from src.features.databases.models.domain import DatabaseConnection, ConnectionHealth
from src.features.databases.repositories.database_repository import DatabaseRepository
from src.common.exceptions.base import DatabaseConnectionException

class DatabaseService:
    """Service for managing database connections."""
    
    def __init__(self):
        self.repository = DatabaseRepository()
    
    async def create_connection(
        self,
        connection_data: Dict[str, Any],
        created_by: str
    ) -> DatabaseConnection:
        """Create new database connection."""
        
        try:
            # Validate connection before creating
            await self._test_connection(connection_data)
            
            # Create connection record
            connection = await self.repository.create_connection(connection_data, created_by)
            
            logger.info(f"Database connection created: {connection.id}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to create database connection: {e}")
            raise DatabaseConnectionException(f"Connection creation failed: {str(e)}")
    
    async def test_connection(self, connection_id: UUID) -> ConnectionHealth:
        """Test database connection health."""
        
        connection = await self.repository.get_connection(connection_id)
        if not connection:
            raise DatabaseConnectionException(f"Connection {connection_id} not found")
        
        return await self._test_connection_health(connection)
    
    async def list_connections(
        self,
        region: Optional[str] = None,
        connection_type: Optional[str] = None,
        active_only: bool = True
    ) -> List[DatabaseConnection]:
        """List database connections with optional filtering."""
        
        return await self.repository.list_connections(
            region=region,
            connection_type=connection_type,
            active_only=active_only
        )
    
    async def update_connection(
        self,
        connection_id: UUID,
        update_data: Dict[str, Any],
        updated_by: str
    ) -> DatabaseConnection:
        """Update database connection."""
        
        try:
            # Test connection if connection details changed
            if any(key in update_data for key in ["host", "port", "database_name", "username", "password"]):
                await self._test_connection(update_data)
            
            connection = await self.repository.update_connection(
                connection_id, update_data, updated_by
            )
            
            logger.info(f"Database connection updated: {connection_id}")
            return connection
            
        except Exception as e:
            logger.error(f"Failed to update database connection {connection_id}: {e}")
            raise DatabaseConnectionException(f"Connection update failed: {str(e)}")
    
    async def delete_connection(self, connection_id: UUID, deleted_by: str) -> bool:
        """Delete database connection (soft delete)."""
        
        try:
            success = await self.repository.delete_connection(connection_id, deleted_by)
            
            if success:
                logger.info(f"Database connection deleted: {connection_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete database connection {connection_id}: {e}")
            raise DatabaseConnectionException(f"Connection deletion failed: {str(e)}")
    
    async def _test_connection(self, connection_data: Dict[str, Any]) -> bool:
        """Test database connection with provided data."""
        
        # Implementation would test actual database connectivity
        # This is a placeholder for the actual connection testing logic
        
        try:
            import asyncpg
            
            pool = await asyncpg.create_pool(
                host=connection_data["host"],
                port=connection_data["port"],
                database=connection_data["database_name"],
                user=connection_data["username"],
                password=connection_data["password"],
                min_size=1,
                max_size=1,
                command_timeout=5
            )
            
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            await pool.close()
            return True
            
        except Exception as e:
            raise DatabaseConnectionException(f"Connection test failed: {str(e)}")
    
    async def _test_connection_health(self, connection: DatabaseConnection) -> ConnectionHealth:
        """Test connection health and return detailed status."""
        
        # Implementation would perform comprehensive health checks
        # This is a placeholder for actual health checking logic
        
        return ConnectionHealth(
            connection_id=connection.id,
            is_healthy=True,
            response_time_ms=50,
            last_checked=datetime.utcnow(),
            error_message=None
        )
```

**Development Notes:**
- Implement comprehensive database connection management
- Include connection testing and health monitoring
- Add proper error handling for connection failures
- Follow repository pattern for data access

---

## 📊 Health and Monitoring

### `src/features/health/routers/system.py`
**Purpose**: System health check endpoints
**Dependencies**: `services/health_service`
**Priority**: Medium

```python
"""
System health check endpoints.
"""
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from loguru import logger

from src.features.health.models.health import SystemHealth, ServiceHealth
from src.features.health.services.health_service import get_health_service

router = APIRouter()

@router.get("/", response_model=SystemHealth)
async def health_check():
    """Basic health check endpoint."""
    
    return SystemHealth(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
        environment="development"  # This would come from settings
    )

@router.get("/detailed", response_model=Dict[str, Any])
async def detailed_health_check():
    """Detailed health check including all services."""
    
    try:
        health_service = get_health_service()
        health_status = await health_service.check_all_services()
        
        return {
            "overall_status": health_status.overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "services": [service.dict() for service in health_status.services],
            "summary": {
                "total_services": len(health_status.services),
                "healthy_services": len([s for s in health_status.services if s.is_healthy]),
                "unhealthy_services": len([s for s in health_status.services if not s.is_healthy])
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Health check service unavailable"
        )

@router.get("/services/{service_name}", response_model=ServiceHealth)
async def service_health_check(service_name: str):
    """Check health of specific service."""
    
    try:
        health_service = get_health_service()
        service_health = await health_service.check_service(service_name)
        
        if not service_health:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service {service_name} not found"
            )
        
        return service_health
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Service health check failed for {service_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed for service {service_name}"
        )

@router.get("/metrics")
async def system_metrics():
    """Get basic system metrics."""
    
    try:
        health_service = get_health_service()
        metrics = await health_service.get_system_metrics()
        
        return metrics
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Metrics collection unavailable"
        )
```

**Development Notes:**
- Implement comprehensive health checking for all services
- Include detailed metrics and monitoring endpoints
- Add proper error handling for service failures
- Follow monitoring best practices

---

## 🧪 Testing Guidelines

### Unit Tests
- **Coverage**: Aim for >95% code coverage
- **Pattern**: One test file per source file (`test_*.py`)
- **Framework**: pytest with async support
- **Mocking**: Use pytest-asyncio and aioresponses

### Integration Tests
- **Database**: Use test database with transaction rollback
- **External Services**: Mock Keycloak and other external dependencies
- **End-to-End**: Test complete workflows from API to database

### Development Workflow
1. **TDD Approach**: Write tests before implementation
2. **Continuous Testing**: Run tests on every change
3. **Quality Gates**: All tests must pass before merge
4. **Performance Testing**: Include performance benchmarks

This file-by-file guide provides the detailed implementation roadmap for the Infrastructure API restructuring project. Each file includes specific code examples, development notes, and integration guidelines to ensure consistent and high-quality implementation.