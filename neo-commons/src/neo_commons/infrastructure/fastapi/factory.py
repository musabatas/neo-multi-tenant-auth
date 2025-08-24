"""FastAPI application factory with standardized configuration.

Provides factory functions to create FastAPI applications with sensible defaults,
proper middleware configuration, and service-specific customization.
"""

import logging
from typing import Optional, Dict, Any, Callable, List, TYPE_CHECKING
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager

try:
    from scalar_fastapi import get_scalar_api_reference
    SCALAR_AVAILABLE = True
except ImportError:
    SCALAR_AVAILABLE = False

from .config import (
    FastAPIConfig,
    AdminAPIConfig,
    TenantAPIConfig,
    DeploymentAPIConfig,
    Environment,
    ServiceType
)
from .middleware_setup import setup_middleware_stack
from .dependencies import configure_dependency_overrides
from ..middleware import MiddlewareFactory
# from ...features.users.services import UserService  # TODO: Enable when UserService is implemented
from ...features.cache.services import CacheService
# from ...features.tenants.services import TenantService  # TODO: Enable when TenantService is implemented
from ...features.database.services import DatabaseService

if TYPE_CHECKING:
    from ...features.users.services import UserService
    from ...features.tenants.services import TenantService

logger = logging.getLogger(__name__)


