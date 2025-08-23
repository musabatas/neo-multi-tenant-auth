"""Keycloak Admin API adapter."""

import logging
from typing import Dict, List, Optional

import httpx
from keycloak import KeycloakAdmin
from keycloak.exceptions import KeycloakError

from ....core.exceptions.auth import (
    KeycloakConnectionError,
    RealmConfigurationError,
    RealmNotFoundError,
)
from ....core.value_objects.identifiers import RealmId, TenantId
from ..entities.keycloak_config import KeycloakConfig

logger = logging.getLogger(__name__)


class KeycloakAdminAdapter:
    """Adapter for Keycloak Admin API operations."""
    
    def __init__(
        self,
        server_url: str,
        realm_name: str = "master",
        client_id: str = "admin-cli",
        verify: bool = True,
        timeout: int = 30,
        # Option 1: Admin username/password authentication
        username: Optional[str] = None,
        password: Optional[str] = None,
        # Option 2: Client credentials authentication
        client_secret: Optional[str] = None,
    ):
        """Initialize Keycloak admin adapter.
        
        Supports two authentication methods:
        1. Admin credentials: username + password
        2. Client credentials: client_id + client_secret
        
        Args:
            server_url: Keycloak server URL
            realm_name: Realm to authenticate against (default: master)
            client_id: Client ID (default: admin-cli)
            verify: SSL verification (default: True)
            timeout: HTTP timeout in seconds (default: 30)
            username: Admin username (for admin auth)
            password: Admin password (for admin auth)
            client_secret: Client secret (for client credentials auth)
        """
        # Ensure server_url doesn't have /auth/ suffix for Keycloak v18+
        self.server_url = self._normalize_server_url(server_url)
        self.realm_name = realm_name
        self.client_id = client_id
        self.verify = verify
        self.timeout = timeout
        
        # Authentication method
        self.username = username
        self.password = password
        self.client_secret = client_secret
        
        # Validate authentication parameters
        if not ((username and password) or client_secret):
            raise ValueError("Must provide either (username + password) or client_secret for authentication")
        
        self._admin_client: Optional[KeycloakAdmin] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self.target_realm = realm_name  # The realm we want to manage (different from auth realm)
    
    def _normalize_server_url(self, server_url: str) -> str:
        """Normalize server URL for Keycloak v18+ compatibility.
        
        Removes /auth/ suffix if present, as it's not needed for Keycloak v18+.
        """
        server_url = server_url.rstrip('/')
        
        if server_url.endswith('/auth'):
            server_url = server_url[:-5]  # Remove '/auth'
            logger.info(f"Removed /auth suffix for Keycloak v18+ compatibility: {server_url}")
        
        return server_url
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_connected()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_connections()
    
    async def _ensure_connected(self) -> None:
        """Ensure connection to Keycloak admin API."""
        if self._admin_client is None:
            try:
                if self.client_secret:
                    # Use client credentials authentication
                    from keycloak import KeycloakOpenIDConnection
                    
                    connection = KeycloakOpenIDConnection(
                        server_url=self.server_url,
                        realm_name=self.realm_name,
                        client_id=self.client_id,
                        client_secret_key=self.client_secret,
                        verify=self.verify,
                    )
                    
                    self._admin_client = KeycloakAdmin(connection=connection)
                    logger.info(f"Connected to Keycloak admin API using client credentials for realm: {self.realm_name}")
                    
                    # Store the target realm for operations
                    self.target_realm = self.realm_name  # Client credentials usually work in the same realm
                    
                else:
                    # Use admin username/password authentication
                    # Admin users authenticate against master realm, then manage other realms
                    self._admin_client = KeycloakAdmin(
                        server_url=self.server_url,
                        username=self.username,
                        password=self.password,
                        realm_name="master",  # Admin users ALWAYS authenticate in master realm
                        client_id=self.client_id if self.client_id else "admin-cli",
                        verify=self.verify,
                    )
                    logger.info(f"Connected to Keycloak admin API using admin credentials, will manage realm: {self.realm_name}")
                    
                    # Store the target realm for operations
                    # Admin stays authenticated in master but operates on target realm
                    self.target_realm = self.realm_name
                
                # Test connection (uses master realm for admin auth)
                await self._test_connection()
                
            except Exception as e:
                logger.error(f"Failed to connect to Keycloak admin API: {e}")
                raise KeycloakConnectionError(f"Cannot connect to Keycloak: {e}") from e
        
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify,
            )
    
    async def _test_connection(self) -> None:
        """Test connection to Keycloak."""
        try:
            # Simple test - try to get realms which uses the admin's permissions
            # Note: get_server_info doesn't have an async version, so we use a different test
            # We'll try to count users in the current realm as a connection test
            await self._admin_client.a_users_count()
            logger.info("Successfully connected to Keycloak admin API")
        except KeycloakError as e:
            raise KeycloakConnectionError(f"Keycloak connection test failed: {e}") from e
    
    def _create_realm_admin(self, realm_name: str) -> 'KeycloakAdmin':
        """Create a KeycloakAdmin client for a specific realm."""
        if self.client_secret:
            # Use client credentials authentication
            from keycloak import KeycloakOpenIDConnection
            connection = KeycloakOpenIDConnection(
                server_url=self.server_url,
                realm_name=realm_name,
                client_id=self.client_id,
                client_secret_key=self.client_secret,
                verify=self.verify,
            )
            return KeycloakAdmin(connection=connection)
        else:
            # Use admin username/password authentication
            return KeycloakAdmin(
                server_url=self.server_url,
                username=self.username,
                password=self.password,
                realm_name=realm_name,
                client_id=self.client_id,
                verify=self.verify,
            )
    
    async def _close_connections(self) -> None:
        """Close connections."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
        # KeycloakAdmin doesn't need explicit closing
        self._admin_client = None
    
    async def create_realm(
        self, 
        realm_name: str, 
        display_name: Optional[str] = None,
        enabled: bool = True,
        **realm_settings
    ) -> Dict:
        """Create a new realm."""
        await self._ensure_connected()
        
        realm_data = {
            "realm": realm_name,
            "displayName": display_name or realm_name,
            "enabled": enabled,
            **realm_settings
        }
        
        try:
            self._admin_client.create_realm(realm_data)
            logger.info(f"Created realm: {realm_name}")
            return await self.get_realm(realm_name)
        
        except KeycloakError as e:
            logger.error(f"Failed to create realm {realm_name}: {e}")
            raise RealmConfigurationError(f"Cannot create realm: {e}") from e
    
    async def get_realm(self, realm_name: str) -> Dict:
        """Get realm information."""
        await self._ensure_connected()
        
        try:
            realm_data = self._admin_client.get_realm(realm_name)
            return realm_data
        
        except KeycloakError as e:
            if "404" in str(e):
                raise RealmNotFoundError(f"Realm '{realm_name}' not found") from e
            logger.error(f"Failed to get realm {realm_name}: {e}")
            raise KeycloakConnectionError(f"Cannot get realm: {e}") from e
    
    async def update_realm(self, realm_name: str, realm_data: Dict) -> None:
        """Update realm configuration."""
        await self._ensure_connected()
        
        try:
            self._admin_client.update_realm(realm_name, realm_data)
            logger.info(f"Updated realm: {realm_name}")
        
        except KeycloakError as e:
            if "404" in str(e):
                raise RealmNotFoundError(f"Realm '{realm_name}' not found") from e
            logger.error(f"Failed to update realm {realm_name}: {e}")
            raise RealmConfigurationError(f"Cannot update realm: {e}") from e
    
    async def delete_realm(self, realm_name: str) -> None:
        """Delete a realm."""
        await self._ensure_connected()
        
        try:
            self._admin_client.delete_realm(realm_name)
            logger.info(f"Deleted realm: {realm_name}")
        
        except KeycloakError as e:
            if "404" in str(e):
                raise RealmNotFoundError(f"Realm '{realm_name}' not found") from e
            logger.error(f"Failed to delete realm {realm_name}: {e}")
            raise RealmConfigurationError(f"Cannot delete realm: {e}") from e
    
    async def list_realms(self) -> List[Dict]:
        """List all realms."""
        await self._ensure_connected()
        
        try:
            realms = self._admin_client.get_realms()
            return realms
        
        except KeycloakError as e:
            logger.error(f"Failed to list realms: {e}")
            raise KeycloakConnectionError(f"Cannot list realms: {e}") from e
    
    async def create_client(
        self, 
        realm_name: str, 
        client_id: str, 
        client_secret: Optional[str] = None,
        **client_settings
    ) -> Dict:
        """Create a client in the realm."""
        await self._ensure_connected()
        
        try:
            # Create a separate admin client for the target realm
            if self.client_secret:
                # Use client credentials authentication
                from keycloak import KeycloakOpenIDConnection
                connection = KeycloakOpenIDConnection(
                    server_url=self.server_url,
                    realm_name=realm_name,
                    client_id=self.client_id,
                    client_secret_key=self.client_secret,
                    verify=self.verify,
                )
                target_admin = KeycloakAdmin(connection=connection)
            else:
                # Use admin username/password authentication
                target_admin = KeycloakAdmin(
                    server_url=self.server_url,
                    username=self.username,
                    password=self.password,
                    realm_name=realm_name,
                    client_id=self.client_id,
                    verify=self.verify,
                )
            
            client_data = {
                "clientId": client_id,
                "enabled": True,
                "publicClient": client_secret is None,
                "standardFlowEnabled": True,
                "directAccessGrantsEnabled": True,
                **client_settings
            }
            
            if client_secret:
                client_data["secret"] = client_secret
            
            client_uuid = target_admin.create_client(client_data)
            logger.info(f"Created client {client_id} in realm {realm_name}")
            
            return target_admin.get_client(client_uuid)
        
        except KeycloakError as e:
            logger.error(f"Failed to create client {client_id}: {e}")
            raise RealmConfigurationError(f"Cannot create client: {e}") from e
    
    async def get_realm_public_key(self, realm_name: str) -> str:
        """Get realm's public key."""
        await self._ensure_connected()
        
        try:
            # Get realm's public key from certificates endpoint
            url = f"{self.server_url}/realms/{realm_name}/protocol/openid-connect/certs"
            
            response = await self._http_client.get(url)
            response.raise_for_status()
            
            certs_data = response.json()
            
            # Extract the first RSA key (usually the signing key)
            for key in certs_data.get("keys", []):
                if key.get("kty") == "RSA" and key.get("use") == "sig":
                    return key
            
            raise RealmConfigurationError(f"No RSA signing key found for realm {realm_name}")
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to get public key for realm {realm_name}: {e}")
            raise KeycloakConnectionError(f"Cannot get public key: {e}") from e
    
    async def get_realm_jwks(self, realm_name: str) -> Dict:
        """Get realm's JWKS (JSON Web Key Set)."""
        await self._ensure_connected()
        
        try:
            url = f"{self.server_url}/realms/{realm_name}/protocol/openid-connect/certs"
            
            response = await self._http_client.get(url)
            response.raise_for_status()
            
            return response.json()
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to get JWKS for realm {realm_name}: {e}")
            raise KeycloakConnectionError(f"Cannot get JWKS: {e}") from e
    
    async def get_realm_openid_configuration(self, realm_name: str) -> Dict:
        """Get realm's OpenID Connect configuration."""
        await self._ensure_connected()
        
        try:
            url = f"{self.server_url}/realms/{realm_name}/.well-known/openid-configuration"
            
            response = await self._http_client.get(url)
            response.raise_for_status()
            
            return response.json()
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to get OpenID configuration for realm {realm_name}: {e}")
            raise KeycloakConnectionError(f"Cannot get OpenID configuration: {e}") from e
    
    # User Management Operations
    
    async def create_user(
        self,
        realm_name: str,
        user_data: Dict,
    ) -> str:
        """Create a new user in the realm."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak for user operations
            user_id = await self._admin_client.a_create_user(user_data)
            logger.info(f"Created user {user_data.get('username')} in realm {realm_name}")
            return user_id
        
        except KeycloakError as e:
            logger.error(f"Failed to create user: {e}")
            raise RealmConfigurationError(f"Cannot create user: {e}") from e
        
        finally:
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm
    
    async def get_user_by_username(self, realm_name: str, username: str) -> Optional[Dict]:
        """Get user by username."""
        await self._ensure_connected()
        
        try:
            # Switch to target realm for this operation
            original_realm = self._admin_client.connection.realm_name
            self._admin_client.connection.realm_name = realm_name
            
            # Use async method to get users by username
            users = await self._admin_client.a_get_users({"username": username})
            
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm
            
            if users:
                return users[0]  # Username should be unique
            return None
        
        except KeycloakError as e:
            logger.error(f"Failed to get user {username}: {e}")
            return None
    
    async def get_user_by_email(self, realm_name: str, email: str) -> Optional[Dict]:
        """Get user by email."""
        await self._ensure_connected()
        
        try:
            # Switch to target realm for this operation
            original_realm = self._admin_client.connection.realm_name
            self._admin_client.connection.realm_name = realm_name
            
            # Use async method to get users by email
            users = await self._admin_client.a_get_users({"email": email})
            
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm
            
            if users:
                return users[0]  # Email should be unique
            return None
        
        except KeycloakError as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            return None
    
    async def update_user(self, realm_name: str, user_id: str, user_data: Dict) -> None:
        """Update user information."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak for user operations
            await self._admin_client.a_update_user(user_id, user_data)
            logger.info(f"Updated user {user_id} in realm {realm_name}")
        
        except KeycloakError as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise RealmConfigurationError(f"Cannot update user: {e}") from e
        
        finally:
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm
    
    async def set_user_password(
        self,
        realm_name: str,
        user_id: str,
        password: str,
        temporary: bool = False,
    ) -> None:
        """Set user password."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak for user operations
            await self._admin_client.a_set_user_password(user_id, password, temporary)
            logger.info(f"Set password for user {user_id} in realm {realm_name}")
        
        except KeycloakError as e:
            logger.error(f"Failed to set password for user {user_id}: {e}")
            raise RealmConfigurationError(f"Cannot set user password: {e}") from e
        
        finally:
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm
    
    async def send_user_email_verification(self, realm_name: str, user_id: str) -> None:
        """Send email verification to user."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak for user operations
            await self._admin_client.a_send_verify_email(user_id)
            logger.info(f"Sent email verification to user {user_id}")
        
        except KeycloakError as e:
            logger.error(f"Failed to send email verification to user {user_id}: {e}")
            raise RealmConfigurationError(f"Cannot send email verification: {e}") from e
        
        finally:
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm
    
    async def send_user_password_reset(self, realm_name: str, user_id: str) -> None:
        """Send password reset email to user."""
        await self._ensure_connected()
        
        try:
            # Switch to target realm for this operation
            original_realm = self._admin_client.connection.realm_name
            self._admin_client.connection.realm_name = realm_name
            
            # Use native async method from python-keycloak for user operations
            await self._admin_client.a_send_update_account(user_id, ["UPDATE_PASSWORD"])
            
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm
                
            logger.info(f"Sent password reset to user {user_id} in realm {realm_name}")
        
        except KeycloakError as e:
            logger.error(f"Failed to send password reset to user {user_id} in realm {realm_name}: {e}")
            raise RealmConfigurationError(f"Cannot send password reset: {e}") from e
    
    async def delete_user(self, realm_name: str, user_id: str) -> None:
        """Delete user from realm."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak for user operations  
            await self._admin_client.a_delete_user(user_id)
            logger.info(f"Deleted user {user_id} from realm {realm_name}")
        
        except KeycloakError as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise RealmConfigurationError(f"Cannot delete user: {e}") from e
        
        finally:
            # Restore original realm
            self._admin_client.connection.realm_name = original_realm    
    async def send_verify_email(self, realm_name: str, user_id: str) -> None:
        """Send email verification to user (alias for send_user_email_verification)."""
        await self.send_user_email_verification(realm_name, user_id)
    
    async def send_user_action_email(
        self, 
        realm_name: str, 
        user_id: str,
        actions: List[str],
        lifespan: int = 3600
    ) -> None:
        """Send user action email with specified actions."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak for user operations
            await self._admin_client.a_send_update_account(
                user_id=user_id,
                payload=actions,
                lifespan=lifespan
            )
            logger.info(f"Sent action email to user {user_id} with actions: {actions}")
        
        except KeycloakError as e:
            logger.error(f"Failed to send action email: {e}")
            raise RealmConfigurationError(f"Cannot send action email: {e}") from e
        
        finally:
            self._admin_client.realm_name = original_realm
    
    async def get_user_credentials(self, realm_name: str, user_id: str) -> List[Dict]:
        """Get user credentials."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak
            credentials = await self._admin_client.a_get_credentials(user_id=user_id)
            return credentials
        
        except KeycloakError as e:
            logger.error(f"Failed to get user credentials: {e}")
            raise RealmConfigurationError(f"Cannot get user credentials: {e}") from e
        
        finally:
            self._admin_client.realm_name = original_realm
    
    async def remove_user_totp(self, realm_name: str, user_id: str) -> None:
        """Remove TOTP from user."""
        await self._ensure_connected()
        
        # Get all credentials and remove TOTP ones
        credentials = await self.get_user_credentials(realm_name, user_id)
        
        for credential in credentials:
            if credential.get("type") == "otp":
                await self.delete_user_credential(realm_name, user_id, credential["id"])
                logger.info(f"Removed TOTP credential {credential['id']} from user {user_id}")
    
    async def delete_user_credential(self, realm_name: str, user_id: str, credential_id: str) -> None:
        """Delete a specific user credential."""
        await self._ensure_connected()
        
        # Switch to target realm
        original_realm = self._admin_client.connection.realm_name
        self._admin_client.connection.realm_name = realm_name
        
        try:
            # Use native async method from python-keycloak
            await self._admin_client.a_delete_credential(user_id=user_id, credential_id=credential_id)
            logger.info(f"Deleted credential {credential_id} from user {user_id}")
        
        except KeycloakError as e:
            logger.error(f"Failed to delete credential: {e}")
            raise RealmConfigurationError(f"Cannot delete credential: {e}") from e
        
        finally:
            self._admin_client.realm_name = original_realm
    
    async def logout_user(self, realm_name: str, user_id: str) -> None:
        """Logout all user sessions."""
        await self._ensure_connected()
        
        # Switch to target realm  
        original_realm = self._admin_client.realm_name
        self._admin_client.realm_name = realm_name
        
        try:
            # Get user sessions and logout each one
            sessions = await self._admin_client.a_get_sessions(user_id=user_id)
            
            for session in sessions:
                # Logout each session - this needs to be sync as there's no async version
                self._admin_client.delete_user_session(user_id=user_id, session_id=session["id"])
                logger.debug(f"Logged out session {session['id']} for user {user_id}")
            
            logger.info(f"Logged out all sessions for user {user_id}")
        
        except KeycloakError as e:
            logger.error(f"Failed to logout user: {e}")
            raise RealmConfigurationError(f"Cannot logout user: {e}") from e
        
        finally:
            self._admin_client.realm_name = original_realm