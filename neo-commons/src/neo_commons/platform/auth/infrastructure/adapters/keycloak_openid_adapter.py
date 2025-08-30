"""Keycloak OpenID Connect adapter for authentication platform."""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from .....core.value_objects.identifiers import RealmId
from ...core.value_objects import AccessToken, RefreshToken, RealmIdentifier
from ...core.exceptions import AuthenticationFailed, TokenExpired, InvalidSignature

logger = logging.getLogger(__name__)


class KeycloakOpenIDAdapter:
    """Keycloak OpenID Connect adapter following maximum separation principle.
    
    Handles ONLY Keycloak OpenID Connect operations for authentication platform.
    Does not handle admin operations, caching, or token validation logic.
    """
    
    def __init__(self, keycloak_client):
        """Initialize Keycloak OpenID adapter.
        
        Args:
            keycloak_client: Keycloak OpenID client instance
        """
        if not keycloak_client:
            raise ValueError("Keycloak OpenID client is required")
        self.keycloak_client = keycloak_client
    
    async def __aenter__(self):
        """Async context manager entry."""
        # KeycloakOpenID client doesn't need explicit connection
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # KeycloakOpenID client doesn't need explicit cleanup
        pass
    
    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """Authenticate user and get tokens from Keycloak.
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            Dictionary containing access_token, refresh_token, and token metadata
            
        Raises:
            AuthenticationFailed: If authentication fails
        """
        try:
            logger.info(f"Authenticating user {username} via Keycloak OpenID")
            
            # Use Keycloak OpenID client for authentication
            token_data = await self.keycloak_client.a_token(username, password)
            
            # Validate token_data structure
            if not isinstance(token_data, dict) or 'access_token' not in token_data:
                raise AuthenticationFailed(
                    "Invalid token response from Keycloak",
                    reason="invalid_token_response",
                    context={"username": username}
                )
            
            logger.info(f"Successfully authenticated user {username} via Keycloak")
            
            return {
                "access_token": token_data['access_token'],
                "refresh_token": token_data.get('refresh_token'),
                "expires_in": token_data.get('expires_in'),
                "refresh_expires_in": token_data.get('refresh_expires_in'),
                "token_type": token_data.get('token_type', 'Bearer'),
                "scope": token_data.get('scope'),
                "authenticated_at": datetime.now(timezone.utc)
            }
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to authenticate user {username}: {e}")
            raise AuthenticationFailed(
                "Keycloak authentication failed",
                reason="keycloak_authentication_error",
                context={
                    "username": username,
                    "error": str(e)
                }
            )
    
    async def refresh_token(
        self,
        refresh_token: RefreshToken
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token to use
            
        Returns:
            Dictionary containing new access_token and refresh_token
            
        Raises:
            TokenExpired: If refresh token is expired
            AuthenticationFailed: If refresh fails
        """
        try:
            logger.debug("Refreshing token via Keycloak OpenID")
            
            # Use Keycloak OpenID client for token refresh
            token_data = await self.keycloak_client.a_refresh_token(str(refresh_token.value))
            
            if not isinstance(token_data, dict) or 'access_token' not in token_data:
                raise AuthenticationFailed(
                    "Invalid refresh response from Keycloak",
                    reason="invalid_refresh_response"
                )
            
            logger.debug("Successfully refreshed token via Keycloak")
            
            return {
                "access_token": token_data['access_token'],
                "refresh_token": token_data.get('refresh_token'),
                "expires_in": token_data.get('expires_in'),
                "refresh_expires_in": token_data.get('refresh_expires_in'),
                "token_type": token_data.get('token_type', 'Bearer'),
                "scope": token_data.get('scope'),
                "refreshed_at": datetime.now(timezone.utc)
            }
            
        except TokenExpired:
            # Re-raise token expired exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            
            # Check if it's a token expiry issue
            if "expired" in str(e).lower() or "invalid_grant" in str(e).lower():
                raise TokenExpired(
                    "Refresh token is expired or invalid",
                    context={"error": str(e)}
                )
            
            raise AuthenticationFailed(
                "Token refresh failed",
                reason="keycloak_refresh_error",
                context={"error": str(e)}
            )
    
    async def logout_user(
        self,
        refresh_token: Optional[RefreshToken] = None
    ) -> bool:
        """Logout user in Keycloak (end session).
        
        Args:
            refresh_token: Refresh token for logout (optional)
            
        Returns:
            True if logout was successful
        """
        try:
            logger.debug("Logging out user via Keycloak OpenID")
            
            if refresh_token:
                await self.keycloak_client.a_logout(str(refresh_token.value))
            else:
                # Generic logout without token
                await self.keycloak_client.a_logout(None)
            
            logger.debug("Successfully logged out user via Keycloak")
            return True
            
        except Exception as e:
            logger.error(f"Failed to logout user: {e}")
            # Don't raise exception for logout failures - it's not critical
            return False
    
    async def get_user_info(
        self,
        access_token: AccessToken
    ) -> Dict[str, Any]:
        """Get user information from Keycloak using access token.
        
        Args:
            access_token: Access token
            
        Returns:
            User information dictionary
            
        Raises:
            AuthenticationFailed: If user info retrieval fails
        """
        try:
            logger.debug("Getting user info via Keycloak OpenID")
            
            user_info = await self.keycloak_client.a_userinfo(str(access_token.value))
            
            if not isinstance(user_info, dict):
                raise AuthenticationFailed(
                    "Invalid user info response from Keycloak",
                    reason="invalid_user_info_response"
                )
            
            logger.debug("Successfully retrieved user info via Keycloak")
            return user_info
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise AuthenticationFailed(
                "User info retrieval failed",
                reason="keycloak_userinfo_error",
                context={"error": str(e)}
            )
    
    async def introspect_token(
        self,
        token: AccessToken
    ) -> Dict[str, Any]:
        """Introspect token to get metadata from Keycloak.
        
        Args:
            token: Access token to introspect
            
        Returns:
            Token introspection data
            
        Raises:
            AuthenticationFailed: If introspection fails
        """
        try:
            logger.debug("Introspecting token via Keycloak OpenID")
            
            introspection_data = await self.keycloak_client.a_introspect(str(token.value))
            
            if not isinstance(introspection_data, dict):
                raise AuthenticationFailed(
                    "Invalid introspection response from Keycloak",
                    reason="invalid_introspection_response"
                )
            
            logger.debug("Successfully introspected token via Keycloak")
            return introspection_data
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to introspect token: {e}")
            raise AuthenticationFailed(
                "Token introspection failed",
                reason="keycloak_introspection_error",
                context={"error": str(e)}
            )
    
    async def decode_token(
        self,
        token: AccessToken,
        validate: bool = True
    ) -> Dict[str, Any]:
        """Decode JWT token via Keycloak.
        
        Args:
            token: Access token to decode
            validate: Whether to validate the token
            
        Returns:
            Token claims dictionary
            
        Raises:
            InvalidSignature: If token signature is invalid
            TokenExpired: If token is expired
            AuthenticationFailed: If decode fails
        """
        try:
            logger.debug("Decoding token via Keycloak OpenID")
            
            claims = await self.keycloak_client.a_decode_token(
                str(token.value),
                validate=validate
            )
            
            if not isinstance(claims, dict):
                raise AuthenticationFailed(
                    "Invalid token decode response from Keycloak",
                    reason="invalid_decode_response"
                )
            
            logger.debug("Successfully decoded token via Keycloak")
            return claims
            
        except Exception as e:
            logger.warning(f"Token decode failed: {e}")
            error_str = str(e).lower()
            
            if "expired" in error_str:
                raise TokenExpired(
                    "Token has expired",
                    context={"error": str(e)}
                )
            elif "signature" in error_str:
                raise InvalidSignature(
                    "Token signature is invalid",
                    context={"error": str(e)}
                )
            else:
                raise AuthenticationFailed(
                    "Token decode failed",
                    reason="keycloak_decode_error",
                    context={"error": str(e)}
                )
    
    async def get_public_key(self) -> str:
        """Get realm's public key from Keycloak.
        
        Returns:
            Public key string
            
        Raises:
            AuthenticationFailed: If public key retrieval fails
        """
        try:
            logger.debug("Getting public key via Keycloak OpenID")
            
            public_key = await self.keycloak_client.a_public_key()
            
            if not isinstance(public_key, str) or not public_key.strip():
                raise AuthenticationFailed(
                    "Invalid public key response from Keycloak",
                    reason="invalid_public_key_response"
                )
            
            logger.debug("Successfully retrieved public key via Keycloak")
            return public_key
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get public key: {e}")
            raise AuthenticationFailed(
                "Public key retrieval failed",
                reason="keycloak_public_key_error",
                context={"error": str(e)}
            )
    
    async def get_well_known_configuration(self) -> Dict[str, Any]:
        """Get OpenID Connect well-known configuration from Keycloak.
        
        Returns:
            Well-known configuration dictionary
            
        Raises:
            AuthenticationFailed: If configuration retrieval fails
        """
        try:
            logger.debug("Getting well-known configuration via Keycloak OpenID")
            
            config = await self.keycloak_client.a_well_known()
            
            if not isinstance(config, dict):
                raise AuthenticationFailed(
                    "Invalid well-known config response from Keycloak",
                    reason="invalid_well_known_response"
                )
            
            logger.debug("Successfully retrieved well-known configuration via Keycloak")
            return config
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get well-known configuration: {e}")
            raise AuthenticationFailed(
                "Well-known configuration retrieval failed",
                reason="keycloak_well_known_error",
                context={"error": str(e)}
            )
    
    async def exchange_token(
        self,
        token: AccessToken,
        target_client_id: str,
        target_audience: str,
        subject: Optional[str] = None
    ) -> Dict[str, Any]:
        """Exchange token for different client/audience.
        
        Args:
            token: Current access token
            target_client_id: Target client ID
            target_audience: Target audience for new token
            subject: Optional subject for new token
            
        Returns:
            Dictionary containing exchanged token data
            
        Raises:
            AuthenticationFailed: If token exchange fails
        """
        try:
            logger.debug(f"Exchanging token for client {target_client_id} and audience {target_audience}")
            
            exchange_data = await self.keycloak_client.a_exchange_token(
                str(token.value),
                target_client_id,
                target_audience,
                subject
            )
            
            if not isinstance(exchange_data, dict) or 'access_token' not in exchange_data:
                raise AuthenticationFailed(
                    "Invalid token exchange response from Keycloak",
                    reason="invalid_exchange_response",
                    context={
                        "client_id": target_client_id, 
                        "audience": target_audience
                    }
                )
            
            logger.debug(f"Successfully exchanged token for client {target_client_id}")
            
            return {
                "access_token": exchange_data['access_token'],
                "token_type": exchange_data.get('token_type', 'Bearer'),
                "expires_in": exchange_data.get('expires_in'),
                "scope": exchange_data.get('scope'),
                "exchanged_at": datetime.now(timezone.utc),
                "target_client_id": target_client_id,
                "target_audience": target_audience
            }
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to exchange token: {e}")
            raise AuthenticationFailed(
                "Token exchange failed",
                reason="keycloak_exchange_error",
                context={
                    "client_id": target_client_id,
                    "audience": target_audience,
                    "error": str(e)
                }
            )