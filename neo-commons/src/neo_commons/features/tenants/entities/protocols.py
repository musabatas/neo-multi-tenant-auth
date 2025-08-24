"""Protocol interfaces for tenant-specific operations.

Defines contracts for tenant repositories and services following 
protocol-based dependency injection patterns.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable, List, Optional, Dict, Any
from datetime import datetime

from ....core.value_objects import TenantId, OrganizationId
from .tenant import Tenant


@runtime_checkable
class TenantRepository(Protocol):
    """Protocol for tenant data persistence operations."""
    
    @abstractmethod
    async def save(self, tenant: Tenant) -> Tenant:
        """Save tenant to persistent storage."""
        ...
    
    @abstractmethod
    async def find_by_id(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Find tenant by ID."""
        ...
    
    @abstractmethod
    async def find_by_slug(self, slug: str) -> Optional[Tenant]:
        """Find tenant by slug."""
        ...
    
    @abstractmethod
    async def find_by_organization(self, organization_id: OrganizationId) -> List[Tenant]:
        """Find all tenants for an organization."""
        ...
    
    @abstractmethod
    async def find_active(self, limit: Optional[int] = None) -> List[Tenant]:
        """Find active tenants."""
        ...
    
    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant:
        """Update tenant."""
        ...
    
    @abstractmethod
    async def delete(self, tenant_id: TenantId) -> bool:
        """Hard delete tenant."""
        ...
    
    @abstractmethod
    async def exists(self, tenant_id: TenantId) -> bool:
        """Check if tenant exists."""
        ...


@runtime_checkable
class TenantCache(Protocol):
    """Protocol for tenant caching operations."""
    
    @abstractmethod
    async def get(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Get cached tenant."""
        ...
    
    @abstractmethod
    async def set(self, tenant: Tenant, ttl: Optional[int] = None) -> bool:
        """Cache tenant."""
        ...
    
    @abstractmethod
    async def delete(self, tenant_id: TenantId) -> bool:
        """Remove tenant from cache."""
        ...
    
    @abstractmethod
    async def clear_organization(self, organization_id: OrganizationId) -> bool:
        """Clear all cached tenants for an organization."""
        ...


@runtime_checkable
class TenantConfigResolver(Protocol):
    """Protocol for resolving tenant-specific configurations.
    
    Integrates with existing configuration infrastructure to provide
    tenant-specific config resolution without duplication.
    """
    
    @abstractmethod
    async def get_config(self, tenant_id: TenantId, key: str, default: Any = None) -> Any:
        """Get tenant-specific configuration value."""
        ...
    
    @abstractmethod
    async def get_configs(self, tenant_id: TenantId, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Get all tenant configurations, optionally filtered by namespace."""
        ...
    
    @abstractmethod
    async def set_config(self, tenant_id: TenantId, key: str, value: Any) -> bool:
        """Set tenant-specific configuration."""
        ...
    
    @abstractmethod
    async def delete_config(self, tenant_id: TenantId, key: str) -> bool:
        """Delete tenant-specific configuration."""
        ...