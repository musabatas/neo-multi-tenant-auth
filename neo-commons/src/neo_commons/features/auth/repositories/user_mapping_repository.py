"""Repository for user mapping data persistence."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from ....core.value_objects.identifiers import KeycloakUserId, TenantId, UserId
from ....utils.uuid import generate_uuid_v7

logger = logging.getLogger(__name__)


class UserMappingRepository:
    """Repository for managing user ID mapping persistence."""
    
    def __init__(self, database_service):
        """Initialize user mapping repository."""
        if not database_service:
            raise ValueError("Database service is required")
        self.database_service = database_service
    
    async def create_mapping(
        self,
        keycloak_user_id: KeycloakUserId,
        platform_user_id: UserId,
        tenant_id: TenantId,
        user_info: Optional[Dict] = None,
    ) -> None:
        """Create a new user mapping."""
        logger.info(
            f"Creating user mapping: KC={keycloak_user_id.value} -> "
            f"Platform={platform_user_id.value}"
        )
        
        # For now, this is handled by UserRepository directly
        # User mapping is implicit through external_user_id field in users table
        logger.info(f"User mapping handled by UserRepository for KC user {keycloak_user_id.value}")
    
    async def get_by_keycloak_id(
        self, 
        keycloak_user_id: KeycloakUserId, 
        tenant_id: TenantId,
    ) -> Optional[Dict]:
        """Get mapping by Keycloak user ID."""
        logger.debug(f"Getting mapping for Keycloak user {keycloak_user_id.value}")
        
        mapping_key = f"{keycloak_user_id.value}:{tenant_id.value}"
        
        # TODO: Implement actual database query
        mapping = self._mappings.get(mapping_key)
        
        if mapping:
            logger.debug(f"Found mapping for Keycloak user {keycloak_user_id.value}")
        else:
            logger.debug(f"No mapping found for Keycloak user {keycloak_user_id.value}")
        
        return mapping
    
    async def get_by_platform_id(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> Optional[Dict]:
        """Get mapping by platform user ID."""
        logger.debug(f"Getting mapping for platform user {platform_user_id.value}")
        
        # TODO: Implement actual database query with platform_user_id index
        for mapping in self._mappings.values():
            if (
                mapping["platform_user_id"] == platform_user_id.value
                and mapping["tenant_id"] == tenant_id.value
            ):
                logger.debug(f"Found mapping for platform user {platform_user_id.value}")
                return mapping
        
        logger.debug(f"No mapping found for platform user {platform_user_id.value}")
        return None
    
    async def update_user_profile(self, platform_user_id: UserId, user_info: Dict) -> None:
        """Update user profile information."""
        logger.debug(f"Updating profile for platform user {platform_user_id.value}")
        
        try:
            # TODO: Implement actual database update
            self._profiles[platform_user_id.value] = {
                **user_info,
                "updated_at": datetime.now(timezone.utc),
            }
            
            logger.debug(f"Successfully updated profile for user {platform_user_id.value}")
        
        except Exception as e:
            logger.error(f"Failed to update profile for user {platform_user_id.value}: {e}")
            raise
    
    async def delete_mapping(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> None:
        """Delete user mapping."""
        logger.info(f"Deleting mapping for platform user {platform_user_id.value}")
        
        # TODO: Implement actual database deletion
        mapping_to_delete = None
        
        for key, mapping in self._mappings.items():
            if (
                mapping["platform_user_id"] == platform_user_id.value
                and mapping["tenant_id"] == tenant_id.value
            ):
                mapping_to_delete = key
                break
        
        if mapping_to_delete:
            del self._mappings[mapping_to_delete]
            logger.info(f"Successfully deleted mapping for user {platform_user_id.value}")
        else:
            logger.warning(f"No mapping found to delete for user {platform_user_id.value}")
        
        # Also clean up profile
        if platform_user_id.value in self._profiles:
            del self._profiles[platform_user_id.value]
    
    async def get_mapping_info(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> Optional[Dict]:
        """Get complete user mapping information."""
        logger.debug(f"Getting mapping info for platform user {platform_user_id.value}")
        
        mapping = await self.get_by_platform_id(platform_user_id, tenant_id)
        if not mapping:
            return None
        
        profile = self._profiles.get(platform_user_id.value, {})
        
        return {
            "mapping": mapping,
            "profile": profile,
        }
    
    async def update_last_sync(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> None:
        """Update last sync timestamp."""
        logger.debug(f"Updating last sync for platform user {platform_user_id.value}")
        
        # TODO: Implement actual database update
        for mapping in self._mappings.values():
            if (
                mapping["platform_user_id"] == platform_user_id.value
                and mapping["tenant_id"] == tenant_id.value
            ):
                mapping["last_sync"] = datetime.now(timezone.utc)
                break
    
    async def list_mappings_by_tenant(self, tenant_id: TenantId) -> List[Dict]:
        """List all user mappings for a tenant."""
        logger.debug(f"Listing mappings for tenant {tenant_id.value}")
        
        # TODO: Implement actual database query
        mappings = [
            mapping for mapping in self._mappings.values()
            if mapping["tenant_id"] == tenant_id.value
        ]
        
        logger.debug(f"Found {len(mappings)} mappings for tenant {tenant_id.value}")
        return mappings
    
    async def cleanup_stale_mappings(self, days_threshold: int = 90) -> int:
        """Cleanup mappings that haven't been synced recently."""
        logger.info(f"Cleaning up mappings not synced in {days_threshold} days")
        
        cutoff_date = datetime.now(timezone.utc) - timezone.timedelta(days=days_threshold)
        
        # TODO: Implement actual database cleanup
        stale_keys = []
        
        for key, mapping in self._mappings.items():
            last_sync = mapping.get("last_sync", mapping["created_at"])
            if last_sync < cutoff_date:
                stale_keys.append(key)
        
        for key in stale_keys:
            del self._mappings[key]
        
        logger.info(f"Cleaned up {len(stale_keys)} stale mappings")
        return len(stale_keys)
    
    async def get_mapping_stats(self, tenant_id: TenantId) -> Dict:
        """Get mapping statistics for a tenant."""
        logger.debug(f"Getting mapping stats for tenant {tenant_id.value}")
        
        mappings = await self.list_mappings_by_tenant(tenant_id)
        
        # Calculate stats
        total_mappings = len(mappings)
        recent_sync = 0
        
        week_ago = datetime.now(timezone.utc) - timezone.timedelta(days=7)
        
        for mapping in mappings:
            last_sync = mapping.get("last_sync", mapping["created_at"])
            if last_sync >= week_ago:
                recent_sync += 1
        
        return {
            "total_mappings": total_mappings,
            "recent_sync_count": recent_sync,
            "stale_sync_count": total_mappings - recent_sync,
            "sync_rate": recent_sync / total_mappings if total_mappings > 0 else 0,
        }
    
    # TODO: Add actual database implementation methods:
    # async def _execute_query(self, query: str, params: Dict) -> Any:
    # async def _fetch_one(self, query: str, params: Dict) -> Optional[Dict]:
    # async def _fetch_all(self, query: str, params: Dict) -> List[Dict]:
    # def _mapping_from_row(self, row: Dict) -> Dict:
    # def _mapping_to_insert_params(self, mapping: Dict) -> Dict: