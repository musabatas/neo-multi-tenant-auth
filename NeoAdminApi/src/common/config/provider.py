"""Centralized configuration management for NeoAdminApi.

This module provides centralized configuration access and eliminates
repetitive configuration imports throughout the application.
"""

from typing import Optional
from functools import lru_cache

from neo_commons.config.manager import get_env_config, EnvironmentConfig
from neo_commons.features.auth import AuthServiceFactory
from neo_commons.features.database.services import DatabaseService


@lru_cache(maxsize=1)
def get_app_config() -> EnvironmentConfig:
    """Get cached application configuration.
    
    Returns:
        Cached EnvironmentConfig instance
    """
    return get_env_config()


class ConfigurationProvider:
    """Centralized configuration provider for NeoAdminApi services."""
    
    def __init__(self, config: Optional[EnvironmentConfig] = None):
        """Initialize with optional custom configuration."""
        self._config = config or get_app_config()
        self._auth_factory: Optional[AuthServiceFactory] = None
    
    @property 
    def config(self) -> EnvironmentConfig:
        """Get configuration instance."""
        return self._config
    
    async def get_auth_factory(self, database_service: DatabaseService) -> AuthServiceFactory:
        """Get cached auth factory with database service.
        
        Args:
            database_service: Database service instance
            
        Returns:
            Configured AuthServiceFactory instance
        """
        if self._auth_factory is None:
            self._auth_factory = AuthServiceFactory(
                keycloak_server_url=self._config.keycloak_server_url,
                keycloak_admin_username=self._config.keycloak_admin or "admin",
                keycloak_admin_password=self._config.keycloak_password or "admin",
                redis_url=self._config.redis_url,
                redis_password=self._config.redis_password,
                database_service=database_service,
            )
        return self._auth_factory
    
    def get_database_url(self) -> str:
        """Get database URL."""
        return self._config.admin_database_url
    
    def get_keycloak_config(self) -> dict:
        """Get Keycloak configuration."""
        return {
            "server_url": self._config.keycloak_server_url,
            "admin_username": self._config.keycloak_admin or "admin",
            "admin_password": self._config.keycloak_password or "admin",
        }
    
    def get_redis_config(self) -> dict:
        """Get Redis configuration."""
        return {
            "url": self._config.redis_url,
            "password": self._config.redis_password,
        }


# Singleton instance
_config_provider: Optional[ConfigurationProvider] = None


def get_config_provider() -> ConfigurationProvider:
    """Get singleton configuration provider.
    
    Returns:
        ConfigurationProvider instance
    """
    global _config_provider
    if _config_provider is None:
        _config_provider = ConfigurationProvider()
    return _config_provider


def set_config_provider(provider: ConfigurationProvider) -> None:
    """Set custom configuration provider for testing.
    
    Args:
        provider: Custom configuration provider
    """
    global _config_provider
    _config_provider = provider