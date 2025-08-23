"""Auth feature module - Keycloak multi-tenant authentication and authorization.

This module provides comprehensive authentication and authorization capabilities:
- Multi-realm Keycloak integration (one realm per tenant)
- JWT validation with public key caching
- Automatic Keycloak-to-platform user ID mapping
- Redis caching for performance optimization
- FastAPI dependencies for route protection
- Protocol-based design for flexibility

Key Components:
- AuthService: Main orchestration service
- RealmManager: Multi-realm management
- TokenService: JWT lifecycle management
- UserMapper: User ID mapping service
- RedisAuthCache: Performance caching
- AuthDependencies: FastAPI route protection

Usage Example:
```python
from neo_commons.features.auth import (
    create_auth_service_factory,
    configure_auth_middleware,
    require_permission,
    require_tenant_admin,
    get_current_user,
)

# Initialize services
factory = create_auth_service_factory(
    keycloak_server_url="http://localhost:8080",
    keycloak_admin_username="admin",
    keycloak_admin_password="admin",
    redis_url="redis://localhost:6379"
)

# Configure FastAPI app
auth_deps = await factory.get_auth_dependencies()
realm_manager = await factory.get_realm_manager()
configure_auth_middleware(app, auth_deps, realm_manager)

# Protect routes
@router.get("/protected")
async def protected_route(
    current_user: AuthContext = Depends(require_permission("read:data"))
):
    return {"user_id": current_user.user_id.value}
```
"""

# Core entities and value objects
from .entities.auth_context import AuthContext
from .entities.jwt_token import JWTToken
from .entities.keycloak_config import KeycloakConfig
from .entities.realm import Realm

# Protocol interfaces
from .entities.protocols import (
    AuthServiceProtocol,
    JWTValidatorProtocol,
    KeycloakClientProtocol,
    RealmManagerProtocol,
    TokenServiceProtocol,
    UserMapperProtocol,
)

# Cache protocols
from .entities.cache_protocols import (
    AuthCacheManagerProtocol,
    PublicKeyCacheProtocol,
    TokenCacheProtocol,
    UserMappingCacheProtocol,
    RealmConfigCacheProtocol,
)

# Service implementations  
from .services.auth_service import AuthService
from .services.jwt_validator import JWTValidator
from .services.keycloak_service import KeycloakService
from .services.realm_manager import RealmManager
from .services.token_service import TokenService
from .services.user_mapper import UserMapper

# Adapter implementations
from .adapters.keycloak_admin import KeycloakAdminAdapter
from .adapters.keycloak_openid import KeycloakOpenIDAdapter
from .adapters.redis_auth_cache import RedisAuthCache

# Repository implementations
from .repositories.realm_repository import RealmRepository
from .repositories.user_mapping_repository import UserMappingRepository

# FastAPI integration
from .dependencies import (
    AuthDependencies,
    get_current_user,
    get_optional_user,
    init_auth_dependencies,
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    require_any_role,
    require_tenant_admin,
    require_platform_admin,
    require_fresh_token,
)

# API Models
from .models import (
    # Request models
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    LogoutRequest,
    ChangePasswordRequest,
    
    # Response models
    TokenResponse,
    UserProfileResponse,
    LoginResponse,
    RegisterResponse,
    MessageResponse,
    ErrorResponse,
    PasswordResetResponse,
    SessionInfoResponse,
    UserValidationResponse,
)

# Additional Services
from .services.user_registration_service import UserRegistrationService
from .services.password_reset_service import PasswordResetService

# API Router
from .routers import auth_router

from .middleware import (
    AuthMiddleware,
    TenantIsolationMiddleware,
    RateLimitingMiddleware,
    configure_auth_middleware,
    configure_auth_exception_handlers,
)

