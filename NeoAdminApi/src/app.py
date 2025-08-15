"""
FastAPI application factory and configuration.

ENHANCED WITH NEO-COMMONS: Now using neo-commons middleware and dependency injection patterns.
Improved application lifecycle, better error handling, and structured configuration validation.
"""
from contextlib import asynccontextmanager
from typing import Dict
from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference
from loguru import logger

# NEO-COMMONS INTEGRATION: Enhanced application configuration and monitoring
from neo_commons.utils.datetime import utc_now
from neo_commons.config import BaseConfigProtocol

from src.common.config.settings import settings
from src.common.database.connection import init_database, close_database
from src.common.cache.client import init_cache, close_cache
from src.common.middleware import setup_middleware
from src.common.openapi_config import configure_openapi
from src.common.endpoints import register_health_endpoints, register_debug_endpoints
from src.common.exception_handlers import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager with enhanced error handling and monitoring.
    
    ENHANCED WITH NEO-COMMONS: Now includes startup/shutdown timing, structured logging,
    and better error context using neo-commons datetime utilities.
    """
    # Enhanced startup logging with timing
    startup_start = utc_now()
    
    logger.info(
        f"Starting {settings.app_name} v{settings.app_version}",
        extra={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "environment": settings.environment,
            "startup_time": startup_start.isoformat(),
            "host": settings.host,
            "port": settings.port
        }
    )
    
    try:
        # Initialize database connections with error context
        logger.info("Initializing database connections...")
        await init_database()
        logger.info("Database initialization completed")
        
        # Initialize cache (optional - will warn if unavailable)
        logger.info("Initializing cache connections...")
        try:
            await init_cache()
            logger.info("Cache initialization completed")
        except Exception as e:
            logger.warning(
                "Cache initialization failed, continuing without cache",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
        
        # Sync permissions on startup with enhanced logging
        try:
            from src.features.auth.services.permission_manager import PermissionSyncManager
            logger.info("Starting permission synchronization...")
            sync_manager = PermissionSyncManager()
            sync_result = await sync_manager.sync_permissions(
                app=app,
                dry_run=False,  # Actually apply changes
                force_update=False  # Only update if changed
            )
            
            if sync_result['success']:
                logger.info(
                    "Permission sync completed successfully",
                    extra={"sync_stats": sync_result['stats']}
                )
            else:
                logger.warning(
                    "Permission sync completed with issues",
                    extra={"error": sync_result.get('error')}
                )
        except Exception as e:
            logger.error(
                "Permission sync failed",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            # Don't fail startup for permission sync issues
        
        # Calculate and log startup duration
        startup_end = utc_now()
        startup_duration = (startup_end - startup_start).total_seconds()
        
        logger.info(
            "Application startup complete",
            extra={
                "startup_duration_seconds": startup_duration,
                "startup_completed_at": startup_end.isoformat()
            }
        )
        
    except Exception as e:
        logger.error(
            "Failed to start application",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "startup_failed_at": utc_now().isoformat()
            }
        )
        raise
    
    yield
    
    # Enhanced shutdown logging with timing
    shutdown_start = utc_now()
    logger.info(
        "Starting application shutdown",
        extra={"shutdown_started_at": shutdown_start.isoformat()}
    )
    
    try:
        # Close database connections
        logger.info("Closing database connections...")
        await close_database()
        logger.info("Database connections closed")
        
        # Close cache connections (if available)
        logger.info("Closing cache connections...")
        try:
            await close_cache()
            logger.info("Cache connections closed")
        except Exception as e:
            logger.warning(
                "Cache shutdown failed (non-critical)",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
        
        # Calculate and log shutdown duration
        shutdown_end = utc_now()
        shutdown_duration = (shutdown_end - shutdown_start).total_seconds()
        
        logger.info(
            "Application shutdown complete",
            extra={
                "shutdown_duration_seconds": shutdown_duration,
                "shutdown_completed_at": shutdown_end.isoformat()
            }
        )
        
    except Exception as e:
        logger.error(
            "Error during application shutdown",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "shutdown_failed_at": utc_now().isoformat()
            }
        )


def _validate_app_config(config: BaseConfigProtocol) -> bool:
    """
    Validate FastAPI application configuration before startup.
    
    Args:
        config: Configuration object implementing BaseConfigProtocol
        
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    try:
        # Check required application settings
        if not config.app_name:
            logger.error("APP_NAME is required for FastAPI application")
            return False
            
        if not config.app_version:
            logger.error("APP_VERSION is required for FastAPI application")
            return False
            
        if not config.database_url:
            logger.error("DATABASE_URL is required for FastAPI application")
            return False
            
        # Validate port range
        if not (1 <= config.port <= 65535):
            logger.error(f"Invalid port number: {config.port}")
            return False
            
        # Validate environment
        valid_environments = ("development", "staging", "production", "testing")
        if config.environment not in valid_environments:
            logger.warning(f"Unknown environment: {config.environment}")
            
        # Check Redis configuration (optional but warn if missing)
        redis_url = getattr(config, 'redis_url', None)
        if not redis_url:
            logger.warning("REDIS_URL not configured - cache features will be limited")
            
        # Log configuration validation success
        logger.info(
            "Application configuration validation passed",
            extra={
                "app_name": config.app_name,
                "app_version": config.app_version,
                "environment": config.environment,
                "port": config.port,
                "database_configured": bool(config.database_url),
                "redis_configured": bool(redis_url)
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(
            "Application configuration validation error",
            extra={"error": str(e), "error_type": type(e).__name__}
        )
        return False


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application with enhanced monitoring and validation.
    
    ENHANCED WITH NEO-COMMONS: Now includes configuration validation, startup timing,
    and improved error handling using neo-commons patterns.
    """
    
    # Enhanced configuration validation using neo-commons protocols
    if not _validate_app_config(settings):
        raise RuntimeError("Application configuration validation failed")
    
    # Create FastAPI instance with enhanced configuration
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
        logger.info("OpenAPI documentation configured with nested tag groups")
    
    # Setup organized middleware stack with enhanced logging
    logger.info("Setting up middleware stack...")
    middleware_manager = setup_middleware(app)
    logger.info(
        "Middleware stack configured",
        extra={
            "environment": settings.environment,
            "middleware_count": len(middleware_manager._middlewares) if hasattr(middleware_manager, '_middlewares') else 0
        }
    )
    
    # Log middleware status in development
    if settings.is_development:
        try:
            middleware_status = middleware_manager.get_middleware_status()
            logger.info("Active middleware configuration", extra=middleware_status)
        except AttributeError:
            logger.info("Middleware status logging not available")
    
    # Register exception handlers with logging
    logger.info("Registering exception handlers...")
    register_exception_handlers(app)
    
    # Register routers with logging
    logger.info("Registering API routers...")
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
        logger.info("Scalar API documentation configured at /docs")
    
    # Register health and debug endpoints with logging
    logger.info("Registering health and debug endpoints...")
    register_health_endpoints(app)
    register_debug_endpoints(app)
    
    # Log successful app creation
    logger.info(
        "FastAPI application created successfully",
        extra={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "environment": settings.environment,
            "docs_enabled": not settings.is_production,
            "created_at": utc_now().isoformat()
        }
    )
    
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