"""Error handling middleware for FastAPI applications.

Provides comprehensive error handling, logging, and user-friendly error responses
with proper status codes and security considerations.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable, Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from datetime import datetime

from ...core.exceptions import (
    BaseNeoException,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    TenantNotFoundError,
    DatabaseError,
    CacheError,
    ConfigurationError,
    RateLimitExceededError,
    SecurityError
)
from ...core.exceptions import get_http_status_code

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Comprehensive error handling middleware."""
    
    def __init__(
        self,
        app,
        debug: bool = False,
        include_trace: bool = False,
        custom_handlers: Optional[Dict[type, Callable]] = None,
        sensitive_fields: Optional[list] = None
    ):
        super().__init__(app)
        self.debug = debug
        self.include_trace = include_trace
        self.custom_handlers = custom_handlers or {}
        self.sensitive_fields = sensitive_fields or [
            "password", "token", "secret", "key", "credentials"
        ]
        
        # Error statistics
        self.error_stats = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors_by_status": {},
            "last_error_time": None
        }
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Handle errors and provide structured error responses."""
        try:
            response = await call_next(request)
            return response
        
        except Exception as exc:
            return await self._handle_exception(request, exc)
    
    async def _handle_exception(self, request: Request, exc: Exception) -> JSONResponse:
        """Handle and format exceptions into proper HTTP responses."""
        
        # Update error statistics
        self._update_error_stats(exc)
        
        # Get request context for logging
        request_context = self._get_request_context(request)
        
        # Handle different exception types
        if isinstance(exc, HTTPException):
            return await self._handle_http_exception(request, exc, request_context)
        
        elif isinstance(exc, BaseNeoException):
            return await self._handle_neo_exception(request, exc, request_context)
        
        elif exc.__class__ in self.custom_handlers:
            return await self.custom_handlers[exc.__class__](request, exc, request_context)
        
        else:
            return await self._handle_unknown_exception(request, exc, request_context)
    
    async def _handle_http_exception(
        self, 
        request: Request, 
        exc: HTTPException, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle FastAPI HTTPException."""
        
        error_response = {
            "error": {
                "type": "http_error",
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.get("request_id"),
                "path": context.get("path")
            }
        }
        
        # Add debug information if enabled
        if self.debug and hasattr(exc, 'headers'):
            error_response["error"]["headers"] = exc.headers
        
        # Log the error
        logger.warning(
            f"HTTP error {exc.status_code}: {exc.detail}",
            extra={
                "error_context": context,
                "error_details": error_response
            }
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=getattr(exc, 'headers', None)
        )
    
    async def _handle_neo_exception(
        self, 
        request: Request, 
        exc: BaseNeoException, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle custom Neo exceptions."""
        
        # Get HTTP status code from mapping
        status_code = get_http_status_code(exc)
        
        error_response = {
            "error": {
                "type": exc.__class__.__name__.lower().replace("error", ""),
                "code": status_code,
                "message": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.get("request_id"),
                "path": context.get("path")
            }
        }
        
        # Add exception-specific details
        if hasattr(exc, 'details') and exc.details:
            error_response["error"]["details"] = self._sanitize_error_details(exc.details)
        
        if hasattr(exc, 'error_code') and exc.error_code:
            error_response["error"]["error_code"] = exc.error_code
        
        # Add debug information if enabled
        if self.debug:
            error_response["error"]["debug"] = {
                "exception_type": exc.__class__.__name__,
                "module": exc.__class__.__module__
            }
        
        # Add stack trace if enabled and not a user error
        if self.include_trace and not self._is_user_error(exc):
            error_response["error"]["trace"] = traceback.format_exc()
        
        # Determine log level based on exception type
        if isinstance(exc, (AuthenticationError, AuthorizationError, ValidationError)):
            log_level = logging.WARNING
        elif isinstance(exc, (DatabaseError, CacheError, ConfigurationError)):
            log_level = logging.ERROR
        else:
            log_level = logging.INFO
        
        # Log the error
        logger.log(
            log_level,
            f"{exc.__class__.__name__}: {exc}",
            extra={
                "error_context": context,
                "error_details": error_response
            },
            exc_info=log_level >= logging.ERROR
        )
        
        return JSONResponse(
            status_code=status_code,
            content=error_response
        )
    
    async def _handle_unknown_exception(
        self, 
        request: Request, 
        exc: Exception, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        
        error_response = {
            "error": {
                "type": "internal_error",
                "code": 500,
                "message": "An internal server error occurred" if not self.debug else str(exc),
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.get("request_id"),
                "path": context.get("path")
            }
        }
        
        # Add debug information if enabled
        if self.debug:
            error_response["error"]["debug"] = {
                "exception_type": exc.__class__.__name__,
                "module": exc.__class__.__module__,
                "args": [str(arg) for arg in exc.args]
            }
        
        # Add stack trace if enabled
        if self.include_trace:
            error_response["error"]["trace"] = traceback.format_exc()
        
        # Log the error with full details
        logger.error(
            f"Unhandled exception: {exc.__class__.__name__}: {exc}",
            extra={
                "error_context": context,
                "error_details": error_response
            },
            exc_info=True
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )
    
    def _get_request_context(self, request: Request) -> Dict[str, Any]:
        """Extract request context for error logging."""
        context = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add request ID if available
        if hasattr(request.state, 'request_id'):
            context["request_id"] = request.state.request_id
        
        # Add user context if available
        if hasattr(request.state, 'user_context') and request.state.user_context:
            user_context = request.state.user_context
            context.update({
                "user_id": str(user_context.user_id) if user_context.user_id else None,
                "tenant_id": str(user_context.tenant_id) if user_context.tenant_id else None,
                "user_email": user_context.user_email
            })
        
        # Add tenant context if available
        if hasattr(request.state, 'tenant_context') and request.state.tenant_context:
            tenant_context = request.state.tenant_context
            context.update({
                "tenant_slug": tenant_context.get("tenant_slug"),
                "organization_id": tenant_context.get("organization_id")
            })
        
        return context
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _sanitize_error_details(self, details: Any) -> Any:
        """Sanitize error details to remove sensitive information."""
        if isinstance(details, dict):
            sanitized = {}
            for key, value in details.items():
                key_lower = key.lower()
                
                if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_error_details(value)
            
            return sanitized
        
        elif isinstance(details, list):
            return [self._sanitize_error_details(item) for item in details]
        
        elif isinstance(details, str):
            # Check for sensitive patterns in strings
            for sensitive in self.sensitive_fields:
                if sensitive.lower() in details.lower():
                    return "[REDACTED - contains sensitive data]"
            return details
        
        else:
            return details
    
    def _is_user_error(self, exc: Exception) -> bool:
        """Determine if exception is caused by user input (not system error)."""
        user_error_types = (
            AuthenticationError,
            AuthorizationError,
            ValidationError,
            TenantNotFoundError,
            RateLimitExceededError,
            SecurityError
        )
        
        return isinstance(exc, user_error_types)
    
    def _update_error_stats(self, exc: Exception) -> None:
        """Update error statistics."""
        self.error_stats["total_errors"] += 1
        self.error_stats["last_error_time"] = datetime.utcnow().isoformat()
        
        # Track by exception type
        exc_type = exc.__class__.__name__
        self.error_stats["errors_by_type"][exc_type] = (
            self.error_stats["errors_by_type"].get(exc_type, 0) + 1
        )
        
        # Track by HTTP status code
        if isinstance(exc, HTTPException):
            status_code = exc.status_code
        elif isinstance(exc, BaseNeoException):
            status_code = get_http_status_code(exc)
        else:
            status_code = 500
        
        self.error_stats["errors_by_status"][status_code] = (
            self.error_stats["errors_by_status"].get(status_code, 0) + 1
        )
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return self.error_stats.copy()
    
    def reset_error_stats(self) -> None:
        """Reset error statistics."""
        self.error_stats = {
            "total_errors": 0,
            "errors_by_type": {},
            "errors_by_status": {},
            "last_error_time": None
        }


class ValidationErrorHandler:
    """Custom handler for validation errors."""
    
    @staticmethod
    async def handle_validation_error(
        request: Request, 
        exc: ValidationError, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle validation errors with detailed field information."""
        
        error_response = {
            "error": {
                "type": "validation_error",
                "code": 422,
                "message": "Validation failed",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.get("request_id"),
                "path": context.get("path"),
                "details": {
                    "validation_errors": exc.details if hasattr(exc, 'details') else [str(exc)]
                }
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response
        )


class DatabaseErrorHandler:
    """Custom handler for database errors."""
    
    @staticmethod
    async def handle_database_error(
        request: Request, 
        exc: DatabaseError, 
        context: Dict[str, Any]
    ) -> JSONResponse:
        """Handle database errors with appropriate abstraction."""
        
        # Don't expose internal database details in production
        public_message = "A database error occurred"
        if hasattr(exc, 'user_message') and exc.user_message:
            public_message = exc.user_message
        
        error_response = {
            "error": {
                "type": "database_error",
                "code": 500,
                "message": public_message,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.get("request_id"),
                "path": context.get("path")
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )