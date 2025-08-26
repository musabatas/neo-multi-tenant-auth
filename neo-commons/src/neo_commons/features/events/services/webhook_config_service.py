"""Webhook configuration service with environment variable support.

Centralizes all webhook-related configuration values with fallback defaults.
Supports environment variable override and runtime configuration changes.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Union
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class WebhookPerformanceConfig:
    """Performance-related configuration for webhook processing."""
    
    # Event processing limits
    default_event_limit: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_DEFAULT_EVENT_LIMIT', '100')))
    max_event_limit: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_EVENT_LIMIT', '1000')))
    
    # Batch processing configuration
    default_batch_size: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_DEFAULT_BATCH_SIZE', '10')))
    max_batch_size: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_BATCH_SIZE', '100')))
    optimal_batch_size: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_OPTIMAL_BATCH_SIZE', '20')))
    
    # Concurrency controls
    max_concurrent_batches: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_CONCURRENT_BATCHES', '5')))
    max_concurrent_events: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_CONCURRENT_EVENTS', '20')))
    max_delivery_concurrency: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_DELIVERY_CONCURRENCY', '10')))
    concurrent_workers: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_CONCURRENT_WORKERS', '10')))
    
    # Streaming configuration
    stream_chunk_size: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_STREAM_CHUNK_SIZE', '50')))
    max_stream_chunks: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_STREAM_CHUNKS', '20')))
    
    # Timeout configuration
    event_processing_timeout_seconds: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_EVENT_PROCESSING_TIMEOUT', '30.0')))
    batch_processing_timeout_seconds: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_BATCH_PROCESSING_TIMEOUT', '120.0')))
    delivery_timeout_seconds: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_DELIVERY_TIMEOUT', '15.0')))


@dataclass
class WebhookDatabaseConfig:
    """Database optimization configuration for webhook operations."""
    
    # Query optimization settings
    use_for_update_skip_locked: bool = field(default_factory=lambda: os.getenv('WEBHOOK_USE_FOR_UPDATE_SKIP_LOCKED', 'true').lower() == 'true')
    use_selective_columns: bool = field(default_factory=lambda: os.getenv('WEBHOOK_USE_SELECTIVE_COLUMNS', 'true').lower() == 'true')
    use_index_only_scans: bool = field(default_factory=lambda: os.getenv('WEBHOOK_USE_INDEX_ONLY_SCANS', 'true').lower() == 'true')
    use_bulk_operations: bool = field(default_factory=lambda: os.getenv('WEBHOOK_USE_BULK_OPERATIONS', 'true').lower() == 'true')
    
    # Bulk operation configuration
    bulk_operation_batch_size: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_BULK_OPERATION_BATCH_SIZE', '50')))
    max_bulk_batch_size: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_BULK_BATCH_SIZE', '100')))
    
    # Connection pool settings
    max_connections: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_DB_MAX_CONNECTIONS', '20')))
    connection_timeout_seconds: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_DB_CONNECTION_TIMEOUT', '10.0')))
    
    # Query performance settings
    query_timeout_seconds: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_QUERY_TIMEOUT', '5.0')))
    slow_query_threshold_ms: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_SLOW_QUERY_THRESHOLD_MS', '100.0')))


@dataclass  
class WebhookDeliveryConfig:
    """Webhook delivery and HTTP configuration."""
    
    # HTTP client configuration
    connection_pool_size: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_CONNECTION_POOL_SIZE', '100')))
    connection_pool_size_per_host: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_CONNECTION_POOL_SIZE_PER_HOST', '10')))
    keep_alive_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_KEEP_ALIVE_TIMEOUT', '30')))
    dns_cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_DNS_CACHE_TTL', '300')))
    
    # Retry configuration
    max_retry_attempts: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_RETRY_ATTEMPTS', '3')))
    retry_backoff_seconds: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_RETRY_BACKOFF_SECONDS', '2.0')))
    retry_backoff_multiplier: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_RETRY_BACKOFF_MULTIPLIER', '2.0')))
    max_retry_backoff_seconds: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_MAX_RETRY_BACKOFF', '60.0')))
    
    # Delivery timeouts
    default_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_DEFAULT_TIMEOUT', '30')))
    min_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MIN_TIMEOUT', '5')))
    max_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_TIMEOUT', '300')))
    
    # Delivery validation
    max_payload_size_mb: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_PAYLOAD_SIZE_MB', '10')))
    allowed_response_codes: str = field(default_factory=lambda: os.getenv('WEBHOOK_ALLOWED_RESPONSE_CODES', '200,201,202,204'))


@dataclass
class WebhookValidationConfig:
    """Validation thresholds and constraints configuration.
    
    Provides environment-specific validation bounds for all webhook-related
    validation rules, allowing different constraints for dev, staging, and production.
    """
    
    # URL validation thresholds
    max_url_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_URL_LENGTH', '2048')))
    allowed_protocols: str = field(default_factory=lambda: os.getenv('WEBHOOK_ALLOWED_PROTOCOLS', 'http,https'))
    block_loopback: bool = field(default_factory=lambda: os.getenv('WEBHOOK_BLOCK_LOOPBACK', 'true').lower() == 'true')
    block_private_networks: bool = field(default_factory=lambda: os.getenv('WEBHOOK_BLOCK_PRIVATE_NETWORKS', 'false').lower() == 'true')
    
    # Endpoint validation thresholds
    max_endpoint_name_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_ENDPOINT_NAME_LENGTH', '255')))
    max_description_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_DESCRIPTION_LENGTH', '1000')))
    
    # Secret token validation thresholds
    min_secret_token_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MIN_SECRET_TOKEN_LENGTH', '16')))
    max_secret_token_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_SECRET_TOKEN_LENGTH', '512')))
    
    # Custom headers validation thresholds
    max_custom_headers: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_CUSTOM_HEADERS', '20')))
    max_header_name_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_HEADER_NAME_LENGTH', '100')))
    max_header_value_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_HEADER_VALUE_LENGTH', '1000')))
    
    # Event data validation thresholds
    max_event_data_depth: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_EVENT_DATA_DEPTH', '10')))
    max_event_data_size_kb: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_EVENT_DATA_SIZE_KB', '100')))
    
    # Retry configuration validation bounds
    max_retry_attempts_limit: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_RETRY_ATTEMPTS_LIMIT', '10')))
    min_retry_attempts: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MIN_RETRY_ATTEMPTS', '0')))
    min_backoff_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MIN_BACKOFF_SECONDS', '1')))
    max_backoff_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_BACKOFF_SECONDS', '3600')))
    min_backoff_multiplier: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_MIN_BACKOFF_MULTIPLIER', '1.0')))
    max_backoff_multiplier: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_MAX_BACKOFF_MULTIPLIER', '5.0')))
    
    # Timeout validation bounds
    min_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MIN_TIMEOUT_SECONDS', '5')))
    max_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_TIMEOUT_SECONDS', '300')))
    
    # Aggregate and domain event validation thresholds  
    max_aggregate_type_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_AGGREGATE_TYPE_LENGTH', '100')))
    min_aggregate_version: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MIN_AGGREGATE_VERSION', '1')))
    max_aggregate_version: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_AGGREGATE_VERSION', '999999')))
    
    # Event type validation bounds
    max_event_type_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_EVENT_TYPE_LENGTH', '100')))
    max_event_category_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_EVENT_CATEGORY_LENGTH', '50')))
    max_event_action_length: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_EVENT_ACTION_LENGTH', '50')))
    
    # Performance-related validation thresholds
    max_concurrent_validations: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_CONCURRENT_VALIDATIONS', '100')))
    validation_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_VALIDATION_TIMEOUT_SECONDS', '30')))
    
    # Response validation thresholds
    max_response_size_mb: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_RESPONSE_SIZE_MB', '10')))
    max_response_time_ms: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_RESPONSE_TIME_MS', '30000')))
    
    # Content validation thresholds
    max_payload_size_mb: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_PAYLOAD_SIZE_MB', '5')))
    max_metadata_size_kb: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_MAX_METADATA_SIZE_KB', '50')))
    
    # Environment-specific overrides
    strict_validation_mode: bool = field(default_factory=lambda: os.getenv('WEBHOOK_STRICT_VALIDATION_MODE', 'false').lower() == 'true')
    allow_test_endpoints: bool = field(default_factory=lambda: os.getenv('WEBHOOK_ALLOW_TEST_ENDPOINTS', 'true').lower() == 'true')
    validate_ssl_certificates: bool = field(default_factory=lambda: os.getenv('WEBHOOK_VALIDATE_SSL_CERTIFICATES', 'true').lower() == 'true')
    
    def get_environment_profile(self) -> str:
        """Get the current environment validation profile.
        
        Returns:
            Environment profile: 'development', 'staging', 'production'
        """
        return os.getenv('WEBHOOK_VALIDATION_PROFILE', 'production')
    
    def is_development_environment(self) -> bool:
        """Check if running in development environment with relaxed validation."""
        return self.get_environment_profile() == 'development'
    
    def is_production_environment(self) -> bool:
        """Check if running in production environment with strict validation."""
        return self.get_environment_profile() == 'production'
    
    def get_adjusted_limits_for_environment(self) -> Dict[str, Any]:
        """Get validation limits adjusted for current environment.
        
        Returns:
            Dictionary of adjusted limits based on environment profile
        """
        profile = self.get_environment_profile()
        
        if profile == 'development':
            return {
                'max_retry_attempts_limit': min(self.max_retry_attempts_limit, 3),
                'max_timeout_seconds': min(self.max_timeout_seconds, 60),
                'block_private_networks': False,
                'block_loopback': False,
                'strict_validation_mode': False
            }
        elif profile == 'staging':
            return {
                'max_retry_attempts_limit': min(self.max_retry_attempts_limit, 5),
                'max_timeout_seconds': min(self.max_timeout_seconds, 120),
                'block_private_networks': True,
                'block_loopback': True,
                'strict_validation_mode': True
            }
        else:  # production
            return {
                'max_retry_attempts_limit': self.max_retry_attempts_limit,
                'max_timeout_seconds': self.max_timeout_seconds,
                'block_private_networks': self.block_private_networks,
                'block_loopback': self.block_loopback,
                'strict_validation_mode': self.strict_validation_mode
            }
    
    def validate_configuration(self) -> List[str]:
        """Validate the configuration itself for consistency.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # Check logical constraints
        if self.min_secret_token_length > self.max_secret_token_length:
            warnings.append("min_secret_token_length cannot be greater than max_secret_token_length")
        
        if self.min_timeout_seconds > self.max_timeout_seconds:
            warnings.append("min_timeout_seconds cannot be greater than max_timeout_seconds")
        
        if self.min_backoff_seconds > self.max_backoff_seconds:
            warnings.append("min_backoff_seconds cannot be greater than max_backoff_seconds")
        
        if self.min_backoff_multiplier > self.max_backoff_multiplier:
            warnings.append("min_backoff_multiplier cannot be greater than max_backoff_multiplier")
        
        if self.min_aggregate_version > self.max_aggregate_version:
            warnings.append("min_aggregate_version cannot be greater than max_aggregate_version")
        
        # Check reasonable limits
        if self.max_url_length > 10000:
            warnings.append("max_url_length seems very large (>10KB)")
        
        if self.max_payload_size_mb > 100:
            warnings.append("max_payload_size_mb seems very large (>100MB)")
        
        if self.max_concurrent_validations > 1000:
            warnings.append("max_concurrent_validations seems very high (>1000)")
        
        return warnings


