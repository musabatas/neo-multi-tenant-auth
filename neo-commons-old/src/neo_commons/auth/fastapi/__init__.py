"""
FastAPI Integration Module for Neo-Commons

Comprehensive FastAPI authentication and authorization components including:
- Protocol-based dependency injection for token validation and permission checking
- Declarative permission decorators with OpenAPI integration
- Enterprise-grade authentication middleware with performance monitoring
- User context management and tenant-aware authentication support

Key Features:
- JWT token validation with configurable strategies
- Database-driven permission checking with intelligent caching
- Automatic permission discovery and metadata collection
- Multi-tenant authentication and authorization support
- Performance metrics and security audit logging
"""

# FastAPI dependencies
from .dependencies import (
    UserProfile,
    CurrentUser,
    CheckPermission,
    TokenData,
    create_current_user,
    create_permission_checker,
    create_token_data,
    require_permissions,
    get_user_permissions,
    get_user_roles,
    security,
)

# Permission decorators
from .decorators import (
    RequirePermission,
    require_permission,
    PermissionMetadata,
)

# Authentication middleware
from .middleware import (
    AuthenticationMiddleware,
    TenantAwareAuthMiddleware,
    create_auth_middleware,
    create_tenant_aware_middleware,
)

__all__ = [
    # FastAPI dependencies
    "UserProfile",
    "CurrentUser",
    "CheckPermission",
    "TokenData",
    "create_current_user",
    "create_permission_checker",
    "create_token_data",
    "require_permissions",
    "get_user_permissions",
    "get_user_roles",
    "security",
    
    # Permission decorators
    "RequirePermission",
    "require_permission", 
    "PermissionMetadata",
    
    # Authentication middleware
    "AuthenticationMiddleware",
    "TenantAwareAuthMiddleware",
    "create_auth_middleware",
    "create_tenant_aware_middleware",
]