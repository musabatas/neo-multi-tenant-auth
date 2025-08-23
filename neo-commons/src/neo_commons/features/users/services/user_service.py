"""User service for business logic."""

import logging
from typing import Optional, Dict, Any

from ....core.value_objects import UserId
from ..entities.user import User
from ..repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    """Service for user business logic."""
    
    def __init__(self, user_repository: UserRepository):
        """Initialize user service."""
        self.user_repository = user_repository
    
    async def sync_keycloak_user(
        self,
        external_user_id: str,
        username: str,
        email: str,
        first_name: str,
        last_name: str,
        schema_name: str = "admin"
    ) -> UserId:
        """Sync a Keycloak user to the database."""
        logger.debug(f"Syncing Keycloak user {username} to {schema_name} schema")
        
        user_id = await self.user_repository.sync_user_from_keycloak(
            external_user_id=external_user_id,
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            schema_name=schema_name
        )
        
        # Update last login timestamp
        await self.user_repository.update_last_login(user_id, schema_name)
        
        logger.debug(f"Successfully synced user {username} with ID {user_id.value}")
        return user_id
    
    async def get_user_by_id(self, user_id: UserId, schema_name: str = "admin") -> Optional[User]:
        """Get user by ID."""
        return await self.user_repository.get_by_id(user_id, schema_name)
    
    async def get_user_by_external_id(self, external_user_id: str, schema_name: str = "admin") -> Optional[User]:
        """Get user by external user ID (Keycloak ID)."""
        return await self.user_repository.get_by_external_id(external_user_id, schema_name)
    
    async def get_user_by_email(self, email: str, schema_name: str = "admin") -> Optional[User]:
        """Get user by email."""
        return await self.user_repository.get_by_email(email, schema_name)
    
    async def update_user_login(self, user_id: UserId, schema_name: str = "admin") -> None:
        """Update user's last login timestamp."""
        await self.user_repository.update_last_login(user_id, schema_name)
    
    async def get_complete_user_data(self, user_id: UserId, schema_name: str = "admin") -> Optional[Dict[str, Any]]:
        """Get complete user data including all public fields from the users table."""
        try:
            user_data = await self.user_repository.get_user_by_id(user_id, schema_name)
            if not user_data:
                return None
            
            # Convert database values to API-friendly format
            return self._format_user_data(user_data)
        
        except Exception as e:
            logger.error(f"Failed to get complete user data for {user_id.value}: {e}")
            return None
    
    async def get_complete_user_by_external_id(self, external_user_id: str, schema_name: str = "admin") -> Optional[Dict[str, Any]]:
        """Get complete user data by external user ID."""
        try:
            user_data = await self.user_repository.get_user_by_external_id(external_user_id, schema_name)
            if not user_data:
                return None
            
            return self._format_user_data(user_data)
        
        except Exception as e:
            logger.error(f"Failed to get complete user data for external ID {external_user_id}: {e}")
            return None
    
    def _format_user_data(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format raw user data from database for API response."""
        import json
        
        def parse_json_field(field_value):
            """Parse JSON field from database, handling both string and dict cases."""
            if field_value is None:
                return {}
            if isinstance(field_value, dict):
                return field_value
            if isinstance(field_value, str):
                try:
                    return json.loads(field_value) if field_value.strip() else {}
                except (json.JSONDecodeError, AttributeError):
                    return {}
            return {}
        
        def parse_array_field(field_value):
            """Parse array field from database."""
            if field_value is None:
                return []
            if isinstance(field_value, list):
                return field_value
            return []
        
        return {
            # Core Identity
            "id": str(user_data["id"]),
            "email": user_data["email"],
            "username": user_data["username"],
            
            # External Auth (publicly safe fields)
            "external_user_id": user_data["external_user_id"],
            "external_auth_provider": user_data["external_auth_provider"],
            
            # Profile Information
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"], 
            "display_name": user_data["display_name"],
            "avatar_url": user_data["avatar_url"],
            "phone": user_data["phone"],
            "job_title": user_data["job_title"],
            
            # Localization
            "timezone": user_data["timezone"],
            "locale": user_data["locale"],
            
            # Status
            "status": user_data["status"],
            
            # Organizational
            "departments": parse_array_field(user_data["departments"]),
            "company": user_data["company"],
            "manager_id": str(user_data["manager_id"]) if user_data["manager_id"] else None,
            
            # Role and Access
            "default_role_level": user_data["default_role_level"],
            "is_system_user": user_data["is_system_user"],
            
            # Onboarding and Profile
            "is_onboarding_completed": user_data["is_onboarding_completed"],
            "profile_completion_percentage": user_data["profile_completion_percentage"],
            
            # Preferences (parse JSON fields properly)
            "notification_preferences": parse_json_field(user_data["notification_preferences"]),
            "ui_preferences": parse_json_field(user_data["ui_preferences"]),
            "feature_flags": parse_json_field(user_data["feature_flags"]),
            
            # Tags and Custom Fields (parse JSON fields properly)
            "tags": parse_array_field(user_data["tags"]),
            "custom_fields": parse_json_field(user_data["custom_fields"]),
            "metadata": parse_json_field(user_data["metadata"]),
            
            # Activity Tracking (formatted timestamps)
            "invited_at": user_data["invited_at"].isoformat() if user_data["invited_at"] else None,
            "activated_at": user_data["activated_at"].isoformat() if user_data["activated_at"] else None,
            "last_activity_at": user_data["last_activity_at"].isoformat() if user_data["last_activity_at"] else None,
            "last_login_at": user_data["last_login_at"].isoformat() if user_data["last_login_at"] else None,
            
            # Audit Fields
            "created_at": user_data["created_at"].isoformat() if user_data["created_at"] else None,
            "updated_at": user_data["updated_at"].isoformat() if user_data["updated_at"] else None,
        }