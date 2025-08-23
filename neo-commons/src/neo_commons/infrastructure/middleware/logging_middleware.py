"""Structured logging middleware for FastAPI with request context.

Provides comprehensive request/response logging with tenant and user context,
performance metrics, and structured log format for observability.
"""

import logging
import time
import json
from typing import Optional, Dict, Any, List
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from datetime import datetime
from uuid import uuid4

from ...core.value_objects import UserId, TenantId
from ...utils.uuid import generate_uuid7

logger = logging.getLogger(__name__)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for structured request/response logging."""
    
    def __init__(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        sensitive_headers: Optional[List[str]] = None,
        sensitive_fields: Optional[List[str]] = None,
        max_body_size: int = 1024,
        exempt_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.sensitive_headers = sensitive_headers or [
            "authorization", "cookie", "x-api-key", "x-auth-token"
        ]
        self.sensitive_fields = sensitive_fields or [
            "password", "token", "secret", "key", "credentials"
        ]
        self.max_body_size = max_body_size
        self.exempt_paths = exempt_paths or [
            "/health", "/metrics", "/docs", "/openapi.json"
        ]
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with structured logging."""
        
        # Skip logging for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)
        
        # Generate request ID if not provided
        request_id = request.headers.get("X-Request-ID") or str(generate_uuid7())
        
        # Store request ID in request state
        request.state.request_id = request_id
        
        # Extract context information
        user_context = getattr(request.state, 'user_context', None)
        tenant_context = getattr(request.state, 'tenant_context', None)
        
        # Build base log context
        log_context = {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
        }
        
        # Add user context if available
        if user_context:
            log_context.update({
                "user_id": str(user_context.user_id) if user_context.user_id else None,
                "keycloak_user_id": user_context.keycloak_user_id,
                "user_email": user_context.user_email,
                "user_roles": user_context.user_roles,
            })
        
        # Add tenant context if available
        if tenant_context:
            log_context.update({
                "tenant_id": tenant_context.get("tenant_id"),
                "tenant_slug": tenant_context.get("tenant_slug"),
                "organization_id": tenant_context.get("organization_id"),
                "region": tenant_context.get("region"),
            })
        
        # Log request if enabled
        if self.log_requests:
            request_log = log_context.copy()
            request_log.update({
                "event_type": "request_start",
                "headers": self._sanitize_headers(dict(request.headers)),
            })
            
            # Add request body if enabled and appropriate
            if self.log_request_body and self._should_log_body(request):
                request_body = await self._get_request_body(request)
                if request_body:
                    request_log["request_body"] = self._sanitize_body(request_body)
            
            logger.info("Request started", extra={"structured_data": request_log})
        
        # Process request and measure timing
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Log response if enabled
            if self.log_responses:
                response_log = log_context.copy()
                response_log.update({
                    "event_type": "request_complete",
                    "status_code": response.status_code,
                    "processing_time_ms": round(processing_time * 1000, 2),
                    "response_headers": self._sanitize_headers(dict(response.headers)),
                })
                
                # Determine log level based on status code
                if response.status_code >= 500:
                    log_level = logging.ERROR
                elif response.status_code >= 400:
                    log_level = logging.WARNING
                else:
                    log_level = logging.INFO
                
                logger.log(
                    log_level,
                    f"Request completed - {response.status_code} in {processing_time * 1000:.2f}ms",
                    extra={"structured_data": response_log}
                )
            
            # Add performance headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Processing-Time"] = str(round(processing_time * 1000, 2))
            
            return response
        
        except Exception as e:
            # Calculate processing time for error case
            processing_time = time.time() - start_time
            
            # Log error
            error_log = log_context.copy()
            error_log.update({
                "event_type": "request_error",
                "error_type": type(e).__name__,
                "error_message": str(e),
                "processing_time_ms": round(processing_time * 1000, 2),
            })
            
            logger.error(
                f"Request failed - {type(e).__name__}: {e}",
                extra={"structured_data": error_log},
                exc_info=True
            )
            
            # Re-raise the exception
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to client host
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize sensitive headers for logging."""
        sanitized = {}
        
        for key, value in headers.items():
            key_lower = key.lower()
            
            if key_lower in self.sensitive_headers:
                # Mask sensitive headers
                if len(value) > 8:
                    sanitized[key] = f"{value[:4]}***{value[-4:]}"
                else:
                    sanitized[key] = "***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _sanitize_body(self, body: str) -> str:
        """Sanitize sensitive fields in request/response body."""
        try:
            # Try to parse as JSON and sanitize
            data = json.loads(body)
            sanitized_data = self._sanitize_dict(data)
            return json.dumps(sanitized_data)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, return truncated string
            return body[:self.max_body_size] + "..." if len(body) > self.max_body_size else body
    
    def _sanitize_dict(self, data: Any) -> Any:
        """Recursively sanitize dictionary for sensitive fields."""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                key_lower = key.lower()
                
                if any(sensitive in key_lower for sensitive in self.sensitive_fields):
                    # Mask sensitive fields
                    if isinstance(value, str) and len(value) > 8:
                        sanitized[key] = f"{value[:3]}***{value[-2:]}"
                    else:
                        sanitized[key] = "***"
                else:
                    sanitized[key] = self._sanitize_dict(value)
            
            return sanitized
        
        elif isinstance(data, list):
            return [self._sanitize_dict(item) for item in data]
        
        else:
            return data
    
    def _should_log_body(self, request: Request) -> bool:
        """Determine if request body should be logged."""
        content_type = request.headers.get("Content-Type", "")
        
        # Only log text-based content types
        return any(ct in content_type for ct in [
            "application/json",
            "application/x-www-form-urlencoded",
            "text/"
        ])
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Safely extract request body."""
        try:
            body = await request.body()
            if len(body) <= self.max_body_size:
                return body.decode("utf-8")
            else:
                return body[:self.max_body_size].decode("utf-8", errors="ignore") + "..."
        except Exception as e:
            logger.warning(f"Failed to read request body: {e}")
            return None


class RequestContextLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that automatically includes request context."""
    
    def __init__(self, logger: logging.Logger, request: Request):
        self.request = request
        super().__init__(logger, {})
    
    def process(self, msg, kwargs):
        """Add request context to log records."""
        extra = kwargs.get('extra', {})
        
        # Add request context
        if hasattr(self.request.state, 'request_id'):
            extra['request_id'] = self.request.state.request_id
        
        if hasattr(self.request.state, 'user_context'):
            user_context = self.request.state.user_context
            if user_context:
                extra.update({
                    'user_id': str(user_context.user_id) if user_context.user_id else None,
                    'tenant_id': str(user_context.tenant_id) if user_context.tenant_id else None,
                })
        
        kwargs['extra'] = extra
        return msg, kwargs


def get_request_logger(request: Request) -> RequestContextLoggerAdapter:
    """Get a logger with automatic request context."""
    return RequestContextLoggerAdapter(logger, request)