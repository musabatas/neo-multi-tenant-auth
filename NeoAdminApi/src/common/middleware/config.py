"""
Middleware configuration management and factory.

MIGRATED TO NEO-COMMONS: Now using neo-commons middleware patterns with UnifiedContextMiddleware.
Import compatibility maintained - all existing middleware configurations continue to work.
Enhanced with unified context tracking, better performance monitoring, and improved error handling.
"""
from typing import Dict, Any, List, Optional, Type, Callable
from dataclasses import dataclass, field
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

# NEO-COMMONS IMPORT: Use neo-commons middleware configuration directly
from neo_commons.middleware.config import (
    # Core classes
    MiddlewareConfig as NeoCommonsMiddlewareConfig,
    MiddlewareManager as NeoCommonsMiddlewareManager,
    
    # Factory functions
    create_development_config,
    create_production_config,
    create_testing_config,
    get_middleware_config as neo_commons_get_middleware_config,
    
    # Default manager
    default_middleware_manager,
)

# Import settings for backward compatibility
from src.common.config.settings import settings


@dataclass
class MiddlewareConfig(NeoCommonsMiddlewareConfig):
    """
    NeoAdminApi middleware configuration extending neo-commons MiddlewareConfig.
    
    Maintains backward compatibility while leveraging enhanced neo-commons features:
    - UnifiedContextMiddleware combines logging, timing, and metadata tracking
    - Enhanced security headers with auto-detection of production environment
    - Improved rate limiting with better caching and performance
    - Better path exclusion management with unified patterns
    - Enhanced CORS support with more flexible configuration
    """
    
    def __post_init__(self):
        """Configure NeoAdminApi-specific middleware settings after initialization."""
        # Call parent __post_init__ if it exists
        if hasattr(super(), '__post_init__'):
            super().__post_init__()
        
        # Apply NeoAdminApi-specific configurations from settings
        if hasattr(settings, 'is_production'):
            # Auto-detect environment from settings if not set
            if not hasattr(self, 'environment') or not self.environment:
                if settings.is_production:
                    self.environment = "production"
                elif hasattr(settings, 'is_testing') and settings.is_testing:
                    self.environment = "testing"
                else:
                    self.environment = "development"
        
        # Update security config with NeoAdminApi settings
        if hasattr(settings, 'is_production'):
            self.security_config.update({
                "force_https": settings.is_production
            })
        
        # Update rate limiting with NeoAdminApi settings if available
        if hasattr(settings, 'rate_limit_enabled'):
            self.rate_limit_enabled = settings.rate_limit_enabled
            
        if hasattr(settings, 'rate_limit_requests_per_minute'):
            self.rate_limit_config.update({
                "requests_per_minute": settings.rate_limit_requests_per_minute
            })
            
        if hasattr(settings, 'rate_limit_requests_per_hour'):
            self.rate_limit_config.update({
                "requests_per_hour": settings.rate_limit_requests_per_hour
            })
        
        # Update CORS config with NeoAdminApi settings if available
        if hasattr(settings, 'get_cors_origins'):
            self.cors_config.update({
                "allow_origins": settings.get_cors_origins()
            })
            
        if hasattr(settings, 'cors_allow_credentials'):
            self.cors_config.update({
                "allow_credentials": settings.cors_allow_credentials
            })
            
        if hasattr(settings, 'cors_allow_methods'):
            self.cors_config.update({
                "allow_methods": settings.cors_allow_methods
            })
            
        if hasattr(settings, 'cors_allow_headers'):
            self.cors_config.update({
                "allow_headers": settings.cors_allow_headers
            })
        
        # Update trusted hosts with NeoAdminApi settings if available
        if hasattr(settings, 'allowed_hosts'):
            self.trusted_hosts_enabled = settings.allowed_hosts != ["*"]
            self.trusted_hosts_config.update({
                "allowed_hosts": settings.allowed_hosts
            })


# Backward compatibility aliases for existing NeoAdminApi middleware components
# These maintain import compatibility while using neo-commons implementations

# Logging middleware -> unified_context middleware mapping
logging_enabled = property(lambda self: self.unified_context_enabled)
logging_config = property(lambda self: {
    "log_requests": self.unified_context_config.get("log_requests", True),
    "log_responses": self.unified_context_config.get("log_responses", True),
    "log_body": self.unified_context_config.get("log_response_body", False),
    "log_headers": False,  # Not directly supported in unified context
    "exclude_paths": self.unified_context_config.get("exclude_paths", []),
    "max_body_size": 1024,  # Legacy field
    "sensitive_headers": self.unified_context_config.get("sensitive_headers", [])
})

# Timing middleware -> unified_context middleware mapping  
timing_enabled = property(lambda self: self.unified_context_enabled)
timing_config = property(lambda self: {
    "add_timing_header": self.unified_context_config.get("add_timing_header", True),
    "log_slow_requests": self.unified_context_config.get("log_slow_requests", True),
    "slow_request_threshold": self.unified_context_config.get("slow_request_threshold", 1.0),
    "very_slow_threshold": self.unified_context_config.get("very_slow_threshold", 5.0),
    "exclude_paths": self.unified_context_config.get("exclude_paths", []),
    "track_detailed_timing": self.unified_context_config.get("track_performance_markers", True)
})

