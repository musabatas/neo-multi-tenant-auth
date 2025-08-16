"""
Keycloak client for authentication and user management.
"""
from typing import Optional, Dict, Any, List
import httpx
from loguru import logger
from jose import jwt, JWTError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

from src.common.config.settings import settings
from src.common.exceptions.base import (
    ExternalServiceError,
    UnauthorizedError,
    NotFoundError
)


class KeycloakClient:
    """Client for interacting with Keycloak."""
    
    def __init__(self):
        self.base_url = str(settings.keycloak_url)
        self.admin_realm = settings.keycloak_admin_realm
        self.client_id = settings.keycloak_admin_client_id
        self.client_secret = settings.keycloak_admin_client_secret.get_secret_value()
        self.admin_username = settings.keycloak_admin_username
        self.admin_password = settings.keycloak_admin_password.get_secret_value()
        self._admin_token: Optional[str] = None
        self._public_key: Optional[str] = None
        
    async def _get_admin_token(self) -> str:
        """Get admin access token for Keycloak API."""
        if self._admin_token:
            # TODO: Check token expiry
            return self._admin_token
        
        token_url = f"{self.base_url}/realms/master/protocol/openid-connect/token"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "password",
                        "client_id": "admin-cli",
                        "username": self.admin_username,
                        "password": self.admin_password
                    }
                )
                response.raise_for_status()
                data = response.json()
                self._admin_token = data["access_token"]
                return self._admin_token
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to get Keycloak admin token: {e}")
                raise ExternalServiceError(
                    message="Failed to authenticate with Keycloak",
                    service="Keycloak"
                )
    
    async def get_realm_public_key(self, realm: str) -> str:
        """Get public key for a realm."""
        if self._public_key:
            return self._public_key
        
        url = f"{self.base_url}/realms/{realm}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                # Format the public key
                public_key = data.get("public_key", "")
                formatted_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
                self._public_key = formatted_key
                return formatted_key
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to get realm public key: {e}")
                raise ExternalServiceError(
                    message="Failed to get realm public key",
                    service="Keycloak"
                )
    
    async def validate_token(self, token: str, realm: str) -> Dict[str, Any]:
        """Validate JWT token and return decoded claims."""
        try:
            # Get public key for the realm
            public_key = await self.get_realm_public_key(realm)
            
            # Decode and validate the token
            decode_kwargs = {
                "key": public_key,
                "algorithms": [settings.jwt_algorithm],
                "issuer": f"{self.base_url}/realms/{realm}"
            }
            
            # Add audience if verification is enabled
            if settings.jwt_verify_audience:
                decode_kwargs["audience"] = settings.jwt_audience
            
            try:
                decoded = jwt.decode(token, **decode_kwargs)
            except JWTError as e:
                if "Invalid audience" in str(e) and settings.jwt_audience_fallback:
                    # Fallback: Try without audience validation
                    logger.warning(f"Audience validation failed, trying without audience verification: {e}")
                    decode_kwargs.pop("audience", None)
                    # Disable audience verification in options
                    jwt_options = {"verify_aud": False}
                    decode_kwargs["options"] = jwt_options
                    try:
                        decoded = jwt.decode(token, **decode_kwargs)
                        
                        # Log for debugging
                        if settings.jwt_debug_claims:
                            token_aud = decoded.get('aud', 'not_present')
                            logger.debug(f"Token audience: {token_aud}, Expected: {settings.jwt_audience}")
                    except JWTError as fallback_error:
                        # Log the actual token claims for debugging issuer mismatch
                        logger.error(f"Fallback validation also failed: {fallback_error}")
                        logger.error(f"Expected issuer: {decode_kwargs.get('issuer')}")
                        
                        # Try to decode without verification to see actual claims
                        try:
                            unverified_claims = jwt.decode(token, options={"verify_signature": False, "verify_aud": False, "verify_iss": False})
                            logger.error(f"Actual token issuer: {unverified_claims.get('iss', 'not_present')}")
                            logger.error(f"Actual token audience: {unverified_claims.get('aud', 'not_present')}")
                        except Exception as debug_error:
                            logger.error(f"Could not decode token for debugging: {debug_error}")
                        raise fallback_error
                else:
                    raise
            
            return decoded
            
        except JWTError as e:
            if "expired" in str(e).lower():
                raise UnauthorizedError("Token has expired")
            logger.error(f"Invalid token: {e}")
            raise UnauthorizedError("Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise UnauthorizedError("Token validation failed")
    
    async def create_realm(self, realm_name: str, display_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new realm."""
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms"
        
        realm_data = {
            "realm": realm_name,
            "enabled": True,
            "displayName": display_name or realm_name,
            "sslRequired": "external",
            "bruteForceProtected": True,
            "passwordPolicy": "length(8) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)",
            "duplicateEmailsAllowed": False,
            "loginTheme": "keycloak",
            "adminTheme": "keycloak",
            "emailTheme": "keycloak",
            "internationalizationEnabled": True,
            "supportedLocales": ["en"],
            "defaultLocale": "en"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=realm_data,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 201:
                    logger.info(f"Created realm: {realm_name}")
                    return realm_data
                elif response.status_code == 409:
                    logger.warning(f"Realm {realm_name} already exists")
                    return realm_data
                else:
                    response.raise_for_status()
                    
            except httpx.HTTPError as e:
                logger.error(f"Failed to create realm {realm_name}: {e}")
                raise ExternalServiceError(
                    message=f"Failed to create realm {realm_name}",
                    service="Keycloak"
                )
    
    async def create_client(
        self, 
        realm: str, 
        client_id: str,
        client_name: Optional[str] = None,
        redirect_uris: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a client in a realm."""
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/clients"
        
        client_data = {
            "clientId": client_id,
            "name": client_name or client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "serviceAccountsEnabled": True,
            "authorizationServicesEnabled": False,
            "redirectUris": redirect_uris or ["*"],
            "webOrigins": ["*"],
            "attributes": {
                "saml.force.post.binding": "false",
                "saml.multivalued.roles": "false",
                "oauth2.device.authorization.grant.enabled": "false",
                "oidc.ciba.grant.enabled": "false"
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=client_data,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 201:
                    logger.info(f"Created client {client_id} in realm {realm}")
                    
                    # Get the created client details
                    location = response.headers.get("Location")
                    if location:
                        client_response = await client.get(
                            location,
                            headers={"Authorization": f"Bearer {admin_token}"}
                        )
                        return client_response.json()
                    return client_data
                    
                elif response.status_code == 409:
                    logger.warning(f"Client {client_id} already exists in realm {realm}")
                    return client_data
                else:
                    response.raise_for_status()
                    
            except httpx.HTTPError as e:
                logger.error(f"Failed to create client {client_id}: {e}")
                raise ExternalServiceError(
                    message=f"Failed to create client {client_id}",
                    service="Keycloak"
                )
    
    async def create_user(
        self,
        realm: str,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        password: Optional[str] = None,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """Create a user in a realm."""
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users"
        
        user_data = {
            "username": username,
            "email": email,
            "firstName": first_name or "",
            "lastName": last_name or "",
            "enabled": enabled,
            "emailVerified": False,
            "credentials": []
        }
        
        if password:
            user_data["credentials"] = [{
                "type": "password",
                "value": password,
                "temporary": False
            }]
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=user_data,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 201:
                    logger.info(f"Created user {username} in realm {realm}")
                    
                    # Get the created user ID from Location header
                    location = response.headers.get("Location")
                    if location:
                        user_id = location.split("/")[-1]
                        user_data["id"] = user_id
                    return user_data
                    
                elif response.status_code == 409:
                    logger.warning(f"User {username} already exists in realm {realm}")
                    return user_data
                else:
                    response.raise_for_status()
                    
            except httpx.HTTPError as e:
                logger.error(f"Failed to create user {username}: {e}")
                raise ExternalServiceError(
                    message=f"Failed to create user {username}",
                    service="Keycloak"
                )
    
    async def get_user(self, realm: str, user_id: str) -> Dict[str, Any]:
        """Get user details by ID."""
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users/{user_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 404:
                    raise NotFoundError("User", user_id)
                    
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to get user {user_id}: {e}")
                raise ExternalServiceError(
                    message=f"Failed to get user {user_id}",
                    service="Keycloak"
                )
    
    async def get_user_by_username(self, realm: str, username: str) -> Optional[Dict[str, Any]]:
        """Get user details by username."""
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    params={"username": username, "exact": "true"},
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                response.raise_for_status()
                users = response.json()
                
                if users:
                    return users[0]
                return None
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to get user by username {username}: {e}")
                raise ExternalServiceError(
                    message=f"Failed to get user {username}",
                    service="Keycloak"
                )
    
    async def update_user(
        self,
        realm: str,
        user_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user details."""
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users/{user_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.put(
                    url,
                    json=updates,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 404:
                    raise NotFoundError("User", user_id)
                    
                response.raise_for_status()
                logger.info(f"Updated user {user_id} in realm {realm}")
                return updates
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to update user {user_id}: {e}")
                raise ExternalServiceError(
                    message=f"Failed to update user {user_id}",
                    service="Keycloak"
                )
    
    async def delete_user(self, realm: str, user_id: str) -> bool:
        """Delete a user."""
        admin_token = await self._get_admin_token()
        url = f"{self.base_url}/admin/realms/{realm}/users/{user_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.delete(
                    url,
                    headers={"Authorization": f"Bearer {admin_token}"}
                )
                
                if response.status_code == 404:
                    raise NotFoundError("User", user_id)
                    
                response.raise_for_status()
                logger.info(f"Deleted user {user_id} from realm {realm}")
                return True
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to delete user {user_id}: {e}")
                raise ExternalServiceError(
                    message=f"Failed to delete user {user_id}",
                    service="Keycloak"
                )
    
    async def authenticate(
        self,
        realm: str,
        username: str,
        password: str,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate a user and get tokens."""
        token_url = f"{self.base_url}/realms/{realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "password",
            "username": username,
            "password": password,
            "client_id": client_id or self.client_id
        }
        
        if client_id == self.client_id:
            data["client_secret"] = self.client_secret
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)
                
                if response.status_code == 401:
                    raise UnauthorizedError("Invalid username or password")
                    
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"Authentication failed: {e}")
                raise UnauthorizedError("Authentication failed")
    
    async def refresh_token(self, realm: str, refresh_token: str) -> Dict[str, Any]:
        """Refresh an access token."""
        token_url = f"{self.base_url}/realms/{realm}/protocol/openid-connect/token"
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(token_url, data=data)
                
                if response.status_code == 401:
                    raise UnauthorizedError("Invalid or expired refresh token")
                    
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPError as e:
                logger.error(f"Token refresh failed: {e}")
                raise UnauthorizedError("Token refresh failed")
    
    async def logout(self, realm: str, refresh_token: str) -> bool:
        """Logout a user session."""
        logout_url = f"{self.base_url}/realms/{realm}/protocol/openid-connect/logout"
        
        data = {
            "refresh_token": refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(logout_url, data=data)
                response.raise_for_status()
                return True
                
            except httpx.HTTPError as e:
                logger.error(f"Logout failed: {e}")
                # Logout failures are not critical
                return False


# Global Keycloak client instance
_keycloak_client: Optional[KeycloakClient] = None


def get_keycloak_client() -> KeycloakClient:
    """Get the global Keycloak client instance."""
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakClient()
    return _keycloak_client