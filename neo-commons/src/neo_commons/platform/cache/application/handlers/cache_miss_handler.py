"""Cache miss handler.

ONLY miss handling - handles cache miss events for performance monitoring,
cache effectiveness analysis, and warming opportunities.

Following maximum separation architecture - one file = one purpose.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Protocol, runtime_checkable

from ...core.events.cache_miss import CacheMiss, MissReason


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol for metrics collection."""
    
    async def record_cache_miss(
        self,
        namespace: str,
        reason: str,
        lookup_time_ms: float
    ) -> None:
        """Record cache miss metrics."""
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


@runtime_checkable
class CacheWarmingService(Protocol):
    """Protocol for cache warming service."""
    
    async def schedule_warming(
        self,
        cache_key: str,
        namespace: str,
        priority: str = "normal"
    ) -> None:
        """Schedule cache warming for frequently missed keys."""
        ...


@dataclass
class CacheMissHandlerResult:
    """Result of cache miss handling."""
    
    success: bool
    metrics_recorded: bool = False
    alerts_sent: int = 0
    warming_scheduled: bool = False
    error_message: Optional[str] = None


class CacheMissHandler:
    """Cache miss event handler with analytics and optimization.
    
    Handles cache miss events by:
    - Recording miss metrics and analyzing miss patterns
    - Tracking cache effectiveness and identifying problematic keys
    - Triggering alerts for high miss rates or errors
    - Scheduling cache warming for frequently missed keys
    - Analyzing miss reasons for optimization opportunities
    """
    
    # Performance thresholds
    SLOW_MISS_THRESHOLD_MS = 10.0     # Slow miss lookup threshold
    HIGH_MISS_RATE_THRESHOLD = 0.8    # High miss rate alert threshold
    WARMING_FREQUENCY_THRESHOLD = 5   # Miss frequency for warming consideration
    
    def __init__(
        self,
        metrics_collector: Optional[MetricsCollector] = None,
        alerting_service: Optional[AlertingService] = None,
        warming_service: Optional[CacheWarmingService] = None,
        enable_detailed_logging: bool = True,
        enable_warming_scheduling: bool = True
    ):
        """Initialize cache miss handler.
        
        Args:
            metrics_collector: Metrics collection service
            alerting_service: Alerting service for performance issues
            warming_service: Cache warming service
            enable_detailed_logging: Whether to enable detailed logging
            enable_warming_scheduling: Whether to enable cache warming scheduling
        """
        self._metrics_collector = metrics_collector
        self._alerting_service = alerting_service
        self._warming_service = warming_service
        self._enable_detailed_logging = enable_detailed_logging
        self._enable_warming_scheduling = enable_warming_scheduling
        self._logger = logging.getLogger(__name__)
    
    async def handle(self, event: CacheMiss) -> CacheMissHandlerResult:
        """Handle cache miss event.
        
        Args:
            event: Cache miss event to handle
            
        Returns:
            Result of miss handling with metrics and actions
        """
        try:
            result = CacheMissHandlerResult(success=True)
            
            # Record miss metrics
            if self._metrics_collector:
                await self._record_miss_metrics(event)
                result.metrics_recorded = True
            
            # Log miss details
            if self._enable_detailed_logging:
                self._log_miss_details(event)
            
            # Check for performance issues and alerts
            if self._alerting_service:
                alerts_sent = await self._check_miss_alerts(event)
                result.alerts_sent = alerts_sent
            
            # Schedule warming if appropriate
            if self._enable_warming_scheduling and self._warming_service:
                warming_scheduled = await self._consider_warming(event)
                result.warming_scheduled = warming_scheduled
            
            # Analyze miss patterns
            await self._analyze_miss_pattern(event)
            
            return result
            
        except Exception as e:
            self._logger.error(
                f"Failed to handle cache miss event {event.event_id}: {str(e)}",
                extra={
                    "event_id": event.event_id,
                    "cache_key": str(event.key),
                    "namespace": str(event.namespace),
                    "miss_reason": event.reason.value,
                    "error": str(e)
                }
            )
            
            return CacheMissHandlerResult(
                success=False,
                error_message=str(e)
            )
    
    async def _record_miss_metrics(self, event: CacheMiss) -> None:
        """Record cache miss metrics."""
        try:
            await self._metrics_collector.record_cache_miss(
                namespace=str(event.namespace),
                reason=event.reason.value,
                lookup_time_ms=event.lookup_time_ms
            )
        except Exception as e:
            self._logger.warning(
                f"Failed to record miss metrics for {event.event_id}: {str(e)}"
            )
    
    def _log_miss_details(self, event: CacheMiss) -> None:
        """Log cache miss details."""
        log_context = {
            "event_id": event.event_id,
            "cache_key": str(event.key),
            "namespace": str(event.namespace),
            "miss_reason": event.reason.value,
            "lookup_time_ms": event.lookup_time_ms,
            "cacheable": event.is_cacheable_miss(),
            "request_id": event.request_id,
            "user_id": event.user_id,
            "tenant_id": event.tenant_id
        }
        
        # Log level based on miss reason and performance
        if event.is_error_miss():
            self._logger.error("Cache miss due to error", extra=log_context)
        elif event.is_slow_miss(self.SLOW_MISS_THRESHOLD_MS):
            self._logger.warning("Slow cache miss detected", extra=log_context)
        elif event.reason == MissReason.NOT_FOUND:
            self._logger.debug("Cache miss - key not found", extra=log_context)
        else:
            self._logger.info(f"Cache miss - {event.reason.value}", extra=log_context)
    
    async def _check_miss_alerts(self, event: CacheMiss) -> int:
        """Check for miss-related issues and send alerts."""
        alerts_sent = 0
        
        try:
            # Error miss alert
            if event.is_error_miss():
                await self._alerting_service.send_performance_alert(
                    alert_type="cache_error",
                    message=f"Cache error during lookup: {event.error_message or 'Unknown error'}",
                    context={
                        "event_id": event.event_id,
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "error_message": event.error_message
                    }
                )
                alerts_sent += 1
            
            # Slow miss alert
            if event.is_slow_miss(self.SLOW_MISS_THRESHOLD_MS):
                await self._alerting_service.send_performance_alert(
                    alert_type="slow_cache_miss",
                    message=f"Slow cache miss detected: {event.lookup_time_ms:.2f}ms",
                    context={
                        "event_id": event.event_id,
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "lookup_time_ms": event.lookup_time_ms,
                        "threshold_ms": self.SLOW_MISS_THRESHOLD_MS,
                        "miss_reason": event.reason.value
                    }
                )
                alerts_sent += 1
                
        except Exception as e:
            self._logger.error(f"Failed to send miss alerts: {str(e)}")
        
        return alerts_sent
    
    async def _consider_warming(self, event: CacheMiss) -> bool:
        """Consider scheduling cache warming based on miss patterns."""
        try:
            # Only warm cacheable misses (not errors)
            if not event.is_cacheable_miss():
                return False
            
            # Schedule warming for expired and evicted entries
            # These were recently cached, so they might be accessed again
            if event.reason in [MissReason.EXPIRED, MissReason.EVICTED]:
                await self._warming_service.schedule_warming(
                    cache_key=str(event.key),
                    namespace=str(event.namespace),
                    priority="high"  # High priority for recently cached items
                )
                
                self._logger.info(
                    f"Scheduled cache warming for {event.reason.value} key",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "miss_reason": event.reason.value
                    }
                )
                return True
            
            # Consider warming for frequently missed NOT_FOUND keys
            # This would require tracking miss frequency, which could be
            # implemented with a separate service
            
        except Exception as e:
            self._logger.error(f"Failed to schedule cache warming: {str(e)}")
        
        return False
    
    async def _analyze_miss_pattern(self, event: CacheMiss) -> None:
        """Analyze miss patterns for optimization insights."""
        try:
            # Log different miss reasons for analysis
            if event.reason == MissReason.EXPIRED:
                self._logger.info(
                    "Cache entry expired - consider TTL optimization",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "miss_reason": event.reason.value
                    }
                )
            
            elif event.reason == MissReason.EVICTED:
                self._logger.warning(
                    "Cache entry evicted - possible memory pressure",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "miss_reason": event.reason.value
                    }
                )
            
            elif event.reason == MissReason.INVALIDATED:
                self._logger.info(
                    "Cache entry invalidated - normal cache management",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "miss_reason": event.reason.value
                    }
                )
            
            elif event.reason == MissReason.NOT_FOUND:
                self._logger.debug(
                    "Cache key not found - new or cold cache",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "miss_reason": event.reason.value
                    }
                )
            
        except Exception as e:
            self._logger.error(f"Failed to analyze miss pattern: {str(e)}")


# Factory function for dependency injection
def create_cache_miss_handler(
    metrics_collector: Optional[MetricsCollector] = None,
    alerting_service: Optional[AlertingService] = None,
    warming_service: Optional[CacheWarmingService] = None,
    enable_detailed_logging: bool = True,
    enable_warming_scheduling: bool = True
) -> CacheMissHandler:
    """Create cache miss handler with configuration.
    
    Args:
        metrics_collector: Metrics collection service
        alerting_service: Alerting service for performance issues  
        warming_service: Cache warming service
        enable_detailed_logging: Whether to enable detailed logging
        enable_warming_scheduling: Whether to enable cache warming scheduling
        
    Returns:
        Configured cache miss handler
    """
    return CacheMissHandler(
        metrics_collector=metrics_collector,
        alerting_service=alerting_service,
        warming_service=warming_service,
        enable_detailed_logging=enable_detailed_logging,
        enable_warming_scheduling=enable_warming_scheduling
    )