"""
Application settings and configuration management.

Service wrapper that extends neo-commons base settings with NeoAdminApi-specific
configuration while maintaining backward compatibility.
"""
from typing import Optional, List, Dict, Any
from functools import lru_cache
from pydantic import Field, SecretStr, PostgresDsn, HttpUrl

# Import from neo-commons
from neo_commons.config.settings import BaseAppSettings, BaseKeycloakSettings, BaseJWTSettings


class Settings(BaseAppSettings):
    """NeoAdminApi settings that extend neo-commons BaseAppSettings."""
    
    # Service-specific application settings
    app_name: str = Field(default="NeoAdminApi", env="APP_NAME")
    port: int = Field(default=8001, env="PORT")
    api_prefix: Optional[str] = Field(default="/api/v1", env="API_PREFIX")
    enable_prefix_routes: bool = Field(default=True, env="ENABLE_PREFIX_ROUTES")
    
    # Service-specific database settings
    admin_database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/neofast_admin",
        env="ADMIN_DATABASE_URL"
    )
    
    # Service-specific CORS origins
    cors_origins: List[str] = Field(
        default=["http://localhost:3001", "http://localhost:3000"],
        env="CORS_ORIGINS"
    )
    
    # Keycloak Configuration (NeoAdminApi-specific)
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
    
    # JWT Configuration (NeoAdminApi-specific)
    jwt_algorithm: str = Field(default="RS256", env="JWT_ALGORITHM")
    jwt_issuer: str = Field(default="http://localhost:8080/realms/neo-admin", env="JWT_ISSUER")
    jwt_audience: str = Field(default="admin-api", env="JWT_AUDIENCE")
    jwt_public_key_cache_ttl: int = Field(default=3600, env="JWT_PUBLIC_KEY_CACHE_TTL")
    jwt_verify_audience: bool = Field(default=True, env="JWT_VERIFY_AUDIENCE")
    jwt_audience_fallback: bool = Field(default=True, env="JWT_AUDIENCE_FALLBACK")
    jwt_debug_claims: bool = Field(default=False, env="JWT_DEBUG_CLAIMS")
    jwt_verify_issuer: bool = Field(default=True, env="JWT_VERIFY_ISSUER")
    
    # NeoAdminApi-specific feature flags
    feature_billing: bool = Field(default=True, env="FEATURE_BILLING")
    
    # Tenant Management (NeoAdminApi-specific)
    tenant_schema_prefix: str = Field(default="tenant_", env="TENANT_SCHEMA_PREFIX")
    tenant_provisioning_timeout: int = Field(default=60, env="TENANT_PROVISIONING_TIMEOUT")
    
    # Background Tasks (NeoAdminApi-specific)
    task_queue_enabled: bool = Field(default=False, env="TASK_QUEUE_ENABLED")
    task_queue_broker_url: Optional[str] = Field(default=None, env="TASK_QUEUE_BROKER_URL")
    
    def get_service_specific_config(self) -> Dict[str, Any]:
        """Get NeoAdminApi-specific configuration."""
        return {
            "service_name": "NeoAdminApi",
            "service_type": "admin_api",
            "keycloak_config": self.get_keycloak_config(),
            "jwt_config": self.get_jwt_config(),
            "tenant_config": {
                "schema_prefix": self.tenant_schema_prefix,
                "provisioning_timeout": self.tenant_provisioning_timeout
            },
            "feature_flags": {
                "billing": self.feature_billing,
                "multi_region": self.feature_multi_region,
                "analytics": self.feature_analytics
            }
        }
    
    def get_keycloak_config(self) -> BaseKeycloakSettings:
        """Get Keycloak configuration as BaseKeycloakSettings."""
        return BaseKeycloakSettings(
            keycloak_url=str(self.keycloak_url),
            admin_realm=self.keycloak_admin_realm,
            admin_client_id=self.keycloak_admin_client_id,
            admin_client_secret=str(self.keycloak_admin_client_secret.get_secret_value()),
            admin_username=self.keycloak_admin_username,
            admin_password=str(self.keycloak_admin_password.get_secret_value())
        )
    
    def get_jwt_config(self) -> BaseJWTSettings:
        """Get JWT configuration as BaseJWTSettings."""
        return BaseJWTSettings(
            algorithm=self.jwt_algorithm,
            issuer=self.jwt_issuer,
            audience=self.jwt_audience,
            public_key_cache_ttl=self.jwt_public_key_cache_ttl,
            verify_audience=self.jwt_verify_audience,
            audience_fallback=self.jwt_audience_fallback,
            debug_claims=self.jwt_debug_claims,
            verify_issuer=self.jwt_verify_issuer
        )
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL (for Alembic)."""
        return str(self.admin_database_url).replace("+asyncpg", "")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Export commonly used settings for backward compatibility
settings = get_settings()