"""Delivery service protocol for platform events infrastructure.

This module defines the DeliveryService protocol contract following maximum separation architecture.
Single responsibility: Webhook delivery coordination and management.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .....core.value_objects import UserId
from ..value_objects import EventId, WebhookEndpointId
from ..entities.domain_event import DomainEvent
from ..entities.webhook_endpoint import WebhookEndpoint
from ..entities.webhook_delivery import WebhookDelivery


@runtime_checkable
class DeliveryService(Protocol):
    """Delivery service protocol for coordinating webhook delivery operations.
    
    This protocol defines the contract for webhook delivery operations following
    maximum separation architecture. Single responsibility: coordinate webhook delivery
    lifecycle, retry management, endpoint verification, and delivery optimization.
    
    Pure platform infrastructure protocol - implementations handle:
    - Webhook delivery coordination
    - Multi-endpoint delivery orchestration  
    - Delivery retry and backoff strategies
    - Endpoint health monitoring
    - Performance optimization
    - Delivery statistics and monitoring
    """

    # ===========================================
    # Core Delivery Operations
    # ===========================================
    
    @abstractmethod
    async def deliver_event(
        self,
        event: DomainEvent,
        target_endpoints: Optional[List[WebhookEndpoint]] = None,
        delivery_context: Optional[Dict[str, Any]] = None,
        priority: Optional[str] = None
    ) -> List[WebhookDelivery]:
        """Deliver an event to all subscribed webhook endpoints.
        
        This is the core delivery method that:
        - Finds matching webhook subscriptions (if target_endpoints not provided)
        - Creates delivery records for each endpoint
        - Coordinates parallel delivery attempts
        - Handles errors and retry scheduling
        - Returns delivery tracking information
        
        Args:
            event: Domain event to deliver
            target_endpoints: Optional specific endpoints to deliver to (overrides subscriptions)
            delivery_context: Additional context for delivery (tenant_id, priority, etc.)
            priority: Optional priority override (normal, high, critical)
            
        Returns:
            List of WebhookDelivery records for all delivery attempts
            
        Raises:
            DeliveryError: If delivery coordination fails
            EndpointNotFoundError: If target endpoints don't exist
        """
        ...
    
    @abstractmethod
    async def deliver_to_endpoint(
        self,
        event: DomainEvent,
        endpoint: WebhookEndpoint,
        delivery_options: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> WebhookDelivery:
        """Deliver an event to a specific webhook endpoint.
        
        Handles single endpoint delivery with comprehensive tracking:
        - Creates delivery record with UUIDv7 for time-ordering
        - Executes HTTP request with proper authentication
        - Handles response processing and error classification
        - Manages timeout and retry scheduling
        - Records performance metrics
        
        Args:
            event: Domain event to deliver
            endpoint: Target webhook endpoint
            delivery_options: Optional delivery configuration overrides
            correlation_id: For tracking related deliveries
            
        Returns:
            WebhookDelivery record with complete delivery information
            
        Raises:
            DeliveryError: If delivery attempt fails
            EndpointError: If endpoint configuration is invalid
            TimeoutError: If delivery exceeds timeout threshold
        """
        ...
    
    @abstractmethod
    async def deliver_events_batch(
        self,
        events: List[DomainEvent],
        delivery_strategy: str = "parallel",
        max_concurrent_deliveries: Optional[int] = None,
        timeout_seconds: Optional[float] = None
    ) -> Dict[str, Any]:
        """High-performance batch delivery for multiple events.
        
        Coordinates efficient delivery of multiple events with configurable
        strategies and comprehensive performance tracking.
        
        Args:
            events: List of events to deliver
            delivery_strategy: "parallel", "sequential", or "adaptive"
            max_concurrent_deliveries: Maximum concurrent deliveries (uses config if None)
            timeout_seconds: Timeout for entire batch operation (uses config if None)
            
        Returns:
            Dict with batch delivery results and performance metrics:
            - total_events: Total events processed
            - successful_deliveries: Count of successful deliveries
            - failed_deliveries: Count of failed deliveries
            - deliveries: List of all WebhookDelivery records
            - total_duration_ms: Total processing time
            - average_delivery_time_ms: Average delivery time per endpoint
            - deliveries_per_second: Processing throughput
            - endpoint_success_rates: Per-endpoint success rates
            
        Raises:
            DeliveryError: If batch coordination fails
            TimeoutError: If batch processing exceeds timeout
        """
        ...

    # ===========================================
    # Retry and Recovery Operations
    # ===========================================
    
    @abstractmethod
    async def retry_failed_deliveries(
        self,
        limit: int = 100,
        event_types: Optional[List[str]] = None,
        endpoint_ids: Optional[List[WebhookEndpointId]] = None,
        max_age_hours: int = 24,
        retry_strategy: str = "exponential_backoff"
    ) -> int:
        """Retry failed webhook deliveries with intelligent filtering and backoff.
        
        Finds eligible failed deliveries and retries them using configurable
        strategies and comprehensive error handling.
        
        Args:
            limit: Maximum number of deliveries to retry
            event_types: Optional filter by event types
            endpoint_ids: Optional filter by specific endpoints
            max_age_hours: Maximum age of failures to consider for retry
            retry_strategy: "exponential_backoff", "fixed_interval", or "adaptive"
            
        Returns:
            Count of retry attempts initiated
            
        Raises:
            DeliveryRetryError: If retry processing fails
        """
        ...
    
    @abstractmethod
    async def retry_delivery(
        self,
        delivery_id: str,
        retry_reason: Optional[str] = None,
        override_retry_limit: bool = False,
        retry_delay_seconds: Optional[int] = None
    ) -> WebhookDelivery:
        """Retry a specific failed delivery with custom configuration.
        
        Retries a single delivery with optional configuration overrides
        for administrative or debugging purposes.
        
        Args:
            delivery_id: ID of the delivery to retry
            retry_reason: Optional reason for manual retry
            override_retry_limit: Whether to ignore max retry limit
            retry_delay_seconds: Optional custom delay before retry
            
        Returns:
            New WebhookDelivery record for the retry attempt
            
        Raises:
            DeliveryNotFoundError: If delivery doesn't exist
            RetryNotAllowedError: If delivery is not eligible for retry
            DeliveryRetryError: If retry setup fails
        """
        ...
    
    @abstractmethod
    async def cancel_delivery(
        self,
        delivery_id: str,
        cancellation_reason: str = "Cancelled by request"
    ) -> bool:
        """Cancel a pending or retrying webhook delivery.
        
        Marks delivery as cancelled to prevent further retry attempts
        and updates delivery statistics.
        
        Args:
            delivery_id: ID of the delivery to cancel
            cancellation_reason: Reason for cancellation
            
        Returns:
            True if cancellation was successful, False if delivery couldn't be cancelled
            
        Raises:
            DeliveryNotFoundError: If delivery doesn't exist
            DeliveryError: If cancellation operation fails
        """
        ...

    # ===========================================
    # Endpoint Management Operations
    # ===========================================
    
    @abstractmethod
    async def verify_endpoint(
        self,
        endpoint: WebhookEndpoint,
        verification_payload: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 10
    ) -> Dict[str, Any]:
        """Verify that a webhook endpoint is reachable and properly configured.
        
        Performs comprehensive endpoint verification including connectivity,
        authentication, and response validation.
        
        Args:
            endpoint: Webhook endpoint to verify
            verification_payload: Optional custom test payload
            timeout_seconds: Verification request timeout
            
        Returns:
            Dict with verification results:
            - is_reachable: Whether endpoint is accessible
            - response_time_ms: Response time in milliseconds
            - response_status: HTTP response status code
            - supports_signature: Whether endpoint validates signatures correctly
            - error_message: Error details if verification failed
            - verified_at: Timestamp of verification
            
        Raises:
            EndpointVerificationError: If verification process fails
        """
        ...
    
    @abstractmethod
    async def test_endpoint_delivery(
        self,
        endpoint: WebhookEndpoint,
        test_event: Optional[DomainEvent] = None,
        include_signature: bool = True
    ) -> WebhookDelivery:
        """Test delivery to an endpoint with a sample event.
        
        Performs a test delivery to validate endpoint configuration
        and response handling without affecting production metrics.
        
        Args:
            endpoint: Webhook endpoint to test
            test_event: Optional custom test event (generates default if None)
            include_signature: Whether to include HMAC signature
            
        Returns:
            WebhookDelivery record for the test delivery
            
        Raises:
            DeliveryError: If test delivery fails
            EndpointError: If endpoint configuration is invalid
        """
        ...
    
    @abstractmethod
    async def get_endpoint_health(
        self,
        endpoint_id: WebhookEndpointId,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Get health status and performance metrics for a webhook endpoint.
        
        Provides comprehensive health information for monitoring and
        operational decision making.
        
        Args:
            endpoint_id: ID of the endpoint to analyze
            time_range_hours: Time range for metrics calculation
            
        Returns:
            Dict with endpoint health information:
            - is_healthy: Overall health status
            - success_rate: Recent delivery success rate
            - average_response_time_ms: Average response time
            - total_deliveries: Total delivery attempts
            - recent_failures: Count of recent failures
            - last_successful_delivery: Timestamp of last success
            - error_patterns: Common error types and counts
            - health_score: Computed health score (0-100)
            
        Raises:
            EndpointNotFoundError: If endpoint doesn't exist
            DeliveryError: If health calculation fails
        """
        ...

    # ===========================================
    # Subscription and Routing Operations
    # ===========================================
    
    @abstractmethod
    async def get_subscribed_endpoints(
        self,
        event_type: str,
        context_id: Optional[str] = None,
        active_only: bool = True,
        include_health_check: bool = False
    ) -> List[WebhookEndpoint]:
        """Get webhook endpoints subscribed to a specific event type.
        
        Finds all endpoints that should receive deliveries for the given
        event type, with optional health filtering.
        
        Args:
            event_type: Event type to find subscriptions for
            context_id: Optional context filter (organization, team, etc.)
            active_only: Whether to include only active endpoints
            include_health_check: Whether to filter out unhealthy endpoints
            
        Returns:
            List of webhook endpoints subscribed to the event type
            
        Raises:
            DeliveryError: If subscription lookup fails
        """
        ...
    
    @abstractmethod
    async def get_delivery_routing(
        self,
        event: DomainEvent,
        include_filtering: bool = True
    ) -> List[Dict[str, Any]]:
        """Get delivery routing information for an event.
        
        Determines which endpoints should receive the event and provides
        routing decision information for debugging and monitoring.
        
        Args:
            event: Domain event to analyze
            include_filtering: Whether to apply event filters
            
        Returns:
            List of routing decisions with endpoint and filtering information:
            - endpoint: WebhookEndpoint that will receive the event
            - subscription_id: Subscription that matched
            - filter_match: Whether event passes subscription filters
            - routing_reason: Why this endpoint was selected
            - delivery_priority: Computed delivery priority
            
        Raises:
            DeliveryError: If routing calculation fails
        """
        ...

    # ===========================================
    # Statistics and Monitoring Operations  
    # ===========================================
    
    @abstractmethod
    async def get_delivery_statistics(
        self,
        event_type: Optional[str] = None,
        endpoint_id: Optional[WebhookEndpointId] = None,
        time_range_hours: int = 24,
        include_performance_metrics: bool = True
    ) -> Dict[str, Any]:
        """Get comprehensive delivery statistics for monitoring and analysis.
        
        Provides detailed statistics for system monitoring, performance
        analysis, and operational decision making.
        
        Args:
            event_type: Optional filter by event type
            endpoint_id: Optional filter by specific endpoint
            time_range_hours: Time range for statistics calculation
            include_performance_metrics: Whether to include detailed performance data
            
        Returns:
            Dict with comprehensive delivery statistics:
            - total_deliveries: Total delivery attempts
            - successful_deliveries: Successful delivery count
            - failed_deliveries: Failed delivery count
            - success_rate: Overall success percentage
            - average_response_time_ms: Average delivery time
            - p95_response_time_ms: 95th percentile response time
            - retry_rate: Percentage of deliveries that required retry
            - endpoint_performance: Per-endpoint performance metrics
            - error_distribution: Error types and frequencies
            - throughput_per_hour: Deliveries processed per hour
            - peak_delivery_times: Time periods with highest delivery volume
            
        Raises:
            DeliveryError: If statistics calculation fails
        """
        ...
    
    @abstractmethod
    async def get_failed_deliveries(
        self,
        limit: int = 100,
        event_type: Optional[str] = None,
        endpoint_id: Optional[WebhookEndpointId] = None,
        error_types: Optional[List[str]] = None,
        min_retry_count: int = 0
    ) -> List[WebhookDelivery]:
        """Get failed deliveries for analysis and operational investigation.
        
        Retrieves failed deliveries with filtering options for debugging,
        error analysis, and operational monitoring.
        
        Args:
            limit: Maximum number of deliveries to return
            event_type: Optional filter by event type
            endpoint_id: Optional filter by specific endpoint
            error_types: Optional filter by error types
            min_retry_count: Minimum retry count to include
            
        Returns:
            List of failed WebhookDelivery records with error information
            
        Raises:
            DeliveryError: If retrieval fails
        """
        ...
    
    @abstractmethod
    async def cleanup_old_deliveries(
        self,
        retention_days: int = 30,
        keep_failures_days: int = 90,
        batch_size: int = 1000,
        preserve_statistics: bool = True
    ) -> int:
        """Clean up old delivery records for database performance maintenance.
        
        Removes old delivery records while preserving important failure
        information and aggregate statistics for analysis.
        
        Args:
            retention_days: Days to retain successful delivery records
            keep_failures_days: Days to retain failed delivery records
            batch_size: Number of records to delete per batch
            preserve_statistics: Whether to preserve aggregate statistics
            
        Returns:
            Count of delivery records cleaned up
            
        Raises:
            DeliveryError: If cleanup operation fails
        """
        ...