class FastAPIFactory:
    """Factory for creating configured FastAPI applications."""
    
    def __init__(
        self,
        user_service: Optional["UserService"] = None,
        cache_service: Optional[CacheService] = None,
        tenant_service: Optional["TenantService"] = None,
        database_service: Optional[DatabaseService] = None
    ):
        self.user_service = user_service
        self.cache_service = cache_service
        self.tenant_service = tenant_service
        self.database_service = database_service
        self._middleware_factory: Optional[MiddlewareFactory] = None
    
    def create_app(
        self,
        config: FastAPIConfig,
        lifespan: Optional[Callable] = None,
        custom_routes: Optional[List[Any]] = None,
        dependency_overrides: Optional[Dict[Any, Any]] = None,
        **kwargs
    ) -> FastAPI:
        """Create FastAPI application with the given configuration."""
        
        # Create lifespan context manager
        if lifespan is None:
            lifespan = self._create_default_lifespan(config)
        
        # Configure documentation URLs based on Scalar availability
        docs_url = None if not config.docs_config.use_scalar else config.docs_config.docs_url
        swagger_url = config.docs_config.swagger_url if config.docs_config.use_scalar else config.docs_config.docs_url
        
        # Create FastAPI app with basic configuration
        app = FastAPI(
            title=config.docs_config.title,
            description=config.docs_config.description,
            version=config.docs_config.version,
            docs_url=swagger_url if not SCALAR_AVAILABLE or not config.docs_config.use_scalar else None,
            redoc_url=config.docs_config.redoc_url,
            openapi_url=config.docs_config.openapi_url,
            debug=config.debug,
            lifespan=lifespan,
            contact=config.docs_config.contact,
            license_info=config.docs_config.license_info,
            servers=config.docs_config.servers,
            swagger_ui_oauth2_redirect_url=config.docs_config.swagger_ui_oauth2_redirect_url,
            swagger_ui_parameters=config.docs_config.swagger_ui_parameters,
            **kwargs
        )
        
        # Add security schemes to OpenAPI spec for authentication
        def custom_openapi():
            if app.openapi_schema:
                return app.openapi_schema
            
            from fastapi.openapi.utils import get_openapi
            openapi_schema = get_openapi(
                title=config.docs_config.title,
                version=config.docs_config.version,
                description=config.docs_config.description,
                routes=app.routes,
            )
            
            # Add security schemes for Bearer token authentication
            openapi_schema["components"]["securitySchemes"] = {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "Enter JWT Bearer token"
                }
            }
            
            app.openapi_schema = openapi_schema
            return app.openapi_schema
        
        app.openapi = custom_openapi
        
        # Store configuration in app state
        app.state.config = config
        
        # Setup Scalar API documentation if enabled and available
        if SCALAR_AVAILABLE and config.docs_config.use_scalar and config.docs_config.docs_url:
            self._setup_scalar_docs(app, config)
        
        # Configure dependency overrides
        if dependency_overrides:
            configure_dependency_overrides(app, dependency_overrides)
        
        # Add basic middleware (order matters - these go first)
        self._add_basic_middleware(app, config)
        
        # Add service-specific middleware stack
        if self._can_setup_middleware(config):
            self._setup_service_middleware(app, config)
        
        # Add custom routes
        if custom_routes:
            for route in custom_routes:
                app.include_router(route)
        
        # Add health check endpoints
        self._add_health_endpoints(app, config)
        
        logger.info(
            f"Created {config.service_type.value} FastAPI application",
            extra={
                "service_type": config.service_type.value,
                "environment": config.environment.value,
                "debug": config.debug,
                "port": config.port
            }
        )
        
        return app
    
    def _setup_scalar_docs(self, app: FastAPI, config: FastAPIConfig) -> None:
        """Setup Scalar API documentation."""
        try:
            # Extract only supported parameters from scalar_config
            scalar_config = config.docs_config.scalar_config
            supported_params = {}
            
            # Map configuration keys to supported get_scalar_api_reference parameters
            param_mapping = {
                "layout": "layout",
                "show_sidebar": "show_sidebar", 
                "hide_download_button": "hide_download_button",
                "hide_models": "hide_models",
                "dark_mode": "dark_mode",
                "search_hot_key": "search_hot_key",
                "servers": "servers",
                "default_open_all_tags": "default_open_all_tags",
                "authentication": "authentication",
                "hide_client_button": "hide_client_button",
                "scalar_theme": "scalar_theme",
                "scalar_favicon_url": "scalar_favicon_url"
            }
            
            # Extract only supported parameters with proper value handling
            # Only include safe parameters that don't require enum conversion
            safe_params = {
                "show_sidebar", "hide_download_button", "hide_models", 
                "dark_mode", "servers", "default_open_all_tags", 
                "authentication", "hide_client_button", "scalar_theme", 
                "scalar_favicon_url"
            }
            
            for config_key, param_key in param_mapping.items():
                if config_key in scalar_config and param_key in safe_params:
                    supported_params[param_key] = scalar_config[config_key]
            
            # Add servers from docs config if defined
            if config.docs_config.servers:
                supported_params["servers"] = config.docs_config.servers
            
            # Create Scalar API reference endpoint
            @app.get(config.docs_config.docs_url, include_in_schema=False)
            async def scalar_html():
                return get_scalar_api_reference(
                    openapi_url=config.docs_config.openapi_url,
                    title=config.docs_config.title,
                    **supported_params
                )
                
            logger.info(f"Scalar API documentation enabled at {config.docs_config.docs_url}")
            
        except Exception as e:
            logger.warning(f"Failed to setup Scalar documentation: {e}")
            logger.info("Falling back to default Swagger UI")
    
    def _create_default_lifespan(self, config: FastAPIConfig):
        """Create default lifespan context manager."""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info(
                f"Starting {config.service_type.value} API",
                extra={
                    "environment": config.environment.value,
                    "version": config.version
                }
            )
            
            # Initialize services if needed
            if hasattr(app.state, 'startup_tasks'):
                for task in app.state.startup_tasks:
                    await task()
            
            yield
            
            # Shutdown
            logger.info(f"Shutting down {config.service_type.value} API")
            
            # Cleanup services if needed
            if hasattr(app.state, 'shutdown_tasks'):
                for task in app.state.shutdown_tasks:
                    await task()
        
        return lifespan
    
    def _add_basic_middleware(self, app: FastAPI, config: FastAPIConfig) -> None:
        """Add basic middleware that should be present on all apps."""
        
        # GZip compression
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Trusted host middleware for production
        if config.environment == Environment.PRODUCTION:
            allowed_hosts = ["*"]  # Configure based on your domains
            app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    def _can_setup_middleware(self, config: FastAPIConfig) -> bool:
        """Check if we can setup the full middleware stack."""
        return (
            self.user_service is not None and
            self.cache_service is not None and
            config.jwt_secret is not None
        )
    
    def _setup_service_middleware(self, app: FastAPI, config: FastAPIConfig) -> None:
        """Setup service-specific middleware stack."""
        
        if not self._middleware_factory:
            self._middleware_factory = MiddlewareFactory(
                user_service=self.user_service,
                cache_service=self.cache_service,
                tenant_service=self.tenant_service,
                database_service=self.database_service,
                jwt_secret=config.jwt_secret,
                jwt_algorithm=config.jwt_algorithm
            )
        
        # Setup middleware based on service type and environment
        setup_middleware_stack(
            app=app,
            config=config,
            middleware_factory=self._middleware_factory
        )
    
    def _add_health_endpoints(self, app: FastAPI, config: FastAPIConfig) -> None:
        """Add standard health check endpoints."""
        
        @app.get("/health", tags=["Health"])
        async def health_check():
            """Basic health check endpoint."""
            docs_info = {}
            if config.docs_config.use_scalar and SCALAR_AVAILABLE and config.docs_config.docs_url:
                docs_info["docs"] = f"Scalar API docs available at {config.docs_config.docs_url}"
            elif config.docs_config.docs_url:
                docs_info["docs"] = f"Swagger UI docs available at {config.docs_config.docs_url}"
            
            response = {
                "status": "healthy",
                "service": config.service_type.value,
                "version": config.version,
                "environment": config.environment.value
            }
            
            if docs_info:
                response.update(docs_info)
                
            return response
        
        @app.get("/health/ready", tags=["Health"])
        async def readiness_check(request: Request):
            """Readiness check with service dependencies."""
            checks = {
                "service": "ready",
                "database": "unknown",
                "cache": "unknown"
            }
            
            # Check database if available
            if self.database_service:
                try:
                    await self.database_service.health_check()
                    checks["database"] = "ready"
                except Exception:
                    checks["database"] = "not_ready"
            
            # Check cache if available
            if self.cache_service:
                try:
                    await self.cache_service.ping()
                    checks["cache"] = "ready"
                except Exception:
                    checks["cache"] = "not_ready"
            
            # Determine overall status
            all_ready = all(
                status in ["ready", "unknown"] 
                for status in checks.values()
            )
            
            status_code = 200 if all_ready else 503
            
            return JSONResponse(
                status_code=status_code,
                content={
                    "status": "ready" if all_ready else "not_ready",
                    "checks": checks,
                    "service": config.service_type.value,
                    "version": config.version
                }
            )
        
        @app.get("/health/live", tags=["Health"])
        async def liveness_check():
            """Liveness check - simple endpoint to verify app is running."""
            return {"status": "alive"}


