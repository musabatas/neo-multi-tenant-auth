"""Webhook delivery metrics and monitoring service.

Provides comprehensive metrics collection, analysis, and monitoring
for webhook delivery performance, success rates, and system health.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from ....core.value_objects import WebhookEndpointId, EventId
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.webhook_delivery import DeliveryStatus, WebhookDelivery
from ..entities.protocols import WebhookDeliveryRepository, WebhookEndpointRepository, EventRepository
from ..utils.queries import WEBHOOK_DELIVERY_GET_STATS
from .webhook_config_service import get_webhook_config


logger = logging.getLogger(__name__)


class MetricsPeriod(Enum):
    """Time periods for metrics aggregation."""
    LAST_HOUR = "last_hour"
    LAST_24_HOURS = "last_24_hours"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class DeliveryMetrics:
    """Delivery performance metrics for a specific period."""
    
    # Time period
    period: MetricsPeriod
    start_time: datetime
    end_time: datetime
    
    # Basic counts
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    timeout_deliveries: int = 0
    cancelled_deliveries: int = 0
    retrying_deliveries: int = 0
    
    # Performance metrics
    avg_response_time_ms: Optional[float] = None
    min_response_time_ms: Optional[int] = None
    max_response_time_ms: Optional[int] = None
    p50_response_time_ms: Optional[float] = None
    p95_response_time_ms: Optional[float] = None
    p99_response_time_ms: Optional[float] = None
    
    # Rate calculations
    success_rate: float = field(init=False)
    failure_rate: float = field(init=False)
    timeout_rate: float = field(init=False)
    
    # Throughput
    deliveries_per_hour: float = field(init=False)
    deliveries_per_minute: float = field(init=False)
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.total_deliveries > 0:
            self.success_rate = (self.successful_deliveries / self.total_deliveries) * 100
            self.failure_rate = (self.failed_deliveries / self.total_deliveries) * 100
            self.timeout_rate = (self.timeout_deliveries / self.total_deliveries) * 100
        else:
            self.success_rate = 0.0
            self.failure_rate = 0.0
            self.timeout_rate = 0.0
        
        # Calculate throughput
        duration_hours = (self.end_time - self.start_time).total_seconds() / 3600
        if duration_hours > 0:
            self.deliveries_per_hour = self.total_deliveries / duration_hours
            self.deliveries_per_minute = self.deliveries_per_hour / 60
        else:
            self.deliveries_per_hour = 0.0
            self.deliveries_per_minute = 0.0


@dataclass
class EndpointMetrics:
    """Metrics for a specific webhook endpoint."""
    
    endpoint_id: WebhookEndpointId
    endpoint_name: Optional[str] = None
    endpoint_url: Optional[str] = None
    
    # Metrics by period
    metrics: Dict[MetricsPeriod, DeliveryMetrics] = field(default_factory=dict)
    
    # Health indicators
    is_healthy: bool = True
    health_score: float = 100.0  # 0-100 score
    last_successful_delivery: Optional[datetime] = None
    consecutive_failures: int = 0
    
    # Alert status
    active_alerts: List[str] = field(default_factory=list)


@dataclass
class EventProcessingMetrics:
    """Event processing and throughput metrics."""
    
    # Event volume metrics
    total_events_created: int = 0
    total_events_processed: int = 0
    events_pending_processing: int = 0
    
    # Event throughput (events per time unit)
    events_per_second: float = 0.0
    events_per_minute: float = 0.0
    events_per_hour: float = 0.0
    
    # Event processing performance
    avg_processing_time_ms: Optional[float] = None
    p50_processing_time_ms: Optional[float] = None  
    p95_processing_time_ms: Optional[float] = None
    p99_processing_time_ms: Optional[float] = None
    
    # Event types breakdown
    top_event_types: List[Dict[str, Any]] = field(default_factory=list)
    
    # Event processing stages
    event_creation_rate_per_sec: float = 0.0
    event_delivery_rate_per_sec: float = 0.0
    event_completion_rate_per_sec: float = 0.0
    
    # Processing efficiency
    processing_efficiency_percentage: float = 0.0  # processed/created ratio
    backlog_trend: str = "stable"  # "growing", "shrinking", "stable"


@dataclass
class BusinessMetrics:
    """High-level business KPIs and metrics."""
    
    # Customer impact metrics
    successful_notification_rate: float = 0.0
    customer_impacting_failures: int = 0
    customer_satisfaction_score: float = 100.0  # Based on success rates and latency
    
    # SLA compliance metrics
    sla_compliance_percentage: float = 100.0
    sla_breach_count: int = 0
    availability_percentage: float = 100.0
    
    # Resource efficiency metrics  
    cost_per_delivery_cents: Optional[float] = None
    resource_utilization_percentage: float = 0.0
    scaling_recommendations: List[str] = field(default_factory=list)
    
    # Business growth indicators
    delivery_volume_trend: str = "stable"  # "growing", "declining", "stable"
    new_endpoints_this_period: int = 0
    churned_endpoints_this_period: int = 0


@dataclass
class SystemMetrics:
    """System-wide webhook delivery metrics with comprehensive business KPIs."""
    
    # Overall metrics by period
    metrics: Dict[MetricsPeriod, DeliveryMetrics] = field(default_factory=dict)
    
    # Event processing metrics
    event_processing: Optional[EventProcessingMetrics] = None
    
    # Business KPIs
    business_metrics: Optional[BusinessMetrics] = None
    
    # Endpoint performance
    total_endpoints: int = 0
    healthy_endpoints: int = 0
    unhealthy_endpoints: int = 0
    
    # Top performers and problematic endpoints
    top_performing_endpoints: List[EndpointMetrics] = field(default_factory=list)
    problematic_endpoints: List[EndpointMetrics] = field(default_factory=list)
    
    # System health indicators
    overall_health_score: float = 100.0
    active_alerts: List[str] = field(default_factory=list)
    
    # Resource usage
    connection_pool_usage: Optional[Dict[str, Any]] = None
    queue_depth: Optional[int] = None


@dataclass
class Alert:
    """System alert for monitoring webhook delivery issues."""
    
    id: str
    severity: AlertSeverity
    title: str
    description: str
    endpoint_id: Optional[WebhookEndpointId] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    
    def is_resolved(self) -> bool:
        """Check if alert has been resolved."""
        return self.resolved_at is not None
    
    def resolve(self) -> None:
        """Mark alert as resolved."""
        self.resolved_at = datetime.now(timezone.utc)


class WebhookMetricsService:
    """Service for webhook delivery metrics collection and analysis."""
    
    def __init__(
        self,
        delivery_repository: WebhookDeliveryRepository,
        endpoint_repository: WebhookEndpointRepository,
        event_repository: EventRepository,
        database_repository: DatabaseRepository,
        schema: str
    ):
        """Initialize metrics service.
        
        Args:
            delivery_repository: Webhook delivery repository
            endpoint_repository: Webhook endpoint repository
            event_repository: Event repository for event processing metrics
            database_repository: Database repository for raw queries
            schema: Database schema name
        """
        self._delivery_repo = delivery_repository
        self._endpoint_repo = endpoint_repository
        self._event_repo = event_repository
        self._db = database_repository
        self._schema = schema
        
        # Get configuration
        self._config = get_webhook_config()
        
        # Alert thresholds (configurable via environment)
        self._alert_thresholds = {
            "success_rate_warning": float(self._config.monitoring.success_rate_warning_threshold),
            "success_rate_critical": float(self._config.monitoring.success_rate_critical_threshold),
            "response_time_warning": float(self._config.monitoring.response_time_warning_threshold_ms),
            "response_time_critical": float(self._config.monitoring.response_time_critical_threshold_ms),
            "consecutive_failures_warning": int(self._config.monitoring.consecutive_failures_warning_threshold),
            "consecutive_failures_critical": int(self._config.monitoring.consecutive_failures_critical_threshold),
            "events_per_second_warning": float(self._config.monitoring.events_per_second_warning_threshold),
            "events_per_second_critical": float(self._config.monitoring.events_per_second_critical_threshold),
        }
        
        # Cache for metrics to avoid excessive database queries
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache TTL
    
    async def get_system_metrics(
        self, 
        include_endpoint_details: bool = True
    ) -> SystemMetrics:
        """Get comprehensive system-wide metrics.
        
        Args:
            include_endpoint_details: Include detailed endpoint metrics
            
        Returns:
            Complete system metrics including health indicators
        """
        logger.info("Generating comprehensive system metrics")
        
        system_metrics = SystemMetrics()
        
        # Get metrics for all standard periods
        for period in MetricsPeriod:
            metrics = await self._get_period_metrics(period)
            system_metrics.metrics[period] = metrics
        
        # Get comprehensive event processing metrics
        system_metrics.event_processing = await self._get_event_processing_metrics()
        
        # Get business KPIs
        system_metrics.business_metrics = await self._get_business_metrics()
        
        # Get endpoint statistics
        if include_endpoint_details:
            endpoint_metrics = await self._get_all_endpoint_metrics()
            
            # Classify endpoints by health
            healthy_endpoints = []
            unhealthy_endpoints = []
            
            for endpoint_metric in endpoint_metrics:
                if endpoint_metric.is_healthy:
                    healthy_endpoints.append(endpoint_metric)
                else:
                    unhealthy_endpoints.append(endpoint_metric)
            
            system_metrics.total_endpoints = len(endpoint_metrics)
            system_metrics.healthy_endpoints = len(healthy_endpoints)
            system_metrics.unhealthy_endpoints = len(unhealthy_endpoints)
            
            # Get top performers (by success rate and response time)
            system_metrics.top_performing_endpoints = sorted(
                healthy_endpoints,
                key=lambda e: e.health_score,
                reverse=True
            )[:10]
            
            # Get problematic endpoints (by health score)
            system_metrics.problematic_endpoints = sorted(
                endpoint_metrics,
                key=lambda e: e.health_score
            )[:10]
        
        # Calculate overall health score
        if system_metrics.total_endpoints > 0:
            health_percentage = (system_metrics.healthy_endpoints / system_metrics.total_endpoints) * 100
            system_metrics.overall_health_score = health_percentage
        
        # Generate alerts
        alerts = await self._generate_system_alerts(system_metrics)
        system_metrics.active_alerts = [alert.title for alert in alerts]
        
        logger.info(f"System metrics generated: {system_metrics.total_endpoints} endpoints, "
                   f"{system_metrics.overall_health_score:.1f}% healthy")
        
        return system_metrics
    
    async def get_endpoint_metrics(
        self, 
        endpoint_id: WebhookEndpointId,
        periods: List[MetricsPeriod] = None
    ) -> EndpointMetrics:
        """Get detailed metrics for a specific endpoint.
        
        Args:
            endpoint_id: Webhook endpoint ID
            periods: Time periods to include (default: all)
            
        Returns:
            Detailed endpoint metrics
        """
        if periods is None:
            periods = list(MetricsPeriod)
        
        logger.debug(f"Getting metrics for endpoint {endpoint_id}")
        
        # Get endpoint details
        endpoint = await self._endpoint_repo.get_by_id(endpoint_id)
        
        endpoint_metrics = EndpointMetrics(
            endpoint_id=endpoint_id,
            endpoint_name=endpoint.name if endpoint else None,
            endpoint_url=endpoint.endpoint_url if endpoint else None
        )
        
        # Get metrics for each requested period
        for period in periods:
            metrics = await self._get_endpoint_period_metrics(endpoint_id, period)
            endpoint_metrics.metrics[period] = metrics
        
        # Calculate health indicators
        await self._calculate_endpoint_health(endpoint_metrics)
        
        # Generate endpoint-specific alerts
        alerts = await self._generate_endpoint_alerts(endpoint_metrics)
        endpoint_metrics.active_alerts = [alert.title for alert in alerts]
        
        return endpoint_metrics
    
    async def get_delivery_trends(
        self, 
        hours: int = 24,
        granularity_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get delivery trends over time with specified granularity.
        
        Args:
            hours: Number of hours to analyze
            granularity_minutes: Time bucket size in minutes
            
        Returns:
            List of time-series data points with delivery counts and rates
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        # Calculate number of buckets
        total_minutes = hours * 60
        num_buckets = total_minutes // granularity_minutes
        
        trends = []
        
        for i in range(num_buckets):
            bucket_start = start_time + timedelta(minutes=i * granularity_minutes)
            bucket_end = bucket_start + timedelta(minutes=granularity_minutes)
            
            # Get deliveries in this time bucket
            bucket_metrics = await self._get_time_bucket_metrics(bucket_start, bucket_end)
            
            trends.append({
                "timestamp": bucket_start,
                "period_minutes": granularity_minutes,
                "total_deliveries": bucket_metrics.total_deliveries,
                "successful_deliveries": bucket_metrics.successful_deliveries,
                "failed_deliveries": bucket_metrics.failed_deliveries,
                "success_rate": bucket_metrics.success_rate,
                "avg_response_time_ms": bucket_metrics.avg_response_time_ms,
                "deliveries_per_minute": bucket_metrics.deliveries_per_minute
            })
        
        logger.info(f"Generated delivery trends: {len(trends)} data points over {hours} hours")
        return trends
    
    async def _get_period_metrics(self, period: MetricsPeriod) -> DeliveryMetrics:
        """Get aggregated metrics for a specific time period."""
        # Calculate time bounds
        end_time = datetime.now(timezone.utc)
        
        if period == MetricsPeriod.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
        elif period == MetricsPeriod.LAST_24_HOURS:
            start_time = end_time - timedelta(hours=24)
        elif period == MetricsPeriod.LAST_7_DAYS:
            start_time = end_time - timedelta(days=7)
        elif period == MetricsPeriod.LAST_30_DAYS:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=24)  # Default to 24 hours
        
        return await self._get_time_bucket_metrics(start_time, end_time, period)
    
    async def _get_time_bucket_metrics(
        self, 
        start_time: datetime, 
        end_time: datetime,
        period: MetricsPeriod = None
    ) -> DeliveryMetrics:
        """Get metrics for a specific time bucket."""
        cache_key = f"metrics_{start_time.isoformat()}_{end_time.isoformat()}"
        
        # Check cache first
        if cache_key in self._metrics_cache:
            cached_data, cached_time = self._metrics_cache[cache_key]
            if datetime.now(timezone.utc) - cached_time < self._cache_ttl:
                return cached_data
        
        # Query delivery statistics
        query = """
        SELECT 
            COUNT(*) as total_deliveries,
            COUNT(CASE WHEN delivery_status = 'success' THEN 1 END) as successful_deliveries,
            COUNT(CASE WHEN delivery_status = 'failed' THEN 1 END) as failed_deliveries,
            COUNT(CASE WHEN delivery_status = 'timeout' THEN 1 END) as timeout_deliveries,
            COUNT(CASE WHEN delivery_status = 'cancelled' THEN 1 END) as cancelled_deliveries,
            COUNT(CASE WHEN delivery_status = 'retrying' THEN 1 END) as retrying_deliveries,
            AVG(response_time_ms) as avg_response_time_ms,
            MIN(response_time_ms) as min_response_time_ms,
            MAX(response_time_ms) as max_response_time_ms,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY response_time_ms) as p50_response_time_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) as p95_response_time_ms,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) as p99_response_time_ms
        FROM {schema}.webhook_deliveries 
        WHERE attempted_at >= $1 AND attempted_at <= $2
        """.format(schema=self._schema)
        
        row = await self._db.fetchrow(query, start_time, end_time)
        
        if not row or row["total_deliveries"] == 0:
            metrics = DeliveryMetrics(
                period=period or MetricsPeriod.LAST_HOUR,
                start_time=start_time,
                end_time=end_time
            )
        else:
            metrics = DeliveryMetrics(
                period=period or MetricsPeriod.LAST_HOUR,
                start_time=start_time,
                end_time=end_time,
                total_deliveries=row["total_deliveries"] or 0,
                successful_deliveries=row["successful_deliveries"] or 0,
                failed_deliveries=row["failed_deliveries"] or 0,
                timeout_deliveries=row["timeout_deliveries"] or 0,
                cancelled_deliveries=row["cancelled_deliveries"] or 0,
                retrying_deliveries=row["retrying_deliveries"] or 0,
                avg_response_time_ms=float(row["avg_response_time_ms"]) if row["avg_response_time_ms"] else None,
                min_response_time_ms=row["min_response_time_ms"],
                max_response_time_ms=row["max_response_time_ms"],
                p50_response_time_ms=float(row["p50_response_time_ms"]) if row["p50_response_time_ms"] else None,
                p95_response_time_ms=float(row["p95_response_time_ms"]) if row["p95_response_time_ms"] else None,
                p99_response_time_ms=float(row["p99_response_time_ms"]) if row["p99_response_time_ms"] else None,
            )
        
        # Cache the result
        self._metrics_cache[cache_key] = (metrics, datetime.now(timezone.utc))
        
        return metrics
    
    async def _get_endpoint_period_metrics(
        self, 
        endpoint_id: WebhookEndpointId, 
        period: MetricsPeriod
    ) -> DeliveryMetrics:
        """Get metrics for a specific endpoint and period."""
        # Calculate time bounds
        end_time = datetime.now(timezone.utc)
        
        if period == MetricsPeriod.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
        elif period == MetricsPeriod.LAST_24_HOURS:
            start_time = end_time - timedelta(hours=24)
        elif period == MetricsPeriod.LAST_7_DAYS:
            start_time = end_time - timedelta(days=7)
        elif period == MetricsPeriod.LAST_30_DAYS:
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(hours=24)
        
        # Query endpoint-specific statistics
        query = """
        SELECT 
            COUNT(*) as total_deliveries,
            COUNT(CASE WHEN delivery_status = 'success' THEN 1 END) as successful_deliveries,
            COUNT(CASE WHEN delivery_status = 'failed' THEN 1 END) as failed_deliveries,
            COUNT(CASE WHEN delivery_status = 'timeout' THEN 1 END) as timeout_deliveries,
            COUNT(CASE WHEN delivery_status = 'cancelled' THEN 1 END) as cancelled_deliveries,
            COUNT(CASE WHEN delivery_status = 'retrying' THEN 1 END) as retrying_deliveries,
            AVG(response_time_ms) as avg_response_time_ms,
            MIN(response_time_ms) as min_response_time_ms,
            MAX(response_time_ms) as max_response_time_ms
        FROM {schema}.webhook_deliveries 
        WHERE webhook_endpoint_id = $1 
        AND attempted_at >= $2 AND attempted_at <= $3
        """.format(schema=self._schema)
        
        row = await self._db.fetchrow(query, endpoint_id.value, start_time, end_time)
        
        if not row or row["total_deliveries"] == 0:
            return DeliveryMetrics(
                period=period,
                start_time=start_time,
                end_time=end_time
            )
        
        return DeliveryMetrics(
            period=period,
            start_time=start_time,
            end_time=end_time,
            total_deliveries=row["total_deliveries"] or 0,
            successful_deliveries=row["successful_deliveries"] or 0,
            failed_deliveries=row["failed_deliveries"] or 0,
            timeout_deliveries=row["timeout_deliveries"] or 0,
            cancelled_deliveries=row["cancelled_deliveries"] or 0,
            retrying_deliveries=row["retrying_deliveries"] or 0,
            avg_response_time_ms=float(row["avg_response_time_ms"]) if row["avg_response_time_ms"] else None,
            min_response_time_ms=row["min_response_time_ms"],
            max_response_time_ms=row["max_response_time_ms"],
        )
    
    async def _get_all_endpoint_metrics(self) -> List[EndpointMetrics]:
        """Get metrics for all webhook endpoints."""
        # Get all active endpoints
        active_endpoints = await self._endpoint_repo.get_active_endpoints()
        
        # Get metrics for each endpoint (focus on last 24 hours for efficiency)
        endpoint_metrics = []
        
        for endpoint in active_endpoints:
            metrics = await self.get_endpoint_metrics(
                endpoint.id, 
                [MetricsPeriod.LAST_24_HOURS]
            )
            endpoint_metrics.append(metrics)
        
        return endpoint_metrics
    
    async def _calculate_endpoint_health(self, endpoint_metrics: EndpointMetrics) -> None:
        """Calculate health indicators for an endpoint."""
        # Get 24-hour metrics for health calculation
        day_metrics = endpoint_metrics.metrics.get(MetricsPeriod.LAST_24_HOURS)
        if not day_metrics:
            endpoint_metrics.is_healthy = False
            endpoint_metrics.health_score = 0.0
            return
        
        # Calculate health score based on multiple factors
        health_score = 100.0
        
        # Success rate impact (40% of score)
        if day_metrics.total_deliveries > 0:
            success_rate_score = (day_metrics.success_rate / 100) * 40
            health_score = success_rate_score
        else:
            health_score = 50.0  # Neutral score if no deliveries
        
        # Response time impact (30% of score)
        if day_metrics.avg_response_time_ms:
            if day_metrics.avg_response_time_ms < 1000:  # < 1s is excellent
                response_time_score = 30.0
            elif day_metrics.avg_response_time_ms < 3000:  # < 3s is good
                response_time_score = 25.0
            elif day_metrics.avg_response_time_ms < 5000:  # < 5s is acceptable
                response_time_score = 15.0
            else:  # > 5s is poor
                response_time_score = 5.0
            
            health_score += response_time_score
        else:
            health_score += 15.0  # Neutral score if no response time data
        
        # Failure rate penalty (30% of score)
        failure_penalty = (day_metrics.failure_rate / 100) * 30
        health_score += (30.0 - failure_penalty)
        
        # Ensure score is between 0 and 100
        health_score = max(0.0, min(100.0, health_score))
        
        endpoint_metrics.health_score = health_score
        endpoint_metrics.is_healthy = health_score >= 70.0  # Healthy threshold
        
        # Get last successful delivery time
        query = """
        SELECT MAX(attempted_at) as last_success
        FROM {schema}.webhook_deliveries 
        WHERE webhook_endpoint_id = $1 AND delivery_status = 'success'
        """.format(schema=self._schema)
        
        row = await self._db.fetchrow(query, endpoint_metrics.endpoint_id.value)
        if row and row["last_success"]:
            endpoint_metrics.last_successful_delivery = row["last_success"]
        
        # Get consecutive failures count
        query = """
        SELECT COUNT(*) as consecutive_failures
        FROM {schema}.webhook_deliveries 
        WHERE webhook_endpoint_id = $1 
        AND attempted_at > COALESCE(
            (SELECT MAX(attempted_at) FROM {schema}.webhook_deliveries 
             WHERE webhook_endpoint_id = $1 AND delivery_status = 'success'), 
            '1970-01-01'::timestamp
        )
        AND delivery_status IN ('failed', 'timeout', 'cancelled')
        """.format(schema=self._schema)
        
        row = await self._db.fetchrow(query, endpoint_metrics.endpoint_id.value)
        if row:
            endpoint_metrics.consecutive_failures = row["consecutive_failures"] or 0
    
    async def _generate_system_alerts(self, system_metrics: SystemMetrics) -> List[Alert]:
        """Generate system-wide alerts based on metrics."""
        alerts = []
        
        # Get 24-hour metrics for alerting
        day_metrics = system_metrics.metrics.get(MetricsPeriod.LAST_24_HOURS)
        if not day_metrics:
            return alerts
        
        # System-wide success rate alerts
        if day_metrics.total_deliveries > 0:
            if day_metrics.success_rate < self._alert_thresholds["success_rate_critical"]:
                alerts.append(Alert(
                    id="system_success_rate_critical",
                    severity=AlertSeverity.CRITICAL,
                    title="Critical: System-wide Success Rate Low",
                    description=f"System success rate is {day_metrics.success_rate:.1f}% "
                              f"(threshold: {self._alert_thresholds['success_rate_critical']}%)",
                    metric_value=day_metrics.success_rate,
                    threshold=self._alert_thresholds["success_rate_critical"]
                ))
            elif day_metrics.success_rate < self._alert_thresholds["success_rate_warning"]:
                alerts.append(Alert(
                    id="system_success_rate_warning",
                    severity=AlertSeverity.WARNING,
                    title="Warning: System-wide Success Rate Low",
                    description=f"System success rate is {day_metrics.success_rate:.1f}% "
                              f"(threshold: {self._alert_thresholds['success_rate_warning']}%)",
                    metric_value=day_metrics.success_rate,
                    threshold=self._alert_thresholds["success_rate_warning"]
                ))
        
        # Response time alerts
        if day_metrics.avg_response_time_ms:
            if day_metrics.avg_response_time_ms > self._alert_thresholds["response_time_critical"]:
                alerts.append(Alert(
                    id="system_response_time_critical",
                    severity=AlertSeverity.CRITICAL,
                    title="Critical: High Response Times",
                    description=f"Average response time is {day_metrics.avg_response_time_ms:.0f}ms "
                              f"(threshold: {self._alert_thresholds['response_time_critical']}ms)",
                    metric_value=day_metrics.avg_response_time_ms,
                    threshold=self._alert_thresholds["response_time_critical"]
                ))
            elif day_metrics.avg_response_time_ms > self._alert_thresholds["response_time_warning"]:
                alerts.append(Alert(
                    id="system_response_time_warning",
                    severity=AlertSeverity.WARNING,
                    title="Warning: High Response Times",
                    description=f"Average response time is {day_metrics.avg_response_time_ms:.0f}ms "
                              f"(threshold: {self._alert_thresholds['response_time_warning']}ms)",
                    metric_value=day_metrics.avg_response_time_ms,
                    threshold=self._alert_thresholds["response_time_warning"]
                ))
        
        # Endpoint health alerts
        unhealthy_percentage = (system_metrics.unhealthy_endpoints / max(1, system_metrics.total_endpoints)) * 100
        if unhealthy_percentage > 25:  # More than 25% unhealthy
            alerts.append(Alert(
                id="system_endpoint_health_critical",
                severity=AlertSeverity.CRITICAL,
                title="Critical: Many Unhealthy Endpoints",
                description=f"{system_metrics.unhealthy_endpoints} of {system_metrics.total_endpoints} "
                          f"endpoints are unhealthy ({unhealthy_percentage:.1f}%)",
                metric_value=unhealthy_percentage,
                threshold=25.0
            ))
        elif unhealthy_percentage > 10:  # More than 10% unhealthy
            alerts.append(Alert(
                id="system_endpoint_health_warning",
                severity=AlertSeverity.WARNING,
                title="Warning: Some Unhealthy Endpoints",
                description=f"{system_metrics.unhealthy_endpoints} of {system_metrics.total_endpoints} "
                          f"endpoints are unhealthy ({unhealthy_percentage:.1f}%)",
                metric_value=unhealthy_percentage,
                threshold=10.0
            ))
        
        return alerts
    
    async def _generate_endpoint_alerts(self, endpoint_metrics: EndpointMetrics) -> List[Alert]:
        """Generate alerts for a specific endpoint."""
        alerts = []
        
        # Get 24-hour metrics for alerting
        day_metrics = endpoint_metrics.metrics.get(MetricsPeriod.LAST_24_HOURS)
        if not day_metrics:
            return alerts
        
        endpoint_id = endpoint_metrics.endpoint_id
        
        # Consecutive failures alert
        if endpoint_metrics.consecutive_failures >= self._alert_thresholds["consecutive_failures_critical"]:
            alerts.append(Alert(
                id=f"endpoint_{endpoint_id}_failures_critical",
                severity=AlertSeverity.CRITICAL,
                title=f"Critical: Endpoint {endpoint_metrics.endpoint_name or 'Unknown'} Consecutive Failures",
                description=f"Endpoint has {endpoint_metrics.consecutive_failures} consecutive failures",
                endpoint_id=endpoint_id,
                metric_value=endpoint_metrics.consecutive_failures,
                threshold=self._alert_thresholds["consecutive_failures_critical"]
            ))
        elif endpoint_metrics.consecutive_failures >= self._alert_thresholds["consecutive_failures_warning"]:
            alerts.append(Alert(
                id=f"endpoint_{endpoint_id}_failures_warning",
                severity=AlertSeverity.WARNING,
                title=f"Warning: Endpoint {endpoint_metrics.endpoint_name or 'Unknown'} Multiple Failures",
                description=f"Endpoint has {endpoint_metrics.consecutive_failures} consecutive failures",
                endpoint_id=endpoint_id,
                metric_value=endpoint_metrics.consecutive_failures,
                threshold=self._alert_thresholds["consecutive_failures_warning"]
            ))
        
        # Endpoint-specific success rate alerts
        if day_metrics.total_deliveries > 0 and day_metrics.success_rate < self._alert_thresholds["success_rate_warning"]:
            severity = AlertSeverity.CRITICAL if day_metrics.success_rate < self._alert_thresholds["success_rate_critical"] else AlertSeverity.WARNING
            alerts.append(Alert(
                id=f"endpoint_{endpoint_id}_success_rate_{severity.value}",
                severity=severity,
                title=f"{severity.value.title()}: Endpoint {endpoint_metrics.endpoint_name or 'Unknown'} Low Success Rate",
                description=f"Endpoint success rate is {day_metrics.success_rate:.1f}% over the last 24 hours",
                endpoint_id=endpoint_id,
                metric_value=day_metrics.success_rate,
                threshold=self._alert_thresholds["success_rate_warning"]
            ))
        
        return alerts
    
    async def _get_event_processing_metrics(self) -> EventProcessingMetrics:
        """Get comprehensive event processing and throughput metrics."""
        try:
            # Get event counts
            total_events_created = await self._get_total_events_created()
            total_events_processed = await self._get_total_events_processed() 
            events_pending_processing = await self._event_repo.count_unprocessed()
            
            # Calculate processing rates over the last hour
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=1)
            
            events_created_last_hour = await self._get_events_created_in_period(start_time, end_time)
            events_processed_last_hour = await self._get_events_processed_in_period(start_time, end_time)
            deliveries_completed_last_hour = await self._get_deliveries_completed_in_period(start_time, end_time)
            
            # Calculate rates
            events_per_second = events_processed_last_hour / 3600.0 if events_processed_last_hour > 0 else 0.0
            events_per_minute = events_per_second * 60.0
            events_per_hour = events_processed_last_hour
            
            event_creation_rate_per_sec = events_created_last_hour / 3600.0 if events_created_last_hour > 0 else 0.0
            event_delivery_rate_per_sec = deliveries_completed_last_hour / 3600.0 if deliveries_completed_last_hour > 0 else 0.0
            event_completion_rate_per_sec = events_per_second
            
            # Get processing time statistics
            processing_times = await self._get_event_processing_times()
            
            # Get top event types
            top_event_types = await self._get_top_event_types()
            
            # Calculate efficiency metrics
            processing_efficiency = (total_events_processed / max(total_events_created, 1)) * 100 if total_events_created > 0 else 100.0
            
            # Determine backlog trend
            backlog_trend = await self._determine_backlog_trend()
            
            return EventProcessingMetrics(
                total_events_created=total_events_created,
                total_events_processed=total_events_processed,
                events_pending_processing=events_pending_processing,
                events_per_second=events_per_second,
                events_per_minute=events_per_minute,
                events_per_hour=events_per_hour,
                avg_processing_time_ms=processing_times.get("avg"),
                p50_processing_time_ms=processing_times.get("p50"),
                p95_processing_time_ms=processing_times.get("p95"),
                p99_processing_time_ms=processing_times.get("p99"),
                top_event_types=top_event_types,
                event_creation_rate_per_sec=event_creation_rate_per_sec,
                event_delivery_rate_per_sec=event_delivery_rate_per_sec,
                event_completion_rate_per_sec=event_completion_rate_per_sec,
                processing_efficiency_percentage=processing_efficiency,
                backlog_trend=backlog_trend
            )
            
        except Exception as e:
            logger.error(f"Error calculating event processing metrics: {e}")
            return EventProcessingMetrics()
    
    async def _get_business_metrics(self) -> BusinessMetrics:
        """Calculate high-level business KPIs and metrics."""
        try:
            # Get 24-hour delivery metrics for business calculations
            day_metrics = await self._get_period_metrics(MetricsPeriod.LAST_24_HOURS)
            
            # Calculate customer impact metrics
            successful_notification_rate = day_metrics.success_rate if day_metrics.total_deliveries > 0 else 100.0
            customer_impacting_failures = day_metrics.failed_deliveries + day_metrics.timeout_deliveries
            
            # Calculate customer satisfaction score based on success rate and response time
            customer_satisfaction_score = await self._calculate_customer_satisfaction_score(day_metrics)
            
            # Calculate SLA compliance metrics
            sla_compliance_percentage = await self._calculate_sla_compliance()
            sla_breach_count = await self._get_sla_breach_count()
            availability_percentage = await self._calculate_availability_percentage()
            
            # Resource efficiency metrics
            cost_per_delivery = await self._calculate_cost_per_delivery()
            resource_utilization = await self._calculate_resource_utilization()
            scaling_recommendations = await self._generate_scaling_recommendations(day_metrics)
            
            # Business growth indicators
            delivery_volume_trend = await self._calculate_delivery_volume_trend()
            new_endpoints_count = await self._get_new_endpoints_count()
            churned_endpoints_count = await self._get_churned_endpoints_count()
            
            return BusinessMetrics(
                successful_notification_rate=successful_notification_rate,
                customer_impacting_failures=customer_impacting_failures,
                customer_satisfaction_score=customer_satisfaction_score,
                sla_compliance_percentage=sla_compliance_percentage,
                sla_breach_count=sla_breach_count,
                availability_percentage=availability_percentage,
                cost_per_delivery_cents=cost_per_delivery,
                resource_utilization_percentage=resource_utilization,
                scaling_recommendations=scaling_recommendations,
                delivery_volume_trend=delivery_volume_trend,
                new_endpoints_this_period=new_endpoints_count,
                churned_endpoints_this_period=churned_endpoints_count
            )
            
        except Exception as e:
            logger.error(f"Error calculating business metrics: {e}")
            return BusinessMetrics()
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics for dashboards.
        
        Returns:
            Dict with current real-time metrics including events/second,
            delivery latency, success rates, and system health indicators
        """
        try:
            current_time = datetime.now(timezone.utc)
            
            # Get metrics for the last 5 minutes for real-time view
            five_minutes_ago = current_time - timedelta(minutes=5)
            
            # Real-time event processing
            recent_events = await self._get_events_processed_in_period(five_minutes_ago, current_time)
            events_per_second_realtime = recent_events / 300.0  # 5 minutes = 300 seconds
            
            # Real-time delivery metrics
            recent_deliveries = await self._get_deliveries_completed_in_period(five_minutes_ago, current_time)
            deliveries_per_second_realtime = recent_deliveries / 300.0
            
            # Current queue depths and system status
            unprocessed_events = await self._event_repo.count_unprocessed()
            processing_events = await self._event_repo.count_processing()
            
            # Average response time for recent deliveries
            recent_avg_response_time = await self._get_avg_response_time_in_period(five_minutes_ago, current_time)
            
            # System health indicators
            active_endpoints = len(await self._endpoint_repo.get_active_endpoints())
            
            return {
                "timestamp": current_time.isoformat(),
                "real_time_performance": {
                    "events_per_second": round(events_per_second_realtime, 2),
                    "deliveries_per_second": round(deliveries_per_second_realtime, 2),
                    "avg_response_time_ms": recent_avg_response_time,
                    "events_pending": unprocessed_events,
                    "events_processing": processing_events,
                },
                "system_status": {
                    "total_active_endpoints": active_endpoints,
                    "queue_health": "healthy" if unprocessed_events < 1000 else "warning" if unprocessed_events < 5000 else "critical",
                    "processing_health": "healthy" if events_per_second_realtime > 1 else "warning" if events_per_second_realtime > 0 else "critical"
                },
                "capacity_indicators": {
                    "current_load_percentage": min(100.0, (events_per_second_realtime / self._alert_thresholds["events_per_second_warning"]) * 100),
                    "queue_capacity_percentage": min(100.0, (unprocessed_events / 10000) * 100),  # Assuming 10k queue capacity
                    "response_time_health": "healthy" if (recent_avg_response_time or 0) < 1000 else "warning" if (recent_avg_response_time or 0) < 3000 else "critical"
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting real-time metrics: {e}")
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e),
                "real_time_performance": {},
                "system_status": {},
                "capacity_indicators": {}
            }
    
    # Helper methods for business metrics calculations
    async def _get_total_events_created(self) -> int:
        """Get total number of events created."""
        query = f"SELECT COUNT(*) FROM {self._schema}.webhook_events"
        row = await self._db.fetchrow(query)
        return row[0] if row else 0
    
    async def _get_total_events_processed(self) -> int:
        """Get total number of events processed."""
        query = f"SELECT COUNT(*) FROM {self._schema}.webhook_events WHERE processed_at IS NOT NULL"
        row = await self._db.fetchrow(query)
        return row[0] if row else 0
    
    async def _calculate_customer_satisfaction_score(self, metrics: DeliveryMetrics) -> float:
        """Calculate customer satisfaction based on success rate and response time."""
        if metrics.total_deliveries == 0:
            return 100.0
        
        # Base score from success rate (70% weight)
        success_score = metrics.success_rate * 0.7
        
        # Response time score (30% weight)
        response_time_score = 30.0
        if metrics.avg_response_time_ms:
            if metrics.avg_response_time_ms <= 1000:  # <= 1s = excellent
                response_time_score = 30.0
            elif metrics.avg_response_time_ms <= 3000:  # <= 3s = good
                response_time_score = 25.0
            elif metrics.avg_response_time_ms <= 5000:  # <= 5s = acceptable
                response_time_score = 15.0
            else:  # > 5s = poor
                response_time_score = 5.0
        
        return min(100.0, success_score + response_time_score)
    
    def clear_metrics_cache(self) -> None:
        """Clear the metrics cache to force fresh data."""
        self._metrics_cache.clear()
        logger.info("Metrics cache cleared")
    
    def set_alert_threshold(self, threshold_name: str, value: float) -> None:
        """Update an alert threshold.
        
        Args:
            threshold_name: Name of the threshold to update
            value: New threshold value
        """
        if threshold_name in self._alert_thresholds:
            old_value = self._alert_thresholds[threshold_name]
            self._alert_thresholds[threshold_name] = value
            logger.info(f"Updated alert threshold '{threshold_name}' from {old_value} to {value}")
        else:
            logger.warning(f"Unknown alert threshold: {threshold_name}")
    
    def get_alert_thresholds(self) -> Dict[str, float]:
        """Get current alert thresholds."""
        return self._alert_thresholds.copy()