__all__ = [
    # Core entities
    "AuthContext",
    "JWTToken", 
    "KeycloakConfig",
    "Realm",
    
    # Protocol interfaces
    "AuthServiceProtocol",
    "JWTValidatorProtocol",
    "KeycloakClientProtocol", 
    "RealmManagerProtocol",
    "TokenServiceProtocol",
    "UserMapperProtocol",
    "AuthCacheManagerProtocol",
    "PublicKeyCacheProtocol",
    "TokenCacheProtocol",
    "UserMappingCacheProtocol",
    "RealmConfigCacheProtocol",
    
    # Service implementations
    "AuthService",
    "JWTValidator",
    "KeycloakService",
    "RealmManager", 
    "TokenService",
    "UserMapper",
    "UserRegistrationService",
    "PasswordResetService",
    
    # Adapter implementations
    "KeycloakAdminAdapter",
    "KeycloakOpenIDAdapter",
    "RedisAuthCache",
    
    # Repository implementations
    "RealmRepository",
    "UserMappingRepository",
    
    # FastAPI integration
    "AuthDependencies",
    "get_current_user",
    "get_optional_user", 
    "init_auth_dependencies",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_role",
    "require_any_role",
    "require_tenant_admin",
    "require_platform_admin",
    "require_fresh_token",
    
    # API Models - Requests
    "LoginRequest",
    "RegisterRequest",
    "RefreshTokenRequest",
    "ForgotPasswordRequest",
    "ResetPasswordRequest",
    "LogoutRequest",
    "ChangePasswordRequest",
    
    # API Models - Responses
    "TokenResponse",
    "UserProfileResponse",
    "LoginResponse",
    "RegisterResponse",
    "MessageResponse",
    "ErrorResponse",
    "PasswordResetResponse",
    "SessionInfoResponse",
    "UserValidationResponse",
    
    # API Router
    "auth_router",
    
    # Middleware
    "AuthMiddleware",
    "TenantIsolationMiddleware", 
    "RateLimitingMiddleware",
    "configure_auth_middleware",
    "configure_auth_exception_handlers",
    
    # Factory functions
    "create_auth_service_factory",
    "AuthServiceFactory",
]


# Factory for creating configured auth services

