"""
FastAPI application factory and configuration.
"""
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference
from loguru import logger

from src.common.config.settings import settings
from src.common.database.connection import init_database, close_database
from src.common.cache.client import init_cache, close_cache
from src.common.middleware import setup_middleware
from src.common.openapi_config import configure_openapi
from src.common.endpoints import register_health_endpoints, register_debug_endpoints
from src.common.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    
    try:
        # Initialize database connections
        await init_database()
        
        # Initialize cache (optional - will warn if unavailable)
        try:
            await init_cache()
        except Exception as e:
            logger.warning(f"Cache initialization failed, continuing without cache: {e}")
        
        # Sync permissions on startup
        from src.features.auth.services.permission_manager import PermissionSyncManager
        logger.info("Syncing permissions from code to database...")
        sync_manager = PermissionSyncManager()
        sync_result = await sync_manager.sync_permissions(
            app=app,
            dry_run=False,  # Actually apply changes
            force_update=False  # Only update if changed
        )
        
        if sync_result['success']:
            logger.info(f"Permission sync completed: {sync_result['stats']}")
        else:
            logger.warning(f"Permission sync had issues: {sync_result.get('error')}")
        
        # Initialize other services as needed
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    try:
        # Close database connections
        await close_database()
        
        # Close cache connections (if available)
        try:
            await close_cache()
        except Exception as e:
            logger.warning(f"Cache shutdown failed (non-critical): {e}")
        
        logger.info("Application shutdown complete")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Create FastAPI instance
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Platform Administration API for NeoMultiTenant",
        docs_url="/swagger" if not settings.is_production else None,  # Swagger at /swagger
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan
    )
    
    # Configure nested tag groups for better API documentation organization
    if not settings.is_production:
        configure_openapi(app)
    
    # Setup organized middleware stack
    middleware_manager = setup_middleware(app)
    logger.info(f"Configured middleware stack for {settings.environment} environment")
    
    # Log middleware status in development
    if settings.is_development:
        middleware_status = middleware_manager.get_middleware_status()
        logger.info("Active middleware:", **middleware_status)
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register routers
    register_routers(app)
    
    # Add Scalar documentation at /docs
    if not settings.is_production:
        @app.get("/docs", include_in_schema=False)
        async def scalar_docs():
            return get_scalar_api_reference(
                openapi_url=app.openapi_url,
                title=app.title,
                scalar_favicon_url="https://fastapi.tiangolo.com/img/favicon.png"
            )
    
    # Register health and debug endpoints
    register_health_endpoints(app)
    register_debug_endpoints(app)
    
    return app


def _import_routers():
    """Import all application routers.
    
    Returns:
        Dictionary of router groups with their routers
    """
    from src.features.regions import database_router, region_router
    from src.features.auth.routers.auth import router as auth_router
    from src.features.auth.routers.permissions import router as permissions_router
    from src.features.tenants.routers.v1 import router as tenants_router
    from src.features.organizations.routers.v1 import router as organizations_router
    from src.features.users.routers.v1 import router as users_router
    from src.features.users.routers.me import router as users_me_router
    from src.features.roles import roles_router
    from src.features.reference_data import reference_data_router
    
    return {
        "auth": {
            "auth": (auth_router, "/auth", ["Authentication"]),
            "permissions": (permissions_router, "/permissions", ["Permissions"]),
            "roles": (roles_router, "/roles", ["Roles"])
        },
        "users": {
            "users_me": (users_me_router, "/users/me", ["User Profile"]),
            "users": (users_router, "/users", ["Platform Users"])
        },
        "organizations": {
            "organizations": (organizations_router, "/organizations", ["Organizations"])
        },
        "tenants": {
            "tenants": (tenants_router, "/tenants", ["Tenants"])
        },
        "infrastructure": {
            "regions": (region_router, "/regions", ["Regions"]),
            "databases": (database_router, "/databases", ["Database Connections"])
        },
        "reference_data": {
            "reference_data": (reference_data_router, "", [])
        }
    }


def _register_router_group(app: FastAPI, routers: Dict, with_prefix: bool = False) -> None:
    """Register a group of routers.
    
    Args:
        app: FastAPI application instance
        routers: Dictionary of routers with their configuration
        with_prefix: Whether to include API prefix
    """
    for router_info in routers.values():
        router, path, tags = router_info
        
        if with_prefix and settings.api_prefix:
            # Register with API prefix, hidden from docs
            app.include_router(
                router,
                prefix=f"{settings.api_prefix}{path}",
                tags=tags,
                include_in_schema=False
            )
        else:
            # Register without prefix, shown in docs
            app.include_router(
                router,
                prefix=path,
                tags=tags
            )


def register_routers(app: FastAPI) -> None:
    """Register all application routers.
    
    By default, routers are registered without a prefix (e.g., /databases).
    If ENABLE_PREFIX_ROUTES is true, they are ALSO registered with the API prefix.
    """
    # Import all routers
    router_groups = _import_routers()
    
    # PRIMARY: Register WITHOUT API prefix (default, shown in docs)
    # Note: Order matters - /users/me must be registered before /users
    for group_name, routers in router_groups.items():
        _register_router_group(app, routers, with_prefix=False)
    
    # OPTIONAL: Also register WITH API prefix (for backward compatibility)
    # Only if explicitly enabled to avoid duplication in docs
    if settings.enable_prefix_routes and settings.api_prefix:
        for group_name, routers in router_groups.items():
            _register_router_group(app, routers, with_prefix=True)
    
    # Log registration summary
    logger.info("Registered routers with organized tag groups:")
    logger.info("  Auth & Authorization: /auth, /permissions, /roles")
    logger.info("  User Management: /users")
    logger.info("  Organization Management: /organizations")
    logger.info("  Tenant Management: /tenants")
    logger.info("  Infrastructure: /regions, /databases")
    logger.info("  Reference Data: /currencies, /countries, /languages")
    
    if settings.enable_prefix_routes and settings.api_prefix:
        logger.info(f"  📦 Compatibility routes with {settings.api_prefix} prefix (hidden from docs)")