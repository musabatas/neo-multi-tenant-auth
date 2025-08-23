"""Value objects for identifiers in neo-commons.

This module defines immutable value objects for various identifiers
used throughout the system. These provide type safety and validation.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserId:
    """User identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("User ID must be a non-empty string")


@dataclass(frozen=True)
class TenantId:
    """Tenant identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Tenant ID must be a non-empty string")


@dataclass(frozen=True)
class OrganizationId:
    """Organization identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Organization ID must be a non-empty string")


@dataclass(frozen=True)
class PermissionCode:
    """Permission code value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Permission code must be a non-empty string")


@dataclass(frozen=True)
class RoleCode:
    """Role code value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Role code must be a non-empty string")


@dataclass(frozen=True)
class DatabaseConnectionId:
    """Database connection identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Database connection ID must be a non-empty string")


@dataclass(frozen=True)
class RegionId:
    """Region identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Region ID must be a non-empty string")


@dataclass(frozen=True)
class RealmId:
    """Keycloak realm identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Realm ID must be a non-empty string")


@dataclass(frozen=True)
class KeycloakUserId:
    """Keycloak user identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Keycloak User ID must be a non-empty string")


@dataclass(frozen=True)
class TokenId:
    """Token identifier value object."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Token ID must be a non-empty string")