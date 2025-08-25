"""Organization cache adapter using existing cache infrastructure.

Provides organization caching without duplicating existing cache logic.
Uses existing cache service with organization-specific key patterns.
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from ....core.value_objects import OrganizationId, UserId
from ....features.cache.entities.protocols import Cache
from ..entities.organization import Organization
from ..entities.protocols import OrganizationCache


logger = logging.getLogger(__name__)


class OrganizationCacheAdapter:
    """Cache adapter for organization operations.
    
    Uses existing cache infrastructure without duplication.
    Follows DRY principles by reusing existing cache patterns.
    """
    
    def __init__(self, cache_service: Cache, key_prefix: str = "org"):
        """Initialize with existing cache service.
        
        Args:
            cache_service: Cache implementation from neo-commons
            key_prefix: Key prefix for organization cache keys
        """
        self._cache = cache_service
        self._key_prefix = key_prefix
        self._default_ttl = 3600  # 1 hour default
    
    def _make_key(self, suffix: str) -> str:
        """Create cache key with prefix."""
        return f"{self._key_prefix}:{suffix}"
    
    def _make_id_key(self, organization_id: OrganizationId) -> str:
        """Create cache key for organization ID."""
        return self._make_key(f"id:{organization_id.value}")
    
    def _make_slug_key(self, slug: str) -> str:
        """Create cache key for organization slug."""
        return self._make_key(f"slug:{slug}")
    
    def _make_user_key(self, user_id: UserId) -> str:
        """Create cache key for user organizations."""
        return self._make_key(f"user:{user_id.value}")
    
    async def get(self, organization_id: OrganizationId) -> Optional[Organization]:
        """Get cached organization."""
        try:
            key = self._make_id_key(organization_id)
            cached_data = await self._cache.get(key)
            
            if cached_data:
                return self._deserialize_organization(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached organization {organization_id}: {e}")
            return None
    
    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        """Get cached organization by slug."""
        try:
            key = self._make_slug_key(slug)
            cached_data = await self._cache.get(key)
            
            if cached_data:
                return self._deserialize_organization(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached organization by slug '{slug}': {e}")
            return None
    
    async def set(self, organization: Organization, ttl: Optional[int] = None) -> bool:
        """Cache organization with dual key storage (ID and slug)."""
        try:
            if ttl is None:
                ttl = self._default_ttl
            
            serialized_data = self._serialize_organization(organization)
            
            # Cache by ID
            id_key = self._make_id_key(organization.id)
            id_result = await self._cache.set(id_key, serialized_data, ttl)
            
            # Cache by slug
            slug_key = self._make_slug_key(organization.slug)
            slug_result = await self._cache.set(slug_key, serialized_data, ttl)
            
            # Both should succeed
            success = id_result and slug_result
            if success:
                logger.debug(f"Cached organization {organization.id} with slug '{organization.slug}'")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to cache organization {organization.id}: {e}")
            return False
    
    async def delete(self, organization_id: OrganizationId) -> bool:
        """Remove organization from cache."""
        try:
            # Get organization first to find slug
            organization = await self.get(organization_id)
            
            # Delete by ID
            id_key = self._make_id_key(organization_id)
            id_result = await self._cache.delete(id_key)
            
            # Delete by slug if we found the organization
            slug_result = True
            if organization:
                slug_key = self._make_slug_key(organization.slug)
                slug_result = await self._cache.delete(slug_key)
                
                # Clear user cache if primary contact exists
                if organization.primary_contact_id:
                    user_id = UserId(organization.primary_contact_id)
                    await self.clear_user_organizations(user_id)
            
            success = id_result and slug_result
            if success:
                logger.debug(f"Deleted cached organization {organization_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete cached organization {organization_id}: {e}")
            return False
    
    async def delete_by_slug(self, slug: str) -> bool:
        """Remove organization from cache by slug."""
        try:
            # Get organization first to find ID
            organization = await self.get_by_slug(slug)
            
            if organization:
                return await self.delete(organization.id)
            
            # If not found, just delete the slug key
            slug_key = self._make_slug_key(slug)
            return await self._cache.delete(slug_key)
            
        except Exception as e:
            logger.error(f"Failed to delete cached organization by slug '{slug}': {e}")
            return False
    
    async def clear_user_organizations(self, user_id: UserId) -> bool:
        """Clear cached organizations for a user (as primary contact)."""
        try:
            # Delete user-specific cache pattern
            user_key = self._make_user_key(user_id)
            result = await self._cache.delete(user_key)
            
            # Could also implement pattern-based deletion if cache supports it
            # Pattern: org:user:{user_id}:*
            pattern_key = self._make_key(f"user:{user_id.value}:*")
            if hasattr(self._cache, 'delete_pattern'):
                await self._cache.delete_pattern(pattern_key)
            
            if result:
                logger.debug(f"Cleared user organizations cache for {user_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to clear user organizations cache for {user_id}: {e}")
            return False
    
    def _serialize_organization(self, organization: Organization) -> str:
        """Serialize organization to JSON string."""
        try:
            data = {
                "id": str(organization.id.value),
                "name": organization.name,
                "slug": organization.slug,
                "legal_name": organization.legal_name,
                "tax_id": organization.tax_id,
                "business_type": organization.business_type,
                "industry": organization.industry,
                "company_size": organization.company_size,
                "website_url": organization.website_url,
                "primary_contact_id": organization.primary_contact_id,
                "address_line1": organization.address_line1,
                "address_line2": organization.address_line2,
                "city": organization.city,
                "state_province": organization.state_province,
                "postal_code": organization.postal_code,
                "country_code": organization.country_code,
                "default_timezone": organization.default_timezone,
                "default_locale": organization.default_locale,
                "default_currency": organization.default_currency,
                "logo_url": organization.logo_url,
                "brand_colors": organization.brand_colors,
                "is_active": organization.is_active,
                "verified_at": organization.verified_at.isoformat() if organization.verified_at else None,
                "verification_documents": organization.verification_documents,
                "created_at": organization.created_at.isoformat(),
                "updated_at": organization.updated_at.isoformat(),
                "deleted_at": organization.deleted_at.isoformat() if organization.deleted_at else None,
                "_cached_at": datetime.utcnow().isoformat()
            }
            return json.dumps(data)
            
        except Exception as e:
            logger.error(f"Failed to serialize organization {organization.id}: {e}")
            raise
    
    def _deserialize_organization(self, cached_data: str) -> Organization:
        """Deserialize JSON string to organization entity."""
        try:
            data = json.loads(cached_data)
            
            return Organization(
                id=OrganizationId(data["id"]),
                name=data["name"],
                slug=data["slug"],
                legal_name=data.get("legal_name"),
                tax_id=data.get("tax_id"),
                business_type=data.get("business_type"),
                industry=data.get("industry"),
                company_size=data.get("company_size"),
                website_url=data.get("website_url"),
                primary_contact_id=data.get("primary_contact_id"),
                address_line1=data.get("address_line1"),
                address_line2=data.get("address_line2"),
                city=data.get("city"),
                state_province=data.get("state_province"),
                postal_code=data.get("postal_code"),
                country_code=data.get("country_code"),
                default_timezone=data.get("default_timezone", "UTC"),
                default_locale=data.get("default_locale", "en-US"),
                default_currency=data.get("default_currency", "USD"),
                logo_url=data.get("logo_url"),
                brand_colors=data.get("brand_colors", {}),
                is_active=data.get("is_active", True),
                verified_at=datetime.fromisoformat(data["verified_at"]) if data.get("verified_at") else None,
                verification_documents=data.get("verification_documents", []),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                deleted_at=datetime.fromisoformat(data["deleted_at"]) if data.get("deleted_at") else None
            )
            
        except Exception as e:
            logger.error(f"Failed to deserialize organization data: {e}")
            raise