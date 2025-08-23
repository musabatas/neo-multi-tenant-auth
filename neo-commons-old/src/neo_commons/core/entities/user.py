"""
User entity representing a platform user across all services.

The User entity encapsulates the core identity and properties of a user
within the NeoMultiTenant platform, providing a consistent representation
across all bounded contexts.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..value_objects import UserId, TenantId


@dataclass(frozen=True)
class User:
    """
    Core user entity for the NeoMultiTenant platform.
    
    Represents a user with their essential identity and properties.
    This entity is immutable and focuses on core user concepts that
    are consistent across all services.
    
    Attributes:
        id: Unique identifier for the user
        tenant_id: ID of the tenant this user belongs to
        external_id: External system identifier (e.g., Keycloak user ID)
        email: User's email address (primary identifier)
        username: Optional username for the user
        first_name: User's first name
        last_name: User's last name
        is_active: Whether the user account is active
        is_verified: Whether the user's email has been verified
        created_at: When the user was created
        updated_at: When the user was last updated
    """
    
    id: UserId
    tenant_id: TenantId
    email: str
    external_id: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self) -> None:
        """Validate user data after initialization."""
        if not self.email or '@' not in self.email:
            raise ValueError("User must have a valid email address")
        
        if self.username is not None and len(self.username.strip()) == 0:
            raise ValueError("Username cannot be empty if provided")
    
    @property
    def full_name(self) -> str:
        """
        Get the user's full name.
        
        Returns:
            str: Combination of first and last name, or email if names not available
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email
    
    @property
    def display_name(self) -> str:
        """
        Get the user's display name for UI purposes.
        
        Returns:
            str: Username if available, otherwise full name, otherwise email
        """
        if self.username:
            return self.username
        return self.full_name
    
    def is_external_user(self) -> bool:
        """
        Check if this user is managed by an external identity provider.
        
        Returns:
            bool: True if user has an external_id (e.g., from Keycloak)
        """
        return self.external_id is not None
    
    def has_complete_profile(self) -> bool:
        """
        Check if the user has a complete profile.
        
        Returns:
            bool: True if user has first name, last name, and verified email
        """
        return (
            self.first_name is not None 
            and self.last_name is not None 
            and self.is_verified
        )
    
    def can_login(self) -> bool:
        """
        Check if the user can log into the system.
        
        Returns:
            bool: True if user is active and verified
        """
        return self.is_active and self.is_verified
    
    def belongs_to_tenant(self, tenant_id: TenantId) -> bool:
        """
        Check if the user belongs to a specific tenant.
        
        Args:
            tenant_id: The tenant ID to check
            
        Returns:
            bool: True if user belongs to the specified tenant
        """
        return self.tenant_id == tenant_id