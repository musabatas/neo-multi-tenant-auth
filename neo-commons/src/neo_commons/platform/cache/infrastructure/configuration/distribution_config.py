"""Distribution configuration management.

ONLY distribution configuration functionality - handles distributed cache
settings, cluster management, and coordination service configuration.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class DistributionType(Enum):
    """Distribution implementation types."""
    NONE = "none"
    REDIS = "redis"
    KAFKA = "kafka"
    CUSTOM = "custom"


class ConsistencyLevel(Enum):
    """Consistency level options."""
    EVENTUAL = "eventual"
    STRONG = "strong"
    WEAK = "weak"
    CAUSAL = "causal"


class PartitionStrategy(Enum):
    """Partitioning strategies."""
    HASH = "hash"
    RANGE = "range"
    CONSISTENT_HASH = "consistent_hash"
    CUSTOM = "custom"


class ReplicationStrategy(Enum):
    """Replication strategies."""
    SIMPLE = "simple"
    NETWORK_TOPOLOGY = "network_topology"
    RACK_AWARE = "rack_aware"
    DATACENTER_AWARE = "datacenter_aware"


@dataclass
class NodeConfig:
    """Individual node configuration."""
    node_id: str
    host: str
    port: int
    datacenter: str = "default"
    rack: str = "default"
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DistributionConfig:
    """Distribution-specific configuration.
    
    Handles configuration for distributed cache operations, cluster
    management, coordination services, and consistency settings.
    """
    
    # Distribution selection
    distribution_type: DistributionType = DistributionType.NONE
    enable_distribution: bool = False
    
    # Cluster settings
    cluster_name: str = "neo-cache-cluster"
    node_id: Optional[str] = None
    nodes: List[NodeConfig] = field(default_factory=list)
    
    # Consistency settings
    consistency_level: ConsistencyLevel = ConsistencyLevel.EVENTUAL
    read_consistency: Optional[ConsistencyLevel] = None
    write_consistency: Optional[ConsistencyLevel] = None
    
    # Partitioning settings
    partition_strategy: PartitionStrategy = PartitionStrategy.HASH
    partition_count: int = 256
    virtual_nodes_per_partition: int = 150  # for consistent hashing
    
    # Replication settings
    replication_factor: int = 2
    replication_strategy: ReplicationStrategy = ReplicationStrategy.SIMPLE
    auto_failover_enabled: bool = True
    failover_timeout_seconds: int = 30
    
    # Communication settings
    heartbeat_interval_seconds: int = 30
    node_timeout_seconds: int = 90
    connection_timeout_seconds: int = 10
    message_timeout_seconds: int = 5
    
    # Redis distribution settings
    redis_cluster_enabled: bool = False
    redis_sentinel_enabled: bool = False
    redis_sentinel_hosts: List[Dict[str, Any]] = field(default_factory=list)
    redis_sentinel_service_name: str = "neo-cache"
    redis_pub_sub_channel_prefix: str = "neo:cache:events"
    
    # Kafka distribution settings
    kafka_bootstrap_servers: List[str] = field(default_factory=lambda: ["localhost:9092"])
    kafka_topic_prefix: str = "neo.cache"
    kafka_consumer_group_prefix: str = "neo-cache-group"
    kafka_replication_factor: int = 1
    kafka_partition_count: int = 3
    kafka_retention_hours: int = 24
    kafka_compression_type: str = "snappy"  # snappy, gzip, lz4
    
    # Conflict resolution settings
    enable_conflict_resolution: bool = True
    conflict_resolution_strategy: str = "timestamp"  # timestamp, version, custom
    vector_clock_enabled: bool = False
    
    # Network partition handling
    enable_partition_tolerance: bool = True
    partition_detection_threshold: int = 3  # failed heartbeats
    split_brain_protection: bool = True
    minimum_quorum_size: int = 2
    
    # Performance settings
    enable_batch_operations: bool = True
    batch_size: int = 100
    batch_timeout_seconds: float = 0.1
    enable_compression: bool = True
    compression_algorithm: str = "snappy"
    
    # Monitoring settings
    enable_distribution_metrics: bool = True
    enable_network_monitoring: bool = True
    metrics_collection_interval: int = 60  # seconds
    enable_latency_tracking: bool = True
    
    # Security settings
    enable_encryption: bool = False
    encryption_algorithm: str = "AES-256-GCM"
    enable_authentication: bool = False
    auth_token: Optional[str] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate_configuration()
        self._set_defaults()
    
    def _validate_configuration(self):
        """Validate distribution configuration."""
        if self.enable_distribution and self.distribution_type == DistributionType.NONE:
            raise ValueError("distribution_type must be set when distribution is enabled")
        
        if self.replication_factor < 1:
            raise ValueError("replication_factor must be at least 1")
        
        if self.partition_count <= 0:
            raise ValueError("partition_count must be positive")
        
        if self.heartbeat_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds must be positive")
        
        if self.node_timeout_seconds <= self.heartbeat_interval_seconds:
            raise ValueError("node_timeout_seconds must be greater than heartbeat_interval_seconds")
        
        if self.minimum_quorum_size < 1:
            raise ValueError("minimum_quorum_size must be at least 1")
        
        if self.kafka_replication_factor < 1:
            raise ValueError("kafka_replication_factor must be at least 1")
    
    def _set_defaults(self):
        """Set default values for optional fields."""
        if not self.node_id:
            import uuid
            self.node_id = f"node-{str(uuid.uuid4())[:8]}"
        
        if not self.redis_sentinel_hosts:
            self.redis_sentinel_hosts = []
        
        if not self.kafka_bootstrap_servers:
            self.kafka_bootstrap_servers = ["localhost:9092"]
        
        # Set read/write consistency if not specified
        if self.read_consistency is None:
            self.read_consistency = self.consistency_level
        
        if self.write_consistency is None:
            self.write_consistency = self.consistency_level
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis distribution configuration.
        
        Returns:
            Redis distribution configuration
        """
        config = {
            "enabled": self.distribution_type == DistributionType.REDIS,
            "cluster_name": self.cluster_name,
            "node_id": self.node_id,
            "cluster_enabled": self.redis_cluster_enabled,
            "sentinel_enabled": self.redis_sentinel_enabled,
            "sentinel_hosts": self.redis_sentinel_hosts,
            "sentinel_service_name": self.redis_sentinel_service_name,
            "pub_sub_channel_prefix": self.redis_pub_sub_channel_prefix,
            "heartbeat_interval": self.heartbeat_interval_seconds,
            "node_timeout": self.node_timeout_seconds,
            "connection_timeout": self.connection_timeout_seconds
        }
        
        return config
    
    def get_kafka_config(self) -> Dict[str, Any]:
        """Get Kafka distribution configuration.
        
        Returns:
            Kafka distribution configuration
        """
        return {
            "enabled": self.distribution_type == DistributionType.KAFKA,
            "bootstrap_servers": self.kafka_bootstrap_servers,
            "topic_prefix": self.kafka_topic_prefix,
            "consumer_group_prefix": self.kafka_consumer_group_prefix,
            "replication_factor": self.kafka_replication_factor,
            "partition_count": self.kafka_partition_count,
            "retention_hours": self.kafka_retention_hours,
            "compression_type": self.kafka_compression_type,
            "cluster_name": self.cluster_name,
            "node_id": self.node_id
        }
    
    def get_consistency_config(self) -> Dict[str, Any]:
        """Get consistency configuration.
        
        Returns:
            Consistency configuration
        """
        return {
            "level": self.consistency_level.value,
            "read_level": self.read_consistency.value,
            "write_level": self.write_consistency.value,
            "enable_conflict_resolution": self.enable_conflict_resolution,
            "conflict_resolution_strategy": self.conflict_resolution_strategy,
            "vector_clock_enabled": self.vector_clock_enabled
        }
    
    def get_partitioning_config(self) -> Dict[str, Any]:
        """Get partitioning configuration.
        
        Returns:
            Partitioning configuration
        """
        return {
            "strategy": self.partition_strategy.value,
            "partition_count": self.partition_count,
            "virtual_nodes_per_partition": self.virtual_nodes_per_partition,
            "hash_function": "md5"  # could be configurable
        }
    
    def get_replication_config(self) -> Dict[str, Any]:
        """Get replication configuration.
        
        Returns:
            Replication configuration
        """
        return {
            "factor": self.replication_factor,
            "strategy": self.replication_strategy.value,
            "auto_failover_enabled": self.auto_failover_enabled,
            "failover_timeout_seconds": self.failover_timeout_seconds
        }
    
    def get_network_config(self) -> Dict[str, Any]:
        """Get network configuration.
        
        Returns:
            Network configuration
        """
        return {
            "heartbeat_interval": self.heartbeat_interval_seconds,
            "node_timeout": self.node_timeout_seconds,
            "connection_timeout": self.connection_timeout_seconds,
            "message_timeout": self.message_timeout_seconds,
            "enable_compression": self.enable_compression,
            "compression_algorithm": self.compression_algorithm
        }
    
    def get_partition_tolerance_config(self) -> Dict[str, Any]:
        """Get partition tolerance configuration.
        
        Returns:
            Partition tolerance configuration
        """
        return {
            "enabled": self.enable_partition_tolerance,
            "detection_threshold": self.partition_detection_threshold,
            "split_brain_protection": self.split_brain_protection,
            "minimum_quorum_size": self.minimum_quorum_size
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration.
        
        Returns:
            Performance configuration
        """
        return {
            "enable_batch_operations": self.enable_batch_operations,
            "batch_size": self.batch_size,
            "batch_timeout_seconds": self.batch_timeout_seconds,
            "enable_compression": self.enable_compression,
            "compression_algorithm": self.compression_algorithm
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration.
        
        Returns:
            Monitoring configuration
        """
        return {
            "enable_metrics": self.enable_distribution_metrics,
            "enable_network_monitoring": self.enable_network_monitoring,
            "collection_interval": self.metrics_collection_interval,
            "enable_latency_tracking": self.enable_latency_tracking
        }
    
    def get_security_config(self) -> Dict[str, Any]:
        """Get security configuration.
        
        Returns:
            Security configuration
        """
        return {
            "enable_encryption": self.enable_encryption,
            "encryption_algorithm": self.encryption_algorithm,
            "enable_authentication": self.enable_authentication,
            "auth_token": self.auth_token
        }
    
    def add_node(self, node: NodeConfig) -> None:
        """Add node to cluster configuration.
        
        Args:
            node: Node configuration to add
        """
        # Check for duplicate node IDs
        existing_ids = {n.node_id for n in self.nodes}
        if node.node_id in existing_ids:
            raise ValueError(f"Node ID already exists: {node.node_id}")
        
        self.nodes.append(node)
    
    def remove_node(self, node_id: str) -> bool:
        """Remove node from cluster configuration.
        
        Args:
            node_id: ID of node to remove
            
        Returns:
            True if node was removed
        """
        for i, node in enumerate(self.nodes):
            if node.node_id == node_id:
                del self.nodes[i]
                return True
        return False
    
    def get_node(self, node_id: str) -> Optional[NodeConfig]:
        """Get node configuration by ID.
        
        Args:
            node_id: ID of node to get
            
        Returns:
            Node configuration or None if not found
        """
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None
    
    def get_nodes_by_datacenter(self, datacenter: str) -> List[NodeConfig]:
        """Get nodes in specific datacenter.
        
        Args:
            datacenter: Datacenter name
            
        Returns:
            List of nodes in datacenter
        """
        return [node for node in self.nodes if node.datacenter == datacenter]
    
    def is_redis_enabled(self) -> bool:
        """Check if Redis distribution is enabled.
        
        Returns:
            True if Redis distribution is configured
        """
        return (self.enable_distribution and 
                self.distribution_type == DistributionType.REDIS)
    
    def is_kafka_enabled(self) -> bool:
        """Check if Kafka distribution is enabled.
        
        Returns:
            True if Kafka distribution is configured
        """
        return (self.enable_distribution and 
                self.distribution_type == DistributionType.KAFKA)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        config_dict = {}
        
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, Enum):
                config_dict[field_name] = field_value.value
            elif isinstance(field_value, list) and field_value and hasattr(field_value[0], '__dict__'):
                # Handle NodeConfig objects
                config_dict[field_name] = [
                    {k: v.value if isinstance(v, Enum) else v 
                     for k, v in item.__dict__.items()}
                    for item in field_value
                ]
            else:
                config_dict[field_name] = field_value
        
        return config_dict
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return (f"DistributionConfig(type={self.distribution_type.value}, "
                f"enabled={self.enable_distribution})")
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"DistributionConfig(type={self.distribution_type.value}, "
                f"cluster={self.cluster_name}, "
                f"nodes={len(self.nodes)}, "
                f"replication={self.replication_factor})")


