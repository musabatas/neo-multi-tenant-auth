"""Repository configuration management.

ONLY repository configuration functionality - handles cache repository
settings, connection parameters, and backend-specific configurations.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class RepositoryType(Enum):
    """Repository implementation types."""
    MEMORY = "memory"
    REDIS = "redis"
    DISTRIBUTED = "distributed"


class ConnectionPooling(Enum):
    """Connection pooling strategies."""
    NONE = "none"
    SIMPLE = "simple"
    ADVANCED = "advanced"


@dataclass
class RepositoryConfig:
    """Repository-specific configuration.
    
    Handles configuration for different cache repository implementations
    with connection management, pooling, and backend-specific settings.
    """
    
    # Repository selection
    repository_type: RepositoryType = RepositoryType.MEMORY
    
    # Connection settings
    connection_timeout: int = 5  # seconds
    read_timeout: int = 3  # seconds
    write_timeout: int = 3  # seconds
    
    # Connection pooling
    pooling_strategy: ConnectionPooling = ConnectionPooling.SIMPLE
    min_connections: int = 1
    max_connections: int = 10
    connection_idle_timeout: int = 300  # seconds
    connection_max_age: int = 3600  # seconds
    
    # Retry settings
    max_retries: int = 3
    retry_backoff_factor: float = 0.5
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    
    # Memory repository settings
    memory_initial_capacity: int = 1000
    memory_load_factor: float = 0.75
    memory_cleanup_interval: int = 60  # seconds
    memory_max_entries: int = 10000
    memory_max_memory_mb: int = 100
    
    # Redis repository settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_username: Optional[str] = None
    redis_ssl: bool = False
    redis_ssl_cert_path: Optional[str] = None
    redis_ssl_key_path: Optional[str] = None
    redis_ssl_ca_path: Optional[str] = None
    redis_cluster_mode: bool = False
    redis_cluster_nodes: List[Dict[str, Any]] = None
    redis_sentinel_hosts: List[Dict[str, Any]] = None
    redis_sentinel_service_name: Optional[str] = None
    
    # Distributed repository settings
    distributed_nodes: List[Dict[str, Any]] = None
    distributed_replication_factor: int = 2
    distributed_consistency_level: str = "eventual"  # eventual, strong, weak
    distributed_partitioning_strategy: str = "hash"  # hash, range, custom
    
    # Performance tuning
    enable_pipelining: bool = True
    pipeline_batch_size: int = 100
    enable_compression: bool = False
    compression_algorithm: str = "gzip"  # gzip, lz4, snappy
    compression_level: int = 6
    
    # Monitoring and health
    enable_connection_monitoring: bool = True
    health_check_interval: int = 30  # seconds
    connection_metrics_enabled: bool = True
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate_configuration()
        self._set_defaults()
    
    def _validate_configuration(self):
        """Validate repository configuration."""
        if self.min_connections <= 0:
            raise ValueError("min_connections must be positive")
        
        if self.max_connections < self.min_connections:
            raise ValueError("max_connections must be >= min_connections")
        
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
        
        if self.redis_port < 1 or self.redis_port > 65535:
            raise ValueError("redis_port must be between 1 and 65535")
        
        if self.memory_load_factor <= 0 or self.memory_load_factor >= 1:
            raise ValueError("memory_load_factor must be between 0 and 1")
        
        if self.distributed_replication_factor < 1:
            raise ValueError("distributed_replication_factor must be at least 1")
    
    def _set_defaults(self):
        """Set default values for optional fields."""
        if self.redis_cluster_nodes is None:
            self.redis_cluster_nodes = []
        
        if self.redis_sentinel_hosts is None:
            self.redis_sentinel_hosts = []
        
        if self.distributed_nodes is None:
            self.distributed_nodes = []
    
    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory repository configuration.
        
        Returns:
            Memory repository configuration
        """
        return {
            "initial_capacity": self.memory_initial_capacity,
            "load_factor": self.memory_load_factor,
            "cleanup_interval": self.memory_cleanup_interval,
            "connection_timeout": self.connection_timeout
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis repository configuration.
        
        Returns:
            Redis repository configuration
        """
        config = {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "password": self.redis_password,
            "username": self.redis_username,
            "ssl": self.redis_ssl,
            "connection_timeout": self.connection_timeout,
            "socket_timeout": self.read_timeout,
            "socket_connect_timeout": self.connection_timeout,
            "retry_on_timeout": self.retry_on_timeout,
            "health_check_interval": self.health_check_interval,
            "max_connections": self.max_connections
        }
        
        # SSL configuration
        if self.redis_ssl:
            ssl_config = {}
            if self.redis_ssl_cert_path:
                ssl_config["ssl_certfile"] = self.redis_ssl_cert_path
            if self.redis_ssl_key_path:
                ssl_config["ssl_keyfile"] = self.redis_ssl_key_path
            if self.redis_ssl_ca_path:
                ssl_config["ssl_ca_certs"] = self.redis_ssl_ca_path
            config.update(ssl_config)
        
        # Cluster configuration
        if self.redis_cluster_mode and self.redis_cluster_nodes:
            config["cluster_nodes"] = self.redis_cluster_nodes
        
        # Sentinel configuration
        if self.redis_sentinel_hosts:
            config["sentinel_hosts"] = self.redis_sentinel_hosts
            config["sentinel_service_name"] = self.redis_sentinel_service_name
        
        return config
    
    def get_distributed_config(self) -> Dict[str, Any]:
        """Get distributed repository configuration.
        
        Returns:
            Distributed repository configuration
        """
        return {
            "nodes": self.distributed_nodes,
            "replication_factor": self.distributed_replication_factor,
            "consistency_level": self.distributed_consistency_level,
            "partitioning_strategy": self.distributed_partitioning_strategy,
            "connection_timeout": self.connection_timeout,
            "read_timeout": self.read_timeout,
            "write_timeout": self.write_timeout,
            "max_retries": self.max_retries,
            "retry_backoff_factor": self.retry_backoff_factor
        }
    
    def get_connection_pool_config(self) -> Dict[str, Any]:
        """Get connection pool configuration.
        
        Returns:
            Connection pool configuration
        """
        return {
            "pooling_strategy": self.pooling_strategy.value,
            "min_connections": self.min_connections,
            "max_connections": self.max_connections,
            "connection_idle_timeout": self.connection_idle_timeout,
            "connection_max_age": self.connection_max_age,
            "health_check_interval": self.health_check_interval,
            "monitoring_enabled": self.enable_connection_monitoring
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration.
        
        Returns:
            Performance configuration
        """
        return {
            "enable_pipelining": self.enable_pipelining,
            "pipeline_batch_size": self.pipeline_batch_size,
            "enable_compression": self.enable_compression,
            "compression_algorithm": self.compression_algorithm,
            "compression_level": self.compression_level,
            "connection_metrics_enabled": self.connection_metrics_enabled
        }
    
    def is_redis_cluster_enabled(self) -> bool:
        """Check if Redis cluster mode is enabled.
        
        Returns:
            True if Redis cluster is configured
        """
        return (self.repository_type == RepositoryType.REDIS and 
                self.redis_cluster_mode and 
                len(self.redis_cluster_nodes) > 0)
    
    def is_redis_sentinel_enabled(self) -> bool:
        """Check if Redis Sentinel is enabled.
        
        Returns:
            True if Redis Sentinel is configured
        """
        return (self.repository_type == RepositoryType.REDIS and 
                len(self.redis_sentinel_hosts) > 0 and 
                self.redis_sentinel_service_name is not None)
    
    def is_distributed_enabled(self) -> bool:
        """Check if distributed repository is enabled.
        
        Returns:
            True if distributed repository is configured
        """
        return (self.repository_type == RepositoryType.DISTRIBUTED and 
                len(self.distributed_nodes) > 0)
    
    def get_repository_config_for_type(self) -> Dict[str, Any]:
        """Get configuration specific to the selected repository type.
        
        Returns:
            Type-specific repository configuration
        """
        if self.repository_type == RepositoryType.MEMORY:
            return self.get_memory_config()
        elif self.repository_type == RepositoryType.REDIS:
            return self.get_redis_config()
        elif self.repository_type == RepositoryType.DISTRIBUTED:
            return self.get_distributed_config()
        else:
            raise ValueError(f"Unsupported repository type: {self.repository_type}")
    
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
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return f"RepositoryConfig(type={self.repository_type.value})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"RepositoryConfig(type={self.repository_type.value}, "
                f"connections={self.min_connections}-{self.max_connections}, "
                f"timeout={self.connection_timeout}s)")


def create_repository_config(
    repository_type: str = "memory",
    overrides: Optional[Dict[str, Any]] = None
) -> RepositoryConfig:
    """Factory function to create repository configuration.
    
    Args:
        repository_type: Type of repository ("memory", "redis", "distributed")
        overrides: Optional configuration overrides
        
    Returns:
        Configured repository configuration instance
    """
    config_data = {
        "repository_type": RepositoryType(repository_type)
    }
    
    if overrides:
        config_data.update(overrides)
    
    return RepositoryConfig(**config_data)