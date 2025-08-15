"""
Application settings and configuration management.

MIGRATED TO NEO-COMMONS: Now using neo-commons AdminConfig with NeoAdminApi-specific extensions.
Import compatibility maintained - all existing imports continue to work.
"""
from typing import Optional, List, Dict, Any
from functools import lru_cache
from pydantic import Field, SecretStr, HttpUrl

# NEO-COMMONS IMPORT: Use neo-commons AdminConfig as base
from neo_commons.config.base import AdminConfig


class Settings(AdminConfig):
    """
    NeoAdminApi settings extending neo-commons AdminConfig.
    
    Maintains backward compatibility while leveraging neo-commons infrastructure.
    """
    
    # NeoAdminApi-specific configuration extensions
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    enable_prefix_routes: bool = Field(default=True, env="ENABLE_PREFIX_ROUTES")
    
    # Database - use neo-commons configurable pattern but with NeoAdminApi defaults
    admin_database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/neofast_admin",
        env="ADMIN_DATABASE_URL"
    )
    
    # NeoAdminApi-specific Database settings
    db_pool_size: int = Field(default=20, env="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, env="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, env="DB_POOL_RECYCLE")
    db_echo: bool = Field(default=False, env="DB_ECHO")
    
    # NeoAdminApi-specific Cache settings
    cache_ttl_default: int = Field(default=300, env="CACHE_TTL_DEFAULT")  # 5 minutes
    cache_ttl_permissions: int = Field(default=600, env="CACHE_TTL_PERMISSIONS")  # 10 minutes
    cache_ttl_tenant: int = Field(default=1800, env="CACHE_TTL_TENANT")  # 30 minutes
    
    # Keycloak Configuration
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
    
    # JWT Configuration
    jwt_algorithm: str = Field(default="RS256", env="JWT_ALGORITHM")
    jwt_issuer: str = Field(default="http://localhost:8080/realms/neo-admin", env="JWT_ISSUER")
    jwt_audience: str = Field(default="admin-api", env="JWT_AUDIENCE")
    jwt_public_key_cache_ttl: int = Field(default=3600, env="JWT_PUBLIC_KEY_CACHE_TTL")
    
    # JWT Validation Options - Keycloak 2025 compliance
    jwt_verify_audience: bool = Field(default=True, env="JWT_VERIFY_AUDIENCE")
    jwt_audience_fallback: bool = Field(default=True, env="JWT_AUDIENCE_FALLBACK")
    jwt_debug_claims: bool = Field(default=False, env="JWT_DEBUG_CLAIMS")
    jwt_verify_issuer: bool = Field(default=True, env="JWT_VERIFY_ISSUER")
    
    # NeoAdminApi-specific Security
    app_encryption_key: str = Field(
        default="default-dev-key-change-in-production",
        env="APP_ENCRYPTION_KEY"
    )
    
    # NeoAdminApi-specific Features
    feature_multi_region: bool = Field(default=True, env="FEATURE_MULTI_REGION")
    feature_billing: bool = Field(default=True, env="FEATURE_BILLING")
    feature_analytics: bool = Field(default=True, env="FEATURE_ANALYTICS")
    
    # Tenant Provisioning
    tenant_schema_prefix: str = Field(default="tenant_", env="TENANT_SCHEMA_PREFIX")
    tenant_provisioning_timeout: int = Field(default=60, env="TENANT_PROVISIONING_TIMEOUT")
    
    # Background Tasks
    task_queue_enabled: bool = Field(default=False, env="TASK_QUEUE_ENABLED")
    task_queue_broker_url: Optional[str] = Field(default=None, env="TASK_QUEUE_BROKER_URL")
    
    # NeoAdminApi-specific computed properties
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)."""
        return str(self.admin_database_url).replace("+asyncpg", "")
    
    @property
    def get_cache_key_prefix(self) -> str:
        """Get cache key prefix based on environment."""
        return f"{self.app_name}:{self.environment}:"
    
    @property
    def is_cache_enabled(self) -> bool:
        """Check if Redis caching is configured."""
        return self.redis_url is not None


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# BACKWARD COMPATIBILITY: Export commonly used settings
settings = get_settings()