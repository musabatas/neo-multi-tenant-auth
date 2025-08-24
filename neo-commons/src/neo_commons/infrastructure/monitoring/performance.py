"""Performance monitoring decorators and utilities.

This module provides decorators for monitoring bottlenecks and measuring
execution times across critical operations in the neo-commons library.
"""

import time
import asyncio
import functools
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from ...core.shared.application import ConfigurationProtocol


class PerformanceLevel(Enum):
    """Performance monitoring levels."""
    CRITICAL = "critical"      # Database operations, external API calls
    HIGH = "high"             # Business logic, complex computations
    MEDIUM = "medium"         # Service methods, validation
    LOW = "low"               # Utility functions, simple operations


class AlertThreshold(Enum):
    """Performance alert thresholds in milliseconds."""
    CRITICAL = 1000    # 1 second - database operations
    HIGH = 500         # 500ms - API calls
    MEDIUM = 100       # 100ms - business logic
    LOW = 50           # 50ms - utility functions


@dataclass
class PerformanceMetric:
    """Performance measurement data."""
    
    operation_name: str
    execution_time_ms: float
    level: PerformanceLevel
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    exceeded_threshold: bool = False
    error_occurred: bool = False


@dataclass 
class PerformanceStats:
    """Aggregated performance statistics."""
    
    operation_name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    threshold_violations: int = 0
    error_count: int = 0
    
    def update(self, metric: PerformanceMetric) -> None:
        """Update statistics with new metric."""
        self.call_count += 1
        self.total_time_ms += metric.execution_time_ms
        self.avg_time_ms = self.total_time_ms / self.call_count
        self.min_time_ms = min(self.min_time_ms, metric.execution_time_ms)
        self.max_time_ms = max(self.max_time_ms, metric.execution_time_ms)
        
        if metric.exceeded_threshold:
            self.threshold_violations += 1
        if metric.error_occurred:
            self.error_count += 1


