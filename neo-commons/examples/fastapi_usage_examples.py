"""FastAPI Configuration Usage Examples for neo-commons.

This file demonstrates how to use the neo-commons FastAPI infrastructure
to create standardized FastAPI applications with minimal boilerplate.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List, Optional
import asyncio

# Import neo-commons FastAPI infrastructure
from neo_commons.infrastructure.fastapi import (
    FastAPIFactory,
    create_fastapi_factory,
    create_admin_api,
    create_tenant_api,
    create_deployment_api,
    create_development_api,
    create_production_api,
    AdminAPIConfig,
    TenantAPIConfig,
    DocsConfig,
    Environment,
    ServiceType,
    setup_service_dependencies,
    create_user_service_dependency,
    create_cache_service_dependency,
    get_app_config
)
from neo_commons.infrastructure.middleware import MiddlewareFactory
from neo_commons.features.users.services import UserService
from neo_commons.features.cache.services import CacheService
from neo_commons.features.database.services import DatabaseService
from neo_commons.features.tenants.services import TenantService
from neo_commons.core.value_objects import UserId


# Example 1: Quick Development API
def example_development_api():
    """Create a simple development API with minimal configuration."""
    
    app = create_development_api(
        service_type=ServiceType.CUSTOM,
        title="My Development API",
        description="Quick development API with minimal setup",
        port=8003
    )
    
    @app.get("/")
    async def root():
        return {"message": "Development API is running!"}
    
    @app.get("/config")
    async def get_config(config = Depends(get_app_config)):
        return {
            "service_type": config.service_type.value,
            "environment": config.environment.value,
            "debug": config.debug
        }
    
    return app


# Example 2: Admin API with Full Configuration
async def example_admin_api():
    """Create a production-ready Admin API with full middleware stack."""
    
    # Initialize services (normally done in your service layer)
    user_service = UserService()  # Your actual implementation
    cache_service = CacheService()  # Your actual implementation
    database_service = DatabaseService()  # Your actual implementation
    
    # Create factory with services
    factory = create_fastapi_factory(
        user_service=user_service,
        cache_service=cache_service,
        database_service=database_service
    )
    
    # Create Admin API with custom configuration
    app = create_admin_api(
        factory,
        config_overrides={
            "environment": Environment.PRODUCTION,
            "jwt_secret": "your-production-jwt-secret",
            "enable_audit_logging": True,
            "enable_system_metrics": True
        }
    )
    
    # Get dependency functions
    get_user_service = create_user_service_dependency()
    get_cache_service = create_cache_service_dependency()
    
    # Add admin-specific routes
    @app.get("/admin/users")
    async def list_users(
        user_service: UserService = Depends(get_user_service),
        current_user: UserId = Depends()  # From auth middleware
    ):
        """List all platform users - admin only."""
        users = await user_service.list_all_users()
        return {"users": users}
    
    @app.get("/admin/health/detailed")
    async def detailed_health(
        user_service: UserService = Depends(get_user_service),
        cache_service: CacheService = Depends(get_cache_service)
    ):
        """Detailed health check for admin monitoring."""
        health_data = {
            "database": "unknown",
            "cache": "unknown",
            "user_service": "unknown"
        }
        
        # Check each service
        try:
            await user_service.health_check()
            health_data["user_service"] = "healthy"
        except Exception as e:
            health_data["user_service"] = f"unhealthy: {str(e)}"
        
        try:
            await cache_service.ping()
            health_data["cache"] = "healthy"
        except Exception as e:
            health_data["cache"] = f"unhealthy: {str(e)}"
        
        return health_data
    
    return app


# Example 3: Tenant API with Multi-tenancy
async def example_tenant_api():
    """Create a multi-tenant API with tenant context middleware."""
    
    # Initialize services
    user_service = UserService()
    cache_service = CacheService()
    tenant_service = TenantService()
    database_service = DatabaseService()
    
    # Create factory
    factory = create_fastapi_factory(
        user_service=user_service,
        cache_service=cache_service,
        tenant_service=tenant_service,
        database_service=database_service
    )
    
    # Create Tenant API
    app = create_tenant_api(
        factory,
        config_overrides={
            "environment": Environment.STAGING,
            "tenant_header": "X-Tenant-ID",
            "subdomain_extraction": True,
            "enable_tenant_context": True
        }
    )
    
    # Tenant-specific routes
    @app.get("/tenant/profile")
    async def get_tenant_profile(
        tenant_service: TenantService = Depends(create_tenant_service_dependency()),
        # Tenant context automatically injected by middleware
        request  # Access to tenant context via request.state.tenant_id
    ):
        """Get current tenant profile."""
        tenant_id = getattr(request.state, 'tenant_id', None)
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        tenant = await tenant_service.get_tenant(tenant_id)
        return {"tenant": tenant}
    
    @app.get("/tenant/users")
    async def list_tenant_users(
        user_service: UserService = Depends(create_user_service_dependency()),
        request  # For tenant context
    ):
        """List users within current tenant."""
        tenant_id = getattr(request.state, 'tenant_id', None)
        if not tenant_id:
            raise HTTPException(status_code=400, detail="Tenant context required")
        
        users = await user_service.list_tenant_users(tenant_id)
        return {"users": users}
    
    return app


# Example 4: Custom API with Manual Configuration
async def example_custom_api():
    """Create a custom API with manual configuration for specific needs."""
    
    # Custom configuration
    config = AdminAPIConfig(
        title="Custom Service API",
        description="Custom API with specific requirements",
        port=8005,
        environment=Environment.PRODUCTION,
        enable_auth=True,
        enable_tenant_context=False,  # Single-tenant custom service
        enable_audit_logging=True,
        cors_config=CORSConfig.from_environment(Environment.PRODUCTION)
    )
    
    # Initialize services
    user_service = UserService()
    cache_service = CacheService()
    database_service = DatabaseService()
    
    # Setup service dependencies
    setup_service_dependencies(
        user_service=user_service,
        cache_service=cache_service,
        database_service=database_service
    )
    
    # Create factory and app
    factory = FastAPIFactory(
        user_service=user_service,
        cache_service=cache_service,
        database_service=database_service
    )
    
    app = factory.create_app(config)
    
    # Custom routes
    @app.get("/custom/status")
    async def custom_status():
        return {"status": "Custom API operational"}
    
    @app.post("/custom/process")
    async def process_data(data: dict):
        """Custom data processing endpoint."""
        # Your custom business logic here
        processed_data = {"processed": True, "original": data}
        return processed_data
    
    return app


# Example 5: Production API with Complete Setup
async def example_production_setup():
    """Complete production setup with all services and monitoring."""
    
    # Initialize all services with production configuration
    user_service = UserService()
    cache_service = CacheService()
    database_service = DatabaseService()
    tenant_service = TenantService()
    
    # Create production-ready API
    app = create_production_api(
        service_type=ServiceType.ADMIN_API,
        user_service=user_service,
        cache_service=cache_service,
        database_service=database_service,
        tenant_service=tenant_service,
        jwt_secret="your-secure-production-jwt-secret",
        config_overrides={
            "cors_config": {
                "allow_origins": [
                    "https://admin.yourdomain.com",
                    "https://app.yourdomain.com"
                ]
            },
            "security_config": {
                "rate_limit": "1000/minute",
                "burst_rate_limit": "50/second",
                "enable_https_redirect": True
            }
        }
    )
    
    # Production monitoring endpoints
    @app.get("/monitoring/metrics")
    async def get_metrics():
        """Production metrics endpoint."""
        return {
            "requests_per_minute": 120,
            "response_time_p95": 45,
            "error_rate": 0.01,
            "active_users": 250
        }
    
    @app.get("/monitoring/alerts")
    async def get_alerts():
        """Active alerts and warnings."""
        return {
            "critical": [],
            "warnings": [
                {"type": "high_response_time", "threshold": 100, "current": 95}
            ]
        }
    
    return app


# Example 6: Testing Setup
def example_testing_setup():
    """Setup for testing with mock services."""
    from unittest.mock import AsyncMock
    
    # Create mock services
    mock_user_service = AsyncMock(spec=UserService)
    mock_cache_service = AsyncMock(spec=CacheService)
    mock_database_service = AsyncMock(spec=DatabaseService)
    
    # Setup mock responses
    mock_user_service.health_check.return_value = None
    mock_cache_service.ping.return_value = "PONG"
    mock_database_service.health_check.return_value = None
    
    # Create test app
    factory = create_fastapi_factory(
        user_service=mock_user_service,
        cache_service=mock_cache_service,
        database_service=mock_database_service
    )
    
    app = create_development_api(
        service_type=ServiceType.CUSTOM,
        title="Test API",
        description="API for testing"
    )
    
    # Override dependencies for testing
    app.dependency_overrides[create_user_service_dependency()] = lambda: mock_user_service
    app.dependency_overrides[create_cache_service_dependency()] = lambda: mock_cache_service
    
    return app, {
        "user_service": mock_user_service,
        "cache_service": mock_cache_service,
        "database_service": mock_database_service
    }


# Example 7: Environment-specific Configuration
def example_environment_configs():
    """Examples of environment-specific configurations."""
    
    # Development environment
    dev_config = AdminAPIConfig(
        environment=Environment.DEVELOPMENT,
        debug=True,
        enable_auth=False,  # Simplified for development
        cors_config=CORSConfig(allow_origins=["*"])  # Permissive CORS
    )
    
    # Staging environment  
    staging_config = AdminAPIConfig(
        environment=Environment.STAGING,
        debug=True,
        enable_auth=True,
        cors_config=CORSConfig.from_environment(Environment.STAGING)
    )
    
    # Production environment
    prod_config = AdminAPIConfig(
        environment=Environment.PRODUCTION,
        debug=False,
        enable_auth=True,
        enable_audit_logging=True,
        cors_config=CORSConfig.from_environment(Environment.PRODUCTION),
        security_config=SecurityConfig.from_environment(
            Environment.PRODUCTION, 
            ServiceType.ADMIN_API
        )
    )
    
    return {
        "development": dev_config,
        "staging": staging_config,
        "production": prod_config
    }


# Example 8: Scalar API Documentation Configuration
def example_scalar_configuration():
    """Example of configuring Scalar API documentation."""
    
    # Custom Scalar configuration
    custom_docs_config = DocsConfig(
        title="Advanced API with Scalar",
        description="API with custom Scalar documentation",
        use_scalar=True,
        docs_url="/docs",  # Scalar endpoint
        swagger_url="/swagger",  # Traditional Swagger UI fallback
        redoc_url="/redoc",  # ReDoc still available
        scalar_config={
            "layout": "modern",
            "theme": "purple",  # purple, default, moon, saturn, kepler, mars, blueprint, alternate, none
            "show_sidebar": True,
            "hide_download_button": False,
            "hide_test_request_button": False,
            "servers": [
                {"url": "https://api.example.com", "description": "Production"},
                {"url": "https://staging-api.example.com", "description": "Staging"},
                {"url": "http://localhost:8000", "description": "Development"}
            ],
            "custom_css": """
                .scalar-api-reference {
                    --scalar-color-1: #2a2f45;
                    --scalar-color-2: #757575;
                    --scalar-color-3: #8e8e8e;
                    --scalar-radius: 6px;
                }
            """,
            "favicon": "https://example.com/favicon.ico"
        }
    )
    
    # Create API with custom Scalar docs
    config = AdminAPIConfig(
        title="API with Custom Scalar",
        docs_config=custom_docs_config,
        environment=Environment.DEVELOPMENT
    )
    
    factory = FastAPIFactory()
    app = factory.create_app(config)
    
    @app.get("/")
    async def root():
        return {
            "message": "API with Scalar documentation",
            "docs": {
                "scalar": "/docs",
                "swagger": "/swagger", 
                "redoc": "/redoc"
            }
        }
    
    @app.get("/features")
    async def features():
        """Example endpoint to showcase in Scalar docs."""
        return {
            "scalar_features": [
                "Modern UI with beautiful design",
                "Interactive API testing",
                "Multiple theme options",
                "Better performance than Swagger UI",
                "Mobile-friendly responsive design",
                "Advanced search and filtering",
                "Custom CSS styling support"
            ]
        }
    
    return app


# Example 9: Environment-specific Scalar Configuration
def example_environment_scalar():
    """Examples of environment-specific Scalar configurations."""
    
    # Development: Full-featured Scalar with testing capabilities
    dev_docs = DocsConfig.from_environment(Environment.DEVELOPMENT, ServiceType.ADMIN_API)
    dev_docs.scalar_config.update({
        "theme": "purple",
        "layout": "modern",
        "show_sidebar": True,
        "hide_download_button": False,
        "hide_test_request_button": False,  # Enable testing in dev
        "custom_css": "/* Development styling with extra padding */"
    })
    
    # Staging: Limited Scalar with restricted testing
    staging_docs = DocsConfig.from_environment(Environment.STAGING, ServiceType.ADMIN_API)
    staging_docs.scalar_config.update({
        "theme": "default",
        "hide_download_button": True,
        "hide_test_request_button": True,  # Disable testing in staging
        "custom_css": "/* Staging environment - restricted mode */"
    })
    
    # Production: No docs (for security)
    prod_docs = DocsConfig.from_environment(Environment.PRODUCTION, ServiceType.ADMIN_API)
    # Production automatically disables all docs
    
    return {
        "development": dev_docs,
        "staging": staging_docs,
        "production": prod_docs
    }


# Example 10: Startup and Shutdown Handlers
async def example_lifecycle_management():
    """Example with custom startup and shutdown handlers."""
    
    # Initialize services
    user_service = UserService()
    cache_service = CacheService()
    database_service = DatabaseService()
    
    # Create startup tasks
    async def initialize_database():
        """Initialize database connections."""
        await database_service.initialize()
        print("Database initialized")
    
    async def warm_cache():
        """Warm up the cache with frequently accessed data."""
        await cache_service.warm_up()
        print("Cache warmed up")
    
    # Create shutdown tasks
    async def cleanup_database():
        """Clean up database connections."""
        await database_service.cleanup()
        print("Database cleaned up")
    
    async def clear_cache():
        """Clear cache before shutdown."""
        await cache_service.clear()
        print("Cache cleared")
    
    # Create lifecycle handlers
    from neo_commons.infrastructure.fastapi import create_startup_handler, create_shutdown_handler
    
    startup_handler = create_startup_handler(
        initialize_database,
        warm_cache
    )
    
    shutdown_handler = create_shutdown_handler(
        clear_cache,
        cleanup_database
    )
    
    # Create lifespan context manager
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await startup_handler()
        yield
        # Shutdown
        await shutdown_handler()
    
    # Create app with custom lifespan
    factory = create_fastapi_factory(
        user_service=user_service,
        cache_service=cache_service,
        database_service=database_service
    )
    
    config = AdminAPIConfig()
    app = factory.create_app(config, lifespan=lifespan)
    
    return app


if __name__ == "__main__":
    """Run examples for demonstration."""
    
    print("Neo-commons FastAPI Configuration Examples")
    print("=" * 50)
    
    # Example 1: Development API
    print("\n1. Creating Development API...")
    dev_app = example_development_api()
    print(f"   ✓ Development API created: {dev_app.title}")
    
    # Example 7: Environment configs
    print("\n7. Environment-specific configurations...")
    env_configs = example_environment_configs()
    for env_name, config in env_configs.items():
        print(f"   ✓ {env_name.capitalize()}: debug={config.debug}, auth={config.enable_auth}")
    
    # Example 8: Scalar configuration
    print("\n8. Scalar API documentation...")
    scalar_app = example_scalar_configuration()
    print(f"   ✓ Scalar app created: {scalar_app.title}")
    print("   ✓ Scalar docs at /docs, Swagger at /swagger, ReDoc at /redoc")
    
    # Example 9: Environment-specific Scalar
    print("\n9. Environment-specific Scalar configurations...")
    scalar_configs = example_environment_scalar()
    for env_name, docs_config in scalar_configs.items():
        scalar_enabled = docs_config.use_scalar if hasattr(docs_config, 'use_scalar') else False
        print(f"   ✓ {env_name.capitalize()}: scalar={scalar_enabled}")
    
    # Example 6: Testing setup
    print("\n6. Testing setup with mocks...")
    test_app, mocks = example_testing_setup()
    print(f"   ✓ Test app created with {len(mocks)} mock services")
    
    print("\nAll examples completed successfully!")
    print("\nScalar Features:")
    print("  - Modern, fast API documentation UI")
    print("  - Interactive testing capabilities")
    print("  - Multiple themes (purple, default, moon, saturn, etc.)")
    print("  - Custom CSS styling support")
    print("  - Mobile-friendly responsive design")
    print("\nTo see async examples, run individual functions:")
    print("  - await example_admin_api()")
    print("  - await example_tenant_api()")
    print("  - await example_custom_api()")
    print("  - await example_production_setup()")
    print("  - await example_lifecycle_management()")
    print("\nScalar Documentation:")
    print("  - pip install scalar-fastapi")
    print("  - Visit /docs for Scalar UI")
    print("  - Visit /swagger for traditional Swagger UI")
    print("  - Visit /redoc for ReDoc documentation")