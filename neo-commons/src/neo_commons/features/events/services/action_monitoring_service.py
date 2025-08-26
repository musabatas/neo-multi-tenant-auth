"""Action execution monitoring and logging service."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum

from ....core.value_objects import ActionId
from ..entities.event_action import ActionExecution, EventAction
from ..repositories.action_execution_repository import ActionExecutionRepository


class MonitoringLevel(Enum):
    """Monitoring level enumeration."""
    MINIMAL = "minimal"      # Basic success/failure tracking
    STANDARD = "standard"    # Includes timing and error details
    DETAILED = "detailed"    # Full event data and execution context
    DEBUG = "debug"         # All data including internal state


@dataclass
class ExecutionMetrics:
    """Metrics for action execution monitoring."""
    
    # Timing metrics
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    timeout_executions: int = 0
    
    # Performance metrics
    avg_duration_ms: float = 0.0
    min_duration_ms: int = 0
    max_duration_ms: int = 0
    p95_duration_ms: float = 0.0
    
    # Error tracking
    error_count_by_type: Dict[str, int] = field(default_factory=dict)
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Rate metrics
    executions_per_minute: float = 0.0
    success_rate_percent: float = 0.0
    
    # Time window
    window_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    window_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_executions == 0:
            return 0.0
        return (self.successful_executions / self.total_executions) * 100
    
    def add_execution_result(self, execution: ActionExecution) -> None:
        """Add execution result to metrics."""
        self.total_executions += 1
        
        if execution.status == "success":
            self.successful_executions += 1
        elif execution.status == "failed":
            self.failed_executions += 1
        elif execution.status == "timeout":
            self.timeout_executions += 1
        
        # Update duration metrics
        if execution.duration_ms is not None:
            if self.min_duration_ms == 0 or execution.duration_ms < self.min_duration_ms:
                self.min_duration_ms = execution.duration_ms
            
            if execution.duration_ms > self.max_duration_ms:
                self.max_duration_ms = execution.duration_ms
            
            # Recalculate average (simple running average)
            old_avg = self.avg_duration_ms
            self.avg_duration_ms = ((old_avg * (self.total_executions - 1)) + execution.duration_ms) / self.total_executions
        
        # Track errors
        if execution.error_message:
            error_type = self._classify_error(execution.error_message)
            self.error_count_by_type[error_type] = self.error_count_by_type.get(error_type, 0) + 1
            
            # Keep recent errors (limit to 10)
            self.recent_errors.append({
                "timestamp": execution.completed_at.isoformat() if execution.completed_at else None,
                "type": error_type,
                "message": execution.error_message[:200],  # Truncate long messages
                "execution_id": str(execution.id.value)
            })
            
            if len(self.recent_errors) > 10:
                self.recent_errors.pop(0)
        
        # Update success rate
        self.success_rate_percent = self.calculate_success_rate()
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error message into error types."""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "network"
        elif "404" in error_message or "not found" in error_lower:
            return "not_found"
        elif "401" in error_message or "403" in error_message or "unauthorized" in error_lower:
            return "auth"
        elif "500" in error_message or "internal server error" in error_lower:
            return "server_error"
        elif "validation" in error_lower or "invalid" in error_lower:
            return "validation"
        else:
            return "unknown"


@dataclass
class ActionMonitoringConfig:
    """Configuration for action monitoring."""
    
    # Logging configuration
    log_level: str = "INFO"
    log_executions: bool = True
    log_errors: bool = True
    log_performance: bool = True
    
    # Metrics collection
    collect_metrics: bool = True
    metrics_window_minutes: int = 60
    metrics_retention_hours: int = 24
    
    # Performance monitoring
    slow_execution_threshold_ms: int = 5000
    log_slow_executions: bool = True
    
    # Error monitoring  
    max_recent_errors: int = 50
    alert_on_error_rate: bool = True
    error_rate_threshold_percent: float = 10.0
    
    # Resource monitoring
    monitor_memory_usage: bool = False
    monitor_cpu_usage: bool = False
    
    def __post_init__(self):
        """Validate configuration."""
        if self.metrics_window_minutes <= 0:
            raise ValueError("Metrics window must be positive")
        
        if self.error_rate_threshold_percent < 0 or self.error_rate_threshold_percent > 100:
            raise ValueError("Error rate threshold must be between 0 and 100")