@dataclass
class WebhookMonitoringConfig:
    """Monitoring, metrics, and archival configuration."""
    
    # Metrics collection
    metrics_enabled: bool = field(default_factory=lambda: os.getenv('WEBHOOK_METRICS_ENABLED', 'true').lower() == 'true')
    metrics_collection_interval_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_METRICS_COLLECTION_INTERVAL', '60')))
    metrics_retention_days: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_METRICS_RETENTION_DAYS', '30')))
    
    # Performance monitoring
    latency_percentiles: str = field(default_factory=lambda: os.getenv('WEBHOOK_LATENCY_PERCENTILES', '50,90,95,99'))
    slow_delivery_threshold_ms: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_SLOW_DELIVERY_THRESHOLD_MS', '1000.0')))
    
    # Health check configuration
    health_check_enabled: bool = field(default_factory=lambda: os.getenv('WEBHOOK_HEALTH_CHECK_ENABLED', 'true').lower() == 'true')
    health_check_interval_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_HEALTH_CHECK_INTERVAL', '300')))
    health_check_timeout_seconds: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_HEALTH_CHECK_TIMEOUT', '10')))
    
    # Event archival
    archival_enabled: bool = field(default_factory=lambda: os.getenv('WEBHOOK_ARCHIVAL_ENABLED', 'true').lower() == 'true')
    default_archival_days: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_DEFAULT_ARCHIVAL_DAYS', '90')))
    max_table_size_gb: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_MAX_TABLE_SIZE_GB', '10.0')))
    
    # Alert thresholds for comprehensive business metrics
    success_rate_warning_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_SUCCESS_RATE_WARNING_THRESHOLD', '90.0')))
    success_rate_critical_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_SUCCESS_RATE_CRITICAL_THRESHOLD', '75.0')))
    response_time_warning_threshold_ms: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_RESPONSE_TIME_WARNING_THRESHOLD_MS', '5000.0')))
    response_time_critical_threshold_ms: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_RESPONSE_TIME_CRITICAL_THRESHOLD_MS', '10000.0')))
    consecutive_failures_warning_threshold: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_CONSECUTIVE_FAILURES_WARNING_THRESHOLD', '5')))
    consecutive_failures_critical_threshold: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_CONSECUTIVE_FAILURES_CRITICAL_THRESHOLD', '10')))
    events_per_second_warning_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_EVENTS_PER_SECOND_WARNING_THRESHOLD', '100.0')))
    events_per_second_critical_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_EVENTS_PER_SECOND_CRITICAL_THRESHOLD', '500.0')))
    
    # Business KPI thresholds
    customer_satisfaction_warning_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_CUSTOMER_SATISFACTION_WARNING_THRESHOLD', '85.0')))
    customer_satisfaction_critical_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_CUSTOMER_SATISFACTION_CRITICAL_THRESHOLD', '70.0')))
    sla_compliance_warning_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_SLA_COMPLIANCE_WARNING_THRESHOLD', '95.0')))
    sla_compliance_critical_threshold: float = field(default_factory=lambda: float(os.getenv('WEBHOOK_SLA_COMPLIANCE_CRITICAL_THRESHOLD', '90.0')))
    auto_delete_after_days: int = field(default_factory=lambda: int(os.getenv('WEBHOOK_AUTO_DELETE_AFTER_DAYS', '365')))