class AuthServiceFactory:
    """Factory for creating and configuring auth services."""
    
    def __init__(
        self,
        keycloak_server_url: str,
        keycloak_admin_username: str,
        keycloak_admin_password: str,
        redis_url: str = "redis://localhost:6379",
        redis_password: str = None,
        database_service=None,
    ):
        """Initialize auth service factory."""
        self.keycloak_server_url = keycloak_server_url
        self.keycloak_admin_username = keycloak_admin_username
        self.keycloak_admin_password = keycloak_admin_password
        self.redis_url = redis_url
        self.redis_password = redis_password
        self.database_service = database_service
        
        # Lazy-initialized services
        self._auth_cache = None
        self._realm_repository = None
        self._user_mapping_repository = None
        self._keycloak_service = None
        self._jwt_validator = None
        self._realm_manager = None
        self._user_mapper = None
        self._token_service = None
        self._auth_service = None
        self._auth_dependencies = None
    
    async def get_auth_cache(self) -> RedisAuthCache:
        """Get or create Redis auth cache."""
        if not self._auth_cache:
            self._auth_cache = RedisAuthCache(
                redis_url=self.redis_url,
                redis_password=self.redis_password,
            )
            await self._auth_cache.connect()
        return self._auth_cache
    
    def get_realm_repository(self) -> RealmRepository:
        """Get or create realm repository."""
        if not self._realm_repository:
            self._realm_repository = RealmRepository(
                database_service=self.database_service
            )
        return self._realm_repository
    
    def get_user_mapping_repository(self) -> UserMappingRepository:
        """Get or create user mapping repository."""
        if not self._user_mapping_repository:
            self._user_mapping_repository = UserMappingRepository(
                database_service=self.database_service
            )
        return self._user_mapping_repository
    
    async def get_keycloak_service(self) -> KeycloakService:
        """Get or create Keycloak service."""
        if not self._keycloak_service:
            # KeycloakService needs these dependencies
            realm_manager = await self.get_realm_manager() 
            jwt_validator = await self.get_jwt_validator()
            user_mapper = await self.get_user_mapper()
            
            self._keycloak_service = KeycloakService(
                realm_manager=realm_manager,
                jwt_validator=jwt_validator,
                user_mapper=user_mapper,
            )
        return self._keycloak_service
    
    async def get_jwt_validator(self) -> JWTValidator:
        """Get or create JWT validator."""
        if not self._jwt_validator:
            auth_cache = await self.get_auth_cache()
            realm_manager = await self.get_realm_manager()
            user_mapper = await self.get_user_mapper()
            
            self._jwt_validator = JWTValidator(
                realm_manager=realm_manager,
                user_mapper=user_mapper,
                public_key_cache=auth_cache,
            )
        return self._jwt_validator
    
    async def get_realm_manager(self) -> RealmManager:
        """Get or create realm manager.""" 
        if not self._realm_manager:
            realm_repository = self.get_realm_repository()
            
            self._realm_manager = RealmManager(
                realm_repository=realm_repository,
                keycloak_server_url=self.keycloak_server_url,
                admin_username=self.keycloak_admin_username,
                admin_password=self.keycloak_admin_password,
            )
        return self._realm_manager
    
    async def get_user_mapper(self) -> UserMapper:
        """Get or create user mapper."""
        if not self._user_mapper:
            user_mapping_repository = self.get_user_mapping_repository()
            
            self._user_mapper = UserMapper(
                user_mapping_repository=user_mapping_repository,
            )
        return self._user_mapper
    
    async def get_token_service(self) -> TokenService:
        """Get or create token service."""
        if not self._token_service:
            keycloak_service = await self.get_keycloak_service()
            jwt_validator = await self.get_jwt_validator()
            auth_cache = await self.get_auth_cache()
            
            self._token_service = TokenService(
                keycloak_client=keycloak_service,
                jwt_validator=jwt_validator,
                token_cache=auth_cache,
            )
        return self._token_service
    
    async def get_auth_service(self) -> AuthService:
        """Get or create main auth service."""
        if not self._auth_service:
            keycloak_service = await self.get_keycloak_service()
            jwt_validator = await self.get_jwt_validator()
            user_mapper = await self.get_user_mapper()
            token_service = await self.get_token_service()
            realm_manager = await self.get_realm_manager()
            
            self._auth_service = AuthService(
                keycloak_service=keycloak_service,
                jwt_validator=jwt_validator,
                user_mapper=user_mapper,
                token_service=token_service,
                realm_manager=realm_manager,
            )
        return self._auth_service
    
    async def get_auth_dependencies(self) -> AuthDependencies:
        """Get or create auth dependencies."""
        if not self._auth_dependencies:
            auth_service = await self.get_auth_service()
            jwt_validator = await self.get_jwt_validator()
            token_service = await self.get_token_service()
            user_mapper = await self.get_user_mapper()
            realm_manager = await self.get_realm_manager()
            
            self._auth_dependencies = AuthDependencies(
                auth_service=auth_service,
                jwt_validator=jwt_validator,
                token_service=token_service,
                user_mapper=user_mapper,
                realm_manager=realm_manager,
            )
        return self._auth_dependencies
    
    async def initialize_all_services(self) -> None:
        """Initialize all services for the factory."""
        # Initialize services in dependency order
        await self.get_auth_cache()
        self.get_realm_repository()
        self.get_user_mapping_repository()
        await self.get_realm_manager()
        await self.get_user_mapper()
        await self.get_jwt_validator()
        await self.get_keycloak_service()
        await self.get_token_service()
        await self.get_auth_service()
        await self.get_auth_dependencies()
    
    async def cleanup(self) -> None:
        """Cleanup factory resources."""
        if self._auth_cache:
            await self._auth_cache.disconnect()


def create_auth_service_factory(
    keycloak_server_url: str,
    keycloak_admin_username: str,
    keycloak_admin_password: str,
    redis_url: str = "redis://localhost:6379",
    redis_password: str = None,
    database_service=None,
) -> AuthServiceFactory:
    """Create configured auth service factory.
    
    Args:
        keycloak_server_url: Keycloak server URL (e.g., "http://localhost:8080")
        keycloak_admin_username: Keycloak admin username
        keycloak_admin_password: Keycloak admin password
        redis_url: Redis connection URL
        redis_password: Redis password (optional)
        database_service: Database service instance (optional)
    
    Returns:
        Configured AuthServiceFactory instance
    """
    return AuthServiceFactory(
        keycloak_server_url=keycloak_server_url,
        keycloak_admin_username=keycloak_admin_username,
        keycloak_admin_password=keycloak_admin_password,
        redis_url=redis_url,
        redis_password=redis_password,
        database_service=database_service,
    )