"""Application protocols for neo-commons.

This module defines protocols for application-level contracts and interfaces.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, Union
from abc import abstractmethod
from enum import Enum


@runtime_checkable
class ConfigurationProtocol(Protocol):
    """Protocol for configuration management."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        ...
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        ...
    
    @abstractmethod
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get configuration section."""
        ...


@runtime_checkable
class EventPublisherProtocol(Protocol):
    """Protocol for event publishing."""
    
    @abstractmethod
    async def publish(
        self, 
        event_type: str, 
        data: Dict[str, Any], 
        tenant_id: Optional[str] = None
    ) -> None:
        """Publish event."""
        ...


@runtime_checkable
class EventHandlerProtocol(Protocol):
    """Protocol for event handling."""
    
    @abstractmethod
    async def handle(self, event_type: str, data: Dict[str, Any]) -> None:
        """Handle event."""
        ...


@runtime_checkable
class ValidationProtocol(Protocol):
    """Protocol for input validation."""
    
    @abstractmethod
    def validate(self, data: Any, schema: Any) -> Dict[str, Any]:
        """Validate data against schema."""
        ...
    
    @abstractmethod
    def sanitize(self, data: str) -> str:
        """Sanitize input data."""
        ...


@runtime_checkable
class EncryptionProtocol(Protocol):
    """Protocol for encryption/decryption operations."""
    
    @abstractmethod
    async def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext."""
        ...
    
    @abstractmethod
    async def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext."""
        ...
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash password."""
        ...
    
    @abstractmethod
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        ...


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@runtime_checkable
class LoggingProtocol(Protocol):
    """Protocol for structured logging."""
    
    @abstractmethod
    def log(
        self, 
        level: LogLevel, 
        message: str, 
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log a message with structured data.
        
        Args:
            level: Log level
            message: Log message
            extra: Additional structured data
            **kwargs: Additional keyword arguments for context
        """
        ...
    
    @abstractmethod
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        ...
    
    @abstractmethod
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        ...
    
    @abstractmethod
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        ...
    
    @abstractmethod
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        ...
    
    @abstractmethod
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        ...
    
    @abstractmethod
    def set_context(self, **context: Any) -> None:
        """Set logging context for all subsequent logs."""
        ...
    
    @abstractmethod
    def clear_context(self) -> None:
        """Clear logging context."""
        ...


class MetricType(Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"  
    HISTOGRAM = "histogram"
    TIMER = "timer"


@runtime_checkable
class MetricsProtocol(Protocol):
    """Protocol for application metrics collection."""
    
    @abstractmethod
    def counter(self, name: str, value: Union[int, float] = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric.
        
        Args:
            name: Metric name
            value: Value to increment by (default: 1)
            tags: Optional tags/labels for the metric
        """
        ...
    
    @abstractmethod
    def gauge(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value.
        
        Args:
            name: Metric name
            value: Gauge value to set
            tags: Optional tags/labels for the metric
        """
        ...
    
    @abstractmethod
    def histogram(self, name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value.
        
        Args:
            name: Metric name
            value: Value to record
            tags: Optional tags/labels for the metric
        """
        ...
    
    @abstractmethod
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Create a timer context manager for measuring duration.
        
        Args:
            name: Timer name
            tags: Optional tags/labels for the metric
            
        Returns:
            Context manager that measures execution time
        """
        ...
    
    @abstractmethod
    def timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a timing metric.
        
        Args:
            name: Timer name
            duration: Duration in seconds
            tags: Optional tags/labels for the metric
        """
        ...
    
    @abstractmethod
    def set_global_tags(self, tags: Dict[str, str]) -> None:
        """Set global tags that apply to all metrics."""
        ...


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@runtime_checkable
class MonitoringProtocol(Protocol):
    """Protocol for application monitoring and health checks."""
    
    @abstractmethod
    async def health_check(self, component: str) -> Dict[str, Any]:
        """Perform health check for a component.
        
        Args:
            component: Component name to check
            
        Returns:
            Health check result with status, details, and metadata
        """
        ...
    
    @abstractmethod
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status.
        
        Returns:
            System health summary with component statuses
        """
        ...
    
    @abstractmethod
    def register_health_check(
        self, 
        name: str, 
        check_func: callable, 
        interval: Optional[float] = None,
        timeout: Optional[float] = None
    ) -> None:
        """Register a health check function.
        
        Args:
            name: Health check name
            check_func: Function that returns health status
            interval: Check interval in seconds (optional)
            timeout: Check timeout in seconds (optional)
        """
        ...
    
    @abstractmethod
    def unregister_health_check(self, name: str) -> None:
        """Unregister a health check."""
        ...
    
    @abstractmethod
    async def alert(
        self, 
        severity: str, 
        message: str, 
        component: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send an alert/notification.
        
        Args:
            severity: Alert severity (critical, warning, info)
            message: Alert message
            component: Component that triggered the alert
            metadata: Additional alert metadata
        """
        ...
    
    @abstractmethod
    async def get_performance_metrics(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics for monitoring.
        
        Args:
            component: Optional component to filter metrics
            
        Returns:
            Performance metrics data
        """
        ...
    
    @abstractmethod
    def start_monitoring(self) -> None:
        """Start monitoring services."""
        ...
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """Stop monitoring services."""
        ...