def create_distribution_config(
    distribution_type: str = "none",
    overrides: Optional[Dict[str, Any]] = None
) -> DistributionConfig:
    """Factory function to create distribution configuration.
    
    Args:
        distribution_type: Type of distribution ("none", "redis", "kafka")
        overrides: Optional configuration overrides
        
    Returns:
        Configured distribution configuration instance
    """
    config_data = {
        "distribution_type": DistributionType(distribution_type)
    }
    
    if overrides:
        # Handle enum conversions
        if "consistency_level" in overrides:
            overrides["consistency_level"] = ConsistencyLevel(overrides["consistency_level"])
        
        if "read_consistency" in overrides and overrides["read_consistency"]:
            overrides["read_consistency"] = ConsistencyLevel(overrides["read_consistency"])
        
        if "write_consistency" in overrides and overrides["write_consistency"]:
            overrides["write_consistency"] = ConsistencyLevel(overrides["write_consistency"])
        
        if "partition_strategy" in overrides:
            overrides["partition_strategy"] = PartitionStrategy(overrides["partition_strategy"])
        
        if "replication_strategy" in overrides:
            overrides["replication_strategy"] = ReplicationStrategy(overrides["replication_strategy"])
        
        # Handle node configurations
        if "nodes" in overrides and isinstance(overrides["nodes"], list):
            node_configs = []
            for node_data in overrides["nodes"]:
                if isinstance(node_data, dict):
                    node_configs.append(NodeConfig(**node_data))
                else:
                    node_configs.append(node_data)
            overrides["nodes"] = node_configs
        
        config_data.update(overrides)
    
    return DistributionConfig(**config_data)