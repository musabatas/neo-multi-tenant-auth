"""
Request context middleware for metadata collection.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
request context functionality while maintaining backward compatibility.
"""

# Import from neo-commons
from neo_commons.middleware.request_context import (
    RequestContextMiddleware as NeoRequestContextMiddleware,
    RequestContext,
    RequestContextConfig,
    track_performance,
    get_request_id,
    get_processing_time,
    get_request_metadata,
    # Context variables for backward compatibility
    request_id_var,
    start_time_var,
    db_queries_var,
    cache_operations_var,
    performance_markers_var
)

# Import service-specific settings
from src.common.config.settings import settings


class AdminRequestContextConfig:
    """Service-specific request context configuration for NeoAdminApi."""
    
    @property
    def include_processing_time_header(self) -> bool:
        return True
    
    @property
    def include_request_id_header(self) -> bool:
        return True
    
    @property
    def short_request_id(self) -> bool:
        return True  # Short IDs for better performance
    
    @property
    def enable_performance_tracking(self) -> bool:
        return settings.is_development  # Enable detailed tracking in development


class RequestContextMiddleware(NeoRequestContextMiddleware):
    """
    Service wrapper for NeoAdminApi that extends neo-commons RequestContextMiddleware.
    
    Provides NeoAdminApi-specific request context functionality while maintaining
    full compatibility with existing code.
    """
    
    def __init__(
        self,
        app,
        *,
        include_processing_time_header: bool = True,
        include_request_id_header: bool = True,
        short_request_id: bool = True,
        enable_performance_tracking: bool = None
    ):
        # Create service-specific configuration
        context_config = AdminRequestContextConfig()
        
        # Override enable_performance_tracking based on environment if not specified
        if enable_performance_tracking is None:
            enable_performance_tracking = settings.is_development
        
        # Initialize with service configuration
        super().__init__(
            app,
            config=context_config,
            include_processing_time_header=include_processing_time_header,
            include_request_id_header=include_request_id_header,
            short_request_id=short_request_id,
            enable_performance_tracking=enable_performance_tracking
        )


# Re-export other classes and functions for backward compatibility
__all__ = [
    "RequestContextMiddleware",
    "RequestContext",
    "track_performance",
    "get_request_id",
    "get_processing_time",
    "get_request_metadata",
    # Context variables
    "request_id_var",
    "start_time_var",
    "db_queries_var",
    "cache_operations_var",
    "performance_markers_var"
]