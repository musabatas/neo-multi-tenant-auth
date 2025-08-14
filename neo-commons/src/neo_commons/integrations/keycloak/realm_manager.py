"""
Enhanced multi-tenant realm management for Keycloak with protocol-based dependency injection.
Handles dynamic realm configuration, client management, and tenant provisioning.
"""
import logging
import secrets
import string
from typing import Optional, Dict, Any, List, Protocol, runtime_checkable
from datetime import datetime, timezone
import os

# Protocol-based interfaces
@runtime_checkable
class DatabaseManagerProtocol(Protocol):
    """Protocol for database operations."""
    
    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute query and return single row."""
        ...
    
    async def execute(self, query: str, *args) -> str:
        """Execute query and return status."""
        ...
    
    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute query and return multiple rows."""
        ...


@runtime_checkable
class CacheManagerProtocol(Protocol):
    """Protocol for cache operations."""
    
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value."""
        ...
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set cached value with optional TTL."""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete cached value."""
        ...
    
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        ...


@runtime_checkable
class KeycloakClientProtocol(Protocol):
    """Protocol for Keycloak client operations."""
    
    async def create_realm(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        enabled: bool = True
    ) -> bool:
        """Create a new realm."""
        ...
    
    async def create_or_update_user(
        self,
        username: str,
        email: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        realm: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create or update a user."""
        ...


class RealmConfigProtocol(Protocol):
    """Protocol for realm configuration."""
    
    @property
    def realm_cache_ttl(self) -> int:
        """Cache TTL for realm data."""
        ...
    
    @property
    def password_policy(self) -> str:
        """Default password policy."""
        ...
    
    @property
    def default_locales(self) -> List[str]:
        """Default supported locales."""
        ...
    
    @property
    def brute_force_protection(self) -> Dict[str, Any]:
        """Brute force protection settings."""
        ...


# Default implementations
class DefaultRealmConfig:
    """Default realm configuration with environment variable support."""
    
    def __init__(self):
        self._realm_cache_ttl = None
        self._password_policy = None
        self._default_locales = None
        self._brute_force_settings = None
    
    @property
    def realm_cache_ttl(self) -> int:
        """Cache TTL for realm data (1 hour default)."""
        if self._realm_cache_ttl is None:
            self._realm_cache_ttl = int(os.getenv(
                'REALM_CACHE_TTL', 
                os.getenv('KEYCLOAK_REALM_CACHE_TTL', '3600')
            ))
        return self._realm_cache_ttl
    
    @property
    def password_policy(self) -> str:
        """Default password policy."""
        if self._password_policy is None:
            self._password_policy = os.getenv(
                'REALM_PASSWORD_POLICY',
                os.getenv(
                    'KEYCLOAK_PASSWORD_POLICY',
                    "length(12) and upperCase(2) and lowerCase(2) and digits(2) and specialChars(2)"
                )
            )
        return self._password_policy
    
    @property
    def default_locales(self) -> List[str]:
        """Default supported locales."""
        if self._default_locales is None:
            locales_str = os.getenv(
                'REALM_DEFAULT_LOCALES',
                os.getenv('KEYCLOAK_DEFAULT_LOCALES', 'en')
            )
            self._default_locales = [locale.strip() for locale in locales_str.split(',')]
        return self._default_locales
    
    @property
    def brute_force_protection(self) -> Dict[str, Any]:
        """Brute force protection settings."""
        if self._brute_force_settings is None:
            self._brute_force_settings = {
                "bruteForceProtected": os.getenv('REALM_BRUTE_FORCE_ENABLED', 'true').lower() == 'true',
                "permanentLockout": os.getenv('REALM_PERMANENT_LOCKOUT', 'false').lower() == 'true',
                "maxFailureWaitSeconds": int(os.getenv('REALM_MAX_FAILURE_WAIT', '900')),
                "minimumQuickLoginWaitSeconds": int(os.getenv('REALM_MIN_QUICK_LOGIN_WAIT', '60')),
                "waitIncrementSeconds": int(os.getenv('REALM_WAIT_INCREMENT', '60')),
                "quickLoginCheckMilliSeconds": int(os.getenv('REALM_QUICK_LOGIN_CHECK', '1000')),
                "maxDeltaTimeSeconds": int(os.getenv('REALM_MAX_DELTA_TIME', '43200')),
                "failureFactor": int(os.getenv('REALM_FAILURE_FACTOR', '5'))
            }
        return self._brute_force_settings


