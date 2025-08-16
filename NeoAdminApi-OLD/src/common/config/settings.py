"""
Application settings and configuration management.
"""
from typing import Optional, List, Dict, Any
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, PostgresDsn, RedisDsn, HttpUrl


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="NeoAdminApi", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    api_prefix: Optional[str] = Field(default="/api/v1", env="API_PREFIX")
    enable_prefix_routes: bool = Field(default=True, env="ENABLE_PREFIX_ROUTES")  # Enable backward compatibility
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8001, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    reload: bool = Field(default=False, env="RELOAD")
    
    # Database
    admin_database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/neofast_admin",
        env="ADMIN_DATABASE_URL"
    )
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    db_echo: bool = Field(default=False, env="DB_ECHO")
    
    # Redis Cache (Optional - improves performance when available)
    redis_url: Optional[RedisDsn] = Field(
        default=None,
        env="REDIS_URL"
    )
    redis_pool_size: int = Field(default=10, env="REDIS_POOL_SIZE")
    redis_decode_responses: bool = Field(default=True, env="REDIS_DECODE_RESPONSES")
    cache_ttl_default: int = Field(default=300, env="CACHE_TTL_DEFAULT")  # 5 minutes
    cache_ttl_permissions: int = Field(default=600, env="CACHE_TTL_PERMISSIONS")  # 10 minutes
    cache_ttl_tenant: int = Field(default=1800, env="CACHE_TTL_TENANT")  # 30 minutes
    
    # Keycloak
    keycloak_url: HttpUrl = Field(
        default="http://localhost:8080",
        env="KEYCLOAK_URL"
    )
    keycloak_admin_realm: str = Field(default="neo-admin", env="KEYCLOAK_ADMIN_REALM")
    keycloak_admin_client_id: str = Field(default="admin-api", env="KEYCLOAK_ADMIN_CLIENT_ID")
    keycloak_admin_client_secret: SecretStr = Field(
        default="admin-secret",
        env="KEYCLOAK_ADMIN_CLIENT_SECRET"
    )
    keycloak_admin_username: str = Field(default="admin", env="KEYCLOAK_ADMIN_USERNAME")
    keycloak_admin_password: SecretStr = Field(
        default="admin",
        env="KEYCLOAK_ADMIN_PASSWORD"
    )
    
    # JWT
    jwt_algorithm: str = Field(default="RS256", env="JWT_ALGORITHM")
    jwt_issuer: str = Field(default="http://localhost:8080/realms/neo-admin", env="JWT_ISSUER")
    jwt_audience: str = Field(default="admin-api", env="JWT_AUDIENCE")
    jwt_public_key_cache_ttl: int = Field(default=3600, env="JWT_PUBLIC_KEY_CACHE_TTL")
    
    # JWT Validation Options - Based on Keycloak 2025 stricter validation
    jwt_verify_audience: bool = Field(default=True, env="JWT_VERIFY_AUDIENCE")
    jwt_audience_fallback: bool = Field(default=True, env="JWT_AUDIENCE_FALLBACK") # Allow fallback without audience check
    jwt_debug_claims: bool = Field(default=False, env="JWT_DEBUG_CLAIMS")  # Log token claims for debugging
    jwt_verify_issuer: bool = Field(default=True, env="JWT_VERIFY_ISSUER")  # Verify issuer claim
    
    # Security
    secret_key: SecretStr = Field(
        default="change-me-in-production-use-strong-secret-key",
        env="SECRET_KEY"
    )
    app_encryption_key: str = Field(
        default="default-dev-key-change-in-production",
        env="APP_ENCRYPTION_KEY"
    )
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(
        default=["http://localhost:3001", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_requests_per_hour: int = Field(default=1000, env="RATE_LIMIT_REQUESTS_PER_HOUR")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        env="LOG_FORMAT"
    )
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_rotation: str = Field(default="10 MB", env="LOG_ROTATION")
    log_retention: str = Field(default="7 days", env="LOG_RETENTION")
    
    # Monitoring
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    # tracing_enabled: bool = Field(default=False, env="TRACING_ENABLED")
    # tracing_endpoint: Optional[HttpUrl] = Field(default=None, env="TRACING_ENDPOINT")
    
    # Pagination
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Tenant Provisioning
    tenant_schema_prefix: str = Field(default="tenant_", env="TENANT_SCHEMA_PREFIX")
    tenant_provisioning_timeout: int = Field(default=60, env="TENANT_PROVISIONING_TIMEOUT")
    
    # Background Tasks
    task_queue_enabled: bool = Field(default=False, env="TASK_QUEUE_ENABLED")
    task_queue_broker_url: Optional[str] = Field(default=None, env="TASK_QUEUE_BROKER_URL")
    
    # Feature Flags
    feature_multi_region: bool = Field(default=True, env="FEATURE_MULTI_REGION")
    feature_billing: bool = Field(default=True, env="FEATURE_BILLING")
    feature_analytics: bool = Field(default=True, env="FEATURE_ANALYTICS")
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)."""
        return str(self.admin_database_url).replace("+asyncpg", "")
    
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
        """Get cache key prefix based on environment."""
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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export commonly used settings
settings = get_settings()