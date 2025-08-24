"""Configuration management for NeoAdminApi.

Centralized configuration provider to eliminate duplicate configuration imports
and provide unified access to neo-commons configuration across the application.
"""

from .provider import (
    get_config_provider,
    set_config_provider,
    ConfigurationProvider,
    get_app_config,
)

__all__ = [
    "get_config_provider",
    "set_config_provider", 
    "ConfigurationProvider",
    "get_app_config",
]