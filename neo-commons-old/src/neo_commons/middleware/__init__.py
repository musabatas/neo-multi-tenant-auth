"""
Middleware utilities for the NeoMultiTenant platform.

This module provides generic middleware components and patterns
that can be used across all platform services.
"""

from .logging import (
    StructuredLoggingMiddleware,
    LoggingConfig,
    MetadataCollector,
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
    RateLimitMiddleware,
    SecurityConfig
)

from .timing import (
    TimingMiddleware,
    ResponseSizeMiddleware,
    TimingConfig,
    get_performance_summary
)

from .request_context import (
    RequestContextMiddleware,
    RequestContext,
    RequestContextConfig,
    track_performance,
    get_request_id as get_context_request_id,
    get_processing_time,
    get_request_metadata
)

from .config import (
    MiddlewareConfig,
    MiddlewareManager,
    MiddlewareSettingsProvider,
    create_development_config,
    create_production_config,
    create_testing_config,
    create_middleware_manager
)

__all__ = [
    "StructuredLoggingMiddleware",
    "LoggingConfig",
    "MetadataCollector",
    "get_request_context",
    "get_correlation_id",
    "get_request_id",
    "request_id_var",
    "user_id_var", 
    "tenant_id_var",
    "correlation_id_var",
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware",
    "RateLimitMiddleware",
    "SecurityConfig",
    "TimingMiddleware",
    "ResponseSizeMiddleware",
    "TimingConfig",
    "get_performance_summary",
    "RequestContextMiddleware",
    "RequestContext",
    "RequestContextConfig",
    "track_performance",
    "get_context_request_id",
    "get_processing_time",
    "get_request_metadata",
    "MiddlewareConfig",
    "MiddlewareManager",
    "MiddlewareSettingsProvider",
    "create_development_config",
    "create_production_config",
    "create_testing_config",
    "create_middleware_manager"
]