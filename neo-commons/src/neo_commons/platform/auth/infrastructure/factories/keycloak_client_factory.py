"""Keycloak client factory for authentication platform."""

import logging
from typing import Dict, Any, Optional

from ...core.value_objects import RealmIdentifier
from ...core.exceptions import AuthenticationFailed
from ..adapters import KeycloakAdminAdapter, KeycloakOpenIDAdapter

logger = logging.getLogger(__name__)


class KeycloakClientFactory:
    """Keycloak client factory following maximum separation principle.
    
    Handles ONLY Keycloak client instantiation and configuration for authentication platform.
    Does not handle token validation, caching, or authentication logic.
    """
    
    def __init__(self, keycloak_config: Dict[str, Any]):
        """Initialize Keycloak client factory.
        
        Args:
            keycloak_config: Keycloak configuration dictionary
        """
        if not keycloak_config:
            raise ValueError("Keycloak configuration is required")
        
        self.config = keycloak_config
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate Keycloak configuration.
        
        Raises:
            ValueError: If configuration is invalid
        """
        required_fields = [
            "server_url",
            "realm_name",
            "client_id"
        ]
        
        for field in required_fields:
            if not self.config.get(field):
                raise ValueError(f"Missing required Keycloak config field: {field}")
        
        # Validate server URL format
        server_url = self.config["server_url"]
        if not server_url.startswith(("http://", "https://")):
            raise ValueError("Invalid Keycloak server URL format")
        
        logger.debug("Keycloak configuration validated successfully")
    
    def _normalize_server_url(self, server_url: str) -> str:
        """Normalize Keycloak server URL for v18+ compatibility.
        
        Args:
            server_url: Original server URL
            
        Returns:
            Normalized server URL
        """
        server_url = server_url.rstrip('/')
        
        # Remove '/auth' suffix for Keycloak v18+ compatibility
        if server_url.endswith('/auth'):
            server_url = server_url[:-5]
            logger.debug(f"Removed /auth suffix for Keycloak v18+ compatibility: {server_url}")
        
        return server_url
    
    async def create_openid_client(
        self,
        realm_id: RealmIdentifier,
        client_secret: Optional[str] = None
    ) -> 'KeycloakOpenIDClient':
        """Create Keycloak OpenID Connect client.
        
        Args:
            realm_id: Realm identifier
            client_secret: Optional client secret for confidential clients
            
        Returns:
            Configured Keycloak OpenID client
            
        Raises:
            AuthenticationFailed: If client creation fails
        """
        try:
            logger.debug(f"Creating Keycloak OpenID client for realm: {realm_id.value}")
            
            # Import here to avoid circular dependencies
            from keycloak import KeycloakOpenID
            
            # Prepare client configuration
            config = {
                "server_url": self._normalize_server_url(self.config["server_url"]),
                "client_id": self.config["client_id"],
                "realm_name": str(realm_id.value),
                "client_secret_key": client_secret or self.config.get("client_secret"),
                "verify": self.config.get("verify_ssl", True),
            }
            
            # Create Keycloak OpenID client
            keycloak_openid = KeycloakOpenID(**config)
            
            logger.debug(f"Successfully created Keycloak OpenID client for realm: {realm_id.value}")
            return keycloak_openid
            
        except Exception as e:
            logger.error(f"Failed to create Keycloak OpenID client for realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Keycloak OpenID client creation failed",
                reason="client_creation_failed",
                context={
                    "realm_id": str(realm_id.value),
                    "error": str(e)
                }
            )
    
    async def create_admin_client(
        self,
        realm_id: RealmIdentifier,
        admin_username: Optional[str] = None,
        admin_password: Optional[str] = None,
        admin_client_secret: Optional[str] = None
    ) -> 'KeycloakAdminClient':
        """Create Keycloak Admin API client.
        
        Args:
            realm_id: Realm identifier
            admin_username: Admin username (if using username/password auth)
            admin_password: Admin password (if using username/password auth)
            admin_client_secret: Admin client secret (if using client credentials)
            
        Returns:
            Configured Keycloak Admin client
            
        Raises:
            AuthenticationFailed: If client creation fails
        """
        try:
            logger.debug(f"Creating Keycloak Admin client for realm: {realm_id.value}")
            
            # Import here to avoid circular dependencies
            from keycloak import KeycloakAdmin
            
            # Prepare admin client configuration
            config = {
                "server_url": self._normalize_server_url(self.config["server_url"]),
                "realm_name": str(realm_id.value),
                "verify": self.config.get("verify_ssl", True),
            }
            
            # Add authentication method
            if admin_username and admin_password:
                # Username/password authentication
                config.update({
                    "username": admin_username,
                    "password": admin_password,
                    "client_id": self.config.get("admin_client_id", "admin-cli"),
                })
            elif admin_client_secret:
                # Client credentials authentication
                config.update({
                    "client_id": self.config.get("admin_client_id", self.config["client_id"]),
                    "client_secret_key": admin_client_secret,
                })
            else:
                # Use configuration defaults
                config.update({
                    "username": self.config.get("admin_username"),
                    "password": self.config.get("admin_password"),
                    "client_id": self.config.get("admin_client_id", "admin-cli"),
                    "client_secret_key": self.config.get("admin_client_secret"),
                })
            
            # Create Keycloak Admin client
            keycloak_admin = KeycloakAdmin(**config)
            
            logger.debug(f"Successfully created Keycloak Admin client for realm: {realm_id.value}")
            return keycloak_admin
            
        except Exception as e:
            logger.error(f"Failed to create Keycloak Admin client for realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Keycloak Admin client creation failed",
                reason="admin_client_creation_failed",
                context={
                    "realm_id": str(realm_id.value),
                    "error": str(e)
                }
            )
    
    async def create_openid_adapter(
        self,
        realm_id: RealmIdentifier,
        client_secret: Optional[str] = None
    ) -> KeycloakOpenIDAdapter:
        """Create Keycloak OpenID adapter with client.
        
        Args:
            realm_id: Realm identifier
            client_secret: Optional client secret for confidential clients
            
        Returns:
            Configured Keycloak OpenID adapter
            
        Raises:
            AuthenticationFailed: If adapter creation fails
        """
        try:
            logger.debug(f"Creating Keycloak OpenID adapter for realm: {realm_id.value}")
            
            # Create underlying Keycloak OpenID client
            keycloak_client = await self.create_openid_client(realm_id, client_secret)
            
            # Create adapter with client
            adapter = KeycloakOpenIDAdapter(keycloak_client)
            
            logger.debug(f"Successfully created Keycloak OpenID adapter for realm: {realm_id.value}")
            return adapter
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to create Keycloak OpenID adapter for realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Keycloak OpenID adapter creation failed",
                reason="adapter_creation_failed",
                context={
                    "realm_id": str(realm_id.value),
                    "error": str(e)
                }
            )
    
    async def create_admin_adapter(
        self,
        realm_id: RealmIdentifier,
        admin_username: Optional[str] = None,
        admin_password: Optional[str] = None,
        admin_client_secret: Optional[str] = None
    ) -> KeycloakAdminAdapter:
        """Create Keycloak Admin adapter with client.
        
        Args:
            realm_id: Realm identifier
            admin_username: Admin username (if using username/password auth)
            admin_password: Admin password (if using username/password auth)
            admin_client_secret: Admin client secret (if using client credentials)
            
        Returns:
            Configured Keycloak Admin adapter
            
        Raises:
            AuthenticationFailed: If adapter creation fails
        """
        try:
            logger.debug(f"Creating Keycloak Admin adapter for realm: {realm_id.value}")
            
            # Create underlying Keycloak Admin client
            keycloak_client = await self.create_admin_client(
                realm_id,
                admin_username,
                admin_password,
                admin_client_secret
            )
            
            # Create adapter with client
            adapter = KeycloakAdminAdapter(keycloak_client)
            
            logger.debug(f"Successfully created Keycloak Admin adapter for realm: {realm_id.value}")
            return adapter
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to create Keycloak Admin adapter for realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Keycloak Admin adapter creation failed",
                reason="admin_adapter_creation_failed",
                context={
                    "realm_id": str(realm_id.value),
                    "error": str(e)
                }
            )
    
    def get_connection_info(self, realm_id: RealmIdentifier) -> Dict[str, Any]:
        """Get connection information for realm.
        
        Args:
            realm_id: Realm identifier
            
        Returns:
            Dictionary with connection information
        """
        return {
            "server_url": self._normalize_server_url(self.config["server_url"]),
            "realm_name": str(realm_id.value),
            "client_id": self.config["client_id"],
            "verify_ssl": self.config.get("verify_ssl", True),
            "admin_client_id": self.config.get("admin_client_id", "admin-cli"),
        }
    
    async def test_connection(
        self,
        realm_id: RealmIdentifier
    ) -> Dict[str, Any]:
        """Test connection to Keycloak realm.
        
        Args:
            realm_id: Realm identifier
            
        Returns:
            Dictionary with connection test results
            
        Raises:
            AuthenticationFailed: If connection test fails
        """
        try:
            logger.info(f"Testing Keycloak connection for realm: {realm_id.value}")
            
            # Create OpenID client for testing
            keycloak_client = await self.create_openid_client(realm_id)
            
            # Test connection by getting well-known configuration
            async with KeycloakOpenIDAdapter(keycloak_client) as adapter:
                well_known = await adapter.get_well_known_configuration()
            
            logger.info(f"Successfully tested Keycloak connection for realm: {realm_id.value}")
            
            return {
                "realm_id": str(realm_id.value),
                "server_url": self._normalize_server_url(self.config["server_url"]),
                "connection_status": "success",
                "issuer": well_known.get("issuer"),
                "authorization_endpoint": well_known.get("authorization_endpoint"),
                "token_endpoint": well_known.get("token_endpoint"),
                "tested_at": logger.debug("Connection test completed")
            }
            
        except Exception as e:
            logger.error(f"Keycloak connection test failed for realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Keycloak connection test failed",
                reason="connection_test_failed",
                context={
                    "realm_id": str(realm_id.value),
                    "error": str(e)
                }
            )