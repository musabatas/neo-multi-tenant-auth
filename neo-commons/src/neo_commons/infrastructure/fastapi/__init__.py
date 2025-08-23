"""FastAPI infrastructure package for neo-commons.

Provides FastAPI application factory, configuration, middleware setup,
and dependency injection helpers for standardized service creation.
"""

from .config import (
    FastAPIConfig,
    AdminAPIConfig, 
    TenantAPIConfig,
    DeploymentAPIConfig,
    Environment,
    ServiceType,
    CORSConfig,
    SecurityConfig,
    DocsConfig
)
from .factory import (
    FastAPIFactory,
    create_fastapi_factory,
    create_admin_api,
    create_tenant_api,
    create_deployment_api,
    create_custom_api,
    create_development_api,
    create_production_api
)
from .dependencies import (
    configure_dependency_overrides,
    register_service,
    get_registered_service,
    get_app_config,
    get_service_info,
    get_health_status,
    create_user_service_dependency,
    create_cache_service_dependency,
    create_database_service_dependency,
    create_tenant_service_dependency,
    create_permission_service_dependency,
    create_optional_user_service_dependency,
    create_optional_cache_service_dependency,
    create_optional_tenant_service_dependency,
    setup_service_dependencies,
    create_dependency_overrides,
    create_startup_handler,
    create_shutdown_handler,
    get_database_url,
    get_redis_url,
    get_jwt_secret,
    clear_dependencies
)
from .middleware_setup import (
    setup_middleware_stack,
    setup_admin_middleware,
    setup_tenant_middleware,
    setup_deployment_middleware,
    setup_default_middleware,
    setup_minimal_middleware,
    setup_api_only_middleware
)

__all__ = [
    # Configuration classes
    "FastAPIConfig",
    "AdminAPIConfig",
    "TenantAPIConfig", 
    "DeploymentAPIConfig",
    "Environment",
    "ServiceType",
    "CORSConfig",
    "SecurityConfig",
    "DocsConfig",
    
    # Factory classes and functions
    "FastAPIFactory",
    "create_fastapi_factory",
    "create_admin_api",
    "create_tenant_api",
    "create_deployment_api",
    "create_custom_api",
    "create_development_api",
    "create_production_api",
    
    # Dependency injection helpers
    "configure_dependency_overrides",
    "register_service",
    "get_registered_service",
    "get_app_config",
    "get_service_info",
    "get_health_status",
    "create_user_service_dependency",
    "create_cache_service_dependency",
    "create_database_service_dependency",
    "create_tenant_service_dependency",
    "create_permission_service_dependency",
    "create_optional_user_service_dependency",
    "create_optional_cache_service_dependency",
    "create_optional_tenant_service_dependency",
    "setup_service_dependencies",
    "create_dependency_overrides",
    "create_startup_handler",
    "create_shutdown_handler",
    "get_database_url",
    "get_redis_url",
    "get_jwt_secret",
    "clear_dependencies",
    
    # Middleware setup functions
    "setup_middleware_stack",
    "setup_admin_middleware",
    "setup_tenant_middleware",
    "setup_deployment_middleware",
    "setup_default_middleware",
    "setup_minimal_middleware",
    "setup_api_only_middleware",
]