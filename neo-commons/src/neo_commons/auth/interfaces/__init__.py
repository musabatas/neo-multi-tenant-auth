"""
Authorization interfaces layer - FastAPI integration and adapters.

This layer provides FastAPI dependencies, decorators, and middleware
for integrating authorization with web frameworks.
"""

from .dependencies.auth_dependencies import (
    get_current_user,
    get_user_context,
    get_tenant_context,
    require_permission,
    require_any_permission,
    require_all_permissions,
    get_permission_service,
    get_role_service
)

from .decorators.permission_decorators import (
    permission_required,
    role_required,
    superadmin_required,
    tenant_access_required
)

# Middleware and routers will be implemented when needed

__all__ = [
    # Dependencies
    "get_current_user",
    "get_user_context", 
    "get_tenant_context",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "get_permission_service",
    "get_role_service",
    
    # Decorators
    "permission_required",
    "role_required",
    "superadmin_required", 
    "tenant_access_required"
]