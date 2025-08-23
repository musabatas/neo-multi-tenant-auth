"""
Session Management Module for Neo-Commons

Provides comprehensive session management capabilities including guest authentication,
session caching, and enterprise-grade session protocols for multi-tenant environments.

Key Features:
- Guest session authentication with configurable business rules
- Session-specific caching with intelligent TTL management
- Protocol-based design for dependency injection
- Configurable session providers (default, restrictive, liberal)
- Session validation, extension, and cleanup operations
- Performance metrics and audit trails
"""

# Core session implementations
from .guest import (
    DefaultGuestAuthService,
    DefaultGuestSessionProvider,
    RestrictiveGuestSessionProvider,
    LiberalGuestSessionProvider,
    create_guest_session_provider,
    create_guest_auth_service,
)

# Session caching
from .cache import (
    DefaultSessionCache,
    SessionCacheProtocol,
    create_session_cache,
)

# Session protocols
from .protocols import (
    GuestAuthServiceProtocol,
    SessionCacheServiceProtocol,
    SessionValidatorProtocol,
    SessionManagerProtocol,
    SessionAuditProtocol,
    SessionCleanupProtocol,
    SessionSecurityProtocol,
    SessionMetricsProtocol,
)

__all__ = [
    # Guest authentication services
    "DefaultGuestAuthService",
    "DefaultGuestSessionProvider",
    "RestrictiveGuestSessionProvider", 
    "LiberalGuestSessionProvider",
    "create_guest_session_provider",
    "create_guest_auth_service",
    
    # Session caching
    "DefaultSessionCache",
    "SessionCacheProtocol",
    "create_session_cache",
    
    # Session management protocols
    "GuestAuthServiceProtocol",
    "SessionCacheServiceProtocol",
    "SessionValidatorProtocol",
    "SessionManagerProtocol",
    "SessionAuditProtocol",
    "SessionCleanupProtocol",
    "SessionSecurityProtocol",
    "SessionMetricsProtocol",
]