def create_fastapi_factory(
    user_service: Optional["UserService"] = None,
    cache_service: Optional[CacheService] = None,
    tenant_service: Optional["TenantService"] = None,
    database_service: Optional[DatabaseService] = None
) -> FastAPIFactory:
    """Create a FastAPI factory with services."""
    return FastAPIFactory(
        user_service=user_service,
        cache_service=cache_service,
        tenant_service=tenant_service,
        database_service=database_service
    )


# Convenience functions for specific service types

def create_admin_api(
    factory: FastAPIFactory,
    config_overrides: Optional[Dict[str, Any]] = None,
    **kwargs
) -> FastAPI:
    """Create Admin API with standard configuration."""
    config = AdminAPIConfig.from_environment(
        ServiceType.ADMIN_API,
        **(config_overrides or {})
    )
    return factory.create_app(config, **kwargs)


def create_tenant_api(
    factory: FastAPIFactory,
    config_overrides: Optional[Dict[str, Any]] = None,
    **kwargs
) -> FastAPI:
    """Create Tenant API with standard configuration."""
    config = TenantAPIConfig.from_environment(
        ServiceType.TENANT_API,
        **(config_overrides or {})
    )
    return factory.create_app(config, **kwargs)


def create_deployment_api(
    factory: FastAPIFactory,
    config_overrides: Optional[Dict[str, Any]] = None,
    **kwargs
) -> FastAPI:
    """Create Deployment API with standard configuration."""
    config = DeploymentAPIConfig.from_environment(
        ServiceType.DEPLOYMENT_API,
        **(config_overrides or {})
    )
    return factory.create_app(config, **kwargs)


def create_custom_api(
    factory: FastAPIFactory,
    service_type: ServiceType = ServiceType.CUSTOM,
    config_overrides: Optional[Dict[str, Any]] = None,
    **kwargs
) -> FastAPI:
    """Create custom API with base configuration."""
    config = FastAPIConfig.from_environment(
        service_type,
        **(config_overrides or {})
    )
    return factory.create_app(config, **kwargs)


# Quick setup functions for common patterns

def create_development_api(
    service_type: ServiceType,
    title: str,
    description: str = "",
    port: int = 8000,
    **kwargs
) -> FastAPI:
    """Quick setup for development API with minimal configuration."""
    
    config = FastAPIConfig(
        service_type=service_type,
        title=title,
        description=description,
        port=port,
        environment=Environment.DEVELOPMENT,
        debug=True,
        enable_auth=False,  # Simplified for development
        enable_tenant_context=False
    )
    
    factory = FastAPIFactory()
    return factory.create_app(config, **kwargs)


def create_production_api(
    service_type: ServiceType,
    user_service: "UserService",
    cache_service: CacheService,
    database_service: DatabaseService,
    jwt_secret: str,
    tenant_service: Optional["TenantService"] = None,
    config_overrides: Optional[Dict[str, Any]] = None,
    **kwargs
) -> FastAPI:
    """Quick setup for production API with full configuration."""
    
    factory = FastAPIFactory(
        user_service=user_service,
        cache_service=cache_service,
        tenant_service=tenant_service,
        database_service=database_service
    )
    
    config_dict = {
        "environment": Environment.PRODUCTION,
        "jwt_secret": jwt_secret,
        "debug": False,
        **(config_overrides or {})
    }
    
    config = FastAPIConfig.from_environment(service_type, **config_dict)
    return factory.create_app(config, **kwargs)