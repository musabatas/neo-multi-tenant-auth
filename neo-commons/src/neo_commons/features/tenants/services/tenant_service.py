"""Tenant service implementation using existing neo-commons infrastructure.

This service orchestrates tenant operations using dependency injection
without duplicating existing cache, database, or configuration logic.
"""

import logging
from typing import List, Optional, Dict, Any

from ....core.value_objects import TenantId, OrganizationId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError
from ..entities.tenant import Tenant
from ..entities.protocols import TenantRepository, TenantCache, TenantConfigResolver


logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant operations using existing infrastructure.
    
    Orchestrates tenant repository, cache, and configuration without
    duplicating existing neo-commons services.
    """
    
    def __init__(
        self,
        repository: TenantRepository,
        cache: Optional[TenantCache] = None,
        config_resolver: Optional[TenantConfigResolver] = None
    ):
        """Initialize with injected dependencies.
        
        Args:
            repository: Tenant repository implementation
            cache: Optional tenant cache implementation
            config_resolver: Optional tenant config resolver
        """
        self._repository = repository
        self._cache = cache
        self._config_resolver = config_resolver
    
    async def create_tenant(
        self,
        organization_id: OrganizationId,
        slug: str,
        name: str,
        **kwargs
    ) -> Tenant:
        """Create new tenant."""
        try:
            # Check if slug already exists
            existing = await self.get_by_slug(slug)
            if existing:
                raise EntityAlreadyExistsError(f"Tenant with slug '{slug}' already exists")
            
            # Create tenant entity
            tenant = Tenant(
                id=TenantId.generate(),
                organization_id=organization_id,
                slug=slug,
                name=name,
                **kwargs
            )
            
            # Save to repository
            saved_tenant = await self._repository.save(tenant)
            
            # Cache if available
            if self._cache:
                await self._cache.set(saved_tenant)
            
            logger.info(f"Created tenant {saved_tenant.id} with slug '{slug}'")
            return saved_tenant
            
        except Exception as e:
            logger.error(f"Failed to create tenant with slug '{slug}': {e}")
            raise
    
    async def get_by_id(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Get tenant by ID with caching."""
        try:
            # Check cache first
            if self._cache:
                cached = await self._cache.get(tenant_id)
                if cached:
                    return cached
            
            # Get from repository
            tenant = await self._repository.find_by_id(tenant_id)
            
            # Cache if found
            if tenant and self._cache:
                await self._cache.set(tenant)
            
            return tenant
            
        except Exception as e:
            logger.error(f"Failed to get tenant {tenant_id}: {e}")
            raise
    
    async def get_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        try:
            return await self._repository.find_by_slug(slug)
            
        except Exception as e:
            logger.error(f"Failed to get tenant by slug '{slug}': {e}")
            raise
    
    async def get_by_organization(self, organization_id: OrganizationId) -> List[Tenant]:
        """Get all tenants for an organization."""
        try:
            return await self._repository.find_by_organization(organization_id)
            
        except Exception as e:
            logger.error(f"Failed to get tenants for organization {organization_id}: {e}")
            raise
    
    async def get_active_tenants(self, limit: Optional[int] = None) -> List[Tenant]:
        """Get active tenants."""
        try:
            return await self._repository.find_active(limit)
            
        except Exception as e:
            logger.error(f"Failed to get active tenants: {e}")
            raise
    
    async def update_tenant(self, tenant: Tenant) -> Tenant:
        """Update tenant."""
        try:
            # Update in repository
            updated_tenant = await self._repository.update(tenant)
            
            # Invalidate cache
            if self._cache:
                await self._cache.delete(tenant.id)
            
            logger.info(f"Updated tenant {tenant.id}")
            return updated_tenant
            
        except Exception as e:
            logger.error(f"Failed to update tenant {tenant.id}: {e}")
            raise
    
    async def delete_tenant(self, tenant_id: TenantId, hard_delete: bool = False) -> bool:
        """Delete tenant (soft delete by default)."""
        try:
            if hard_delete:
                # Hard delete
                result = await self._repository.delete(tenant_id)
            else:
                # Soft delete
                tenant = await self.get_by_id(tenant_id)
                if not tenant:
                    raise EntityNotFoundError(f"Tenant {tenant_id} not found")
                
                tenant.soft_delete()
                await self._repository.update(tenant)
                result = True
            
            # Clear from cache
            if self._cache:
                await self._cache.delete(tenant_id)
            
            logger.info(f"Deleted tenant {tenant_id} (hard={hard_delete})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to delete tenant {tenant_id}: {e}")
            raise
    
    async def provision_tenant(self, tenant_id: TenantId) -> Tenant:
        """Start tenant provisioning process."""
        try:
            tenant = await self.get_by_id(tenant_id)
            if not tenant:
                raise EntityNotFoundError(f"Tenant {tenant_id} not found")
            
            tenant.start_provisioning()
            updated_tenant = await self.update_tenant(tenant)
            
            logger.info(f"Started provisioning for tenant {tenant_id}")
            return updated_tenant
            
        except Exception as e:
            logger.error(f"Failed to start provisioning for tenant {tenant_id}: {e}")
            raise
    
    async def activate_tenant(self, tenant_id: TenantId) -> Tenant:
        """Activate tenant."""
        try:
            tenant = await self.get_by_id(tenant_id)
            if not tenant:
                raise EntityNotFoundError(f"Tenant {tenant_id} not found")
            
            if tenant.is_provisioning:
                tenant.complete_provisioning()
            else:
                tenant.activate()
            
            updated_tenant = await self.update_tenant(tenant)
            
            logger.info(f"Activated tenant {tenant_id}")
            return updated_tenant
            
        except Exception as e:
            logger.error(f"Failed to activate tenant {tenant_id}: {e}")
            raise
    
    async def suspend_tenant(self, tenant_id: TenantId, reason: Optional[str] = None) -> Tenant:
        """Suspend tenant."""
        try:
            tenant = await self.get_by_id(tenant_id)
            if not tenant:
                raise EntityNotFoundError(f"Tenant {tenant_id} not found")
            
            tenant.suspend(reason)
            updated_tenant = await self.update_tenant(tenant)
            
            logger.info(f"Suspended tenant {tenant_id}: {reason}")
            return updated_tenant
            
        except Exception as e:
            logger.error(f"Failed to suspend tenant {tenant_id}: {e}")
            raise
    
    async def get_tenant_config(self, tenant_id: TenantId, key: str, default: Any = None) -> Any:
        """Get tenant-specific configuration using config resolver."""
        if not self._config_resolver:
            logger.warning(f"No config resolver available for tenant {tenant_id}")
            return default
        
        try:
            return await self._config_resolver.get_config(tenant_id, key, default)
            
        except Exception as e:
            logger.error(f"Failed to get config {key} for tenant {tenant_id}: {e}")
            return default
    
    async def set_tenant_config(self, tenant_id: TenantId, key: str, value: Any) -> bool:
        """Set tenant-specific configuration using config resolver."""
        if not self._config_resolver:
            logger.warning(f"No config resolver available for tenant {tenant_id}")
            return False
        
        try:
            return await self._config_resolver.set_config(tenant_id, key, value)
            
        except Exception as e:
            logger.error(f"Failed to set config {key} for tenant {tenant_id}: {e}")
            return False
    
    async def update_tenant_activity(self, tenant_id: TenantId) -> bool:
        """Update tenant last activity timestamp."""
        try:
            tenant = await self.get_by_id(tenant_id)
            if not tenant:
                return False
            
            tenant.update_last_activity()
            await self.update_tenant(tenant)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update activity for tenant {tenant_id}: {e}")
            return False
    
    async def tenant_exists(self, tenant_id: TenantId) -> bool:
        """Check if tenant exists."""
        try:
            return await self._repository.exists(tenant_id)
            
        except Exception as e:
            logger.error(f"Failed to check tenant existence {tenant_id}: {e}")
            return False