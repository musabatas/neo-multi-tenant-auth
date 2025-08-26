"""Webhook delivery monitoring service.

Provides real-time monitoring, alerting, and health checking
for webhook delivery systems with automatic incident detection.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from ....core.value_objects import WebhookEndpointId
from ..services.webhook_metrics_service import (
    WebhookMetricsService, 
    Alert, 
    AlertSeverity, 
    SystemMetrics,
    EndpointMetrics
)
from ..entities.protocols import WebhookEndpointRepository, WebhookDeliveryRepository
from ..adapters.http_webhook_adapter import HttpWebhookAdapter


logger = logging.getLogger(__name__)


class MonitoringStatus(Enum):
    """Monitoring service status."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class MonitoringConfig:
    """Configuration for webhook monitoring service."""
    
    # Monitoring intervals
    health_check_interval_seconds: int = 300  # 5 minutes
    metrics_collection_interval_seconds: int = 60  # 1 minute
    alert_evaluation_interval_seconds: int = 120  # 2 minutes
    endpoint_verification_interval_seconds: int = 3600  # 1 hour
    
    # Health check settings
    endpoint_timeout_seconds: int = 30
    max_concurrent_health_checks: int = 10
    health_check_retry_attempts: int = 2
    
    # Alert settings
    alert_cooldown_minutes: int = 15
    max_alerts_per_endpoint: int = 5
    
    # Performance thresholds
    critical_response_time_ms: int = 10000
    warning_response_time_ms: int = 5000
    critical_success_rate: float = 75.0
    warning_success_rate: float = 90.0
    
    # Maintenance settings
    metrics_retention_days: int = 30
    alert_retention_days: int = 7


@dataclass
class HealthCheckResult:
    """Result of an endpoint health check."""
    
    endpoint_id: WebhookEndpointId
    is_healthy: bool
    response_time_ms: Optional[int] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "endpoint_id": str(self.endpoint_id.value),
            "is_healthy": self.is_healthy,
            "response_time_ms": self.response_time_ms,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "checked_at": self.checked_at.isoformat()
        }


@dataclass
class MonitoringStats:
    """Real-time monitoring statistics."""
    
    # Service status
    status: MonitoringStatus
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0.0
    
    # Health check statistics
    total_health_checks: int = 0
    successful_health_checks: int = 0
    failed_health_checks: int = 0
    avg_health_check_time_ms: float = 0.0
    
    # Alert statistics
    total_alerts_generated: int = 0
    active_alerts: int = 0
    resolved_alerts: int = 0
    
    # System performance
    endpoints_monitored: int = 0
    healthy_endpoints: int = 0
    unhealthy_endpoints: int = 0
    last_full_scan: Optional[datetime] = None
    
    def calculate_health_check_success_rate(self) -> float:
        """Calculate health check success rate."""
        if self.total_health_checks == 0:
            return 0.0
        return (self.successful_health_checks / self.total_health_checks) * 100