@dataclass
class WebhookConfig:
    """Complete webhook configuration with all subsections."""
    
    performance: WebhookPerformanceConfig = field(default_factory=WebhookPerformanceConfig)
    database: WebhookDatabaseConfig = field(default_factory=WebhookDatabaseConfig)
    delivery: WebhookDeliveryConfig = field(default_factory=WebhookDeliveryConfig)
    validation: WebhookValidationConfig = field(default_factory=WebhookValidationConfig)
    monitoring: WebhookMonitoringConfig = field(default_factory=WebhookMonitoringConfig)
    
    # Global settings
    debug_enabled: bool = field(default_factory=lambda: os.getenv('WEBHOOK_DEBUG_ENABLED', 'false').lower() == 'true')
    environment: str = field(default_factory=lambda: os.getenv('WEBHOOK_ENVIRONMENT', 'development'))


class WebhookConfigService:
    """Service for managing webhook configuration with caching and environment variable support."""
    
    def __init__(self):
        self._config: Optional[WebhookConfig] = None
        self._config_cache_ttl_seconds = int(os.getenv('WEBHOOK_CONFIG_CACHE_TTL', '300'))  # 5 minutes
        
    @lru_cache(maxsize=1)
    def get_config(self) -> WebhookConfig:
        """Get the current webhook configuration with caching.
        
        Returns:
            WebhookConfig: Complete configuration object
        """
        if self._config is None:
            self._config = self._load_config()
            logger.info("Loaded webhook configuration from environment variables")
        return self._config
    
    def _load_config(self) -> WebhookConfig:
        """Load configuration from environment variables and defaults.
        
        Returns:
            WebhookConfig: Fully initialized configuration
        """
        try:
            config = WebhookConfig()
            
            # Validate critical configuration values
            self._validate_config(config)
            
            if config.debug_enabled:
                logger.debug(f"Webhook configuration loaded for environment: {config.environment}")
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading webhook configuration: {e}")
            # Return default configuration on error
            return WebhookConfig()
    
    def _validate_config(self, config: WebhookConfig) -> None:
        """Validate configuration values for consistency and safety.
        
        Args:
            config: Configuration to validate
            
        Raises:
            ValueError: If configuration values are invalid
        """
        # Performance validation
        if config.performance.max_event_limit < config.performance.default_event_limit:
            raise ValueError("max_event_limit must be >= default_event_limit")
            
        if config.performance.max_batch_size < config.performance.default_batch_size:
            raise ValueError("max_batch_size must be >= default_batch_size")
            
        if config.performance.max_concurrent_batches < 1:
            raise ValueError("max_concurrent_batches must be >= 1")
        
        # Database validation
        if config.database.bulk_operation_batch_size > config.database.max_bulk_batch_size:
            raise ValueError("bulk_operation_batch_size must be <= max_bulk_batch_size")
            
        if config.database.connection_timeout_seconds <= 0:
            raise ValueError("connection_timeout_seconds must be > 0")
        
        # Delivery validation
        if config.delivery.min_timeout_seconds > config.delivery.max_timeout_seconds:
            raise ValueError("min_timeout_seconds must be <= max_timeout_seconds")
            
        if config.delivery.max_retry_attempts < 0:
            raise ValueError("max_retry_attempts must be >= 0")
        
        # Validation constraints
        if config.validation.min_secret_token_length > config.validation.max_secret_token_length:
            raise ValueError("min_secret_token_length must be <= max_secret_token_length")
    
    def reload_config(self) -> WebhookConfig:
        """Force reload configuration from environment variables.
        
        Returns:
            WebhookConfig: Newly loaded configuration
        """
        self.get_config.cache_clear()  # Clear LRU cache
        self._config = None
        logger.info("Webhook configuration cache cleared, reloading from environment")
        return self.get_config()
    
    def get_performance_config(self) -> WebhookPerformanceConfig:
        """Get performance-specific configuration.
        
        Returns:
            WebhookPerformanceConfig: Performance settings
        """
        return self.get_config().performance
    
    def get_database_config(self) -> WebhookDatabaseConfig:
        """Get database-specific configuration.
        
        Returns:
            WebhookDatabaseConfig: Database settings
        """
        return self.get_config().database
    
    def get_delivery_config(self) -> WebhookDeliveryConfig:
        """Get delivery-specific configuration.
        
        Returns:
            WebhookDeliveryConfig: Delivery settings
        """
        return self.get_config().delivery
    
    def get_validation_config(self) -> WebhookValidationConfig:
        """Get validation-specific configuration.
        
        Returns:
            WebhookValidationConfig: Validation settings
        """
        return self.get_config().validation
    
    def get_monitoring_config(self) -> WebhookMonitoringConfig:
        """Get monitoring-specific configuration.
        
        Returns:
            WebhookMonitoringConfig: Monitoring settings
        """
        return self.get_config().monitoring
    
    def update_runtime_config(self, **kwargs) -> None:
        """Update configuration values at runtime.
        
        Args:
            **kwargs: Configuration values to update
            
        Note:
            This updates the in-memory configuration only.
            Environment variables are not modified.
        """
        if self._config is None:
            self._config = self.get_config()
            
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
                logger.info(f"Updated runtime config: {key} = {value}")
            else:
                logger.warning(f"Unknown configuration key: {key}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration for debugging.
        
        Returns:
            Dict[str, Any]: Configuration summary
        """
        config = self.get_config()
        
        return {
            "environment": config.environment,
            "debug_enabled": config.debug_enabled,
            "performance": {
                "default_event_limit": config.performance.default_event_limit,
                "default_batch_size": config.performance.default_batch_size,
                "max_concurrent_batches": config.performance.max_concurrent_batches,
                "concurrent_workers": config.performance.concurrent_workers
            },
            "database": {
                "use_optimizations": config.database.use_for_update_skip_locked,
                "bulk_batch_size": config.database.bulk_operation_batch_size,
                "max_connections": config.database.max_connections
            },
            "delivery": {
                "connection_pool_size": config.delivery.connection_pool_size,
                "max_retry_attempts": config.delivery.max_retry_attempts,
                "default_timeout": config.delivery.default_timeout_seconds
            },
            "monitoring": {
                "metrics_enabled": config.monitoring.metrics_enabled,
                "archival_enabled": config.monitoring.archival_enabled,
                "health_checks_enabled": config.monitoring.health_check_enabled
            }
        }


# Global configuration service instance
_webhook_config_service: Optional[WebhookConfigService] = None

def get_webhook_config_service() -> WebhookConfigService:
    """Get the global webhook configuration service instance.
    
    Returns:
        WebhookConfigService: Singleton configuration service
    """
    global _webhook_config_service
    if _webhook_config_service is None:
        _webhook_config_service = WebhookConfigService()
    return _webhook_config_service

def get_webhook_config() -> WebhookConfig:
    """Get the current webhook configuration.
    
    Returns:
        WebhookConfig: Current configuration
    """
    return get_webhook_config_service().get_config()