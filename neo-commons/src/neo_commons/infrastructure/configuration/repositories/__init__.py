"""Configuration repositories package.

Concrete implementations of configuration data access protocols using AsyncPG.
"""

from .config_repository import AsyncPGConfigurationRepository

__all__ = [
    "AsyncPGConfigurationRepository",
]