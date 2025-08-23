"""
Core authentication module.

Provides fundamental authentication types, enums, exceptions, protocols,
and configuration classes used throughout the auth system.
"""

# Enums
from .enums import (
    ValidationStrategy,
    PermissionScope,
    AuthenticationStatus,
    PermissionAction,
    CacheStrategy,
    SessionType,
    TokenType,
)

# Exceptions
from .exceptions import (
    # Base exception
    AuthError,
    
    # Authentication errors
    AuthenticationError,
    AuthorizationError,
    TokenValidationError,
    PermissionDeniedError,
    
    # Session errors
    SessionError,
    SessionExpiredError,
    SessionNotFoundError,
    
    # Rate limiting
    RateLimitError,
    
    # Resource not found
    UserNotFoundError,
    PermissionNotFoundError,
    RealmNotFoundError,
    
    # System errors
    ConfigurationError,
    ExternalServiceError,
    CacheError,
    ValidationError,
    ConflictError,
)

# Protocols
from .protocols import (
    AuthConfigProtocol,
    CacheKeyProviderProtocol,
    HealthCheckProtocol,
    MetricsProtocol,
    AuditLogProtocol,
    RateLimiterProtocol,
)

# Configuration
from .config import (
    AuthConfig,
    AuthConfigType,
)

__all__ = [
    # Enums
    "ValidationStrategy",
    "PermissionScope",
    "AuthenticationStatus", 
    "PermissionAction",
    "CacheStrategy",
    "SessionType",
    "TokenType",
    
    # Exceptions
    "AuthError",
    "AuthenticationError",
    "AuthorizationError",
    "TokenValidationError",
    "PermissionDeniedError",
    "SessionError",
    "SessionExpiredError",
    "SessionNotFoundError",
    "RateLimitError",
    "UserNotFoundError",
    "PermissionNotFoundError",
    "RealmNotFoundError",
    "ConfigurationError",
    "ExternalServiceError",
    "CacheError",
    "ValidationError",
    "ConflictError",
    
    # Protocols
    "AuthConfigProtocol",
    "CacheKeyProviderProtocol",
    "HealthCheckProtocol",
    "MetricsProtocol",
    "AuditLogProtocol",
    "RateLimiterProtocol",
    
    # Configuration
    "AuthConfig",
    "AuthConfigType",
]