"""Infrastructure-level middleware for FastAPI applications.

Provides cross-cutting concerns like authentication, tenant context, logging,
security, and performance monitoring following Feature-First + Clean Core architecture.
"""

# Auth middleware moved to features/auth/middleware.py for better Feature-First organization
# from ...features.auth.middleware import AuthMiddleware, TenantIsolationMiddleware  # TODO: Enable when UserService is implemented
# from .tenant_middleware import TenantContextMiddleware, MultiTenantDatabaseMiddleware  # TODO: Enable when TenantService is implemented  
from .logging_middleware import StructuredLoggingMiddleware, RequestContextLoggerAdapter
from .security_middleware import SecurityMiddleware, CORSMiddleware, RateLimitMiddleware
from .performance_middleware import PerformanceMiddleware, TimingMiddleware, DatabasePerformanceMiddleware
from .error_middleware import ErrorHandlingMiddleware, ValidationErrorHandler, DatabaseErrorHandler
from .factory import MiddlewareFactory, create_middleware_factory
# from .dependencies import (  # TODO: Enable when services are implemented
#     get_current_user,
#     get_current_tenant,
#     get_request_context,
#     require_permission,
#     require_role,
#     require_authentication,
#     require_tenant_context,
#     require_authenticated_tenant,
#     require_any_permission,
#     require_all_permissions,
#     require_any_role,
#     get_optional_user,
#     get_optional_tenant,
#     get_pagination,
#     require_resource_permission,
#     require_tenant_admin,
#     require_platform_admin
# )

__all__ = [
    # Middleware classes
    # Auth middleware moved to features/auth/middleware.py
    # "AuthMiddleware",  # TODO: Enable when UserService is implemented
    # "TenantIsolationMiddleware",  # TODO: Enable when UserService is implemented
    # "TenantContextMiddleware",  # TODO: Enable when TenantService is implemented
    # "MultiTenantDatabaseMiddleware",  # TODO: Enable when TenantService is implemented
    "StructuredLoggingMiddleware",
    "RequestContextLoggerAdapter", 
    "SecurityMiddleware",
    "CORSMiddleware",
    "RateLimitMiddleware",
    "PerformanceMiddleware",
    "TimingMiddleware",
    "DatabasePerformanceMiddleware",
    "ErrorHandlingMiddleware",
    "ValidationErrorHandler",
    "DatabaseErrorHandler",
    
    # Factory and configuration
    "MiddlewareFactory",
    "create_middleware_factory",
    
    # FastAPI dependencies - TODO: Enable when services are implemented
    # "get_current_user",
    # "get_current_tenant",
    # "get_request_context",
    # "get_optional_user",
    # "get_optional_tenant",
    # "require_authentication",
    # "require_tenant_context",
    # "require_authenticated_tenant",
    # "require_permission",
    # "require_any_permission",
    # "require_all_permissions",
    # "require_resource_permission",
    # "require_role",
    # "require_any_role",
    # "require_tenant_admin",
    # "require_platform_admin",
    # "get_pagination",
]