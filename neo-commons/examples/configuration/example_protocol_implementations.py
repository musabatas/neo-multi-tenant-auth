"""Example implementations of application protocols.

This module demonstrates how to implement the LoggingProtocol, MetricsProtocol,
and MonitoringProtocol interfaces with concrete implementations.
"""

import time
import asyncio
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timezone

from .application import (
    LoggingProtocol, MetricsProtocol, MonitoringProtocol,
    LogLevel, MetricType, HealthStatus
)


class StructuredLogger:
    """Example implementation of LoggingProtocol with structured logging."""
    
    def __init__(self, service_name: str = "neo-commons"):
        """Initialize logger with service context."""
        self.service_name = service_name
        self._context: Dict[str, Any] = {}
    
    def log(
        self, 
        level: LogLevel, 
        message: str, 
        extra: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """Log structured message."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "level": level.value,
            "service": self.service_name,
            "message": message,
            **self._context,
            **(extra or {}),
            **kwargs
        }
        
        # In production, this would send to logging system (ELK, etc.)
        print(f"[{level.value}] {timestamp} - {message} | {log_entry}")
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self.log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self.log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self.log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self.log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self.log(LogLevel.CRITICAL, message, **kwargs)
    
    def set_context(self, **context: Any) -> None:
        """Set logging context."""
        self._context.update(context)
    
    def clear_context(self) -> None:
        """Clear logging context."""
        self._context.clear()


class ApplicationMetrics:
    """Example implementation of MetricsProtocol for application metrics."""
    
    def __init__(self, service_name: str = "neo-commons"):
        """Initialize metrics collector."""
        self.service_name = service_name
        self._global_tags: Dict[str, str] = {"service": service_name}
        self._metrics: List[Dict[str, Any]] = []
    
    def _record_metric(self, metric_type: MetricType, name: str, value: Any, tags: Optional[Dict[str, str]] = None) -> None:
        """Record metric with metadata."""
        timestamp = time.time()
        combined_tags = {**self._global_tags, **(tags or {})}
        
        metric = {
            "timestamp": timestamp,
            "type": metric_type.value,
            "name": name,
            "value": value,
            "tags": combined_tags
        }
        
        self._metrics.append(metric)
        
        # In production, this would send to metrics system (Prometheus, DataDog, etc.)
        print(f"METRIC [{metric_type.value}] {name}={value} tags={combined_tags}")
    
    def counter(self, name: str, value: float = 1, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment counter metric."""
        self._record_metric(MetricType.COUNTER, name, value, tags)
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Set gauge metric."""
        self._record_metric(MetricType.GAUGE, name, value, tags)
    
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record histogram value."""
        self._record_metric(MetricType.HISTOGRAM, name, value, tags)
    
    @contextmanager
    def timer(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Timer context manager."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.timing(name, duration, tags)
    
    def timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record timing metric."""
        self._record_metric(MetricType.TIMER, name, duration, tags)
    
    def set_global_tags(self, tags: Dict[str, str]) -> None:
        """Set global tags."""
        self._global_tags.update(tags)
    
    def get_metrics(self) -> List[Dict[str, Any]]:
        """Get recorded metrics (for testing/inspection)."""
        return self._metrics.copy()


class SystemMonitor:
    """Example implementation of MonitoringProtocol for system monitoring."""
    
    def __init__(self, service_name: str = "neo-commons"):
        """Initialize system monitor."""
        self.service_name = service_name
        self._health_checks: Dict[str, Dict[str, Any]] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._monitoring_active = False
    
    async def health_check(self, component: str) -> Dict[str, Any]:
        """Perform health check for component."""
        check_config = self._health_checks.get(component)
        
        if not check_config:
            return {
                "component": component,
                "status": HealthStatus.UNKNOWN.value,
                "message": f"No health check configured for {component}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        try:
            # Execute health check function
            check_func = check_config["check_func"]
            timeout = check_config.get("timeout", 5.0)
            
            # Run check with timeout
            result = await asyncio.wait_for(check_func(), timeout=timeout)
            
            return {
                "component": component,
                "status": HealthStatus.HEALTHY.value,
                "message": "Health check passed",
                "details": result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except asyncio.TimeoutError:
            return {
                "component": component,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Health check timed out after {timeout}s",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "component": component,
                "status": HealthStatus.UNHEALTHY.value,
                "message": f"Health check failed: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        component_results = {}
        overall_status = HealthStatus.HEALTHY
        
        for component in self._health_checks:
            result = await self.health_check(component)
            component_results[component] = result
            
            # Determine overall status (unhealthy overrides healthy)
            if result["status"] == HealthStatus.UNHEALTHY.value:
                overall_status = HealthStatus.UNHEALTHY
            elif result["status"] == HealthStatus.DEGRADED.value and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        return {
            "service": self.service_name,
            "overall_status": overall_status.value,
            "components": component_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "monitoring_active": self._monitoring_active
        }
    
    def register_health_check(
        self,
        name: str,
        check_func: callable,
        interval: Optional[float] = None,
        timeout: Optional[float] = None
    ) -> None:
        """Register health check function."""
        self._health_checks[name] = {
            "check_func": check_func,
            "interval": interval or 30.0,
            "timeout": timeout or 5.0
        }
        
        print(f"✅ Registered health check: {name}")
    
    def unregister_health_check(self, name: str) -> None:
        """Unregister health check."""
        if name in self._health_checks:
            del self._health_checks[name]
            print(f"❌ Unregistered health check: {name}")
    
    async def alert(
        self,
        severity: str,
        message: str,
        component: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send alert notification."""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "message": message,
            "component": component,
            "service": self.service_name,
            "metadata": metadata or {}
        }
        
        self._alerts.append(alert)
        
        # In production, send to alerting system (PagerDuty, Slack, etc.)
        print(f"🚨 ALERT [{severity}] {component}: {message}")
    
    async def get_performance_metrics(self, component: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics."""
        # Mock performance metrics
        metrics = {
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "active_connections": 12,
            "request_rate": 156.7,
            "error_rate": 0.02,
            "response_time_p95": 0.245
        }
        
        if component:
            # Filter metrics for specific component
            component_metrics = {k: v for k, v in metrics.items() if component.lower() in k}
            return {"component": component, "metrics": component_metrics}
        
        return {"service": self.service_name, "metrics": metrics}
    
    def start_monitoring(self) -> None:
        """Start monitoring services."""
        self._monitoring_active = True
        print(f"🔍 Started monitoring for {self.service_name}")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring services."""
        self._monitoring_active = False
        print(f"⏹️ Stopped monitoring for {self.service_name}")
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get recorded alerts (for testing/inspection)."""
        return self._alerts.copy()


# Example usage and demonstration
async def demonstrate_protocols():
    """Demonstrate usage of all three protocols."""
    
    print("=== LoggingProtocol Demo ===")
    logger = StructuredLogger("demo-service")
    logger.set_context(tenant_id="tenant-123", user_id="user-456")
    logger.info("User authenticated", action="login", ip="192.168.1.1")
    logger.error("Database connection failed", database="primary", error_code="CONN_TIMEOUT")
    
    print("\n=== MetricsProtocol Demo ===")
    metrics = ApplicationMetrics("demo-service")
    metrics.counter("requests.total", tags={"endpoint": "/api/users", "method": "GET"})
    metrics.gauge("active_connections", 15)
    metrics.histogram("request_duration", 0.145, tags={"endpoint": "/api/users"})
    
    # Timer usage
    with metrics.timer("database_query", tags={"query": "select_users"}):
        await asyncio.sleep(0.1)  # Simulate database operation
    
    print("\n=== MonitoringProtocol Demo ===")
    monitor = SystemMonitor("demo-service")
    
    # Register health checks
    async def database_health():
        """Mock database health check."""
        return {"connection_pool": {"active": 5, "idle": 10}, "last_query_time": 0.023}
    
    async def cache_health():
        """Mock cache health check."""
        return {"hit_rate": 0.85, "memory_usage": "45%", "keys": 1250}
    
    monitor.register_health_check("database", database_health)
    monitor.register_health_check("cache", cache_health)
    monitor.start_monitoring()
    
    # Check individual component
    db_health = await monitor.health_check("database")
    print(f"Database health: {db_health}")
    
    # Check overall system health
    system_health = await monitor.get_system_health()
    print(f"System health: {system_health}")
    
    # Send alert
    await monitor.alert("warning", "High memory usage detected", "system", 
                       {"memory_usage": "89%", "threshold": "85%"})
    
    print("\n✅ All protocol demonstrations completed!")


if __name__ == "__main__":
    asyncio.run(demonstrate_protocols())