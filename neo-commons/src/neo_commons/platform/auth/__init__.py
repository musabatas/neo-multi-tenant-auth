"""Authentication platform module.

This module provides enterprise-grade authentication and authorization capabilities
following maximum separation principle - one file = one purpose.

Features:
- JWT token validation and management
- Keycloak integration with multi-realm support
- Session management with Redis caching
- Permission-based access control integration
- Extensible authentication providers

Architecture:
- core/: Clean domain objects and contracts only
- application/: Use cases with command/query separation
- infrastructure/: External system adapters and repositories
- api/: Reusable FastAPI components with role-based routing
- extensions/: Hook system for customization

Usage:
    from neo_commons.platform.auth import AuthModule
    
    # Register the module
    auth_module = AuthModule()
    container.register_module(auth_module)
    
    # Use in FastAPI app
    from neo_commons.platform.auth.api.routers import public_auth_router
    app.include_router(public_auth_router, prefix="/api/v1/auth")
"""

__version__ = "1.0.0"
__author__ = "Neo Commons Team"

# Core exports - domain objects and contracts only
from .core.value_objects import AccessToken, RefreshToken, TokenClaims
from .core.exceptions import AuthenticationFailed, TokenExpired, InvalidSignature
from .core.protocols import TokenValidator, SessionManager, RealmProvider

__all__ = [
    # Value Objects
    "AccessToken",
    "RefreshToken", 
    "TokenClaims",
    
    # Exceptions
    "AuthenticationFailed",
    "TokenExpired",
    "InvalidSignature",
    
    # Protocols
    "TokenValidator",
    "SessionManager", 
    "RealmProvider",
]