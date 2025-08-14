"""
Configuration management for neo-commons.

This module provides protocol-based configuration management with support for
different environments, validation, and flexible configuration sources.
"""

from .protocols import (
    # Individual protocols
    DatabaseConfigProtocol,
    CacheConfigProtocol,
    ServerConfigProtocol,
    SecurityConfigProtocol,
    ApplicationMetadataProtocol,
    LoggingConfigProtocol,
    RateLimitingConfigProtocol,
    PaginationConfigProtocol,
    MonitoringConfigProtocol,
    EnvironmentConfigProtocol,
    ConfigValidationProtocol,
    ConfigFactoryProtocol,
    # Comprehensive protocol
    BaseConfigProtocol
)

from .base import (
    # Base implementations
    EnvironmentConfig,
    BaseNeoConfig,
    AdminConfig,
    TenantConfig,
    TestingConfig,
    # Factory functions
    get_config,
    get_admin_config,
    get_tenant_config,
    get_testing_config,
    create_config_for_environment,
    validate_config_or_exit
)

__all__ = [
    # Protocols
    "DatabaseConfigProtocol",
    "CacheConfigProtocol", 
    "ServerConfigProtocol",
    "SecurityConfigProtocol",
    "ApplicationMetadataProtocol",
    "LoggingConfigProtocol",
    "RateLimitingConfigProtocol",
    "PaginationConfigProtocol",
    "MonitoringConfigProtocol",
    "EnvironmentConfigProtocol",
    "ConfigValidationProtocol",
    "ConfigFactoryProtocol",
    "BaseConfigProtocol",
    
    # Implementations
    "EnvironmentConfig",
    "BaseNeoConfig",
    "AdminConfig",
    "TenantConfig", 
    "TestingConfig",
    
    # Factory functions
    "get_config",
    "get_admin_config",
    "get_tenant_config",
    "get_testing_config",
    "create_config_for_environment",
    "validate_config_or_exit"
]