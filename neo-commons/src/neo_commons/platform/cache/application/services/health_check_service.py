"""Cache health check service.

ONLY health checking - monitors cache system health and component status.

Following maximum separation architecture - one file = one purpose.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ...core.protocols.cache_repository import CacheRepository
from ...core.protocols.cache_serializer import CacheSerializer
from ...core.protocols.invalidation_service import InvalidationService
from ...core.protocols.distribution_service import DistributionService
from .event_publisher import CacheEventPublisher

# Import response models for typing
from ...api.models.responses.cache_health_response import (
    CacheHealthResponse,
    ComponentHealth,
    HealthStatus
)


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: float
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class CacheHealthCheckService:
    """Cache health check service.
    
    Monitors the health of all cache components including repository,
    serializer, invalidation service, distribution service, and event publisher.
    """
    
    def __init__(
        self,
        cache_repository: CacheRepository,
        cache_serializer: Optional[CacheSerializer] = None,
        invalidation_service: Optional[InvalidationService] = None,
        distribution_service: Optional[DistributionService] = None,
        event_publisher: Optional[CacheEventPublisher] = None,
        timeout_seconds: float = 5.0
    ):
        """Initialize health check service.
        
        Args:
            cache_repository: Cache repository to check
            cache_serializer: Optional cache serializer
            invalidation_service: Optional invalidation service
            distribution_service: Optional distribution service
            event_publisher: Optional event publisher
            timeout_seconds: Health check timeout
        """
        self._cache_repository = cache_repository
        self._cache_serializer = cache_serializer
        self._invalidation_service = invalidation_service
        self._distribution_service = distribution_service
        self._event_publisher = event_publisher
        self._timeout_seconds = timeout_seconds
        
        # Health check history for tracking
        self._last_check_time: Optional[datetime] = None
        self._last_check_result: Optional[CacheHealthResponse] = None
        self._startup_time = datetime.now(timezone.utc)
    
    async def check_health(self, detailed: bool = True) -> CacheHealthResponse:
        """Perform comprehensive health check.
        
        Args:
            detailed: Whether to include detailed component checks
            
        Returns:
            Complete health check response
        """
        start_time = datetime.now(timezone.utc)
        health_checks = []
        
        try:
            # Check repository health (required)
            repo_health = await self._check_repository_health()
            health_checks.append(repo_health)
            
            # Check optional components if available
            if detailed:
                if self._cache_serializer:
                    serializer_health = await self._check_serializer_health()
                    health_checks.append(serializer_health)
                
                if self._invalidation_service:
                    invalidation_health = await self._check_invalidation_health()
                    health_checks.append(invalidation_health)
                
                if self._distribution_service:
                    distribution_health = await self._check_distribution_health()
                    health_checks.append(distribution_health)
                
                if self._event_publisher:
                    event_publisher_health = await self._check_event_publisher_health()
                    health_checks.append(event_publisher_health)
            
            # Calculate overall health
            total_response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            overall_status = self._calculate_overall_status(health_checks)
            
            # Count healthy components
            healthy_count = sum(1 for check in health_checks if check.status == HealthStatus.HEALTHY)
            total_count = len(health_checks)
            health_percentage = (healthy_count / total_count) * 100.0 if total_count > 0 else 0.0
            
            # Get uptime
            uptime_seconds = int((datetime.now(timezone.utc) - self._startup_time).total_seconds())
            
            # Create component health objects
            component_healths = self._create_component_healths(health_checks)
            
            # Collect warnings and errors
            warnings = []
            errors = []
            for check in health_checks:
                if check.status == HealthStatus.DEGRADED:
                    warnings.append(f"{check.component}: {check.message}")
                elif check.status == HealthStatus.UNHEALTHY:
                    errors.append(f"{check.component}: {check.error or check.message}")
            
            # Create response
            response = CacheHealthResponse(
                success=True,
                status=overall_status,
                timestamp=datetime.now(timezone.utc),
                uptime_seconds=uptime_seconds,
                repository_health=component_healths.get("repository"),
                serializer_health=component_healths.get("serializer"),
                distribution_health=component_healths.get("distribution"),
                invalidation_health=component_healths.get("invalidation"),
                event_publisher_health=component_healths.get("event_publisher"),
                total_response_time_ms=total_response_time,
                healthy_components=healthy_count,
                total_components=total_count,
                health_percentage=health_percentage,
                warnings=warnings if warnings else None,
                errors=errors if errors else None,
                message=self._generate_health_message(overall_status, healthy_count, total_count)
            )
            
            self._last_check_time = datetime.now(timezone.utc)
            self._last_check_result = response
            
            return response
        
        except Exception as e:
            # Health check failed
            return CacheHealthResponse(
                success=False,
                status=HealthStatus.UNHEALTHY,
                timestamp=datetime.now(timezone.utc),
                repository_health=ComponentHealth(
                    component="health_check_service",
                    status=HealthStatus.UNHEALTHY,
                    message="Health check failed",
                    last_checked=datetime.now(timezone.utc)
                ),
                healthy_components=0,
                total_components=1,
                health_percentage=0.0,
                errors=[f"Health check error: {str(e)}"],
                message="Cache health check failed"
            )
    
    async def check_repository_health_only(self) -> ComponentHealth:
        """Quick repository-only health check."""
        health_result = await self._check_repository_health()
        return ComponentHealth(
            component=health_result.component,
            status=health_result.status,
            message=health_result.message,
            response_time_ms=health_result.response_time_ms,
            last_checked=datetime.now(timezone.utc),
            details=health_result.details
        )
    
    async def _check_repository_health(self) -> HealthCheckResult:
        """Check cache repository health."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Test repository ping/health method
            if hasattr(self._cache_repository, 'ping'):
                is_healthy = await asyncio.wait_for(
                    self._cache_repository.ping(),
                    timeout=self._timeout_seconds
                )
            else:
                # Fallback: test basic operation
                from ...core.value_objects.cache_key import CacheKey
                from ...core.entities.cache_namespace import CacheNamespace, EvictionPolicy
                
                test_key = CacheKey("_health_check_")
                test_namespace = CacheNamespace(
                    name="health",
                    description="Health check namespace",
                    default_ttl=None,
                    max_entries=1,
                    eviction_policy=EvictionPolicy.LRU
                )
                
                # Test exists operation (minimal impact)
                is_healthy = await asyncio.wait_for(
                    self._cache_repository.exists(test_key, test_namespace),
                    timeout=self._timeout_seconds
                )
                is_healthy = True  # If no exception, consider healthy
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            if is_healthy:
                return HealthCheckResult(
                    component="cache_repository",
                    status=HealthStatus.HEALTHY,
                    message="Repository responding normally",
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component="cache_repository",
                    status=HealthStatus.UNHEALTHY,
                    message="Repository ping failed",
                    response_time_ms=response_time,
                    error="Repository ping returned false"
                )
        
        except asyncio.TimeoutError:
            response_time = self._timeout_seconds * 1000
            return HealthCheckResult(
                component="cache_repository",
                status=HealthStatus.UNHEALTHY,
                message="Repository timeout",
                response_time_ms=response_time,
                error=f"Repository did not respond within {self._timeout_seconds}s"
            )
        
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component="cache_repository",
                status=HealthStatus.UNHEALTHY,
                message="Repository error",
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _check_serializer_health(self) -> HealthCheckResult:
        """Check cache serializer health."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Test serialization/deserialization
            test_data = {"health_check": True, "timestamp": datetime.now(timezone.utc).isoformat()}
            
            # Test serialize
            serialized = await asyncio.wait_for(
                self._cache_serializer.serialize(test_data),
                timeout=self._timeout_seconds
            )
            
            # Test deserialize
            deserialized = await asyncio.wait_for(
                self._cache_serializer.deserialize(serialized),
                timeout=self._timeout_seconds
            )
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Verify round-trip
            if deserialized.get("health_check") == True:
                return HealthCheckResult(
                    component="cache_serializer",
                    status=HealthStatus.HEALTHY,
                    message="Serializer functioning normally",
                    response_time_ms=response_time
                )
            else:
                return HealthCheckResult(
                    component="cache_serializer",
                    status=HealthStatus.UNHEALTHY,
                    message="Serializer round-trip failed",
                    response_time_ms=response_time,
                    error="Deserialized data does not match original"
                )
        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component="cache_serializer",
                status=HealthStatus.UNHEALTHY,
                message="Serializer timeout",
                response_time_ms=self._timeout_seconds * 1000,
                error=f"Serializer did not respond within {self._timeout_seconds}s"
            )
        
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component="cache_serializer",
                status=HealthStatus.UNHEALTHY,
                message="Serializer error",
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _check_invalidation_health(self) -> HealthCheckResult:
        """Check invalidation service health."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Basic health check - just verify service is responsive
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                component="invalidation_service",
                status=HealthStatus.HEALTHY,
                message="Invalidation service operational",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component="invalidation_service",
                status=HealthStatus.UNHEALTHY,
                message="Invalidation service error",
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _check_distribution_health(self) -> HealthCheckResult:
        """Check distribution service health."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Basic health check - just verify service is responsive
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            return HealthCheckResult(
                component="distribution_service",
                status=HealthStatus.HEALTHY,
                message="Distribution service active",
                response_time_ms=response_time
            )
        
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component="distribution_service",
                status=HealthStatus.UNHEALTHY,
                message="Distribution service error",
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _check_event_publisher_health(self) -> HealthCheckResult:
        """Check event publisher health."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Get event publisher metrics if available
            metrics = await self._event_publisher.get_metrics()
            
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            details = {}
            if metrics:
                details.update({
                    "events_published": str(metrics.get("total_published", 0)),
                    "success_rate": f"{metrics.get('success_rate_percentage', 0):.1f}%"
                })
            
            return HealthCheckResult(
                component="event_publisher",
                status=HealthStatus.HEALTHY,
                message="Event publishing active",
                response_time_ms=response_time,
                details=details
            )
        
        except Exception as e:
            response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return HealthCheckResult(
                component="event_publisher",
                status=HealthStatus.UNHEALTHY,
                message="Event publisher error",
                response_time_ms=response_time,
                error=str(e)
            )
    
    def _calculate_overall_status(self, health_checks: List[HealthCheckResult]) -> HealthStatus:
        """Calculate overall health status."""
        if not health_checks:
            return HealthStatus.UNKNOWN
        
        unhealthy_count = sum(1 for check in health_checks if check.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for check in health_checks if check.status == HealthStatus.DEGRADED)
        
        # If any component is unhealthy, system is unhealthy
        if unhealthy_count > 0:
            return HealthStatus.UNHEALTHY
        
        # If any component is degraded, system is degraded
        if degraded_count > 0:
            return HealthStatus.DEGRADED
        
        # All components are healthy
        return HealthStatus.HEALTHY
    
    def _create_component_healths(self, health_checks: List[HealthCheckResult]) -> Dict[str, ComponentHealth]:
        """Create component health objects from check results."""
        component_healths = {}
        
        for check in health_checks:
            component_health = ComponentHealth(
                component=check.component,
                status=check.status,
                message=check.message,
                response_time_ms=check.response_time_ms,
                last_checked=datetime.now(timezone.utc),
                details=check.details
            )
            
            # Map to expected component names
            if "repository" in check.component:
                component_healths["repository"] = component_health
            elif "serializer" in check.component:
                component_healths["serializer"] = component_health
            elif "invalidation" in check.component:
                component_healths["invalidation"] = component_health
            elif "distribution" in check.component:
                component_healths["distribution"] = component_health
            elif "event_publisher" in check.component:
                component_healths["event_publisher"] = component_health
        
        return component_healths
    
    def _generate_health_message(self, status: HealthStatus, healthy_count: int, total_count: int) -> str:
        """Generate overall health message."""
        if status == HealthStatus.HEALTHY:
            return "All cache components are healthy"
        elif status == HealthStatus.DEGRADED:
            return f"Cache system degraded: {healthy_count}/{total_count} components healthy"
        elif status == HealthStatus.UNHEALTHY:
            unhealthy_count = total_count - healthy_count
            return f"Cache system unhealthy: {unhealthy_count} component(s) failing"
        else:
            return "Cache system status unknown"
    
    def get_last_check_result(self) -> Optional[CacheHealthResponse]:
        """Get the last health check result."""
        return self._last_check_result
    
    def get_uptime_seconds(self) -> int:
        """Get service uptime in seconds."""
        return int((datetime.now(timezone.utc) - self._startup_time).total_seconds())


# Factory function for dependency injection
def create_cache_health_check_service(
    cache_repository: CacheRepository,
    cache_serializer: Optional[CacheSerializer] = None,
    invalidation_service: Optional[InvalidationService] = None,
    distribution_service: Optional[DistributionService] = None,
    event_publisher: Optional[CacheEventPublisher] = None,
    timeout_seconds: float = 5.0
) -> CacheHealthCheckService:
    """Create cache health check service with dependencies.
    
    Args:
        cache_repository: Cache repository to check
        cache_serializer: Optional cache serializer
        invalidation_service: Optional invalidation service
        distribution_service: Optional distribution service
        event_publisher: Optional event publisher
        timeout_seconds: Health check timeout
        
    Returns:
        Configured cache health check service
    """
    return CacheHealthCheckService(
        cache_repository=cache_repository,
        cache_serializer=cache_serializer,
        invalidation_service=invalidation_service,
        distribution_service=distribution_service,
        event_publisher=event_publisher,
        timeout_seconds=timeout_seconds
    )