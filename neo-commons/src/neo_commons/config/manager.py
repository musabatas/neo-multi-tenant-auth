"""Modern configuration manager for neo-commons.

Clean, type-safe configuration management using the new infrastructure.
No backward compatibility - fresh start for maximum performance and clarity.
"""

from typing import Any, Dict, Optional, Type, TypeVar, Generic
from functools import lru_cache
from pydantic import BaseModel, Field
from datetime import timedelta
import os
import logging

from ..infrastructure.configuration import (
    ConfigurationService, ConfigKey, ConfigValue, ConfigScope, ConfigType,
    AsyncPGConfigurationRepository
)
from ..core.exceptions import ConfigurationError


logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class ConfigurationManager:
    """Modern configuration manager using infrastructure layer."""
    
    def __init__(self, service: ConfigurationService):
        self._service = service
        self._cache: Dict[str, Any] = {}
    
    async def get(
        self,
        key: str,
        default: Any = None,
        scope: ConfigScope = ConfigScope.GLOBAL,
        config_type: Optional[ConfigType] = None
    ) -> Any:
        """Get configuration value with automatic type conversion."""
        return await self._service.get_config(key, scope, default)
    
    async def set(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.GLOBAL,
        is_sensitive: bool = False,
        description: Optional[str] = None,
        expires_in: Optional[timedelta] = None
    ) -> bool:
        """Set configuration value."""
        return await self._service.set_config(
            key, value, scope, description=description,
            is_sensitive=is_sensitive, expires_in=expires_in
        )
    
    async def get_namespace(
        self,
        namespace: str,
        scope: ConfigScope = ConfigScope.GLOBAL
    ) -> Dict[str, Any]:
        """Get all configurations for a namespace."""
        return await self._service.get_configs_by_namespace(namespace, scope)
    
    async def load_from_env(self, prefix: str = "", scope: ConfigScope = ConfigScope.GLOBAL) -> int:
        """Load configuration from environment variables."""
        count = 0
        
        for key, value in os.environ.items():
            if prefix and not key.startswith(prefix):
                continue
            
            config_key = key[len(prefix):] if prefix else key
            
            try:
                await self.set(config_key, value, scope, description=f"Loaded from environment: {key}")
                count += 1
            except Exception as e:
                logger.warning(f"Failed to load env var {key}: {e}")
        
        return count


class EnvironmentConfig(BaseModel):
    """Clean environment configuration model."""
    
    # Environment
    environment: str = Field(default="development", description="Runtime environment")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Database
    admin_database_url: str = Field(..., description="Admin database URL")
    db_pool_min_size: int = Field(default=5, description="Min DB pool size")
    db_pool_max_size: int = Field(default=20, description="Max DB pool size")
    db_command_timeout: int = Field(default=60, description="DB command timeout")
    db_encryption_key: str = Field(..., description="Database encryption key")
    
    # Cache (Redis)
    redis_url: str = Field(default="redis://localhost:6379", description="Redis URL")
    redis_db: int = Field(default=0, description="Redis database")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_max_connections: int = Field(default=50, description="Max Redis connections")
    
    # Authentication (Keycloak)
    keycloak_server_url: str = Field(..., description="Keycloak server URL")
    keycloak_realm: str = Field(default="master", description="Keycloak realm")
    keycloak_client_id: str = Field(..., description="Keycloak client ID")
    keycloak_client_secret: str = Field(..., description="Keycloak client secret")
    # Admin credentials for operations requiring admin access
    keycloak_admin: Optional[str] = Field(default=None, description="Keycloak admin username")
    keycloak_password: Optional[str] = Field(default=None, description="Keycloak admin password")
    
    # Security (JWT handled by Keycloak - no local JWT secrets needed)
    # jwt_secret_key: removed - using Keycloak public key validation
    # jwt_algorithm: removed - Keycloak handles token algorithms  
    # jwt_access_token_expire_minutes: removed - controlled by Keycloak realm settings
    
    # Performance
    permission_check_timeout_ms: int = Field(default=1, description="Permission check timeout")
    api_request_timeout_seconds: int = Field(default=30, description="API timeout")
    
    # Features
    feature_caching: bool = Field(default=True, description="Enable caching")
    feature_metrics: bool = Field(default=True, description="Enable metrics")
    feature_audit_logging: bool = Field(default=True, description="Enable audit logs")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"


