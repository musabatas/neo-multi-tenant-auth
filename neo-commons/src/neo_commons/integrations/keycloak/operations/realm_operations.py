"""
Realm management operations for Keycloak integration.

Handles realm creation, configuration, and realm-related operations.
"""
import logging
from typing import Optional, Dict, Any

from ..protocols.protocols import KeycloakRealmProtocol
from ..clients.base_client import BaseKeycloakClient

logger = logging.getLogger(__name__)


class KeycloakRealmOperations(BaseKeycloakClient, KeycloakRealmProtocol):
    """Realm management operations implementation for Keycloak."""
    
    async def create_realm(
        self,
        realm_name: str,
        realm_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new realm.
        
        Args:
            realm_name: Name of the realm to create
            realm_config: Optional realm configuration
            
        Returns:
            Creation result with realm information
        """
        logger.info(f"Creating realm {realm_name}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Default realm configuration
            default_config = {
                "realm": realm_name,
                "displayName": realm_name.title(),
                "enabled": True,
                "sslRequired": "external",
                "registrationAllowed": False,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "editUsernameAllowed": False,
                "bruteForceProtected": True,
                "passwordPolicy": "length(8) and digits(1) and lowerCase(1) and upperCase(1)",
                "defaultLocale": "en",
                "internationalizationEnabled": True,
                "supportedLocales": ["en", "es", "fr", "de"],
                "loginTheme": "keycloak",
                "accountTheme": "keycloak",
                "adminTheme": "keycloak",
                "emailTheme": "keycloak"
            }
            
            # Merge with custom config if provided
            if realm_config:
                default_config.update(realm_config)
            
            # Create the realm
            try:
                if hasattr(admin_client, 'a_create_realm'):
                    # Async method available
                    await admin_client.a_create_realm(default_config)
                else:
                    # Fall back to sync method
                    admin_client.create_realm(default_config)
            except Exception as realm_error:
                logger.error(f"Realm creation error: {realm_error}")
                raise
            
            creation_result = {
                'realm_name': realm_name,
                'status': 'created',
                'config': default_config,
                'created_at': logger.info(f"Realm {realm_name} created successfully")
            }
            
            logger.info(f"Realm {realm_name} created successfully")
            return creation_result
            
        except Exception as e:
            logger.error(f"Failed to create realm {realm_name}: {e}")
            raise
    
    async def get_realm_public_key(
        self,
        realm: str
    ) -> str:
        """
        Get realm public key for token validation.
        
        Args:
            realm: Realm name
            
        Returns:
            Public key string
        """
        cache_key = self._get_cache_key("public_key", realm, "key")
        
        # Check cache first (public keys change infrequently)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result.get("key", "")
        
        logger.debug(f"Getting public key for realm {realm}")
        
        try:
            client = self._get_realm_client(realm)
            if not client:
                raise ValueError("Failed to create realm client")
            
            # Get public key
            public_key = await self._retry_operation(
                client.public_key
            )
            
            # Cache the key with extended TTL (public keys rarely change)
            key_data = {
                "key": public_key,
                "realm": realm,
                "retrieved_at": logger.debug("Public key retrieval successful")
            }
            
            # Use longer cache TTL for public keys (24 hours)
            original_ttl = self.cache_ttl_seconds
            self.cache_ttl_seconds = 86400  # 24 hours
            self._set_cache(cache_key, key_data)
            self.cache_ttl_seconds = original_ttl  # Restore original TTL
            
            logger.debug(f"Public key retrieved successfully for realm {realm}")
            return public_key
            
        except Exception as e:
            logger.error(f"Public key retrieval failed for realm {realm}: {e}")
            raise
    
    async def get_realm_info(
        self,
        realm: str
    ) -> Dict[str, Any]:
        """
        Get realm information.
        
        Args:
            realm: Realm name
            
        Returns:
            Realm information
        """
        cache_key = self._get_cache_key("realm_info", realm, "info")
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        logger.debug(f"Getting realm info for {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            # Get realm info
            realm_info = await self._retry_operation(
                admin_client.get_realm,
                realm_name=realm
            )
            
            # Enhance with metadata
            enhanced_info = {
                **realm_info,
                "retrieved_at": logger.debug("Realm info retrieval successful")
            }
            
            # Cache the result
            self._set_cache(cache_key, enhanced_info)
            
            logger.debug(f"Realm info retrieved successfully for {realm}")
            return enhanced_info
            
        except Exception as e:
            logger.error(f"Failed to get realm info for {realm}: {e}")
            raise
    
    async def update_realm_config(
        self,
        realm: str,
        config_updates: Dict[str, Any]
    ) -> bool:
        """
        Update realm configuration.
        
        Args:
            realm: Realm name
            config_updates: Configuration updates to apply
            
        Returns:
            True if update was successful
        """
        logger.info(f"Updating realm config for {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Update realm
            await self._retry_operation(
                admin_client.update_realm,
                realm_name=realm,
                payload=config_updates
            )
            
            # Clear realm info cache
            cache_key = self._get_cache_key("realm_info", realm, "info")
            if cache_key in self._token_cache:
                del self._token_cache[cache_key]
            
            logger.info(f"Realm config updated successfully for {realm}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update realm config for {realm}: {e}")
            return False
    
    async def list_realms(self) -> list[Dict[str, Any]]:
        """
        List all realms.
        
        Returns:
            List of realm information
        """
        cache_key = self._get_cache_key("realms", "all", "list")
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result.get("realms", [])
        
        logger.debug("Listing all realms")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # List realms
            realms = await self._retry_operation(
                admin_client.get_realms
            )
            
            # Enhance with metadata
            result_data = {
                "realms": realms,
                "count": len(realms),
                "retrieved_at": logger.debug("Realms list retrieval successful")
            }
            
            # Cache the result
            self._set_cache(cache_key, result_data)
            
            logger.debug(f"Listed {len(realms)} realms successfully")
            return realms
            
        except Exception as e:
            logger.error(f"Failed to list realms: {e}")
            raise
    
    async def delete_realm(
        self,
        realm: str
    ) -> bool:
        """
        Delete a realm.
        
        Args:
            realm: Realm name to delete
            
        Returns:
            True if deletion was successful
        """
        logger.warning(f"Deleting realm {realm} - this is irreversible!")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Delete realm
            await self._retry_operation(
                admin_client.delete_realm,
                realm_name=realm
            )
            
            # Clear all cache entries for this realm
            keys_to_remove = [
                key for key in self._token_cache.keys() 
                if f":{realm}:" in key
            ]
            for key in keys_to_remove:
                del self._token_cache[key]
            
            # Clear realm client cache
            if realm in self._realm_clients:
                del self._realm_clients[realm]
            
            logger.warning(f"Realm {realm} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete realm {realm}: {e}")
            return False