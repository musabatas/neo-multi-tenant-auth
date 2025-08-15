"""
Focused multi-tenant realm management for Keycloak.

Core realm management functionality with essential operations only.
"""
import logging
import secrets
import string
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ..protocols.realm_protocols import (
    DatabaseManagerProtocol, 
    CacheManagerProtocol, 
    KeycloakClientProtocol, 
    RealmConfigProtocol
)
from ..config.realm_config import DefaultRealmConfig
from ..exceptions.realm_exceptions import RealmManagerException, RealmNotConfiguredException, RealmCreationException


class TenantRealmManager:
    """
    Focused multi-tenant realm management.
    
    Essential realm operations for tenant provisioning.
    """
    
    def __init__(
        self,
        database_manager: Optional[DatabaseManagerProtocol] = None,
        cache_manager: Optional[CacheManagerProtocol] = None,
        keycloak_client: Optional[KeycloakClientProtocol] = None,
        config: Optional[RealmConfigProtocol] = None,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize realm manager."""
        self.db = database_manager
        self.cache = cache_manager
        self.keycloak_client = keycloak_client
        self.config = config or DefaultRealmConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Cache patterns
        self.CACHE_PATTERNS = {
            'tenant_realm': "auth:realm:tenant:{tenant_id}",
            'realm_settings': "auth:realm:settings:{realm_name}",
            'realm_prefix': "auth:realm:"
        }
        
        self.logger.info("TenantRealmManager initialized")
    
    def _validate_dependencies(self):
        """Validate required dependencies."""
        if not self.db:
            raise ValueError("Database manager is required")
        if not self.keycloak_client:
            raise ValueError("Keycloak client is required")
    
    def _get_cache_key(self, pattern: str, **kwargs) -> str:
        """Get formatted cache key from pattern."""
        return self.CACHE_PATTERNS[pattern].format(**kwargs)
    
    def _utc_now(self) -> datetime:
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)
    
    async def get_realm_for_tenant(
        self,
        tenant_id: str,
        use_cache: bool = True,
        validate_active: bool = True
    ) -> str:
        """Get the Keycloak realm name for a tenant."""
        self._validate_dependencies()
        
        cache_key = self._get_cache_key('tenant_realm', tenant_id=tenant_id)
        
        # Check cache first
        if use_cache and self.cache:
            cached_realm = await self.cache.get(cache_key)
            if cached_realm:
                self.logger.debug(f"Retrieved cached realm for tenant {tenant_id}: {cached_realm}")
                return cached_realm
        
        # Query database
        query = """
            SELECT 
                tr.realm_name,
                tr.is_active
            FROM admin.tenant_realms tr
            INNER JOIN admin.tenants t ON tr.tenant_id = t.id
            WHERE tr.tenant_id = $1
        """
        
        row = await self.db.fetchrow(query, tenant_id)
        if not row:
            raise RealmNotConfiguredException(
                f"No realm configured for tenant {tenant_id}",
                tenant_id=tenant_id
            )
        
        if validate_active and not row['is_active']:
            raise RealmNotConfiguredException(
                f"Realm for tenant {tenant_id} is not active",
                tenant_id=tenant_id,
                realm_name=row['realm_name']
            )
        
        realm_name = row['realm_name']
        
        # Cache result
        if use_cache and self.cache:
            await self.cache.set(cache_key, realm_name, self.config.realm_cache_ttl)
        
        self.logger.info(f"Retrieved realm for tenant {tenant_id}: {realm_name}")
        return realm_name
    
    async def ensure_realm_exists(
        self,
        tenant_id: str,
        realm_name: Optional[str] = None,
        create_if_missing: bool = True
    ) -> str:
        """Ensure realm exists for tenant."""
        self._validate_dependencies()
        
        try:
            # Try to get existing realm
            return await self.get_realm_for_tenant(tenant_id, validate_active=False)
        except RealmNotConfiguredException:
            if not create_if_missing:
                raise
            
            # Create new realm
            if not realm_name:
                realm_name = f"tenant-{tenant_id}"
            
            return await self.create_tenant_realm(tenant_id, realm_name)
    
    async def create_tenant_realm(
        self,
        tenant_id: str,
        realm_name: str,
        admin_email: Optional[str] = None
    ) -> str:
        """Create new tenant realm."""
        self._validate_dependencies()
        
        try:
            # Check if realm already exists in database
            existing_query = """
                SELECT realm_name FROM admin.tenant_realms 
                WHERE tenant_id = $1 OR realm_name = $2
            """
            existing = await self.db.fetchrow(existing_query, tenant_id, realm_name)
            if existing:
                raise RealmCreationException(
                    f"Realm already exists for tenant {tenant_id} or realm name {realm_name} is taken",
                    realm_name=realm_name,
                    tenant_id=tenant_id
                )
            
            # Create realm in Keycloak
            realm_created = await self.keycloak_client.create_realm(
                realm_name=realm_name,
                display_name=f"Tenant {tenant_id} Realm",
                enabled=True
            )
            
            if not realm_created:
                raise RealmCreationException(
                    f"Failed to create Keycloak realm {realm_name}",
                    realm_name=realm_name,
                    tenant_id=tenant_id
                )
            
            # Store in database
            insert_query = """
                INSERT INTO admin.tenant_realms (
                    tenant_id, realm_name, keycloak_realm_id, is_active,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
            """
            
            await self.db.execute(
                insert_query,
                tenant_id,
                realm_name,
                realm_name,  # Using realm_name as keycloak_realm_id
                True,
                self._utc_now(),
                self._utc_now()
            )
            
            # Create admin user if email provided
            if admin_email:
                await self._create_realm_admin_user(realm_name, admin_email, tenant_id)
            
            # Configure basic realm settings
            await self._configure_basic_realm_settings(realm_name)
            
            # Clear cache
            if self.cache:
                cache_key = self._get_cache_key('tenant_realm', tenant_id=tenant_id)
                await self.cache.delete(cache_key)
            
            self.logger.info(f"Successfully created realm {realm_name} for tenant {tenant_id}")
            return realm_name
            
        except Exception as e:
            self.logger.error(f"Failed to create realm for tenant {tenant_id}: {e}")
            raise RealmCreationException(
                f"Realm creation failed: {str(e)}",
                realm_name=realm_name,
                tenant_id=tenant_id
            ) from e
    
    async def _configure_basic_realm_settings(self, realm_name: str) -> bool:
        """Configure basic realm settings."""
        try:
            # Basic realm configuration
            realm_config = {
                "enabled": True,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "editUsernameAllowed": False,
                "bruteForceProtected": True,
                "displayName": f"Realm {realm_name}",
                "passwordPolicy": self.config.password_policy
            }
            
            # Apply brute force protection settings
            realm_config.update(self.config.brute_force_protection)
            
            # Cache configuration
            if self.cache:
                cache_key = self._get_cache_key('realm_settings', realm_name=realm_name)
                await self.cache.set(cache_key, realm_config, self.config.realm_cache_ttl)
            
            self.logger.info(f"Basic realm configuration applied for {realm_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to configure realm {realm_name}: {e}")
            return False
    
    async def _create_realm_admin_user(
        self,
        realm_name: str,
        admin_email: str,
        tenant_id: str
    ) -> Optional[str]:
        """Create admin user for realm."""
        try:
            # Generate secure password
            password = self._generate_secure_password()
            username = f"admin-{tenant_id}"
            
            # Create user via Keycloak client
            user_data = await self.keycloak_client.create_or_update_user(
                username=username,
                email=admin_email,
                first_name="Tenant",
                last_name="Admin",
                realm=realm_name,
                attributes={
                    "tenant_id": tenant_id,
                    "role": "tenant_admin",
                    "created_by": "system"
                }
            )
            
            if user_data:
                self.logger.info(f"Created admin user {username} for realm {realm_name}")
                return user_data.get('id')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create admin user for realm {realm_name}: {e}")
            return None
    
    def _generate_secure_password(self, length: int = 16) -> str:
        """Generate secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    async def deactivate_tenant_realm(self, tenant_id: str, soft_delete: bool = True) -> bool:
        """Deactivate tenant realm."""
        self._validate_dependencies()
        
        try:
            if soft_delete:
                # Mark as inactive
                query = """
                    UPDATE admin.tenant_realms 
                    SET is_active = false, updated_at = $2
                    WHERE tenant_id = $1
                """
                await self.db.execute(query, tenant_id, self._utc_now())
            else:
                # Hard delete
                query = "DELETE FROM admin.tenant_realms WHERE tenant_id = $1"
                await self.db.execute(query, tenant_id)
            
            # Clear cache
            if self.cache:
                cache_key = self._get_cache_key('tenant_realm', tenant_id=tenant_id)
                await self.cache.delete(cache_key)
            
            self.logger.info(f"Deactivated realm for tenant {tenant_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to deactivate realm for tenant {tenant_id}: {e}")
            return False
    
    async def clear_tenant_realm_cache(self, tenant_id: Optional[str] = None) -> int:
        """Clear tenant realm cache."""
        if not self.cache:
            return 0
        
        try:
            cleared_count = 0
            
            if tenant_id:
                cache_key = self._get_cache_key('tenant_realm', tenant_id=tenant_id)
                if await self.cache.delete(cache_key):
                    cleared_count += 1
            else:
                # Clear all realm-related cache
                cleared_count = await self.cache.clear_pattern(self.CACHE_PATTERNS['realm_prefix'] + "*")
            
            self.logger.info(f"Cleared {cleared_count} cache entries")
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            return 0
    
    async def get_tenant_realm_info(self, tenant_id: str) -> Dict[str, Any]:
        """Get basic tenant realm information."""
        self._validate_dependencies()
        
        query = """
            SELECT 
                tr.realm_name,
                tr.keycloak_realm_id,
                tr.is_active,
                tr.created_at,
                tr.updated_at,
                t.name as tenant_name,
                t.slug as tenant_slug
            FROM admin.tenant_realms tr
            INNER JOIN admin.tenants t ON tr.tenant_id = t.id
            WHERE tr.tenant_id = $1
        """
        
        row = await self.db.fetchrow(query, tenant_id)
        if not row:
            raise RealmNotConfiguredException(
                f"No realm configured for tenant {tenant_id}",
                tenant_id=tenant_id
            )
        
        return {
            "tenant_id": tenant_id,
            "realm_name": row['realm_name'],
            "keycloak_realm_id": row['keycloak_realm_id'],
            "is_active": row['is_active'],
            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
            "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
            "tenant_name": row['tenant_name'],
            "tenant_slug": row['tenant_slug']
        }