"""
Middleware configuration management and factory.

Generic middleware configuration system that can be used across all platform services
in the NeoMultiTenant ecosystem.
"""
from typing import Dict, Any, List, Optional, Type, Callable, Protocol, runtime_checkable
from dataclasses import dataclass, field
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware


@runtime_checkable
class MiddlewareSettingsProvider(Protocol):
    """Protocol for providing service-specific middleware settings."""
    
    @property
    def is_production(self) -> bool:
        """Whether the service is running in production mode."""
        ...
    
    @property
    def is_testing(self) -> bool:
        """Whether the service is running in testing mode."""
        ...
    
    @property
    def is_development(self) -> bool:
        """Whether the service is running in development mode."""
        ...
    
    @property
    def rate_limit_enabled(self) -> bool:
        """Whether rate limiting is enabled."""
        ...
    
    @property
    def rate_limit_requests_per_minute(self) -> int:
        """Rate limit requests per minute."""
        ...
    
    @property
    def rate_limit_requests_per_hour(self) -> int:
        """Rate limit requests per hour."""
        ...
    
    @property
    def cors_allow_credentials(self) -> bool:
        """Whether CORS allows credentials."""
        ...
    
    @property
    def cors_allow_methods(self) -> List[str]:
        """Allowed CORS methods."""
        ...
    
    @property
    def cors_allow_headers(self) -> List[str]:
        """Allowed CORS headers."""
        ...
    
    @property
    def allowed_hosts(self) -> List[str]:
        """Allowed hosts for trusted host middleware."""
        ...
    
    def get_cors_origins(self) -> List[str]:
        """Get allowed CORS origins."""
        ...


@dataclass
class MiddlewareConfig:
    """Configuration for middleware setup."""
    
    # Logging middleware
    logging_enabled: bool = True
    logging_config: Dict[str, Any] = field(default_factory=lambda: {
        "log_requests": True,
        "log_responses": True,
        "log_body": False,
        "log_headers": False,
        "exclude_paths": ["/health", "/metrics", "/docs", "/openapi.json", "/swagger"],
        "max_body_size": 1024,
        "sensitive_headers": ["authorization", "cookie", "x-api-key", "x-keycloak-token"]
    })
    
    # Security middleware
    security_enabled: bool = True
    security_config: Dict[str, Any] = field(default_factory=lambda: {
        "force_https": False,  # Will be set by environment
        "hsts_max_age": 31536000,
        "hsts_include_subdomains": True,
        "content_security_policy": None,  # Will use default
        "frame_options": "DENY",
        "exclude_paths": ["/docs", "/swagger", "/redoc", "/openapi.json"]
    })
    
    # Timing middleware
    timing_enabled: bool = True
    timing_config: Dict[str, Any] = field(default_factory=lambda: {
        "add_timing_header": True,
        "log_slow_requests": True,
        "slow_request_threshold": 1.0,
        "very_slow_threshold": 5.0,
        "exclude_paths": ["/health", "/metrics", "/docs"],
        "track_detailed_timing": True  # Will be set by environment
    })
    
    # Response size middleware
    response_size_enabled: bool = True
    response_size_config: Dict[str, Any] = field(default_factory=lambda: {
        "add_size_header": True,  # Will be set by environment
        "log_large_responses": True,
        "large_response_threshold": 1024 * 1024,  # 1MB
        "exclude_paths": ["/health", "/metrics"]
    })
    
    # Rate limiting middleware
    rate_limit_enabled: bool = False  # Will be set by environment
    rate_limit_config: Dict[str, Any] = field(default_factory=lambda: {
        "requests_per_minute": 60,  # Default values
        "requests_per_hour": 1000,
        "exclude_paths": ["/health", "/metrics", "/docs", "/swagger", "/redoc"]
    })
    
    # CORS middleware
    cors_enabled: bool = True
    cors_config: Dict[str, Any] = field(default_factory=lambda: {
        "allow_origins": ["*"],  # Will be set by environment
        "allow_credentials": False,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "max_age": 3600
    })
    
    # Trusted hosts middleware
    trusted_hosts_enabled: bool = False  # Will be set by environment
    trusted_hosts_config: Dict[str, Any] = field(default_factory=lambda: {
        "allowed_hosts": ["*"]
    })
    
    # Request context middleware
    request_context_enabled: bool = True
    request_context_config: Dict[str, Any] = field(default_factory=lambda: {
        "include_processing_time_header": True,
        "include_request_id_header": True,
        "short_request_id": True,
        "enable_performance_tracking": True
    })
    
    # Middleware order (important for proper functioning)
    middleware_order: List[str] = field(default_factory=lambda: [
        "trusted_hosts",      # First - validate host
        "security",           # Security headers
        "cors",               # CORS handling
        "rate_limit",         # Rate limiting
        "request_context",    # Request context tracking
        "logging",            # Request/response logging
        "timing",             # Performance timing
        "response_size"       # Response size tracking
    ])