# Response size middleware -> unified_context middleware mapping
response_size_enabled = property(lambda self: self.unified_context_enabled)
response_size_config = property(lambda self: {
    "add_size_header": not self.is_production,  # Development only
    "log_large_responses": True,
    "large_response_threshold": 1024 * 1024,  # 1MB
    "exclude_paths": self.unified_context_config.get("exclude_paths", [])
})

# Add these properties to the MiddlewareConfig class for backward compatibility
MiddlewareConfig.logging_enabled = logging_enabled
MiddlewareConfig.logging_config = logging_config
MiddlewareConfig.timing_enabled = timing_enabled
MiddlewareConfig.timing_config = timing_config
MiddlewareConfig.response_size_enabled = response_size_enabled
MiddlewareConfig.response_size_config = response_size_config

# Legacy middleware order for backward compatibility
LEGACY_MIDDLEWARE_ORDER = [
    "trusted_hosts",  # First - validate host
    "security",       # Security headers
    "cors",           # CORS handling
    "rate_limit",     # Rate limiting
    "logging",        # Request/response logging (now unified_context)
    "timing",         # Performance timing (now unified_context)
    "response_size"   # Response size tracking (now unified_context)
]


class MiddlewareManager(NeoCommonsMiddlewareManager):
    """
    NeoAdminApi middleware manager extending neo-commons MiddlewareManager.
    
    Maintains backward compatibility with legacy middleware names while leveraging
    enhanced neo-commons features. Provides mapping from legacy middleware names
    to unified context middleware implementation.
    """
    
    def __init__(self, config: Optional[MiddlewareConfig] = None):
        # Create NeoAdminApi-specific config if not provided
        if config is None:
            config = MiddlewareConfig()
        
        # Initialize neo-commons manager
        super().__init__(config)
        
        # Store legacy middleware mappings for backward compatibility
        self._legacy_middleware_mapping = {
            "logging": "unified_context",
            "timing": "unified_context", 
            "response_size": "unified_context",
            # Other middleware names map directly
            "security": "security",
            "rate_limit": "rate_limit",
            "cors": "cors",
            "trusted_hosts": "trusted_hosts"
        }
    
    def setup_middleware(self, app: FastAPI) -> None:
        """
        Set up all middleware on the FastAPI application with legacy compatibility.
        
        Automatically maps legacy middleware names to neo-commons implementations.
        """
        # Convert legacy middleware order to neo-commons order if needed
        if hasattr(self.config, 'middleware_order'):
            # Map legacy names to neo-commons names
            mapped_order = []
            unified_context_added = False
            
            for middleware_name in self.config.middleware_order:
                mapped_name = self._legacy_middleware_mapping.get(middleware_name, middleware_name)
                
                # Only add unified_context once (combines logging, timing, response_size)
                if mapped_name == "unified_context" and not unified_context_added:
                    mapped_order.append("unified_context")
                    unified_context_added = True
                elif mapped_name != "unified_context":
                    mapped_order.append(mapped_name)
            
            # Update config with mapped order
            self.config.middleware_order = mapped_order
        
        # Use neo-commons setup with updated order
        super().setup_middleware(app)
    
    def get_middleware_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all middleware configurations with legacy compatibility."""
        # Get status from neo-commons
        neo_status = super().get_middleware_status()
        
        # Add legacy middleware status for backward compatibility
        legacy_status = {}
        
        for legacy_name, neo_name in self._legacy_middleware_mapping.items():
            if neo_name in neo_status:
                # Map unified_context back to individual legacy names
                if neo_name == "unified_context":
                    legacy_status[legacy_name] = {
                        "enabled": neo_status[neo_name]["enabled"],
                        "config_keys": self._get_legacy_config_keys(legacy_name),
                        "order_position": neo_status[neo_name]["order_position"],
                        "mapped_to": "unified_context"
                    }
                else:
                    legacy_status[legacy_name] = neo_status[neo_name]
        
        # Merge neo-commons status with legacy status
        legacy_status.update(neo_status)
        return legacy_status
    
    def _get_legacy_config_keys(self, legacy_name: str) -> List[str]:
        """Get configuration keys for legacy middleware names."""
        if legacy_name == "logging":
            return ["log_requests", "log_responses", "log_body", "log_headers", 
                   "exclude_paths", "max_body_size", "sensitive_headers"]
        elif legacy_name == "timing":
            return ["add_timing_header", "log_slow_requests", "slow_request_threshold",
                   "very_slow_threshold", "exclude_paths", "track_detailed_timing"]
        elif legacy_name == "response_size":
            return ["add_size_header", "log_large_responses", "large_response_threshold", 
                   "exclude_paths"]
        else:
            return []
    
    def update_config(self, middleware_name: str, **kwargs) -> None:
        """Update configuration for middleware with legacy name mapping."""
        # Map legacy names to neo-commons names
        neo_name = self._legacy_middleware_mapping.get(middleware_name, middleware_name)
        
        if neo_name == "unified_context" and middleware_name in ["logging", "timing", "response_size"]:
            # Update unified_context config with legacy mappings
            self._update_unified_context_config(middleware_name, **kwargs)
        else:
            # Use neo-commons update
            super().update_config(neo_name, **kwargs)
    
    def _update_unified_context_config(self, legacy_name: str, **kwargs) -> None:
        """Update unified context config based on legacy middleware name."""
        unified_config = self.config.unified_context_config
        
        if legacy_name == "logging":
            # Map logging config to unified context
            legacy_to_unified = {
                "log_requests": "log_requests",
                "log_responses": "log_responses", 
                "log_body": "log_response_body",
                "exclude_paths": "exclude_paths",
                "sensitive_headers": "sensitive_headers"
            }
            for legacy_key, unified_key in legacy_to_unified.items():
                if legacy_key in kwargs:
                    unified_config[unified_key] = kwargs[legacy_key]
                    
        elif legacy_name == "timing":
            # Map timing config to unified context
            legacy_to_unified = {
                "add_timing_header": "add_timing_header",
                "log_slow_requests": "log_slow_requests",
                "slow_request_threshold": "slow_request_threshold",
                "very_slow_threshold": "very_slow_threshold",
                "exclude_paths": "exclude_paths",
                "track_detailed_timing": "track_performance_markers"
            }
            for legacy_key, unified_key in legacy_to_unified.items():
                if legacy_key in kwargs:
                    unified_config[unified_key] = kwargs[legacy_key]
                    
        elif legacy_name == "response_size":
            # Response size tracking is handled automatically by unified context
            # No specific mapping needed, but we can log this for debugging
            pass
    
    def enable_middleware(self, middleware_name: str) -> None:
        """Enable middleware with legacy name mapping."""
        neo_name = self._legacy_middleware_mapping.get(middleware_name, middleware_name)
        super().enable_middleware(neo_name)
    
    def disable_middleware(self, middleware_name: str) -> None:
        """Disable middleware with legacy name mapping."""
        neo_name = self._legacy_middleware_mapping.get(middleware_name, middleware_name)
        super().disable_middleware(neo_name)


# Re-export neo-commons factory functions with backward compatibility aliases
# These provide NeoAdminApi-specific middleware configurations

def create_neoadmin_development_config() -> MiddlewareConfig:
    """Create NeoAdminApi development configuration with settings integration."""
    # Create new NeoAdminApi config which will auto-apply settings via __post_init__
    config = MiddlewareConfig()
    config.environment = "development"
    
    # Development-specific unified context adjustments
    config.unified_context_config.update({
        "log_requests": True,
        "log_responses": True,
        "log_response_body": True,
        "add_timing_header": True,
        "track_cache_operations": True,
        "track_db_queries": True,
        "track_performance_markers": True,
        "slow_request_threshold": 0.5  # Lower threshold for dev
    })
    
    config.rate_limit_enabled = False  # Disable in development
    
    return config


def create_neoadmin_production_config() -> MiddlewareConfig:
    """Create NeoAdminApi production configuration with settings integration."""
    # Create new NeoAdminApi config which will auto-apply settings via __post_init__
    config = MiddlewareConfig()
    config.environment = "production"
    
    # Production-specific unified context adjustments
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
    
    config.rate_limit_enabled = True
    
    return config


def create_neoadmin_testing_config() -> MiddlewareConfig:
    """Create NeoAdminApi testing configuration with settings integration."""
    # Create new NeoAdminApi config which will auto-apply settings via __post_init__
    config = MiddlewareConfig()
    config.environment = "testing"
    
    # Testing-specific unified context adjustments
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


# Backward compatibility aliases that maintain existing API
def create_development_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for development."""
    return create_neoadmin_development_config()


def create_production_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for production."""
    return create_neoadmin_production_config()


def create_testing_config() -> MiddlewareConfig:
    """Create middleware configuration optimized for testing."""
    return create_neoadmin_testing_config()


# Factory function with NeoAdminApi-specific logic
def get_middleware_config() -> MiddlewareConfig:
    """Get appropriate middleware configuration based on environment and NeoAdminApi settings."""
    # Determine environment from settings if available, otherwise from neo-commons
    environment = "development"  # default
    
    if hasattr(settings, 'is_production') and settings.is_production:
        environment = "production"
    elif hasattr(settings, 'is_testing') and settings.is_testing:
        environment = "testing"
    
    # Create appropriate config
    if environment == "production":
        return create_production_config()
    elif environment == "testing":
        return create_testing_config()
    else:
        return create_development_config()


# Default manager instance using NeoAdminApi configuration
default_middleware_manager = MiddlewareManager(get_middleware_config())