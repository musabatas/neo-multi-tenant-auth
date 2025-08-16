"""
Middleware package for NeoAdminApi.

This package provides organized middleware components for:
- Structured logging with correlation IDs
- Security headers and protections
- Performance timing and monitoring
- Response size tracking
- Rate limiting
- CORS handling

Usage:
    from src.common.middleware import setup_middleware
    
    app = FastAPI()
    setup_middleware(app)

Custom Configuration:
    from src.common.middleware.config import MiddlewareConfig, MiddlewareManager
    
    config = MiddlewareConfig()
    config.logging_config["log_body"] = True
    
    manager = MiddlewareManager(config)
    manager.setup_middleware(app)
"""

from .config import (
    MiddlewareConfig,
    MiddlewareManager,
    create_development_config,
    create_production_config,
    create_testing_config,
    get_middleware_config,
    default_middleware_manager
)

from .logging import (
    StructuredLoggingMiddleware,
    get_request_context,
    get_correlation_id,
    get_request_id,
    request_id_var,
    user_id_var,
    tenant_id_var,
    correlation_id_var
)

from .security import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware,
    RateLimitMiddleware
)

from .timing import (
    TimingMiddleware,
    ResponseSizeMiddleware,
    get_performance_summary
)

from .request_context import (
    RequestContextMiddleware,
    RequestContext,
    track_performance,
    get_request_id,
    get_processing_time,
    get_request_metadata,
    request_id_var,
    start_time_var,
    db_queries_var,
    cache_operations_var,
    performance_markers_var
)

# Convenience function for easy setup
def setup_middleware(app, config=None):
    """
    Set up all middleware on a FastAPI application.
    
    Args:
        app: FastAPI application instance
        config: Optional MiddlewareConfig instance. If None, uses environment-appropriate config.
    
    Example:
        from fastapi import FastAPI
        from src.common.middleware import setup_middleware
        
        app = FastAPI()
        setup_middleware(app)
    """
    if config is None:
        manager = default_middleware_manager
    else:
        manager = MiddlewareManager(config)
    
    manager.setup_middleware(app)
    return manager


def get_middleware_status():
    """
    Get status of all configured middleware.
    
    Returns:
        Dict containing middleware status and configuration
    """
    return default_middleware_manager.get_middleware_status()


# Export all middleware classes for direct use
__all__ = [
    # Configuration
    'MiddlewareConfig',
    'MiddlewareManager',
    'create_development_config',
    'create_production_config', 
    'create_testing_config',
    'get_middleware_config',
    'default_middleware_manager',
    
    # Logging middleware
    'StructuredLoggingMiddleware',
    'get_request_context',
    'get_correlation_id',
    'get_request_id',
    'request_id_var',
    'user_id_var',
    'tenant_id_var',
    'correlation_id_var',
    
    # Security middleware
    'SecurityHeadersMiddleware',
    'CORSSecurityMiddleware', 
    'RateLimitMiddleware',
    
    # Performance middleware
    'TimingMiddleware',
    'ResponseSizeMiddleware',
    'get_performance_summary',
    
    # Request context middleware
    'RequestContextMiddleware',
    'RequestContext',
    'track_performance',
    'get_request_id',
    'get_processing_time',
    'get_request_metadata',
    'request_id_var',
    'start_time_var',
    'db_queries_var',
    'cache_operations_var',
    'performance_markers_var',
    
    # Convenience functions
    'setup_middleware',
    'get_middleware_status'
]