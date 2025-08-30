"""Keycloak token repository for authentication platform."""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone

from .....core.value_objects.identifiers import TenantId, UserId, KeycloakUserId
from ...core.value_objects import AccessToken, RefreshToken, RealmIdentifier
from ...core.entities import TokenMetadata
from ...core.exceptions import AuthenticationFailed, TokenExpired, InvalidSignature

logger = logging.getLogger(__name__)


class KeycloakTokenRepository:
    """Keycloak token repository following maximum separation principle.
    
    Handles ONLY Keycloak token operations for authentication platform.
    Does not handle user data storage, permission loading, or session management.
    """
    
    def __init__(self, keycloak_adapter_factory):
        """Initialize Keycloak token repository.
        
        Args:
            keycloak_adapter_factory: Factory to create Keycloak adapters for different realms
        """
        if not keycloak_adapter_factory:
            raise ValueError("Keycloak adapter factory is required")
        self.keycloak_adapter_factory = keycloak_adapter_factory
        self._adapters = {}  # Cache adapters per realm
    
    async def _get_adapter(self, realm_id: RealmIdentifier):
        """Get or create Keycloak adapter for realm.
        
        Args:
            realm_id: Realm identifier
            
        Returns:
            Keycloak adapter instance
        """
        realm_key = str(realm_id.value)
        
        if realm_key not in self._adapters:
            try:
                adapter = await self.keycloak_adapter_factory.create_adapter(realm_id)
                self._adapters[realm_key] = adapter
            except Exception as e:
                logger.error(f"Failed to create Keycloak adapter for realm {realm_id.value}: {e}")
                raise AuthenticationFailed(
                    "Failed to initialize Keycloak connection",
                    reason="adapter_creation_failed",
                    context={"realm_id": str(realm_id.value), "error": str(e)}
                )
        
        return self._adapters[realm_key]
    
    async def authenticate_user(
        self,
        username: str,
        password: str,
        realm_id: RealmIdentifier
    ) -> Dict[str, Any]:
        """Authenticate user and get tokens from Keycloak.
        
        Args:
            username: User's username
            password: User's password
            realm_id: Realm identifier
            
        Returns:
            Dictionary containing access_token, refresh_token, and token metadata
            
        Raises:
            AuthenticationFailed: If authentication fails
        """
        adapter = await self._get_adapter(realm_id)
        
        try:
            logger.info(f"Authenticating user {username} in realm {realm_id.value}")
            
            async with adapter:
                token_data = await adapter.authenticate(username, password)
            
            # Validate token_data structure
            if not isinstance(token_data, dict) or 'access_token' not in token_data:
                raise AuthenticationFailed(
                    "Invalid token response from Keycloak",
                    reason="invalid_token_response",
                    context={"realm_id": str(realm_id.value), "username": username}
                )
            
            logger.info(f"Successfully authenticated user {username} in realm {realm_id.value}")
            
            return {
                "access_token": token_data['access_token'],
                "refresh_token": token_data.get('refresh_token'),
                "expires_in": token_data.get('expires_in'),
                "token_type": token_data.get('token_type', 'Bearer'),
                "scope": token_data.get('scope'),
                "authenticated_at": datetime.now(timezone.utc)
            }
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to authenticate user {username} in realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Keycloak authentication failed",
                reason="keycloak_authentication_error",
                context={
                    "realm_id": str(realm_id.value),
                    "username": username,
                    "error": str(e)
                }
            )
    
    async def refresh_token(
        self,
        refresh_token: RefreshToken,
        realm_id: RealmIdentifier
    ) -> Dict[str, Any]:
        """Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token to use
            realm_id: Realm identifier
            
        Returns:
            Dictionary containing new access_token and refresh_token
            
        Raises:
            TokenExpired: If refresh token is expired
            AuthenticationFailed: If refresh fails
        """
        adapter = await self._get_adapter(realm_id)
        
        try:
            logger.debug(f"Refreshing token in realm {realm_id.value}")
            
            async with adapter:
                token_data = await adapter.refresh_token(str(refresh_token.value))
            
            if not isinstance(token_data, dict) or 'access_token' not in token_data:
                raise AuthenticationFailed(
                    "Invalid refresh response from Keycloak",
                    reason="invalid_refresh_response",
                    context={"realm_id": str(realm_id.value)}
                )
            
            logger.debug(f"Successfully refreshed token in realm {realm_id.value}")
            
            return {
                "access_token": token_data['access_token'],
                "refresh_token": token_data.get('refresh_token'),
                "expires_in": token_data.get('expires_in'),
                "token_type": token_data.get('token_type', 'Bearer'),
                "scope": token_data.get('scope'),
                "refreshed_at": datetime.now(timezone.utc)
            }
            
        except TokenExpired:
            # Re-raise token expired exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to refresh token in realm {realm_id.value}: {e}")
            
            # Check if it's a token expiry issue
            if "expired" in str(e).lower() or "invalid" in str(e).lower():
                raise TokenExpired(
                    "Refresh token is expired or invalid",
                    context={"realm_id": str(realm_id.value), "error": str(e)}
                )
            
            raise AuthenticationFailed(
                "Token refresh failed",
                reason="keycloak_refresh_error",
                context={"realm_id": str(realm_id.value), "error": str(e)}
            )
    
    async def revoke_token(
        self,
        token: AccessToken,
        realm_id: RealmIdentifier
    ) -> bool:
        """Revoke access token in Keycloak.
        
        Args:
            token: Access token to revoke
            realm_id: Realm identifier
            
        Returns:
            True if revocation was successful
        """
        adapter = await self._get_adapter(realm_id)
        
        try:
            logger.debug(f"Revoking token in realm {realm_id.value}")
            
            async with adapter:
                success = await adapter.revoke_token(str(token.value))
            
            if success:
                logger.debug(f"Successfully revoked token in realm {realm_id.value}")
            else:
                logger.warning(f"Token revocation returned false in realm {realm_id.value}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to revoke token in realm {realm_id.value}: {e}")
            # Don't raise exception for revocation failures - it's not critical
            return False
    
    async def introspect_token(
        self,
        token: AccessToken,
        realm_id: RealmIdentifier
    ) -> Dict[str, Any]:
        """Introspect token to get metadata from Keycloak.
        
        Args:
            token: Access token to introspect
            realm_id: Realm identifier
            
        Returns:
            Token introspection data
            
        Raises:
            AuthenticationFailed: If introspection fails
        """
        adapter = await self._get_adapter(realm_id)
        
        try:
            logger.debug(f"Introspecting token in realm {realm_id.value}")
            
            async with adapter:
                introspection_data = await adapter.introspect_token(str(token.value))
            
            if not isinstance(introspection_data, dict):
                raise AuthenticationFailed(
                    "Invalid introspection response from Keycloak",
                    reason="invalid_introspection_response",
                    context={"realm_id": str(realm_id.value)}
                )
            
            logger.debug(f"Successfully introspected token in realm {realm_id.value}")
            return introspection_data
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to introspect token in realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Token introspection failed",
                reason="keycloak_introspection_error",
                context={"realm_id": str(realm_id.value), "error": str(e)}
            )
    
    async def get_user_info(
        self,
        token: AccessToken,
        realm_id: RealmIdentifier
    ) -> Dict[str, Any]:
        """Get user information from Keycloak using access token.
        
        Args:
            token: Access token
            realm_id: Realm identifier
            
        Returns:
            User information dictionary
            
        Raises:
            AuthenticationFailed: If user info retrieval fails
        """
        adapter = await self._get_adapter(realm_id)
        
        try:
            logger.debug(f"Getting user info from realm {realm_id.value}")
            
            async with adapter:
                user_info = await adapter.get_user_info(str(token.value))
            
            if not isinstance(user_info, dict):
                raise AuthenticationFailed(
                    "Invalid user info response from Keycloak",
                    reason="invalid_user_info_response",
                    context={"realm_id": str(realm_id.value)}
                )
            
            logger.debug(f"Successfully retrieved user info from realm {realm_id.value}")
            return user_info
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get user info from realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "User info retrieval failed",
                reason="keycloak_userinfo_error",
                context={"realm_id": str(realm_id.value), "error": str(e)}
            )
    
    async def exchange_token(
        self,
        token: AccessToken,
        target_audience: str,
        realm_id: RealmIdentifier
    ) -> Dict[str, Any]:
        """Exchange token for different audience.
        
        Args:
            token: Current access token
            target_audience: Target audience for new token
            realm_id: Realm identifier
            
        Returns:
            Dictionary containing exchanged token data
            
        Raises:
            AuthenticationFailed: If token exchange fails
        """
        adapter = await self._get_adapter(realm_id)
        
        try:
            logger.debug(f"Exchanging token for audience {target_audience} in realm {realm_id.value}")
            
            async with adapter:
                exchange_data = await adapter.exchange_token(
                    str(token.value),
                    target_audience=target_audience
                )
            
            if not isinstance(exchange_data, dict) or 'access_token' not in exchange_data:
                raise AuthenticationFailed(
                    "Invalid token exchange response from Keycloak",
                    reason="invalid_exchange_response",
                    context={"realm_id": str(realm_id.value), "audience": target_audience}
                )
            
            logger.debug(f"Successfully exchanged token in realm {realm_id.value}")
            
            return {
                "access_token": exchange_data['access_token'],
                "token_type": exchange_data.get('token_type', 'Bearer'),
                "expires_in": exchange_data.get('expires_in'),
                "scope": exchange_data.get('scope'),
                "exchanged_at": datetime.now(timezone.utc),
                "target_audience": target_audience
            }
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to exchange token in realm {realm_id.value}: {e}")
            raise AuthenticationFailed(
                "Token exchange failed",
                reason="keycloak_exchange_error",
                context={
                    "realm_id": str(realm_id.value),
                    "audience": target_audience,
                    "error": str(e)
                }
            )
    
    async def logout_user(
        self,
        refresh_token: Optional[RefreshToken],
        realm_id: RealmIdentifier
    ) -> bool:
        """Logout user in Keycloak (end session).
        
        Args:
            refresh_token: Refresh token for logout (optional)
            realm_id: Realm identifier
            
        Returns:
            True if logout was successful
        """
        adapter = await self._get_adapter(realm_id)
        
        try:
            logger.debug(f"Logging out user in realm {realm_id.value}")
            
            async with adapter:
                if refresh_token:
                    success = await adapter.logout(str(refresh_token.value))
                else:
                    # Generic logout without token
                    success = await adapter.logout(None)
            
            if success:
                logger.debug(f"Successfully logged out user in realm {realm_id.value}")
            else:
                logger.warning(f"User logout returned false in realm {realm_id.value}")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to logout user in realm {realm_id.value}: {e}")
            # Don't raise exception for logout failures - it's not critical
            return False