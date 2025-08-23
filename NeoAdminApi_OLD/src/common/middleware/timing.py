"""
Timing and performance middleware for request processing metrics.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
timing functionality while maintaining backward compatibility.
"""
from typing import List

# Import from neo-commons
from neo_commons.middleware.timing import (
    TimingMiddleware as NeoTimingMiddleware,
    ResponseSizeMiddleware,
    TimingConfig,
    get_performance_summary
)

# Import service-specific settings
from src.common.config.settings import settings


class AdminTimingConfig:
    """Service-specific timing configuration for NeoAdminApi."""
    
    @property
    def add_timing_header(self) -> bool:
        return True
    
    @property
    def log_slow_requests(self) -> bool:
        return True
    
    @property
    def slow_request_threshold(self) -> float:
        return 1.0  # seconds
    
    @property
    def very_slow_threshold(self) -> float:
        return 5.0  # seconds
    
    @property
    def exclude_paths(self) -> List[str]:
        return ["/health", "/metrics", "/docs", "/openapi.json", "/swagger", "/redoc"]
    
    @property
    def track_detailed_timing(self) -> bool:
        return settings.is_development


class TimingMiddleware(NeoTimingMiddleware):
    """
    Service wrapper for NeoAdminApi that extends neo-commons TimingMiddleware.
    
    Provides NeoAdminApi-specific timing functionality while maintaining
    full compatibility with existing code.
    """
    
    def __init__(
        self,
        app,
        *,
        add_timing_header: bool = True,
        log_slow_requests: bool = True,
        slow_request_threshold: float = 1.0,  # seconds
        very_slow_threshold: float = 5.0,  # seconds
        exclude_paths: List[str] = None,
        track_detailed_timing: bool = None
    ):
        # Create service-specific configuration
        timing_config = AdminTimingConfig()
        
        # Override track_detailed_timing based on environment if not specified
        if track_detailed_timing is None:
            track_detailed_timing = settings.is_development
        
        # NeoAdminApi-specific defaults
        if exclude_paths is None:
            exclude_paths = timing_config.exclude_paths
        
        # Initialize with service configuration
        super().__init__(
            app,
            config=timing_config,
            add_timing_header=add_timing_header,
            log_slow_requests=log_slow_requests,
            slow_request_threshold=slow_request_threshold,
            very_slow_threshold=very_slow_threshold,
            exclude_paths=exclude_paths,
            track_detailed_timing=track_detailed_timing
        )


# Re-export other classes for backward compatibility
__all__ = [
    "TimingMiddleware",
    "ResponseSizeMiddleware",
    "get_performance_summary"
]