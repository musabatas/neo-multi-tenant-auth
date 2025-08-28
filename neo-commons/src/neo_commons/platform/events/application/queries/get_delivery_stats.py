"""Get delivery statistics query for platform events infrastructure.

This module handles ONLY delivery statistics retrieval operations following maximum separation architecture.
Single responsibility: Retrieve comprehensive webhook delivery statistics including success rates, performance metrics, and analytics.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from ...core.protocols import DeliveryService
from ...core.entities import WebhookDelivery
from ...core.value_objects import WebhookEndpointId
from ...core.exceptions import WebhookDeliveryFailed
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now


@dataclass
class GetDeliveryStatsData:
    """Data required to retrieve delivery statistics.
    
    Contains all the parameters needed for comprehensive delivery statistics operations.
    Separates data from business logic following CQRS patterns.
    """
    # Filtering options
    event_type: Optional[str] = None
    endpoint_id: Optional[WebhookEndpointId] = None
    correlation_id: Optional[str] = None
    user_id: Optional[UserId] = None
    
    # Time range filtering
    time_range_hours: int = 24
    from_time: Optional[datetime] = None
    to_time: Optional[datetime] = None
    
    # Statistics configuration
    include_performance_metrics: bool = True
    include_endpoint_breakdown: bool = True
    include_error_analysis: bool = True
    include_trend_analysis: bool = False
    
    # Granularity and grouping
    group_by: str = "hour"  # hour, day, week
    endpoint_limit: int = 50  # Max endpoints to include in breakdown
    
    
@dataclass
class GetDeliveryStatsResult:
    """Result of delivery statistics retrieval operation.
    
    Contains comprehensive delivery statistics data for monitoring and analysis.
    Provides structured feedback about delivery performance and trends.
    """
    # Query metadata
    statistics_generated_at: datetime
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    data_points_analyzed: int = 0
    
    # Core delivery statistics
    total_deliveries: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    pending_deliveries: int = 0
    cancelled_deliveries: int = 0
    
    # Success and failure rates
    success_rate: float = 0.0
    failure_rate: float = 0.0
    retry_rate: float = 0.0
    cancellation_rate: float = 0.0
    
    # Performance metrics
    average_response_time_ms: Optional[int] = None
    median_response_time_ms: Optional[int] = None
    p95_response_time_ms: Optional[int] = None
    p99_response_time_ms: Optional[int] = None
    min_response_time_ms: Optional[int] = None
    max_response_time_ms: Optional[int] = None
    
    # Throughput metrics
    deliveries_per_hour: Optional[float] = None
    deliveries_per_minute: Optional[float] = None
    peak_delivery_rate: Optional[float] = None
    
    # Retry and error analysis
    total_retry_attempts: int = 0
    average_retries_per_delivery: Optional[float] = None
    max_retries_reached: int = 0
    common_error_types: Optional[Dict[str, int]] = None
    error_distribution: Optional[Dict[str, float]] = None
    
    # Endpoint performance breakdown
    endpoint_performance: Optional[List[Dict[str, Any]]] = None
    top_performing_endpoints: Optional[List[Dict[str, Any]]] = None
    underperforming_endpoints: Optional[List[Dict[str, Any]]] = None
    
    # Trend analysis (if enabled)
    hourly_trends: Optional[List[Dict[str, Any]]] = None
    daily_trends: Optional[List[Dict[str, Any]]] = None
    performance_trends: Optional[Dict[str, List[Dict[str, Any]]]] = None
    
    # Query performance
    retrieval_time_ms: Optional[int] = None
    error_message: Optional[str] = None


class GetDeliveryStatsQuery:
    """Query to retrieve comprehensive delivery statistics and performance metrics.
    
    Single responsibility: Orchestrate the retrieval of complete delivery statistics including
    success rates, performance metrics, error analysis, endpoint breakdowns, and trend data.
    Provides comprehensive delivery monitoring for operational visibility and analysis.
    
    Following enterprise query pattern with protocol-based dependencies.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    def __init__(
        self,
        delivery_service: DeliveryService
    ):
        """Initialize get delivery stats query with required dependencies.
        
        Args:
            delivery_service: Protocol for delivery operations and statistics
        """
        self._delivery_service = delivery_service
    
    async def execute(self, data: GetDeliveryStatsData) -> GetDeliveryStatsResult:
        """Execute delivery statistics retrieval query.
        
        Orchestrates the complete delivery statistics retrieval process:
        1. Validate time range and filtering parameters
        2. Retrieve core delivery statistics from service
        3. Calculate derived metrics and rates
        4. Optionally retrieve endpoint performance breakdown
        5. Optionally retrieve error analysis and trend data
        6. Return comprehensive delivery statistics
        
        Args:
            data: Delivery statistics configuration data
            
        Returns:
            GetDeliveryStatsResult with comprehensive delivery statistics
        """
        start_time = utc_now()
        
        try:
            # 1. Validate and prepare time range
            time_range_start, time_range_end = self._prepare_time_range(data)
            
            # 2. Retrieve core delivery statistics from service
            core_stats = await self._delivery_service.get_delivery_statistics(
                event_type=data.event_type,
                endpoint_id=data.endpoint_id,
                time_range_hours=data.time_range_hours,
                include_performance_metrics=data.include_performance_metrics
            )
            
            # 3. Initialize result with core statistics
            result_data = {
                "statistics_generated_at": utc_now(),
                "time_range_start": time_range_start,
                "time_range_end": time_range_end,
                "data_points_analyzed": core_stats.get("total_deliveries", 0)
            }
            
            # 4. Extract and calculate core metrics
            self._extract_core_metrics(core_stats, result_data)
            
            # 5. Optionally retrieve endpoint performance breakdown
            if data.include_endpoint_breakdown:
                endpoint_data = await self._get_endpoint_breakdown(data, core_stats)
                result_data.update(endpoint_data)
            
            # 6. Optionally retrieve error analysis
            if data.include_error_analysis:
                error_data = await self._get_error_analysis(data, core_stats)
                result_data.update(error_data)
            
            # 7. Optionally retrieve trend analysis
            if data.include_trend_analysis:
                trend_data = await self._get_trend_analysis(data)
                result_data.update(trend_data)
            
            # 8. Calculate retrieval metrics
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            result_data["retrieval_time_ms"] = retrieval_time_ms
            
            return GetDeliveryStatsResult(**result_data)
            
        except Exception as e:
            # Calculate retrieval time for failed operations
            end_time = utc_now()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            return GetDeliveryStatsResult(
                statistics_generated_at=utc_now(),
                retrieval_time_ms=retrieval_time_ms,
                error_message=f"Failed to retrieve delivery statistics: {str(e)}"
            )
    
    async def execute_simple(
        self,
        event_type: Optional[str] = None,
        time_range_hours: int = 24
    ) -> GetDeliveryStatsResult:
        """Execute simple delivery statistics retrieval with basic metrics.
        
        Convenience method for basic delivery statistics with minimal data.
        Useful for quick health checks and basic performance monitoring.
        
        Args:
            event_type: Optional event type filter
            time_range_hours: Time range for statistics
            
        Returns:
            GetDeliveryStatsResult with basic delivery statistics
        """
        data = GetDeliveryStatsData(
            event_type=event_type,
            time_range_hours=time_range_hours,
            include_performance_metrics=True,
            include_endpoint_breakdown=False,
            include_error_analysis=False,
            include_trend_analysis=False
        )
        return await self.execute(data)
    
    async def execute_endpoint_focused(
        self,
        endpoint_id: WebhookEndpointId,
        time_range_hours: int = 24
    ) -> GetDeliveryStatsResult:
        """Execute delivery statistics retrieval focused on a specific endpoint.
        
        Convenience method for endpoint-specific analysis with detailed
        performance metrics and error analysis.
        
        Args:
            endpoint_id: ID of the endpoint to analyze
            time_range_hours: Time range for statistics
            
        Returns:
            GetDeliveryStatsResult with endpoint-focused statistics
        """
        data = GetDeliveryStatsData(
            endpoint_id=endpoint_id,
            time_range_hours=time_range_hours,
            include_performance_metrics=True,
            include_endpoint_breakdown=True,
            include_error_analysis=True,
            include_trend_analysis=False
        )
        return await self.execute(data)
    
    async def execute_comprehensive(
        self,
        time_range_hours: int = 168  # 7 days
    ) -> GetDeliveryStatsResult:
        """Execute comprehensive delivery statistics with all available data.
        
        Convenience method for complete delivery analysis including all
        performance metrics, endpoint breakdowns, error analysis, and trends.
        
        Args:
            time_range_hours: Time range for comprehensive analysis
            
        Returns:
            GetDeliveryStatsResult with complete delivery statistics
        """
        data = GetDeliveryStatsData(
            time_range_hours=time_range_hours,
            include_performance_metrics=True,
            include_endpoint_breakdown=True,
            include_error_analysis=True,
            include_trend_analysis=True,
            group_by="hour" if time_range_hours <= 48 else "day"
        )
        return await self.execute(data)
    
    async def execute_error_analysis(
        self,
        time_range_hours: int = 24
    ) -> GetDeliveryStatsResult:
        """Execute delivery statistics focused on error analysis.
        
        Convenience method for error pattern analysis and failure investigation.
        
        Args:
            time_range_hours: Time range for error analysis
            
        Returns:
            GetDeliveryStatsResult with detailed error analysis
        """
        data = GetDeliveryStatsData(
            time_range_hours=time_range_hours,
            include_performance_metrics=False,
            include_endpoint_breakdown=True,
            include_error_analysis=True,
            include_trend_analysis=False
        )
        return await self.execute(data)
    
    def _prepare_time_range(self, data: GetDeliveryStatsData) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Prepare and validate time range for statistics calculation.
        
        Args:
            data: Statistics data configuration
            
        Returns:
            Tuple of start and end datetime for the analysis period
        """
        if data.from_time and data.to_time:
            return data.from_time, data.to_time
        
        end_time = utc_now()
        start_time = end_time - timedelta(hours=data.time_range_hours)
        
        return start_time, end_time
    
    def _extract_core_metrics(self, core_stats: Dict[str, Any], result_data: Dict[str, Any]) -> None:
        """Extract and calculate core delivery metrics from service statistics.
        
        Args:
            core_stats: Raw statistics from delivery service
            result_data: Result dictionary to populate
        """
        # Extract basic counters
        total = core_stats.get("total_deliveries", 0)
        successful = core_stats.get("successful_deliveries", 0)
        failed = core_stats.get("failed_deliveries", 0)
        
        result_data.update({
            "total_deliveries": total,
            "successful_deliveries": successful,
            "failed_deliveries": failed,
            "pending_deliveries": core_stats.get("pending_deliveries", 0),
            "cancelled_deliveries": core_stats.get("cancelled_deliveries", 0)
        })
        
        # Calculate rates
        if total > 0:
            result_data.update({
                "success_rate": round((successful / total) * 100, 2),
                "failure_rate": round((failed / total) * 100, 2),
                "retry_rate": round(core_stats.get("retry_rate", 0), 2),
                "cancellation_rate": round((result_data["cancelled_deliveries"] / total) * 100, 2)
            })
        
        # Extract performance metrics
        result_data.update({
            "average_response_time_ms": core_stats.get("average_response_time_ms"),
            "p95_response_time_ms": core_stats.get("p95_response_time_ms"),
            "deliveries_per_hour": core_stats.get("throughput_per_hour"),
            "total_retry_attempts": core_stats.get("total_retry_attempts", 0)
        })
    
    async def _get_endpoint_breakdown(
        self,
        data: GetDeliveryStatsData,
        core_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get detailed endpoint performance breakdown.
        
        Args:
            data: Statistics configuration
            core_stats: Core statistics from service
            
        Returns:
            Dictionary with endpoint performance data
        """
        endpoint_performance = core_stats.get("endpoint_performance", [])
        
        if not endpoint_performance:
            return {
                "endpoint_performance": [],
                "top_performing_endpoints": [],
                "underperforming_endpoints": []
            }
        
        # Sort endpoints by success rate
        sorted_endpoints = sorted(
            endpoint_performance,
            key=lambda x: x.get("success_rate", 0),
            reverse=True
        )
        
        # Limit endpoints if requested
        if len(sorted_endpoints) > data.endpoint_limit:
            sorted_endpoints = sorted_endpoints[:data.endpoint_limit]
        
        # Identify top and underperforming endpoints
        total_endpoints = len(sorted_endpoints)
        top_count = max(1, total_endpoints // 4)  # Top 25%
        bottom_count = max(1, total_endpoints // 4)  # Bottom 25%
        
        return {
            "endpoint_performance": sorted_endpoints,
            "top_performing_endpoints": sorted_endpoints[:top_count],
            "underperforming_endpoints": sorted_endpoints[-bottom_count:] if total_endpoints > 1 else []
        }
    
    async def _get_error_analysis(
        self,
        data: GetDeliveryStatsData,
        core_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get detailed error analysis from delivery statistics.
        
        Args:
            data: Statistics configuration
            core_stats: Core statistics from service
            
        Returns:
            Dictionary with error analysis data
        """
        error_distribution = core_stats.get("error_distribution", {})
        total_errors = sum(error_distribution.values()) if error_distribution else 0
        
        # Calculate error percentages
        error_percentages = {}
        if total_errors > 0:
            for error_type, count in error_distribution.items():
                error_percentages[error_type] = round((count / total_errors) * 100, 2)
        
        # Get top error types
        common_errors = dict(
            sorted(error_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        ) if error_distribution else {}
        
        return {
            "common_error_types": common_errors,
            "error_distribution": error_percentages,
            "max_retries_reached": core_stats.get("max_retries_reached", 0)
        }
    
    async def _get_trend_analysis(self, data: GetDeliveryStatsData) -> Dict[str, Any]:
        """Get trend analysis data for delivery performance over time.
        
        Args:
            data: Statistics configuration
            
        Returns:
            Dictionary with trend analysis data
        """
        # This would be implemented based on actual service capabilities
        # For now, return placeholder structure
        return {
            "hourly_trends": [],
            "daily_trends": [],
            "performance_trends": {
                "success_rate": [],
                "response_time": [],
                "throughput": []
            }
        }