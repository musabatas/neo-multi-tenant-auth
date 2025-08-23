"""Keycloak OpenID Connect adapter."""

import logging
from typing import Dict, Optional

from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakAuthenticationError, KeycloakError

from ....core.exceptions.auth import (
    InvalidCredentialsError,
    InvalidTokenError,
    KeycloakConnectionError,
    TokenExpiredError,
)
from ....core.value_objects.identifiers import RealmId
from ..entities.jwt_token import JWTToken
from ..entities.keycloak_config import KeycloakConfig

logger = logging.getLogger(__name__)


class KeycloakOpenIDAdapter:
    """Adapter for Keycloak OpenID Connect operations."""
    
    def __init__(self, config: KeycloakConfig):
        """Initialize Keycloak OpenID adapter."""
        # Normalize server URL for Keycloak v18+ compatibility
        normalized_config = self._normalize_config(config)
        self.config = normalized_config
        self._openid_client: Optional[KeycloakOpenID] = None
    
    def _normalize_config(self, config: KeycloakConfig) -> KeycloakConfig:
        """Normalize Keycloak configuration for v18+ compatibility."""
        from ..entities.keycloak_config import KeycloakConfig
        
        server_url = config.server_url.rstrip('/')
        
        if server_url.endswith('/auth'):
            server_url = server_url[:-5]  # Remove '/auth'
            logger.info(f"Removed /auth suffix for Keycloak v18+ compatibility: {server_url}")
        
        # Create new config with normalized server URL
        return KeycloakConfig(
            server_url=server_url,
            realm_name=config.realm_name,
            client_id=config.client_id,
            realm_id=config.realm_id,
            tenant_id=config.tenant_id,
            client_secret=config.client_secret,
            verify_signature=config.verify_signature,
            verify_audience=config.verify_audience,
            verify_exp=config.verify_exp,
            verify_nbf=config.verify_nbf,
            verify_iat=config.verify_iat,
            algorithms=config.algorithms,
            audience=config.audience,
            require_https=config.require_https,
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_connected()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # KeycloakOpenID doesn't need explicit closing
        pass
    
    async def _ensure_connected(self) -> None:
        """Ensure OpenID client is initialized."""
        if self._openid_client is None:
            try:
                self._openid_client = KeycloakOpenID(
                    server_url=self.config.server_url,
                    client_id=self.config.client_id,
                    realm_name=self.config.realm_name,
                    client_secret_key=self.config.client_secret,
                    verify=self.config.require_https,
                )
                
                logger.info(f"Initialized OpenID client for realm: {self.config.realm_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize Keycloak OpenID client: {e}")
                raise KeycloakConnectionError(f"Cannot initialize OpenID client: {e}") from e
    
    async def authenticate(self, username: str, password: str) -> JWTToken:
        """Authenticate user with username/password."""
        await self._ensure_connected()
        
        try:
            token_response = self._openid_client.token(username, password)
            
            logger.info(f"Successfully authenticated user: {username}")
            return JWTToken.from_keycloak_response(token_response)
        
        except KeycloakAuthenticationError as e:
            logger.warning(f"Authentication failed for user {username}: {e}")
            raise InvalidCredentialsError("Invalid username or password") from e
        
        except KeycloakError as e:
            logger.error(f"Keycloak error during authentication: {e}")
            raise KeycloakConnectionError(f"Authentication service error: {e}") from e
    
    async def refresh_token(self, refresh_token: str) -> JWTToken:
        """Refresh an access token using refresh token."""
        await self._ensure_connected()
        
        try:
            token_response = self._openid_client.refresh_token(refresh_token)
            
            logger.info("Successfully refreshed access token")
            return JWTToken.from_keycloak_response(token_response)
        
        except KeycloakAuthenticationError as e:
            logger.warning(f"Token refresh failed: {e}")
            if "invalid_grant" in str(e).lower():
                raise TokenExpiredError("Refresh token expired or invalid") from e
            raise InvalidTokenError("Invalid refresh token") from e
        
        except KeycloakError as e:
            logger.error(f"Keycloak error during token refresh: {e}")
            raise KeycloakConnectionError(f"Token refresh service error: {e}") from e
    
    async def logout(self, refresh_token: str) -> None:
        """Logout user and invalidate tokens."""
        await self._ensure_connected()
        
        try:
            self._openid_client.logout(refresh_token)
            logger.info("Successfully logged out user")
        
        except KeycloakError as e:
            # Don't fail logout on token errors - token might already be invalid
            logger.warning(f"Logout completed with warning: {e}")
    
    async def get_user_info(self, access_token: str) -> Dict:
        """Get user information from access token."""
        await self._ensure_connected()
        
        try:
            user_info = self._openid_client.userinfo(access_token)
            logger.debug("Successfully retrieved user info")
            return user_info
        
        except KeycloakAuthenticationError as e:
            logger.warning(f"Failed to get user info: {e}")
            if "invalid_token" in str(e).lower():
                raise InvalidTokenError("Access token is invalid") from e
            if "token expired" in str(e).lower():
                raise TokenExpiredError("Access token has expired") from e
            raise InvalidTokenError("Token validation failed") from e
        
        except KeycloakError as e:
            logger.error(f"Keycloak error getting user info: {e}")
            raise KeycloakConnectionError(f"User info service error: {e}") from e
    
    async def introspect_token(self, token: str) -> Dict:
        """Introspect token to get detailed metadata."""
        await self._ensure_connected()
        
        try:
            introspection = self._openid_client.introspect(token)
            logger.debug("Successfully introspected token")
            return introspection
        
        except KeycloakError as e:
            logger.error(f"Token introspection failed: {e}")
            raise KeycloakConnectionError(f"Token introspection service error: {e}") from e
    
    async def decode_token(
        self, 
        token: str, 
        validate: bool = True,
        audience: Optional[str] = None,
    ) -> Dict:
        """Decode JWT token and optionally validate."""
        await self._ensure_connected()
        
        try:
            options = {
                "verify_signature": validate and self.config.verify_signature,
                "verify_aud": validate and self.config.verify_audience,
                "verify_exp": validate and self.config.verify_exp,
                "verify_nbf": validate and self.config.verify_nbf,
                "verify_iat": validate and self.config.verify_iat,
            }
            
            # Get public key for validation
            public_key = None
            if validate and self.config.verify_signature:
                public_key = self._openid_client.public_key()
            
            claims = self._openid_client.decode_token(
                token,
                key=public_key,
                options=options,
                audience=audience or self.config.audience,
                algorithms=self.config.algorithms,
            )
            
            logger.debug("Successfully decoded token")
            return claims
        
        except Exception as e:
            logger.warning(f"Token decode failed: {e}")
            if "expired" in str(e).lower():
                raise TokenExpiredError("Token has expired") from e
            if "invalid" in str(e).lower():
                raise InvalidTokenError("Token is invalid") from e
            raise InvalidTokenError(f"Token decode failed: {e}") from e
    
    async def get_public_key(self) -> str:
        """Get realm's public key."""
        await self._ensure_connected()
        
        try:
            public_key = self._openid_client.public_key()
            logger.debug(f"Retrieved public key for realm: {self.config.realm_name}")
            return public_key
        
        except KeycloakError as e:
            logger.error(f"Failed to get public key: {e}")
            raise KeycloakConnectionError(f"Public key retrieval failed: {e}") from e
    
    async def get_well_known_configuration(self) -> Dict:
        """Get OpenID Connect well-known configuration."""
        await self._ensure_connected()
        
        try:
            config = self._openid_client.well_known()
            logger.debug(f"Retrieved well-known config for realm: {self.config.realm_name}")
            return config
        
        except KeycloakError as e:
            logger.error(f"Failed to get well-known configuration: {e}")
            raise KeycloakConnectionError(f"Well-known config retrieval failed: {e}") from e
    
    async def exchange_token(
        self,
        token: str,
        audience: str,
        subject_token_type: str = "urn:ietf:params:oauth:token-type:access_token",
    ) -> JWTToken:
        """Exchange token for another token (token exchange flow)."""
        await self._ensure_connected()
        
        try:
            token_response = self._openid_client.exchange_token(
                token=token,
                audience=audience,
                subject_token_type=subject_token_type,
            )
            
            logger.info(f"Successfully exchanged token for audience: {audience}")
            return JWTToken.from_keycloak_response(token_response)
        
        except KeycloakError as e:
            logger.error(f"Token exchange failed: {e}")
            raise KeycloakConnectionError(f"Token exchange failed: {e}") from e