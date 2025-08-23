"""Cache configuration for neo-commons."""

from typing import Dict, Optional, Any, List, Union
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from enum import Enum

from .protocols import CacheBackend, CacheStrategy, SerializationFormat


class CacheSettings(BaseSettings):
    """Global cache settings."""
    
    # Default backend configuration
    default_backend: CacheBackend = Field(default=CacheBackend.REDIS, description="Default cache backend")
    default_ttl_seconds: int = Field(default=3600, ge=0, description="Default TTL in seconds")
    default_max_connections: int = Field(default=10, ge=1, description="Default max connections")
    
    # Redis configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    redis_ssl: bool = Field(default=False, description="Use SSL for Redis")
    redis_max_connections: int = Field(default=50, ge=1, description="Max Redis connections")
    redis_connection_timeout: int = Field(default=5, ge=1, description="Redis connection timeout")
    redis_command_timeout: int = Field(default=3, ge=1, description="Redis command timeout")
    
    # Redis Cluster configuration
    redis_cluster_nodes: List[str] = Field(default_factory=list, description="Redis cluster nodes")
    redis_cluster_max_connections_per_node: int = Field(default=10, ge=1, description="Max connections per cluster node")
    
    # Memory cache configuration
    memory_max_size: int = Field(default=1000, ge=1, description="Max memory cache entries")
    memory_cleanup_interval: int = Field(default=60, ge=10, description="Memory cleanup interval in seconds")
    
    # Serialization settings
    default_serialization: SerializationFormat = Field(default=SerializationFormat.JSON, description="Default serialization")
    enable_compression: bool = Field(default=False, description="Enable value compression")
    compression_threshold: int = Field(default=1024, ge=0, description="Compression threshold in bytes")
    compression_level: int = Field(default=6, ge=1, le=9, description="Compression level")
    
    # Performance settings
    enable_metrics: bool = Field(default=True, description="Enable cache metrics")
    enable_events: bool = Field(default=False, description="Enable cache events")
    metrics_flush_interval: int = Field(default=30, ge=5, description="Metrics flush interval")
    
    # Tenant isolation
    enable_tenant_isolation: bool = Field(default=True, description="Enable tenant isolation")
    tenant_key_prefix: str = Field(default="tenant", description="Tenant key prefix")
    tenant_quota_enabled: bool = Field(default=False, description="Enable tenant quotas")
    
    # Distributed cache settings
    enable_distributed: bool = Field(default=False, description="Enable distributed cache")
    node_id: Optional[str] = Field(default=None, description="Node ID for distributed cache")
    cluster_discovery_interval: int = Field(default=30, ge=10, description="Cluster discovery interval")
    
    @validator('redis_cluster_nodes')
    def validate_cluster_nodes(cls, v):
        """Validate cluster node format."""
        for node in v:
            if ':' not in node:
                raise ValueError(f"Invalid cluster node format: {node}. Expected 'host:port'")
        return v
    
    class Config:
        env_prefix = "NEO_CACHE_"
        case_sensitive = False


@dataclass
class CacheKeyConfig:
    """Configuration for cache key management."""
    
    # Key structure
    prefix: str = "neo"
    separator: str = ":"
    max_length: int = 250
    
    # Key validation
    allowed_chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_:"
    case_sensitive: bool = True
    
    # Tenant isolation
    tenant_isolation: bool = True
    tenant_prefix: str = "tenant"
    
    def build_key(self, *parts: str) -> str:
        """Build cache key from parts."""
        # Filter out empty parts
        clean_parts = [str(part) for part in parts if part is not None and str(part)]
        
        # Add prefix
        if self.prefix:
            clean_parts.insert(0, self.prefix)
        
        # Join with separator
        key = self.separator.join(clean_parts)
        
        # Validate key
        if len(key) > self.max_length:
            raise ValueError(f"Cache key too long: {len(key)} > {self.max_length}")
        
        if not all(c in self.allowed_chars for c in key):
            raise ValueError(f"Cache key contains invalid characters: {key}")
        
        return key
    
    def build_tenant_key(self, tenant_id: str, *parts: str) -> str:
        """Build tenant-specific cache key."""
        if self.tenant_isolation:
            return self.build_key(self.tenant_prefix, tenant_id, *parts)
        else:
            return self.build_key(*parts)


@dataclass
class CacheBackendConfig:
    """Configuration for a specific cache backend."""
    
    # Backend identification
    name: str
    backend_type: CacheBackend
    
    # Connection settings
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    database: int = 0
    ssl: bool = False
    
    # Pool settings
    max_connections: int = 10
    min_connections: int = 1
    connection_timeout: int = 5
    command_timeout: int = 3
    retry_attempts: int = 3
    retry_delay: float = 0.1
    
    # Behavior settings
    default_ttl: int = 3600
    key_prefix: str = ""
    enable_pipelining: bool = True
    enable_compression: bool = False
    compression_threshold: int = 1024
    
    # Advanced settings
    serialization_format: SerializationFormat = SerializationFormat.JSON
    health_check_interval: int = 30
    eviction_policy: str = "allkeys-lru"
    max_memory_mb: Optional[int] = None
    
    # Cluster settings (for Redis Cluster)
    cluster_nodes: List[str] = field(default_factory=list)
    max_connections_per_node: int = 10
    cluster_require_full_coverage: bool = True
    
    def to_connection_kwargs(self) -> Dict[str, Any]:
        """Convert to connection arguments for the backend."""
        kwargs = {
            "host": self.host,
            "port": self.port,
            "db": self.database,
            "password": self.password,
            "socket_timeout": self.command_timeout,
            "socket_connect_timeout": self.connection_timeout,
            "retry_on_timeout": True,
            "retry_on_error": [ConnectionError, TimeoutError],
            "health_check_interval": self.health_check_interval,
        }
        
        # Only add ssl if it's True (Redis asyncio doesn't like ssl=False)
        if self.ssl:
            kwargs["ssl"] = self.ssl
        
        # Add pool settings for Redis
        if self.backend_type in (CacheBackend.REDIS, CacheBackend.REDIS_CLUSTER):
            kwargs.update({
                "max_connections": self.max_connections
            })
        
        return kwargs


