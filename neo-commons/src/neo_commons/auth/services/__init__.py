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
    create_guest_auth_service,
    create_user_identity_resolver,
    create_neo_commons_guest_service
)

__all__ = [
    "AuthServiceWrapper",
    "PermissionServiceWrapper", 
    "GuestAuthServiceWrapper",
    "create_auth_service",
    "create_permission_service",
    "create_guest_auth_service",
    "create_user_identity_resolver",
    "create_neo_commons_guest_service"
]