"""
Structured logging middleware with correlation IDs and comprehensive context.
"""
import time
import json
from typing import Callable, Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from contextvars import ContextVar
from uuid import uuid4

from src.common.utils.uuid import generate_uuid_v7


# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
tenant_id_var: ContextVar[Optional[str]] = ContextVar('tenant_id', default=None)
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured logging with correlation IDs and request context.
    
    Features:
    - Request/response logging with timing
    - Correlation ID generation and propagation
    - User and tenant context extraction
    - Performance metrics tracking
    - Error context preservation
    """
    
    def __init__(
        self,
        app,
        *,
        log_requests: bool = True,
        log_responses: bool = True,
        log_body: bool = False,
        log_headers: bool = False,
        exclude_paths: Optional[list] = None,
        max_body_size: int = 1024,
        sensitive_headers: Optional[list] = None
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_body = log_body
        self.log_headers = log_headers
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json"]
        self.max_body_size = max_body_size
        self.sensitive_headers = sensitive_headers or ["authorization", "cookie", "x-api-key"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with structured logging."""
        start_time = time.time()
        
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Generate correlation and request IDs
        correlation_id = self._extract_or_generate_correlation_id(request)
        request_id = generate_uuid_v7()
        
        # Set context variables
        request_id_var.set(request_id)
        correlation_id_var.set(correlation_id)
        
        # Extract user and tenant context
        user_id = self._extract_user_id(request)
        tenant_id = self._extract_tenant_id(request)
        
        if user_id:
            user_id_var.set(user_id)
        if tenant_id:
            tenant_id_var.set(tenant_id)
        
        # Store in request state for access by other components
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.user_id = user_id
        request.state.tenant_id = tenant_id
        request.state.start_time = start_time
        
        # Reset performance counters for new request
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.reset_counters()
        except ImportError:
            pass  # Metadata system not available
        
        # Log incoming request
        if self.log_requests:
            await self._log_request(request, correlation_id, request_id, user_id, tenant_id)
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate timing
            process_time = time.time() - start_time
            
            # Log response
            if self.log_responses:
                await self._log_response(request, response, process_time, correlation_id, request_id)
            
            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as exc:
            # Log error with full context
            process_time = time.time() - start_time
            await self._log_error(request, exc, process_time, correlation_id, request_id)
            raise
    
    def _extract_or_generate_correlation_id(self, request: Request) -> str:
        """Extract correlation ID from headers or generate new one."""
        correlation_id = (
            request.headers.get("x-correlation-id") or
            request.headers.get("x-request-id") or
            request.headers.get("correlation-id") or
            generate_uuid_v7()
        )
        return correlation_id
    
    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from JWT token or headers."""
        # Try to get from JWT token if available
        if hasattr(request.state, 'user') and request.state.user:
            return getattr(request.state.user, 'id', None)
        
        # Try to get from headers
        return request.headers.get("x-user-id")
    
    def _extract_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request context."""
        # Try to get from request state (set by auth middleware)
        if hasattr(request.state, 'tenant_id'):
            return request.state.tenant_id
        
        # Try to get from headers
        return request.headers.get("x-tenant-id")
    
    async def _log_request(
        self,
        request: Request,
        correlation_id: str,
        request_id: str,
        user_id: Optional[str],
        tenant_id: Optional[str]
    ):
        """Log incoming request with context."""
        log_data = {
            "event": "request_started",
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params) if request.query_params else None,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length")
        }
        
        # Add headers if requested
        if self.log_headers:
            log_data["headers"] = self._sanitize_headers(dict(request.headers))
        
        # Add body if requested and content type is suitable
        if self.log_body and self._should_log_body(request):
            try:
                body = await self._get_request_body(request)
                if body:
                    log_data["body"] = body
            except Exception as e:
                log_data["body_error"] = str(e)
        
        logger.info("Incoming request", **log_data)
    
    async def _log_response(
        self,
        request: Request,
        response: Response,
        process_time: float,
        correlation_id: str,
        request_id: str
    ):
        """Log response with timing and context."""
        log_data = {
            "event": "request_completed",
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "correlation_id": correlation_id,
            "request_id": request_id,
            "response_size": len(response.body) if hasattr(response, 'body') else None
        }
        
        # Add performance classification
        if process_time > 5.0:
            log_data["performance"] = "very_slow"
            log_level = "warning"
        elif process_time > 1.0:
            log_data["performance"] = "slow"
            log_level = "warning"
        elif process_time > 0.1:
            log_data["performance"] = "normal"
            log_level = "info"
        else:
            log_data["performance"] = "fast"
            log_level = "info"
        
        # Adjust log level based on status code
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"
        
        getattr(logger, log_level)("Request completed", **log_data)
    
    async def _log_error(
        self,
        request: Request,
        exc: Exception,
        process_time: float,
        correlation_id: str,
        request_id: str
    ):
        """Log error with full context."""
        log_data = {
            "event": "request_error",
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "process_time_ms": round(process_time * 1000, 2),
            "correlation_id": correlation_id,
            "request_id": request_id
        }
        
        logger.error("Request error", **log_data, exc_info=True)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address handling proxies."""
        # Check for forwarded headers (load balancers, proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        if hasattr(request.client, 'host'):
            return request.client.host
        
        return "unknown"
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers from log data."""
        sanitized = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    def _should_log_body(self, request: Request) -> bool:
        """Determine if request body should be logged."""
        content_type = request.headers.get("content-type", "")
        
        # Only log text-based content types
        allowed_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "text/"
        ]
        
        return any(content_type.startswith(allowed) for allowed in allowed_types)
    
    async def _get_request_body(self, request: Request) -> Optional[str]:
        """Safely get request body for logging."""
        try:
            body = await request.body()
            if len(body) > self.max_body_size:
                return f"[BODY TOO LARGE: {len(body)} bytes]"
            
            # Try to decode as text
            try:
                text_body = body.decode('utf-8')
                
                # Try to parse as JSON for pretty formatting
                if request.headers.get("content-type", "").startswith("application/json"):
                    try:
                        json_data = json.loads(text_body)
                        return json.dumps(json_data, separators=(',', ':'))  # Compact JSON
                    except json.JSONDecodeError:
                        pass
                
                return text_body[:self.max_body_size]
                
            except UnicodeDecodeError:
                return f"[BINARY BODY: {len(body)} bytes]"
                
        except Exception:
            return None


def get_request_context() -> Dict[str, Any]:
    """Get current request context from context variables."""
    return {
        "request_id": request_id_var.get(''),
        "correlation_id": correlation_id_var.get(''),
        "user_id": user_id_var.get(),
        "tenant_id": tenant_id_var.get()
    }


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get('')


def get_request_id() -> str:
    """Get current request ID."""
    return request_id_var.get('')