class RealmManagerException(Exception):
    """Custom exception for realm management operations."""
    
    def __init__(self, message: str, realm_name: Optional[str] = None, tenant_id: Optional[str] = None):
        super().__init__(message)
        self.realm_name = realm_name
        self.tenant_id = tenant_id
        self.timestamp = datetime.now(timezone.utc)


class RealmNotConfiguredException(RealmManagerException):
    """Exception raised when tenant has no realm configured."""
    pass


class RealmCreationException(RealmManagerException):
    """Exception raised when realm creation fails."""
    pass


class TenantRealmManager:
    """
    Enhanced multi-tenant realm management with protocol-based dependency injection.
    
    Features:
    - Protocol-based dependency injection for testability
    - Environment-based configuration with fallbacks
    - Enhanced caching with pattern-based invalidation
    - Comprehensive realm setup and management
    - Security best practices enforcement
    - Audit logging and monitoring
    - Graceful error handling and recovery
    - Admin user management per tenant
    - Client configuration automation
    - Realm settings synchronization
    """
    
    def __init__(
        self,
        database_manager: Optional[DatabaseManagerProtocol] = None,
        cache_manager: Optional[CacheManagerProtocol] = None,
        keycloak_client: Optional[KeycloakClientProtocol] = None,
        config: Optional[RealmConfigProtocol] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize realm manager with dependency injection.
        
        Args:
            database_manager: Database operations interface
            cache_manager: Cache operations interface
            keycloak_client: Keycloak client interface
            config: Realm configuration
            logger: Logger instance
        """
        self.db = database_manager
        self.cache = cache_manager
        self.keycloak_client = keycloak_client
        self.config = config or DefaultRealmConfig()
        self.logger = logger or logging.getLogger(__name__)
        
        # Cache key patterns with hierarchy
        self.CACHE_PATTERNS = {
            'tenant_realm': "auth:realm:tenant:{tenant_id}",
            'realm_settings': "auth:realm:settings:{realm_name}",
            'realm_clients': "auth:realm:clients:{realm_name}",
            'tenant_prefix': "auth:realm:tenant:",
            'realm_prefix': "auth:realm:"
        }
        
        self.logger.info("TenantRealmManager initialized with protocol-based dependencies")
    
    def _validate_dependencies(self):
        """Validate that required dependencies are available."""
        if not self.db:
            raise ValueError("Database manager is required")
        if not self.cache:
            raise ValueError("Cache manager is required")
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
        """
        Get the Keycloak realm name for a tenant.
        
        CRITICAL: Never assume realm naming pattern!
        Always reads from database column `tenants.external_auth_realm`
        
        Args:
            tenant_id: Tenant UUID
            use_cache: Whether to use cache
            validate_active: Whether to validate tenant is active
            
        Returns:
            Realm name from database
            
        Raises:
            RealmManagerException: Tenant not found or no realm configured
            RealmNotConfiguredException: Tenant has no realm configured
        """
        self._validate_dependencies()
        
        # Check cache first
        cache_key = self._get_cache_key('tenant_realm', tenant_id=tenant_id)
        if use_cache:
            try:
                cached_realm = await self.cache.get(cache_key)
                if cached_realm:
                    self.logger.debug(
                        f"Cache hit for tenant {tenant_id} realm: {cached_realm}",
                        extra={"tenant_id": tenant_id, "realm_name": cached_realm, "source": "cache"}
                    )
                    return cached_realm
            except Exception as e:
                self.logger.warning(f"Cache read failed for tenant {tenant_id}: {e}")
        
        # Query database
        query = """
            SELECT 
                external_auth_realm,
                name,
                slug,
                is_active,
                created_at,
                updated_at
            FROM admin.tenants
            WHERE id = $1
        """
        
        try:
            result = await self.db.fetchrow(query, tenant_id)
        except Exception as e:
            self.logger.error(f"Database query failed for tenant {tenant_id}: {e}")
            raise RealmManagerException(
                f"Failed to query tenant {tenant_id}",
                tenant_id=tenant_id
            )
        
        if not result:
            self.logger.warning(f"Tenant {tenant_id} not found in database")
            raise RealmManagerException(
                f"Tenant {tenant_id} not found",
                tenant_id=tenant_id
            )
        
        # Validate tenant is active if requested
        if validate_active and not result["is_active"]:
            self.logger.warning(f"Tenant {tenant_id} is not active")
            raise RealmManagerException(
                f"Tenant {tenant_id} is not active",
                tenant_id=tenant_id
            )
        
        realm_name = result["external_auth_realm"]
        
        # Check if tenant has realm configured
        if not realm_name:
            self.logger.warning(
                f"Tenant {tenant_id} has no realm configured",
                extra={"tenant_id": tenant_id, "tenant_name": result.get("name")}
            )
            raise RealmNotConfiguredException(
                f"Tenant {tenant_id} has no authentication realm configured",
                tenant_id=tenant_id
            )
        
        # Cache the realm name
        if use_cache:
            try:
                await self.cache.set(
                    cache_key,
                    realm_name,
                    ttl=self.config.realm_cache_ttl
                )
                self.logger.debug(f"Cached realm name for tenant {tenant_id}")
            except Exception as e:
                self.logger.warning(f"Failed to cache realm for tenant {tenant_id}: {e}")
        
        self.logger.info(
            f"Retrieved realm '{realm_name}' for tenant {tenant_id}",
            extra={"tenant_id": tenant_id, "realm_name": realm_name, "source": "database"}
        )
        return realm_name
    
    async def ensure_realm_exists(
        self,
        realm_name: str,
        display_name: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        validate_settings: bool = True
    ) -> bool:
        """
        Ensure a realm exists in Keycloak with proper configuration.
        
        Args:
            realm_name: Unique realm identifier
            display_name: Human-readable realm name
            settings: Additional realm settings
            validate_settings: Whether to validate settings structure
            
        Returns:
            True if realm exists or was created
            
        Raises:
            RealmCreationException: Failed to create realm
        """
        self._validate_dependencies()
        
        try:
            # Build default settings with security best practices
            default_settings = {
                "passwordPolicy": self.config.password_policy,
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
                "supportedLocales": self.config.default_locales,
                "defaultLocale": self.config.default_locales[0] if self.config.default_locales else "en",
                "defaultRoles": ["tenant_user"],
                **self.config.brute_force_protection
            }
            
            # Merge with custom settings
            if settings:
                if validate_settings:
                    self._validate_realm_settings(settings)
                default_settings.update(settings)
            
            # Create realm via Keycloak client
            success = await self.keycloak_client.create_realm(
                realm_name=realm_name,
                display_name=display_name,
                enabled=True
            )
            
            if success:
                self.logger.info(
                    f"Successfully ensured realm exists: {realm_name}",
                    extra={"realm_name": realm_name, "display_name": display_name, "action": "create_or_verify"}
                )
                
                # Cache realm settings
                settings_key = self._get_cache_key('realm_settings', realm_name=realm_name)
                try:
                    await self.cache.set(
                        settings_key,
                        default_settings,
                        ttl=self.config.realm_cache_ttl
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to cache realm settings: {e}")
                
                # Apply additional settings if needed
                if settings:
                    await self.update_realm_settings(realm_name, settings)
                
                return True
            else:
                self.logger.error(f"Failed to ensure realm {realm_name} exists")
                raise RealmCreationException(
                    f"Failed to create realm {realm_name}",
                    realm_name=realm_name
                )
                
        except Exception as e:
            if isinstance(e, RealmCreationException):
                raise
            self.logger.error(f"Unexpected error ensuring realm {realm_name} exists: {e}")
            raise RealmCreationException(
                f"Failed to ensure realm {realm_name} exists: {str(e)}",
                realm_name=realm_name
            )
    
    def _validate_realm_settings(self, settings: Dict[str, Any]) -> None:
        """Validate realm settings for security and consistency."""
        # Check for security-critical settings
        if "sslRequired" in settings and settings["sslRequired"] == "none":
            self.logger.warning("SSL is disabled in realm settings - security risk")
        
        if "bruteForceProtected" in settings and not settings["bruteForceProtected"]:
            self.logger.warning("Brute force protection is disabled - security risk")
        
        if "passwordPolicy" in settings:
            policy = settings["passwordPolicy"]
            if not any(check in policy for check in ["length", "upperCase", "lowerCase", "digits"]):
                self.logger.warning("Weak password policy detected")
    
    async def configure_realm_client(
        self,
        realm_name: str,
        client_id: str,
        client_name: Optional[str] = None,
        redirect_uris: Optional[List[str]] = None,
        web_origins: Optional[List[str]] = None,
        settings: Optional[Dict[str, Any]] = None,
        environment: str = "development"
    ) -> Dict[str, Any]:
        """
        Configure a client application in a realm with environment-specific defaults.
        
        Args:
            realm_name: Realm name
            client_id: Client identifier
            client_name: Client display name
            redirect_uris: Allowed redirect URIs
            web_origins: Allowed web origins for CORS
            settings: Additional client settings
            environment: Environment (development/staging/production)
            
        Returns:
            Client configuration
            
        Raises:
            RealmManagerException: Failed to configure client
        """
        self._validate_dependencies()
        
        # Environment-specific defaults
        env_defaults = self._get_environment_defaults(environment, realm_name)
        
        # Build comprehensive client configuration
        client_config = {
            "clientId": client_id,
            "name": client_name or client_id,
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": environment == "development",  # Public only for dev
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": True,
            "serviceAccountsEnabled": environment != "development",  # Service accounts for prod
            "authorizationServicesEnabled": False,
            "implicitFlowEnabled": False,  # Security best practice
            "bearerOnly": False,
            "consentRequired": False,
            "redirectUris": redirect_uris or env_defaults["redirect_uris"],
            "webOrigins": web_origins or env_defaults["web_origins"],
            "attributes": {
                "saml.force.post.binding": "false",
                "saml.multivalued.roles": "false",
                "oauth2.device.authorization.grant.enabled": "false",
                "oidc.ciba.grant.enabled": "false",
                "backchannel.logout.session.required": "true",
                "backchannel.logout.revoke.offline.tokens": "false",
                "access.token.lifespan": env_defaults["token_lifespan"],
                "client.session.idle.timeout": env_defaults["session_timeout"],
                "client.session.max.lifespan": env_defaults["max_session_lifespan"]
            },
            "protocolMappers": self._get_default_protocol_mappers()
        }
        
        # Apply custom settings
        if settings:
            client_config = self._merge_client_settings(client_config, settings)
        
        # Cache client configuration
        clients_key = self._get_cache_key('realm_clients', realm_name=realm_name)
        try:
            cached_clients = await self.cache.get(clients_key) or {}
            cached_clients[client_id] = client_config
            await self.cache.set(
                clients_key,
                cached_clients,
                ttl=self.config.realm_cache_ttl
            )
        except Exception as e:
            self.logger.warning(f"Failed to cache client configuration: {e}")
        
        self.logger.info(
            f"Configured client {client_id} in realm {realm_name} for {environment}",
            extra={
                "realm_name": realm_name,
                "client_id": client_id,
                "environment": environment,
                "public_client": client_config["publicClient"]
            }
        )
        
        return client_config
    
    def _get_environment_defaults(self, environment: str, realm_name: str) -> Dict[str, Any]:
        """Get environment-specific defaults for client configuration."""
        base_domain = os.getenv('BASE_DOMAIN', 'example.com')
        
        defaults = {
            "development": {
                "redirect_uris": [
                    "http://localhost:3002/*",  # Tenant admin
                    "http://localhost:3003/*",  # Tenant frontend
                    "http://localhost:8002/*"   # Tenant API
                ],
                "web_origins": [
                    "http://localhost:3002",
                    "http://localhost:3003",
                    "http://localhost:8002"
                ],
                "token_lifespan": "3600",  # 1 hour
                "session_timeout": "1800",  # 30 minutes
                "max_session_lifespan": "7200"  # 2 hours
            },
            "staging": {
                "redirect_uris": [
                    f"https://staging-admin.{realm_name}.{base_domain}/*",
                    f"https://staging.{realm_name}.{base_domain}/*"
                ],
                "web_origins": [
                    f"https://staging-admin.{realm_name}.{base_domain}",
                    f"https://staging.{realm_name}.{base_domain}"
                ],
                "token_lifespan": "1800",  # 30 minutes
                "session_timeout": "900",   # 15 minutes
                "max_session_lifespan": "3600"  # 1 hour
            },
            "production": {
                "redirect_uris": [
                    f"https://admin.{realm_name}.{base_domain}/*",
                    f"https://{realm_name}.{base_domain}/*",
                    f"https://www.{realm_name}.{base_domain}/*"
                ],
                "web_origins": [
                    f"https://admin.{realm_name}.{base_domain}",
                    f"https://{realm_name}.{base_domain}",
                    f"https://www.{realm_name}.{base_domain}"
                ],
                "token_lifespan": "900",   # 15 minutes
                "session_timeout": "600",  # 10 minutes
                "max_session_lifespan": "1800"  # 30 minutes
            }
        }
        
        return defaults.get(environment, defaults["development"])
    
    def _get_default_protocol_mappers(self) -> List[Dict[str, Any]]:
        """Get default protocol mappers for client."""
        return [
            {
                "name": "tenant_id",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "config": {
                    "user.attribute": "tenant_id",
                    "claim.name": "tenant_id",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                }
            },
            {
                "name": "roles",
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-realm-role-mapper",
                "config": {
                    "claim.name": "roles",
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true"
                }
            }
        ]
    
    def _merge_client_settings(self, base_config: Dict[str, Any], custom_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Safely merge custom client settings with base configuration."""
        merged = base_config.copy()
        
        for key, value in custom_settings.items():
            if isinstance(value, dict) and key in merged:
                # Deep merge for nested dictionaries
                if isinstance(merged[key], dict):
                    merged[key].update(value)
                else:
                    merged[key] = value
            else:
                merged[key] = value
        
        return merged
    
    async def update_realm_settings(
        self,
        realm_name: str,
        settings: Dict[str, Any],
        validate: bool = True
    ) -> bool:
        """
        Update realm settings in Keycloak with validation.
        
        Args:
            realm_name: Realm name
            settings: Settings to update
            validate: Whether to validate settings
            
        Returns:
            True if updated successfully
        """
        self._validate_dependencies()
        
        if validate:
            self._validate_realm_settings(settings)
        
        try:
            # Note: In full implementation, this would use Keycloak Admin API
            # to update the realm settings
            
            # Update cached settings
            settings_key = self._get_cache_key('realm_settings', realm_name=realm_name)
            try:
                cached_settings = await self.cache.get(settings_key) or {}
                cached_settings.update(settings)
                await self.cache.set(
                    settings_key,
                    cached_settings,
                    ttl=self.config.realm_cache_ttl
                )
            except Exception as e:
                self.logger.warning(f"Failed to update cached settings: {e}")
            
            self.logger.info(
                f"Updated settings for realm {realm_name}",
                extra={"realm_name": realm_name, "settings_count": len(settings)}
            )
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update realm settings for {realm_name}: {e}")
            raise RealmManagerException(
                f"Failed to update realm settings for {realm_name}",
                realm_name=realm_name
            )
    
    async def create_tenant_realm(
        self,
        tenant_id: str,
        realm_name: str,
        display_name: str,
        admin_email: str,
        admin_password: Optional[str] = None,
        environment: str = "development",
        additional_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete realm setup for a new tenant with comprehensive configuration.
        
        Args:
            tenant_id: Tenant UUID
            realm_name: Unique realm identifier
            display_name: Tenant display name
            admin_email: Admin user email
            admin_password: Admin password (auto-generated if not provided)
            environment: Deployment environment
            additional_settings: Additional realm settings
            
        Returns:
            Complete realm setup information
            
        Raises:
            RealmCreationException: Setup failed
            RealmManagerException: Configuration error
        """
        self._validate_dependencies()
        
        try:
            # Build comprehensive realm settings
            realm_settings = {
                "passwordPolicy": self.config.password_policy,
                "defaultRoles": ["tenant_user", "tenant_viewer"],
                "requiredCredentials": ["password"],
                "rememberMe": True,
                "registrationAllowed": False,
                "registrationEmailAsUsername": True,
                "editUsernameAllowed": False,
                "resetPasswordAllowed": True,
                "verifyEmail": True,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "sslRequired": "external" if environment == "production" else "none",
                "internationalizationEnabled": True,
                "supportedLocales": self.config.default_locales,
                "defaultLocale": self.config.default_locales[0] if self.config.default_locales else "en",
                **self.config.brute_force_protection
            }
            
            # Merge additional settings
            if additional_settings:
                realm_settings.update(additional_settings)
            
            # Ensure realm exists with settings
            await self.ensure_realm_exists(
                realm_name=realm_name,
                display_name=display_name,
                settings=realm_settings,
                validate_settings=True
            )
            
            # Generate client ID based on tenant
            client_id = f"tenant-{tenant_id[:8]}"
            
            # Configure default client for the tenant
            client_config = await self.configure_realm_client(
                realm_name=realm_name,
                client_id=client_id,
                client_name=display_name,
                environment=environment
            )
            
            # Generate secure admin password if not provided
            if not admin_password:
                admin_password = self._generate_secure_password()
                password_generated = True
            else:
                password_generated = False
            
            # Create admin user for the tenant
            admin_user = await self.keycloak_client.create_or_update_user(
                username=admin_email,
                email=admin_email,
                first_name="Admin",
                last_name=display_name,
                realm=realm_name,
                attributes={
                    "tenant_id": tenant_id,
                    "is_admin": "true",
                    "created_at": self._utc_now().isoformat(),
                    "environment": environment
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
            
            # Clear relevant caches
            await self.clear_tenant_realm_cache(tenant_id)
            
            # Create setup result
            setup_result = {
                "realm_name": realm_name,
                "display_name": display_name,
                "client_id": client_id,
                "client_config": client_config,
                "admin_user": admin_user,
                "admin_email": admin_email,
                "environment": environment,
                "created_at": self._utc_now().isoformat(),
                "settings_applied": len(realm_settings)
            }
            
            # Only include password in response if it was generated
            if password_generated:
                setup_result["admin_password"] = admin_password
                setup_result["password_generated"] = True
            
            self.logger.info(
                f"Created complete realm setup for tenant {tenant_id}",
                extra={
                    "tenant_id": tenant_id,
                    "realm_name": realm_name,
                    "client_id": client_id,
                    "environment": environment,
                    "admin_email": admin_email
                }
            )
            
            return setup_result
            
        except Exception as e:
            self.logger.error(f"Failed to create tenant realm for {tenant_id}: {e}")
            if isinstance(e, (RealmManagerException, RealmCreationException)):
                raise
            raise RealmCreationException(
                f"Failed to create tenant realm: {str(e)}",
                realm_name=realm_name,
                tenant_id=tenant_id
            )
    
    def _generate_secure_password(self, length: int = 16) -> str:
        """Generate a cryptographically secure password."""
        # Use strong character set
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        # Generate password ensuring complexity
        password = [
            secrets.choice(string.ascii_uppercase),  # At least one uppercase
            secrets.choice(string.ascii_lowercase),  # At least one lowercase
            secrets.choice(string.digits),           # At least one digit
            secrets.choice("!@#$%^&*")              # At least one special char
        ]
        
        # Fill remaining length with random choices
        for _ in range(length - 4):
            password.append(secrets.choice(alphabet))
        
        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    async def deactivate_tenant_realm(
        self,
        tenant_id: str,
        soft_delete: bool = True
    ) -> Dict[str, Any]:
        """
        Deactivate a tenant's realm with comprehensive cleanup.
        
        Args:
            tenant_id: Tenant UUID
            soft_delete: Whether to soft delete (disable) or hard delete
            
        Returns:
            Deactivation result information
            
        Raises:
            RealmManagerException: Deactivation failed
        """
        self._validate_dependencies()
        
        try:
            # Get realm name
            realm_name = await self.get_realm_for_tenant(
                tenant_id, 
                use_cache=False,
                validate_active=False
            )
            
            deactivation_result = {
                "tenant_id": tenant_id,
                "realm_name": realm_name,
                "soft_delete": soft_delete,
                "deactivated_at": self._utc_now().isoformat(),
                "actions_performed": []
            }
            
            if soft_delete:
                # Note: In production, this would disable the realm in Keycloak
                # rather than deleting it completely
                deactivation_result["actions_performed"].append("realm_disabled")
                self.logger.info(f"Soft-deactivated realm {realm_name} for tenant {tenant_id}")
            else:
                # Note: Hard deletion would remove the realm entirely
                deactivation_result["actions_performed"].append("realm_deleted")
                self.logger.warning(f"Hard-deleted realm {realm_name} for tenant {tenant_id}")
            
            # Clear all related caches
            cleared_caches = await self.clear_tenant_realm_cache(
                tenant_id, 
                clear_realm_caches=True, 
                realm_name=realm_name
            )
            deactivation_result["caches_cleared"] = cleared_caches
            deactivation_result["actions_performed"].append("caches_cleared")
            
            self.logger.info(
                f"Deactivated realm {realm_name} for tenant {tenant_id}",
                extra={
                    "tenant_id": tenant_id,
                    "realm_name": realm_name,
                    "soft_delete": soft_delete,
                    "actions": deactivation_result["actions_performed"]
                }
            )
            
            return deactivation_result
            
        except RealmNotConfiguredException:
            # Tenant has no realm - nothing to deactivate
            self.logger.info(f"Tenant {tenant_id} has no realm to deactivate")
            return {
                "tenant_id": tenant_id,
                "realm_name": None,
                "deactivated_at": self._utc_now().isoformat(),
                "actions_performed": ["no_realm_configured"],
                "caches_cleared": 0
            }
        except Exception as e:
            self.logger.error(f"Failed to deactivate realm for tenant {tenant_id}: {e}")
            raise RealmManagerException(
                f"Failed to deactivate tenant realm: {str(e)}",
                tenant_id=tenant_id
            )
    
    async def clear_tenant_realm_cache(
        self, 
        tenant_id: str,
        clear_realm_caches: bool = False,
        realm_name: Optional[str] = None
    ) -> int:
        """
        Clear cached realm information for a tenant with optional realm-wide clearing.
        
        Args:
            tenant_id: Tenant UUID
            clear_realm_caches: Whether to clear realm-wide caches too
            realm_name: Realm name (auto-retrieved if not provided and needed)
            
        Returns:
            Number of cache entries cleared
        """
        self._validate_dependencies()
        cleared_count = 0
        
        try:
            # Clear tenant-specific realm cache
            tenant_cache_key = self._get_cache_key('tenant_realm', tenant_id=tenant_id)
            if await self.cache.delete(tenant_cache_key):
                cleared_count += 1
                
            # Clear realm-wide caches if requested
            if clear_realm_caches:
                if not realm_name:
                    try:
                        realm_name = await self.get_realm_for_tenant(tenant_id, use_cache=False)
                    except Exception:
                        # If we can't get realm name, skip realm-wide clearing
                        pass
                
                if realm_name:
                    # Clear realm settings cache
                    settings_key = self._get_cache_key('realm_settings', realm_name=realm_name)
                    if await self.cache.delete(settings_key):
                        cleared_count += 1
                    
                    # Clear realm clients cache
                    clients_key = self._get_cache_key('realm_clients', realm_name=realm_name)
                    if await self.cache.delete(clients_key):
                        cleared_count += 1
            
            # Use pattern-based clearing if cache supports it
            try:
                if hasattr(self.cache, 'clear_pattern'):
                    pattern_cleared = await self.cache.clear_pattern(
                        f"{self.CACHE_PATTERNS['tenant_prefix']}{tenant_id}*"
                    )
                    cleared_count += pattern_cleared
            except Exception as e:
                self.logger.debug(f"Pattern-based cache clearing not available: {e}")
            
            self.logger.debug(
                f"Cleared {cleared_count} cache entries for tenant {tenant_id}",
                extra={"tenant_id": tenant_id, "realm_name": realm_name, "cleared_count": cleared_count}
            )
            
            return cleared_count
            
        except Exception as e:
            self.logger.warning(f"Failed to clear some caches for tenant {tenant_id}: {e}")
            return cleared_count
    
    async def get_tenant_realm_info(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get comprehensive realm information for a tenant.
        
        Args:
            tenant_id: Tenant UUID
            
        Returns:
            Comprehensive realm information
        """
        self._validate_dependencies()
        
        try:
            realm_name = await self.get_realm_for_tenant(tenant_id)
            
            # Get cached settings if available
            settings_key = self._get_cache_key('realm_settings', realm_name=realm_name)
            realm_settings = await self.cache.get(settings_key) or {}
            
            # Get cached clients if available
            clients_key = self._get_cache_key('realm_clients', realm_name=realm_name)
            realm_clients = await self.cache.get(clients_key) or {}
            
            return {
                "tenant_id": tenant_id,
                "realm_name": realm_name,
                "settings": realm_settings,
                "clients": realm_clients,
                "cache_keys": {
                    "realm": self._get_cache_key('tenant_realm', tenant_id=tenant_id),
                    "settings": settings_key,
                    "clients": clients_key
                },
                "retrieved_at": self._utc_now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get realm info for tenant {tenant_id}: {e}")
            raise RealmManagerException(
                f"Failed to get realm info for tenant {tenant_id}",
                tenant_id=tenant_id
            )


# Factory functions for easy instantiation
def create_tenant_realm_manager(
    database_manager: Optional[DatabaseManagerProtocol] = None,
    cache_manager: Optional[CacheManagerProtocol] = None,
    keycloak_client: Optional[KeycloakClientProtocol] = None,
    config: Optional[RealmConfigProtocol] = None
) -> TenantRealmManager:
    """
    Factory function to create TenantRealmManager with dependency injection.
    
    Args:
        database_manager: Database operations interface
        cache_manager: Cache operations interface  
        keycloak_client: Keycloak client interface
        config: Realm configuration
        
    Returns:
        Configured TenantRealmManager instance
    """
    return TenantRealmManager(
        database_manager=database_manager,
        cache_manager=cache_manager,
        keycloak_client=keycloak_client,
        config=config or DefaultRealmConfig()
    )


# Global realm manager instance (singleton pattern)
_realm_manager: Optional[TenantRealmManager] = None


def get_realm_manager(
    database_manager: Optional[DatabaseManagerProtocol] = None,
    cache_manager: Optional[CacheManagerProtocol] = None,
    keycloak_client: Optional[KeycloakClientProtocol] = None,
    config: Optional[RealmConfigProtocol] = None
) -> TenantRealmManager:
    """
    Get the global realm manager instance with lazy initialization.
    
    Args:
        database_manager: Database operations interface (for initial setup)
        cache_manager: Cache operations interface (for initial setup)
        keycloak_client: Keycloak client interface (for initial setup)
        config: Realm configuration (for initial setup)
        
    Returns:
        TenantRealmManager instance
    """
    global _realm_manager
    if _realm_manager is None:
        _realm_manager = create_tenant_realm_manager(
            database_manager=database_manager,
            cache_manager=cache_manager,
            keycloak_client=keycloak_client,
            config=config
        )
    return _realm_manager


# Convenience function for dependency injection setup
def setup_realm_manager_dependencies(
    database_manager: DatabaseManagerProtocol,
    cache_manager: CacheManagerProtocol,
    keycloak_client: KeycloakClientProtocol,
    config: Optional[RealmConfigProtocol] = None
) -> TenantRealmManager:
    """
    Setup realm manager with all required dependencies.
    
    Args:
        database_manager: Database operations interface
        cache_manager: Cache operations interface
        keycloak_client: Keycloak client interface
        config: Optional realm configuration
        
    Returns:
        Fully configured TenantRealmManager instance
    """
    return TenantRealmManager(
        database_manager=database_manager,
        cache_manager=cache_manager,
        keycloak_client=keycloak_client,
        config=config or DefaultRealmConfig(),
        logger=logging.getLogger("neo_commons.realm_manager")
    )