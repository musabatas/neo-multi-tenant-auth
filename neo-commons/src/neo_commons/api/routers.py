"""
Base custom APIRouter implementations for neo-commons.
Provides the core NeoAPIRouter with enhanced slash handling and protocol-based design.
"""
import logging
from typing import Any, Callable, Optional, Dict, List, Union, Sequence
from fastapi import APIRouter as FastAPIRouter, Depends
from fastapi.routing import APIRoute
from fastapi.types import DecoratedCallable
from enum import Enum

logger = logging.getLogger(__name__)


class NeoAPIRouter(FastAPIRouter):
    """
    Enhanced APIRouter that automatically handles both trailing and non-trailing slash endpoints.
    
    This router automatically registers both versions of each route (with and without trailing slash)
    to avoid 307 redirects and make the API more flexible for client integrations.
    
    Features:
    - Automatic slash handling for all routes
    - Configurable behavior for root paths
    - Debug logging for route registration
    - Clean OpenAPI documentation (only main route appears in docs)
    """
    
    def __init__(
        self,
        *,
        prefix: str = "",
        tags: Optional[List[Union[str, Enum]]] = None,
        dependencies: Optional[Sequence[Depends]] = None,
        default_response_class: type = None,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        callbacks: Optional[List[APIRoute]] = None,
        routes: Optional[List[APIRoute]] = None,
        redirect_slashes: bool = False,  # Disable FastAPI's default redirect behavior
        default: Optional[APIRoute] = None,
        dependency_overrides_provider: Optional[Any] = None,
        route_class: type = APIRoute,
        on_startup: Optional[Sequence[Callable[[], Any]]] = None,
        on_shutdown: Optional[Sequence[Callable[[], Any]]] = None,
        deprecated: Optional[bool] = None,
        include_in_schema: bool = True,
        # Neo-specific parameters
        auto_slash_handling: bool = True,
        handle_root_slash: bool = False,
        debug_route_registration: bool = False
    ):
        """
        Initialize NeoAPIRouter with enhanced slash handling.
        
        Args:
            auto_slash_handling: Enable automatic trailing slash handling
            handle_root_slash: Apply slash handling to root path ("/")
            debug_route_registration: Enable debug logging for route registration
            **kwargs: Standard FastAPI router arguments
        """
        super().__init__(
            prefix=prefix,
            tags=tags,
            dependencies=dependencies,
            default_response_class=default_response_class,
            responses=responses,
            callbacks=callbacks,
            routes=routes,
            redirect_slashes=redirect_slashes,  # We handle this ourselves
            default=default,
            dependency_overrides_provider=dependency_overrides_provider,
            route_class=route_class,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            deprecated=deprecated,
            include_in_schema=include_in_schema
        )
        
        # Neo-specific configuration
        self.auto_slash_handling = auto_slash_handling
        self.handle_root_slash = handle_root_slash
        self.debug_route_registration = debug_route_registration
        
        if self.debug_route_registration:
            logger.debug(f"Initialized NeoAPIRouter with prefix='{prefix}', auto_slash_handling={auto_slash_handling}")
    
    def api_route(
        self, 
        path: str, 
        *, 
        include_in_schema: bool = True, 
        **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """
        Enhanced api_route that registers both slash variations.
        
        Args:
            path: The URL path for the route
            include_in_schema: Whether to include in OpenAPI schema (only main route is included)
            **kwargs: Additional route configuration
            
        Returns:
            Decorator function for the route handler
        """
        # Skip automatic slash handling if disabled or for root path (unless explicitly enabled)
        if not self.auto_slash_handling or (path == "/" and not self.handle_root_slash):
            if self.debug_route_registration:
                logger.debug(f"Registering single route: {path} (slash handling disabled)")
            return super().api_route(path, include_in_schema=include_in_schema, **kwargs)
        
        # Determine main and alternate paths
        if path.endswith("/") and path != "/":
            # Path has trailing slash - also register without
            main_path = path
            alternate_path = path[:-1]
        elif not path.endswith("/"):
            # Path has no trailing slash - also register with
            main_path = path
            alternate_path = path + "/"
        else:
            # Root path "/" - handle based on configuration
            main_path = path
            alternate_path = None
        
        # Register main path (included in schema)
        add_main_path = super().api_route(
            main_path, 
            include_in_schema=include_in_schema, 
            **kwargs
        )
        
        # Register alternate path if it exists (hidden from schema to avoid duplication)
        add_alternate_path = None
        if alternate_path:
            add_alternate_path = super().api_route(
                alternate_path, 
                include_in_schema=False,  # Hide from OpenAPI docs
                **kwargs
            )

        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            """Decorator that registers both route variations."""
            if self.debug_route_registration:
                if alternate_path:
                    logger.debug(f"Registering dual routes: main={main_path}, alternate={alternate_path}")
                else:
                    logger.debug(f"Registering single route: {main_path}")
            
            # Register alternate path first (if exists)
            if add_alternate_path:
                add_alternate_path(func)
            
            # Then register main path
            return add_main_path(func)

        return decorator


# Import specialized routers and factories for re-export
from .specialized_routers import (
    VersionedAPIRouter,
    SecureAPIRouter,
    CachedAPIRouter,
    AdminAPIRouter,
    TenantAPIRouter,
    PublicAPIRouter
)
from .router_factories import (
    create_admin_router,
    create_tenant_router,
    create_public_router,
    create_secure_router,
    create_cached_router,
    create_versioned_router,
    create_microservice_router,
    create_health_router,
    create_debug_router,
    create_api_router_by_type
)

# Re-export all classes and functions for backward compatibility
__all__ = [
    # Base router
    "NeoAPIRouter",
    # Specialized routers
    "VersionedAPIRouter",
    "SecureAPIRouter", 
    "CachedAPIRouter",
    "AdminAPIRouter",
    "TenantAPIRouter",
    "PublicAPIRouter",
    # Factory functions
    "create_admin_router",
    "create_tenant_router",
    "create_public_router",
    "create_secure_router",
    "create_cached_router",
    "create_versioned_router",
    "create_microservice_router",
    "create_health_router",
    "create_debug_router",
    "create_api_router_by_type"
]