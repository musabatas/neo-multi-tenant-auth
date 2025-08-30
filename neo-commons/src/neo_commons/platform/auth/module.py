"""Authentication module registration and dependency injection configuration.

This module provides the complete authentication platform module following
maximum separation principles with protocol-based dependency injection.

Usage:
    from neo_commons.platform.auth import AuthModule
    from neo_commons.platform.container import get_container
    
    # Register the module
    container = get_container()
    auth_module = AuthModule()
    container.register_module(auth_module)
    
    # Use dependencies
    from neo_commons.platform.auth.application.commands import AuthenticateUser
    authenticate_command = await container.get(AuthenticateUser)
"""

from typing import Dict, Type, Any, Optional
import logging

from ...platform.module import ModuleProtocol
from ...platform.container import Container
from ...core.shared.application import ApplicationProtocol

# Core Protocol Imports
from .core.protocols import (
    TokenValidator,
    PublicKeyProvider, 
    SessionManager,
    RealmProvider,
    PermissionLoader,
)

# Application Protocol Imports  
from .application.protocols import (
    KeycloakClient,
    TokenCache,
    UserMapper,
    PermissionChecker,
    SessionStore,
)

# Application Command/Query Imports
from .application.commands import (
    AuthenticateUser,
    LogoutUser,
    RefreshToken,
    RevokeToken,
    InvalidateSession,
    ChangePassword,
)

from .application.queries import (
    ValidateToken,
    GetUserContext,
    CheckSessionActive,
    GetTokenMetadata,
    ListUserSessions,
    GetRealmConfig,
)

# Application Service Imports
from .application.services import (
    TokenOrchestrator,
    SessionOrchestrator,
    AuthenticationOrchestrator,
    PermissionOrchestrator,
)

# Application Validator Imports
from .application.validators import (
    TokenFormatValidator,
    SignatureValidator,
    ExpirationValidator,
    AudienceValidator,
    IssuerValidator,
    FreshnessValidator,
)

# Infrastructure Imports
from .infrastructure.repositories import (
    KeycloakTokenRepository,
    RedisSessionRepository,
    MemoryTokenCache,
    DatabaseUserRepository,
    FilePublicKeyRepository,
)

from .infrastructure.adapters import (
    KeycloakAdminAdapter,
    KeycloakOpenIDAdapter,
    PublicKeyCacheAdapter,
    RedisCacheAdapter,
    SMTPNotificationAdapter,
)

from .infrastructure.factories import (
    KeycloakClientFactory,
    TokenValidatorFactory,
    SessionManagerFactory,
    CacheFactory,
)

logger = logging.getLogger(__name__)


