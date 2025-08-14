"""
Enhanced exception handlers for neo-commons with protocol-based dependency injection.
Provides flexible exception handling without tight coupling to application-specific settings.
"""
import logging
from typing import Optional, Protocol, runtime_checkable, Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from neo_commons.models.base import APIResponse

logger = logging.getLogger(__name__)


@runtime_checkable
class BaseExceptionProtocol(Protocol):
    """Protocol for base application exceptions."""
    
    @property
    def status_code(self) -> int:
        """HTTP status code for the exception."""
        ...
    
    @property
    def message(self) -> str:
        """Error message."""
        ...
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        ...


@runtime_checkable
class ApplicationConfigProtocol(Protocol):
    """Protocol for application configuration."""
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        ...


class DefaultApplicationConfig:
    """Default implementation of application configuration."""
    
    def __init__(self, is_production: bool = False):
        self._is_production = is_production
    
    @property
    def is_production(self) -> bool:
        return self._is_production


class DefaultBaseException(Exception):
    """Default base exception implementation."""
    
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self._message = message
        self._status_code = status_code
    
    @property
    def status_code(self) -> int:
        return self._status_code
    
    @property
    def message(self) -> str:
        return self._message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code
        }


def register_exception_handlers(
    app: FastAPI,
    base_exception_class: Optional[type] = None,
    app_config: Optional[ApplicationConfigProtocol] = None
) -> None:
    """
    Register exception handlers with dependency injection.
    
    Args:
        app: FastAPI application instance
        base_exception_class: Base exception class to handle (must implement BaseExceptionProtocol)
        app_config: Application configuration for production checks
    """
    config = app_config or DefaultApplicationConfig()
    
    # Handle custom base exception if provided
    if base_exception_class:
        @app.exception_handler(base_exception_class)
        async def custom_base_exception_handler(request: Request, exc: BaseExceptionProtocol):
            """Handle application-specific base exceptions."""
            logger.warning(
                f"Application exception: {exc.__class__.__name__}: {exc.message}",
                extra={
                    "exception_type": exc.__class__.__name__,
                    "status_code": exc.status_code,
                    "path": request.url.path,
                    "method": request.method
                }
            )
            
            return JSONResponse(
                status_code=exc.status_code,
                content=APIResponse.error_response(
                    message=exc.message,
                    errors=[exc.to_dict()]
                ).model_dump()
            )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle value errors with detailed logging."""
        logger.warning(
            f"ValueError in request: {str(exc)}",
            extra={
                "exception_type": "ValueError",
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params)
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=APIResponse.error_response(
                message="Invalid input data",
                errors=[{
                    "error": "ValueError",
                    "message": str(exc) if not config.is_production else "Invalid input data",
                    "status_code": 400
                }]
            ).model_dump()
        )
    
    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        """Handle key errors (missing required fields)."""
        logger.warning(
            f"KeyError in request: {str(exc)}",
            extra={
                "exception_type": "KeyError",
                "path": request.url.path,
                "method": request.method,
                "missing_key": str(exc)
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=APIResponse.error_response(
                message="Missing required field",
                errors=[{
                    "error": "KeyError",
                    "message": f"Missing required field: {str(exc)}" if not config.is_production else "Missing required field",
                    "status_code": 400
                }]
            ).model_dump()
        )
    
    @app.exception_handler(TypeError)
    async def type_error_handler(request: Request, exc: TypeError):
        """Handle type errors (invalid data types)."""
        logger.warning(
            f"TypeError in request: {str(exc)}",
            extra={
                "exception_type": "TypeError",
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=APIResponse.error_response(
                message="Invalid data type",
                errors=[{
                    "error": "TypeError",
                    "message": str(exc) if not config.is_production else "Invalid data type",
                    "status_code": 400
                }]
            ).model_dump()
        )
    
    @app.exception_handler(PermissionError)
    async def permission_error_handler(request: Request, exc: PermissionError):
        """Handle permission errors."""
        logger.warning(
            f"PermissionError in request: {str(exc)}",
            extra={
                "exception_type": "PermissionError",
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=APIResponse.error_response(
                message="Access denied",
                errors=[{
                    "error": "PermissionError",
                    "message": "You don't have permission to access this resource",
                    "status_code": 403
                }]
            ).model_dump()
        )
    
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError):
        """Handle file not found errors."""
        logger.warning(
            f"FileNotFoundError in request: {str(exc)}",
            extra={
                "exception_type": "FileNotFoundError",
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=APIResponse.error_response(
                message="Resource not found",
                errors=[{
                    "error": "FileNotFoundError",
                    "message": "The requested resource was not found",
                    "status_code": 404
                }]
            ).model_dump()
        )
    
    @app.exception_handler(ConnectionError)
    async def connection_error_handler(request: Request, exc: ConnectionError):
        """Handle connection errors (database, cache, external services)."""
        logger.error(
            f"ConnectionError in request: {str(exc)}",
            exc_info=True,
            extra={
                "exception_type": "ConnectionError",
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=APIResponse.error_response(
                message="Service temporarily unavailable",
                errors=[{
                    "error": "ConnectionError",
                    "message": "Service temporarily unavailable. Please try again later.",
                    "status_code": 503
                }]
            ).model_dump()
        )
    
    @app.exception_handler(TimeoutError)
    async def timeout_error_handler(request: Request, exc: TimeoutError):
        """Handle timeout errors."""
        logger.error(
            f"TimeoutError in request: {str(exc)}",
            exc_info=True,
            extra={
                "exception_type": "TimeoutError",
                "path": request.url.path,
                "method": request.method
            }
        )
        
        return JSONResponse(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            content=APIResponse.error_response(
                message="Request timeout",
                errors=[{
                    "error": "TimeoutError",
                    "message": "The request took too long to process. Please try again.",
                    "status_code": 504
                }]
            ).model_dump()
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other unexpected exceptions."""
        logger.error(
            f"Unhandled exception: {exc.__class__.__name__}: {str(exc)}",
            exc_info=True,
            extra={
                "exception_type": exc.__class__.__name__,
                "path": request.url.path,
                "method": request.method,
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("user-agent", "unknown")
            }
        )
        
        # Determine message based on environment
        if config.is_production:
            message = "An unexpected error occurred"
            error_detail = "An unexpected error occurred. Please try again or contact support if the problem persists."
        else:
            message = f"Unexpected error: {exc.__class__.__name__}"
            error_detail = str(exc)
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse.error_response(
                message=message,
                errors=[{
                    "error": exc.__class__.__name__,
                    "message": error_detail,
                    "status_code": 500
                }]
            ).model_dump()
        )
    
    logger.info("Exception handlers registered successfully")


def register_standard_exception_handlers(
    app: FastAPI,
    base_exception_class: Optional[type] = None,
    is_production: bool = False
) -> None:
    """
    Register standard exception handlers with simplified configuration.
    
    Args:
        app: FastAPI application instance
        base_exception_class: Base exception class to handle
        is_production: Whether running in production environment
    """
    config = DefaultApplicationConfig(is_production=is_production)
    register_exception_handlers(
        app=app,
        base_exception_class=base_exception_class,
        app_config=config
    )