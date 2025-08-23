"""
Application exception handlers for FastAPI applications.

This module provides generic exception handlers that can be used across
all services in the NeoMultiTenant platform.
"""
from typing import Dict, Any, Optional, Callable
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import logging

from ..exceptions.base import NeoException

logger = logging.getLogger(__name__)


class ExceptionHandlerRegistry:
    """Registry for managing exception handlers across the platform."""
    
    def __init__(
        self,
        response_formatter: Optional[Callable[[str, Optional[list], Optional[Dict[str, Any]]], Dict[str, Any]]] = None,
        is_production: bool = True
    ):
        """
        Initialize exception handler registry.
        
        Args:
            response_formatter: Function to format error responses
            is_production: Whether running in production mode
        """
        self.response_formatter = response_formatter or self._default_response_formatter
        self.is_production = is_production
    
    def _default_response_formatter(
        self, 
        message: str, 
        errors: Optional[list] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Default error response formatter."""
        return {
            "success": False,
            "message": message,
            "errors": errors or [],
            "data": None,
            "metadata": metadata or {}
        }
    
    def register_handlers(self, app: FastAPI) -> None:
        """Register exception handlers for the application.
        
        Args:
            app: FastAPI application instance
        """
        @app.exception_handler(NeoException)
        async def neo_exception_handler(request: Request, exc: NeoException):
            """Handle platform-specific exceptions."""
            return JSONResponse(
                status_code=exc.status_code,
                content=self.response_formatter(
                    message=exc.message,
                    errors=[exc.to_dict()]
                )
            )
        
        @app.exception_handler(ValueError)
        async def value_error_handler(request: Request, exc: ValueError):
            """Handle value errors."""
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=self.response_formatter(message=str(exc))
            )
        
        @app.exception_handler(KeyError) 
        async def key_error_handler(request: Request, exc: KeyError):
            """Handle key errors."""
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=self.response_formatter(
                    message=f"Missing required field: {str(exc)}"
                )
            )
        
        @app.exception_handler(TypeError)
        async def type_error_handler(request: Request, exc: TypeError):
            """Handle type errors.""" 
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=self.response_formatter(
                    message=f"Type error: {str(exc)}"
                )
            )
        
        @app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            """Handle unexpected exceptions."""
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            
            if self.is_production:
                message = "An unexpected error occurred"
            else:
                message = str(exc)
            
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=self.response_formatter(message=message)
            )


def register_exception_handlers(
    app: FastAPI,
    response_formatter: Optional[Callable[[str, Optional[list], Optional[Dict[str, Any]]], Dict[str, Any]]] = None,
    is_production: bool = True
) -> None:
    """
    Register exception handlers for a FastAPI application.
    
    This is a convenience function that creates an ExceptionHandlerRegistry
    and registers handlers in one call.
    
    Args:
        app: FastAPI application instance
        response_formatter: Custom response formatter function
        is_production: Whether running in production mode
    """
    registry = ExceptionHandlerRegistry(response_formatter, is_production)
    registry.register_handlers(app)