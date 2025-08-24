"""Tenant cache adapter that implements TenantCache protocol using existing cache infrastructure."""

import logging
from typing import Optional
import json

from ....core.value_objects import TenantId, OrganizationId
from ....features.cache.entities.protocols import Cache
from ..entities.tenant import Tenant
from ..entities.protocols import TenantCache


logger = logging.getLogger(__name__)


class TenantCacheAdapter:
    """Adapter that implements TenantCache protocol using existing cache infrastructure.
    
    Converts tenant entities to/from cache format and integrates with
    existing cache service without duplication.
    """
    
    def __init__(self, cache: Cache, ttl: int = 3600):
        """Initialize with existing cache service.
        
        Args:
            cache: Existing cache service from neo-commons
            ttl: Time-to-live for cached tenants in seconds
        """
        self._cache = cache
        self._ttl = ttl
        self._tenant_prefix = "tenant"
        self._org_prefix = "org_tenants"
    
    def _make_tenant_key(self, tenant_id: TenantId) -> str:
        """Create cache key for tenant."""
        return f"{self._tenant_prefix}:{tenant_id.value}"
    
    def _make_org_key(self, organization_id: OrganizationId) -> str:
        """Create cache key for organization tenants."""
        return f"{self._org_prefix}:{organization_id.value}"
    
    def _serialize_tenant(self, tenant: Tenant) -> str:
        """Serialize tenant to JSON string."""
        try:
            tenant_dict = {
                "id": str(tenant.id.value),
                "organization_id": str(tenant.organization_id.value),
                "slug": tenant.slug,
                "name": tenant.name,
                "description": tenant.description,
                "schema_name": tenant.schema_name,
                "database_name": tenant.database_name,
                "custom_domain": tenant.custom_domain,
                "deployment_type": tenant.deployment_type.value,
                "environment": tenant.environment,
                "region_id": tenant.region_id,
                "database_connection_id": tenant.database_connection_id,
                "external_auth_provider": tenant.external_auth_provider,
                "external_auth_realm": tenant.external_auth_realm,
                "external_user_id": tenant.external_user_id,
                "external_auth_metadata": tenant.external_auth_metadata,
                "allow_impersonations": tenant.allow_impersonations,
                "status": tenant.status.value,
                "internal_notes": tenant.internal_notes,
                "features_enabled": tenant.features_enabled,
                "feature_overrides": tenant.feature_overrides,
                "provisioned_at": tenant.provisioned_at.isoformat() if tenant.provisioned_at else None,
                "activated_at": tenant.activated_at.isoformat() if tenant.activated_at else None,
                "suspended_at": tenant.suspended_at.isoformat() if tenant.suspended_at else None,
                "last_activity_at": tenant.last_activity_at.isoformat() if tenant.last_activity_at else None,
                "metadata": tenant.metadata,
                "created_at": tenant.created_at.isoformat(),
                "updated_at": tenant.updated_at.isoformat(),
                "deleted_at": tenant.deleted_at.isoformat() if tenant.deleted_at else None
            }
            return json.dumps(tenant_dict)
        except Exception as e:
            logger.error(f"Failed to serialize tenant {tenant.id}: {e}")
            raise
    
    def _deserialize_tenant(self, data: str) -> Tenant:
        """Deserialize tenant from JSON string."""
        try:
            from datetime import datetime
            from ....config.constants import TenantStatus, DeploymentType
            
            tenant_dict = json.loads(data)
            
            return Tenant(
                id=TenantId(tenant_dict["id"]),
                organization_id=OrganizationId(tenant_dict["organization_id"]),
                slug=tenant_dict["slug"],
                name=tenant_dict["name"],
                description=tenant_dict.get("description"),
                schema_name=tenant_dict.get("schema_name", ""),
                database_name=tenant_dict.get("database_name"),
                custom_domain=tenant_dict.get("custom_domain"),
                deployment_type=DeploymentType(tenant_dict.get("deployment_type", "schema")),
                environment=tenant_dict.get("environment", "production"),
                region_id=tenant_dict.get("region_id"),
                database_connection_id=tenant_dict.get("database_connection_id"),
                external_auth_provider=tenant_dict.get("external_auth_provider", "keycloak"),
                external_auth_realm=tenant_dict.get("external_auth_realm", ""),
                external_user_id=tenant_dict.get("external_user_id", ""),
                external_auth_metadata=tenant_dict.get("external_auth_metadata", {}),
                allow_impersonations=tenant_dict.get("allow_impersonations", False),
                status=TenantStatus(tenant_dict.get("status", "pending")),
                internal_notes=tenant_dict.get("internal_notes"),
                features_enabled=tenant_dict.get("features_enabled", {}),
                feature_overrides=tenant_dict.get("feature_overrides", {}),
                provisioned_at=datetime.fromisoformat(tenant_dict["provisioned_at"]) if tenant_dict.get("provisioned_at") else None,
                activated_at=datetime.fromisoformat(tenant_dict["activated_at"]) if tenant_dict.get("activated_at") else None,
                suspended_at=datetime.fromisoformat(tenant_dict["suspended_at"]) if tenant_dict.get("suspended_at") else None,
                last_activity_at=datetime.fromisoformat(tenant_dict["last_activity_at"]) if tenant_dict.get("last_activity_at") else None,
                metadata=tenant_dict.get("metadata", {}),
                created_at=datetime.fromisoformat(tenant_dict["created_at"]),
                updated_at=datetime.fromisoformat(tenant_dict["updated_at"]),
                deleted_at=datetime.fromisoformat(tenant_dict["deleted_at"]) if tenant_dict.get("deleted_at") else None
            )
        except Exception as e:
            logger.error(f"Failed to deserialize tenant: {e}")
            raise
    
    async def get(self, tenant_id: TenantId) -> Optional[Tenant]:
        """Get cached tenant."""
        try:
            key = self._make_tenant_key(tenant_id)
            cached_data = await self._cache.get(key)
            
            if cached_data:
                return self._deserialize_tenant(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached tenant {tenant_id}: {e}")
            return None
    
    async def set(self, tenant: Tenant, ttl: Optional[int] = None) -> bool:
        """Cache tenant."""
        try:
            key = self._make_tenant_key(tenant.id)
            serialized = self._serialize_tenant(tenant)
            
            effective_ttl = ttl or self._ttl
            await self._cache.set(key, serialized, ttl=effective_ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to cache tenant {tenant.id}: {e}")
            return False
    
    async def delete(self, tenant_id: TenantId) -> bool:
        """Remove tenant from cache."""
        try:
            key = self._make_tenant_key(tenant_id)
            return await self._cache.delete(key)
            
        except Exception as e:
            logger.error(f"Failed to delete cached tenant {tenant_id}: {e}")
            return False
    
    async def clear_organization(self, organization_id: OrganizationId) -> bool:
        """Clear all cached tenants for an organization."""
        try:
            # Clear the organization tenants list cache
            org_key = self._make_org_key(organization_id)
            await self._cache.delete(org_key)
            
            # Note: We don't clear individual tenant caches here as they
            # might be accessed independently. They'll expire naturally.
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear organization cache {organization_id}: {e}")
            return False