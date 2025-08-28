"""Invalidation configuration management.

ONLY invalidation configuration functionality - handles invalidation
strategy settings, scheduler configuration, and event trigger management.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import timedelta


class InvalidationStrategy(Enum):
    """Invalidation strategy types."""
    IMMEDIATE = "immediate"
    BATCHED = "batched"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"


class PatternType(Enum):
    """Pattern matching types."""
    WILDCARD = "wildcard"
    REGEX = "regex"
    LITERAL = "literal"


class SchedulerType(Enum):
    """Scheduler implementation types."""
    MEMORY = "memory"
    REDIS = "redis"
    DATABASE = "database"


@dataclass
class InvalidationConfig:
    """Invalidation-specific configuration.
    
    Handles configuration for cache invalidation strategies, schedulers,
    pattern matching, and event-driven invalidation.
    """
    
    # Strategy selection
    default_strategy: InvalidationStrategy = InvalidationStrategy.IMMEDIATE
    enable_pattern_invalidation: bool = True
    enable_time_invalidation: bool = True
    enable_event_invalidation: bool = True
    
    # Pattern invalidation settings
    supported_pattern_types: List[PatternType] = field(default_factory=lambda: [
        PatternType.WILDCARD, PatternType.REGEX, PatternType.LITERAL
    ])
    max_pattern_complexity: int = 1000  # regex complexity limit
    pattern_cache_size: int = 100  # compiled pattern cache
    pattern_timeout_seconds: float = 1.0  # pattern execution timeout
    
    # Batch invalidation settings
    batch_size: int = 1000
    batch_timeout_seconds: float = 5.0
    batch_max_wait_seconds: float = 30.0
    enable_batch_compression: bool = True
    
    # Time-based invalidation settings
    scheduler_type: SchedulerType = SchedulerType.MEMORY
    scheduler_check_interval: timedelta = field(default_factory=lambda: timedelta(seconds=1))
    max_scheduled_operations: int = 10000
    scheduler_persistence_enabled: bool = False
    cleanup_expired_schedules_interval: timedelta = field(default_factory=lambda: timedelta(hours=1))
    
    # Event-driven invalidation settings
    event_queue_size: int = 10000
    event_processing_workers: int = 2
    event_batch_size: int = 100
    event_timeout_seconds: float = 10.0
    enable_event_deduplication: bool = True
    event_dedup_window_seconds: int = 60
    
    # Dependency tracking settings
    enable_dependency_tracking: bool = True
    max_dependency_depth: int = 5
    dependency_cache_size: int = 1000
    circular_dependency_detection: bool = True
    
    # Performance settings
    enable_parallel_invalidation: bool = True
    max_parallel_workers: int = 4
    invalidation_timeout_seconds: float = 30.0
    retry_failed_invalidations: bool = True
    max_invalidation_retries: int = 3
    retry_backoff_seconds: float = 1.0
    
    # Monitoring settings
    enable_invalidation_metrics: bool = True
    track_invalidation_reasons: bool = True
    metrics_aggregation_interval: int = 60  # seconds
    enable_performance_tracking: bool = True
    
    # Safety settings
    max_keys_per_invalidation: int = 100000
    enable_invalidation_rate_limiting: bool = True
    rate_limit_per_second: int = 1000
    enable_dry_run_mode: bool = False
    
    # Redis scheduler settings (when scheduler_type=redis)
    redis_scheduler_key_prefix: str = "neo:cache:scheduler"
    redis_scheduler_db: int = 1  # separate from cache db
    redis_scheduler_connection_pool_size: int = 5
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        self._validate_configuration()
        self._set_defaults()
    
    def _validate_configuration(self):
        """Validate invalidation configuration."""
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        
        if self.max_scheduled_operations <= 0:
            raise ValueError("max_scheduled_operations must be positive")
        
        if self.event_queue_size <= 0:
            raise ValueError("event_queue_size must be positive")
        
        if self.event_processing_workers <= 0:
            raise ValueError("event_processing_workers must be positive")
        
        if self.max_parallel_workers <= 0:
            raise ValueError("max_parallel_workers must be positive")
        
        if self.max_dependency_depth <= 0:
            raise ValueError("max_dependency_depth must be positive")
        
        if self.pattern_timeout_seconds <= 0:
            raise ValueError("pattern_timeout_seconds must be positive")
        
        if self.rate_limit_per_second <= 0:
            raise ValueError("rate_limit_per_second must be positive")
    
    def _set_defaults(self):
        """Set default values for optional fields."""
        if not self.supported_pattern_types:
            self.supported_pattern_types = [
                PatternType.WILDCARD, PatternType.REGEX, PatternType.LITERAL
            ]
    
    def get_pattern_config(self) -> Dict[str, Any]:
        """Get pattern invalidation configuration.
        
        Returns:
            Pattern invalidation configuration
        """
        return {
            "enabled": self.enable_pattern_invalidation,
            "supported_types": [pt.value for pt in self.supported_pattern_types],
            "max_complexity": self.max_pattern_complexity,
            "cache_size": self.pattern_cache_size,
            "timeout_seconds": self.pattern_timeout_seconds
        }
    
    def get_batch_config(self) -> Dict[str, Any]:
        """Get batch invalidation configuration.
        
        Returns:
            Batch invalidation configuration
        """
        return {
            "size": self.batch_size,
            "timeout_seconds": self.batch_timeout_seconds,
            "max_wait_seconds": self.batch_max_wait_seconds,
            "enable_compression": self.enable_batch_compression
        }
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """Get scheduler configuration.
        
        Returns:
            Scheduler configuration
        """
        config = {
            "enabled": self.enable_time_invalidation,
            "type": self.scheduler_type.value,
            "check_interval_seconds": self.scheduler_check_interval.total_seconds(),
            "max_operations": self.max_scheduled_operations,
            "persistence_enabled": self.scheduler_persistence_enabled,
            "cleanup_interval_seconds": self.cleanup_expired_schedules_interval.total_seconds()
        }
        
        # Redis-specific settings
        if self.scheduler_type == SchedulerType.REDIS:
            config.update({
                "redis_key_prefix": self.redis_scheduler_key_prefix,
                "redis_db": self.redis_scheduler_db,
                "redis_pool_size": self.redis_scheduler_connection_pool_size
            })
        
        return config
    
    def get_event_config(self) -> Dict[str, Any]:
        """Get event-driven invalidation configuration.
        
        Returns:
            Event invalidation configuration
        """
        return {
            "enabled": self.enable_event_invalidation,
            "queue_size": self.event_queue_size,
            "processing_workers": self.event_processing_workers,
            "batch_size": self.event_batch_size,
            "timeout_seconds": self.event_timeout_seconds,
            "enable_deduplication": self.enable_event_deduplication,
            "dedup_window_seconds": self.event_dedup_window_seconds
        }
    
    def get_dependency_config(self) -> Dict[str, Any]:
        """Get dependency tracking configuration.
        
        Returns:
            Dependency tracking configuration
        """
        return {
            "enabled": self.enable_dependency_tracking,
            "max_depth": self.max_dependency_depth,
            "cache_size": self.dependency_cache_size,
            "circular_detection": self.circular_dependency_detection
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration.
        
        Returns:
            Performance configuration
        """
        return {
            "enable_parallel": self.enable_parallel_invalidation,
            "max_workers": self.max_parallel_workers,
            "timeout_seconds": self.invalidation_timeout_seconds,
            "retry_failed": self.retry_failed_invalidations,
            "max_retries": self.max_invalidation_retries,
            "retry_backoff_seconds": self.retry_backoff_seconds
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration.
        
        Returns:
            Monitoring configuration
        """
        return {
            "enable_metrics": self.enable_invalidation_metrics,
            "track_reasons": self.track_invalidation_reasons,
            "aggregation_interval": self.metrics_aggregation_interval,
            "enable_performance_tracking": self.enable_performance_tracking
        }
    
    def get_safety_config(self) -> Dict[str, Any]:
        """Get safety configuration.
        
        Returns:
            Safety configuration
        """
        return {
            "max_keys_per_operation": self.max_keys_per_invalidation,
            "enable_rate_limiting": self.enable_invalidation_rate_limiting,
            "rate_limit_per_second": self.rate_limit_per_second,
            "enable_dry_run": self.enable_dry_run_mode
        }
    
    def is_pattern_type_supported(self, pattern_type: PatternType) -> bool:
        """Check if pattern type is supported.
        
        Args:
            pattern_type: Pattern type to check
            
        Returns:
            True if pattern type is supported
        """
        return pattern_type in self.supported_pattern_types
    
    def get_strategy_config(self, strategy: InvalidationStrategy) -> Dict[str, Any]:
        """Get configuration for specific invalidation strategy.
        
        Args:
            strategy: Invalidation strategy
            
        Returns:
            Strategy-specific configuration
        """
        if strategy == InvalidationStrategy.IMMEDIATE:
            return {"enabled": True}
        elif strategy == InvalidationStrategy.BATCHED:
            return self.get_batch_config()
        elif strategy == InvalidationStrategy.SCHEDULED:
            return self.get_scheduler_config()
        elif strategy == InvalidationStrategy.EVENT_DRIVEN:
            return self.get_event_config()
        else:
            raise ValueError(f"Unsupported invalidation strategy: {strategy}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        config_dict = {}
        
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, Enum):
                config_dict[field_name] = field_value.value
            elif isinstance(field_value, list) and field_value and isinstance(field_value[0], Enum):
                config_dict[field_name] = [item.value for item in field_value]
            elif isinstance(field_value, timedelta):
                config_dict[field_name] = field_value.total_seconds()
            else:
                config_dict[field_name] = field_value
        
        return config_dict
    
    def __str__(self) -> str:
        """String representation of configuration."""
        enabled_strategies = []
        if self.enable_pattern_invalidation:
            enabled_strategies.append("pattern")
        if self.enable_time_invalidation:
            enabled_strategies.append("time")
        if self.enable_event_invalidation:
            enabled_strategies.append("event")
        
        return f"InvalidationConfig(strategies={','.join(enabled_strategies)})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"InvalidationConfig(default={self.default_strategy.value}, "
                f"batch_size={self.batch_size}, "
                f"scheduler={self.scheduler_type.value})")


def create_invalidation_config(
    strategy: str = "immediate",
    overrides: Optional[Dict[str, Any]] = None
) -> InvalidationConfig:
    """Factory function to create invalidation configuration.
    
    Args:
        strategy: Default invalidation strategy
        overrides: Optional configuration overrides
        
    Returns:
        Configured invalidation configuration instance
    """
    config_data = {
        "default_strategy": InvalidationStrategy(strategy)
    }
    
    if overrides:
        # Handle enum conversions in overrides
        if "supported_pattern_types" in overrides:
            overrides["supported_pattern_types"] = [
                PatternType(pt) if isinstance(pt, str) else pt
                for pt in overrides["supported_pattern_types"]
            ]
        
        if "scheduler_type" in overrides:
            overrides["scheduler_type"] = SchedulerType(overrides["scheduler_type"])
        
        # Handle timedelta conversions
        if "scheduler_check_interval" in overrides:
            val = overrides["scheduler_check_interval"]
            if isinstance(val, (int, float)):
                overrides["scheduler_check_interval"] = timedelta(seconds=val)
        
        if "cleanup_expired_schedules_interval" in overrides:
            val = overrides["cleanup_expired_schedules_interval"]
            if isinstance(val, (int, float)):
                overrides["cleanup_expired_schedules_interval"] = timedelta(seconds=val)
        
        config_data.update(overrides)
    
    return InvalidationConfig(**config_data)