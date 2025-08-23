"""Modern configuration module for neo-commons.

Clean, type-safe configuration management with no backward compatibility.
Uses the new infrastructure configuration system for maximum performance.
"""

# Keep constants for compatibility with database schema
from .constants import *

# New modern configuration management
from .manager import (
    ConfigurationManager,
    EnvironmentConfig,
    ServiceConfig,
    get_env_config,
    validate_required_env_vars,
    create_config_manager,
    get_database_url,
    get_redis_url,
    is_production,
    is_development,
)

# Logging configuration
from .logging_config import (
    setup_logging,
    LogVerbosity,
    LogFormat,
    LoggingConfig,
)

# Re-export infrastructure configuration for advanced use
from ..infrastructure.configuration import (
    ConfigKey, ConfigValue, ConfigScope, ConfigType, ConfigSource,
    ConfigurationService
)

__all__ = [
    # Constants (database schema compatibility)
    "PerformanceTargets",
    "CacheKeys", 
    "CacheTTL",
    "DatabaseSchemas",
    "AuthProvider",
    "RoleLevel", 
    "UserStatus",
    "PermissionScope",
    "TeamType",
    "RiskLevel",
    "SettingType",
    "ContactType",
    "TenantStatus",
    "DeploymentType",
    "EnvironmentType",
    "PlanTier",
    "BillingCycle",
    "SubscriptionStatus",
    "InvoiceStatus",
    "LineItemType",
    "ConnectionType",
    "HealthStatus",
    "ActorType",
    "RetentionPolicy",
    "DefaultValues",
    "ValidationLimits",
    "SecurityDefaults",
    "ErrorCodes",
    "Headers",
    "AuditEventTypes",
    "APIVersions",
    "FeatureFlags",
    
    # Modern configuration management
    "ConfigurationManager",
    "EnvironmentConfig",
    "ServiceConfig",
    "get_env_config",
    "validate_required_env_vars",
    "create_config_manager",
    "get_database_url",
    "get_redis_url",
    "is_production",
    "is_development",
    
    # Infrastructure components (advanced use)
    "ConfigKey",
    "ConfigValue",
    "ConfigScope",
    "ConfigType",
    "ConfigSource",
    "ConfigurationService",
    
    # Logging configuration
    "setup_logging",
    "LogVerbosity",
    "LogFormat",
    "LoggingConfig",
]