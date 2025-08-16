"""
Auth Services Module

Backward compatibility wrappers and protocol implementations for authentication services with:
- Legacy API compatibility for existing NeoAdminApi services
- Protocol-based implementations for new services
- Configuration injection for service independence
- Performance optimization with caching integration
"""

from .compatibility import (
    AuthServiceWrapper,
    PermissionServiceWrapper,
    GuestAuthServiceWrapper,
    create_auth_service,
    create_permission_service,
    create_guest_auth_service_wrapper,
    create_user_identity_resolver,
    create_neo_commons_guest_service
)

# Import actual guest service factory (not wrapper)
from .guest.factory import (
    create_guest_auth_service,
    create_default_guest_service,
    create_restrictive_guest_service,
    create_liberal_guest_service
)

__all__ = [
    # Wrapper services (compatibility layer)
    "AuthServiceWrapper",
    "PermissionServiceWrapper", 
    "GuestAuthServiceWrapper",
    
    # Factory functions for wrappers
    "create_auth_service",
    "create_permission_service",
    "create_guest_auth_service_wrapper",
    "create_user_identity_resolver",
    "create_neo_commons_guest_service",
    
    # Actual guest service factories
    "create_guest_auth_service",
    "create_default_guest_service",
    "create_restrictive_guest_service",
    "create_liberal_guest_service"
]