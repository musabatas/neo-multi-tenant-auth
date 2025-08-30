"""Keycloak Admin adapter for authentication platform."""

import logging
from typing import Dict, List, Optional, Any

from .....core.value_objects.identifiers import UserId, KeycloakUserId
from ...core.value_objects import RealmIdentifier
from ...core.exceptions import AuthenticationFailed, UserNotFound

logger = logging.getLogger(__name__)


class KeycloakAdminAdapter:
    """Keycloak Admin API adapter following maximum separation principle.
    
    Handles ONLY Keycloak Admin API operations for authentication platform.
    Does not handle OpenID operations, token validation, or caching.
    """
    
    def __init__(self, keycloak_admin_client):
        """Initialize Keycloak Admin adapter.
        
        Args:
            keycloak_admin_client: Keycloak Admin client instance
        """
        if not keycloak_admin_client:
            raise ValueError("Keycloak Admin client is required")
        self.keycloak_admin_client = keycloak_admin_client
    
    async def __aenter__(self):
        """Async context manager entry."""
        # Keycloak Admin client doesn't need explicit connection
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Keycloak Admin client doesn't need explicit cleanup
        pass
    
    async def get_user_by_username(
        self,
        username: str
    ) -> Dict[str, Any]:
        """Get user information by username from Keycloak.
        
        Args:
            username: Username to search for
            
        Returns:
            User information dictionary
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If operation fails
        """
        try:
            logger.debug(f"Getting user by username: {username}")
            
            users = await self.keycloak_admin_client.a_get_users({"username": username})
            
            if not users or len(users) == 0:
                raise UserNotFound(
                    f"User not found: {username}",
                    context={"username": username}
                )
            
            # Return the first user (username should be unique)
            user = users[0]
            logger.debug(f"Successfully retrieved user: {username}")
            return user
            
        except UserNotFound:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            raise AuthenticationFailed(
                "User retrieval failed",
                reason="keycloak_admin_error",
                context={"username": username, "error": str(e)}
            )
    
    async def get_user_by_id(
        self,
        user_id: KeycloakUserId
    ) -> Dict[str, Any]:
        """Get user information by ID from Keycloak.
        
        Args:
            user_id: Keycloak user ID
            
        Returns:
            User information dictionary
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If operation fails
        """
        try:
            logger.debug(f"Getting user by ID: {user_id.value}")
            
            user = await self.keycloak_admin_client.a_get_user(str(user_id.value))
            
            if not user:
                raise UserNotFound(
                    f"User not found: {user_id.value}",
                    context={"user_id": str(user_id.value)}
                )
            
            logger.debug(f"Successfully retrieved user: {user_id.value}")
            return user
            
        except UserNotFound:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to get user by ID {user_id.value}: {e}")
            raise AuthenticationFailed(
                "User retrieval failed",
                reason="keycloak_admin_error",
                context={"user_id": str(user_id.value), "error": str(e)}
            )
    
    async def create_user(
        self,
        user_data: Dict[str, Any]
    ) -> KeycloakUserId:
        """Create user in Keycloak.
        
        Args:
            user_data: User data dictionary
            
        Returns:
            Created user's Keycloak ID
            
        Raises:
            AuthenticationFailed: If user creation fails
        """
        try:
            username = user_data.get('username', 'unknown')
            logger.info(f"Creating user in Keycloak: {username}")
            
            user_id = await self.keycloak_admin_client.a_create_user(user_data)
            
            if not user_id:
                raise AuthenticationFailed(
                    "User creation failed - no user ID returned",
                    reason="keycloak_create_user_failed",
                    context={"username": username}
                )
            
            logger.info(f"Successfully created user: {username} with ID: {user_id}")
            return KeycloakUserId(user_id)
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise AuthenticationFailed(
                "User creation failed",
                reason="keycloak_admin_error",
                context={
                    "username": user_data.get('username'),
                    "error": str(e)
                }
            )
    
    async def update_user(
        self,
        user_id: KeycloakUserId,
        user_data: Dict[str, Any]
    ) -> bool:
        """Update user in Keycloak.
        
        Args:
            user_id: Keycloak user ID
            user_data: Updated user data
            
        Returns:
            True if update was successful
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If update fails
        """
        try:
            logger.debug(f"Updating user in Keycloak: {user_id.value}")
            
            result = await self.keycloak_admin_client.a_update_user(
                str(user_id.value),
                user_data
            )
            
            logger.debug(f"Successfully updated user: {user_id.value}")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str:
                raise UserNotFound(
                    f"User not found for update: {user_id.value}",
                    context={"user_id": str(user_id.value)}
                )
            
            logger.error(f"Failed to update user {user_id.value}: {e}")
            raise AuthenticationFailed(
                "User update failed",
                reason="keycloak_admin_error",
                context={"user_id": str(user_id.value), "error": str(e)}
            )
    
    async def delete_user(
        self,
        user_id: KeycloakUserId
    ) -> bool:
        """Delete user from Keycloak.
        
        Args:
            user_id: Keycloak user ID
            
        Returns:
            True if deletion was successful
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If deletion fails
        """
        try:
            logger.warning(f"Deleting user from Keycloak: {user_id.value}")
            
            result = await self.keycloak_admin_client.a_delete_user(str(user_id.value))
            
            logger.warning(f"Successfully deleted user: {user_id.value}")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str:
                raise UserNotFound(
                    f"User not found for deletion: {user_id.value}",
                    context={"user_id": str(user_id.value)}
                )
            
            logger.error(f"Failed to delete user {user_id.value}: {e}")
            raise AuthenticationFailed(
                "User deletion failed",
                reason="keycloak_admin_error",
                context={"user_id": str(user_id.value), "error": str(e)}
            )
    
    async def get_user_roles(
        self,
        user_id: KeycloakUserId
    ) -> List[Dict[str, Any]]:
        """Get user's roles from Keycloak.
        
        Args:
            user_id: Keycloak user ID
            
        Returns:
            List of user roles
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If operation fails
        """
        try:
            logger.debug(f"Getting user roles for: {user_id.value}")
            
            roles = await self.keycloak_admin_client.a_get_user_realm_roles(str(user_id.value))
            
            if roles is None:
                roles = []
            
            logger.debug(f"Successfully retrieved {len(roles)} roles for user: {user_id.value}")
            return roles
            
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str:
                raise UserNotFound(
                    f"User not found for roles retrieval: {user_id.value}",
                    context={"user_id": str(user_id.value)}
                )
            
            logger.error(f"Failed to get user roles for {user_id.value}: {e}")
            raise AuthenticationFailed(
                "User roles retrieval failed",
                reason="keycloak_admin_error",
                context={"user_id": str(user_id.value), "error": str(e)}
            )
    
    async def assign_user_role(
        self,
        user_id: KeycloakUserId,
        role_name: str
    ) -> bool:
        """Assign role to user in Keycloak.
        
        Args:
            user_id: Keycloak user ID
            role_name: Role name to assign
            
        Returns:
            True if role assignment was successful
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If role assignment fails
        """
        try:
            logger.info(f"Assigning role {role_name} to user: {user_id.value}")
            
            # First get the role by name
            role = await self.keycloak_admin_client.a_get_realm_role(role_name)
            
            if not role:
                raise AuthenticationFailed(
                    f"Role not found: {role_name}",
                    reason="role_not_found",
                    context={"role_name": role_name}
                )
            
            # Assign the role to user
            result = await self.keycloak_admin_client.a_assign_user_realm_roles(
                str(user_id.value),
                [role]
            )
            
            logger.info(f"Successfully assigned role {role_name} to user: {user_id.value}")
            return True
            
        except AuthenticationFailed:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str and "user" in error_str:
                raise UserNotFound(
                    f"User not found for role assignment: {user_id.value}",
                    context={"user_id": str(user_id.value)}
                )
            
            logger.error(f"Failed to assign role {role_name} to user {user_id.value}: {e}")
            raise AuthenticationFailed(
                "User role assignment failed",
                reason="keycloak_admin_error",
                context={
                    "user_id": str(user_id.value),
                    "role_name": role_name,
                    "error": str(e)
                }
            )
    
    async def remove_user_role(
        self,
        user_id: KeycloakUserId,
        role_name: str
    ) -> bool:
        """Remove role from user in Keycloak.
        
        Args:
            user_id: Keycloak user ID
            role_name: Role name to remove
            
        Returns:
            True if role removal was successful
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If role removal fails
        """
        try:
            logger.info(f"Removing role {role_name} from user: {user_id.value}")
            
            # First get the role by name
            role = await self.keycloak_admin_client.a_get_realm_role(role_name)
            
            if not role:
                logger.warning(f"Role not found for removal: {role_name}")
                return True  # Role doesn't exist, consider it removed
            
            # Remove the role from user
            result = await self.keycloak_admin_client.a_remove_user_realm_roles(
                str(user_id.value),
                [role]
            )
            
            logger.info(f"Successfully removed role {role_name} from user: {user_id.value}")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str and "user" in error_str:
                raise UserNotFound(
                    f"User not found for role removal: {user_id.value}",
                    context={"user_id": str(user_id.value)}
                )
            
            logger.error(f"Failed to remove role {role_name} from user {user_id.value}: {e}")
            raise AuthenticationFailed(
                "User role removal failed",
                reason="keycloak_admin_error",
                context={
                    "user_id": str(user_id.value),
                    "role_name": role_name,
                    "error": str(e)
                }
            )
    
    async def set_user_password(
        self,
        user_id: KeycloakUserId,
        password: str,
        temporary: bool = False
    ) -> bool:
        """Set user password in Keycloak.
        
        Args:
            user_id: Keycloak user ID
            password: New password
            temporary: Whether password is temporary (requires change on next login)
            
        Returns:
            True if password was set successfully
            
        Raises:
            UserNotFound: If user is not found
            AuthenticationFailed: If password setting fails
        """
        try:
            logger.info(f"Setting password for user: {user_id.value}")
            
            result = await self.keycloak_admin_client.a_set_user_password(
                str(user_id.value),
                password,
                temporary=temporary
            )
            
            logger.info(f"Successfully set password for user: {user_id.value}")
            return True
            
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str:
                raise UserNotFound(
                    f"User not found for password setting: {user_id.value}",
                    context={"user_id": str(user_id.value)}
                )
            
            logger.error(f"Failed to set password for user {user_id.value}: {e}")
            raise AuthenticationFailed(
                "Password setting failed",
                reason="keycloak_admin_error",
                context={"user_id": str(user_id.value), "error": str(e)}
            )
    
    async def get_realm_roles(self) -> List[Dict[str, Any]]:
        """Get all realm roles from Keycloak.
        
        Returns:
            List of realm roles
            
        Raises:
            AuthenticationFailed: If operation fails
        """
        try:
            logger.debug("Getting all realm roles")
            
            roles = await self.keycloak_admin_client.a_get_realm_roles()
            
            if roles is None:
                roles = []
            
            logger.debug(f"Successfully retrieved {len(roles)} realm roles")
            return roles
            
        except Exception as e:
            logger.error(f"Failed to get realm roles: {e}")
            raise AuthenticationFailed(
                "Realm roles retrieval failed",
                reason="keycloak_admin_error",
                context={"error": str(e)}
            )
    
    async def create_realm_role(
        self,
        role_name: str,
        description: Optional[str] = None
    ) -> bool:
        """Create realm role in Keycloak.
        
        Args:
            role_name: Name of the role to create
            description: Optional role description
            
        Returns:
            True if role was created successfully
            
        Raises:
            AuthenticationFailed: If role creation fails
        """
        try:
            logger.info(f"Creating realm role: {role_name}")
            
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description
            
            result = await self.keycloak_admin_client.a_create_realm_role(role_data)
            
            logger.info(f"Successfully created realm role: {role_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create realm role {role_name}: {e}")
            raise AuthenticationFailed(
                "Realm role creation failed",
                reason="keycloak_admin_error",
                context={"role_name": role_name, "error": str(e)}
            )