"""
Event context middleware.

ONLY handles event-specific request context enrichment.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ....core.shared import RequestContext
from ....core.value_objects import UserId, TenantId


class EventContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enrich request context with event-specific information.
    
    Adds correlation IDs, request timing, and event-specific headers.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add event context."""
        start_time = time.time()
        
        # Generate correlation ID if not present
        correlation_id = (
            request.headers.get("X-Correlation-ID") or
            request.headers.get("X-Request-ID") or
            f"req_{uuid.uuid4().hex[:12]}"
        )
        
        # Extract trace ID for distributed tracing
        trace_id = (
            request.headers.get("X-Trace-ID") or
            request.headers.get("Traceparent") or
            f"trace_{uuid.uuid4().hex[:16]}"
        )
        
        # Store context in request state
        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id
        request.state.start_time = start_time
        
        # Add request metadata
        request.state.request_metadata = {
            "method": request.method,
            "path": str(request.url.path),
            "query_params": dict(request.query_params),
            "user_agent": request.headers.get("User-Agent", ""),
            "client_ip": self._get_client_ip(request),
            "event_api_version": "v1",
        }
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Add event-specific response headers
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Processing-Time-MS"] = str(round(processing_time * 1000, 2))
            response.headers["X-Event-API-Version"] = "v1"
            
            # Add performance timing headers
            if processing_time > 1.0:  # Log slow requests
                response.headers["X-Slow-Request"] = "true"
            
            return response
            
        except Exception as e:
            # Ensure correlation ID is available for error tracking
            response = Response(
                content={"error": "Internal server error", "correlation_id": correlation_id},
                status_code=500,
                headers={
                    "X-Correlation-ID": correlation_id,
                    "X-Trace-ID": trace_id,
                    "Content-Type": "application/json"
                }
            )
            return response
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request headers."""
        # Check for forwarded headers first (proxy/load balancer scenarios)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


# Middleware instance for easy import
event_context_middleware = EventContextMiddleware