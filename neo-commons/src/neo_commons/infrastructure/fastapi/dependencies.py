"""FastAPI dependency injection helpers and configuration.

Provides helper functions for configuring dependency injection,
service resolution, and application-level dependencies.
"""

from typing import Dict, Any, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ...features.users.services import UserService
    from ...features.tenants.services import TenantService  
    from ...features.permissions.services import PermissionService
from fastapi import FastAPI, Depends, Request

from .config import FastAPIConfig
# from ...features.users.services import UserService  # TODO: Enable when UserService is implemented
from ...features.cache.services import CacheService
# from ...features.tenants.services import TenantService  # TODO: Enable when TenantService is implemented
from ...features.database.services import DatabaseService
# from ...features.permissions.services import PermissionService  # TODO: Enable when PermissionService is implemented


# Application-level dependency storage
_app_dependencies: Dict[str, Any] = {}


def configure_dependency_overrides(
    app: FastAPI,
    overrides: Dict[Any, Any]
) -> None:
    """Configure FastAPI dependency overrides."""
    app.dependency_overrides.update(overrides)


def register_service(service_name: str, service_instance: Any) -> None:
    """Register a service instance for dependency injection."""
    _app_dependencies[service_name] = service_instance


def get_registered_service(service_name: str) -> Any:
    """Get a registered service instance."""
    return _app_dependencies.get(service_name)


# Configuration dependencies

def get_app_config(request: Request) -> FastAPIConfig:
    """Get application configuration from app state."""
    return request.app.state.config


def get_service_info(request: Request) -> Dict[str, Any]:
    """Get service information for the current app."""
    config = get_app_config(request)
    return {
        "service_type": config.service_type.value,
        "environment": config.environment.value,
        "version": config.version,
        "debug": config.debug
    }


# Health and status dependencies

async def get_health_status(
    user_service: Optional["UserService"] = Depends(lambda: get_registered_service("user_service")),
    cache_service: Optional[CacheService] = Depends(lambda: get_registered_service("cache_service")),
    database_service: Optional[DatabaseService] = Depends(lambda: get_registered_service("database_service")),
    tenant_service: Optional["TenantService"] = Depends(lambda: get_registered_service("tenant_service"))
) -> Dict[str, str]:
    """Get health status of all registered services."""
    status = {}
    
    # Check database service
    if database_service:
        try:
            await database_service.health_check()
            status["database"] = "healthy"
        except Exception as e:
            status["database"] = f"unhealthy: {str(e)}"
    else:
        status["database"] = "not_configured"
    
    # Check cache service
    if cache_service:
        try:
            await cache_service.ping()
            status["cache"] = "healthy"
        except Exception as e:
            status["cache"] = f"unhealthy: {str(e)}"
    else:
        status["cache"] = "not_configured"
    
    # Check user service (basic validation)
    if user_service:
        try:
            # Basic service validation - you might want to implement a health_check method
            status["user_service"] = "healthy"
        except Exception as e:
            status["user_service"] = f"unhealthy: {str(e)}"
    else:
        status["user_service"] = "not_configured"
    
    # Check tenant service
    if tenant_service:
        try:
            status["tenant_service"] = "healthy"
        except Exception as e:
            status["tenant_service"] = f"unhealthy: {str(e)}"
    else:
        status["tenant_service"] = "not_configured"
    
    return status


# Service dependency factories

def create_user_service_dependency() -> Callable:
    """Create a dependency function for UserService."""
    def get_user_service() -> "UserService":
        service = get_registered_service("user_service")
        if not service:
            raise RuntimeError("UserService not registered. Call register_service('user_service', instance) first.")
        return service
    return get_user_service


def create_cache_service_dependency() -> Callable:
    """Create a dependency function for CacheService."""
    def get_cache_service() -> CacheService:
        service = get_registered_service("cache_service")
        if not service:
            raise RuntimeError("CacheService not registered. Call register_service('cache_service', instance) first.")
        return service
    return get_cache_service


def create_database_service_dependency() -> Callable:
    """Create a dependency function for DatabaseService."""
    def get_database_service() -> DatabaseService:
        service = get_registered_service("database_service")
        if not service:
            raise RuntimeError("DatabaseService not registered. Call register_service('database_service', instance) first.")
        return service
    return get_database_service


def create_tenant_service_dependency() -> Callable:
    """Create a dependency function for TenantService."""
    def get_tenant_service() -> "TenantService":
        service = get_registered_service("tenant_service")
        if not service:
            raise RuntimeError("TenantService not registered. Call register_service('tenant_service', instance) first.")
        return service
    return get_tenant_service


