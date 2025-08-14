"""
Router factory functions for neo-commons.
Provides convenient factory functions to create pre-configured routers for common use cases.
"""
import logging
from typing import Optional, List, Any

from .routers import NeoAPIRouter
from .specialized_routers import (
    VersionedAPIRouter,
    SecureAPIRouter,
    CachedAPIRouter,
    AdminAPIRouter,
    TenantAPIRouter,
    PublicAPIRouter
)

logger = logging.getLogger(__name__)


def create_admin_router(
    prefix: str = "",
    version: str = "v1",
    require_auth: bool = True,
    **kwargs
) -> NeoAPIRouter:
    """
    Create a router configured for admin/platform APIs.
    
    Args:
        prefix: Route prefix
        version: API version
        require_auth: Require authentication
        **kwargs: Additional router arguments
        
    Returns:
        Configured router for admin APIs
    """
    return AdminAPIRouter(
        prefix=f"/{version}{prefix}".rstrip("/"),
        version=version,
        require_admin_auth=require_auth,
        auto_slash_handling=True,
        debug_route_registration=False,
        **kwargs
    )


def create_tenant_router(
    prefix: str = "",
    version: str = "v1",
    require_auth: bool = True,
    cache_ttl: int = 300,
    **kwargs
) -> NeoAPIRouter:
    """
    Create a router configured for tenant APIs.
    
    Args:
        prefix: Route prefix
        version: API version  
        require_auth: Require authentication
        cache_ttl: Default cache TTL
        **kwargs: Additional router arguments
        
    Returns:
        Configured router for tenant APIs
    """
    return TenantAPIRouter(
        prefix=f"/{version}{prefix}".rstrip("/"),
        version=version,
        require_tenant_auth=require_auth,
        default_cache_ttl=cache_ttl,
        auto_slash_handling=True,
        **kwargs
    )


def create_public_router(
    prefix: str = "",
    version: str = "v1",
    cache_ttl: int = 3600,  # 1 hour for public data
    enable_guest_sessions: bool = True,
    **kwargs
) -> NeoAPIRouter:
    """
    Create a router configured for public APIs.
    
    Args:
        prefix: Route prefix
        version: API version
        cache_ttl: Default cache TTL
        enable_guest_sessions: Enable guest session tracking
        **kwargs: Additional router arguments
        
    Returns:
        Configured router for public APIs
    """
    return PublicAPIRouter(
        prefix=f"/{version}{prefix}".rstrip("/"),
        version=version,
        default_cache_ttl=cache_ttl,
        enable_guest_sessions=enable_guest_sessions,
        auto_slash_handling=True,
        **kwargs
    )


def create_secure_router(
    prefix: str = "",
    version: str = "v1",
    auth_scopes: Optional[List[str]] = None,
    guest_allowed: bool = False,
    **kwargs
) -> SecureAPIRouter:
    """
    Create a security-focused router with authentication requirements.
    
    Args:
        prefix: Route prefix
        version: API version
        auth_scopes: Required authentication scopes
        guest_allowed: Allow guest access
        **kwargs: Additional router arguments
        
    Returns:
        Configured secure router
    """
    full_prefix = f"/{version}{prefix}".rstrip("/") if version else prefix
    
    return SecureAPIRouter(
        prefix=full_prefix,
        require_auth=True,
        auth_scopes=auth_scopes or [],
        guest_allowed=guest_allowed,
        auto_slash_handling=True,
        **kwargs
    )


def create_cached_router(
    prefix: str = "",
    version: str = "v1",
    cache_ttl: int = 300,
    cache_prefix: Optional[str] = None,
    **kwargs
) -> CachedAPIRouter:
    """
    Create a caching-focused router with response caching.
    
    Args:
        prefix: Route prefix
        version: API version
        cache_ttl: Default cache TTL in seconds
        cache_prefix: Cache key prefix
        **kwargs: Additional router arguments
        
    Returns:
        Configured cached router
    """
    full_prefix = f"/{version}{prefix}".rstrip("/") if version else prefix
    
    return CachedAPIRouter(
        prefix=full_prefix,
        default_cache_ttl=cache_ttl,
        cache_key_prefix=cache_prefix or "api",
        auto_slash_handling=True,
        **kwargs
    )


def create_versioned_router(
    version: str,
    prefix: str = "",
    deprecated: bool = False,
    deprecation_message: Optional[str] = None,
    **kwargs
) -> VersionedAPIRouter:
    """
    Create a version-aware router with automatic version handling.
    
    Args:
        version: API version (e.g., "v1", "v2")
        prefix: Route prefix (after version)
        deprecated: Mark this version as deprecated
        deprecation_message: Custom deprecation message
        **kwargs: Additional router arguments
        
    Returns:
        Configured versioned router
    """
    return VersionedAPIRouter(
        version=version,
        prefix=prefix,
        deprecated=deprecated,
        deprecation_message=deprecation_message,
        auto_slash_handling=True,
        **kwargs
    )


