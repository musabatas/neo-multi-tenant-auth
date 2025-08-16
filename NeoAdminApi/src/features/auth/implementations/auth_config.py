"""
AuthConfig implementation for NeoAdminApi.

Protocol-compliant wrapper around existing settings for neo-commons integration.
"""
from typing import Dict, Any, Optional, List
from loguru import logger

from neo_commons.auth.protocols import AuthConfigProtocol
from src.common.config.settings import settings


class NeoAdminAuthConfig:
    """
    AuthConfig implementation for NeoAdminApi.
    
    Wraps the existing settings to provide protocol compliance.
    """
    
    def __init__(self):
        """Initialize auth config."""
        pass
    
    @property
    def keycloak_server_url(self) -> str:
        """Get Keycloak server URL."""
        return getattr(settings, 'keycloak_server_url', 'http://localhost:8080')
    
    @property
    def keycloak_admin_realm(self) -> str:
        """Get Keycloak admin realm."""
        return getattr(settings, 'keycloak_admin_realm', 'master')
    
    @property
    def keycloak_admin_client_id(self) -> str:
        """Get Keycloak admin client ID."""
        return getattr(settings, 'keycloak_admin_client_id', 'admin-cli')
    
    @property
    def keycloak_admin_client_secret(self) -> Optional[str]:
        """Get Keycloak admin client secret."""
        return getattr(settings, 'keycloak_admin_client_secret', None)
    
    @property
    def keycloak_admin_username(self) -> Optional[str]:
        """Get Keycloak admin username."""
        return getattr(settings, 'keycloak_admin_username', None)
    
    @property
    def keycloak_admin_password(self) -> Optional[str]:
        """Get Keycloak admin password."""
        return getattr(settings, 'keycloak_admin_password', None)
    
    @property
    def token_validation_strategy(self) -> str:
        """Get default token validation strategy."""
        return getattr(settings, 'token_validation_strategy', 'DUAL')
    
    @property
    def token_cache_ttl(self) -> int:
        """Get token cache TTL in seconds."""
        return getattr(settings, 'token_cache_ttl', 300)
    
    @property
    def permission_cache_ttl(self) -> int:
        """Get permission cache TTL in seconds."""
        return getattr(settings, 'permission_cache_ttl', 600)
    
    @property
    def session_timeout(self) -> int:
        """Get session timeout in seconds."""
        return getattr(settings, 'session_timeout', 3600)
    
    @property
    def max_failed_login_attempts(self) -> int:
        """Get maximum failed login attempts."""
        return getattr(settings, 'max_failed_login_attempts', 5)
    
    @property
    def account_lockout_duration(self) -> int:
        """Get account lockout duration in seconds."""
        return getattr(settings, 'account_lockout_duration', 900)
    
    @property
    def require_mfa(self) -> bool:
        """Get whether MFA is required."""
        return getattr(settings, 'require_mfa', False)
    
    @property
    def password_min_length(self) -> int:
        """Get minimum password length."""
        return getattr(settings, 'password_min_length', 8)
    
    @property
    def password_require_special_chars(self) -> bool:
        """Get whether passwords require special characters."""
        return getattr(settings, 'password_require_special_chars', True)
    
    @property
    def allowed_redirect_urls(self) -> List[str]:
        """Get allowed redirect URLs."""
        urls = getattr(settings, 'allowed_redirect_urls', '')
        if isinstance(urls, str):
            return [url.strip() for url in urls.split(',') if url.strip()]
        return urls or []
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS allowed origins."""
        origins = getattr(settings, 'cors_origins', '')
        if isinstance(origins, str):
            return [origin.strip() for origin in origins.split(',') if origin.strip()]
        return origins or []
    
    @property
    def debug_mode(self) -> bool:
        """Get whether debug mode is enabled."""
        return getattr(settings, 'debug', False)
    
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return getattr(settings, 'log_level', 'INFO')
    
    def get_keycloak_config(self) -> Dict[str, Any]:
        """
        Get Keycloak configuration.
        
        Returns:
            Keycloak configuration dictionary
        """
        return {
            "server_url": self.keycloak_server_url,
            "admin_realm": self.keycloak_admin_realm,
            "admin_client_id": self.keycloak_admin_client_id,
            "admin_client_secret": self.keycloak_admin_client_secret,
            "admin_username": self.keycloak_admin_username,
            "admin_password": self.keycloak_admin_password,
            "verify_ssl": getattr(settings, 'keycloak_verify_ssl', True),
            "connection_timeout": getattr(settings, 'keycloak_connection_timeout', 30),
            "request_timeout": getattr(settings, 'keycloak_request_timeout', 10)
        }
    
    def get_cache_config(self) -> Dict[str, Any]:
        """
        Get cache configuration.
        
        Returns:
            Cache configuration dictionary
        """
        return {
            "token_ttl": self.token_cache_ttl,
            "permission_ttl": self.permission_cache_ttl,
            "session_ttl": self.session_timeout,
            "key_prefix": getattr(settings, 'cache_key_prefix', 'neoapi'),
            "namespace_separator": getattr(settings, 'cache_namespace_separator', ':')
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """
        Get security configuration.
        
        Returns:
            Security configuration dictionary
        """
        return {
            "max_failed_login_attempts": self.max_failed_login_attempts,
            "account_lockout_duration": self.account_lockout_duration,
            "require_mfa": self.require_mfa,
            "password_min_length": self.password_min_length,
            "password_require_special_chars": self.password_require_special_chars,
            "session_timeout": self.session_timeout,
            "token_validation_strategy": self.token_validation_strategy,
            "allowed_redirect_urls": self.allowed_redirect_urls,
            "cors_origins": self.cors_origins
        }
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """
        Get feature flags.
        
        Returns:
            Feature flags dictionary
        """
        return {
            "guest_auth_enabled": getattr(settings, 'guest_auth_enabled', True),
            "multi_tenant_enabled": getattr(settings, 'multi_tenant_enabled', True),
            "audit_logging_enabled": getattr(settings, 'audit_logging_enabled', True),
            "rate_limiting_enabled": getattr(settings, 'rate_limiting_enabled', True),
            "permission_caching_enabled": getattr(settings, 'permission_caching_enabled', True),
            "token_introspection_enabled": getattr(settings, 'token_introspection_enabled', True),
            "mfa_enforcement_enabled": getattr(settings, 'mfa_enforcement_enabled', False),
            "debug_mode": self.debug_mode
        }
    
    def get_tenant_config(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get tenant-specific configuration.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Tenant-specific configuration
        """
        # For now, return default config
        # In the future, this could fetch tenant-specific settings from database
        return {
            "realm_name": f"tenant-{tenant_id}",  # Default pattern
            "session_timeout": self.session_timeout,
            "require_mfa": self.require_mfa,
            "allowed_redirect_urls": self.allowed_redirect_urls,
            "cors_origins": self.cors_origins,
            "custom_claims": {},
            "permission_overrides": {}
        }
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate configuration.
        
        Returns:
            Validation result with status and any issues
        """
        issues = []
        
        # Check required Keycloak settings
        if not self.keycloak_server_url:
            issues.append("keycloak_server_url is required")
        
        if not self.keycloak_admin_realm:
            issues.append("keycloak_admin_realm is required")
        
        if not self.keycloak_admin_client_id:
            issues.append("keycloak_admin_client_id is required")
        
        # Check cache TTL values
        if self.token_cache_ttl <= 0:
            issues.append("token_cache_ttl must be positive")
        
        if self.permission_cache_ttl <= 0:
            issues.append("permission_cache_ttl must be positive")
        
        # Check security settings
        if self.password_min_length < 4:
            issues.append("password_min_length should be at least 4")
        
        if self.max_failed_login_attempts <= 0:
            issues.append("max_failed_login_attempts must be positive")
        
        if self.account_lockout_duration <= 0:
            issues.append("account_lockout_duration must be positive")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues
        }
    
    def get_environment_info(self) -> Dict[str, Any]:
        """
        Get environment information.
        
        Returns:
            Environment information
        """
        return {
            "environment": getattr(settings, 'environment', 'development'),
            "debug": self.debug_mode,
            "log_level": self.log_level,
            "keycloak_server": self.keycloak_server_url,
            "admin_realm": self.keycloak_admin_realm,
            "config_source": "settings.py"
        }