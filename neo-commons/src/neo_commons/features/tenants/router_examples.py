"""Example usage of core tenant routers with database connection and schema parameters.

Demonstrates how services can use tenant routers by providing database connection
and schema name as parameters, following the auth feature pattern.
"""

from fastapi import FastAPI
from typing import Optional

# Import existing neo-commons infrastructure
from ...features.database.services import DatabaseService
from ...features.cache.services import CacheService
from ...infrastructure.configuration.services import ConfigurationService

# Import tenant feature components
from . import (
    tenant_router,
    TenantService,
    TenantDatabaseRepository,
    TenantCacheAdapter,
    TenantConfigurationResolver,
    TenantDependencies
)
from .routers.tenant_router import get_tenant_service, get_tenant_dependencies


async def setup_tenant_router_with_admin_database(app: FastAPI) -> None:
    """Example: Setup tenant router using admin database connection.
    
    This shows how NeoAdminApi would use tenant routers with admin database.
    """
    
    # Initialize existing database service
    database_service = DatabaseService()
    await database_service.initialize()
    
    # Create tenant repository using admin schema
    tenant_repository = TenantDatabaseRepository(
        database_repository=database_service.repository,
        schema="admin"  # Use admin schema
    )
    
    # Initialize cache service
    cache_service = CacheService()
    await cache_service.initialize()
    
    # Create tenant cache adapter
    tenant_cache = TenantCacheAdapter(
        cache=cache_service.cache,
        ttl=3600
    )
    
    # Initialize configuration service
    config_service = ConfigurationService()
    await config_service.initialize()
    
    # Create tenant config resolver
    tenant_config_resolver = TenantConfigurationResolver(
        config_provider=config_service.provider
    )
    
    # Create tenant service with all dependencies
    tenant_service = TenantService(
        repository=tenant_repository,
        cache=tenant_cache,
        config_resolver=tenant_config_resolver
    )
    
    # Create tenant dependencies
    tenant_dependencies = TenantDependencies(
        tenant_repository=tenant_repository,
        tenant_cache=tenant_cache,
        config_resolver=tenant_config_resolver
    )
    
    # Override router dependencies (following auth pattern)
    tenant_router.dependency_overrides = {
        get_tenant_service: lambda: tenant_service,
        get_tenant_dependencies: lambda: tenant_dependencies
    }
    
    # Include router in FastAPI app
    app.include_router(tenant_router, prefix="/api/v1")
    
    print("✅ Tenant router configured with admin database")


async def setup_tenant_router_with_custom_connection(
    app: FastAPI,
    connection_name: str,
    schema_name: str
) -> None:
    """Example: Setup tenant router with custom database connection and schema.
    
    This shows how any service can use tenant routers with specific connections.
    """
    
    # Initialize database service with custom connection
    database_service = DatabaseService()
    await database_service.initialize()
    
    # Verify connection exists (would be added at app startup)
    if not await database_service.connection_registry.has_connection(connection_name):
        raise ValueError(f"Database connection '{connection_name}' not found")
    
    # Create tenant repository with custom schema
    tenant_repository = TenantDatabaseRepository(
        database_repository=database_service.repository,
        schema=schema_name  # Use custom schema
    )
    
    # Minimal tenant service (no cache or config in this example)
    tenant_service = TenantService(repository=tenant_repository)
    
    # Minimal dependencies
    tenant_dependencies = TenantDependencies(tenant_repository=tenant_repository)
    
    # Override router dependencies
    tenant_router.dependency_overrides = {
        get_tenant_service: lambda: tenant_service,
        get_tenant_dependencies: lambda: tenant_dependencies
    }
    
    # Include router
    app.include_router(tenant_router, prefix="/api/v1")
    
    print(f"✅ Tenant router configured with connection '{connection_name}' and schema '{schema_name}'")


async def setup_tenant_router_regional_database(
    app: FastAPI,
    region: str = "us-east"
) -> None:
    """Example: Setup tenant router for regional database.
    
    This shows how to use tenant routers with regional databases.
    """
    
    # Initialize database service
    database_service = DatabaseService()
    await database_service.initialize()
    
    # Regional connection mapping
    regional_connections = {
        "us-east": "neofast-shared-us-primary",
        "eu-west": "neofast-shared-eu-primary"
    }
    
    connection_name = regional_connections.get(region)
    if not connection_name:
        raise ValueError(f"Unsupported region: {region}")
    
    # Create repository for regional tenant management
    tenant_repository = TenantDatabaseRepository(
        database_repository=database_service.repository,
        schema="tenant_management"  # Regional schema for tenant metadata
    )
    
    # Regional cache (if available)
    cache_service = CacheService()
    await cache_service.initialize()
    tenant_cache = TenantCacheAdapter(cache=cache_service.cache)
    
    # Create services
    tenant_service = TenantService(
        repository=tenant_repository,
        cache=tenant_cache
    )
    
    tenant_dependencies = TenantDependencies(
        tenant_repository=tenant_repository,
        tenant_cache=tenant_cache
    )
    
    # Override dependencies
    tenant_router.dependency_overrides = {
        get_tenant_service: lambda: tenant_service,
        get_tenant_dependencies: lambda: tenant_dependencies
    }
    
    # Include router with regional prefix
    app.include_router(tenant_router, prefix=f"/api/v1/regions/{region}")
    
    print(f"✅ Tenant router configured for region '{region}'")


def create_tenant_enabled_app() -> FastAPI:
    """Example: Create FastAPI app with tenant management enabled.
    
    This demonstrates the complete setup process.
    """
    
    app = FastAPI(
        title="Tenant Management API",
        description="API with tenant management using neo-commons routers",
        version="1.0.0"
    )
    
    @app.on_event("startup")
    async def startup():
        """Initialize tenant router on startup."""
        await setup_tenant_router_with_admin_database(app)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "features": ["tenant_management"]}
    
    return app


# Usage in different services:

def neoadminapi_usage():
    """How NeoAdminApi would use tenant routers."""
    app = FastAPI()
    
    @app.on_event("startup")
    async def setup():
        # NeoAdminApi uses admin database
        await setup_tenant_router_with_admin_database(app)
    
    return app


def neotenantapi_usage():
    """How NeoTenantApi might use tenant routers for tenant-specific operations."""
    app = FastAPI()
    
    @app.on_event("startup") 
    async def setup():
        # NeoTenantApi might use regional databases
        await setup_tenant_router_regional_database(app, region="us-east")
    
    return app


def custom_service_usage():
    """How a custom service would use tenant routers."""
    app = FastAPI()
    
    @app.on_event("startup")
    async def setup():
        # Custom service uses specific connection and schema
        await setup_tenant_router_with_custom_connection(
            app,
            connection_name="custom_tenant_db",
            schema_name="tenant_registry"
        )
    
    return app


# Key benefits of this router architecture:
#
# 1. **Reusable**: Same router works across all services
# 2. **Flexible**: Accepts any database connection and schema
# 3. **DRY**: No duplication between services
# 4. **Protocol-Based**: Easy to test and mock
# 5. **Consistent**: Same API endpoints across services
# 6. **Override Pattern**: Following established auth feature pattern
#
# Services just need to:
# 1. Initialize their database/cache/config services
# 2. Create tenant service/dependencies with their connections
# 3. Override router dependencies
# 4. Include router in their FastAPI app