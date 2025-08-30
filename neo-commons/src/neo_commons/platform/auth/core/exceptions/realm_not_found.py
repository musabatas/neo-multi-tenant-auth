"""Realm configuration not found exception."""

from typing import Optional, Dict, Any, List
from ....core.exceptions.base import DomainException


class RealmNotFound(DomainException):
    """Exception raised when realm configuration cannot be found.
    
    Handles ONLY realm not found representation with context.
    Does not manage realm configuration - that's handled by providers.
    """
    
    def __init__(
        self,
        message: str = "Realm not found",
        *,
        realm_id: Optional[str] = None,
        realm_name: Optional[str] = None,
        tenant_id: Optional[str] = None,
        available_realms: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize realm not found exception.
        
        Args:
            message: Human-readable error message
            realm_id: Realm identifier that was not found
            realm_name: Realm name that was not found
            tenant_id: Tenant ID associated with the realm request
            available_realms: List of available realm identifiers for debugging
            context: Additional context for debugging
        """
        super().__init__(message)
        
        self.realm_id = realm_id
        self.realm_name = realm_name
        self.tenant_id = tenant_id
        self.available_realms = available_realms or []
        self.context = context or {}
        
        # Add structured data for logging and monitoring
        self.details = {
            'realm_id': self.realm_id,
            'realm_name': self.realm_name,
            'tenant_id': self.tenant_id,
            'available_realms': self.available_realms,
            **self.context
        }
    
    @property
    def has_suggestions(self) -> bool:
        """Check if there are suggested available realms."""
        return len(self.available_realms) > 0
    
    @property
    def is_tenant_realm_missing(self) -> bool:
        """Check if this is a tenant-specific realm that's missing."""
        return self.tenant_id is not None and (
            (self.realm_id and 'tenant' in self.realm_id.lower()) or
            (self.realm_name and 'tenant' in self.realm_name.lower())
        )
    
    @property
    def suggested_realm(self) -> Optional[str]:
        """Get the most likely correct realm suggestion."""
        if not self.available_realms:
            return None
        
        # If looking for tenant realm, prefer tenant-prefixed realms
        if self.is_tenant_realm_missing:
            tenant_realms = [
                realm for realm in self.available_realms
                if 'tenant' in realm.lower()
            ]
            if tenant_realms:
                return tenant_realms[0]
        
        # Otherwise, return first available realm
        return self.available_realms[0]
    
    @classmethod
    def by_id(
        cls,
        realm_id: str,
        available_realms: Optional[List[str]] = None
    ) -> 'RealmNotFound':
        """Create exception for realm ID not found."""
        message = f"Realm with ID '{realm_id}' not found"
        
        if available_realms:
            message += f". Available realms: {', '.join(available_realms)}"
        
        return cls(
            message=message,
            realm_id=realm_id,
            available_realms=available_realms
        )
    
    @classmethod
    def by_name(
        cls,
        realm_name: str,
        available_realms: Optional[List[str]] = None
    ) -> 'RealmNotFound':
        """Create exception for realm name not found."""
        message = f"Realm with name '{realm_name}' not found"
        
        if available_realms:
            message += f". Available realms: {', '.join(available_realms)}"
        
        return cls(
            message=message,
            realm_name=realm_name,
            available_realms=available_realms
        )
    
    @classmethod
    def for_tenant(
        cls,
        tenant_id: str,
        expected_realm: Optional[str] = None,
        available_realms: Optional[List[str]] = None
    ) -> 'RealmNotFound':
        """Create exception for tenant realm not found."""
        if expected_realm:
            message = f"Realm '{expected_realm}' for tenant '{tenant_id}' not found"
        else:
            message = f"No realm configured for tenant '{tenant_id}'"
        
        if available_realms:
            message += f". Available realms: {', '.join(available_realms)}"
        
        return cls(
            message=message,
            realm_id=expected_realm,
            tenant_id=tenant_id,
            available_realms=available_realms
        )
    
    @classmethod
    def configuration_missing(
        cls,
        realm_id: str,
        configuration_type: str = "keycloak"
    ) -> 'RealmNotFound':
        """Create exception for missing realm configuration."""
        return cls(
            message=f"Realm '{realm_id}' found but {configuration_type} configuration is missing",
            realm_id=realm_id,
            context={'missing_configuration': configuration_type}
        )
    
    @classmethod
    def disabled_realm(
        cls,
        realm_id: str,
        reason: Optional[str] = None
    ) -> 'RealmNotFound':
        """Create exception for disabled realm."""
        message = f"Realm '{realm_id}' is disabled"
        if reason:
            message += f": {reason}"
        
        return cls(
            message=message,
            realm_id=realm_id,
            context={'disabled': True, 'reason': reason}
        )
    
    @classmethod
    def default_realm_missing(
        cls,
        available_realms: Optional[List[str]] = None
    ) -> 'RealmNotFound':
        """Create exception for missing default realm."""
        message = "Default realm is not configured"
        
        if available_realms:
            message += f". Available realms: {', '.join(available_realms)}"
        
        return cls(
            message=message,
            realm_id="default",
            available_realms=available_realms,
            context={'is_default_realm': True}
        )
    
    def get_help_message(self) -> str:
        """Get helpful message for resolving the issue."""
        if self.is_tenant_realm_missing:
            return (
                "This appears to be a tenant-specific realm. "
                "Ensure the tenant is properly configured with a realm in the system."
            )
        
        if self.suggested_realm:
            return f"Did you mean '{self.suggested_realm}'?"
        
        if self.has_suggestions:
            return f"Available realms: {', '.join(self.available_realms)}"
        
        return "Check your realm configuration and ensure the realm is registered."
    
    def __str__(self) -> str:
        """String representation with realm context."""
        base_msg = super().__str__()
        
        context_parts = []
        if self.realm_id:
            context_parts.append(f"realm_id={self.realm_id}")
        if self.tenant_id:
            context_parts.append(f"tenant_id={self.tenant_id}")
        
        if context_parts:
            return f"{base_msg} ({', '.join(context_parts)})"
        
        return base_msg