class AuthModule(ModuleProtocol):
    """Authentication module with maximum separation architecture.
    
    This module provides enterprise-grade authentication capabilities with:
    - JWT token validation and management
    - Keycloak integration with multi-realm support  
    - Session management with Redis caching
    - Permission-based access control integration
    - Extensible authentication providers
    
    Architecture:
    - Maximum separation: one file = one purpose
    - Protocol-based dependency injection
    - Clean Core with domain objects only
    - Command/query separation in application layer
    - Infrastructure adapters for external systems
    """
    
    def __init__(self):
        """Initialize auth module."""
        self.name = "auth"
        self.version = "1.0.0"
        self._container: Optional[Container] = None
        self._configured = False
        
    async def configure(self, container: Container, config: Dict[str, Any]) -> None:
        """Configure the auth module with dependencies.
        
        Args:
            container: Dependency injection container
            config: Module configuration dictionary
            
        Configuration structure:
        {
            "keycloak": {
                "server_url": "http://localhost:8080",
                "admin_username": "admin",
                "admin_password": "admin"
            },
            "cache": {
                "redis_url": "redis://localhost:6379",
                "token_ttl": 300,
                "session_ttl": 3600
            },
            "security": {
                "verify_signature": True,
                "verify_expiration": True,
                "token_freshness_seconds": 300
            }
        }
        """
        self._container = container
        auth_config = config.get("auth", {})
        
        logger.info("Configuring auth module with maximum separation architecture")
        
        # Register core protocols with default implementations
        await self._register_core_protocols(auth_config)
        
        # Register application layer components
        await self._register_application_layer(auth_config)
        
        # Register infrastructure layer components
        await self._register_infrastructure_layer(auth_config)
        
        # Register API layer components
        await self._register_api_layer(auth_config)
        
        # Register extension system
        await self._register_extensions(auth_config)
        
        self._configured = True
        logger.info("Auth module configuration completed successfully")
    
    async def _register_core_protocols(self, config: Dict[str, Any]) -> None:
        """Register core protocol implementations."""
        logger.debug("Registering core auth protocols")
        
        # Token validation protocol - composition of focused validators
        token_validator_factory = TokenValidatorFactory(config.get("security", {}))
        token_validator = await token_validator_factory.create_validator()
        self._container.register(TokenValidator, token_validator)
        
        # Public key provider protocol
        public_key_config = config.get("public_keys", {})
        if public_key_config.get("provider") == "file":
            public_key_provider = FilePublicKeyRepository(
                key_directory=public_key_config.get("directory", "./keys")
            )
        else:
            # Default to cache-based provider
            public_key_provider = PublicKeyCacheAdapter(
                cache_ttl=public_key_config.get("cache_ttl", 3600)
            )
        self._container.register(PublicKeyProvider, public_key_provider)
        
        # Session manager protocol
        session_config = config.get("sessions", {})
        session_manager_factory = SessionManagerFactory(session_config)
        session_manager = await session_manager_factory.create_session_manager()
        self._container.register(SessionManager, session_manager)
        
        # Realm provider protocol
        realm_config = config.get("realms", {})
        if realm_config.get("provider") == "database":
            # Database-based realm configuration
            realm_provider = DatabaseUserRepository()  # Will implement RealmProvider protocol
        else:
            # Default to Keycloak admin adapter
            realm_provider = KeycloakAdminAdapter(
                server_url=config.get("keycloak", {}).get("server_url"),
                username=config.get("keycloak", {}).get("admin_username"),
                password=config.get("keycloak", {}).get("admin_password"),
            )
        self._container.register(RealmProvider, realm_provider)
        
        logger.debug("Core auth protocols registered successfully")
    
    async def _register_application_layer(self, config: Dict[str, Any]) -> None:
        """Register application layer components."""
        logger.debug("Registering auth application layer")
        
        # Register focused validators (one responsibility each)
        self._container.register(TokenFormatValidator, TokenFormatValidator())
        
        signature_config = config.get("security", {})
        self._container.register(
            SignatureValidator, 
            SignatureValidator(
                verify_signature=signature_config.get("verify_signature", True)
            )
        )
        
        expiration_config = config.get("security", {})
        self._container.register(
            ExpirationValidator,
            ExpirationValidator(
                verify_expiration=expiration_config.get("verify_expiration", True)
            )
        )
        
        self._container.register(AudienceValidator, AudienceValidator())
        self._container.register(IssuerValidator, IssuerValidator())
        
        freshness_config = config.get("security", {})
        self._container.register(
            FreshnessValidator,
            FreshnessValidator(
                max_age_seconds=freshness_config.get("token_freshness_seconds", 300)
            )
        )
        
        # Register orchestration services (compose focused components)
        self._container.register(TokenOrchestrator, TokenOrchestrator)
        self._container.register(SessionOrchestrator, SessionOrchestrator)
        self._container.register(AuthenticationOrchestrator, AuthenticationOrchestrator)
        self._container.register(PermissionOrchestrator, PermissionOrchestrator)
        
        # Register commands (one purpose each)
        self._container.register(AuthenticateUser, AuthenticateUser)
        self._container.register(LogoutUser, LogoutUser)
        self._container.register(RefreshToken, RefreshToken)
        self._container.register(RevokeToken, RevokeToken)
        self._container.register(InvalidateSession, InvalidateSession)
        self._container.register(ChangePassword, ChangePassword)
        
        # Register queries (one purpose each)  
        self._container.register(ValidateToken, ValidateToken)
        self._container.register(GetUserContext, GetUserContext)
        self._container.register(CheckSessionActive, CheckSessionActive)
        self._container.register(GetTokenMetadata, GetTokenMetadata)
        self._container.register(ListUserSessions, ListUserSessions)
        self._container.register(GetRealmConfig, GetRealmConfig)
        
        logger.debug("Auth application layer registered successfully")
    
    async def _register_infrastructure_layer(self, config: Dict[str, Any]) -> None:
        """Register infrastructure layer components."""
        logger.debug("Registering auth infrastructure layer")
        
        # Register repositories (focused on single external system each)
        keycloak_config = config.get("keycloak", {})
        keycloak_token_repo = KeycloakTokenRepository(
            server_url=keycloak_config.get("server_url"),
            admin_credentials={
                "username": keycloak_config.get("admin_username"),
                "password": keycloak_config.get("admin_password"),
            }
        )
        self._container.register(KeycloakTokenRepository, keycloak_token_repo)
        
        # Redis session repository
        cache_config = config.get("cache", {})
        redis_session_repo = RedisSessionRepository(
            redis_url=cache_config.get("redis_url", "redis://localhost:6379"),
            session_ttl=cache_config.get("session_ttl", 3600)
        )
        self._container.register(RedisSessionRepository, redis_session_repo)
        self._container.register(SessionStore, redis_session_repo)  # Protocol binding
        
        # Memory token cache for development
        memory_cache = MemoryTokenCache(
            max_size=cache_config.get("memory_cache_size", 1000),
            ttl_seconds=cache_config.get("token_ttl", 300)
        )
        self._container.register(MemoryTokenCache, memory_cache)
        self._container.register(TokenCache, memory_cache)  # Protocol binding
        
        # Database user repository
        db_user_repo = DatabaseUserRepository()
        self._container.register(DatabaseUserRepository, db_user_repo)
        self._container.register(UserMapper, db_user_repo)  # Protocol binding
        
        # Register adapters (focused on single external service each)
        keycloak_admin_adapter = KeycloakAdminAdapter(
            server_url=keycloak_config.get("server_url"),
            username=keycloak_config.get("admin_username"),
            password=keycloak_config.get("admin_password"),
        )
        self._container.register(KeycloakAdminAdapter, keycloak_admin_adapter)
        
        keycloak_openid_adapter = KeycloakOpenIDAdapter(
            server_url=keycloak_config.get("server_url")
        )
        self._container.register(KeycloakOpenIDAdapter, keycloak_openid_adapter)
        self._container.register(KeycloakClient, keycloak_openid_adapter)  # Protocol binding
        
        # Public key cache adapter
        public_key_cache = PublicKeyCacheAdapter(
            cache_ttl=cache_config.get("public_key_ttl", 3600)
        )
        self._container.register(PublicKeyCacheAdapter, public_key_cache)
        
        # Redis cache adapter
        redis_cache_adapter = RedisCacheAdapter(
            redis_url=cache_config.get("redis_url", "redis://localhost:6379")
        )
        self._container.register(RedisCacheAdapter, redis_cache_adapter)
        
        # SMTP notification adapter (for password reset, etc.)
        smtp_config = config.get("smtp", {})
        smtp_adapter = SMTPNotificationAdapter(
            smtp_host=smtp_config.get("host", "localhost"),
            smtp_port=smtp_config.get("port", 587),
            username=smtp_config.get("username"),
            password=smtp_config.get("password"),
            use_tls=smtp_config.get("use_tls", True),
        )
        self._container.register(SMTPNotificationAdapter, smtp_adapter)
        
        logger.debug("Auth infrastructure layer registered successfully")
    
    async def _register_api_layer(self, config: Dict[str, Any]) -> None:
        """Register API layer components."""
        logger.debug("Registering auth API layer")
        
        # API layer components will be registered when imported
        # This allows services to include only the routers they need
        
        # Dependencies will be injected automatically through container
        # No need to register routers here - they use dependency injection
        
        logger.debug("Auth API layer configuration completed")
    
    async def _register_extensions(self, config: Dict[str, Any]) -> None:
        """Register extension system components.""" 
        logger.debug("Registering auth extension system")
        
        # Extension system will be dynamically loaded
        extensions_config = config.get("extensions", {})
        
        # Hook system configuration
        if extensions_config.get("hooks_enabled", True):
            # Register hook managers when implemented
            pass
        
        # Custom validators configuration  
        custom_validators = extensions_config.get("custom_validators", [])
        for validator_config in custom_validators:
            # Dynamic loading of custom validators when implemented
            pass
        
        logger.debug("Auth extension system registered successfully")
    
    def get_dependencies(self) -> Dict[str, Type[Any]]:
        """Get module dependencies for container registration."""
        return {
            # Core Protocols
            "token_validator": TokenValidator,
            "public_key_provider": PublicKeyProvider,
            "session_manager": SessionManager,
            "realm_provider": RealmProvider,
            
            # Application Commands
            "authenticate_user": AuthenticateUser,
            "logout_user": LogoutUser,
            "refresh_token": RefreshToken,
            "revoke_token": RevokeToken,
            "invalidate_session": InvalidateSession,
            
            # Application Queries
            "validate_token": ValidateToken,
            "get_user_context": GetUserContext,
            "check_session_active": CheckSessionActive,
            "get_token_metadata": GetTokenMetadata,
            
            # Infrastructure Repositories
            "keycloak_token_repository": KeycloakTokenRepository,
            "redis_session_repository": RedisSessionRepository,
            "memory_token_cache": MemoryTokenCache,
            
            # Infrastructure Adapters
            "keycloak_admin_adapter": KeycloakAdminAdapter,
            "keycloak_openid_adapter": KeycloakOpenIDAdapter,
            "public_key_cache_adapter": PublicKeyCacheAdapter,
        }
    
    def get_health_checks(self) -> Dict[str, Any]:
        """Get health check configuration for auth module."""
        return {
            "auth_token_validation": {
                "name": "Token Validation Pipeline",
                "check": "validate_test_token",
                "timeout": 5.0,
                "critical": True,
            },
            "auth_keycloak_connectivity": {
                "name": "Keycloak Connectivity", 
                "check": "check_keycloak_health",
                "timeout": 10.0,
                "critical": True,
            },
            "auth_cache_connectivity": {
                "name": "Cache Connectivity",
                "check": "check_cache_health", 
                "timeout": 5.0,
                "critical": False,
            },
            "auth_session_storage": {
                "name": "Session Storage",
                "check": "check_session_storage",
                "timeout": 5.0,
                "critical": False,
            },
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics configuration for auth module."""
        return {
            "auth_authentication_rate": {
                "name": "Authentication Rate",
                "type": "counter",
                "description": "Number of authentication attempts",
                "labels": ["realm", "status", "provider"],
            },
            "auth_token_validation_duration": {
                "name": "Token Validation Duration",
                "type": "histogram",
                "description": "Time taken for token validation",
                "labels": ["realm", "cached"],
                "buckets": [0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
            },
            "auth_session_count": {
                "name": "Active Session Count",
                "type": "gauge", 
                "description": "Number of active user sessions",
                "labels": ["realm"],
            },
            "auth_cache_hit_rate": {
                "name": "Cache Hit Rate",
                "type": "gauge",
                "description": "Cache hit rate for auth operations",
                "labels": ["cache_type"],
            },
        }
    
    async def startup(self) -> None:
        """Initialize auth module on startup."""
        if not self._configured:
            raise RuntimeError("Auth module not configured. Call configure() first.")
        
        logger.info("Starting auth module")
        
        # Initialize critical components
        if self._container:
            # Test key connections
            try:
                keycloak_client = await self._container.get(KeycloakClient)
                await keycloak_client.health_check()
                logger.info("Keycloak connectivity verified")
            except Exception as e:
                logger.warning(f"Keycloak connectivity issue: {e}")
            
            try:
                session_store = await self._container.get(SessionStore)
                await session_store.health_check()
                logger.info("Session storage connectivity verified")
            except Exception as e:
                logger.warning(f"Session storage connectivity issue: {e}")
        
        logger.info("Auth module startup completed")
    
    async def shutdown(self) -> None:
        """Cleanup auth module on shutdown."""
        logger.info("Shutting down auth module")
        
        if self._container:
            # Cleanup resources
            try:
                session_store = await self._container.get(SessionStore) 
                await session_store.cleanup()
                logger.info("Session storage cleanup completed")
            except Exception as e:
                logger.warning(f"Session storage cleanup issue: {e}")
            
            try:
                token_cache = await self._container.get(TokenCache)
                await token_cache.cleanup()
                logger.info("Token cache cleanup completed") 
            except Exception as e:
                logger.warning(f"Token cache cleanup issue: {e}")
        
        logger.info("Auth module shutdown completed")
    
    @property
    def configured(self) -> bool:
        """Check if module is configured."""
        return self._configured
    
    @property
    def container(self) -> Optional[Container]:
        """Get module container."""
        return self._container