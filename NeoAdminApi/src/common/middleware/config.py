"""
Middleware configuration management and factory.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
middleware configuration while maintaining backward compatibility.
"""
from typing import Dict, Any, List

# Import from neo-commons
from neo_commons.middleware.config import (
    MiddlewareConfig as NeoMiddlewareConfig,
    MiddlewareManager as NeoMiddlewareManager,
    MiddlewareSettingsProvider,
    create_development_config as neo_create_development_config,
    create_production_config as neo_create_production_config,
    create_testing_config as neo_create_testing_config,
    create_middleware_manager as neo_create_middleware_manager
)

# Import service-specific components
from src.common.config.settings import settings
from src.common.middleware.logging import StructuredLoggingMiddleware
from src.common.middleware.security import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware,
    RateLimitMiddleware
)
from src.common.middleware.timing import TimingMiddleware, ResponseSizeMiddleware
from src.common.middleware.request_context import RequestContextMiddleware


class AdminSettingsProvider:
    """Service-specific settings provider for NeoAdminApi middleware configuration."""
    
    @property
    def is_production(self) -> bool:
        return settings.is_production
    
    @property
    def is_testing(self) -> bool:
        return settings.is_testing
    
    @property
    def is_development(self) -> bool:
        return settings.is_development
    
    @property
    def rate_limit_enabled(self) -> bool:
        return settings.rate_limit_enabled
    
    @property
    def rate_limit_requests_per_minute(self) -> int:
        return settings.rate_limit_requests_per_minute
    
    @property
    def rate_limit_requests_per_hour(self) -> int:
        return settings.rate_limit_requests_per_hour
    
    @property
    def cors_allow_credentials(self) -> bool:
        return settings.cors_allow_credentials
    
    @property
    def cors_allow_methods(self) -> List[str]:
        return settings.cors_allow_methods
    
    @property
    def cors_allow_headers(self) -> List[str]:
        return settings.cors_allow_headers
    
    @property
    def allowed_hosts(self) -> List[str]:
        return settings.allowed_hosts
    
    def get_cors_origins(self) -> List[str]:
        return settings.get_cors_origins()


# Create service-specific settings provider
admin_settings_provider = AdminSettingsProvider()


class MiddlewareConfig(NeoMiddlewareConfig):
    """
    Service wrapper for NeoAdminApi that extends neo-commons MiddlewareConfig.
    
    Provides NeoAdminApi-specific middleware configuration while maintaining
    full compatibility with existing code.
    """
    pass


class MiddlewareManager(NeoMiddlewareManager):
    """
    Service wrapper for NeoAdminApi that extends neo-commons MiddlewareManager.
    
    Provides NeoAdminApi-specific middleware functionality while maintaining
    full compatibility with existing code.
    """
    
    def __init__(self, config=None):
        # Create middleware manager with service-specific settings
        super().__init__(
            config=config,
            settings_provider=admin_settings_provider
        )
        
        # Register service-specific middleware classes
        self.register_middleware("logging", StructuredLoggingMiddleware)
        self.register_middleware("security", SecurityHeadersMiddleware)
        self.register_middleware("timing", TimingMiddleware)
        self.register_middleware("response_size", ResponseSizeMiddleware)
        self.register_middleware("rate_limit", RateLimitMiddleware)
        self.register_middleware("request_context", RequestContextMiddleware)


# Factory functions with service-specific behavior
def create_development_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for development."""
    return neo_create_development_config(admin_settings_provider)


def create_production_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for production."""
    return neo_create_production_config(admin_settings_provider)


def create_testing_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for testing."""
    return neo_create_testing_config(admin_settings_provider)


def get_middleware_config() -> MiddlewareConfig:
    """Get appropriate middleware configuration based on environment."""
    if settings.is_production:
        return create_production_config()
    elif settings.is_testing:
        return create_testing_config()
    else:
        return create_development_config()


def create_middleware_manager(config=None) -> MiddlewareManager:
    """Create a middleware manager with environment-appropriate configuration."""
    if config is None:
        config = get_middleware_config()
    return MiddlewareManager(config)


# Default manager instance for backward compatibility
default_middleware_manager = create_middleware_manager()


# Re-export for backward compatibility
__all__ = [
    "MiddlewareConfig",
    "MiddlewareManager", 
    "AdminSettingsProvider",
    "create_development_config",
    "create_production_config",
    "create_testing_config",
    "get_middleware_config",
    "create_middleware_manager",
    "default_middleware_manager",
    "admin_settings_provider"
]