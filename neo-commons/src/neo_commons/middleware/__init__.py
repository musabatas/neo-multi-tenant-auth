"""
Neo Commons Middleware Package

This package contains reusable middleware components for FastAPI applications
in the NeoMultiTenant platform.

Components:
- Security: Headers, CORS, rate limiting
- Logging: Structured request/response logging  
- Timing: Performance tracking and metrics
- Config: Middleware configuration management
- RequestContext: Request metadata collection
"""

from .security import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware, 
    RateLimitMiddleware
)
from .logging import (
    StructuredLoggingMiddleware,
    get_request_context,
    get_correlation_id,
    get_request_id
)
from .timing import (
    TimingMiddleware,
    ResponseSizeMiddleware,
    get_performance_summary
)
from .config import (
    MiddlewareConfig,
    MiddlewareManager,
    get_middleware_config,
    create_development_config,
    create_production_config,
    create_testing_config,
    default_middleware_manager
)
from .request_context import (
    RequestContextMiddleware,
    RequestContext,
    track_performance
)

__all__ = [
    # Security middleware
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware", 
    "RateLimitMiddleware",
    
    # Logging middleware
    "StructuredLoggingMiddleware",
    "get_request_context",
    "get_correlation_id", 
    "get_request_id",
    
    # Timing middleware
    "TimingMiddleware",
    "ResponseSizeMiddleware",
    "get_performance_summary",
    
    # Configuration
    "MiddlewareConfig",
    "MiddlewareManager",
    "get_middleware_config",
    "create_development_config",
    "create_production_config", 
    "create_testing_config",
    "default_middleware_manager",
    
    # Request context
    "RequestContextMiddleware",
    "RequestContext",
    "track_performance"
]