class ServiceConfig(BaseModel, Generic[T]):
    """Base service configuration model."""
    
    service_name: str = Field(..., description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    service_port: int = Field(..., description="Service port")
    service_host: str = Field(default="0.0.0.0", description="Service host")
    
    # Service-specific settings can be added by extending this class


@lru_cache(maxsize=1)
def get_env_config() -> EnvironmentConfig:
    """Get environment configuration from environment variables."""
    try:
        return EnvironmentConfig(
            # Environment
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            
            # Database  
            admin_database_url=os.getenv("ADMIN_DATABASE_URL"),
            db_pool_min_size=int(os.getenv("DB_POOL_MIN_SIZE", "5")),
            db_pool_max_size=int(os.getenv("DB_POOL_MAX_SIZE", "20")),
            db_command_timeout=int(os.getenv("DB_COMMAND_TIMEOUT", "60")),
            db_encryption_key=os.getenv("DB_ENCRYPTION_KEY"),
            
            # Cache
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            redis_max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
            
            # Authentication
            keycloak_server_url=os.getenv("KEYCLOAK_SERVER_URL"),
            keycloak_realm=os.getenv("KEYCLOAK_REALM", "master"),
            keycloak_client_id=os.getenv("KEYCLOAK_CLIENT_ID"),
            keycloak_client_secret=os.getenv("KEYCLOAK_CLIENT_SECRET"),
            keycloak_admin=os.getenv("KEYCLOAK_ADMIN"),
            keycloak_password=os.getenv("KEYCLOAK_PASSWORD"),
            
            # Security (JWT handled by Keycloak)
            # jwt_secret_key, jwt_algorithm, jwt_access_token_expire_minutes removed
            
            # Performance
            permission_check_timeout_ms=int(os.getenv("PERMISSION_CHECK_TIMEOUT_MS", "1")),
            api_request_timeout_seconds=int(os.getenv("API_REQUEST_TIMEOUT_SECONDS", "30")),
            
            # Features
            feature_caching=os.getenv("FEATURE_CACHING", "true").lower() == "true",
            feature_metrics=os.getenv("FEATURE_METRICS", "true").lower() == "true",
            feature_audit_logging=os.getenv("FEATURE_AUDIT_LOGGING", "true").lower() == "true",
        )
    except Exception as e:
        raise ConfigurationError(f"Failed to load environment configuration: {e}")


def validate_required_env_vars() -> None:
    """Validate that all required environment variables are set."""
    required_vars = [
        "ADMIN_DATABASE_URL",
        "DB_ENCRYPTION_KEY", 
        "KEYCLOAK_SERVER_URL",
        "KEYCLOAK_CLIENT_ID",
        "KEYCLOAK_CLIENT_SECRET",
        # JWT_SECRET_KEY removed - using Keycloak public key validation only
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ConfigurationError(f"Required environment variables missing: {', '.join(missing_vars)}")


# Convenience functions
async def create_config_manager(connection_manager) -> ConfigurationManager:
    """Create configuration manager with database backend."""
    repository = AsyncPGConfigurationRepository(connection_manager)
    service = ConfigurationService(repository)
    return ConfigurationManager(service)


def get_database_url() -> str:
    """Get database URL from environment."""
    return get_env_config().admin_database_url


def get_redis_url() -> str:
    """Get Redis URL from environment."""
    return get_env_config().redis_url


def is_production() -> bool:
    """Check if running in production environment."""
    return get_env_config().is_production


def is_development() -> bool:
    """Check if running in development environment."""
    return get_env_config().is_development