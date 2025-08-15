"""
Neo Commons Middleware Package

This package contains reusable middleware components for FastAPI applications
using the neo-commons library.

Components:
- UnifiedContext: All-in-one context, logging, timing, and metadata
- Security: Headers, CORS, rate limiting
- Config: Middleware configuration management
"""

# Unified middleware for all context, logging, timing, and metadata needs
from .unified_context import (
    UnifiedContextMiddleware,
    UnifiedRequestContext,
    get_request_context,
    get_correlation_id, 
    get_request_id,
    track_performance
)

from .security import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware, 
    RateLimitMiddleware
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

# Convenience aliases for backward compatibility
RequestContext = UnifiedRequestContext
RequestContextMiddleware = UnifiedContextMiddleware

__all__ = [
    # Unified middleware for context, logging, timing, and metadata
    "UnifiedContextMiddleware",
    "UnifiedRequestContext", 
    "get_request_context",
    "get_correlation_id", 
    "get_request_id",
    "track_performance",
    
    # Security middleware
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware", 
    "RateLimitMiddleware",
    
    # Configuration
    "MiddlewareConfig",
    "MiddlewareManager",
    "get_middleware_config",
    "create_development_config",
    "create_production_config", 
    "create_testing_config",
    "default_middleware_manager",
    
    # Backward compatibility aliases
    "RequestContext",
    "RequestContextMiddleware",
]