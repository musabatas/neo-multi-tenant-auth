"""
Middleware configuration management and factory.
"""
import os
from typing import Dict, Any, List, Optional, Type, Callable
from dataclasses import dataclass, field
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from neo_commons.middleware.unified_context import UnifiedContextMiddleware
from neo_commons.middleware.security import (
    SecurityHeadersMiddleware,
    CORSSecurityMiddleware,
    RateLimitMiddleware
)


@dataclass
class MiddlewareConfig:
    """Configuration for middleware setup."""
    
    # Environment detection
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development").lower())
    
    # Unified context middleware (combines logging, timing, and metadata)
    unified_context_enabled: bool = True
    unified_context_config: Dict[str, Any] = field(default_factory=lambda: {
        # Request context options
        "generate_request_id": True,
        "generate_correlation_id": True,
        "extract_user_context": True,
        
        # Logging options
        "log_requests": True,
        "log_responses": True,
        "log_response_body": False,
        "sensitive_headers": ["authorization", "cookie", "x-api-key", "x-keycloak-token"],
        
        # Timing options
        "add_timing_header": True,
        "log_slow_requests": True,
        "slow_request_threshold": 1.0,
        "very_slow_threshold": 5.0,
        
        # Metadata tracking options
        "track_cache_operations": True,
        "track_db_queries": True,
        "track_performance_markers": True,
        
        # Path filtering
        "exclude_paths": ["/health", "/metrics", "/docs", "/openapi.json", "/swagger"],
        "include_health_endpoints": False
    })
    
    # Security middleware
    security_enabled: bool = True
    security_config: Dict[str, Any] = field(default_factory=lambda: {
        "force_https": None,  # Will auto-detect production
        "hsts_max_age": 31536000,
        "hsts_include_subdomains": True,
        "content_security_policy": None,  # Will use default
        "frame_options": "DENY",
        "exclude_paths": ["/docs", "/swagger", "/redoc", "/openapi.json"]
    })
    
    # Rate limiting middleware
    rate_limit_enabled: bool = field(default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true")
    rate_limit_config: Dict[str, Any] = field(default_factory=lambda: {
        "requests_per_minute": int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60")),
        "requests_per_hour": int(os.getenv("RATE_LIMIT_REQUESTS_PER_HOUR", "1000")),
        "exclude_paths": ["/health", "/metrics", "/docs", "/swagger", "/redoc"]
    })
    
    # CORS middleware
    cors_enabled: bool = True
    cors_config: Dict[str, Any] = field(default_factory=lambda: {
        "allow_origins": _get_cors_origins(),
        "allow_credentials": os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true",
        "allow_methods": os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(","),
        "allow_headers": os.getenv("CORS_ALLOW_HEADERS", "*").split(",") if os.getenv("CORS_ALLOW_HEADERS") != "*" else ["*"],
        "max_age": 3600
    })
    
    # Trusted hosts middleware
    trusted_hosts_enabled: bool = field(default_factory=lambda: _get_allowed_hosts() != ["*"])
    trusted_hosts_config: Dict[str, Any] = field(default_factory=lambda: {
        "allowed_hosts": _get_allowed_hosts()
    })
    
    # Middleware order (important for proper functioning)
    middleware_order: List[str] = field(default_factory=lambda: [
        "trusted_hosts",      # First - validate host
        "security",           # Security headers
        "cors",               # CORS handling
        "rate_limit",         # Rate limiting
        "unified_context"     # Unified context, logging, timing, and metadata
    ])
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment in ("testing", "test")


def _get_cors_origins() -> List[str]:
    """Get CORS origins from environment."""
    origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003")
    if origins_str == "*":
        return ["*"]
    return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


def _get_allowed_hosts() -> List[str]:
    """Get allowed hosts from environment."""
    hosts_str = os.getenv("ALLOWED_HOSTS", "*")
    if hosts_str == "*":
        return ["*"]
    return [host.strip() for host in hosts_str.split(",") if host.strip()]


class MiddlewareManager:
    """Manager for configuring and adding middleware to FastAPI application."""
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        self.config = config or MiddlewareConfig()
        self._middleware_registry: Dict[str, Type[BaseHTTPMiddleware]] = {
            "unified_context": UnifiedContextMiddleware,
            "security": SecurityHeadersMiddleware,
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
        
        elif middleware_name == "unified_context" and self.config.unified_context_enabled:
            app.add_middleware(
                UnifiedContextMiddleware,
                **self.config.unified_context_config
            )
        
        elif middleware_name == "security" and self.config.security_enabled:
            app.add_middleware(
                SecurityHeadersMiddleware,
                **self.config.security_config
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
            # Handle special cases
            if middleware_name == "trusted_hosts":
                enabled = self.config.trusted_hosts_enabled
                config = self.config.trusted_hosts_config
            elif middleware_name == "cors":
                enabled = self.config.cors_enabled
                config = self.config.cors_config
            elif middleware_name == "unified_context":
                enabled = self.config.unified_context_enabled
                config = self.config.unified_context_config
            elif middleware_name == "security":
                enabled = self.config.security_enabled
                config = self.config.security_config
            elif middleware_name == "rate_limit":
                enabled = self.config.rate_limit_enabled
                config = self.config.rate_limit_config
            else:
                # Fallback for any other middleware
                enabled_attr = f"{middleware_name}_enabled"
                config_attr = f"{middleware_name}_config"
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
        # Map middleware names to actual config attributes
        config_mapping = {
            "unified_context": "unified_context_config",
            "security": "security_config", 
            "rate_limit": "rate_limit_config",
            "cors": "cors_config",
            "trusted_hosts": "trusted_hosts_config"
        }
        
        config_attr = config_mapping.get(middleware_name, f"{middleware_name}_config")
        
        if hasattr(self.config, config_attr):
            current_config = getattr(self.config, config_attr)
            current_config.update(kwargs)
        else:
            raise ValueError(f"Unknown middleware: {middleware_name}")
    
    def enable_middleware(self, middleware_name: str) -> None:
        """Enable a specific middleware."""
        # Map middleware names to actual enabled attributes
        enabled_mapping = {
            "unified_context": "unified_context_enabled",
            "security": "security_enabled", 
            "rate_limit": "rate_limit_enabled",
            "cors": "cors_enabled",
            "trusted_hosts": "trusted_hosts_enabled"
        }
        
        enabled_attr = enabled_mapping.get(middleware_name, f"{middleware_name}_enabled")
        
        if hasattr(self.config, enabled_attr):
            setattr(self.config, enabled_attr, True)
        else:
            raise ValueError(f"Unknown middleware: {middleware_name}")
    
    def disable_middleware(self, middleware_name: str) -> None:
        """Disable a specific middleware."""
        # Map middleware names to actual enabled attributes
        enabled_mapping = {
            "unified_context": "unified_context_enabled",
            "security": "security_enabled", 
            "rate_limit": "rate_limit_enabled",
            "cors": "cors_enabled",
            "trusted_hosts": "trusted_hosts_enabled"
        }
        
        enabled_attr = enabled_mapping.get(middleware_name, f"{middleware_name}_enabled")
        
        if hasattr(self.config, enabled_attr):
            setattr(self.config, enabled_attr, False)
        else:
            raise ValueError(f"Unknown middleware: {middleware_name}")


def create_development_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for development."""
    config = MiddlewareConfig()
    
    # Development-specific adjustments
    config.unified_context_config.update({
        "log_requests": True,
        "log_responses": True,
        "log_response_body": True,
        "add_timing_header": True,
        "track_cache_operations": True,
        "track_db_queries": True,
        "track_performance_markers": True
    })
    
    config.security_config.update({
        "force_https": False,
        "exclude_paths": ["/docs", "/swagger", "/redoc", "/openapi.json", "/scalar"]
    })
    
    config.rate_limit_enabled = False  # Disable in development
    
    return config


def create_production_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for production."""
    config = MiddlewareConfig()
    
    # Production-specific adjustments
    config.unified_context_config.update({
        "log_requests": True,
        "log_responses": False,  # Reduce logging volume
        "log_response_body": False,
        "add_timing_header": False,  # Don't expose timing in production
        "slow_request_threshold": 2.0,  # Higher threshold for production
        "track_cache_operations": True,
        "track_db_queries": True,
        "track_performance_markers": False  # Reduce overhead in production
    })
    
    config.security_config.update({
        "force_https": True,
        "hsts_max_age": 31536000,  # 1 year
        "hsts_include_subdomains": True,
        "hsts_preload": True
    })
    
    config.rate_limit_enabled = True
    
    return config


def create_testing_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for testing."""
    config = MiddlewareConfig()
    
    # Testing-specific adjustments
    config.unified_context_config.update({
        "log_requests": False,
        "log_responses": False,
        "log_response_body": False,
        "add_timing_header": False,
        "track_cache_operations": False,
        "track_db_queries": False,
        "track_performance_markers": False
    })
    
    config.security_enabled = False  # Disable security headers in tests
    config.rate_limit_enabled = False  # Disable rate limiting in tests
    
    return config


# Factory function
def get_middleware_config() -> MiddlewareConfig:
    """Get appropriate middleware configuration based on environment."""
    environment = os.getenv("ENVIRONMENT", "development").lower()
    
    if environment == "production":
        return create_production_config()
    elif environment in ("testing", "test"):
        return create_testing_config()
    else:
        return create_development_config()


# Default manager instance
default_middleware_manager = MiddlewareManager(get_middleware_config())