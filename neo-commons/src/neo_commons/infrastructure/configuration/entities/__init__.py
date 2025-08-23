"""Configuration entities package.

Domain entities and protocols for configuration management.
"""

from .config import (
    ConfigKey, ConfigValue, ConfigSchema, ConfigGroup,
    ConfigScope, ConfigType, ConfigSource
)
from .protocols import (
    ConfigurationProvider,
    ConfigurationRepository,
    ConfigurationCache,
    ConfigurationValidator,
    ConfigurationSource,
    ConfigurationWatcher,
    ConfigurationExporter,
    ConfigurationAuditor,
    ConfigurationManager
)

__all__ = [
    # Domain entities
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
    "ConfigurationSource",
    "ConfigurationWatcher",
    "ConfigurationExporter",
    "ConfigurationAuditor",
    "ConfigurationManager",
]