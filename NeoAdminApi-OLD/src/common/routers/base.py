"""
Custom APIRouter that handles both trailing and non-trailing slash endpoints.

This router automatically registers both versions of each route (with and without trailing slash)
to avoid 307 redirects and make the API more flexible.
"""
from typing import Any, Callable
from fastapi import APIRouter as FastAPIRouter
from fastapi.types import DecoratedCallable


class NeoAPIRouter(FastAPIRouter):
    """
    Custom APIRouter that automatically handles both trailing and non-trailing slash versions.
    
    This solves the issue where FastAPI returns 307 redirects when accessing an endpoint
    with a different trailing slash pattern than how it was defined.
    
    Example:
        If you define @router.get("/items/"), this will automatically also handle "/items"
        If you define @router.get("/items"), this will automatically also handle "/items/"
    """
    
    def api_route(
        self, 
        path: str, 
        *, 
        include_in_schema: bool = True, 
        **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """
        Override api_route to register both slash variations.
        
        Args:
            path: The URL path for the route
            include_in_schema: Whether to include in OpenAPI schema (only main route is included)
            **kwargs: Additional route configuration
            
        Returns:
            Decorator function for the route handler
        """
        # For root path, don't add alternate
        if path == "/":
            return super().api_route(path, include_in_schema=include_in_schema, **kwargs)
        
        # Determine main and alternate paths
        if path.endswith("/"):
            # Path has trailing slash - also register without
            main_path = path
            alternate_path = path[:-1]
        else:
            # Path has no trailing slash - also register with
            main_path = path
            alternate_path = path + "/"
        
        # Register main path (included in schema)
        add_main_path = super().api_route(
            main_path, 
            include_in_schema=include_in_schema, 
            **kwargs
        )
        
        # Register alternate path (hidden from schema to avoid duplication)
        add_alternate_path = super().api_route(
            alternate_path, 
            include_in_schema=False,  # Hide from OpenAPI docs
            **kwargs
        )

        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            """Decorator that registers both route variations."""
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Registering routes: main={main_path}, alternate={alternate_path}")
            
            # Register alternate path first
            add_alternate_path(func)
            # Then register main path
            return add_main_path(func)

        return decorator