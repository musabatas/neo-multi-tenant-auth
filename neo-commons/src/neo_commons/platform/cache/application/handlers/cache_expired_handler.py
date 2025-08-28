"""Cache expired handler.

ONLY expiration handling - handles cache expiration events for TTL analysis,
cache warming triggers, and expiration efficiency monitoring.

Following maximum separation architecture - one file = one purpose.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, Protocol, runtime_checkable

from ...core.events.cache_expired import CacheExpired, ExpirationTrigger


@runtime_checkable
class MetricsCollector(Protocol):
    """Protocol for metrics collection."""
    
    async def record_cache_expiration(
        self,
        namespace: str,
        trigger: str,
        entry_age_seconds: int,
        detection_delay_seconds: float
    ) -> None:
        """Record cache expiration metrics."""
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
        """Schedule cache warming for expired entries."""
        ...


@runtime_checkable
class TTLAnalyticsService(Protocol):
    """Protocol for TTL analytics service."""
    
    async def analyze_ttl_effectiveness(
        self,
        cache_key: str,
        namespace: str,
        original_ttl_seconds: Optional[int],
        entry_age_seconds: int,
        access_count: Optional[int]
    ) -> None:
        """Analyze TTL effectiveness for optimization."""
        ...


@dataclass
class CacheExpiredHandlerResult:
    """Result of cache expired handling."""
    
    success: bool
    metrics_recorded: bool = False
    alerts_sent: int = 0
    warming_scheduled: bool = False
    ttl_analyzed: bool = False
    error_message: Optional[str] = None


class CacheExpiredHandler:
    """Cache expired event handler with TTL analysis and warming triggers.
    
    Handles cache expiration events by:
    - Recording expiration metrics and analyzing expiration patterns
    - Tracking TTL effectiveness and detection efficiency
    - Triggering cache warming for frequently accessed expired entries
    - Analyzing optimal TTL values based on access patterns
    - Monitoring expiration detection delays and performance
    """
    
    # Performance thresholds
    POOR_DETECTION_THRESHOLD_SECONDS = 1800    # 30 minutes detection delay
    FREQUENT_ACCESS_THRESHOLD = 10             # High access count
    RECENT_ACCESS_THRESHOLD_SECONDS = 300      # 5 minutes since last access
    SHORT_TTL_THRESHOLD_SECONDS = 300          # 5 minutes TTL
    
    def __init__(
        self,
        metrics_collector: Optional[MetricsCollector] = None,
        alerting_service: Optional[AlertingService] = None,
        warming_service: Optional[CacheWarmingService] = None,
        ttl_analytics_service: Optional[TTLAnalyticsService] = None,
        enable_detailed_logging: bool = True,
        enable_warming_triggers: bool = True
    ):
        """Initialize cache expired handler.
        
        Args:
            metrics_collector: Metrics collection service
            alerting_service: Alerting service for performance issues
            warming_service: Cache warming service
            ttl_analytics_service: TTL analytics service
            enable_detailed_logging: Whether to enable detailed logging
            enable_warming_triggers: Whether to enable warming triggers
        """
        self._metrics_collector = metrics_collector
        self._alerting_service = alerting_service
        self._warming_service = warming_service
        self._ttl_analytics_service = ttl_analytics_service
        self._enable_detailed_logging = enable_detailed_logging
        self._enable_warming_triggers = enable_warming_triggers
        self._logger = logging.getLogger(__name__)
    
    async def handle(self, event: CacheExpired) -> CacheExpiredHandlerResult:
        """Handle cache expired event.
        
        Args:
            event: Cache expired event to handle
            
        Returns:
            Result of expiration handling with metrics and actions
        """
        try:
            result = CacheExpiredHandlerResult(success=True)
            
            # Record expiration metrics
            if self._metrics_collector:
                await self._record_expiration_metrics(event)
                result.metrics_recorded = True
            
            # Log expiration details
            if self._enable_detailed_logging:
                self._log_expiration_details(event)
            
            # Check for detection efficiency issues
            if self._alerting_service:
                alerts_sent = await self._check_expiration_alerts(event)
                result.alerts_sent = alerts_sent
            
            # Consider cache warming for frequently accessed entries
            if self._enable_warming_triggers and self._warming_service:
                warming_scheduled = await self._consider_warming(event)
                result.warming_scheduled = warming_scheduled
            
            # Analyze TTL effectiveness
            if self._ttl_analytics_service:
                await self._analyze_ttl_effectiveness(event)
                result.ttl_analyzed = True
            
            # Analyze expiration patterns
            await self._analyze_expiration_pattern(event)
            
            return result
            
        except Exception as e:
            self._logger.error(
                f"Failed to handle cache expired event {event.event_id}: {str(e)}",
                extra={
                    "event_id": event.event_id,
                    "cache_key": str(event.key),
                    "namespace": str(event.namespace),
                    "trigger": event.trigger.value,
                    "error": str(e)
                }
            )
            
            return CacheExpiredHandlerResult(
                success=False,
                error_message=str(e)
            )
    
    async def _record_expiration_metrics(self, event: CacheExpired) -> None:
        """Record cache expiration metrics."""
        try:
            await self._metrics_collector.record_cache_expiration(
                namespace=str(event.namespace),
                trigger=event.trigger.value,
                entry_age_seconds=event.entry_age_seconds,
                detection_delay_seconds=event.get_detection_delay_seconds()
            )
        except Exception as e:
            self._logger.warning(
                f"Failed to record expiration metrics for {event.event_id}: {str(e)}"
            )
    
    def _log_expiration_details(self, event: CacheExpired) -> None:
        """Log cache expiration details."""
        log_context = {
            "event_id": event.event_id,
            "cache_key": str(event.key),
            "namespace": str(event.namespace),
            "trigger": event.trigger.value,
            "entry_age_seconds": event.entry_age_seconds,
            "detection_delay_seconds": event.get_detection_delay_seconds(),
            "expiration_category": event.get_expiration_category(),
            "detection_efficiency": event.get_detection_efficiency(),
            "warming_candidate": event.is_candidate_for_warming(),
            "access_count": event.access_count,
            "request_id": event.request_id,
            "user_id": event.user_id,
            "tenant_id": event.tenant_id
        }
        
        # Log level based on expiration category and efficiency
        if event.get_expiration_category() == "premature":
            self._logger.warning("Premature cache expiration", extra=log_context)
        elif event.get_detection_efficiency() == "poor":
            self._logger.warning("Poor expiration detection efficiency", extra=log_context)
        elif event.get_expiration_category() == "unused":
            self._logger.debug("Unused cache entry expired", extra=log_context)
        else:
            self._logger.info(f"Cache expired - {event.get_expiration_category()}", extra=log_context)
    
    async def _check_expiration_alerts(self, event: CacheExpired) -> int:
        """Check for expiration-related issues and send alerts."""
        alerts_sent = 0
        
        try:
            # Poor detection efficiency alert
            detection_delay = event.get_detection_delay_seconds()
            if detection_delay > self.POOR_DETECTION_THRESHOLD_SECONDS:
                await self._alerting_service.send_performance_alert(
                    alert_type="poor_expiration_detection",
                    message=f"Poor expiration detection: {detection_delay:.0f}s delay",
                    context={
                        "event_id": event.event_id,
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "detection_delay_seconds": detection_delay,
                        "threshold_seconds": self.POOR_DETECTION_THRESHOLD_SECONDS,
                        "detection_efficiency": event.get_detection_efficiency()
                    }
                )
                alerts_sent += 1
            
            # Premature expiration alert
            if event.get_expiration_category() == "premature":
                await self._alerting_service.send_performance_alert(
                    alert_type="premature_cache_expiration",
                    message="Frequently accessed cache entry expired prematurely",
                    context={
                        "event_id": event.event_id,
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "access_count": event.access_count,
                        "entry_age_seconds": event.entry_age_seconds,
                        "original_ttl_seconds": event.original_ttl_seconds
                    }
                )
                alerts_sent += 1
                
        except Exception as e:
            self._logger.error(f"Failed to send expiration alerts: {str(e)}")
        
        return alerts_sent
    
    async def _consider_warming(self, event: CacheExpired) -> bool:
        """Consider scheduling cache warming for expired entries."""
        try:
            # Use the event's built-in warming candidate detection
            if event.is_candidate_for_warming():
                await self._warming_service.schedule_warming(
                    cache_key=str(event.key),
                    namespace=str(event.namespace),
                    priority="high"  # High priority for warming candidates
                )
                
                self._logger.info(
                    "Scheduled cache warming for expired frequently accessed entry",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "access_count": event.access_count,
                        "entry_age_seconds": event.entry_age_seconds
                    }
                )
                return True
            
        except Exception as e:
            self._logger.error(f"Failed to schedule cache warming: {str(e)}")
        
        return False
    
    async def _analyze_ttl_effectiveness(self, event: CacheExpired) -> None:
        """Analyze TTL effectiveness for optimization."""
        try:
            await self._ttl_analytics_service.analyze_ttl_effectiveness(
                cache_key=str(event.key),
                namespace=str(event.namespace),
                original_ttl_seconds=event.original_ttl_seconds,
                entry_age_seconds=event.entry_age_seconds,
                access_count=event.access_count
            )
        except Exception as e:
            self._logger.warning(f"Failed to analyze TTL effectiveness: {str(e)}")
    
    async def _analyze_expiration_pattern(self, event: CacheExpired) -> None:
        """Analyze expiration patterns for optimization insights."""
        try:
            expiration_category = event.get_expiration_category()
            
            # Analyze different expiration categories
            if expiration_category == "premature":
                self._logger.info(
                    "Premature expiration detected - consider increasing TTL",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "access_count": event.access_count,
                        "original_ttl_seconds": event.original_ttl_seconds,
                        "entry_age_seconds": event.entry_age_seconds
                    }
                )
            
            elif expiration_category == "unused":
                self._logger.debug(
                    "Unused entry expired - TTL may be too long",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "original_ttl_seconds": event.original_ttl_seconds,
                        "entry_age_seconds": event.entry_age_seconds
                    }
                )
            
            # Analyze detection efficiency
            detection_efficiency = event.get_detection_efficiency()
            if detection_efficiency in ["acceptable", "poor"]:
                self._logger.warning(
                    f"Suboptimal expiration detection: {detection_efficiency}",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace),
                        "detection_delay_seconds": event.get_detection_delay_seconds(),
                        "trigger": event.trigger.value,
                        "detection_efficiency": detection_efficiency
                    }
                )
            
            # Analyze trigger patterns
            if event.trigger == ExpirationTrigger.ACCESS:
                self._logger.debug(
                    "Expiration detected on access - reactive detection",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace)
                    }
                )
            elif event.trigger == ExpirationTrigger.CLEANUP:
                self._logger.debug(
                    "Expiration detected by cleanup - proactive detection",
                    extra={
                        "cache_key": str(event.key),
                        "namespace": str(event.namespace)
                    }
                )
            
        except Exception as e:
            self._logger.error(f"Failed to analyze expiration pattern: {str(e)}")


# Factory function for dependency injection
def create_cache_expired_handler(
    metrics_collector: Optional[MetricsCollector] = None,
    alerting_service: Optional[AlertingService] = None,
    warming_service: Optional[CacheWarmingService] = None,
    ttl_analytics_service: Optional[TTLAnalyticsService] = None,
    enable_detailed_logging: bool = True,
    enable_warming_triggers: bool = True
) -> CacheExpiredHandler:
    """Create cache expired handler with configuration.
    
    Args:
        metrics_collector: Metrics collection service
        alerting_service: Alerting service for performance issues
        warming_service: Cache warming service
        ttl_analytics_service: TTL analytics service  
        enable_detailed_logging: Whether to enable detailed logging
        enable_warming_triggers: Whether to enable warming triggers
        
    Returns:
        Configured cache expired handler
    """
    return CacheExpiredHandler(
        metrics_collector=metrics_collector,
        alerting_service=alerting_service,
        warming_service=warming_service,
        ttl_analytics_service=ttl_analytics_service,
        enable_detailed_logging=enable_detailed_logging,
        enable_warming_triggers=enable_warming_triggers
    )