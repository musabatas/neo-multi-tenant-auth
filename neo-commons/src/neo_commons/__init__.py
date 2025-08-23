"""Neo-Commons - Enterprise-grade shared library for NeoMultiTenant platform.

This library provides unified authentication, database connection management,
caching, and common utilities for the NeoMultiTenant ecosystem.
"""

# Modern configuration management
from .config import (
    get_env_config,
    validate_required_env_vars,
    get_database_url,
    get_redis_url,
    is_production,
    is_development,
    DatabaseSchemas,
    AuthProvider,
    UserStatus,
    PermissionScope,
    TenantStatus,
)

# Infrastructure components
from .infrastructure import (
    ConfigurationService,
    ConfigKey,
    ConfigValue,
    ConfigScope,
)

from .core.exceptions import (
    # Base Exception
    NeoCommonsError,
    
    # Common Exceptions
    ConfigurationError,
    DatabaseError,
    AuthenticationError,
    AuthorizationError,
    TenantError,
    CacheError,
    ValidationError,
    
    # Utility Functions
    get_http_status_code,
    create_error_response,
)

from .core.value_objects import (
    # Value Objects
    UserId,
    TenantId,
    OrganizationId,
    PermissionCode,
    RoleCode,
)

# TODO: Re-enable these imports when the modules are properly implemented
# from .core.shared import (
#     # Core Entities
#     RequestContext,
#     
#     # Core Protocols
#     TenantContextProtocol,
#     UserIdentityProtocol,
#     PermissionCheckerProtocol,
# )

# TODO: Re-enable these imports when entities are properly implemented
# from .features.users.entities import User
# from .features.organizations.entities import Organization
# from .features.tenants.entities import Tenant
# from .features.teams.entities import Team

# TODO: Re-enable these imports when protocols are properly implemented
# from .infrastructure.protocols import (
#     DatabaseConnectionProtocol,
#     CacheProtocol,
# )

from .utils import (
    generate_uuid_v7,
    generate_uuid_v4,
    generate_id,
    is_valid_uuid,
    generate_tenant_slug,
)

# TODO: Re-enable feature services when they are properly implemented
# from .features import (
#     # Database features
#     DatabaseService,
#     
#     # Cache features
#     CacheService,
# )

__version__ = "0.1.0"

__all__ = [
    # Modern Configuration
    "get_env_config",
    "validate_required_env_vars",
    "get_database_url",
    "get_redis_url", 
    "is_production",
    "is_development",
    "DatabaseSchemas",
    "AuthProvider",
    "UserStatus",
    "PermissionScope",
    "TenantStatus",
    
    # Infrastructure
    "ConfigurationService",
    "ConfigKey",
    "ConfigValue",
    "ConfigScope",
    
    # Core Exceptions
    "NeoCommonsError",
    "ConfigurationError",
    "DatabaseError",
    "AuthenticationError",
    "AuthorizationError",
    "TenantError",
    "CacheError",
    "ValidationError",
    "get_http_status_code",
    "create_error_response",
    
    # Value Objects
    "UserId",
    "TenantId",
    "OrganizationId",
    "PermissionCode",
    "RoleCode",
    
    # TODO: Re-enable when entities and protocols are implemented
    # "User",
    # "Organization", 
    # "Tenant",
    # "Team",
    # "RequestContext",
    # "TenantContextProtocol",
    # "UserIdentityProtocol", 
    # "PermissionCheckerProtocol",
    # "DatabaseConnectionProtocol",
    # "CacheProtocol",
    
    # Utilities
    "generate_uuid_v7",
    "generate_uuid_v4",
    "generate_id",
    "is_valid_uuid",
    "generate_tenant_slug",
    
    # TODO: Re-enable when feature services are implemented
    # "DatabaseService",
    # "CacheService",
    
    # Version
    "__version__",
]
