"""Centralized Keycloak configuration service following DRY principles.

This service provides a single source of truth for Keycloak configuration,
eliminating duplication and ensuring consistent configuration across the application.
"""

import os
from typing import Optional
from dataclasses import dataclass

from ..entities.keycloak_config import KeycloakConfig
from ....core.exceptions.auth import AuthenticationError


@dataclass
class KeycloakEnvironmentConfig:
    """Environment configuration for Keycloak with standardized variable names."""
    
    # Server configuration
    server_url: str
    require_https: bool
    
    # Admin realm configuration
    admin_realm: str
    admin_client_id: str
    admin_client_secret: Optional[str]
    
    # Admin credentials (fallback for operations requiring admin access)
    admin_username: Optional[str]
    admin_password: Optional[str]
    
    # Additional settings
    verify_ssl: bool
    timeout: int
    
    @classmethod
    def from_environment(cls) -> "KeycloakEnvironmentConfig":
        """Load configuration from environment variables with consistent naming."""
        return cls(
            # Server configuration
            server_url=os.getenv("KEYCLOAK_SERVER_URL", "http://localhost:8080"),
            require_https=os.getenv("KEYCLOAK_REQUIRE_HTTPS", "false").lower() == "true",
            
            # Admin realm configuration
            admin_realm=os.getenv("KEYCLOAK_REALM", "platform-admin"),
            admin_client_id=os.getenv("KEYCLOAK_CLIENT_ID", "neo-admin-api"),
            admin_client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET"),
            
            # Admin credentials (fallback)
            admin_username=os.getenv("KEYCLOAK_ADMIN"),
            admin_password=os.getenv("KEYCLOAK_PASSWORD"),
            
            # Additional settings
            verify_ssl=os.getenv("KEYCLOAK_VERIFY_SSL", "false").lower() == "true",
            timeout=int(os.getenv("KEYCLOAK_TIMEOUT", "30")),
        )
    
    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.server_url:
            raise AuthenticationError("KEYCLOAK_SERVER_URL is required")
        
        if not self.admin_realm:
            raise AuthenticationError("KEYCLOAK_REALM is required")
        
        if not self.admin_client_id:
            raise AuthenticationError("KEYCLOAK_CLIENT_ID is required")
        
        # Either client secret OR admin credentials must be provided
        has_client_auth = bool(self.admin_client_secret)
        has_admin_auth = bool(self.admin_username and self.admin_password)
        
        if not has_client_auth and not has_admin_auth:
            raise AuthenticationError(
                "Either KEYCLOAK_CLIENT_SECRET or "
                "KEYCLOAK_ADMIN/KEYCLOAK_PASSWORD must be provided"
            )


class KeycloakConfigService:
    """Centralized service for Keycloak configuration management.
    
    This service ensures consistent configuration across all Keycloak operations,
    following DRY principles and eliminating configuration duplication.
    """
    
    _instance: Optional["KeycloakConfigService"] = None
    _env_config: Optional[KeycloakEnvironmentConfig] = None
    
    def __new__(cls) -> "KeycloakConfigService":
        """Singleton pattern to ensure single configuration instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration service."""
        if self._env_config is None:
            self._env_config = KeycloakEnvironmentConfig.from_environment()
            self._env_config.validate()
    
    @classmethod
    def get_instance(cls) -> "KeycloakConfigService":
        """Get singleton instance of configuration service."""
        return cls()
    
    def get_admin_realm_config(self) -> KeycloakConfig:
        """Get KeycloakConfig for admin realm operations.
        
        This configuration is used for administrative operations like
        user authentication in the admin realm.
        
        Returns:
            KeycloakConfig configured for the admin realm
        """
        if not self._env_config:
            self._env_config = KeycloakEnvironmentConfig.from_environment()
            self._env_config.validate()
        
        return KeycloakConfig(
            server_url=self._env_config.server_url,
            realm_name=self._env_config.admin_realm,
            client_id=self._env_config.admin_client_id,
            client_secret=self._env_config.admin_client_secret or "",
            require_https=self._env_config.require_https,
        )
    
    def get_tenant_realm_config(self, realm_name: str) -> KeycloakConfig:
        """Get KeycloakConfig for tenant realm operations.
        
        This configuration is used for tenant-specific operations.
        
        Args:
            realm_name: Name of the tenant realm
            
        Returns:
            KeycloakConfig configured for the specified tenant realm
        """
        if not self._env_config:
            self._env_config = KeycloakEnvironmentConfig.from_environment()
            self._env_config.validate()
        
        # For tenant realms, we typically use the same client but different realm
        # This can be customized per-tenant if needed
        return KeycloakConfig(
            server_url=self._env_config.server_url,
            realm_name=realm_name,
            client_id=self._env_config.admin_client_id,
            client_secret=self._env_config.admin_client_secret or "",
            require_https=self._env_config.require_https,
        )
    
    def get_admin_adapter_config(self) -> dict:
        """Get configuration for KeycloakAdminAdapter.
        
        Returns configuration dict for initializing KeycloakAdminAdapter,
        preferring client credentials over admin username/password.
        
        Returns:
            Dict with configuration for KeycloakAdminAdapter
        """
        if not self._env_config:
            self._env_config = KeycloakEnvironmentConfig.from_environment()
            self._env_config.validate()
        
        config = {
            "server_url": self._env_config.server_url,
            "realm_name": self._env_config.admin_realm,
            "verify": self._env_config.verify_ssl,
            "timeout": self._env_config.timeout,
        }
        
        # Prefer client credentials if available
        if self._env_config.admin_client_secret:
            config.update({
                "client_id": self._env_config.admin_client_id,
                "client_secret": self._env_config.admin_client_secret,
            })
        else:
            # Fallback to admin username/password
            config.update({
                "client_id": "admin-cli",  # Default admin client
                "username": self._env_config.admin_username,
                "password": self._env_config.admin_password,
            })
        
        return config
    
    def get_environment_config(self) -> KeycloakEnvironmentConfig:
        """Get raw environment configuration for advanced use cases.
        
        Returns:
            KeycloakEnvironmentConfig with all settings
        """
        if not self._env_config:
            self._env_config = KeycloakEnvironmentConfig.from_environment()
            self._env_config.validate()
        
        return self._env_config
    
    @classmethod
    def reload_configuration(cls) -> None:
        """Reload configuration from environment variables.
        
        Useful for testing or when environment variables change.
        """
        if cls._instance:
            cls._instance._env_config = KeycloakEnvironmentConfig.from_environment()
            cls._instance._env_config.validate()