@dataclass
class CacheInstanceConfig:
    """Configuration for a specific cache instance."""
    
    # Instance identification
    name: str
    backend_config: CacheBackendConfig
    
    # Cache behavior
    default_ttl: Optional[int] = None
    strategy: CacheStrategy = CacheStrategy.TTL
    max_size: Optional[int] = None
    
    # Key management
    key_config: CacheKeyConfig = field(default_factory=CacheKeyConfig)
    
    # Serialization
    serialization_format: SerializationFormat = SerializationFormat.JSON
    enable_compression: bool = False
    compression_threshold: int = 1024
    
    # Features
    enable_metrics: bool = True
    enable_events: bool = False
    enable_transactions: bool = False
    enable_distributed: bool = False
    
    # Tenant features
    enable_tenant_isolation: bool = True
    enable_tenant_quotas: bool = False
    tenant_max_keys: int = 10000
    tenant_max_memory_mb: int = 100
    
    # Tags and invalidation
    enable_tags: bool = False
    tag_separator: str = ","
    max_tags_per_key: int = 10
    
    # Warmup and preloading
    enable_warmup: bool = False
    warmup_patterns: List[str] = field(default_factory=list)
    
    def get_effective_ttl(self) -> int:
        """Get effective TTL (instance or backend default)."""
        return self.default_ttl or self.backend_config.default_ttl
    
    def get_key_config(self) -> CacheKeyConfig:
        """Get key configuration with overrides."""
        key_config = self.key_config
        
        # Apply backend prefix if not set
        if not key_config.prefix and self.backend_config.key_prefix:
            key_config.prefix = self.backend_config.key_prefix
        
        return key_config


@dataclass
class CacheRegistryConfig:
    """Configuration for cache registry."""
    
    # Registry settings
    default_cache_name: str = "default"
    auto_create_default: bool = True
    
    # Backend configurations
    backends: Dict[str, CacheBackendConfig] = field(default_factory=dict)
    
    # Cache instances
    caches: Dict[str, CacheInstanceConfig] = field(default_factory=dict)
    
    # Global settings
    global_key_config: CacheKeyConfig = field(default_factory=CacheKeyConfig)
    global_metrics_enabled: bool = True
    global_events_enabled: bool = False
    
    def add_backend(self, config: CacheBackendConfig) -> None:
        """Add backend configuration."""
        self.backends[config.name] = config
    
    def add_cache(self, config: CacheInstanceConfig) -> None:
        """Add cache instance configuration."""
        self.caches[config.name] = config
    
    def get_backend(self, name: str) -> Optional[CacheBackendConfig]:
        """Get backend configuration."""
        return self.backends.get(name)
    
    def get_cache(self, name: str) -> Optional[CacheInstanceConfig]:
        """Get cache instance configuration."""
        return self.caches.get(name)
    
    def get_default_cache(self) -> Optional[CacheInstanceConfig]:
        """Get default cache configuration."""
        return self.caches.get(self.default_cache_name)


def create_default_registry_config(settings: CacheSettings) -> CacheRegistryConfig:
    """Create default cache registry configuration from settings."""
    registry_config = CacheRegistryConfig()
    
    # Create default backend configuration
    if settings.default_backend == CacheBackend.REDIS:
        backend_config = CacheBackendConfig(
            name="default-redis",
            backend_type=CacheBackend.REDIS,
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            database=settings.redis_db,
            ssl=settings.redis_ssl,
            max_connections=settings.redis_max_connections,
            connection_timeout=settings.redis_connection_timeout,
            command_timeout=settings.redis_command_timeout,
            default_ttl=settings.default_ttl_seconds,
            serialization_format=settings.default_serialization,
            enable_compression=settings.enable_compression,
            compression_threshold=settings.compression_threshold,
        )
    else:
        # Memory backend
        backend_config = CacheBackendConfig(
            name="default-memory",
            backend_type=CacheBackend.MEMORY,
            default_ttl=settings.default_ttl_seconds,
            serialization_format=settings.default_serialization,
        )
    
    registry_config.add_backend(backend_config)
    
    # Create default cache instance
    cache_config = CacheInstanceConfig(
        name="default",
        backend_config=backend_config,
        default_ttl=settings.default_ttl_seconds,
        key_config=CacheKeyConfig(
            tenant_isolation=settings.enable_tenant_isolation,
            tenant_prefix=settings.tenant_key_prefix,
        ),
        serialization_format=settings.default_serialization,
        enable_compression=settings.enable_compression,
        compression_threshold=settings.compression_threshold,
        enable_metrics=settings.enable_metrics,
        enable_events=settings.enable_events,
        enable_tenant_isolation=settings.enable_tenant_isolation,
        enable_tenant_quotas=settings.tenant_quota_enabled,
        enable_distributed=settings.enable_distributed,
    )
    
    registry_config.add_cache(cache_config)
    
    return registry_config


# Global configuration instances
cache_settings = CacheSettings()
default_registry_config = create_default_registry_config(cache_settings)