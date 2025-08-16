"""
Base configuration management for the NeoMultiTenant platform.

Generic configuration classes and patterns that can be used across all platform services
in the NeoMultiTenant ecosystem.
"""
from typing import Optional, List, Dict, Any, Protocol, runtime_checkable
from abc import ABC, abstractmethod
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, PostgresDsn, RedisDsn, HttpUrl


@runtime_checkable
class AppConfig(Protocol):
    """Protocol for application configuration."""
    
    @property
    def app_name(self) -> str:
        """Application name."""
        ...
    
    @property
    def app_version(self) -> str:
        """Application version."""
        ...
    
    @property
    def environment(self) -> str:
        """Environment name (development, production, etc.)."""
        ...


class BaseAppSettings(BaseSettings, ABC):
    """Base application settings that can be extended by services."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Core Application Settings (must be overridden by services)
    app_name: str = Field(env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(env="PORT")  # Must be overridden by service
    workers: int = Field(default=4, env="WORKERS")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Database Configuration
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    db_echo: bool = Field(default=False, env="DB_ECHO")
    
    # Redis Cache Configuration
    redis_url: Optional[RedisDsn] = Field(default=None, env="REDIS_URL")
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    redis_decode_responses: bool = Field(default=True, env="REDIS_DECODE_RESPONSES")
    cache_ttl_default: int = Field(default=300, env="CACHE_TTL_DEFAULT")  # 5 minutes
    cache_ttl_permissions: int = Field(default=600, env="CACHE_TTL_PERMISSIONS")  # 10 minutes
    cache_ttl_tenant: int = Field(default=1800, env="CACHE_TTL_TENANT")  # 30 minutes
    
    # Security Configuration
    secret_key: SecretStr = Field(
        default="change-me-in-production-use-strong-secret-key",
        env="SECRET_KEY"
    )
    app_encryption_key: str = Field(
        default="default-dev-key-change-in-production",
        env="APP_ENCRYPTION_KEY"
    )
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # CORS Configuration
    cors_origins: List[str] = Field(default=[], env="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Rate Limiting Configuration
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_requests_per_hour: int = Field(default=1000, env="RATE_LIMIT_REQUESTS_PER_HOUR")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: str = Field(default="10 MB", env="LOG_ROTATION")
    log_retention: str = Field(default="7 days", env="LOG_RETENTION")
    
    # Monitoring Configuration
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    
    # Pagination Configuration
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Feature Flags (generic)
    feature_multi_region: bool = Field(default=True, env="FEATURE_MULTI_REGION")
    feature_analytics: bool = Field(default=True, env="FEATURE_ANALYTICS")
    
    # Abstract methods that must be implemented by services
    @abstractmethod
    def get_service_specific_config(self) -> Dict[str, Any]:
        """Get service-specific configuration."""
        pass
    
    # Common helper methods
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
    
    def get_cache_key_prefix(self) -> str:
        """Get cache key prefix based on service and environment."""
        return f"{self.app_name}:{self.environment}:"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as list."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins
    
    @property
    def is_cache_enabled(self) -> bool:
        """Check if Redis caching is configured."""
        return self.redis_url is not None


class BaseKeycloakSettings:
    """Base Keycloak configuration that can be extended by services."""
    
    def __init__(
        self,
        keycloak_url: str = "http://localhost:8080",
        admin_realm: str = "master",
        admin_client_id: str = "admin-cli",
        admin_client_secret: str = "",
        admin_username: str = "admin",
        admin_password: str = "admin"
    ):
        self.keycloak_url = keycloak_url
        self.admin_realm = admin_realm
        self.admin_client_id = admin_client_id
        self.admin_client_secret = admin_client_secret
        self.admin_username = admin_username
        self.admin_password = admin_password


class BaseJWTSettings:
    """Base JWT configuration that can be extended by services."""
    
    def __init__(
        self,
        algorithm: str = "RS256",
        issuer: Optional[str] = None,
        audience: Optional[str] = None,
        public_key_cache_ttl: int = 3600,
        verify_audience: bool = True,
        audience_fallback: bool = True,
        debug_claims: bool = False,
        verify_issuer: bool = True
    ):
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.public_key_cache_ttl = public_key_cache_ttl
        self.verify_audience = verify_audience
        self.audience_fallback = audience_fallback
        self.debug_claims = debug_claims
        self.verify_issuer = verify_issuer


class ConfigHelper:
    """Helper utilities for configuration management."""
    
    @staticmethod
    def validate_required_settings(settings: BaseAppSettings, required_fields: List[str]) -> None:
        """Validate that required settings are provided."""
        missing_fields = []
        for field in required_fields:
            if not hasattr(settings, field) or getattr(settings, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {missing_fields}")
    
    @staticmethod
    def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries."""
        merged = {}
        for config in configs:
            if config:
                merged.update(config)
        return merged
    
    @staticmethod
    def get_env_list(env_var: str, default: List[str], separator: str = ",") -> List[str]:
        """Parse environment variable as list."""
        import os
        value = os.getenv(env_var)
        if value:
            return [item.strip() for item in value.split(separator)]
        return default