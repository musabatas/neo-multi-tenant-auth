"""Cache hit handler.

ONLY hit handling - handles cache hit events for performance monitoring,
metrics collection, and access pattern analysis.

Following maximum separation architecture - one file = one purpose.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Protocol, runtime_checkable
from datetime import datetime

from ...core.events.cache_hit import CacheHit


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol for metrics collection."""
    
    async def record_cache_hit(
        self, 
        namespace: str, 
        lookup_time_ms: float,
        value_size_bytes: int
    ) -> None:
        """Record cache hit metrics."""
        ...


@runtime_checkable
class AlertingService(Protocol):
    """Protocol for alerting service."""
    
    async def send_performance_alert(
        self,
        alert_type: str,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """Send performance alert."""
        ...


@dataclass
class CacheHitHandlerResult:
    """Result of cache hit handling."""
    
    success: bool
    metrics_recorded: bool = False
    alerts_sent: int = 0
    error_message: Optional[str] = None


class CacheHitHandler:
    """Cache hit event handler with performance monitoring and alerting.
    
    Handles cache hit events by:
    - Recording performance metrics (hit rate, response times, value sizes)
    - Analyzing access patterns and trends
    - Triggering alerts for performance anomalies
    - Updating cache effectiveness statistics
    - Identifying optimization opportunities
    """
    
    # Performance thresholds
    SLOW_HIT_THRESHOLD_MS = 10.0      # Slow cache hit threshold
    LARGE_VALUE_THRESHOLD = 1024 * 1024  # 1MB threshold for large values
    HIGH_ACCESS_THRESHOLD = 100       # High access count threshold
    
    def __init__(
        self,
        metrics_collector: Optional[MetricsCollector] = None,
        alerting_service: Optional[AlertingService] = None,
        enable_detailed_logging: bool = True,
        enable_performance_alerts: bool = True
    ):
        """Initialize cache hit handler.
        
        Args:
            metrics_collector: Metrics collection service
            alerting_service: Alerting service for performance issues
            enable_detailed_logging: Whether to enable detailed logging
            enable_performance_alerts: Whether to enable performance alerts
        """
        self._metrics_collector = metrics_collector
        self._alerting_service = alerting_service
        self._enable_detailed_logging = enable_detailed_logging
        self._enable_performance_alerts = enable_performance_alerts
        self._logger = logging.getLogger(__name__)
    
    async def handle(self, event: CacheHit) -> CacheHitHandlerResult:
        """Handle cache hit event.
        
        Args:
            event: Cache hit event to handle
            
        Returns:
            Result of hit handling with metrics and alerts
        """
        try:
            result = CacheHitHandlerResult(success=True)
            
            # Record basic metrics
            if self._metrics_collector:
                await self._record_hit_metrics(event)
                result.metrics_recorded = True
            
            # Log hit details
            if self._enable_detailed_logging:
                self._log_hit_details(event)
            
            # Check for performance issues and alerts
            if self._enable_performance_alerts and self._alerting_service:
                alerts_sent = await self._check_performance_alerts(event)
                result.alerts_sent = alerts_sent
            
            # Analyze access patterns
            await self._analyze_access_pattern(event)
            
            return result
            
        except Exception as e:
            self._logger.error(
                f"Failed to handle cache hit event {event.event_id}: {str(e)}",
                extra={
                    "event_id": event.event_id,
                    "cache_key": str(event.key),
                    "namespace": str(event.namespace),
                    "error": str(e)
                }
            )
            
            return CacheHitHandlerResult(
                success=False,
                error_message=str(e)
            )
    
    async def _record_hit_metrics(self, event: CacheHit) -> None:
        """Record cache hit metrics."""
        try:
            await self._metrics_collector.record_cache_hit(
                namespace=str(event.namespace),
                lookup_time_ms=event.lookup_time_ms,
                value_size_bytes=event.value_size_bytes
            )
        except Exception as e:
            self._logger.warning(
                f"Failed to record hit metrics for {event.event_id}: {str(e)}"
            )
    
    def _log_hit_details(self, event: CacheHit) -> None:
        """Log cache hit details."""
        log_context = {
            "event_id": event.event_id,
            "cache_key": str(event.key),
            "namespace": str(event.namespace),
            "lookup_time_ms": event.lookup_time_ms,
            "value_size_bytes": event.value_size_bytes,
            "performance_category": event.get_performance_category(),
            "value_size_category": event.get_value_size_category(),
            "request_id": event.request_id,
            "user_id": event.user_id,
            "tenant_id": event.tenant_id
        }
        
        # Log level based on performance
        if event.is_fast_hit():
            self._logger.debug("Fast cache hit", extra=log_context)
        elif event.lookup_time_ms > self.SLOW_HIT_THRESHOLD_MS:
            self._logger.warning("Slow cache hit detected", extra=log_context)
        else:
            self._logger.info("Cache hit", extra=log_context)
    
    async def _check_performance_alerts(self, event: CacheHit) -> int:
        """Check for performance issues and send alerts."""
        alerts_sent = 0
        
        try:
            # Slow hit alert
            if event.lookup_time_ms > self.SLOW_HIT_THRESHOLD_MS:
                await self._alerting_service.send_performance_alert(
                    alert_type="slow_cache_hit",
                    message=f"Slow cache hit detected: {event.lookup_time_ms:.2f}ms",
                    context={
                        "event_id": event.event_id,
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "lookup_time_ms": event.lookup_time_ms,
                        "threshold_ms": self.SLOW_HIT_THRESHOLD_MS
                    }
                )
                alerts_sent += 1
            
            # Large value alert
            if event.value_size_bytes > self.LARGE_VALUE_THRESHOLD:
                await self._alerting_service.send_performance_alert(
                    alert_type="large_cache_value",
                    message=f"Large cached value detected: {event.value_size_bytes} bytes",
                    context={
                        "event_id": event.event_id,
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "value_size_bytes": event.value_size_bytes,
                        "threshold_bytes": self.LARGE_VALUE_THRESHOLD
                    }
                )
                alerts_sent += 1
            
            # Expiring soon alert (if applicable)
            if event.is_expiring_soon():
                await self._alerting_service.send_performance_alert(
                    alert_type="cache_expiring_soon",
                    message="Frequently accessed cache entry expiring soon",
                    context={
                        "event_id": event.event_id,
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "ttl_remaining_seconds": event.ttl_remaining_seconds,
                        "access_count": event.access_count
                    }
                )
                alerts_sent += 1
                
        except Exception as e:
            self._logger.error(f"Failed to send performance alerts: {str(e)}")
        
        return alerts_sent
    
    async def _analyze_access_pattern(self, event: CacheHit) -> None:
        """Analyze access patterns for optimization opportunities."""
        try:
            # Log frequently accessed entries for warming consideration
            if event.is_frequently_accessed():
                self._logger.info(
                    "Frequently accessed cache entry detected",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "access_count": event.access_count,
                        "entry_age_seconds": event.entry_age_seconds
                    }
                )
            
            # Log large values for compression consideration
            if event.is_large_value():
                self._logger.info(
                    "Large cache value accessed - consider compression",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "value_size_bytes": event.value_size_bytes,
                        "value_size_category": event.get_value_size_category()
                    }
                )
            
            # Log performance issues for optimization
            performance_category = event.get_performance_category()
            if performance_category in ["acceptable", "slow"]:
                self._logger.warning(
                    f"Suboptimal cache performance: {performance_category}",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "lookup_time_ms": event.lookup_time_ms,
                        "performance_category": performance_category
                    }
                )
                
        except Exception as e:
            self._logger.error(f"Failed to analyze access pattern: {str(e)}")


# Factory function for dependency injection
def create_cache_hit_handler(
    metrics_collector: Optional[MetricsCollector] = None,
    alerting_service: Optional[AlertingService] = None,
    enable_detailed_logging: bool = True,
    enable_performance_alerts: bool = True
) -> CacheHitHandler:
    """Create cache hit handler with configuration.
    
    Args:
        metrics_collector: Metrics collection service
        alerting_service: Alerting service for performance issues
        enable_detailed_logging: Whether to enable detailed logging
        enable_performance_alerts: Whether to enable performance alerts
        
    Returns:
        Configured cache hit handler
    """
    return CacheHitHandler(
        metrics_collector=metrics_collector,
        alerting_service=alerting_service,
        enable_detailed_logging=enable_detailed_logging,
        enable_performance_alerts=enable_performance_alerts
    )