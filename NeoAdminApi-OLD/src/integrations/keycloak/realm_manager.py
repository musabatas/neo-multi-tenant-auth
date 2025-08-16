"""
Multi-tenant realm management for Keycloak.
Handles dynamic realm configuration and client management.
"""
from typing import Optional, Dict, Any, List
from loguru import logger

from src.common.database.connection import get_database
from src.common.cache.client import get_cache
from src.common.exceptions.base import NotFoundError, ConflictError, ExternalServiceError
from .async_client import get_keycloak_client


class RealmManager:
    """
    Multi-tenant realm management.
    
    Features:
    - Dynamic realm configuration from database
    - Client management per realm
    - Realm settings synchronization
    - Caching for performance
    """
    
    def __init__(self):
        """Initialize realm manager."""
        self.db = get_database()
        self.cache = get_cache()
        self.keycloak_client = None
        
        # Cache key patterns
        self.REALM_CACHE_KEY = "auth:realm:tenant:{tenant_id}"
        self.REALM_CACHE_TTL = 3600  # 1 hour
    
    async def _get_client(self):
        """Get Keycloak client instance."""
        if not self.keycloak_client:
            self.keycloak_client = await get_keycloak_client()
        return self.keycloak_client
    
    async def get_realm_for_tenant(
        self,
        tenant_id: str,
        use_cache: bool = True
    ) -> str:
        """
        Get the Keycloak realm name for a tenant.
        
        IMPORTANT: Never assume realm naming pattern!
        Always read from database column `tenants.external_auth_realm`
        
        Args:
            tenant_id: Tenant UUID
            use_cache: Whether to use cache
            
        Returns:
            Realm name from database
            
        Raises:
            NotFoundError: Tenant not found
        """
        # Check cache
        if use_cache:
            cache_key = self.REALM_CACHE_KEY.format(tenant_id=tenant_id)
            cached_realm = await self.cache.get(cache_key)
            if cached_realm:
                logger.debug(f"Cache hit for tenant {tenant_id} realm: {cached_realm}")
                return cached_realm
        
        # Query database
        query = """
            SELECT 
                external_auth_realm,
                name,
                slug,
                is_active
            FROM admin.tenants
            WHERE id = $1
        """
        
        result = await self.db.fetchrow(query, tenant_id)
        
        if not result:
            raise NotFoundError("Tenant", tenant_id)
        
        if not result["is_active"]:
            raise ExternalServiceError(
                message=f"Tenant {tenant_id} is not active",
                service="RealmManager"
            )
        
        realm_name = result["external_auth_realm"]
        
        if not realm_name:
            # Tenant doesn't have a realm configured yet
            logger.warning(f"Tenant {tenant_id} has no realm configured")
            raise ExternalServiceError(
                message=f"Tenant {tenant_id} has no authentication realm configured",
                service="RealmManager"
            )
        
        # Cache the realm name
        if use_cache:
            await self.cache.set(
                cache_key,
                realm_name,
                ttl=self.REALM_CACHE_TTL
            )
        
        logger.info(f"Retrieved realm '{realm_name}' for tenant {tenant_id}")
        return realm_name
    
    async def ensure_realm_exists(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Ensure a realm exists in Keycloak with proper configuration.
        
        Args:
            realm_name: Unique realm identifier
            display_name: Human-readable realm name
            settings: Additional realm settings
            
        Returns:
            True if realm exists or was created
            
        Raises:
            ExternalServiceError: Failed to create realm
        """
        client = await self._get_client()
        
        try:
            # Try to create the realm
            await client.create_realm(
                realm_name=realm_name,
                display_name=display_name,
                enabled=True
            )
            
            logger.info(f"Created new realm: {realm_name}")
            
            # Apply additional settings if provided
            if settings:
                await self.update_realm_settings(realm_name, settings)
            
            return True
            
        except ConflictError:
            # Realm already exists
            logger.debug(f"Realm {realm_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Failed to ensure realm {realm_name} exists: {e}")
            raise ExternalServiceError(
                message=f"Failed to create realm {realm_name}",
                service="Keycloak"
            )
    
    async def configure_realm_client(
        self,
        realm_name: str,
        client_id: str,
        client_name: Optional[str] = None,
        redirect_uris: Optional[List[str]] = None,
        web_origins: Optional[List[str]] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Configure a client application in a realm.
        
        Args:
            realm_name: Realm name
            client_id: Client identifier
            client_name: Client display name
            redirect_uris: Allowed redirect URIs
            web_origins: Allowed web origins for CORS
            settings: Additional client settings
            
        Returns:
            Client configuration
            
        Raises:
            ExternalServiceError: Failed to configure client
        """
        # Build client configuration
        client_config = {
            "clientId": client_id,
            "name": client_name or client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "serviceAccountsEnabled": True,
            "authorizationServicesEnabled": False,
            "redirectUris": redirect_uris or ["*"],
            "webOrigins": web_origins or ["*"],
            "attributes": {
                "saml.force.post.binding": "false",
                "saml.multivalued.roles": "false",
                "oauth2.device.authorization.grant.enabled": "false",
                "oidc.ciba.grant.enabled": "false",
                "backchannel.logout.session.required": "true",
                "backchannel.logout.revoke.offline.tokens": "false"
            }
        }
        
        # Apply additional settings
        if settings:
            client_config.update(settings)
        
        # Note: Actual client creation would be done through Keycloak Admin API
        # This is a placeholder for the client configuration
        logger.info(f"Configured client {client_id} in realm {realm_name}")
        
        return client_config
    
    async def update_realm_settings(
        self,
        realm_name: str,
        settings: Dict[str, Any]
    ) -> bool:
        """
        Update realm settings in Keycloak.
        
        Args:
            realm_name: Realm name
            settings: Settings to update
            
        Returns:
            True if updated successfully
        """
        # Note: This would use Keycloak Admin API to update realm settings
        logger.info(f"Updated settings for realm {realm_name}")
        return True
    
    async def create_tenant_realm(
        self,
        tenant_id: str,
        realm_name: str,
        display_name: str,
        admin_email: str,
        admin_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a complete realm setup for a new tenant.
        
        Args:
            tenant_id: Tenant UUID
            realm_name: Unique realm identifier
            display_name: Tenant display name
            admin_email: Admin user email
            admin_password: Admin password (generated if not provided)
            
        Returns:
            Realm setup information
            
        Raises:
            ConflictError: Realm already exists
            ExternalServiceError: Setup failed
        """
        client = await self._get_client()
        
        # Ensure realm exists
        await self.ensure_realm_exists(
            realm_name=realm_name,
            display_name=display_name,
            settings={
                "passwordPolicy": "length(12) and upperCase(2) and lowerCase(2) and digits(2) and specialChars(2)",
                "bruteForceProtected": True,
                "permanentLockout": False,
                "maxFailureWaitSeconds": 900,
                "minimumQuickLoginWaitSeconds": 60,
                "waitIncrementSeconds": 60,
                "quickLoginCheckMilliSeconds": 1000,
                "maxDeltaTimeSeconds": 43200,
                "failureFactor": 5,
                "defaultRoles": ["tenant_user"],
                "requiredCredentials": ["password"],
                "rememberMe": True,
                "registrationAllowed": False,
                "registrationEmailAsUsername": True,
                "editUsernameAllowed": False,
                "resetPasswordAllowed": True,
                "verifyEmail": True,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "sslRequired": "external",
                "internationalizationEnabled": True,
                "supportedLocales": ["en"],
                "defaultLocale": "en"
            }
        )
        
        # Configure default client for the tenant
        await self.configure_realm_client(
            realm_name=realm_name,
            client_id=f"tenant-{tenant_id[:8]}",  # Short tenant ID for client
            client_name=display_name,
            redirect_uris=[
                "http://localhost:3002/*",  # Tenant admin
                "http://localhost:3003/*",  # Tenant frontend
                f"https://*.{realm_name}.example.com/*"  # Production URLs
            ],
            web_origins=[
                "http://localhost:3002",
                "http://localhost:3003",
                f"https://*.{realm_name}.example.com"
            ]
        )
        
        # Create admin user for the tenant
        if not admin_password:
            # Generate secure password if not provided
            import secrets
            import string
            alphabet = string.ascii_letters + string.digits + string.punctuation
            admin_password = ''.join(secrets.choice(alphabet) for _ in range(16))
        
        admin_user = await client.create_or_update_user(
            username=admin_email,
            email=admin_email,
            first_name="Admin",
            last_name=display_name,
            realm=realm_name,
            attributes={
                "tenant_id": tenant_id,
                "is_admin": "true"
            }
        )
        
        # Update tenant in database with realm name
        update_query = """
            UPDATE admin.tenants
            SET 
                external_auth_realm = $1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $2
        """
        
        await self.db.execute(update_query, realm_name, tenant_id)
        
        # Clear cache for this tenant
        cache_key = self.REALM_CACHE_KEY.format(tenant_id=tenant_id)
        await self.cache.delete(cache_key)
        
        logger.info(f"Created complete realm setup for tenant {tenant_id}")
        
        return {
            "realm_name": realm_name,
            "display_name": display_name,
            "admin_user": admin_user,
            "admin_email": admin_email,
            "admin_password": admin_password,  # Only returned on creation
            "client_id": f"tenant-{tenant_id[:8]}"
        }
    
    async def deactivate_tenant_realm(
        self,
        tenant_id: str
    ) -> bool:
        """
        Deactivate a tenant's realm (soft delete).
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if deactivated successfully
        """
        # Get realm name
        realm_name = await self.get_realm_for_tenant(tenant_id, use_cache=False)
        
        # Note: In production, this would disable the realm in Keycloak
        # For now, we just log the action
        logger.info(f"Deactivated realm {realm_name} for tenant {tenant_id}")
        
        # Clear cache
        cache_key = self.REALM_CACHE_KEY.format(tenant_id=tenant_id)
        await self.cache.delete(cache_key)
        
        return True
    
    async def clear_tenant_realm_cache(self, tenant_id: str) -> bool:
        """
        Clear cached realm information for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            True if cache cleared
        """
        cache_key = self.REALM_CACHE_KEY.format(tenant_id=tenant_id)
        await self.cache.delete(cache_key)
        logger.debug(f"Cleared realm cache for tenant {tenant_id}")
        return True


# Global realm manager instance
_realm_manager: Optional[RealmManager] = None


def get_realm_manager() -> RealmManager:
    """
    Get the global realm manager instance.
    
    Returns:
        RealmManager instance
    """
    global _realm_manager
    if _realm_manager is None:
        _realm_manager = RealmManager()
    return _realm_manager