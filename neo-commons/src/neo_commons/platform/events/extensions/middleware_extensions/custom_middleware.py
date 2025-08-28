"""
Custom middleware for event platform processing.

ONLY handles platform-specific custom middleware implementations.
"""

import time
import logging
from typing import Dict, Any, Optional, List, Callable, Awaitable

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from .middleware_extension import (
    MiddlewareExtension,
    MiddlewareContext,
    MiddlewareResult,
    MiddlewareStage
)
from ....core.value_objects import RequestId, TenantId, UserId


class EventPlatformMiddleware(BaseHTTPMiddleware):
    """
    Custom middleware for event platform.
    
    Integrates with middleware extensions for comprehensive request processing.
    """
    
    def __init__(self, app, extensions: Optional[List[MiddlewareExtension]] = None):
        super().__init__(app)
        self._extensions = extensions or []
        self._logger = logging.getLogger(__name__)
        
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Process request through middleware extensions.
        
        Args:
            request: HTTP request
            call_next: Next middleware in chain
            
        Returns:
            HTTP response
        """
        start_time = time.time()
        request_id = self._generate_request_id()
        
        # Extract tenant and user context
        tenant_id = self._extract_tenant_id(request)
        user_id = self._extract_user_id(request)
        
        # Create middleware context
        context = MiddlewareContext(
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
            request_path=str(request.url.path),
            request_method=request.method,
            stage=MiddlewareStage.PRE_REQUEST,
            metadata={}
        )
        
        # Add request ID to request state
        request.state.request_id = request_id
        
        try:
            # Execute pre-request extensions
            pre_result = await self._execute_extensions(
                MiddlewareStage.PRE_REQUEST,
                context,
                request
            )
            
            # Check if any extension blocked the request
            if not pre_result.continue_processing:
                return self._create_error_response(
                    pre_result.error_message or "Request blocked by middleware",
                    429 if "rate limit" in (pre_result.error_message or "").lower() else 403,
                    pre_result.additional_headers
                )
                
            # Process request
            response = await call_next(request)
            
            # Update context for post-request processing
            processing_time = (time.time() - start_time) * 1000
            context.stage = MiddlewareStage.POST_REQUEST
            context.processing_time_ms = processing_time
            
            # Execute post-request extensions
            post_result = await self._execute_extensions(
                MiddlewareStage.POST_REQUEST,
                context,
                request,
                response
            )
            
            # Add headers from extensions
            if post_result.additional_headers:
                for header_name, header_value in post_result.additional_headers.items():
                    response.headers[header_name] = header_value
                    
            return response
            
        except Exception as e:
            # Update context for error processing
            processing_time = (time.time() - start_time) * 1000
            context.stage = MiddlewareStage.ON_ERROR
            context.processing_time_ms = processing_time
            context.error_message = str(e)
            
            # Execute error extensions
            await self._execute_extensions(
                MiddlewareStage.ON_ERROR,
                context,
                request,
                error=e
            )
            
            # Re-raise the exception
            raise
            
    async def _execute_extensions(
        self,
        stage: MiddlewareStage,
        context: MiddlewareContext,
        request: Request,
        response: Optional[Response] = None,
        error: Optional[Exception] = None
    ) -> MiddlewareResult:
        """
        Execute middleware extensions for a specific stage.
        
        Args:
            stage: Middleware stage
            context: Processing context
            request: HTTP request
            response: HTTP response (for post-request stage)
            error: Exception (for error stage)
            
        Returns:
            Aggregated middleware result
        """
        aggregated_result = MiddlewareResult(success=True, continue_processing=True)
        additional_headers = {}
        
        # Filter extensions that support this stage and apply to this path
        applicable_extensions = [
            ext for ext in self._extensions
            if ext.enabled and ext.supports_stage(stage) and ext.matches_path(context.request_path)
        ]
        
        # Sort by priority
        applicable_extensions.sort(key=lambda x: x.priority)
        
        for extension in applicable_extensions:
            try:
                # Execute appropriate method based on stage
                if stage == MiddlewareStage.PRE_REQUEST:
                    result = await extension.process_request(context, request)
                elif stage == MiddlewareStage.POST_REQUEST and response:
                    result = await extension.process_response(context, request, response)
                elif stage == MiddlewareStage.ON_ERROR and error:
                    result = await extension.process_error(context, request, error)
                else:
                    continue
                    
                # Aggregate results
                if not result.success:
                    aggregated_result.success = False
                    aggregated_result.error_message = result.error_message
                    
                if not result.continue_processing:
                    aggregated_result.continue_processing = False
                    
                # Collect additional headers
                if result.additional_headers:
                    additional_headers.update(result.additional_headers)
                    
                # Update context metadata
                if result.additional_metadata:
                    context.metadata.update(result.additional_metadata)
                    
                # Stop processing if extension requested it
                if not result.continue_processing:
                    break
                    
            except Exception as e:
                self._logger.error(f"Extension {extension.name} failed: {e}", exc_info=True)
                # Continue with other extensions
                
        # Set aggregated headers
        if additional_headers:
            aggregated_result.additional_headers = additional_headers
            
        return aggregated_result
        
    def _generate_request_id(self) -> RequestId:
        """Generate a unique request ID."""
        import uuid
        return RequestId(str(uuid.uuid4()))
        
    def _extract_tenant_id(self, request: Request) -> Optional[TenantId]:
        """
        Extract tenant ID from request.
        
        Args:
            request: HTTP request
            
        Returns:
            Tenant ID if found, None otherwise
        """
        # Check headers first
        tenant_header = request.headers.get("X-Tenant-ID") or request.headers.get("x-tenant-id")
        if tenant_header:
            return TenantId(tenant_header)
            
        # Check query parameters
        tenant_param = request.query_params.get("tenant_id")
        if tenant_param:
            return TenantId(tenant_param)
            
        # Check path parameters (if using tenant-specific URLs)
        path_parts = str(request.url.path).strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "tenants":
            return TenantId(path_parts[1])
            
        return None
        
    def _extract_user_id(self, request: Request) -> Optional[UserId]:
        """
        Extract user ID from request.
        
        Args:
            request: HTTP request
            
        Returns:
            User ID if found, None otherwise
        """
        # Check if user info is available from authentication
        if hasattr(request.state, 'user_id'):
            return UserId(request.state.user_id)
            
        # Check headers
        user_header = request.headers.get("X-User-ID") or request.headers.get("x-user-id")
        if user_header:
            return UserId(user_header)
            
        return None
        
    def _create_error_response(
        self,
        message: str,
        status_code: int = 400,
        headers: Optional[Dict[str, str]] = None
    ) -> Response:
        """
        Create error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            headers: Optional additional headers
            
        Returns:
            Error response
        """
        from starlette.responses import JSONResponse
        
        response_data = {
            "error": message,
            "status_code": status_code
        }
        
        response = JSONResponse(content=response_data, status_code=status_code)
        
        if headers:
            for header_name, header_value in headers.items():
                response.headers[header_name] = header_value
                
        return response


class CustomMiddleware:
    """
    Custom middleware implementations for event platform.
    
    Provides concrete middleware extensions.
    """
    
    @staticmethod
    def create_request_logging_middleware(
        log_level: str = "INFO",
        include_request_body: bool = False,
        include_response_body: bool = False
    ) -> "RequestLoggingMiddleware":
        """
        Create request logging middleware.
        
        Args:
            log_level: Logging level
            include_request_body: Whether to log request body
            include_response_body: Whether to log response body
            
        Returns:
            Request logging middleware instance
        """
        return RequestLoggingMiddleware(
            log_level=log_level,
            include_request_body=include_request_body,
            include_response_body=include_response_body
        )
        
    @staticmethod
    def create_security_headers_middleware(
        custom_headers: Optional[Dict[str, str]] = None
    ) -> "SecurityHeadersMiddleware":
        """
        Create security headers middleware.
        
        Args:
            custom_headers: Additional custom headers
            
        Returns:
            Security headers middleware instance
        """
        return SecurityHeadersMiddleware(custom_headers=custom_headers or {})
        
    @staticmethod
    def create_rate_limit_middleware(
        requests_per_minute: int = 60,
        burst_size: int = 10
    ) -> "RateLimitMiddleware":
        """
        Create rate limiting middleware.
        
        Args:
            requests_per_minute: Rate limit per minute
            burst_size: Burst allowance
            
        Returns:
            Rate limit middleware instance
        """
        return RateLimitMiddleware(
            requests_per_minute=requests_per_minute,
            burst_size=burst_size
        )


class RequestLoggingMiddleware(MiddlewareExtension):
    """Request logging middleware implementation."""
    
    def __init__(self, log_level: str = "INFO", include_request_body: bool = False, include_response_body: bool = False):
        self.log_level = log_level
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self._logger = logging.getLogger(__name__)
        
    @property
    def name(self) -> str:
        return "request_logging_middleware"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "Logs HTTP requests and responses with configurable detail"
        
    @property
    def middleware_stages(self) -> List[MiddlewareStage]:
        return [MiddlewareStage.PRE_REQUEST, MiddlewareStage.POST_REQUEST, MiddlewareStage.ON_ERROR]
        
    async def process_request(self, context: MiddlewareContext, request: Request) -> MiddlewareResult:
        """Log incoming request."""
        log_data = {
            "request_id": context.request_id.value,
            "method": context.request_method,
            "path": context.request_path,
            "tenant_id": context.tenant_id.value if context.tenant_id else None,
            "user_id": context.user_id.value if context.user_id else None,
            "headers": dict(request.headers) if self.log_level == "DEBUG" else None,
        }
        
        if self.include_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                log_data["body_size"] = len(body)
                if self.log_level == "DEBUG":
                    log_data["body"] = body.decode("utf-8", errors="ignore")[:1000]  # Truncate
            except Exception:
                pass
                
        self._logger.info(f"Request started: {log_data}")
        return MiddlewareResult(success=True, continue_processing=True)
        
    async def process_response(self, context: MiddlewareContext, request: Request, response: Response) -> MiddlewareResult:
        """Log outgoing response."""
        log_data = {
            "request_id": context.request_id.value,
            "status_code": response.status_code,
            "processing_time_ms": context.processing_time_ms,
            "response_headers": dict(response.headers) if self.log_level == "DEBUG" else None,
        }
        
        self._logger.info(f"Request completed: {log_data}")
        return MiddlewareResult(success=True, continue_processing=True)
        
    async def process_error(self, context: MiddlewareContext, request: Request, error: Exception) -> MiddlewareResult:
        """Log request error."""
        log_data = {
            "request_id": context.request_id.value,
            "error": str(error),
            "error_type": type(error).__name__,
            "processing_time_ms": context.processing_time_ms,
        }
        
        self._logger.error(f"Request failed: {log_data}")
        return MiddlewareResult(success=True, continue_processing=True)


class SecurityHeadersMiddleware(MiddlewareExtension):
    """Security headers middleware implementation."""
    
    def __init__(self, custom_headers: Optional[Dict[str, str]] = None):
        self.custom_headers = custom_headers or {}
        
    @property
    def name(self) -> str:
        return "security_headers_middleware"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "Adds security headers to HTTP responses"
        
    @property
    def middleware_stages(self) -> List[MiddlewareStage]:
        return [MiddlewareStage.POST_REQUEST]
        
    async def process_request(self, context: MiddlewareContext, request: Request) -> MiddlewareResult:
        """Security headers don't process requests."""
        return MiddlewareResult(success=True, continue_processing=True)
        
    async def process_response(self, context: MiddlewareContext, request: Request, response: Response) -> MiddlewareResult:
        """Add security headers to response."""
        default_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Content-Security-Policy": "default-src 'self'",
        }
        
        # Merge with custom headers
        security_headers = {**default_headers, **self.custom_headers}
        
        return MiddlewareResult(
            success=True,
            continue_processing=True,
            additional_headers=security_headers
        )


