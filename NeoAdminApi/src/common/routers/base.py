"""
Custom APIRouter that handles both trailing and non-trailing slash endpoints.

ENHANCED WITH NEO-COMMONS: Now using structured logging and dependency injection patterns.
This router automatically registers both versions of each route (with and without trailing slash)
to avoid 307 redirects and make the API more flexible.
"""
from typing import Any, Callable, Optional
from fastapi import APIRouter as FastAPIRouter
from fastapi.types import DecoratedCallable
from loguru import logger

# NEO-COMMONS INTEGRATION: Enhanced logging utilities
from neo_commons.utils.datetime import utc_now


class NeoAPIRouter(FastAPIRouter):
    """
    Custom APIRouter that automatically handles both trailing and non-trailing slash versions.
    
    ENHANCED WITH NEO-COMMONS: Now includes structured logging, route registration tracking,
    and improved error handling using neo-commons patterns.
    
    This solves the issue where FastAPI returns 307 redirects when accessing an endpoint
    with a different trailing slash pattern than how it was defined.
    
    Example:
        If you define @router.get("/items/"), this will automatically also handle "/items"
        If you define @router.get("/items"), this will automatically also handle "/items/"
    
    Features:
        - Automatic route duplication for trailing slash flexibility
        - Structured logging for route registration
        - Enhanced debugging and monitoring capabilities
        - Integration with neo-commons logging patterns
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize router with enhanced logging."""
        super().__init__(*args, **kwargs)
        self._route_registration_count = 0
        self._registered_routes = set()
        
        # Log router initialization
        logger.debug(
            "NeoAPIRouter initialized",
            extra={
                "router_prefix": getattr(self, 'prefix', ''),
                "router_tags": getattr(self, 'tags', []),
                "initialized_at": utc_now().isoformat()
            }
        )
    
    def api_route(
        self, 
        path: str, 
        *, 
        include_in_schema: bool = True, 
        **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """
        Override api_route to register both slash variations with enhanced logging.
        
        ENHANCED WITH NEO-COMMONS: Now includes structured logging for route registration,
        route tracking, and error handling using neo-commons patterns.
        
        Args:
            path: The URL path for the route
            include_in_schema: Whether to include in OpenAPI schema (only main route is included)
            **kwargs: Additional route configuration
            
        Returns:
            Decorator function for the route handler
        """
        # For root path, don't add alternate
        if path == "/":
            logger.debug(
                "Registering root path route",
                extra={"path": path, "include_in_schema": include_in_schema}
            )
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
        
        # Extract method information for logging
        methods = kwargs.get('methods', ['GET'])
        
        # Enhanced logging for route registration
        logger.debug(
            "Preparing dual route registration",
            extra={
                "main_path": main_path,
                "alternate_path": alternate_path,
                "methods": methods,
                "include_in_schema": include_in_schema,
                "router_prefix": getattr(self, 'prefix', ''),
                "router_tags": getattr(self, 'tags', [])
            }
        )
        
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
            """
            Decorator that registers both route variations with enhanced error handling.
            
            ENHANCED WITH NEO-COMMONS: Now includes structured logging and error tracking.
            """
            try:
                # Track route registration
                self._route_registration_count += 1
                self._registered_routes.add(main_path)
                self._registered_routes.add(alternate_path)
                
                # Enhanced structured logging
                logger.debug(
                    "Registering route variations",
                    extra={
                        "main_path": main_path,
                        "alternate_path": alternate_path,
                        "methods": methods,
                        "function_name": getattr(func, '__name__', 'unknown'),
                        "registration_count": self._route_registration_count,
                        "total_routes": len(self._registered_routes),
                        "registered_at": utc_now().isoformat()
                    }
                )
                
                # Register alternate path first
                add_alternate_path(func)
                # Then register main path
                result = add_main_path(func)
                
                logger.debug(
                    "Route registration completed successfully",
                    extra={
                        "main_path": main_path,
                        "alternate_path": alternate_path,
                        "function_name": getattr(func, '__name__', 'unknown')
                    }
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Route registration failed",
                    extra={
                        "main_path": main_path,
                        "alternate_path": alternate_path,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "function_name": getattr(func, '__name__', 'unknown')
                    }
                )
                raise

        return decorator
    
    def get_route_stats(self) -> dict:
        """
        Get statistics about registered routes.
        
        Returns:
            dict: Route registration statistics
        """
        return {
            "total_routes": len(self._registered_routes),
            "registration_count": self._route_registration_count,
            "router_prefix": getattr(self, 'prefix', ''),
            "router_tags": getattr(self, 'tags', []),
            "registered_routes": sorted(list(self._registered_routes))
        }