class MiddlewareManager:
    """Manager for configuring and adding middleware to FastAPI application."""
    
    def __init__(
        self,
        config: Optional[MiddlewareConfig] = None,
        settings_provider: Optional[MiddlewareSettingsProvider] = None
    ):
        self.config = config or MiddlewareConfig()
        self.settings_provider = settings_provider
        
        # Import middleware classes dynamically to avoid circular imports
        self._middleware_registry: Dict[str, Callable] = {}
        
        # Initialize with environment-specific settings if provider is available
        if self.settings_provider:
            self._apply_environment_settings()
    
    def _apply_environment_settings(self):
        """Apply environment-specific settings from the provider."""
        if not self.settings_provider:
            return
        
        # Security settings
        self.config.security_config["force_https"] = self.settings_provider.is_production
        
        # Timing settings
        self.config.timing_config["track_detailed_timing"] = not self.settings_provider.is_production
        
        # Response size settings
        self.config.response_size_config["add_size_header"] = not self.settings_provider.is_production
        
        # Rate limiting settings
        self.config.rate_limit_enabled = self.settings_provider.rate_limit_enabled
        self.config.rate_limit_config.update({
            "requests_per_minute": self.settings_provider.rate_limit_requests_per_minute,
            "requests_per_hour": self.settings_provider.rate_limit_requests_per_hour
        })
        
        # CORS settings
        self.config.cors_config.update({
            "allow_origins": self.settings_provider.get_cors_origins(),
            "allow_credentials": self.settings_provider.cors_allow_credentials,
            "allow_methods": self.settings_provider.cors_allow_methods,
            "allow_headers": self.settings_provider.cors_allow_headers
        })
        
        # Trusted hosts settings
        self.config.trusted_hosts_enabled = self.settings_provider.allowed_hosts != ["*"]
        self.config.trusted_hosts_config["allowed_hosts"] = self.settings_provider.allowed_hosts
    
    def register_middleware(self, name: str, middleware_class: Type[BaseHTTPMiddleware]):
        """Register a middleware class for use by the manager."""
        self._middleware_registry[name] = middleware_class
    
    def setup_middleware(self, app: FastAPI) -> None:
        """
        Set up all middleware on the FastAPI application.
        
        Note: Middleware is added in reverse order of execution.
        The last middleware added is the first to process requests.
        """
        # Add middleware in reverse order since FastAPI/Starlette processes them in LIFO order
        for middleware_name in reversed(self.config.middleware_order):
            self._add_middleware(app, middleware_name)
    
    def _add_middleware(self, app: FastAPI, middleware_name: str) -> None:
        """Add a specific middleware to the application."""
        
        if middleware_name == "trusted_hosts" and self.config.trusted_hosts_enabled:
            app.add_middleware(
                TrustedHostMiddleware,
                **self.config.trusted_hosts_config
            )
        
        elif middleware_name == "cors" and self.config.cors_enabled:
            # Use FastAPI's built-in CORS middleware for simplicity
            app.add_middleware(
                CORSMiddleware,
                **self.config.cors_config
            )
        
        elif middleware_name in self._middleware_registry:
            # Use registered middleware classes
            enabled_attr = f"{middleware_name}_enabled"
            config_attr = f"{middleware_name}_config"
            
            if getattr(self.config, enabled_attr, False):
                middleware_class = self._middleware_registry[middleware_name]
                middleware_config = getattr(self.config, config_attr, {})
                app.add_middleware(middleware_class, **middleware_config)
    
    def get_middleware_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all middleware configurations."""
        status = {}
        
        for middleware_name in self.config.middleware_order:
            enabled_attr = f"{middleware_name}_enabled"
            config_attr = f"{middleware_name}_config"
            
            # Handle special cases
            if middleware_name == "trusted_hosts":
                enabled = self.config.trusted_hosts_enabled
                config = self.config.trusted_hosts_config
            elif middleware_name == "cors":
                enabled = self.config.cors_enabled
                config = self.config.cors_config
            else:
                enabled = getattr(self.config, enabled_attr, False)
                config = getattr(self.config, config_attr, {})
            
            status[middleware_name] = {
                "enabled": enabled,
                "config_keys": list(config.keys()) if isinstance(config, dict) else [],
                "order_position": self.config.middleware_order.index(middleware_name),
                "registered": middleware_name in self._middleware_registry or middleware_name in ["trusted_hosts", "cors"]
            }
        
        return status
    
    def update_config(self, middleware_name: str, **kwargs) -> None:
        """Update configuration for a specific middleware."""
        config_attr = f"{middleware_name}_config"
        
        if hasattr(self.config, config_attr):
            current_config = getattr(self.config, config_attr)
            current_config.update(kwargs)
        else:
            raise ValueError(f"Unknown middleware: {middleware_name}")
    
    def enable_middleware(self, middleware_name: str) -> None:
        """Enable a specific middleware."""
        enabled_attr = f"{middleware_name}_enabled"
        
        if hasattr(self.config, enabled_attr):
            setattr(self.config, enabled_attr, True)
        else:
            raise ValueError(f"Unknown middleware: {middleware_name}")
    
    def disable_middleware(self, middleware_name: str) -> None:
        """Disable a specific middleware."""
        enabled_attr = f"{middleware_name}_enabled"
        
        if hasattr(self.config, enabled_attr):
            setattr(self.config, enabled_attr, False)
        else:
            raise ValueError(f"Unknown middleware: {middleware_name}")


def create_development_config(settings_provider: Optional[MiddlewareSettingsProvider] = None) -> MiddlewareConfig:
    """Create middleware configuration optimized for development."""
    config = MiddlewareConfig()
    
    # Development-specific adjustments
    config.logging_config.update({
        "log_requests": True,
        "log_responses": True,
        "log_body": True,
        "log_headers": True,
        "max_body_size": 2048
    })
    
    config.security_config.update({
        "force_https": False,
        "exclude_paths": ["/docs", "/swagger", "/redoc", "/openapi.json", "/scalar"]
    })
    
    config.timing_config.update({
        "add_timing_header": True,
        "track_detailed_timing": True,
        "slow_request_threshold": 0.5  # Lower threshold for dev
    })
    
    config.response_size_config.update({
        "add_size_header": True
    })
    
    config.request_context_config.update({
        "enable_performance_tracking": True
    })
    
    config.rate_limit_enabled = False  # Disable in development
    
    return config


def create_production_config(settings_provider: Optional[MiddlewareSettingsProvider] = None) -> MiddlewareConfig:
    """Create middleware configuration optimized for production."""
    config = MiddlewareConfig()
    
    # Production-specific adjustments
    config.logging_config.update({
        "log_requests": True,
        "log_responses": False,  # Reduce logging volume
        "log_body": False,
        "log_headers": False,
        "max_body_size": 512
    })
    
    config.security_config.update({
        "force_https": True,
        "hsts_max_age": 31536000,  # 1 year
        "hsts_include_subdomains": True,
        "hsts_preload": True
    })
    
    config.timing_config.update({
        "add_timing_header": False,  # Don't expose timing in production
        "track_detailed_timing": False,
        "slow_request_threshold": 2.0  # Higher threshold for production
    })
    
    config.response_size_config.update({
        "add_size_header": False  # Don't expose size in production
    })
    
    config.request_context_config.update({
        "enable_performance_tracking": False
    })
    
    # Rate limiting enabled in production if provider supports it
    if settings_provider and hasattr(settings_provider, 'rate_limit_enabled'):
        config.rate_limit_enabled = settings_provider.rate_limit_enabled
    else:
        config.rate_limit_enabled = True
    
    return config


def create_testing_config(settings_provider: Optional[MiddlewareSettingsProvider] = None) -> MiddlewareConfig:
    """Create middleware configuration optimized for testing."""
    config = MiddlewareConfig()
    
    # Testing-specific adjustments
    config.logging_config.update({
        "log_requests": False,
        "log_responses": False,
        "log_body": False,
        "log_headers": False
    })
    
    config.security_enabled = False  # Disable security headers in tests
    config.timing_enabled = False   # Disable timing in tests
    config.response_size_enabled = False  # Disable size tracking in tests
    config.rate_limit_enabled = False  # Disable rate limiting in tests
    config.request_context_enabled = False  # Disable context tracking in tests
    
    return config


def create_middleware_manager(
    settings_provider: Optional[MiddlewareSettingsProvider] = None,
    config: Optional[MiddlewareConfig] = None
) -> MiddlewareManager:
    """
    Create a middleware manager with environment-appropriate configuration.
    
    Args:
        settings_provider: Provider for service-specific settings
        config: Optional custom configuration (overrides environment-based config)
    
    Returns:
        Configured MiddlewareManager instance
    """
    if config is None and settings_provider:
        # Determine config based on environment
        if settings_provider.is_production:
            config = create_production_config(settings_provider)
        elif settings_provider.is_testing:
            config = create_testing_config(settings_provider)
        else:
            config = create_development_config(settings_provider)
    elif config is None:
        # Default development config
        config = create_development_config()
    
    return MiddlewareManager(config=config, settings_provider=settings_provider)