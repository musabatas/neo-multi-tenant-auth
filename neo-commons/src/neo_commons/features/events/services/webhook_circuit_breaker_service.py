"""Circuit breaker service for webhook delivery resilience.

Implements circuit breaker pattern to handle webhook endpoint failures gracefully
and prevent cascading failures in high-load scenarios.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, Optional, Callable, Awaitable, Union
from uuid import UUID

from ....core.value_objects import WebhookEndpointId
from .webhook_config_service import get_webhook_config_service

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states following standard pattern."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Circuit open, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics for monitoring and debugging."""
    
    endpoint_id: WebhookEndpointId
    state: CircuitBreakerState
    failure_count: int = 0
    success_count: int = 0
    total_requests: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changed_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recovery_start_time: Optional[datetime] = None
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failure_count / self.total_requests) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate current success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.success_count / self.total_requests) * 100.0
    
    def reset_counts(self) -> None:
        """Reset failure and success counts for new monitoring window."""
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
    
    def get_time_in_current_state_seconds(self) -> float:
        """Get time spent in current state in seconds."""
        return (datetime.now(timezone.utc) - self.state_changed_time).total_seconds()


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    
    # Failure thresholds
    failure_threshold: int = 5  # Number of failures to open circuit
    failure_rate_threshold: float = 50.0  # Percentage failure rate to open circuit
    minimum_requests: int = 10  # Minimum requests before considering failure rate
    
    # Time windows
    timeout_seconds: float = 60.0  # How long circuit stays open
    recovery_timeout_seconds: float = 30.0  # Timeout for half-open recovery attempts
    monitoring_window_seconds: float = 300.0  # Window for failure rate calculation
    
    # Half-open testing
    max_recovery_requests: int = 3  # Max requests allowed in half-open state
    recovery_success_threshold: int = 2  # Successful requests needed to close circuit
    
    @classmethod
    def from_webhook_config(cls, config_service=None) -> 'CircuitBreakerConfig':
        """Create circuit breaker config from webhook configuration."""
        if config_service is None:
            config_service = get_webhook_config_service()
        
        webhook_config = config_service.get_config()
        delivery_config = webhook_config.delivery
        
        return cls(
            failure_threshold=min(delivery_config.max_retry_attempts + 2, 5),
            timeout_seconds=delivery_config.max_retry_backoff_seconds,
            recovery_timeout_seconds=delivery_config.default_timeout_seconds,
            monitoring_window_seconds=300.0  # 5 minutes
        )


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker blocks a request."""
    
    def __init__(self, endpoint_id: WebhookEndpointId, state: CircuitBreakerState, message: str):
        self.endpoint_id = endpoint_id
        self.state = state
        super().__init__(message)


class WebhookCircuitBreakerService:
    """Service implementing circuit breaker pattern for webhook endpoints.
    
    Provides resilience against failing webhook endpoints by:
    - Monitoring endpoint health and failure rates
    - Automatically blocking requests to failing endpoints
    - Implementing recovery testing with gradual traffic restoration
    - Providing detailed metrics for monitoring and alerting
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker service.
        
        Args:
            config: Circuit breaker configuration (uses webhook config defaults if None)
        """
        self._config = config or CircuitBreakerConfig.from_webhook_config()
        self._circuit_breakers: Dict[WebhookEndpointId, CircuitBreakerStats] = {}
        self._locks: Dict[WebhookEndpointId, asyncio.Lock] = {}
        self._recovery_counters: Dict[WebhookEndpointId, int] = {}
        
        logger.info(f"Circuit breaker service initialized with config: {self._config}")
    
    async def execute_with_circuit_breaker(
        self,
        endpoint_id: WebhookEndpointId,
        operation: Callable[[], Awaitable[Any]],
        operation_name: str = "webhook_delivery"
    ) -> Any:
        """Execute operation with circuit breaker protection.
        
        Args:
            endpoint_id: Webhook endpoint identifier
            operation: Async operation to execute
            operation_name: Name of operation for logging
            
        Returns:
            Operation result
            
        Raises:
            CircuitBreakerError: If circuit breaker blocks the operation
            Exception: Any exception from the operation itself
        """
        # Check circuit breaker state
        stats = await self._get_or_create_circuit_breaker(endpoint_id)
        
        # Block request if circuit is open
        if stats.state == CircuitBreakerState.OPEN:
            await self._check_timeout_and_transition_to_half_open(endpoint_id, stats)
            
            # Re-check state after potential transition
            if stats.state == CircuitBreakerState.OPEN:
                raise CircuitBreakerError(
                    endpoint_id,
                    CircuitBreakerState.OPEN,
                    f"Circuit breaker OPEN for endpoint {endpoint_id}. "
                    f"Failure rate: {stats.failure_rate:.1f}%, "
                    f"Time in state: {stats.get_time_in_current_state_seconds():.1f}s"
                )
        
        # Limit concurrent requests in half-open state
        if stats.state == CircuitBreakerState.HALF_OPEN:
            current_recovery_count = self._recovery_counters.get(endpoint_id, 0)
            if current_recovery_count >= self._config.max_recovery_requests:
                raise CircuitBreakerError(
                    endpoint_id,
                    CircuitBreakerState.HALF_OPEN,
                    f"Circuit breaker HALF_OPEN for endpoint {endpoint_id}. "
                    f"Recovery limit reached: {current_recovery_count}/{self._config.max_recovery_requests}"
                )
            
            self._recovery_counters[endpoint_id] = current_recovery_count + 1
        
        # Execute operation with failure tracking
        start_time = datetime.now(timezone.utc)
        try:
            result = await asyncio.wait_for(
                operation(),
                timeout=self._config.recovery_timeout_seconds
            )
            
            # Record success
            await self._record_success(endpoint_id, stats, start_time)
            
            logger.debug(f"Circuit breaker SUCCESS for endpoint {endpoint_id} operation {operation_name}")
            return result
            
        except asyncio.TimeoutError:
            # Record timeout as failure
            await self._record_failure(
                endpoint_id, 
                stats, 
                start_time, 
                f"Operation timeout after {self._config.recovery_timeout_seconds}s"
            )
            raise
            
        except Exception as e:
            # Record operation failure
            await self._record_failure(endpoint_id, stats, start_time, str(e))
            raise
    
    async def _get_or_create_circuit_breaker(self, endpoint_id: WebhookEndpointId) -> CircuitBreakerStats:
        """Get or create circuit breaker stats for endpoint."""
        if endpoint_id not in self._circuit_breakers:
            # Create new circuit breaker
            self._circuit_breakers[endpoint_id] = CircuitBreakerStats(
                endpoint_id=endpoint_id,
                state=CircuitBreakerState.CLOSED
            )
            self._locks[endpoint_id] = asyncio.Lock()
            self._recovery_counters[endpoint_id] = 0
            
            logger.info(f"Created new circuit breaker for endpoint {endpoint_id}")
        
        return self._circuit_breakers[endpoint_id]
    
    async def _record_success(
        self, 
        endpoint_id: WebhookEndpointId, 
        stats: CircuitBreakerStats,
        start_time: datetime
    ) -> None:
        """Record successful operation and update circuit breaker state."""
        async with self._locks[endpoint_id]:
            stats.success_count += 1
            stats.total_requests += 1
            stats.last_success_time = datetime.now(timezone.utc)
            
            duration_ms = (stats.last_success_time - start_time).total_seconds() * 1000
            
            # Handle state transitions on success
            if stats.state == CircuitBreakerState.HALF_OPEN:
                recovery_successes = stats.success_count
                if recovery_successes >= self._config.recovery_success_threshold:
                    # Close circuit after sufficient successful recoveries
                    await self._transition_to_closed(endpoint_id, stats)
                    logger.info(
                        f"Circuit breaker CLOSED for endpoint {endpoint_id} after "
                        f"{recovery_successes} successful recovery attempts"
                    )
            
            elif stats.state == CircuitBreakerState.CLOSED:
                # Reset failure count on success in closed state
                if stats.failure_count > 0:
                    logger.debug(
                        f"Circuit breaker reset failure count for endpoint {endpoint_id} "
                        f"after successful operation ({duration_ms:.1f}ms)"
                    )
                    # Keep partial failure count for trend analysis, but reduce impact
                    stats.failure_count = max(0, stats.failure_count - 1)
    
    async def _record_failure(
        self,
        endpoint_id: WebhookEndpointId,
        stats: CircuitBreakerStats,
        start_time: datetime,
        error_message: str
    ) -> None:
        """Record failed operation and update circuit breaker state."""
        async with self._locks[endpoint_id]:
            stats.failure_count += 1
            stats.total_requests += 1
            stats.last_failure_time = datetime.now(timezone.utc)
            
            duration_ms = (stats.last_failure_time - start_time).total_seconds() * 1000
            
            logger.warning(
                f"Circuit breaker FAILURE for endpoint {endpoint_id}: {error_message} "
                f"({duration_ms:.1f}ms). Failures: {stats.failure_count}/{stats.total_requests}"
            )
            
            # Check if circuit should be opened
            should_open = self._should_open_circuit(stats)
            
            if should_open and stats.state != CircuitBreakerState.OPEN:
                await self._transition_to_open(endpoint_id, stats)
                logger.error(
                    f"Circuit breaker OPENED for endpoint {endpoint_id}. "
                    f"Failure threshold exceeded: {stats.failure_count} failures, "
                    f"{stats.failure_rate:.1f}% failure rate"
                )
            
            elif stats.state == CircuitBreakerState.HALF_OPEN:
                # Failure in half-open state -> back to open
                await self._transition_to_open(endpoint_id, stats)
                logger.warning(
                    f"Circuit breaker returned to OPEN for endpoint {endpoint_id} "
                    f"due to failure during recovery attempt"
                )
    
    def _should_open_circuit(self, stats: CircuitBreakerStats) -> bool:
        """Determine if circuit should be opened based on failure criteria."""
        # Check absolute failure threshold
        if stats.failure_count >= self._config.failure_threshold:
            return True
        
        # Check failure rate threshold (only if minimum requests met)
        if (stats.total_requests >= self._config.minimum_requests and 
            stats.failure_rate >= self._config.failure_rate_threshold):
            return True
        
        return False
    
    async def _transition_to_open(self, endpoint_id: WebhookEndpointId, stats: CircuitBreakerStats) -> None:
        """Transition circuit breaker to OPEN state."""
        stats.state = CircuitBreakerState.OPEN
        stats.state_changed_time = datetime.now(timezone.utc)
        self._recovery_counters[endpoint_id] = 0
        
        # Optionally reset counts to start fresh monitoring when circuit reopens
        # stats.reset_counts()
    
    async def _transition_to_half_open(self, endpoint_id: WebhookEndpointId, stats: CircuitBreakerStats) -> None:
        """Transition circuit breaker to HALF_OPEN state for recovery testing."""
        stats.state = CircuitBreakerState.HALF_OPEN
        stats.state_changed_time = datetime.now(timezone.utc)
        stats.recovery_start_time = datetime.now(timezone.utc)
        self._recovery_counters[endpoint_id] = 0
        
        # Reset counts for recovery testing
        stats.reset_counts()
        
        logger.info(f"Circuit breaker transitioned to HALF_OPEN for endpoint {endpoint_id} - starting recovery test")
    
    async def _transition_to_closed(self, endpoint_id: WebhookEndpointId, stats: CircuitBreakerStats) -> None:
        """Transition circuit breaker to CLOSED state."""
        stats.state = CircuitBreakerState.CLOSED
        stats.state_changed_time = datetime.now(timezone.utc)
        stats.recovery_start_time = None
        self._recovery_counters[endpoint_id] = 0
        
        # Reset counts for fresh monitoring
        stats.reset_counts()
    
    async def _check_timeout_and_transition_to_half_open(
        self, 
        endpoint_id: WebhookEndpointId, 
        stats: CircuitBreakerStats
    ) -> None:
        """Check if circuit should transition from OPEN to HALF_OPEN based on timeout."""
        if stats.state != CircuitBreakerState.OPEN:
            return
        
        time_in_open_state = stats.get_time_in_current_state_seconds()
        
        if time_in_open_state >= self._config.timeout_seconds:
            await self._transition_to_half_open(endpoint_id, stats)
    
    async def get_circuit_breaker_stats(self, endpoint_id: WebhookEndpointId) -> Optional[CircuitBreakerStats]:
        """Get current circuit breaker statistics for an endpoint.
        
        Args:
            endpoint_id: Webhook endpoint identifier
            
        Returns:
            CircuitBreakerStats if exists, None otherwise
        """
        return self._circuit_breakers.get(endpoint_id)
    
    async def get_all_circuit_breaker_stats(self) -> Dict[WebhookEndpointId, CircuitBreakerStats]:
        """Get circuit breaker statistics for all endpoints.
        
        Returns:
            Dictionary mapping endpoint IDs to their circuit breaker stats
        """
        return self._circuit_breakers.copy()
    
    async def reset_circuit_breaker(self, endpoint_id: WebhookEndpointId) -> bool:
        """Reset circuit breaker for an endpoint to CLOSED state.
        
        Args:
            endpoint_id: Webhook endpoint identifier
            
        Returns:
            True if reset successful, False if endpoint not found
        """
        if endpoint_id not in self._circuit_breakers:
            return False
        
        async with self._locks[endpoint_id]:
            stats = self._circuit_breakers[endpoint_id]
            await self._transition_to_closed(endpoint_id, stats)
            logger.info(f"Circuit breaker manually reset for endpoint {endpoint_id}")
            return True
    
    async def force_open_circuit_breaker(self, endpoint_id: WebhookEndpointId) -> bool:
        """Force circuit breaker to OPEN state for an endpoint.
        
        Args:
            endpoint_id: Webhook endpoint identifier
            
        Returns:
            True if operation successful, False if endpoint not found
        """
        stats = await self._get_or_create_circuit_breaker(endpoint_id)
        
        async with self._locks[endpoint_id]:
            await self._transition_to_open(endpoint_id, stats)
            logger.warning(f"Circuit breaker manually opened for endpoint {endpoint_id}")
            return True
    
    async def cleanup_old_circuit_breakers(self, max_age_hours: int = 24) -> int:
        """Clean up circuit breakers that haven't been used recently.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of circuit breakers cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleanup_count = 0
        
        endpoints_to_remove = []
        
        for endpoint_id, stats in self._circuit_breakers.items():
            # Consider circuit breaker old if no recent activity
            last_activity = max(
                stats.last_success_time or datetime.min.replace(tzinfo=timezone.utc),
                stats.last_failure_time or datetime.min.replace(tzinfo=timezone.utc),
                stats.state_changed_time
            )
            
            if last_activity < cutoff_time:
                endpoints_to_remove.append(endpoint_id)
        
        # Remove old circuit breakers
        for endpoint_id in endpoints_to_remove:
            del self._circuit_breakers[endpoint_id]
            del self._locks[endpoint_id]
            if endpoint_id in self._recovery_counters:
                del self._recovery_counters[endpoint_id]
            cleanup_count += 1
            
            logger.info(f"Cleaned up old circuit breaker for endpoint {endpoint_id}")
        
        if cleanup_count > 0:
            logger.info(f"Circuit breaker cleanup complete: removed {cleanup_count} old circuit breakers")
        
        return cleanup_count
    
    def get_circuit_breaker_summary(self) -> Dict[str, Any]:
        """Get summary of all circuit breakers for monitoring.
        
        Returns:
            Dictionary with circuit breaker summary statistics
        """
        total_breakers = len(self._circuit_breakers)
        state_counts = {
            CircuitBreakerState.CLOSED: 0,
            CircuitBreakerState.OPEN: 0,
            CircuitBreakerState.HALF_OPEN: 0
        }
        
        total_requests = 0
        total_failures = 0
        
        for stats in self._circuit_breakers.values():
            state_counts[stats.state] += 1
            total_requests += stats.total_requests
            total_failures += stats.failure_count
        
        overall_failure_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "total_circuit_breakers": total_breakers,
            "states": {
                "closed": state_counts[CircuitBreakerState.CLOSED],
                "open": state_counts[CircuitBreakerState.OPEN], 
                "half_open": state_counts[CircuitBreakerState.HALF_OPEN]
            },
            "overall_stats": {
                "total_requests": total_requests,
                "total_failures": total_failures,
                "overall_failure_rate": round(overall_failure_rate, 2)
            },
            "config": {
                "failure_threshold": self._config.failure_threshold,
                "failure_rate_threshold": self._config.failure_rate_threshold,
                "timeout_seconds": self._config.timeout_seconds
            }
        }


# Global circuit breaker service instance
_circuit_breaker_service: Optional[WebhookCircuitBreakerService] = None

def get_webhook_circuit_breaker_service() -> WebhookCircuitBreakerService:
    """Get the global webhook circuit breaker service instance.
    
    Returns:
        WebhookCircuitBreakerService: Singleton circuit breaker service
    """
    global _circuit_breaker_service
    if _circuit_breaker_service is None:
        _circuit_breaker_service = WebhookCircuitBreakerService()
    return _circuit_breaker_service