class ActionMonitoringService:
    """Service for monitoring and logging action executions."""
    
    def __init__(
        self,
        execution_repository: ActionExecutionRepository,
        config: Optional[ActionMonitoringConfig] = None
    ):
        """Initialize monitoring service.
        
        Args:
            execution_repository: Repository for execution data
            config: Monitoring configuration
        """
        self._repository = execution_repository
        self._config = config or ActionMonitoringConfig()
        
        # Setup logging
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._logger.setLevel(getattr(logging, self._config.log_level))
        
        # Metrics storage (in-memory for now, could be Redis/external)
        self._metrics_cache: Dict[str, ExecutionMetrics] = {}
        self._global_metrics = ExecutionMetrics()
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        
        self._logger.info("Action monitoring service initialized")
    
    async def start_monitoring(self) -> None:
        """Start background monitoring tasks."""
        if self._config.collect_metrics:
            self._metrics_task = asyncio.create_task(self._metrics_collection_loop())
        
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._logger.info("Background monitoring tasks started")
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks."""
        if self._metrics_task:
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        self._logger.info("Background monitoring tasks stopped")
    
    async def log_execution_start(
        self, 
        action: EventAction, 
        execution: ActionExecution,
        event_data: Dict[str, Any]
    ) -> None:
        """Log action execution start.
        
        Args:
            action: The action being executed
            execution: Execution instance
            event_data: Event data that triggered the action
        """
        if not self._config.log_executions:
            return
        
        log_context = {
            "action_id": str(action.id.value),
            "action_name": action.name,
            "execution_id": str(execution.id.value),
            "event_type": execution.event_type,
            "handler_type": action.handler_type.value,
            "execution_mode": action.execution_mode.value
        }
        
        # Add event data if detailed logging enabled
        if self._config.log_level == "DEBUG":
            log_context["event_data"] = event_data
        
        self._logger.info(
            f"Action execution started: {action.name} ({action.handler_type.value})",
            extra=log_context
        )
    
    async def log_execution_complete(
        self, 
        action: EventAction, 
        execution: ActionExecution
    ) -> None:
        """Log action execution completion.
        
        Args:
            action: The action that was executed
            execution: Completed execution instance
        """
        if not self._config.log_executions:
            return
        
        log_context = {
            "action_id": str(action.id.value),
            "action_name": action.name,
            "execution_id": str(execution.id.value),
            "status": execution.status,
            "duration_ms": execution.duration_ms,
            "retry_count": execution.retry_count
        }
        
        # Determine log level based on status
        if execution.status == "success":
            self._logger.info(
                f"Action execution completed successfully: {action.name} "
                f"({execution.duration_ms}ms)",
                extra=log_context
            )
        elif execution.status == "failed":
            if self._config.log_errors:
                log_context["error_message"] = execution.error_message
                self._logger.error(
                    f"Action execution failed: {action.name} - {execution.error_message}",
                    extra=log_context
                )
        elif execution.status == "timeout":
            self._logger.warning(
                f"Action execution timed out: {action.name} "
                f"({execution.duration_ms}ms)",
                extra=log_context
            )
        
        # Log slow executions
        if (self._config.log_slow_executions and 
            execution.duration_ms and 
            execution.duration_ms > self._config.slow_execution_threshold_ms):
            
            self._logger.warning(
                f"Slow action execution detected: {action.name} "
                f"({execution.duration_ms}ms > {self._config.slow_execution_threshold_ms}ms)",
                extra=log_context
            )
        
        # Update metrics
        if self._config.collect_metrics:
            await self._update_metrics(action, execution)
    
    async def log_execution_error(
        self, 
        action: EventAction, 
        execution: ActionExecution, 
        error: Exception
    ) -> None:
        """Log execution error with full context.
        
        Args:
            action: The action that failed
            execution: Failed execution instance
            error: The exception that occurred
        """
        if not self._config.log_errors:
            return
        
        log_context = {
            "action_id": str(action.id.value),
            "action_name": action.name,
            "execution_id": str(execution.id.value),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "retry_count": execution.retry_count
        }
        
        self._logger.error(
            f"Action execution error: {action.name} - {type(error).__name__}: {str(error)}",
            extra=log_context,
            exc_info=True if self._config.log_level == "DEBUG" else False
        )
    
    async def get_action_metrics(self, action_id: str) -> Optional[ExecutionMetrics]:
        """Get metrics for a specific action.
        
        Args:
            action_id: Action ID
            
        Returns:
            ExecutionMetrics if available, None otherwise
        """
        return self._metrics_cache.get(action_id)
    
    async def get_global_metrics(self) -> ExecutionMetrics:
        """Get global execution metrics.
        
        Returns:
            Global ExecutionMetrics
        """
        return self._global_metrics
    
    async def get_recent_executions(
        self, 
        action_id: Optional[str] = None,
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[ActionExecution]:
        """Get recent executions for monitoring.
        
        Args:
            action_id: Specific action ID, or None for all actions
            limit: Maximum number of executions to return
            status: Filter by execution status
            
        Returns:
            List of recent executions
        """
        # This would use the execution repository to get recent executions
        # Implementation depends on repository capabilities
        return []
    
    async def check_action_health(self, action_id: str) -> Dict[str, Any]:
        """Check health status of an action.
        
        Args:
            action_id: Action ID to check
            
        Returns:
            Health status information
        """
        metrics = await self.get_action_metrics(action_id)
        if not metrics:
            return {
                "status": "unknown",
                "message": "No execution data available"
            }
        
        # Determine health status
        if metrics.total_executions == 0:
            status = "inactive"
            message = "No recent executions"
        elif metrics.success_rate_percent >= 95:
            status = "healthy"
            message = f"Success rate: {metrics.success_rate_percent:.1f}%"
        elif metrics.success_rate_percent >= 80:
            status = "warning"
            message = f"Success rate: {metrics.success_rate_percent:.1f}% (below optimal)"
        else:
            status = "critical"
            message = f"Success rate: {metrics.success_rate_percent:.1f}% (needs attention)"
        
        return {
            "status": status,
            "message": message,
            "metrics": {
                "total_executions": metrics.total_executions,
                "success_rate": metrics.success_rate_percent,
                "avg_duration_ms": metrics.avg_duration_ms,
                "recent_errors": len(metrics.recent_errors)
            }
        }
    
    async def _update_metrics(self, action: EventAction, execution: ActionExecution) -> None:
        """Update metrics with execution result.
        
        Args:
            action: The executed action
            execution: Completed execution
        """
        action_id = str(action.id.value)
        
        # Update action-specific metrics
        if action_id not in self._metrics_cache:
            self._metrics_cache[action_id] = ExecutionMetrics()
        
        self._metrics_cache[action_id].add_execution_result(execution)
        
        # Update global metrics
        self._global_metrics.add_execution_result(execution)
        
        # Check for alerts
        await self._check_alerts(action, self._metrics_cache[action_id])
    
    async def _check_alerts(self, action: EventAction, metrics: ExecutionMetrics) -> None:
        """Check if any alerts should be triggered.
        
        Args:
            action: The action to check
            metrics: Current metrics for the action
        """
        if not self._config.alert_on_error_rate:
            return
        
        # Check error rate threshold
        if (metrics.total_executions >= 10 and  # Minimum executions for meaningful rate
            metrics.success_rate_percent < (100 - self._config.error_rate_threshold_percent)):
            
            self._logger.critical(
                f"HIGH ERROR RATE ALERT: Action '{action.name}' has success rate "
                f"{metrics.success_rate_percent:.1f}% (threshold: "
                f"{100 - self._config.error_rate_threshold_percent}%)",
                extra={
                    "alert_type": "high_error_rate",
                    "action_id": str(action.id.value),
                    "action_name": action.name,
                    "success_rate": metrics.success_rate_percent,
                    "threshold": 100 - self._config.error_rate_threshold_percent,
                    "total_executions": metrics.total_executions
                }
            )
    
    async def _metrics_collection_loop(self) -> None:
        """Background task to collect and persist metrics."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                
                # Here you could persist metrics to database, send to monitoring system, etc.
                # For now, just log summary
                if self._global_metrics.total_executions > 0:
                    self._logger.debug(
                        f"Metrics summary: {self._global_metrics.total_executions} executions, "
                        f"{self._global_metrics.success_rate_percent:.1f}% success rate, "
                        f"{self._global_metrics.avg_duration_ms:.1f}ms avg duration"
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up old metrics and data."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Clean up old metrics (keep only recent data)
                cutoff_time = datetime.now(timezone.utc) - timedelta(
                    hours=self._config.metrics_retention_hours
                )
                
                # Clean up metrics cache (simplified approach)
                for action_id in list(self._metrics_cache.keys()):
                    metrics = self._metrics_cache[action_id]
                    if metrics.window_end < cutoff_time:
                        del self._metrics_cache[action_id]
                
                # Clean up recent errors
                for metrics in self._metrics_cache.values():
                    if len(metrics.recent_errors) > self._config.max_recent_errors:
                        metrics.recent_errors = metrics.recent_errors[-self._config.max_recent_errors:]
                
                self._logger.debug("Completed metrics cleanup")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)  # Wait before retrying