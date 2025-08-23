"""Configuration infrastructure for neo-commons.

Infrastructure-level configuration management system:
- entities/: Configuration domain objects, values, and protocols
- services/: Configuration business logic and orchestration  
- repositories/: Configuration data access and persistence

This is a core infrastructure component that serves ALL features and services.
"""

# Core configuration entities and protocols
from .entities import (
    ConfigKey, ConfigValue, ConfigSchema, ConfigGroup,
    ConfigScope, ConfigType, ConfigSource,
    ConfigurationProvider, ConfigurationRepository, ConfigurationCache,
    ConfigurationValidator, ConfigurationSource as ConfigSourceProtocol,
    ConfigurationWatcher, ConfigurationExporter, ConfigurationAuditor,
    ConfigurationManager
)

# Configuration service orchestration
from .services import ConfigurationService

# Concrete repository implementations
from .repositories import AsyncPGConfigurationRepository

__all__ = [
    # Entities
    "ConfigKey",
    "ConfigValue",
    "ConfigSchema", 
    "ConfigGroup",
    
    # Enums
    "ConfigScope",
    "ConfigType",
    "ConfigSource",
    
    # Protocols
    "ConfigurationProvider",
    "ConfigurationRepository",
    "ConfigurationCache",
    "ConfigurationValidator",
    "ConfigSourceProtocol",
    "ConfigurationWatcher", 
    "ConfigurationExporter",
    "ConfigurationAuditor",
    "ConfigurationManager",
    
    # Services
    "ConfigurationService",
    
    # Repository Implementations
    "AsyncPGConfigurationRepository",
]