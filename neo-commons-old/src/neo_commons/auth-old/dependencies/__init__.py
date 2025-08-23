"""
Auth Dependencies Module

FastAPI dependency injection components for authentication and authorization with:
- Token validation and user extraction
- Permission checking with database integration
- Guest authentication support for public endpoints
- Multi-tenant permission scoping
- Protocol-based configuration injection
"""

from .auth import (
    CurrentUser,
    CheckPermission,
    TokenData,
    get_current_user,
    get_current_user_optional,
    require_permissions,
    get_token_data,
    get_user_permissions,
    get_user_roles
)
from .guest import (
    GuestOrAuthenticated,
    GuestSessionInfo,
    get_reference_data_access,
    get_guest_session_info,
    create_guest_or_authenticated,
    create_guest_session_info,
    create_reference_data_access
)

__all__ = [
    # Auth dependencies
    "CurrentUser",
    "CheckPermission", 
    "TokenData",
    "get_current_user",
    "get_current_user_optional",
    "require_permissions",
    "get_token_data",
    "get_user_permissions",
    "get_user_roles",
    # Guest dependencies
    "GuestOrAuthenticated",
    "GuestSessionInfo",
    "get_reference_data_access", 
    "get_guest_session_info",
    "create_guest_or_authenticated",
    "create_guest_session_info",
    "create_reference_data_access"
]