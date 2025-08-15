"""
User management operations for Keycloak integration.

Handles user creation, updates, and user-related operations.
"""
import logging
from typing import Optional, Dict, Any

from ..protocols.protocols import KeycloakUserProtocol
from ..clients.base_client import BaseKeycloakClient

logger = logging.getLogger(__name__)


class KeycloakUserOperations(BaseKeycloakClient, KeycloakUserProtocol):
    """User management operations implementation for Keycloak."""
    
    async def get_user_by_username(
        self,
        username: str,
        realm: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get user by username.
        
        Args:
            username: Username to search for
            realm: Realm name (defaults to admin realm)
            
        Returns:
            User data if found, None otherwise
        """
        realm = realm or self.config.admin_realm
        
        cache_key = self._get_cache_key("user", realm, username)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        logger.debug(f"Getting user {username} from realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            # Search for user by username
            users = await self._retry_operation(
                admin_client.get_users,
                query={"username": username}
            )
            
            if not users:
                logger.debug(f"User {username} not found in realm {realm}")
                return None
            
            # Get the first matching user (usernames should be unique)
            user_data = users[0]
            
            # Enhance with metadata
            enhanced_user = {
                **user_data,
                "realm": realm,
                "retrieved_at": logger.debug("User retrieval successful")
            }
            
            # Cache the result
            self._set_cache(cache_key, enhanced_user)
            
            logger.debug(f"User {username} retrieved successfully from realm {realm}")
            return enhanced_user
            
        except Exception as e:
            logger.error(f"Failed to get user {username} from realm {realm}: {e}")
            raise
    
    async def create_or_update_user(
        self,
        user_data: Dict[str, Any],
        realm: Optional[str] = None,
        update_if_exists: bool = True
    ) -> Dict[str, Any]:
        """
        Create or update user.
        
        Args:
            user_data: User data dictionary
            realm: Realm name (defaults to admin realm)
            update_if_exists: Whether to update if user exists
            
        Returns:
            User data with operation result
        """
        realm = realm or self.config.admin_realm
        username = user_data.get("username")
        
        if not username:
            raise ValueError("Username is required in user_data")
        
        logger.info(f"Creating/updating user {username} in realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            # Check if user exists
            existing_user = await self.get_user_by_username(username, realm)
            
            if existing_user:
                if update_if_exists:
                    # Update existing user
                    user_id = existing_user["id"]
                    await self._retry_operation(
                        admin_client.update_user,
                        user_id=user_id,
                        payload=user_data
                    )
                    
                    operation_result = {
                        "operation": "update",
                        "user_id": user_id,
                        "username": username,
                        "realm": realm,
                        "success": True
                    }
                    
                    logger.info(f"User {username} updated successfully in realm {realm}")
                else:
                    operation_result = {
                        "operation": "skip",
                        "user_id": existing_user["id"],
                        "username": username,
                        "realm": realm,
                        "success": True,
                        "message": "User exists and update_if_exists is False"
                    }
                    
                    logger.info(f"User {username} already exists in realm {realm}, skipping")
            else:
                # Create new user
                user_id = await self._retry_operation(
                    admin_client.create_user,
                    payload=user_data
                )
                
                operation_result = {
                    "operation": "create",
                    "user_id": user_id,
                    "username": username,
                    "realm": realm,
                    "success": True
                }
                
                logger.info(f"User {username} created successfully in realm {realm}")
            
            # Clear cache for this user
            cache_key = self._get_cache_key("user", realm, username)
            if cache_key in self._token_cache:
                del self._token_cache[cache_key]
            
            # Get updated user data
            updated_user = await self.get_user_by_username(username, realm)
            
            return {
                **operation_result,
                "user_data": updated_user
            }
            
        except Exception as e:
            logger.error(f"Failed to create/update user {username} in realm {realm}: {e}")
            raise
    
    async def set_user_password(
        self,
        user_id: str,
        password: str,
        realm: Optional[str] = None,
        temporary: bool = False
    ) -> bool:
        """
        Set user password.
        
        Args:
            user_id: User ID
            password: New password
            realm: Realm name (defaults to admin realm)
            temporary: Whether password is temporary
            
        Returns:
            True if password was set successfully
        """
        realm = realm or self.config.admin_realm
        
        logger.info(f"Setting password for user {user_id} in realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            # Set password
            await self._retry_operation(
                admin_client.set_user_password,
                user_id=user_id,
                password=password,
                temporary=temporary
            )
            
            logger.info(f"Password set successfully for user {user_id} in realm {realm}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set password for user {user_id} in realm {realm}: {e}")
            return False
    
    async def get_user_roles(
        self,
        user_id: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get user roles.
        
        Args:
            user_id: User ID
            realm: Realm name (defaults to admin realm)
            
        Returns:
            User roles information
        """
        realm = realm or self.config.admin_realm
        
        cache_key = self._get_cache_key("user_roles", realm, user_id)
        
        # Check cache first
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            return cached_result
        
        logger.debug(f"Getting roles for user {user_id} in realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            # Get realm roles
            realm_roles = await self._retry_operation(
                admin_client.get_realm_roles_of_user,
                user_id=user_id
            )
            
            # Get client roles
            client_roles = await self._retry_operation(
                admin_client.get_client_roles_of_user,
                user_id=user_id
            )
            
            roles_data = {
                "user_id": user_id,
                "realm": realm,
                "realm_roles": realm_roles,
                "client_roles": client_roles,
                "retrieved_at": logger.debug("User roles retrieval successful")
            }
            
            # Cache the result
            self._set_cache(cache_key, roles_data)
            
            logger.debug(f"Roles retrieved successfully for user {user_id} in realm {realm}")
            return roles_data
            
        except Exception as e:
            logger.error(f"Failed to get roles for user {user_id} in realm {realm}: {e}")
            raise
    
    async def assign_user_role(
        self,
        user_id: str,
        role_name: str,
        realm: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> bool:
        """
        Assign role to user.
        
        Args:
            user_id: User ID
            role_name: Role name to assign
            realm: Realm name (defaults to admin realm)
            client_id: Client ID for client roles (None for realm roles)
            
        Returns:
            True if role was assigned successfully
        """
        realm = realm or self.config.admin_realm
        
        logger.info(f"Assigning role {role_name} to user {user_id} in realm {realm}")
        
        try:
            admin_client = await self._get_admin_client()
            if not admin_client:
                raise ValueError("Failed to create admin client")
            
            # Switch to the target realm
            admin_client.realm_name = realm
            
            if client_id:
                # Assign client role
                client_roles = await self._retry_operation(
                    admin_client.get_client_roles,
                    client_id=client_id
                )
                
                role = next((r for r in client_roles if r["name"] == role_name), None)
                if not role:
                    raise ValueError(f"Client role {role_name} not found")
                
                await self._retry_operation(
                    admin_client.assign_client_role,
                    user_id=user_id,
                    client_id=client_id,
                    roles=[role]
                )
            else:
                # Assign realm role
                realm_roles = await self._retry_operation(
                    admin_client.get_realm_roles
                )
                
                role = next((r for r in realm_roles if r["name"] == role_name), None)
                if not role:
                    raise ValueError(f"Realm role {role_name} not found")
                
                await self._retry_operation(
                    admin_client.assign_realm_roles,
                    user_id=user_id,
                    roles=[role]
                )
            
            # Clear user roles cache
            cache_key = self._get_cache_key("user_roles", realm, user_id)
            if cache_key in self._token_cache:
                del self._token_cache[cache_key]
            
            logger.info(f"Role {role_name} assigned successfully to user {user_id} in realm {realm}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign role {role_name} to user {user_id} in realm {realm}: {e}")
            return False