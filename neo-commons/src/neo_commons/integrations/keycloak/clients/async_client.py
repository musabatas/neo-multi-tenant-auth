"""
Enhanced async Keycloak client with protocol-based dependency injection.

Streamlined client that combines all Keycloak operations in a single interface.
"""
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from ..protocols.protocols import (
    KeycloakConfigProtocol, 
    HttpClientProtocol,
    KeycloakTokenProtocol,
    KeycloakUserProtocol,
    KeycloakRealmProtocol,
    KeycloakAdminProtocol
)
from ..config.config import DefaultKeycloakConfig, HttpxHttpClient
from ..operations.token_operations import KeycloakTokenOperations
from ..operations.user_operations import KeycloakUserOperations
from ..operations.realm_operations import KeycloakRealmOperations
from ..operations.admin_operations import KeycloakAdminOperations

logger = logging.getLogger(__name__)


class EnhancedKeycloakAsyncClient:
    """
    Enhanced async Keycloak client with comprehensive functionality.
    
    Combines token, user, realm, and admin operations in a single interface
    while maintaining clean architecture through composition.
    """
    
    def __init__(
        self,
        config: Optional[KeycloakConfigProtocol] = None,
        http_client: Optional[HttpClientProtocol] = None,
        enable_caching: bool = True,
        cache_ttl_seconds: int = 3600,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize enhanced Keycloak client.
        
        Args:
            config: Keycloak configuration provider
            http_client: HTTP client implementation
            enable_caching: Whether to enable token caching
            cache_ttl_seconds: Cache TTL in seconds
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
        """
        # Use defaults if not provided
        self.config = config or DefaultKeycloakConfig()
        self.http_client = http_client or HttpxHttpClient(
            timeout=self.config.connection_timeout,
            max_connections=self.config.max_connections,
            verify_ssl=self.config.verify_ssl
        )
        
        # Initialize operation components
        common_kwargs = {
            'config': self.config,
            'http_client': self.http_client,
            'enable_caching': enable_caching,
            'cache_ttl_seconds': cache_ttl_seconds,
            'max_retries': max_retries,
            'retry_delay': retry_delay
        }
        
        self._token_ops = KeycloakTokenOperations(**common_kwargs)
        self._user_ops = KeycloakUserOperations(**common_kwargs)
        self._realm_ops = KeycloakRealmOperations(**common_kwargs)
        self._admin_ops = KeycloakAdminOperations(**common_kwargs)
        
        self._is_closed = False
        
        logger.info("EnhancedKeycloakAsyncClient initialized with all operation modules")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def close(self):
        """Close the client and clean up resources."""
        if not self._is_closed:
            logger.info("Closing EnhancedKeycloakAsyncClient...")
            
            # Close all operation components
            await self._token_ops.close()
            await self._user_ops.close()
            await self._realm_ops.close()
            await self._admin_ops.close()
            
            self._is_closed = True
            logger.info("EnhancedKeycloakAsyncClient closed")
    
    # Token Operations - Delegate to token_ops
    async def authenticate(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate user and get tokens."""
        return await self._token_ops.authenticate(username, password, realm, client_id)
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Introspect token validity."""
        return await self._token_ops.introspect_token(token, realm)
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refresh access token."""
        return await self._token_ops.refresh_token(refresh_token, realm)
    
    async def logout(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> bool:
        """Logout user."""
        return await self._token_ops.logout(refresh_token, realm)
    
    async def get_userinfo(
        self,
        access_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user information from access token."""
        return await self._token_ops.get_userinfo(access_token, realm)
    
    async def decode_token(
        self,
        token: str,
        realm: Optional[str] = None,
        validate: bool = True
    ) -> Dict[str, Any]:
        """Decode and optionally validate JWT token."""
        return await self._token_ops.decode_token(token, realm, validate)
    
    # User Operations - Delegate to user_ops
    async def get_user_by_username(
        self,
        username: str,
        realm: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        return await self._user_ops.get_user_by_username(username, realm)
    
    async def create_or_update_user(
        self,
        user_data: Dict[str, Any],
        realm: Optional[str] = None,
        update_if_exists: bool = True
    ) -> Dict[str, Any]:
        """Create or update user."""
        return await self._user_ops.create_or_update_user(user_data, realm, update_if_exists)
    
    async def set_user_password(
        self,
        user_id: str,
        password: str,
        realm: Optional[str] = None,
        temporary: bool = False
    ) -> bool:
        """Set user password."""
        return await self._user_ops.set_user_password(user_id, password, realm, temporary)
    
    async def get_user_roles(
        self,
        user_id: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user roles."""
        return await self._user_ops.get_user_roles(user_id, realm)
    
    async def assign_user_role(
        self,
        user_id: str,
        role_name: str,
        realm: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> bool:
        """Assign role to user."""
        return await self._user_ops.assign_user_role(user_id, role_name, realm, client_id)
    
    # Realm Operations - Delegate to realm_ops
    async def create_realm(
        self,
        realm_name: str,
        realm_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new realm."""
        return await self._realm_ops.create_realm(realm_name, realm_config)
    
    async def get_realm_public_key(
        self,
        realm: str
    ) -> str:
        """Get realm public key for token validation."""
        return await self._realm_ops.get_realm_public_key(realm)
    
    async def get_realm_info(
        self,
        realm: str
    ) -> Dict[str, Any]:
        """Get realm information."""
        return await self._realm_ops.get_realm_info(realm)
    
    async def update_realm_config(
        self,
        realm: str,
        config_updates: Dict[str, Any]
    ) -> bool:
        """Update realm configuration."""
        return await self._realm_ops.update_realm_config(realm, config_updates)
    
    async def list_realms(self) -> List[Dict[str, Any]]:
        """List all realms."""
        return await self._realm_ops.list_realms()
    
    async def delete_realm(
        self,
        realm: str
    ) -> bool:
        """Delete a realm."""
        return await self._realm_ops.delete_realm(realm)
    
    # Admin Operations - Delegate to admin_ops
    async def health_check(self) -> Dict[str, Any]:
        """Check Keycloak health."""
        return await self._admin_ops.health_check()
    
    async def get_client_statistics(self) -> Dict[str, Any]:
        """Get client statistics."""
        return await self._admin_ops.get_client_statistics()
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get Keycloak server information."""
        return await self._admin_ops.get_server_info()
    
    async def get_realm_statistics(
        self,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get realm-specific statistics."""
        return await self._admin_ops.get_realm_statistics(realm)
    
    async def clear_cache(self, cache_type: Optional[str] = None) -> bool:
        """Clear client cache."""
        return await self._admin_ops.clear_cache(cache_type)
    
    async def clear_realm_cache(
        self,
        realm: Optional[str] = None
    ) -> bool:
        """Clear Keycloak realm cache."""
        return await self._admin_ops.clear_realm_cache(realm)
    
    async def clear_user_cache(
        self,
        realm: Optional[str] = None
    ) -> bool:
        """Clear Keycloak user cache."""
        return await self._admin_ops.clear_user_cache(realm)
    
    async def export_realm(
        self,
        realm: str,
        include_users: bool = False,
        include_clients: bool = True,
        include_roles: bool = True
    ) -> Dict[str, Any]:
        """Export realm configuration."""
        return await self._admin_ops.export_realm(realm, include_users, include_clients, include_roles)


# Factory functions and utilities
def create_keycloak_client(
    server_url: Optional[str] = None,
    admin_realm: Optional[str] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    admin_username: Optional[str] = None,
    admin_password: Optional[str] = None,
    **kwargs
) -> EnhancedKeycloakAsyncClient:
    """
    Create a Keycloak client with explicit configuration.
    
    This factory function provides a convenient way to create a client
    with explicit parameters instead of relying on environment variables.
    """
    config = DefaultKeycloakConfig(
        server_url=server_url,
        admin_realm=admin_realm,
        client_id=client_id,
        client_secret=client_secret,
        admin_username=admin_username,
        admin_password=admin_password
    )
    
    return EnhancedKeycloakAsyncClient(config=config, **kwargs)


@asynccontextmanager
async def keycloak_client_context(**config_overrides):
    """
    Async context manager for Keycloak client lifecycle management.
    
    Usage:
        async with keycloak_client_context(server_url="...") as client:
            result = await client.authenticate("user", "pass")
    """
    client = create_keycloak_client(**config_overrides)
    try:
        yield client
    finally:
        await client.close()


# Global client instance management
_global_keycloak_client: Optional[EnhancedKeycloakAsyncClient] = None


def get_global_keycloak_client(**config_overrides) -> EnhancedKeycloakAsyncClient:
    """
    Get or create global Keycloak client instance.
    
    This provides a singleton pattern for applications that need
    a single shared client instance.
    """
    global _global_keycloak_client
    if _global_keycloak_client is None:
        _global_keycloak_client = create_keycloak_client(**config_overrides)
        logger.info("Global Keycloak client created")
    return _global_keycloak_client


async def reset_global_client():
    """Reset global client instance (useful for testing)."""
    global _global_keycloak_client
    if _global_keycloak_client:
        await _global_keycloak_client.close()
        _global_keycloak_client = None
        logger.info("Global Keycloak client reset")


# Convenience functions
async def quick_authenticate(
    username: str,
    password: str,
    realm: Optional[str] = None,
    **config_overrides
) -> Dict[str, Any]:
    """Quick authentication without managing client lifecycle."""
    async with keycloak_client_context(**config_overrides) as client:
        return await client.authenticate(username, password, realm)


async def quick_token_validation(
    token: str,
    realm: Optional[str] = None,
    **config_overrides
) -> Dict[str, Any]:
    """Quick token validation without managing client lifecycle."""
    async with keycloak_client_context(**config_overrides) as client:
        return await client.introspect_token(token, realm)


async def quick_user_info(
    access_token: str,
    realm: Optional[str] = None,
    **config_overrides
) -> Dict[str, Any]:
    """Quick user info retrieval without managing client lifecycle."""
    async with keycloak_client_context(**config_overrides) as client:
        return await client.get_userinfo(access_token, realm)