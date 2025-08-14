"""
Configuration protocols for neo-commons.
Defines protocol interfaces for different types of configuration management.
"""
from typing import Protocol, runtime_checkable, Optional, List, Dict, Any
from abc import abstractmethod


@runtime_checkable
class DatabaseConfigProtocol(Protocol):
    """Protocol for database configuration management."""
    
    @property
    def database_url(self) -> str:
        """Primary database connection URL."""
        ...
    
    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL (for migrations)."""
        ...
    
    @property
    def db_pool_size(self) -> int:
        """Database connection pool size."""
        ...
    
    @property
    def db_max_overflow(self) -> int:
        """Maximum overflow connections."""
        ...
    
    @property
    def db_pool_timeout(self) -> int:
        """Connection pool timeout in seconds."""
        ...
    
    @property
    def db_pool_recycle(self) -> int:
        """Connection recycle time in seconds."""
        ...
    
    @property
    def db_echo(self) -> bool:
        """Enable database query logging."""
        ...


@runtime_checkable
class CacheConfigProtocol(Protocol):
    """Protocol for cache configuration management."""
    
    @property
    def cache_url(self) -> Optional[str]:
        """Cache server connection URL."""
        ...
    
    @property
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled."""
        ...
    
    @property
    def cache_pool_size(self) -> int:
        """Cache connection pool size."""
        ...
    
    @property
    def cache_decode_responses(self) -> bool:
        """Decode cache responses to strings."""
        ...
    
    @property
    def cache_ttl_default(self) -> int:
        """Default cache TTL in seconds."""
        ...
    
    @property
    def cache_ttl_permissions(self) -> int:
        """Permission cache TTL in seconds."""
        ...
    
    @property
    def cache_ttl_tenant(self) -> int:
        """Tenant data cache TTL in seconds."""
        ...
    
    def get_cache_key_prefix(self) -> str:
        """Get cache key prefix for namespacing."""
        ...


@runtime_checkable
class ServerConfigProtocol(Protocol):
    """Protocol for server configuration management."""
    
    @property
    def host(self) -> str:
        """Server host address."""
        ...
    
    @property
    def port(self) -> int:
        """Server port number."""
        ...
    
    @property
    def workers(self) -> int:
        """Number of worker processes."""
        ...
    
    @property
    def reload(self) -> bool:
        """Enable auto-reload for development."""
        ...


@runtime_checkable
class SecurityConfigProtocol(Protocol):
    """Protocol for security configuration management."""
    
    @property
    def secret_key(self) -> str:
        """Application secret key."""
        ...
    
    @property
    def app_encryption_key(self) -> str:
        """Application encryption key."""
        ...
    
    @property
    def allowed_hosts(self) -> List[str]:
        """Allowed host names."""
        ...
    
    @property
    def cors_origins(self) -> List[str]:
        """CORS allowed origins."""
        ...
    
    @property
    def cors_allow_credentials(self) -> bool:
        """Allow CORS credentials."""
        ...
    
    @property
    def cors_allow_methods(self) -> List[str]:
        """CORS allowed methods."""
        ...
    
    @property
    def cors_allow_headers(self) -> List[str]:
        """CORS allowed headers."""
        ...
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins as processed list."""
        ...


@runtime_checkable
class ApplicationMetadataProtocol(Protocol):
    """Protocol for application metadata management."""
    
    @property
    def app_name(self) -> str:
        """Application name."""
        ...
    
    @property
    def app_version(self) -> str:
        """Application version."""
        ...
    
    @property
    def debug(self) -> bool:
        """Debug mode enabled."""
        ...
    
    @property
    def environment(self) -> str:
        """Current environment (development, production, etc.)."""
        ...
    
    @property
    def api_prefix(self) -> Optional[str]:
        """API route prefix."""
        ...
    
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        ...
    
    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        ...
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing."""
        ...


@runtime_checkable
class LoggingConfigProtocol(Protocol):
    """Protocol for logging configuration management."""
    
    @property
    def log_level(self) -> str:
        """Logging level."""
        ...
    
    @property
    def log_format(self) -> str:
        """Log message format."""
        ...
    
    @property
    def log_file(self) -> Optional[str]:
        """Log file path."""
        ...
    
    @property
    def log_rotation(self) -> str:
        """Log rotation policy."""
        ...
    
    @property
    def log_retention(self) -> str:
        """Log retention policy."""
        ...


@runtime_checkable
class RateLimitingConfigProtocol(Protocol):
    """Protocol for rate limiting configuration management."""
    
    @property
    def rate_limit_enabled(self) -> bool:
        """Rate limiting enabled."""
        ...
    
    @property
    def rate_limit_requests_per_minute(self) -> int:
        """Requests per minute limit."""
        ...
    
    @property
    def rate_limit_requests_per_hour(self) -> int:
        """Requests per hour limit."""
        ...


@runtime_checkable
class PaginationConfigProtocol(Protocol):
    """Protocol for pagination configuration management."""
    
    @property
    def default_page_size(self) -> int:
        """Default page size for paginated results."""
        ...
    
    @property
    def max_page_size(self) -> int:
        """Maximum allowed page size."""
        ...


@runtime_checkable
class MonitoringConfigProtocol(Protocol):
    """Protocol for monitoring configuration management."""
    
    @property
    def metrics_enabled(self) -> bool:
        """Metrics collection enabled."""
        ...


@runtime_checkable
class EnvironmentConfigProtocol(Protocol):
    """Protocol for environment variable handling."""
    
    @abstractmethod
    def get_env_var(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable value."""
        ...
    
    @abstractmethod
    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """Get environment variable as boolean."""
        ...
    
    @abstractmethod
    def get_env_int(self, key: str, default: int = 0) -> int:
        """Get environment variable as integer."""
        ...
    
    @abstractmethod
    def get_env_list(self, key: str, default: Optional[List[str]] = None, separator: str = ",") -> List[str]:
        """Get environment variable as list."""
        ...


@runtime_checkable
class BaseConfigProtocol(
    DatabaseConfigProtocol,
    CacheConfigProtocol,
    ServerConfigProtocol,
    SecurityConfigProtocol,
    ApplicationMetadataProtocol,
    LoggingConfigProtocol,
    RateLimitingConfigProtocol,
    PaginationConfigProtocol,
    MonitoringConfigProtocol,
    EnvironmentConfigProtocol,
    Protocol
):
    """
    Comprehensive configuration protocol combining all configuration aspects.
    
    This is the primary protocol that applications should implement or depend on
    for complete configuration management.
    """
    pass


@runtime_checkable
class ConfigValidationProtocol(Protocol):
    """Protocol for configuration validation."""
    
    @abstractmethod
    def validate_config(self) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        ...
    
    @abstractmethod
    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors."""
        ...
    
    @abstractmethod
    def is_valid(self) -> bool:
        """Check if configuration is valid."""
        ...


@runtime_checkable
class ConfigFactoryProtocol(Protocol):
    """Protocol for configuration factories."""
    
    @abstractmethod
    def create_config(self, **kwargs) -> BaseConfigProtocol:
        """Create a configuration instance."""
        ...
    
    @abstractmethod
    def create_from_env(self) -> BaseConfigProtocol:
        """Create configuration from environment variables."""
        ...
    
    @abstractmethod
    def create_for_testing(self) -> BaseConfigProtocol:
        """Create configuration optimized for testing."""
        ...
    
    @abstractmethod
    def create_for_production(self) -> BaseConfigProtocol:
        """Create configuration optimized for production."""
        ...