class PerformanceMonitor:
    """Central performance monitoring system."""
    
    def __init__(self, 
                 config: Optional[ConfigurationProtocol] = None,
                 persistence_storage: Optional['PerformanceStorage'] = None):
        """Initialize performance monitor."""
        self._config = config
        self._metrics: List[PerformanceMetric] = []
        self._stats: Dict[str, PerformanceStats] = {}
        self._logger = logging.getLogger(f"{__name__}.PerformanceMonitor")
        self._enabled = True
        
        # Optional database persistence (zero performance impact)
        self._persistence_storage = persistence_storage
        self._background_persister: Optional['BackgroundMetricsPersister'] = None
        
        if self._persistence_storage:
            from .persistence import BackgroundMetricsPersister
            self._background_persister = BackgroundMetricsPersister(self._persistence_storage)
            self._background_persister.start()
        
    def is_enabled(self) -> bool:
        """Check if performance monitoring is enabled."""
        if self._config:
            return self._config.get("performance_monitoring.enabled", True)
        return self._enabled
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable performance monitoring."""
        self._enabled = enabled
    
    def get_threshold(self, level: PerformanceLevel) -> float:
        """Get threshold for performance level."""
        if self._config:
            key = f"performance_monitoring.threshold.{level.value}"
            return float(self._config.get(key, AlertThreshold[level.name].value))
        return AlertThreshold[level.name].value
    
    def record_metric(self, metric: PerformanceMetric) -> None:
        """Record a performance metric."""
        if not self.is_enabled():
            return
            
        # Check threshold violation
        threshold = self.get_threshold(metric.level)
        metric.exceeded_threshold = metric.execution_time_ms > threshold
        
        # Store metric in memory
        self._metrics.append(metric)
        
        # Update statistics
        if metric.operation_name not in self._stats:
            self._stats[metric.operation_name] = PerformanceStats(metric.operation_name)
        self._stats[metric.operation_name].update(metric)
        
        # Queue for background persistence (zero performance impact)
        if self._background_persister:
            self._background_persister.queue_metric(metric)
            self._background_persister.queue_stats(self._stats)
        
        # Log threshold violations
        if metric.exceeded_threshold:
            self._logger.warning(
                f"Performance threshold exceeded for {metric.operation_name}: "
                f"{metric.execution_time_ms:.2f}ms > {threshold}ms"
            )
        
        # Log critical performance issues
        if metric.level == PerformanceLevel.CRITICAL and metric.execution_time_ms > 5000:
            self._logger.error(
                f"Critical performance issue in {metric.operation_name}: "
                f"{metric.execution_time_ms:.2f}ms"
            )
    
    def get_stats(self, operation_name: Optional[str] = None) -> Union[PerformanceStats, Dict[str, PerformanceStats]]:
        """Get performance statistics."""
        if operation_name:
            return self._stats.get(operation_name, PerformanceStats(operation_name))
        return self._stats.copy()
    
    def get_metrics(self, operation_name: Optional[str] = None, limit: int = 100) -> List[PerformanceMetric]:
        """Get recent performance metrics."""
        metrics = self._metrics
        if operation_name:
            metrics = [m for m in metrics if m.operation_name == operation_name]
        return metrics[-limit:]
    
    def get_bottlenecks(self, threshold_multiplier: float = 2.0) -> List[PerformanceStats]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        for stats in self._stats.values():
            if stats.call_count > 0:
                expected_threshold = self.get_threshold(PerformanceLevel.MEDIUM)
                if stats.avg_time_ms > expected_threshold * threshold_multiplier:
                    bottlenecks.append(stats)
        
        # Sort by average execution time
        return sorted(bottlenecks, key=lambda s: s.avg_time_ms, reverse=True)
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics and statistics."""
        self._metrics.clear()
        self._stats.clear()
    
    async def shutdown(self) -> None:
        """Shutdown performance monitor and flush remaining metrics."""
        if self._background_persister:
            await self._background_persister.stop()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance monitoring summary."""
        total_operations = len(self._stats)
        total_calls = sum(s.call_count for s in self._stats.values())
        total_violations = sum(s.threshold_violations for s in self._stats.values())
        total_errors = sum(s.error_count for s in self._stats.values())
        
        return {
            "enabled": self.is_enabled(),
            "total_operations": total_operations,
            "total_calls": total_calls,
            "threshold_violations": total_violations,
            "error_count": total_errors,
            "bottlenecks": len(self.get_bottlenecks()),
            "metrics_stored": len(self._metrics),
            "persistence_enabled": self._persistence_storage is not None,
        }


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def set_performance_monitor(monitor: PerformanceMonitor) -> None:
    """Set custom performance monitor for testing."""
    global _performance_monitor
    _performance_monitor = monitor


# Performance decorators

F = TypeVar('F', bound=Callable[..., Any])


def performance_monitor(
    name: Optional[str] = None,
    level: PerformanceLevel = PerformanceLevel.MEDIUM,
    include_args: bool = False,
    monitor: Optional[PerformanceMonitor] = None
) -> Callable[[F], F]:
    """Decorator to monitor function performance.
    
    Args:
        name: Custom operation name (defaults to function name)
        level: Performance monitoring level
        include_args: Whether to include function arguments in metadata
        monitor: Custom performance monitor instance
        
    Returns:
        Decorated function with performance monitoring
    """
    def decorator(func: F) -> F:
        operation_name = name or f"{func.__module__}.{func.__qualname__}"
        perf_monitor = monitor or get_performance_monitor()
        
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if not perf_monitor.is_enabled():
                    return await func(*args, **kwargs)
                
                start_time = time.perf_counter()
                error_occurred = False
                metadata = {}
                
                if include_args:
                    metadata["args_count"] = len(args)
                    metadata["kwargs_keys"] = list(kwargs.keys())
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    metadata["error_type"] = type(e).__name__
                    metadata["error_message"] = str(e)
                    raise
                finally:
                    end_time = time.perf_counter()
                    execution_time_ms = (end_time - start_time) * 1000
                    
                    metric = PerformanceMetric(
                        operation_name=operation_name,
                        execution_time_ms=execution_time_ms,
                        level=level,
                        metadata=metadata,
                        error_occurred=error_occurred
                    )
                    perf_monitor.record_metric(metric)
            
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if not perf_monitor.is_enabled():
                    return func(*args, **kwargs)
                
                start_time = time.perf_counter()
                error_occurred = False
                metadata = {}
                
                if include_args:
                    metadata["args_count"] = len(args)
                    metadata["kwargs_keys"] = list(kwargs.keys())
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_occurred = True
                    metadata["error_type"] = type(e).__name__
                    metadata["error_message"] = str(e)
                    raise
                finally:
                    end_time = time.perf_counter()
                    execution_time_ms = (end_time - start_time) * 1000
                    
                    metric = PerformanceMetric(
                        operation_name=operation_name,
                        execution_time_ms=execution_time_ms,
                        level=level,
                        metadata=metadata,
                        error_occurred=error_occurred
                    )
                    perf_monitor.record_metric(metric)
            
            return sync_wrapper
    
    return decorator


# Convenience decorators for different performance levels

def critical_performance(name: Optional[str] = None, include_args: bool = False):
    """Decorator for critical performance monitoring (database, external APIs)."""
    return performance_monitor(name=name, level=PerformanceLevel.CRITICAL, include_args=include_args)


def high_performance(name: Optional[str] = None, include_args: bool = False):
    """Decorator for high performance monitoring (business logic)."""
    return performance_monitor(name=name, level=PerformanceLevel.HIGH, include_args=include_args)


def medium_performance(name: Optional[str] = None, include_args: bool = False):
    """Decorator for medium performance monitoring (service methods)."""
    return performance_monitor(name=name, level=PerformanceLevel.MEDIUM, include_args=include_args)


def low_performance(name: Optional[str] = None, include_args: bool = False):
    """Decorator for low performance monitoring (utility functions)."""
    return performance_monitor(name=name, level=PerformanceLevel.LOW, include_args=include_args)


# Context manager for timing code blocks

class performance_timer:
    """Context manager for timing code blocks."""
    
    def __init__(
        self, 
        operation_name: str,
        level: PerformanceLevel = PerformanceLevel.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        monitor: Optional[PerformanceMonitor] = None
    ):
        """Initialize performance timer.
        
        Args:
            operation_name: Name of the operation being timed
            level: Performance monitoring level
            metadata: Additional metadata to include
            monitor: Custom performance monitor instance
        """
        self.operation_name = operation_name
        self.level = level
        self.metadata = metadata or {}
        self.monitor = monitor or get_performance_monitor()
        self.start_time = 0.0
        self.error_occurred = False
    
    def __enter__(self):
        """Start timing."""
        if self.monitor.is_enabled():
            self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and record metric."""
        if not self.monitor.is_enabled():
            return
        
        end_time = time.perf_counter()
        execution_time_ms = (end_time - self.start_time) * 1000
        
        if exc_type is not None:
            self.error_occurred = True
            self.metadata.update({
                "error_type": exc_type.__name__,
                "error_message": str(exc_val),
                "has_traceback": exc_tb is not None
            })
        
        metric = PerformanceMetric(
            operation_name=self.operation_name,
            execution_time_ms=execution_time_ms,
            level=self.level,
            metadata=self.metadata,
            error_occurred=self.error_occurred
        )
        self.monitor.record_metric(metric)