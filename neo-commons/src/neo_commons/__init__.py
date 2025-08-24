"""Neo-Commons - Enterprise-grade shared library for NeoMultiTenant platform.

This library provides unified authentication, database connection management,
caching, and common utilities for the NeoMultiTenant ecosystem.
"""

# Initialize logging configuration on import
from .config.logging_config import setup_logging
setup_logging()

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
    # Basic Value Objects
    UserId,
    TenantId,
    OrganizationId,
    PermissionCode,
    RoleCode,
    
    # Configurable Value Objects Framework
    ConfigurableValueObject,
    ValidationRule,
    ValidationRuleBuilder,
    set_value_object_configuration,
    clear_value_object_cache,
    get_value_object_statistics,
    
    # Configurable Identifier Value Objects
    ConfigurableUserId,
    ConfigurableTenantId,
    ConfigurableOrganizationId,
    ConfigurablePermissionCode,
    ConfigurableRoleCode,
)

from .core.shared import (
    # Core Entities
    RequestContext,
    
    # Application Protocols
    ConfigurationProtocol,
    EventPublisherProtocol,
    EventHandlerProtocol,
    ValidationProtocol,
    EncryptionProtocol,
    LoggingProtocol,
    MetricsProtocol,
    MonitoringProtocol,
    
    # Domain Protocols  
    TenantContextProtocol,
    UserIdentityProtocol,
    UserResolverProtocol,
    
    # Enums
    LogLevel,
    MetricType,
    HealthStatus,
)

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
    "HttpStatusMapper",
    "set_configuration_provider",
    "clear_mapping_cache", 
    "get_mapping_statistics",
    # Backward compatibility aliases
    "ConfigurableHttpStatusMapper",
    
    # Basic Value Objects
    "UserId",
    "TenantId",
    "OrganizationId",
    "PermissionCode",
    "RoleCode",
    
    # Configurable Value Objects Framework
    "ConfigurableValueObject",
    "ValidationRule",
    "ValidationRuleBuilder",
    "set_value_object_configuration",
    "clear_value_object_cache",
    "get_value_object_statistics",
    
    # Configurable Identifier Value Objects
    "ConfigurableUserId",
    "ConfigurableTenantId",
    "ConfigurableOrganizationId",
    "ConfigurablePermissionCode",
    "ConfigurableRoleCode",
    
    # Core Entities
    "RequestContext",
    
    # Application Protocols
    "ConfigurationProtocol",
    "EventPublisherProtocol", 
    "EventHandlerProtocol",
    "ValidationProtocol",
    "EncryptionProtocol",
    "LoggingProtocol",
    "MetricsProtocol",
    "MonitoringProtocol",
    
    # Domain Protocols
    "TenantContextProtocol",
    "UserIdentityProtocol",
    "UserResolverProtocol", 
    
    # Enums
    "LogLevel",
    "MetricType", 
    "HealthStatus",
    
    # TODO: Re-enable when entities are implemented
    # "User",
    # "Organization", 
    # "Tenant",
    # "Team",
    
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
