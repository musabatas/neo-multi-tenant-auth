"""Realm configuration provider protocol contract."""

from typing import Protocol, runtime_checkable, Optional, List, Dict, Any
from ....core.value_objects.identifiers import TenantId
from ..value_objects import RealmIdentifier


@runtime_checkable
class RealmProvider(Protocol):
    """Protocol for realm configuration management.
    
    Defines ONLY the contract for realm configuration operations.
    Implementations handle specific configuration sources (database, file, Keycloak, etc.).
    """
    
    async def get_realm_config(self, realm_id: RealmIdentifier) -> Dict[str, Any]:
        """Get realm configuration.
        
        Args:
            realm_id: Realm identifier
            
        Returns:
            Realm configuration dictionary
            
        Raises:
            RealmNotFound: If realm configuration is not found
        """
        ...
    
    async def get_realm_by_tenant(self, tenant_id: TenantId) -> RealmIdentifier:
        """Get realm identifier for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Realm identifier for the tenant
            
        Raises:
            RealmNotFound: If no realm is configured for tenant
        """
        ...
    
    async def list_available_realms(self) -> List[RealmIdentifier]:
        """List all available realm identifiers.
        
        Returns:
            List of available realm identifiers
        """
        ...
    
    async def is_realm_available(self, realm_id: RealmIdentifier) -> bool:
        """Check if realm is available and enabled.
        
        Args:
            realm_id: Realm identifier to check
            
        Returns:
            True if realm is available, False otherwise
        """
        ...
    
    async def get_default_realm(self) -> RealmIdentifier:
        """Get the default realm identifier.
        
        Returns:
            Default realm identifier
            
        Raises:
            RealmNotFound: If no default realm is configured
        """
        ...
    
    async def get_realm_metadata(self, realm_id: RealmIdentifier) -> Dict[str, Any]:
        """Get realm metadata (without full configuration).
        
        Args:
            realm_id: Realm identifier
            
        Returns:
            Realm metadata dictionary
            
        Raises:
            RealmNotFound: If realm is not found
        """
        ...
    
    async def validate_realm_config(self, realm_id: RealmIdentifier) -> bool:
        """Validate realm configuration completeness.
        
        Args:
            realm_id: Realm identifier to validate
            
        Returns:
            True if configuration is valid and complete
            
        Raises:
            RealmNotFound: If realm is not found
        """
        ...
    
    async def refresh_realm_config(self, realm_id: RealmIdentifier) -> None:
        """Refresh cached realm configuration.
        
        Args:
            realm_id: Realm identifier to refresh
            
        Raises:
            RealmNotFound: If realm is not found
        """
        ...