"""
Base configuration implementations for neo-commons.
Provides concrete implementations of configuration protocols using Pydantic settings.
"""
import os
import logging
from typing import Optional, List, Dict, Any
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr

from .protocols import (
    BaseConfigProtocol,
    EnvironmentConfigProtocol,
    ConfigValidationProtocol
)

logger = logging.getLogger(__name__)


class EnvironmentConfig:
    """Implementation of environment variable handling."""
    
    def get_env_var(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable value."""
        return os.getenv(key, default)
    
    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get environment variable as boolean."""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")
    
    def get_env_int(self, key: str, default: int = 0) -> int:
        """Get environment variable as integer."""
        try:
            return int(os.getenv(key, str(default)))
        except (ValueError, TypeError):
            return default
    
    def get_env_list(
        self,
        key: str,
        default: Optional[List[str]] = None,
        separator: str = ","
    ) -> List[str]:
        """Get environment variable as list."""
        if default is None:
            default = []
        
        value = os.getenv(key)
        if not value:
            return default
        
        return [item.strip() for item in value.split(separator) if item.strip()]


class BaseNeoConfig(BaseSettings, EnvironmentConfig):
    """
    Base configuration class implementing all required protocols.
    
    This provides a comprehensive configuration implementation that can be
    extended or used directly for neo-commons applications.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        validate_assignment=True
    )
    
    # Application metadata
    app_name: str = Field(default="Neo Application", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    api_prefix: Optional[str] = Field(default="/api/v1", env="API_PREFIX")
    
    # Server configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Database configuration
    database_url: str = Field(
        default="postgresql+asyncpg://user:pass@localhost:5432/db",
        env="DATABASE_URL"
    )
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    db_echo: bool = Field(default=False, env="DB_ECHO")
    
    # Cache configuration
    cache_url: Optional[str] = Field(default=None, env="CACHE_URL")
    cache_pool_size: int = Field(default=10, env="CACHE_POOL_SIZE")
    cache_decode_responses: bool = Field(default=True, env="CACHE_DECODE_RESPONSES")
    cache_ttl_default: int = Field(default=300, env="CACHE_TTL_DEFAULT")
    cache_ttl_permissions: int = Field(default=600, env="CACHE_TTL_PERMISSIONS")
    cache_ttl_tenant: int = Field(default=1800, env="CACHE_TTL_TENANT")
    
    # Security configuration
    secret_key: SecretStr = Field(
        default="change-me-in-production",
        env="SECRET_KEY"
    )
    app_encryption_key: str = Field(
        default="default-dev-key",
        env="APP_ENCRYPTION_KEY"
    )
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Logging configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: str = Field(default="10 MB", env="LOG_ROTATION")
    log_retention: str = Field(default="7 days", env="LOG_RETENTION")
    
    # Rate limiting configuration
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_requests_per_hour: int = Field(default=1000, env="RATE_LIMIT_REQUESTS_PER_HOUR")
    
    # Pagination configuration
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Monitoring configuration
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for migrations)."""
        return str(self.database_url).replace("+asyncpg", "").replace("+aiomysql", "")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment.lower() == "testing"
    
    @property
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self.cache_url is not None
    
    def get_cache_key_prefix(self) -> str:
        """Get cache key prefix based on environment."""
        return f"{self.app_name.lower()}:{self.environment}:"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as processed list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins
    
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        errors = []
        warnings = []
        
        # Validate security in production
        if self.is_production:
            if str(self.secret_key.get_secret_value()) == "change-me-in-production":
                errors.append("SECRET_KEY must be changed in production")
            
            if self.app_encryption_key == "default-dev-key":
                errors.append("APP_ENCRYPTION_KEY must be changed in production")
            
            if self.debug:
                warnings.append("DEBUG should be False in production")
                
            if "*" in self.allowed_hosts:
                warnings.append("ALLOWED_HOSTS should not contain '*' in production")
        
        # Validate database configuration
        if not self.database_url:
            errors.append("DATABASE_URL is required")
        
        # Validate cache configuration
        if self.is_cache_enabled and not self.cache_url:
            errors.append("CACHE_URL is required when caching is enabled")
        
        # Validate pagination
        if self.default_page_size > self.max_page_size:
            errors.append("DEFAULT_PAGE_SIZE cannot be greater than MAX_PAGE_SIZE")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config_summary": {
                "app_name": self.app_name,
                "environment": self.environment,
                "debug": self.debug,
                "cache_enabled": self.is_cache_enabled,
                "metrics_enabled": self.metrics_enabled
            }
        }
    
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors."""
        return self.validate_config()["errors"]
    
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        return self.validate_config()["valid"]


class AdminConfig(BaseNeoConfig):
    """Configuration optimized for admin/platform services."""
    
    # Override defaults for admin services
    app_name: str = Field(default="Neo Admin API", env="APP_NAME")
    port: int = Field(default=8001, env="PORT")
    api_prefix: Optional[str] = Field(default="/api/v1", env="API_PREFIX")
    
    # Admin-specific cache TTL
    cache_ttl_permissions: int = Field(default=600, env="CACHE_TTL_PERMISSIONS")  # 10 minutes
    cache_ttl_tenant: int = Field(default=1800, env="CACHE_TTL_TENANT")  # 30 minutes
    
    # Admin-specific CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3001"],  # Admin dashboard
        env="CORS_ORIGINS"
    )


class TenantConfig(BaseNeoConfig):
    """Configuration optimized for tenant services."""
    
    # Override defaults for tenant services
    app_name: str = Field(default="Neo Tenant API", env="APP_NAME")
    port: int = Field(default=8002, env="PORT")
    api_prefix: Optional[str] = Field(default="/api/v1", env="API_PREFIX")
    
    # Tenant-specific cache TTL (shorter for dynamic data)
    cache_ttl_default: int = Field(default=180, env="CACHE_TTL_DEFAULT")  # 3 minutes
    cache_ttl_permissions: int = Field(default=300, env="CACHE_TTL_PERMISSIONS")  # 5 minutes
    
    # Tenant-specific CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3003", "http://localhost:3002"],
        env="CORS_ORIGINS"
    )


class TestingConfig(BaseNeoConfig):
    """Configuration optimized for testing environments."""
    
    # Override defaults for testing
    app_name: str = Field(default="Neo Test API", env="APP_NAME")
    environment: str = Field(default="testing", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Fast database for testing
    database_url: str = Field(
        default="postgresql+asyncpg://test:test@localhost:5432/test_db",
        env="DATABASE_URL"
    )
    db_pool_size: int = Field(default=5, env="DB_POOL_SIZE")
    
    # Disable cache in tests by default
    cache_url: Optional[str] = Field(default=None, env="CACHE_URL")
    
    # Shorter TTLs for testing
    cache_ttl_default: int = Field(default=1, env="CACHE_TTL_DEFAULT")
    cache_ttl_permissions: int = Field(default=1, env="CACHE_TTL_PERMISSIONS")
    cache_ttl_tenant: int = Field(default=1, env="CACHE_TTL_TENANT")
    
    # Disable rate limiting in tests
    rate_limit_enabled: bool = Field(default=False, env="RATE_LIMIT_ENABLED")
    
    # Disable metrics in tests
    metrics_enabled: bool = Field(default=False, env="METRICS_ENABLED")


@lru_cache()
def get_config() -> BaseNeoConfig:
    """Get cached configuration instance."""
    return BaseNeoConfig()


@lru_cache()
def get_admin_config() -> AdminConfig:
    """Get cached admin configuration instance."""
    return AdminConfig()


@lru_cache()
def get_tenant_config() -> TenantConfig:
    """Get cached tenant configuration instance."""
    return TenantConfig()


@lru_cache()
def get_testing_config() -> TestingConfig:
    """Get cached testing configuration instance."""
    return TestingConfig()


def create_config_for_environment(env: str = "development") -> BaseNeoConfig:
    """
    Create configuration for specific environment.
    
    Args:
        env: Environment name (development, testing, production)
        
    Returns:
        Configuration instance optimized for the environment
    """
    env_lower = env.lower()
    
    if env_lower == "testing":
        return get_testing_config()
    elif env_lower in ("admin", "platform"):
        return get_admin_config()
    elif env_lower == "tenant":
        return get_tenant_config()
    else:
        return get_config()


def validate_config_or_exit(config: BaseNeoConfig) -> None:
    """
    Validate configuration and exit if invalid.
    
    Args:
        config: Configuration to validate
        
    Raises:
        SystemExit: If configuration is invalid
    """
    validation_result = config.validate_config()
    
    if validation_result["warnings"]:
        for warning in validation_result["warnings"]:
            logger.warning(f"Configuration warning: {warning}")
    
    if not validation_result["valid"]:
        for error in validation_result["errors"]:
            logger.error(f"Configuration error: {error}")
        
        logger.error("Configuration validation failed. Exiting.")
        raise SystemExit(1)
    
    logger.info(f"Configuration validated successfully for {config.app_name} in {config.environment} mode")