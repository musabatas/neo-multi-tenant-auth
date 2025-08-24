"""Tenant router dependencies following auth feature patterns.

Provides protocol-based dependency injection for tenant operations
with database connection and schema flexibility.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from fastapi import HTTPException, status, Request
from ....core.value_objects import TenantId, OrganizationId
from ....core.exceptions import EntityNotFoundError, ValidationError
from ..entities.protocols import TenantRepository, TenantCache, TenantConfigResolver
from ..entities.tenant import Tenant


logger = logging.getLogger(__name__)


@dataclass
class TenantDependencies:
    """Tenant dependencies container following auth feature pattern.
    
    Accepts protocol interfaces for flexible dependency injection
    with database connection and schema parameters.
    """
    
    tenant_repository: TenantRepository
    tenant_cache: Optional[TenantCache] = None
    config_resolver: Optional[TenantConfigResolver] = None
    
    async def get_tenant_by_id(self, tenant_id: TenantId) -> Tenant:
        """Get tenant by ID with caching and error handling."""
        try:
            # Try cache first
            if self.tenant_cache:
                cached_tenant = await self.tenant_cache.get(tenant_id)
                if cached_tenant:
                    return cached_tenant
            
            # Get from repository
            tenant = await self.tenant_repository.find_by_id(tenant_id)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id.value} not found"
                )
            
            # Cache if available
            if self.tenant_cache:
                await self.tenant_cache.set(tenant)
            
            return tenant
            
        except EntityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {tenant_id.value} not found"
            )
        except Exception as e:
            logger.error(f"Failed to get tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve tenant"
            )
    
    async def get_tenant_by_slug(self, slug: str) -> Tenant:
        """Get tenant by slug with error handling."""
        try:
            tenant = await self.tenant_repository.find_by_slug(slug)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant '{slug}' not found"
                )
            
            return tenant
            
        except EntityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{slug}' not found"
            )
        except Exception as e:
            logger.error(f"Failed to get tenant by slug '{slug}': {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve tenant"
            )
    
    async def get_organization_tenants(self, organization_id: OrganizationId) -> list[Tenant]:
        """Get all tenants for an organization."""
        try:
            return await self.tenant_repository.find_by_organization(organization_id)
            
        except Exception as e:
            logger.error(f"Failed to get tenants for organization {organization_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve organization tenants"
            )
    
    async def validate_tenant_access(
        self, 
        tenant_id: TenantId, 
        required_status: Optional[str] = None,
        require_active: bool = True
    ) -> Tenant:
        """Validate tenant access and status requirements."""
        tenant = await self.get_tenant_by_id(tenant_id)
        
        if require_active and not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tenant {tenant_id.value} is not active"
            )
        
        if required_status and tenant.status.value != required_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant must be in '{required_status}' status, currently '{tenant.status.value}'"
            )
        
        return tenant
    
    async def validate_organization_access(
        self, 
        organization_id: OrganizationId,
        user_organizations: Optional[list[str]] = None
    ) -> bool:
        """Validate user access to organization (placeholder for future auth integration)."""
        # TODO: Integrate with auth service for proper organization access validation
        # For now, allow all access - applications can override this dependency
        return True
    
    async def get_tenant_config(
        self, 
        tenant_id: TenantId, 
        key: str, 
        default: Any = None
    ) -> Any:
        """Get tenant-specific configuration."""
        if not self.config_resolver:
            return default
        
        try:
            return await self.config_resolver.get_config(tenant_id, key, default)
            
        except Exception as e:
            logger.error(f"Failed to get config {key} for tenant {tenant_id}: {e}")
            return default
    
    async def set_tenant_config(
        self, 
        tenant_id: TenantId, 
        key: str, 
        value: Any
    ) -> bool:
        """Set tenant-specific configuration."""
        if not self.config_resolver:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Tenant configuration not available"
            )
        
        try:
            return await self.config_resolver.set_config(tenant_id, key, value)
            
        except Exception as e:
            logger.error(f"Failed to set config {key} for tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set tenant configuration"
            )
    
    async def invalidate_tenant_cache(self, tenant_id: TenantId) -> bool:
        """Invalidate tenant cache."""
        if not self.tenant_cache:
            return True
        
        try:
            return await self.tenant_cache.delete(tenant_id)
            
        except Exception as e:
            logger.error(f"Failed to invalidate cache for tenant {tenant_id}: {e}")
            return False
    
    async def validate_tenant_creation(
        self, 
        slug: str, 
        organization_id: OrganizationId
    ) -> None:
        """Validate tenant creation requirements."""
        # Check if slug already exists
        try:
            existing = await self.tenant_repository.find_by_slug(slug)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tenant with slug '{slug}' already exists"
                )
        except EntityNotFoundError:
            # Slug is available
            pass
        
        # Validate organization access
        await self.validate_organization_access(organization_id)
        
        # Additional validation can be added here
        # e.g., organization limits, subscription checks, etc.