"""
Admin operations for Keycloak integration.

Handles administrative operations, statistics, and system-level functions.
"""
import logging
from typing import Optional, Dict, Any

from ..protocols.protocols import KeycloakAdminProtocol
from ..clients.base_client import BaseKeycloakClient

logger = logging.getLogger(__name__)


class KeycloakAdminOperations(BaseKeycloakClient, KeycloakAdminProtocol):
    """Admin operations implementation for Keycloak."""
    
    async def get_client_statistics(self) -> Dict[str, Any]:
        """
        Get client usage statistics and metrics.
        
        Returns:
            Dictionary containing client statistics
        """
        logger.debug("Collecting client statistics")
        
        try:
            statistics = {
                "cache": {
                    "token_cache_size": len(self._token_cache),
                    "realm_clients_count": len(self._realm_clients),
                    "cache_enabled": self.enable_caching,
                    "cache_ttl_seconds": self.cache_ttl_seconds
                },
                "configuration": {
                    "server_url": self.config.server_url,
                    "admin_realm": self.config.admin_realm,
                    "client_configured": bool(self.config.client_id),
                    "admin_configured": bool(self.config.admin_username),
                    "ssl_verification": self.config.verify_ssl,
                    "connection_timeout": self.config.connection_timeout,
                    "max_connections": self.config.max_connections
                },
                "client_state": {
                    "is_closed": self._is_closed,
                    "admin_client_created": self._admin_client is not None,
                    "retry_config": {
                        "max_retries": self.max_retries,
                        "retry_delay": self.retry_delay
                    }
                }
            }
            
            # Add health check information
            health_status = await self.health_check()
            statistics["health"] = health_status
            
            # Add cache statistics
            if self.enable_caching:
                valid_cache_entries = 0
                expired_cache_entries = 0
                
                for cached_data in self._token_cache.values():
                    if self._is_cache_valid(cached_data):
                        valid_cache_entries += 1
                    else:
                        expired_cache_entries += 1
                
                statistics["cache"].update({
                    "valid_entries": valid_cache_entries,
                    "expired_entries": expired_cache_entries,
                    "cache_hit_potential": valid_cache_entries / max(len(self._token_cache), 1)
                })
            
            logger.debug("Client statistics collected successfully")
            return statistics
            
        except Exception as e:
            logger.error(f"Failed to collect client statistics: {e}")
            raise
    
    async def get_server_info(self) -> Dict[str, Any]:
        """
        Get Keycloak server information.
        
        Returns:
            Server information including version and status
        """
        logger.debug("Getting server information")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Get server info
            server_info = await self._retry_operation(
                admin_client.get_server_info
            )
            
            # Enhance with additional metadata
            enhanced_info = {
                **server_info,
                "client_server_url": self.config.server_url,
                "client_admin_realm": self.config.admin_realm,
                "retrieved_at": logger.debug("Server info retrieval successful")
            }
            
            logger.debug("Server information retrieved successfully")
            return enhanced_info
            
        except Exception as e:
            logger.error(f"Failed to get server information: {e}")
            raise
    
    async def get_realm_statistics(
        self,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get realm-specific statistics.
        
        Args:
            realm: Realm name (defaults to admin realm)
            
        Returns:
            Realm statistics
        """
        realm = realm or self.config.admin_realm
        
        logger.debug(f"Getting statistics for realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            statistics = {
                "realm": realm,
                "users": {
                    "total_count": 0,
                    "enabled_count": 0,
                    "disabled_count": 0
                },
                "clients": {
                    "total_count": 0,
                    "enabled_count": 0
                },
                "roles": {
                    "realm_roles_count": 0,
                    "client_roles_count": 0
                },
                "sessions": {
                    "active_sessions": 0
                }
            }
            
            try:
                # Get user count
                users = await self._retry_operation(
                    admin_client.get_users
                )
                statistics["users"]["total_count"] = len(users)
                statistics["users"]["enabled_count"] = sum(
                    1 for user in users if user.get("enabled", True)
                )
                statistics["users"]["disabled_count"] = (
                    statistics["users"]["total_count"] - 
                    statistics["users"]["enabled_count"]
                )
            except Exception as e:
                logger.warning(f"Failed to get user statistics: {e}")
            
            try:
                # Get client count
                clients = await self._retry_operation(
                    admin_client.get_clients
                )
                statistics["clients"]["total_count"] = len(clients)
                statistics["clients"]["enabled_count"] = sum(
                    1 for client in clients if client.get("enabled", True)
                )
            except Exception as e:
                logger.warning(f"Failed to get client statistics: {e}")
            
            try:
                # Get realm roles count
                realm_roles = await self._retry_operation(
                    admin_client.get_realm_roles
                )
                statistics["roles"]["realm_roles_count"] = len(realm_roles)
            except Exception as e:
                logger.warning(f"Failed to get realm roles statistics: {e}")
            
            try:
                # Get session count
                sessions = await self._retry_operation(
                    admin_client.get_sessions
                )
                statistics["sessions"]["active_sessions"] = len(sessions)
            except Exception as e:
                logger.warning(f"Failed to get session statistics: {e}")
            
            statistics["retrieved_at"] = logger.debug("Realm statistics collection successful")
            
            logger.debug(f"Statistics retrieved successfully for realm {realm}")
            return statistics
            
        except Exception as e:
            logger.error(f"Failed to get statistics for realm {realm}: {e}")
            raise
    
    async def clear_realm_cache(
        self,
        realm: Optional[str] = None
    ) -> bool:
        """
        Clear Keycloak realm cache.
        
        Args:
            realm: Realm name (None for all realms)
            
        Returns:
            True if cache was cleared successfully
        """
        logger.info(f"Clearing cache for realm: {realm or 'all realms'}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            if realm:
                # Clear specific realm cache
                admin_client.realm_name = realm
                await self._retry_operation(
                    admin_client.clear_realm_cache
                )
                logger.info(f"Realm cache cleared for {realm}")
            else:
                # Clear all realm caches
                realms = await self._retry_operation(
                    admin_client.get_realms
                )
                
                for realm_info in realms:
                    realm_name = realm_info.get("realm")
                    if realm_name:
                        try:
                            admin_client.realm_name = realm_name
                            await self._retry_operation(
                                admin_client.clear_realm_cache
                            )
                        except Exception as e:
                            logger.warning(f"Failed to clear cache for realm {realm_name}: {e}")
                
                logger.info("All realm caches cleared")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear realm cache: {e}")
            return False
    
    async def clear_user_cache(
        self,
        realm: Optional[str] = None
    ) -> bool:
        """
        Clear Keycloak user cache.
        
        Args:
            realm: Realm name (defaults to admin realm)
            
        Returns:
            True if cache was cleared successfully
        """
        realm = realm or self.config.admin_realm
        
        logger.info(f"Clearing user cache for realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            # Clear user cache
            await self._retry_operation(
                admin_client.clear_user_cache
            )
            
            logger.info(f"User cache cleared for realm {realm}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear user cache for realm {realm}: {e}")
            return False
    
    async def export_realm(
        self,
        realm: str,
        include_users: bool = False,
        include_clients: bool = True,
        include_roles: bool = True
    ) -> Dict[str, Any]:
        """
        Export realm configuration.
        
        Args:
            realm: Realm name to export
            include_users: Whether to include users in export
            include_clients: Whether to include clients in export
            include_roles: Whether to include roles in export
            
        Returns:
            Realm export data
        """
        logger.info(f"Exporting realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            export_data = {
                "realm": realm,
                "export_options": {
                    "include_users": include_users,
                    "include_clients": include_clients,
                    "include_roles": include_roles
                },
                "exported_at": logger.info(f"Realm export started for {realm}")
            }
            
            # Get realm configuration
            realm_config = await self._retry_operation(
                admin_client.get_realm,
                realm_name=realm
            )
            export_data["realm_config"] = realm_config
            
            # Include clients if requested
            if include_clients:
                clients = await self._retry_operation(
                    admin_client.get_clients
                )
                export_data["clients"] = clients
            
            # Include roles if requested
            if include_roles:
                realm_roles = await self._retry_operation(
                    admin_client.get_realm_roles
                )
                export_data["realm_roles"] = realm_roles
            
            # Include users if requested (warning: can be large)
            if include_users:
                logger.warning(f"Including users in export for {realm} - this may be slow and large")
                users = await self._retry_operation(
                    admin_client.get_users
                )
                export_data["users"] = users
            
            logger.info(f"Realm {realm} exported successfully")
            return export_data
            
        except Exception as e:
            logger.error(f"Failed to export realm {realm}: {e}")
            raise