"""Realm management service for multi-tenant Keycloak realms."""

import logging
from typing import Dict, List, Optional

from ....core.exceptions.auth import RealmConfigurationError, RealmNotFoundError
from ....core.value_objects.identifiers import RealmId, TenantId
from ..adapters.keycloak_admin import KeycloakAdminAdapter
from ..entities.keycloak_config import KeycloakConfig
from ..entities.protocols import RealmManagerProtocol
from ..entities.realm import Realm
from ..repositories.realm_repository import RealmRepository

logger = logging.getLogger(__name__)


class RealmManager(RealmManagerProtocol):
    """Service for managing multi-tenant Keycloak realms."""
    
    def __init__(
        self,
        realm_repository: RealmRepository,
        keycloak_server_url: str,
        admin_username: str,
        admin_password: str,
        default_client_id: str = "neo-platform",
    ):
        """Initialize realm manager."""
        self.realm_repository = realm_repository
        self.keycloak_server_url = keycloak_server_url
        self.admin_username = admin_username
        self.admin_password = admin_password
        self.default_client_id = default_client_id
        # In-memory storage for custom realm configurations
        self._custom_realm_configs: Dict[str, KeycloakConfig] = {}
        self._custom_realms: Dict[str, Realm] = {}
    
    def register_custom_realm_config(self, realm_id: RealmId, config: KeycloakConfig, tenant_id: Optional[TenantId] = None) -> None:
        """Register a custom realm configuration that doesn't require database storage.
        
        This is useful for platform admin realms or other scenarios where realm configs
        should not be stored in the database.
        
        Args:
            realm_id: The realm identifier
            config: Keycloak configuration for the realm
            tenant_id: Optional tenant ID for multi-tenant scenarios
        """
        logger.debug(f"Registering custom realm config for realm {realm_id.value}")
        
        # Store the config
        self._custom_realm_configs[realm_id.value] = config
        
        # Create a lightweight realm object
        custom_realm = Realm(
            realm_id=realm_id,
            tenant_id=tenant_id,
            name=config.realm_name,
            display_name=f"Custom Realm: {config.realm_name}",
            enabled=True,
            config=config,
            status="active",
        )
        self._custom_realms[realm_id.value] = custom_realm
        
        logger.info(f"Registered custom realm config for {realm_id.value}")
    
    def register_platform_realm_config(self, realm_id: RealmId, config: KeycloakConfig) -> None:
        """Register a platform admin realm configuration.
        
        This is a convenience method for registering platform-level realm configs
        that don't belong to any specific tenant.
        
        Args:
            realm_id: The realm identifier
            config: Keycloak configuration for the realm
        """
        self.register_custom_realm_config(realm_id, config, tenant_id=None)
    
    async def get_realm_config_by_id(self, realm_id: RealmId) -> KeycloakConfig:
        """Get realm configuration by realm ID."""
        logger.debug(f"Getting realm config by ID: {realm_id.value}")
        
        # Check custom realm configs first
        if realm_id.value in self._custom_realm_configs:
            logger.debug(f"Found custom realm config for ID: {realm_id.value}")
            return self._custom_realm_configs[realm_id.value]
        
        # Fall back to database-stored realms
        realm = await self.realm_repository.get_by_id(realm_id)
        if not realm:
            raise RealmNotFoundError(f"Realm configuration not found: {realm_id.value}")
        
        if not realm.config:
            raise RealmConfigurationError(f"Realm has no configuration: {realm_id.value}")
        
        return realm.config
    
    async def get_realm_config(self, tenant_id: TenantId) -> KeycloakConfig:
        """Get realm configuration for tenant."""
        logger.debug(f"Getting realm config for tenant {tenant_id.value}")
        
        # First check custom realm configs by tenant
        for realm_id, realm in self._custom_realms.items():
            if realm.tenant_id == tenant_id and realm.config:
                logger.debug(f"Found custom realm config for tenant {tenant_id.value}")
                return realm.config
        
        # Fall back to database-stored realms
        realm = await self.realm_repository.get_by_tenant_id(tenant_id)
        if not realm:
            raise RealmNotFoundError(f"No realm found for tenant: {tenant_id.value}")
        
        if not realm.config:
            raise RealmConfigurationError(f"Realm has no configuration: {realm.realm_id.value}")
        
        return realm.config
    
    async def create_realm(
        self, 
        tenant_id: TenantId, 
        config: KeycloakConfig,
        realm_settings: Optional[Dict] = None,
    ) -> Realm:
        """Create new realm for tenant."""
        logger.info(f"Creating realm for tenant {tenant_id.value}")
        
        # Check if realm already exists for tenant
        existing_realm = await self.realm_repository.get_by_tenant_id(tenant_id)
        if existing_realm:
            raise RealmConfigurationError(f"Realm already exists for tenant: {tenant_id.value}")
        
        realm_name = self._generate_realm_name(tenant_id)
        display_name = f"Tenant {tenant_id.value} Realm"
        
        try:
            # Create realm in Keycloak
            async with self._get_admin_adapter() as admin:
                realm_data = await admin.create_realm(
                    realm_name=realm_name,
                    display_name=display_name,
                    enabled=True,
                    **(realm_settings or {}),
                )
                
                # Create default client for the realm
                await admin.create_client(
                    realm_name=realm_name,
                    client_id=config.client_id,
                    client_secret=config.client_secret,
                    # Client configuration
                    enabled=True,
                    publicClient=config.client_secret is None,
                    standardFlowEnabled=True,
                    directAccessGrantsEnabled=True,
                    serviceAccountsEnabled=config.client_secret is not None,
                    authorizationServicesEnabled=True,
                )
            
            # Create realm entity
            realm = Realm(
                realm_id=config.realm_id,
                tenant_id=tenant_id,
                name=realm_name,
                display_name=display_name,
                enabled=True,
                config=config,
                status="active",
            )
            
            # Save to repository
            await self.realm_repository.create(realm)
            
            logger.info(f"Successfully created realm {realm_name} for tenant {tenant_id.value}")
            return realm
        
        except Exception as e:
            logger.error(f"Failed to create realm for tenant {tenant_id.value}: {e}")
            
            # Cleanup - try to delete realm from Keycloak if it was created
            try:
                async with self._get_admin_adapter() as admin:
                    await admin.delete_realm(realm_name)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup realm {realm_name}: {cleanup_error}")
            
            raise RealmConfigurationError(f"Failed to create realm: {e}") from e
    
    async def update_realm_settings(self, realm_id: RealmId, settings: Dict) -> None:
        """Update realm settings."""
        logger.info(f"Updating settings for realm {realm_id.value}")
        
        realm = await self.realm_repository.get_by_id(realm_id)
        if not realm:
            raise RealmNotFoundError(f"Realm not found: {realm_id.value}")
        
        try:
            # Update in Keycloak
            async with self._get_admin_adapter() as admin:
                await admin.update_realm(realm.name, settings)
            
            # Update realm metadata
            updated_metadata = realm.metadata.copy()
            updated_metadata.update(settings)
            
            updated_realm = Realm(
                realm_id=realm.realm_id,
                tenant_id=realm.tenant_id,
                name=realm.name,
                display_name=realm.display_name,
                enabled=realm.enabled,
                config=realm.config,
                status=realm.status,
                created_at=realm.created_at,
                metadata=updated_metadata,
            )
            
            await self.realm_repository.update(updated_realm)
            
            logger.info(f"Successfully updated realm {realm_id.value}")
        
        except Exception as e:
            logger.error(f"Failed to update realm {realm_id.value}: {e}")
            raise RealmConfigurationError(f"Failed to update realm: {e}") from e
    
    async def delete_realm(self, realm_id: RealmId) -> None:
        """Delete realm."""
        logger.info(f"Deleting realm {realm_id.value}")
        
        realm = await self.realm_repository.get_by_id(realm_id)
        if not realm:
            raise RealmNotFoundError(f"Realm not found: {realm_id.value}")
        
        try:
            # Delete from Keycloak
            async with self._get_admin_adapter() as admin:
                await admin.delete_realm(realm.name)
            
            # Delete from repository
            await self.realm_repository.delete(realm_id)
            
            logger.info(f"Successfully deleted realm {realm_id.value}")
        
        except Exception as e:
            logger.error(f"Failed to delete realm {realm_id.value}: {e}")
            raise RealmConfigurationError(f"Failed to delete realm: {e}") from e
    
    async def list_realms(self) -> List[Realm]:
        """List all managed realms."""
        logger.debug("Listing all managed realms")
        
        realms = await self.realm_repository.list_all()
        return realms
    
    async def get_realm_by_id(self, realm_id: RealmId) -> Optional[Realm]:
        """Get realm by ID."""
        logger.debug(f"Getting realm by ID: {realm_id.value}")
        
        # First check custom realms
        if realm_id.value in self._custom_realms:
            logger.debug(f"Found custom realm for ID: {realm_id.value}")
            return self._custom_realms[realm_id.value]
        
        # Fall back to database-stored realms
        realm = await self.realm_repository.get_by_id(realm_id)
        return realm
    
    async def get_realm_by_tenant(self, tenant_id: TenantId) -> Optional[Realm]:
        """Get realm by tenant ID."""
        logger.debug(f"Getting realm for tenant: {tenant_id.value}")
        
        # First check custom realms
        for realm in self._custom_realms.values():
            if realm.tenant_id == tenant_id:
                logger.debug(f"Found custom realm for tenant: {tenant_id.value}")
                return realm
        
        # Fall back to database-stored realms
        realm = await self.realm_repository.get_by_tenant_id(tenant_id)
        return realm
    
    async def enable_realm(self, realm_id: RealmId) -> None:
        """Enable a realm."""
        logger.info(f"Enabling realm {realm_id.value}")
        
        await self.update_realm_settings(realm_id, {"enabled": True})
        
        # Update local status
        realm = await self.realm_repository.get_by_id(realm_id)
        if realm:
            updated_realm = Realm(
                realm_id=realm.realm_id,
                tenant_id=realm.tenant_id,
                name=realm.name,
                display_name=realm.display_name,
                enabled=True,
                config=realm.config,
                status="active",
                created_at=realm.created_at,
                metadata=realm.metadata,
            )
            await self.realm_repository.update(updated_realm)
    
    async def disable_realm(self, realm_id: RealmId) -> None:
        """Disable a realm."""
        logger.info(f"Disabling realm {realm_id.value}")
        
        await self.update_realm_settings(realm_id, {"enabled": False})
        
        # Update local status
        realm = await self.realm_repository.get_by_id(realm_id)
        if realm:
            updated_realm = Realm(
                realm_id=realm.realm_id,
                tenant_id=realm.tenant_id,
                name=realm.name,
                display_name=realm.display_name,
                enabled=False,
                config=realm.config,
                status="disabled",
                created_at=realm.created_at,
                metadata=realm.metadata,
            )
            await self.realm_repository.update(updated_realm)
    
    async def sync_realm_with_keycloak(self, realm_id: RealmId) -> Realm:
        """Synchronize realm data with Keycloak."""
        logger.info(f"Syncing realm {realm_id.value} with Keycloak")
        
        realm = await self.realm_repository.get_by_id(realm_id)
        if not realm:
            raise RealmNotFoundError(f"Realm not found: {realm_id.value}")
        
        try:
            # Get current data from Keycloak
            async with self._get_admin_adapter() as admin:
                keycloak_data = await admin.get_realm(realm.name)
            
            # Update realm with Keycloak data
            updated_realm = Realm(
                realm_id=realm.realm_id,
                tenant_id=realm.tenant_id,
                name=realm.name,
                display_name=keycloak_data.get("displayName", realm.display_name),
                enabled=keycloak_data.get("enabled", realm.enabled),
                config=realm.config,
                status="active" if keycloak_data.get("enabled") else "disabled",
                created_at=realm.created_at,
                metadata=realm.metadata,
            )
            
            await self.realm_repository.update(updated_realm)
            
            logger.info(f"Successfully synced realm {realm_id.value}")
            return updated_realm
        
        except Exception as e:
            logger.error(f"Failed to sync realm {realm_id.value}: {e}")
            raise RealmConfigurationError(f"Failed to sync realm: {e}") from e
    
    def _generate_realm_name(self, tenant_id: TenantId) -> str:
        """Generate realm name for tenant."""
        # Use pattern: tenant-{tenant_id}
        return f"tenant-{tenant_id.value}"
    
    def _get_admin_adapter(self) -> KeycloakAdminAdapter:
        """Get Keycloak admin adapter."""
        return KeycloakAdminAdapter(
            server_url=self.keycloak_server_url,
            username=self.admin_username,
            password=self.admin_password,
        )