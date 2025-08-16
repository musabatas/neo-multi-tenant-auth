"""
Middleware configuration management and factory.
"""
from typing import Dict, Any, List, Optional, Type, Callable
from dataclasses import dataclass, field
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.common.config.settings import settings
from src.common.middleware.logging import StructuredLoggingMiddleware
from src.common.middleware.security import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware,
    RateLimitMiddleware
)
from src.common.middleware.timing import TimingMiddleware, ResponseSizeMiddleware


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
        "force_https": settings.is_production,
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
        "track_detailed_timing": not settings.is_production
    })
    
    # Response size middleware
    response_size_enabled: bool = True
    response_size_config: Dict[str, Any] = field(default_factory=lambda: {
        "add_size_header": not settings.is_production,
        "log_large_responses": True,
        "large_response_threshold": 1024 * 1024,  # 1MB
        "exclude_paths": ["/health", "/metrics"]
    })
    
    # Rate limiting middleware
    rate_limit_enabled: bool = field(default=settings.rate_limit_enabled)
    rate_limit_config: Dict[str, Any] = field(default_factory=lambda: {
        "requests_per_minute": settings.rate_limit_requests_per_minute,
        "requests_per_hour": settings.rate_limit_requests_per_hour,
        "exclude_paths": ["/health", "/metrics", "/docs", "/swagger", "/redoc"]
    })
    
    # CORS middleware
    cors_enabled: bool = True
    cors_config: Dict[str, Any] = field(default_factory=lambda: {
        "allow_origins": settings.get_cors_origins(),
        "allow_credentials": settings.cors_allow_credentials,
        "allow_methods": settings.cors_allow_methods,
        "allow_headers": settings.cors_allow_headers,
        "max_age": 3600
    })
    
    # Trusted hosts middleware
    trusted_hosts_enabled: bool = field(default=lambda: settings.allowed_hosts != ["*"])
    trusted_hosts_config: Dict[str, Any] = field(default_factory=lambda: {
        "allowed_hosts": settings.allowed_hosts
    })
    
    # Middleware order (important for proper functioning)
    middleware_order: List[str] = field(default_factory=lambda: [
        "trusted_hosts",  # First - validate host
        "security",       # Security headers
        "cors",           # CORS handling
        "rate_limit",     # Rate limiting
        "logging",        # Request/response logging
        "timing",         # Performance timing
        "response_size"   # Response size tracking
    ])


class MiddlewareManager:
    """Manager for configuring and adding middleware to FastAPI application."""
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        self.config = config or MiddlewareConfig()
        self._middleware_registry: Dict[str, Type[BaseHTTPMiddleware]] = {
            "logging": StructuredLoggingMiddleware,
            "security": SecurityHeadersMiddleware,
            "timing": TimingMiddleware,
            "response_size": ResponseSizeMiddleware,
            "rate_limit": RateLimitMiddleware,
        }
    
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
        
        elif middleware_name == "logging" and self.config.logging_enabled:
            app.add_middleware(
                StructuredLoggingMiddleware,
                **self.config.logging_config
            )
        
        elif middleware_name == "security" and self.config.security_enabled:
            app.add_middleware(
                SecurityHeadersMiddleware,
                **self.config.security_config
            )
        
        elif middleware_name == "timing" and self.config.timing_enabled:
            app.add_middleware(
                TimingMiddleware,
                **self.config.timing_config
            )
        
        elif middleware_name == "response_size" and self.config.response_size_enabled:
            app.add_middleware(
                ResponseSizeMiddleware,
                **self.config.response_size_config
            )
        
        elif middleware_name == "rate_limit" and self.config.rate_limit_enabled:
            app.add_middleware(
                RateLimitMiddleware,
                **self.config.rate_limit_config
            )
    
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
                "order_position": self.config.middleware_order.index(middleware_name)
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


def create_development_config() -> MiddlewareConfig:
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
    
    config.rate_limit_enabled = False  # Disable in development
    
    return config


def create_production_config() -> MiddlewareConfig:
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
    
    config.rate_limit_enabled = True
    
    return config


def create_testing_config() -> MiddlewareConfig:
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
    
    return config


# Factory function
def get_middleware_config() -> MiddlewareConfig:
    """Get appropriate middleware configuration based on environment."""
    if settings.is_production:
        return create_production_config()
    elif settings.is_testing:
        return create_testing_config()
    else:
        return create_development_config()


# Default manager instance
default_middleware_manager = MiddlewareManager(get_middleware_config())