def create_permission_service_dependency() -> Callable:
    """Create a dependency function for PermissionService."""
    def get_permission_service() -> "PermissionService":
        service = get_registered_service("permission_service")
        if not service:
            raise RuntimeError("PermissionService not registered. Call register_service('permission_service', instance) first.")
        return service
    return get_permission_service


# Optional service dependencies

def create_optional_user_service_dependency() -> Callable:
    """Create a dependency function for optional UserService."""
    def get_optional_user_service() -> Optional["UserService"]:
        return get_registered_service("user_service")
    return get_optional_user_service


def create_optional_cache_service_dependency() -> Callable:
    """Create a dependency function for optional CacheService."""
    def get_optional_cache_service() -> Optional[CacheService]:
        return get_registered_service("cache_service")
    return get_optional_cache_service


def create_optional_tenant_service_dependency() -> Callable:
    """Create a dependency function for optional TenantService."""
    def get_optional_tenant_service() -> Optional["TenantService"]:
        return get_registered_service("tenant_service")
    return get_optional_tenant_service


# Setup functions for easy service registration

def setup_service_dependencies(
    user_service: Optional["UserService"] = None,
    cache_service: Optional[CacheService] = None,
    database_service: Optional[DatabaseService] = None,
    tenant_service: Optional["TenantService"] = None,
    permission_service: Optional["PermissionService"] = None,
    **custom_services
) -> None:
    """Setup all service dependencies for dependency injection."""
    
    if user_service:
        register_service("user_service", user_service)
    
    if cache_service:
        register_service("cache_service", cache_service)
    
    if database_service:
        register_service("database_service", database_service)
    
    if tenant_service:
        register_service("tenant_service", tenant_service)
    
    if permission_service:
        register_service("permission_service", permission_service)
    
    # Register any custom services
    for name, service in custom_services.items():
        register_service(name, service)


def create_dependency_overrides(
    user_service: Optional["UserService"] = None,
    cache_service: Optional[CacheService] = None,
    database_service: Optional[DatabaseService] = None,
    tenant_service: Optional["TenantService"] = None,
    permission_service: Optional["PermissionService"] = None
) -> Dict[Any, Any]:
    """Create dependency overrides dict for FastAPI app configuration."""
    
    overrides = {}
    
    # Setup service dependencies first
    setup_service_dependencies(
        user_service=user_service,
        cache_service=cache_service,
        database_service=database_service,
        tenant_service=tenant_service,
        permission_service=permission_service
    )
    
    # Create dependency overrides
    if user_service:
        overrides[create_user_service_dependency()] = lambda: user_service
    
    if cache_service:
        overrides[create_cache_service_dependency()] = lambda: cache_service
    
    if database_service:
        overrides[create_database_service_dependency()] = lambda: database_service
    
    if tenant_service:
        overrides[create_tenant_service_dependency()] = lambda: tenant_service
    
    if permission_service:
        overrides[create_permission_service_dependency()] = lambda: permission_service
    
    return overrides


# Application lifecycle helpers

def create_startup_handler(
    *startup_tasks: Callable
) -> Callable:
    """Create a startup handler with multiple tasks."""
    async def startup():
        for task in startup_tasks:
            await task()
    return startup


def create_shutdown_handler(
    *shutdown_tasks: Callable
) -> Callable:
    """Create a shutdown handler with multiple tasks."""
    async def shutdown():
        for task in shutdown_tasks:
            await task()
    return shutdown


# Environment-specific dependency helpers

def get_database_url(config: FastAPIConfig) -> str:
    """Get database URL with fallbacks."""
    if config.database_url:
        return config.database_url
    
    # Environment-specific defaults
    if config.environment.value == "production":
        raise ValueError("DATABASE_URL must be set in production")
    
    return "postgresql://postgres:postgres@localhost:5432/neofast_admin"


def get_redis_url(config: FastAPIConfig) -> str:
    """Get Redis URL with fallbacks."""
    if config.redis_url:
        return config.redis_url
    
    # Environment-specific defaults
    if config.environment.value == "production":
        raise ValueError("REDIS_URL must be set in production")
    
    return "redis://localhost:6379/0"


def get_jwt_secret(config: FastAPIConfig) -> str:
    """Get JWT secret with validation."""
    if not config.jwt_secret:
        if config.environment.value == "production":
            raise ValueError("JWT_SECRET must be set in production")
        return "development-secret-not-for-production"
    
    return config.jwt_secret


# Clear dependencies (useful for testing)

def clear_dependencies() -> None:
    """Clear all registered dependencies."""
    _app_dependencies.clear()