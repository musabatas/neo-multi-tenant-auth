"""Cache configuration management.

ONLY cache configuration functionality - handles cache settings,
defaults, validation, and environment-based configuration.

Following maximum separation architecture - one file = one purpose.
"""

import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml
from enum import Enum


class ConfigSource(Enum):
    """Configuration source types."""
    ENVIRONMENT = "environment"
    FILE = "file"
    DEFAULTS = "defaults"
    OVERRIDE = "override"


class CacheBackend(Enum):
    """Supported cache backend types."""
    MEMORY = "memory"
    REDIS = "redis"
    DISTRIBUTED = "distributed"


class SerializerType(Enum):
    """Supported serializer types."""
    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"


class EvictionPolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheConfig:
    """Main cache configuration.
    
    Centralizes all cache-related settings with environment variable
    support, file-based configuration, and validation.
    """
    
    # Core cache settings
    default_ttl_seconds: int = 3600  # 1 hour
    max_entries: int = 10000
    default_namespace: str = "default"
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    
    # Backend configuration
    backend: CacheBackend = CacheBackend.MEMORY
    serializer: SerializerType = SerializerType.JSON
    
    # Performance settings
    enable_compression: bool = False
    compression_threshold_bytes: int = 1024
    enable_metrics: bool = True
    enable_health_checks: bool = True
    
    # Redis settings (when backend=redis)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_ssl: bool = False
    redis_connection_pool_size: int = 10
    redis_socket_timeout: int = 5
    
    # Distributed settings
    cluster_name: str = "neo-cache-cluster"
    node_id: Optional[str] = None
    enable_distribution: bool = False
    
    # Invalidation settings
    enable_pattern_invalidation: bool = True
    enable_time_invalidation: bool = True  
    enable_event_invalidation: bool = True
    invalidation_batch_size: int = 1000
    
    # Monitoring settings
    stats_collection_interval: int = 60  # seconds
    health_check_interval: int = 30  # seconds
    health_check_timeout_seconds: float = 5.0
    
    # Event publishing settings
    event_batch_size: int = 100
    event_flush_interval: int = 30  # seconds
    
    # Development settings
    debug_mode: bool = False
    log_cache_operations: bool = False
    
    # Configuration metadata
    config_source: ConfigSource = ConfigSource.DEFAULTS
    config_file_path: Optional[str] = None
    environment_prefix: str = "NEO_CACHE"
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate_configuration()
        self._set_derived_values()
    
    def _validate_configuration(self):
        """Validate configuration values."""
        if self.max_entries <= 0:
            raise ValueError("max_entries must be positive")
        
        if self.default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        
        if self.redis_port < 1 or self.redis_port > 65535:
            raise ValueError("redis_port must be between 1 and 65535")
        
        if self.compression_threshold_bytes < 0:
            raise ValueError("compression_threshold_bytes must be non-negative")
        
        if self.invalidation_batch_size <= 0:
            raise ValueError("invalidation_batch_size must be positive")
    
    def _set_derived_values(self):
        """Set derived configuration values."""
        if not self.node_id:
            import uuid
            self.node_id = f"node-{str(uuid.uuid4())[:8]}"
    
    @classmethod
    def from_environment(
        cls, 
        prefix: str = "NEO_CACHE",
        defaults: Optional['CacheConfig'] = None
    ) -> 'CacheConfig':
        """Create configuration from environment variables.
        
        Args:
            prefix: Environment variable prefix
            defaults: Default configuration to override
            
        Returns:
            Configuration instance
        """
        base_config = defaults or cls()
        
        # Map environment variables to config fields
        env_mapping = {
            f"{prefix}_DEFAULT_TTL_SECONDS": ("default_ttl_seconds", int),
            f"{prefix}_MAX_ENTRIES": ("max_entries", int),
            f"{prefix}_DEFAULT_NAMESPACE": ("default_namespace", str),
            f"{prefix}_EVICTION_POLICY": ("eviction_policy", lambda x: EvictionPolicy(x)),
            f"{prefix}_BACKEND": ("backend", lambda x: CacheBackend(x)),
            f"{prefix}_SERIALIZER": ("serializer", lambda x: SerializerType(x)),
            f"{prefix}_ENABLE_COMPRESSION": ("enable_compression", lambda x: x.lower() == 'true'),
            f"{prefix}_COMPRESSION_THRESHOLD_BYTES": ("compression_threshold_bytes", int),
            f"{prefix}_ENABLE_METRICS": ("enable_metrics", lambda x: x.lower() == 'true'),
            f"{prefix}_ENABLE_HEALTH_CHECKS": ("enable_health_checks", lambda x: x.lower() == 'true'),
            f"{prefix}_REDIS_HOST": ("redis_host", str),
            f"{prefix}_REDIS_PORT": ("redis_port", int),
            f"{prefix}_REDIS_DB": ("redis_db", int),
            f"{prefix}_REDIS_PASSWORD": ("redis_password", str),
            f"{prefix}_REDIS_SSL": ("redis_ssl", lambda x: x.lower() == 'true'),
            f"{prefix}_REDIS_CONNECTION_POOL_SIZE": ("redis_connection_pool_size", int),
            f"{prefix}_REDIS_SOCKET_TIMEOUT": ("redis_socket_timeout", int),
            f"{prefix}_CLUSTER_NAME": ("cluster_name", str),
            f"{prefix}_NODE_ID": ("node_id", str),
            f"{prefix}_ENABLE_DISTRIBUTION": ("enable_distribution", lambda x: x.lower() == 'true'),
            f"{prefix}_ENABLE_PATTERN_INVALIDATION": ("enable_pattern_invalidation", lambda x: x.lower() == 'true'),
            f"{prefix}_ENABLE_TIME_INVALIDATION": ("enable_time_invalidation", lambda x: x.lower() == 'true'),
            f"{prefix}_ENABLE_EVENT_INVALIDATION": ("enable_event_invalidation", lambda x: x.lower() == 'true'),
            f"{prefix}_INVALIDATION_BATCH_SIZE": ("invalidation_batch_size", int),
            f"{prefix}_STATS_COLLECTION_INTERVAL": ("stats_collection_interval", int),
            f"{prefix}_HEALTH_CHECK_INTERVAL": ("health_check_interval", int),
            f"{prefix}_DEBUG_MODE": ("debug_mode", lambda x: x.lower() == 'true'),
            f"{prefix}_LOG_CACHE_OPERATIONS": ("log_cache_operations", lambda x: x.lower() == 'true'),
        }
        
        config_dict = {}
        
        for env_var, (field_name, converter) in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    config_dict[field_name] = converter(env_value)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"Invalid value for {env_var}: {env_value} - {e}")
        
        # Create new config with overrides
        config_dict.update({
            "config_source": ConfigSource.ENVIRONMENT,
            "environment_prefix": prefix
        })
        
        return cls(**{**base_config.__dict__, **config_dict})
    
    @classmethod
    def from_file(
        cls, 
        file_path: Union[str, Path],
        defaults: Optional['CacheConfig'] = None
    ) -> 'CacheConfig':
        """Create configuration from file (JSON or YAML).
        
        Args:
            file_path: Path to configuration file
            defaults: Default configuration to override
            
        Returns:
            Configuration instance
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        # Load file based on extension
        with open(file_path, 'r') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                config_data = json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {file_path.suffix}")
        
        # Convert string enums to enum objects
        if 'eviction_policy' in config_data:
            config_data['eviction_policy'] = EvictionPolicy(config_data['eviction_policy'])
        if 'backend' in config_data:
            config_data['backend'] = CacheBackend(config_data['backend'])
        if 'serializer' in config_data:
            config_data['serializer'] = SerializerType(config_data['serializer'])
        
        base_config = defaults or cls()
        config_data.update({
            "config_source": ConfigSource.FILE,
            "config_file_path": str(file_path)
        })
        
        return cls(**{**base_config.__dict__, **config_data})
    
    @classmethod
    def from_dict(
        cls,
        config_dict: Dict[str, Any],
        source: ConfigSource = ConfigSource.OVERRIDE
    ) -> 'CacheConfig':
        """Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            source: Configuration source type
            
        Returns:
            Configuration instance
        """
        config_data = dict(config_dict)
        config_data["config_source"] = source
        
        return cls(**config_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        config_dict = {}
        
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, Enum):
                config_dict[field_name] = field_value.value
            else:
                config_dict[field_name] = field_value
        
        return config_dict
    
    def to_json(self, indent: int = 2) -> str:
        """Convert configuration to JSON string.
        
        Args:
            indent: JSON indentation level
            
        Returns:
            JSON configuration string
        """
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_yaml(self) -> str:
        """Convert configuration to YAML string.
        
        Returns:
            YAML configuration string
        """
        return yaml.dump(self.to_dict(), default_flow_style=False)
    
    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save configuration to file.
        
        Args:
            file_path: Path to save configuration
        """
        file_path = Path(file_path)
        
        with open(file_path, 'w') as f:
            if file_path.suffix.lower() in ['.yaml', '.yml']:
                f.write(self.to_yaml())
            elif file_path.suffix.lower() == '.json':
                f.write(self.to_json())
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
    
    def update(self, **kwargs) -> 'CacheConfig':
        """Create new configuration with updated values.
        
        Args:
            **kwargs: Configuration fields to update
            
        Returns:
            New configuration instance
        """
        config_dict = self.to_dict()
        config_dict.update(kwargs)
        config_dict["config_source"] = ConfigSource.OVERRIDE
        
        return self.__class__(**config_dict)
    
    def get_redis_connection_params(self) -> Dict[str, Any]:
        """Get Redis connection parameters.
        
        Returns:
            Redis connection parameters
        """
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "password": self.redis_password,
            "ssl": self.redis_ssl,
            "socket_timeout": self.redis_socket_timeout,
            "max_connections": self.redis_connection_pool_size
        }
    
    def is_redis_enabled(self) -> bool:
        """Check if Redis backend is enabled.
        
        Returns:
            True if Redis is the configured backend
        """
        return self.backend == CacheBackend.REDIS
    
    def is_distributed_enabled(self) -> bool:
        """Check if distributed caching is enabled.
        
        Returns:
            True if distribution is enabled
        """
        return self.enable_distribution or self.backend == CacheBackend.DISTRIBUTED
    
    def get_invalidation_config(self) -> Dict[str, bool]:
        """Get invalidation configuration.
        
        Returns:
            Invalidation settings dictionary
        """
        return {
            "pattern": self.enable_pattern_invalidation,
            "time": self.enable_time_invalidation,
            "event": self.enable_event_invalidation
        }
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"CacheConfig(backend={self.backend.value}, source={self.config_source.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"CacheConfig(backend={self.backend.value}, "
                f"max_entries={self.max_entries}, "
                f"ttl={self.default_ttl_seconds}s, "
                f"source={self.config_source.value})")


def create_cache_config(
    source: str = "environment",
    config_path: Optional[str] = None,
    overrides: Optional[Dict[str, Any]] = None
) -> CacheConfig:
    """Factory function to create cache configuration.
    
    Args:
        source: Configuration source ("environment", "file", "defaults")
        config_path: Path to configuration file (if source="file")
        overrides: Optional configuration overrides
        
    Returns:
        Configured cache configuration instance
    """
    if source == "environment":
        config = CacheConfig.from_environment()
    elif source == "file":
        if not config_path:
            raise ValueError("config_path required when source='file'")
        config = CacheConfig.from_file(config_path)
    elif source == "defaults":
        config = CacheConfig()
    else:
        raise ValueError(f"Invalid configuration source: {source}")
    
    if overrides:
        config = config.update(**overrides)
    
    return config