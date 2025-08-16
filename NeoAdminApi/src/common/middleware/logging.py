"""
Structured logging middleware with correlation IDs and comprehensive context.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
logging functionality while maintaining backward compatibility.
"""
from typing import Optional

# Import from neo-commons
from neo_commons.middleware.logging import (
    StructuredLoggingMiddleware as NeoStructuredLoggingMiddleware,
    LoggingConfig,
    MetadataCollector as NeoMetadataCollector,
    get_request_context,
    get_correlation_id,
    get_request_id,
    request_id_var,
    user_id_var,
    tenant_id_var,
    correlation_id_var
)


class AdminLoggingConfig:
    """Service-specific logging configuration for NeoAdminApi."""
    
    @property
    def log_requests(self) -> bool:
        return True
    
    @property
    def log_responses(self) -> bool:
        return True
    
    @property
    def log_body(self) -> bool:
        return False
    
    @property
    def log_headers(self) -> bool:
        return False
    
    @property
    def exclude_paths(self) -> list:
        return ["/health", "/metrics", "/docs", "/openapi.json", "/swagger", "/redoc"]
    
    @property
    def max_body_size(self) -> int:
        return 1024
    
    @property
    def sensitive_headers(self) -> list:
        return ["authorization", "cookie", "x-api-key", "x-keycloak-token"]


class AdminMetadataCollector:
    """Service-specific metadata collector for NeoAdminApi."""
    
    @staticmethod
    def reset_counters() -> None:
        """Reset performance counters for NeoAdminApi metadata tracking."""
        try:
            from src.common.utils.metadata import MetadataCollector
            MetadataCollector.reset_counters()
        except ImportError:
            pass  # Metadata system not available


class StructuredLoggingMiddleware(NeoStructuredLoggingMiddleware):
    """
    Service wrapper for NeoAdminApi that extends neo-commons StructuredLoggingMiddleware.
    
    Provides NeoAdminApi-specific logging functionality while maintaining
    full compatibility with existing code.
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
        # Create dynamic configuration that can be overridden
        class DynamicAdminLoggingConfig(AdminLoggingConfig):
            def __init__(self, override_exclude_paths=None, override_sensitive_headers=None):
                self._override_exclude_paths = override_exclude_paths
                self._override_sensitive_headers = override_sensitive_headers
            
            @property
            def exclude_paths(self) -> list:
                return self._override_exclude_paths if self._override_exclude_paths is not None else super().exclude_paths
            
            @property
            def sensitive_headers(self) -> list:
                return self._override_sensitive_headers if self._override_sensitive_headers is not None else super().sensitive_headers
        
        # Create configuration with overrides
        config = DynamicAdminLoggingConfig(
            override_exclude_paths=exclude_paths,
            override_sensitive_headers=sensitive_headers
        )
        metadata_collector = AdminMetadataCollector()
        
        # Initialize with service configuration
        super().__init__(app, config=config, metadata_collector=metadata_collector)
        
        # Override individual settings if provided
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_body = log_body
        self.log_headers = log_headers
        self.max_body_size = max_body_size


# Re-export all utility functions for backward compatibility
__all__ = [
    "StructuredLoggingMiddleware",
    "get_request_context",
    "get_correlation_id", 
    "get_request_id",
    "request_id_var",
    "user_id_var",
    "tenant_id_var",
    "correlation_id_var"
]