class WebhookMonitoringService:
    """Real-time monitoring service for webhook deliveries."""
    
    def __init__(
        self,
        metrics_service: WebhookMetricsService,
        endpoint_repository: WebhookEndpointRepository,
        delivery_repository: WebhookDeliveryRepository,
        http_adapter: HttpWebhookAdapter,
        config: MonitoringConfig = None
    ):
        """Initialize monitoring service.
        
        Args:
            metrics_service: Webhook metrics service
            endpoint_repository: Webhook endpoint repository
            delivery_repository: Webhook delivery repository
            http_adapter: HTTP adapter for endpoint verification
            config: Monitoring configuration
        """
        self._metrics_service = metrics_service
        self._endpoint_repo = endpoint_repository
        self._delivery_repo = delivery_repository
        self._http_adapter = http_adapter
        self._config = config or MonitoringConfig()
        
        # Service state
        self._status = MonitoringStatus.STOPPED
        self._monitoring_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Statistics and caching
        self._stats = MonitoringStats(status=self._status)
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_cooldowns: Dict[str, datetime] = {}
        self._last_health_checks: Dict[WebhookEndpointId, HealthCheckResult] = {}
        
        # Event handlers
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._health_check_handlers: List[Callable[[HealthCheckResult], None]] = []
    
    async def start(self) -> None:
        """Start the monitoring service."""
        if self._status in [MonitoringStatus.RUNNING, MonitoringStatus.STARTING]:
            logger.warning("Monitoring service is already running or starting")
            return
        
        logger.info("Starting webhook monitoring service...")
        self._status = MonitoringStatus.STARTING
        self._stats.status = self._status
        
        try:
            # Reset shutdown event
            self._shutdown_event.clear()
            
            # Start monitoring tasks
            self._monitoring_tasks = [
                asyncio.create_task(self._health_check_loop()),
                asyncio.create_task(self._metrics_collection_loop()),
                asyncio.create_task(self._alert_evaluation_loop()),
                asyncio.create_task(self._endpoint_verification_loop()),
                asyncio.create_task(self._maintenance_loop())
            ]
            
            # Mark as running
            self._status = MonitoringStatus.RUNNING
            self._stats.status = self._status
            self._stats.started_at = datetime.now(timezone.utc)
            
            logger.info("Webhook monitoring service started successfully")
            
        except Exception as e:
            self._status = MonitoringStatus.ERROR
            self._stats.status = self._status
            logger.error(f"Failed to start monitoring service: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the monitoring service."""
        if self._status == MonitoringStatus.STOPPED:
            logger.info("Monitoring service is already stopped")
            return
        
        logger.info("Stopping webhook monitoring service...")
        self._status = MonitoringStatus.STOPPING
        self._stats.status = self._status
        
        try:
            # Signal shutdown
            self._shutdown_event.set()
            
            # Cancel all monitoring tasks
            for task in self._monitoring_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._monitoring_tasks:
                await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
            
            # Clean up
            self._monitoring_tasks.clear()
            self._status = MonitoringStatus.STOPPED
            self._stats.status = self._status
            
            logger.info("Webhook monitoring service stopped")
            
        except Exception as e:
            self._status = MonitoringStatus.ERROR
            self._stats.status = self._status
            logger.error(f"Error stopping monitoring service: {e}")
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status.
        
        Returns:
            Complete system health information
        """
        # Get latest system metrics
        system_metrics = await self._metrics_service.get_system_metrics(include_endpoint_details=False)
        
        # Get service statistics
        if self._stats.started_at:
            self._stats.uptime_seconds = (datetime.now(timezone.utc) - self._stats.started_at).total_seconds()
        
        # Count active alerts by severity
        alerts_by_severity = {"info": 0, "warning": 0, "critical": 0}
        for alert in self._active_alerts.values():
            alerts_by_severity[alert.severity.value] += 1
        
        # Get recent health check results
        recent_health_checks = [
            result.to_dict() for result in list(self._last_health_checks.values())[-10:]
        ]
        
        return {
            "monitoring_service": {
                "status": self._status.value,
                "uptime_seconds": self._stats.uptime_seconds,
                "started_at": self._stats.started_at.isoformat() if self._stats.started_at else None,
                "health_check_success_rate": self._stats.calculate_health_check_success_rate(),
            },
            "system_metrics": {
                "overall_health_score": system_metrics.overall_health_score,
                "total_endpoints": system_metrics.total_endpoints,
                "healthy_endpoints": system_metrics.healthy_endpoints,
                "unhealthy_endpoints": system_metrics.unhealthy_endpoints,
            },
            "alerts": {
                "total_active": len(self._active_alerts),
                "by_severity": alerts_by_severity,
                "recent_alerts": [alert.title for alert in list(self._active_alerts.values())[-5:]]
            },
            "performance": {
                "avg_health_check_time_ms": self._stats.avg_health_check_time_ms,
                "endpoints_monitored": self._stats.endpoints_monitored,
                "last_full_scan": self._stats.last_full_scan.isoformat() if self._stats.last_full_scan else None
            },
            "recent_health_checks": recent_health_checks
        }
    
    async def get_endpoint_health(self, endpoint_id: WebhookEndpointId) -> Optional[HealthCheckResult]:
        """Get latest health check result for a specific endpoint.
        
        Args:
            endpoint_id: Webhook endpoint ID
            
        Returns:
            Latest health check result or None if not found
        """
        return self._last_health_checks.get(endpoint_id)
    
    async def trigger_health_check(self, endpoint_id: WebhookEndpointId) -> HealthCheckResult:
        """Manually trigger a health check for a specific endpoint.
        
        Args:
            endpoint_id: Webhook endpoint ID
            
        Returns:
            Health check result
        """
        logger.info(f"Triggering manual health check for endpoint {endpoint_id}")
        
        endpoint = await self._endpoint_repo.get_by_id(endpoint_id)
        if not endpoint:
            return HealthCheckResult(
                endpoint_id=endpoint_id,
                is_healthy=False,
                error_message="Endpoint not found"
            )
        
        result = await self._perform_health_check(endpoint)
        
        # Update statistics
        self._stats.total_health_checks += 1
        if result.is_healthy:
            self._stats.successful_health_checks += 1
        else:
            self._stats.failed_health_checks += 1
        
        # Trigger handlers
        for handler in self._health_check_handlers:
            try:
                handler(result)
            except Exception as e:
                logger.error(f"Health check handler error: {e}")
        
        return result
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add an alert handler function.
        
        Args:
            handler: Function to call when alerts are generated
        """
        self._alert_handlers.append(handler)
        logger.info("Added alert handler")
    
    def add_health_check_handler(self, handler: Callable[[HealthCheckResult], None]) -> None:
        """Add a health check handler function.
        
        Args:
            handler: Function to call when health checks complete
        """
        self._health_check_handlers.append(handler)
        logger.info("Added health check handler")
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all currently active alerts."""
        return list(self._active_alerts.values())
    
    def get_monitoring_stats(self) -> MonitoringStats:
        """Get current monitoring statistics."""
        # Update uptime
        if self._stats.started_at:
            self._stats.uptime_seconds = (datetime.now(timezone.utc) - self._stats.started_at).total_seconds()
        
        return self._stats
    
    async def _health_check_loop(self) -> None:
        """Main health check monitoring loop."""
        logger.info("Starting health check loop")
        
        while not self._shutdown_event.is_set():
            try:
                start_time = datetime.now(timezone.utc)
                
                # Get all active endpoints
                endpoints = await self._endpoint_repo.get_active_endpoints()
                self._stats.endpoints_monitored = len(endpoints)
                
                if endpoints:
                    # Perform health checks with controlled concurrency
                    semaphore = asyncio.Semaphore(self._config.max_concurrent_health_checks)
                    tasks = [
                        self._perform_health_check_with_semaphore(endpoint, semaphore)
                        for endpoint in endpoints
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    healthy_count = 0
                    unhealthy_count = 0
                    total_response_time = 0
                    response_time_count = 0
                    
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Health check task failed: {result}")
                            continue
                        
                        self._last_health_checks[result.endpoint_id] = result
                        self._stats.total_health_checks += 1
                        
                        if result.is_healthy:
                            healthy_count += 1
                            self._stats.successful_health_checks += 1
                        else:
                            unhealthy_count += 1
                            self._stats.failed_health_checks += 1
                        
                        # Aggregate response times
                        if result.response_time_ms:
                            total_response_time += result.response_time_ms
                            response_time_count += 1
                        
                        # Trigger handlers
                        for handler in self._health_check_handlers:
                            try:
                                handler(result)
                            except Exception as e:
                                logger.error(f"Health check handler error: {e}")
                    
                    # Update statistics
                    self._stats.healthy_endpoints = healthy_count
                    self._stats.unhealthy_endpoints = unhealthy_count
                    
                    if response_time_count > 0:
                        self._stats.avg_health_check_time_ms = total_response_time / response_time_count
                    
                    self._stats.last_full_scan = datetime.now(timezone.utc)
                    
                    logger.info(f"Health check cycle completed: {healthy_count} healthy, {unhealthy_count} unhealthy")
                
                # Wait for next interval
                elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
                sleep_time = max(0, self._config.health_check_interval_seconds - elapsed)
                
                if sleep_time > 0:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=sleep_time)
                
            except asyncio.TimeoutError:
                continue  # Normal timeout, continue loop
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _metrics_collection_loop(self) -> None:
        """Metrics collection and caching loop."""
        logger.info("Starting metrics collection loop")
        
        while not self._shutdown_event.is_set():
            try:
                # Trigger metrics calculation to warm the cache
                await self._metrics_service.get_system_metrics(include_endpoint_details=False)
                
                logger.debug("Metrics collection cycle completed")
                
                # Wait for next interval
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=self._config.metrics_collection_interval_seconds
                    )
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue loop
                
            except Exception as e:
                logger.error(f"Metrics collection loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _alert_evaluation_loop(self) -> None:
        """Alert evaluation and management loop."""
        logger.info("Starting alert evaluation loop")
        
        while not self._shutdown_event.is_set():
            try:
                # Get current system metrics
                system_metrics = await self._metrics_service.get_system_metrics(include_endpoint_details=True)
                
                # Generate new alerts
                new_alerts = await self._evaluate_alerts(system_metrics)
                
                # Process new alerts
                for alert in new_alerts:
                    await self._process_alert(alert)
                
                # Clean up resolved alerts
                await self._cleanup_resolved_alerts()
                
                logger.debug(f"Alert evaluation completed: {len(self._active_alerts)} active alerts")
                
                # Wait for next interval
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=self._config.alert_evaluation_interval_seconds
                    )
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue loop
                
            except Exception as e:
                logger.error(f"Alert evaluation loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _endpoint_verification_loop(self) -> None:
        """Periodic endpoint verification loop."""
        logger.info("Starting endpoint verification loop")
        
        while not self._shutdown_event.is_set():
            try:
                # Get all active endpoints
                endpoints = await self._endpoint_repo.get_active_endpoints()
                
                # Verify endpoints that haven't been verified recently
                for endpoint in endpoints:
                    last_check = self._last_health_checks.get(endpoint.id)
                    if (not last_check or 
                        datetime.now(timezone.utc) - last_check.checked_at > 
                        timedelta(seconds=self._config.endpoint_verification_interval_seconds)):
                        
                        # Perform verification
                        result = await self._perform_health_check(endpoint)
                        self._last_health_checks[endpoint.id] = result
                
                logger.debug("Endpoint verification cycle completed")
                
                # Wait for next interval
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), 
                        timeout=self._config.endpoint_verification_interval_seconds
                    )
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue loop
                
            except Exception as e:
                logger.error(f"Endpoint verification loop error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying
    
    async def _maintenance_loop(self) -> None:
        """Maintenance tasks loop."""
        logger.info("Starting maintenance loop")
        
        while not self._shutdown_event.is_set():
            try:
                # Clean up old alerts
                await self._cleanup_old_alerts()
                
                # Clear metrics cache periodically
                self._metrics_service.clear_metrics_cache()
                
                logger.debug("Maintenance cycle completed")
                
                # Run maintenance every hour
                try:
                    await asyncio.wait_for(self._shutdown_event.wait(), timeout=3600)
                except asyncio.TimeoutError:
                    continue  # Normal timeout, continue loop
                
            except Exception as e:
                logger.error(f"Maintenance loop error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour before retrying
    
    async def _perform_health_check_with_semaphore(
        self, 
        endpoint, 
        semaphore: asyncio.Semaphore
    ) -> HealthCheckResult:
        """Perform health check with concurrency control."""
        async with semaphore:
            return await self._perform_health_check(endpoint)
    
    async def _perform_health_check(self, endpoint) -> HealthCheckResult:
        """Perform health check on a single endpoint."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Use the HTTP adapter to verify endpoint connectivity
            success, verification_info = await self._http_adapter.verify_endpoint(endpoint)
            
            response_time_ms = verification_info.get("response_time_ms")
            status_code = verification_info.get("status_code")
            error_message = verification_info.get("error") or verification_info.get("error_message")
            
            return HealthCheckResult(
                endpoint_id=endpoint.id,
                is_healthy=success,
                response_time_ms=response_time_ms,
                status_code=status_code,
                error_message=error_message,
                checked_at=start_time
            )
            
        except Exception as e:
            logger.error(f"Health check failed for endpoint {endpoint.id}: {e}")
            return HealthCheckResult(
                endpoint_id=endpoint.id,
                is_healthy=False,
                error_message=str(e),
                checked_at=start_time
            )
    
    async def _evaluate_alerts(self, system_metrics: SystemMetrics) -> List[Alert]:
        """Evaluate system metrics and generate alerts."""
        new_alerts = []
        
        # System-wide alerts
        system_alerts = await self._metrics_service._generate_system_alerts(system_metrics)
        new_alerts.extend(system_alerts)
        
        # Endpoint-specific alerts
        for endpoint_metrics in system_metrics.problematic_endpoints[:5]:  # Check top 5 problematic
            endpoint_alerts = await self._metrics_service._generate_endpoint_alerts(endpoint_metrics)
            new_alerts.extend(endpoint_alerts)
        
        return new_alerts
    
    async def _process_alert(self, alert: Alert) -> None:
        """Process a new alert."""
        # Check cooldown period
        cooldown_key = f"{alert.id}_{alert.severity.value}"
        if cooldown_key in self._alert_cooldowns:
            cooldown_until = self._alert_cooldowns[cooldown_key]
            if datetime.now(timezone.utc) < cooldown_until:
                return  # Still in cooldown
        
        # Add to active alerts
        self._active_alerts[alert.id] = alert
        self._stats.total_alerts_generated += 1
        self._stats.active_alerts = len(self._active_alerts)
        
        # Set cooldown
        cooldown_duration = timedelta(minutes=self._config.alert_cooldown_minutes)
        self._alert_cooldowns[cooldown_key] = datetime.now(timezone.utc) + cooldown_duration
        
        logger.warning(f"New {alert.severity.value} alert: {alert.title}")
        
        # Trigger alert handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")
    
    async def _cleanup_resolved_alerts(self) -> None:
        """Clean up alerts that are no longer relevant."""
        resolved_alerts = []
        
        for alert_id, alert in list(self._active_alerts.items()):
            # Check if conditions that triggered the alert still exist
            should_resolve = await self._should_resolve_alert(alert)
            if should_resolve:
                alert.resolve()
                resolved_alerts.append(alert_id)
        
        # Remove resolved alerts
        for alert_id in resolved_alerts:
            del self._active_alerts[alert_id]
            self._stats.resolved_alerts += 1
        
        self._stats.active_alerts = len(self._active_alerts)
        
        if resolved_alerts:
            logger.info(f"Resolved {len(resolved_alerts)} alerts")
    
    async def _should_resolve_alert(self, alert: Alert) -> bool:
        """Check if an alert should be resolved."""
        # For now, keep alerts active for their cooldown period
        # In a more sophisticated implementation, you would check
        # if the conditions that triggered the alert have been resolved
        return False
    
    async def _cleanup_old_alerts(self) -> None:
        """Clean up old cooldown entries and resolved alerts."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=self._config.alert_retention_days)
        
        # Clean up old cooldowns
        expired_cooldowns = [
            key for key, expires_at in self._alert_cooldowns.items()
            if expires_at < cutoff_time
        ]
        
        for key in expired_cooldowns:
            del self._alert_cooldowns[key]
        
        if expired_cooldowns:
            logger.debug(f"Cleaned up {len(expired_cooldowns)} expired alert cooldowns")