"""
Authentication configuration management.

Provides configuration classes and utilities for managing auth settings
including Keycloak integration, JWT validation, caching, and security options.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from .enums import ValidationStrategy, CacheStrategy
from .protocols import AuthConfigProtocol


@dataclass
class AuthConfig:
    """
    Authentication configuration with sensible defaults.
    
    Implements AuthConfigProtocol and provides a concrete configuration
    class with validation and environment variable integration.
    """
    
    # Keycloak configuration
    keycloak_url: str
    admin_client_id: str = "admin-cli"
    admin_client_secret: str = ""
    admin_username: str = "admin"
    admin_password: str = ""
    default_realm: str = "master"
    
    # JWT validation configuration
    jwt_algorithm: str = "RS256"
    jwt_verify_audience: bool = True
    jwt_verify_issuer: bool = True
    jwt_audience: Optional[str] = None
    jwt_issuer: Optional[str] = None
    
    # Validation strategy
    default_validation_strategy: ValidationStrategy = ValidationStrategy.LOCAL
    
    # Cache configuration
    cache_strategy: CacheStrategy = CacheStrategy.BALANCED
    cache_ttl_permissions: int = 300  # 5 minutes
    cache_ttl_tokens: int = 900       # 15 minutes
    cache_ttl_sessions: int = 1800    # 30 minutes
    cache_ttl_realm_keys: int = 3600  # 1 hour
    
    # Rate limiting configuration
    rate_limit_auth_attempts: int = 5
    rate_limit_auth_window: int = 300  # 5 minutes
    rate_limit_permission_checks: int = 1000
    rate_limit_permission_window: int = 60  # 1 minute
    
    # Security configuration
    require_https: bool = True
    session_secure_cookies: bool = True
    session_same_site: str = "lax"
    bcrypt_rounds: int = 12
    
    # Performance configuration
    connection_pool_size: int = 10
    connection_timeout_seconds: int = 30
    request_timeout_seconds: int = 10
    
    # Audit logging configuration
    audit_enabled: bool = True
    audit_include_request_body: bool = False
    audit_include_response_body: bool = False
    
    # Additional configuration
    extra_config: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate_config()
        
        # Set default JWT audience/issuer if not provided
        if not self.jwt_audience:
            self.jwt_audience = f"{self.keycloak_url}/realms/{self.default_realm}"
        if not self.jwt_issuer:
            self.jwt_issuer = f"{self.keycloak_url}/realms/{self.default_realm}"
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        if not self.keycloak_url:
            raise ValueError("keycloak_url is required")
        
        if not self.keycloak_url.startswith(('http://', 'https://')):
            raise ValueError("keycloak_url must include protocol (http:// or https://)")
        
        if self.require_https and not self.keycloak_url.startswith('https://'):
            raise ValueError("keycloak_url must use HTTPS when require_https is True")
        
        if self.cache_ttl_permissions <= 0:
            raise ValueError("cache_ttl_permissions must be positive")
        
        if self.cache_ttl_tokens <= 0:
            raise ValueError("cache_ttl_tokens must be positive")
        
        if self.cache_ttl_sessions <= 0:
            raise ValueError("cache_ttl_sessions must be positive")
        
        if self.rate_limit_auth_attempts <= 0:
            raise ValueError("rate_limit_auth_attempts must be positive")
        
        if self.rate_limit_auth_window <= 0:
            raise ValueError("rate_limit_auth_window must be positive")
        
        if self.bcrypt_rounds < 4 or self.bcrypt_rounds > 20:
            raise ValueError("bcrypt_rounds must be between 4 and 20")
        
        if self.session_same_site not in ('strict', 'lax', 'none'):
            raise ValueError("session_same_site must be 'strict', 'lax', or 'none'")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AuthConfig':
        """Create AuthConfig from dictionary."""
        # Filter out unknown keys
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_dict = {k: v for k, v in config_dict.items() if k in known_fields}
        
        # Handle enum conversions
        if 'default_validation_strategy' in filtered_dict:
            strategy = filtered_dict['default_validation_strategy']
            if isinstance(strategy, str):
                filtered_dict['default_validation_strategy'] = ValidationStrategy(strategy)
        
        if 'cache_strategy' in filtered_dict:
            strategy = filtered_dict['cache_strategy']
            if isinstance(strategy, str):
                filtered_dict['cache_strategy'] = CacheStrategy(strategy)
        
        return cls(**filtered_dict)
    
    @classmethod
    def from_env(cls, prefix: str = "AUTH_") -> 'AuthConfig':
        """Create AuthConfig from environment variables."""
        import os
        
        config_dict = {}
        
        # Map environment variables to config fields
        env_mapping = {
            f"{prefix}KEYCLOAK_URL": "keycloak_url",
            f"{prefix}ADMIN_CLIENT_ID": "admin_client_id",
            f"{prefix}ADMIN_CLIENT_SECRET": "admin_client_secret",
            f"{prefix}ADMIN_USERNAME": "admin_username",
            f"{prefix}ADMIN_PASSWORD": "admin_password",
            f"{prefix}DEFAULT_REALM": "default_realm",
            f"{prefix}JWT_ALGORITHM": "jwt_algorithm",
            f"{prefix}JWT_VERIFY_AUDIENCE": "jwt_verify_audience",
            f"{prefix}JWT_VERIFY_ISSUER": "jwt_verify_issuer",
            f"{prefix}JWT_AUDIENCE": "jwt_audience",
            f"{prefix}JWT_ISSUER": "jwt_issuer",
            f"{prefix}VALIDATION_STRATEGY": "default_validation_strategy",
            f"{prefix}CACHE_STRATEGY": "cache_strategy",
            f"{prefix}CACHE_TTL_PERMISSIONS": "cache_ttl_permissions",
            f"{prefix}CACHE_TTL_TOKENS": "cache_ttl_tokens",
            f"{prefix}CACHE_TTL_SESSIONS": "cache_ttl_sessions",
            f"{prefix}REQUIRE_HTTPS": "require_https",
            f"{prefix}AUDIT_ENABLED": "audit_enabled",
        }
        
        for env_var, config_key in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_key in ('jwt_verify_audience', 'jwt_verify_issuer', 'require_https', 'audit_enabled'):
                    config_dict[config_key] = value.lower() in ('true', '1', 'yes', 'on')
                elif config_key in ('cache_ttl_permissions', 'cache_ttl_tokens', 'cache_ttl_sessions'):
                    config_dict[config_key] = int(value)
                else:
                    config_dict[config_key] = value
        
        # Require at least keycloak_url from environment
        if 'keycloak_url' not in config_dict:
            raise ValueError(f"Environment variable {prefix}KEYCLOAK_URL is required")
        
        return cls.from_dict(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert AuthConfig to dictionary."""
        result = {}
        for field_name, field_obj in self.__dataclass_fields__.items():
            value = getattr(self, field_name)
            
            # Convert enums to strings
            if isinstance(value, (ValidationStrategy, CacheStrategy)):
                result[field_name] = value.value
            else:
                result[field_name] = value
        
        return result
    
    def get_realm_url(self, realm: Optional[str] = None) -> str:
        """Get the full URL for a specific realm."""
        realm_name = realm or self.default_realm
        return f"{self.keycloak_url}/realms/{realm_name}"
    
    def get_realm_auth_url(self, realm: Optional[str] = None) -> str:
        """Get the authentication URL for a specific realm."""
        return f"{self.get_realm_url(realm)}/protocol/openid-connect/auth"
    
    def get_realm_token_url(self, realm: Optional[str] = None) -> str:
        """Get the token URL for a specific realm."""
        return f"{self.get_realm_url(realm)}/protocol/openid-connect/token"
    
    def get_realm_userinfo_url(self, realm: Optional[str] = None) -> str:
        """Get the userinfo URL for a specific realm."""
        return f"{self.get_realm_url(realm)}/protocol/openid-connect/userinfo"
    
    def get_realm_introspect_url(self, realm: Optional[str] = None) -> str:
        """Get the token introspection URL for a specific realm."""
        return f"{self.get_realm_url(realm)}/protocol/openid-connect/token/introspect"
    
    def get_realm_logout_url(self, realm: Optional[str] = None) -> str:
        """Get the logout URL for a specific realm."""
        return f"{self.get_realm_url(realm)}/protocol/openid-connect/logout"
    
    def get_realm_certs_url(self, realm: Optional[str] = None) -> str:
        """Get the certificates URL for a specific realm."""
        return f"{self.get_realm_url(realm)}/protocol/openid-connect/certs"


# Type alias for convenience
AuthConfigType = AuthConfig


__all__ = [
    "AuthConfig",
    "AuthConfigType",
]