def create_microservice_router(
    service_name: str,
    version: str = "v1",
    require_auth: bool = True,
    cache_ttl: int = 300,
    **kwargs
) -> NeoAPIRouter:
    """
    Create a router optimized for microservice patterns.
    
    Args:
        service_name: Name of the microservice
        version: API version
        require_auth: Require authentication
        cache_ttl: Default cache TTL
        **kwargs: Additional router arguments
        
    Returns:
        Configured microservice router
    """
    # Use service name as prefix
    prefix = f"/{version}/{service_name}"
    
    # Combine security and caching features
    if require_auth:
        return TenantAPIRouter(
            prefix=prefix,
            version=version,
            require_tenant_auth=require_auth,
            default_cache_ttl=cache_ttl,
            cache_key_prefix=service_name,
            **kwargs
        )
    else:
        return PublicAPIRouter(
            prefix=prefix,
            version=version,
            default_cache_ttl=cache_ttl,
            enable_guest_sessions=True,
            **kwargs
        )


def create_health_router(
    include_deep_checks: bool = True,
    cache_ttl: int = 30,  # Short cache for health checks
    **kwargs
) -> CachedAPIRouter:
    """
    Create a router specifically for health check endpoints.
    
    Args:
        include_deep_checks: Include deep health check endpoints
        cache_ttl: Cache TTL for health responses
        **kwargs: Additional router arguments
        
    Returns:
        Configured health check router
    """
    return CachedAPIRouter(
        prefix="/health",
        default_cache_ttl=cache_ttl,
        cache_key_prefix="health",
        auto_slash_handling=True,
        tags=["Health"],
        **kwargs
    )


def create_debug_router(
    require_auth: bool = True,
    auth_scopes: Optional[List[str]] = None,
    **kwargs
) -> SecureAPIRouter:
    """
    Create a router for debug and development endpoints.
    
    Args:
        require_auth: Require authentication for debug endpoints
        auth_scopes: Required authentication scopes (defaults to admin)
        **kwargs: Additional router arguments
        
    Returns:
        Configured debug router
    """
    return SecureAPIRouter(
        prefix="/debug",
        require_auth=require_auth,
        auth_scopes=auth_scopes or ["admin", "debug"],
        guest_allowed=False,
        auto_slash_handling=True,
        tags=["Debug"],
        **kwargs
    )


def create_api_router_by_type(
    router_type: str,
    **kwargs
) -> NeoAPIRouter:
    """
    Factory function to create routers by type string.
    
    Args:
        router_type: Type of router to create
        **kwargs: Router-specific arguments
        
    Returns:
        Configured router of the specified type
        
    Raises:
        ValueError: If router_type is not recognized
    """
    router_factories = {
        "admin": create_admin_router,
        "tenant": create_tenant_router,
        "public": create_public_router,
        "secure": create_secure_router,
        "cached": create_cached_router,
        "versioned": create_versioned_router,
        "microservice": create_microservice_router,
        "health": create_health_router,
        "debug": create_debug_router
    }
    
    factory = router_factories.get(router_type.lower())
    if not factory:
        available_types = list(router_factories.keys())
        raise ValueError(f"Unknown router type '{router_type}'. Available types: {available_types}")
    
    logger.info(f"Creating {router_type} router with factory function")
    return factory(**kwargs)


def create_api_router(
    prefix: str = "",
    version: Optional[str] = None,
    router_type: str = "basic",
    **kwargs
) -> NeoAPIRouter:
    """
    General-purpose API router factory function.
    
    Args:
        prefix: Route prefix
        version: API version (optional)
        router_type: Type of router to create (basic, admin, tenant, public, secure, cached)
        **kwargs: Additional router arguments
        
    Returns:
        Configured router based on the specified type
    """
    # Handle basic router (default)
    if router_type == "basic":
        full_prefix = f"/{version}{prefix}".rstrip("/") if version else prefix.rstrip("/")
        return NeoAPIRouter(
            prefix=full_prefix,
            auto_slash_handling=True,
            **kwargs
        )
    
    # Delegate to specialized factory functions
    if router_type in ["admin", "tenant", "public", "secure", "cached", "versioned", "microservice", "health", "debug"]:
        factory_kwargs = kwargs.copy()
        if version:
            factory_kwargs["version"] = version
        if prefix:
            factory_kwargs["prefix"] = prefix
        return create_api_router_by_type(router_type, **factory_kwargs)
    
    # Default to basic router if type not recognized
    logger.warning(f"Unknown router type '{router_type}', defaulting to basic router")
    full_prefix = f"/{version}{prefix}".rstrip("/") if version else prefix.rstrip("/")
    return NeoAPIRouter(
        prefix=full_prefix,
        auto_slash_handling=True,
        **kwargs
    )


# Convenience aliases for backward compatibility
create_platform_router = create_admin_router
create_client_router = create_tenant_router
create_guest_router = create_public_router