class RateLimitMiddleware(MiddlewareExtension):
    """Rate limiting middleware implementation."""
    
    def __init__(self, requests_per_minute: int = 60, burst_size: int = 10):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self._request_counts: Dict[str, List[float]] = {}
        
    @property
    def name(self) -> str:
        return "rate_limit_middleware"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "Enforces rate limits on HTTP requests"
        
    @property
    def middleware_stages(self) -> List[MiddlewareStage]:
        return [MiddlewareStage.PRE_REQUEST]
        
    async def process_request(self, context: MiddlewareContext, request: Request) -> MiddlewareResult:
        """Check rate limits for incoming request."""
        # Use tenant ID as rate limit key, fallback to IP
        rate_limit_key = (
            context.tenant_id.value if context.tenant_id 
            else request.client.host if request.client
            else "unknown"
        )
        
        current_time = time.time()
        minute_ago = current_time - 60
        
        # Get or create request history for this key
        if rate_limit_key not in self._request_counts:
            self._request_counts[rate_limit_key] = []
            
        request_times = self._request_counts[rate_limit_key]
        
        # Remove requests older than 1 minute
        request_times[:] = [t for t in request_times if t > minute_ago]
        
        # Check if rate limit exceeded
        if len(request_times) >= self.requests_per_minute:
            headers = {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(min(request_times) + 60)),
                "Retry-After": "60",
            }
            
            return MiddlewareResult(
                success=False,
                continue_processing=False,
                additional_headers=headers,
                error_message="Rate limit exceeded"
            )
            
        # Record this request
        request_times.append(current_time)
        
        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(self.requests_per_minute),
            "X-RateLimit-Remaining": str(max(0, self.requests_per_minute - len(request_times))),
        }
        
        return MiddlewareResult(
            success=True,
            continue_processing=True,
            additional_headers=headers
        )