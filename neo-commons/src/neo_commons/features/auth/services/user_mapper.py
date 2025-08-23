"""User mapping service between Keycloak and platform identities."""

import logging
from typing import Dict, Optional

from ....core.exceptions.auth import UserMappingError
from ....core.value_objects.identifiers import KeycloakUserId, TenantId, UserId
from ....utils.uuid import generate_uuid_v7
from ..entities.protocols import UserMapperProtocol
from ..repositories.user_mapping_repository import UserMappingRepository

logger = logging.getLogger(__name__)


class UserMapper(UserMapperProtocol):
    """Service for mapping between Keycloak and platform user identities."""
    
    def __init__(
        self,
        user_mapping_repository: UserMappingRepository,
    ):
        """Initialize user mapper."""
        self.user_mapping_repository = user_mapping_repository
    
    async def map_keycloak_to_platform(
        self, 
        keycloak_user_id: KeycloakUserId, 
        tenant_id: TenantId,
    ) -> UserId:
        """Map Keycloak user ID to platform user ID."""
        logger.debug(f"Mapping Keycloak user {keycloak_user_id.value} to platform user")
        
        try:
            # Check if mapping already exists
            existing_mapping = await self.user_mapping_repository.get_by_keycloak_id(
                keycloak_user_id, tenant_id
            )
            
            if existing_mapping:
                logger.debug(f"Found existing mapping: {existing_mapping['platform_user_id']}")
                return UserId(existing_mapping["platform_user_id"])
            
            # Create new mapping
            platform_user_id = UserId(generate_uuid_v7())
            
            await self.user_mapping_repository.create_mapping(
                keycloak_user_id=keycloak_user_id,
                platform_user_id=platform_user_id,
                tenant_id=tenant_id,
            )
            
            logger.info(
                f"Created new user mapping: KC={keycloak_user_id.value} -> "
                f"Platform={platform_user_id.value}"
            )
            return platform_user_id
        
        except Exception as e:
            logger.error(f"Failed to map Keycloak user {keycloak_user_id.value}: {e}")
            raise UserMappingError(f"User mapping failed: {e}") from e
    
    async def map_platform_to_keycloak(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> Optional[KeycloakUserId]:
        """Map platform user ID to Keycloak user ID."""
        logger.debug(f"Mapping platform user {platform_user_id.value} to Keycloak user")
        
        try:
            mapping = await self.user_mapping_repository.get_by_platform_id(
                platform_user_id, tenant_id
            )
            
            if not mapping:
                logger.debug(f"No Keycloak mapping found for platform user {platform_user_id.value}")
                return None
            
            keycloak_user_id = KeycloakUserId(mapping["keycloak_user_id"])
            logger.debug(f"Found Keycloak mapping: {keycloak_user_id.value}")
            return keycloak_user_id
        
        except Exception as e:
            logger.error(f"Failed to map platform user {platform_user_id.value}: {e}")
            raise UserMappingError(f"Reverse user mapping failed: {e}") from e
    
    async def create_user_mapping(
        self,
        keycloak_user_id: KeycloakUserId,
        platform_user_id: UserId,
        tenant_id: TenantId,
        user_info: Dict,
    ) -> None:
        """Create user mapping with profile sync."""
        logger.info(
            f"Creating user mapping with profile sync: KC={keycloak_user_id.value} -> "
            f"Platform={platform_user_id.value}"
        )
        
        try:
            # Create the mapping
            await self.user_mapping_repository.create_mapping(
                keycloak_user_id=keycloak_user_id,
                platform_user_id=platform_user_id,
                tenant_id=tenant_id,
                user_info=user_info,
            )
            
            # Sync user profile
            await self.sync_user_profile(platform_user_id, user_info)
            
            logger.info(f"Successfully created user mapping with profile sync")
        
        except Exception as e:
            logger.error(f"Failed to create user mapping: {e}")
            raise UserMappingError(f"User mapping creation failed: {e}") from e
    
    async def sync_user_profile(self, platform_user_id: UserId, user_info: Dict) -> None:
        """Sync user profile from Keycloak to platform."""
        logger.debug(f"Syncing profile for platform user {platform_user_id.value}")
        
        try:
            # Update user profile in platform database
            await self.user_mapping_repository.update_user_profile(
                platform_user_id, user_info
            )
            
            logger.debug(f"Successfully synced profile for user {platform_user_id.value}")
        
        except Exception as e:
            logger.error(f"Failed to sync profile for user {platform_user_id.value}: {e}")
            # Don't raise exception for profile sync failures - mapping is more important
            logger.warning("Continuing despite profile sync failure")
    
    async def delete_user_mapping(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> None:
        """Delete user mapping."""
        logger.info(f"Deleting user mapping for platform user {platform_user_id.value}")
        
        try:
            await self.user_mapping_repository.delete_mapping(platform_user_id, tenant_id)
            
            logger.info(f"Successfully deleted user mapping for {platform_user_id.value}")
        
        except Exception as e:
            logger.error(f"Failed to delete user mapping: {e}")
            raise UserMappingError(f"User mapping deletion failed: {e}") from e
    
    async def get_user_mapping_info(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> Optional[Dict]:
        """Get complete user mapping information."""
        logger.debug(f"Getting mapping info for platform user {platform_user_id.value}")
        
        try:
            mapping_info = await self.user_mapping_repository.get_mapping_info(
                platform_user_id, tenant_id
            )
            
            return mapping_info
        
        except Exception as e:
            logger.error(f"Failed to get user mapping info: {e}")
            raise UserMappingError(f"Failed to get mapping info: {e}") from e
    
    async def update_last_sync(
        self, 
        platform_user_id: UserId, 
        tenant_id: TenantId,
    ) -> None:
        """Update last sync timestamp for user mapping."""
        logger.debug(f"Updating last sync for platform user {platform_user_id.value}")
        
        try:
            await self.user_mapping_repository.update_last_sync(platform_user_id, tenant_id)
        
        except Exception as e:
            logger.error(f"Failed to update last sync: {e}")
            # Non-critical operation, don't raise exception
    
    async def bulk_sync_users(self, tenant_id: TenantId, user_infos: Dict[str, Dict]) -> Dict:
        """Bulk sync multiple users for a tenant."""
        logger.info(f"Bulk syncing {len(user_infos)} users for tenant {tenant_id.value}")
        
        results = {
            "success": [],
            "errors": [],
            "total": len(user_infos),
        }
        
        for keycloak_id, user_info in user_infos.items():
            try:
                keycloak_user_id = KeycloakUserId(keycloak_id)
                platform_user_id = await self.map_keycloak_to_platform(
                    keycloak_user_id, tenant_id
                )
                
                await self.sync_user_profile(platform_user_id, user_info)
                
                results["success"].append({
                    "keycloak_user_id": keycloak_id,
                    "platform_user_id": platform_user_id.value,
                })
            
            except Exception as e:
                logger.error(f"Failed to sync user {keycloak_id}: {e}")
                results["errors"].append({
                    "keycloak_user_id": keycloak_id,
                    "error": str(e),
                })
        
        logger.info(
            f"Bulk sync completed: {len(results['success'])} success, "
            f"{len(results['errors'])} errors"
        )
        return results