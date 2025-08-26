"""Tests for event services."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from neo_commons.features.events.services.event_dispatcher_service import EventDispatcherService
from neo_commons.features.events.services.webhook_metrics_service import WebhookMetricsService
from neo_commons.features.events.services.webhook_monitoring_service import WebhookMonitoringService
from neo_commons.features.events.entities.domain_event import DomainEvent
from neo_commons.features.events.entities.webhook_subscription import WebhookSubscription
from neo_commons.features.events.entities.webhook_endpoint import WebhookEndpoint
from neo_commons.features.events.entities.webhook_delivery import WebhookDelivery, DeliveryStatus
from neo_commons.features.events.entities.webhook_delivery_attempt import (
    WebhookDeliveryAttempt, AttemptStatus
)
from neo_commons.core.value_objects import (
    EventId, WebhookEndpointId, WebhookSubscriptionId, WebhookDeliveryId,
    UserId, OrganizationId, EventType
)


class TestEventDispatcherService:
    """Test event dispatcher service business logic."""
    
    @pytest.fixture
    def service(self, mock_event_repository, mock_webhook_subscription_repository, 
                mock_webhook_delivery_repository, mock_http_adapter):
        return EventDispatcherService(
            event_repository=mock_event_repository,
            subscription_repository=mock_webhook_subscription_repository,
            delivery_repository=mock_webhook_delivery_repository,
            http_adapter=mock_http_adapter
        )
    
    @pytest.mark.asyncio
    async def test_dispatch_single_event(self, service, sample_domain_event, 
                                       mock_webhook_subscription_repository,
                                       mock_webhook_delivery_repository,
                                       mock_http_adapter):
        """Test dispatching a single event."""
        # Mock subscription
        subscription = WebhookSubscription(
            id=WebhookSubscriptionId(uuid4()),
            endpoint_id=WebhookEndpointId(uuid4()),
            event_type_id=uuid4(),
            event_type="test.event",
            event_filters={},
            is_active=True,
            context_id=sample_domain_event.context_id,
            subscription_name="Test Subscription",
            description="Test subscription"
        )
        
        mock_webhook_subscription_repository.get_matching_subscriptions.return_value = [subscription]
        mock_webhook_delivery_repository.save.return_value = None
        mock_http_adapter.deliver_webhook.return_value = MagicMock(
            success=True,
            status_code=200,
            response_body="OK"
        )
        
        result = await service.dispatch_event(sample_domain_event)
        
        assert result == 1
        mock_webhook_subscription_repository.get_matching_subscriptions.assert_called_once()
        mock_webhook_delivery_repository.save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dispatch_event_no_subscriptions(self, service, sample_domain_event,
                                                  mock_webhook_subscription_repository):
        """Test dispatching event with no matching subscriptions."""
        mock_webhook_subscription_repository.get_matching_subscriptions.return_value = []
        
        result = await service.dispatch_event(sample_domain_event)
        
        assert result == 0
        mock_webhook_subscription_repository.get_matching_subscriptions.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dispatch_unprocessed_events_batch(self, service, mock_event_repository,
                                                   mock_webhook_subscription_repository,
                                                   mock_webhook_delivery_repository):
        """Test batch processing of unprocessed events."""
        # Create multiple events
        events = [
            DomainEvent(
                id=EventId(uuid4()),
                event_type=EventType("test.event"),
                event_name="Test Event",
                aggregate_id=uuid4(),
                aggregate_type="test",
                aggregate_version=1,
                event_data={"key": "value"},
                event_metadata={},
                correlation_id=uuid4(),
                causation_id=uuid4(),
                triggered_by_user_id=UserId(uuid4()),
                context_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            ) for _ in range(5)
        ]
        
        mock_event_repository.get_unprocessed.return_value = events
        mock_webhook_subscription_repository.get_matching_subscriptions.return_value = []
        mock_event_repository.mark_multiple_as_processed.return_value = None
        
        result = await service.dispatch_unprocessed_events(limit=10, batch_size=3)
        
        assert result == 5
        mock_event_repository.get_unprocessed.assert_called_once_with(10)
        mock_event_repository.mark_multiple_as_processed.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dispatch_with_filtering(self, service, mock_webhook_subscription_repository):
        """Test event filtering with subscription filters."""
        # Create event with specific data
        event = DomainEvent(
            id=EventId(uuid4()),
            event_type=EventType("user.created"),
            event_name="User Created",
            aggregate_id=uuid4(),
            aggregate_type="user",
            aggregate_version=1,
            event_data={"status": "active", "role": "admin"},
            event_metadata={},
            correlation_id=uuid4(),
            causation_id=uuid4(),
            triggered_by_user_id=UserId(uuid4()),
            context_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        
        # Create subscription with filters
        subscription = WebhookSubscription(
            id=WebhookSubscriptionId(uuid4()),
            endpoint_id=WebhookEndpointId(uuid4()),
            event_type_id=uuid4(),
            event_type="user.created",
            event_filters={"status": {"$eq": "active"}},
            is_active=True,
            context_id=event.context_id,
            subscription_name="Active User Subscription",
            description="Only active users"
        )
        
        mock_webhook_subscription_repository.get_matching_subscriptions.return_value = [subscription]
        
        # Test that subscription matches event (filtering happens in repository)
        result = await service._get_matching_subscriptions(event)
        
        assert len(result) == 1
        assert result[0].event_filters == {"status": {"$eq": "active"}}
    
    @pytest.mark.asyncio
    async def test_retry_failed_deliveries(self, service, mock_webhook_delivery_repository,
                                         mock_http_adapter):
        """Test retrying failed deliveries."""
        # Create failed delivery
        delivery = WebhookDelivery(
            id=WebhookDeliveryId(uuid4()),
            webhook_endpoint_id=WebhookEndpointId(uuid4()),
            webhook_event_id=EventId(uuid4()),
            current_attempt=1,
            overall_status=DeliveryStatus.PENDING,
            max_attempts=3,
            base_backoff_seconds=5,
            backoff_multiplier=2.0,
            next_retry_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            max_attempts_reached=False,
            attempts=[]
        )
        
        mock_webhook_delivery_repository.get_pending_retries.return_value = [delivery]
        mock_webhook_delivery_repository.update.return_value = None
        mock_http_adapter.deliver_webhook.return_value = MagicMock(
            success=True,
            status_code=200,
            response_body="OK"
        )
        
        result = await service.retry_failed_deliveries(limit=10)
        
        assert result == 1
        mock_webhook_delivery_repository.get_pending_retries.assert_called_once()
        mock_webhook_delivery_repository.update.assert_called_once()


class TestWebhookMetricsService:
    """Test webhook metrics service."""
    
    @pytest.fixture
    def service(self, mock_webhook_delivery_repository):
        return WebhookMetricsService(mock_webhook_delivery_repository)
    
    @pytest.mark.asyncio
    async def test_calculate_endpoint_metrics(self, service, mock_webhook_delivery_repository):
        """Test calculating metrics for an endpoint."""
        endpoint_id = WebhookEndpointId(uuid4())
        
        # Mock delivery attempts
        mock_attempts = [
            {
                'response_time_ms': 100,
                'status_code': 200,
                'success': True,
                'attempted_at': datetime.now(timezone.utc)
            },
            {
                'response_time_ms': 150,
                'status_code': 200,
                'success': True,
                'attempted_at': datetime.now(timezone.utc)
            },
            {
                'response_time_ms': 200,
                'status_code': 500,
                'success': False,
                'attempted_at': datetime.now(timezone.utc)
            }
        ]
        
        mock_webhook_delivery_repository.get_delivery_attempts_by_endpoint.return_value = mock_attempts
        
        # Mock delivery statistics
        mock_stats = {
            'total_deliveries': 3,
            'successful_deliveries': 2,
            'failed_deliveries': 1,
            'average_response_time': 150.0
        }
        mock_webhook_delivery_repository.get_endpoint_delivery_stats.return_value = mock_stats
        
        result = await service.calculate_endpoint_metrics(
            endpoint_id=endpoint_id,
            hours_back=24
        )
        
        assert result.endpoint_id == endpoint_id
        assert result.total_deliveries == 3
        assert result.success_rate == 66.67
        assert result.average_response_time == 150.0
        assert result.health_score > 0
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, service, mock_webhook_delivery_repository):
        """Test getting system-wide metrics."""
        # Mock system statistics
        mock_stats = {
            'total_endpoints': 10,
            'active_endpoints': 8,
            'total_deliveries_24h': 1000,
            'successful_deliveries_24h': 950,
            'failed_deliveries_24h': 50,
            'average_response_time_24h': 120.5,
            'events_processed_24h': 800
        }
        
        mock_webhook_delivery_repository.get_system_stats.return_value = mock_stats
        
        result = await service.get_system_metrics(hours_back=24)
        
        assert result.total_endpoints == 10
        assert result.active_endpoints == 8
        assert result.overall_success_rate == 95.0
        assert result.average_response_time == 120.5
        assert result.health_score > 0
    
    def test_calculate_percentiles(self, service):
        """Test percentile calculations."""
        response_times = [100, 120, 130, 140, 150, 200, 250, 300, 400, 500]
        
        result = service._calculate_percentiles(response_times)
        
        assert 'p50' in result
        assert 'p95' in result
        assert 'p99' in result
        assert result['p50'] <= result['p95'] <= result['p99']
    
    def test_calculate_health_score(self, service):
        """Test health score calculation."""
        # High success rate, low response time
        score1 = service._calculate_health_score(
            success_rate=95.0,
            avg_response_time=100.0,
            total_deliveries=1000
        )
        
        # Low success rate, high response time
        score2 = service._calculate_health_score(
            success_rate=70.0,
            avg_response_time=2000.0,
            total_deliveries=1000
        )
        
        assert 0 <= score1 <= 100
        assert 0 <= score2 <= 100
        assert score1 > score2


class TestWebhookMonitoringService:
    """Test webhook monitoring service."""
    
    @pytest.fixture
    def service(self, mock_webhook_delivery_repository, mock_webhook_endpoint_repository):
        service = WebhookMonitoringService(
            delivery_repository=mock_webhook_delivery_repository,
            endpoint_repository=mock_webhook_endpoint_repository
        )
        return service
    
    @pytest.mark.asyncio
    async def test_start_monitoring(self, service):
        """Test starting monitoring tasks."""
        with patch.object(service, '_monitor_health_checks') as mock_health:
            with patch.object(service, '_monitor_delivery_queue') as mock_queue:
                with patch.object(service, '_monitor_error_rates') as mock_errors:
                    with patch.object(service, '_monitor_performance') as mock_perf:
                        with patch.object(service, '_collect_statistics') as mock_stats:
                            await service.start_monitoring()
                            
                            assert service._monitoring_active is True
                            assert len(service._monitoring_tasks) == 5
    
    @pytest.mark.asyncio
    async def test_stop_monitoring(self, service):
        """Test stopping monitoring tasks."""
        # Start monitoring first
        service._monitoring_active = True
        service._monitoring_tasks = [MagicMock() for _ in range(5)]
        
        for task in service._monitoring_tasks:
            task.cancel = MagicMock()
            task.cancelled.return_value = False
            task.done.return_value = True
        
        await service.stop_monitoring()
        
        assert service._monitoring_active is False
        assert len(service._monitoring_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_generate_alert_high_error_rate(self, service):
        """Test alert generation for high error rate."""
        endpoint_id = WebhookEndpointId(uuid4())
        
        alert = await service._generate_alert(
            alert_type="high_error_rate",
            endpoint_id=endpoint_id,
            details={"error_rate": 25.5, "threshold": 10.0}
        )
        
        assert alert is not None
        assert alert['type'] == "high_error_rate"
        assert alert['endpoint_id'] == endpoint_id
        assert alert['severity'] == "high"
        assert "25.5%" in alert['message']
    
    @pytest.mark.asyncio
    async def test_generate_alert_slow_response(self, service):
        """Test alert generation for slow response times."""
        endpoint_id = WebhookEndpointId(uuid4())
        
        alert = await service._generate_alert(
            alert_type="slow_response_time",
            endpoint_id=endpoint_id,
            details={"avg_response_time": 5500, "threshold": 5000}
        )
        
        assert alert is not None
        assert alert['type'] == "slow_response_time"
        assert alert['endpoint_id'] == endpoint_id
        assert alert['severity'] == "medium"
        assert "5500ms" in alert['message']
    
    def test_alert_severity_calculation(self, service):
        """Test alert severity calculation."""
        # High error rate should be high severity
        severity1 = service._calculate_alert_severity("high_error_rate", {"error_rate": 50.0})
        assert severity1 == "critical"
        
        # Medium error rate should be high severity
        severity2 = service._calculate_alert_severity("high_error_rate", {"error_rate": 25.0})
        assert severity2 == "high"
        
        # Low error rate should be medium severity
        severity3 = service._calculate_alert_severity("high_error_rate", {"error_rate": 15.0})
        assert severity3 == "medium"
        
        # Very slow response should be critical
        severity4 = service._calculate_alert_severity("slow_response_time", {"avg_response_time": 10000})
        assert severity4 == "critical"


class TestServiceIntegration:
    """Test service integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_webhook_flow(self, mock_event_repository, mock_webhook_subscription_repository,
                                       mock_webhook_delivery_repository, mock_http_adapter):
        """Test complete webhook delivery flow."""
        # Setup services
        dispatcher = EventDispatcherService(
            event_repository=mock_event_repository,
            subscription_repository=mock_webhook_subscription_repository,
            delivery_repository=mock_webhook_delivery_repository,
            http_adapter=mock_http_adapter
        )
        
        metrics_service = WebhookMetricsService(mock_webhook_delivery_repository)
        
        # Create test event
        event = DomainEvent(
            id=EventId(uuid4()),
            event_type=EventType("order.completed"),
            event_name="Order Completed",
            aggregate_id=uuid4(),
            aggregate_type="order",
            aggregate_version=1,
            event_data={"order_id": "12345", "amount": 100.00},
            event_metadata={"source": "order_service"},
            correlation_id=uuid4(),
            causation_id=uuid4(),
            triggered_by_user_id=UserId(uuid4()),
            context_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        
        # Mock subscription
        subscription = WebhookSubscription(
            id=WebhookSubscriptionId(uuid4()),
            endpoint_id=WebhookEndpointId(uuid4()),
            event_type_id=uuid4(),
            event_type="order.completed",
            event_filters={"amount": {"$gte": 50.00}},
            is_active=True,
            context_id=event.context_id,
            subscription_name="Order Completion Webhook",
            description="Webhook for completed orders"
        )
        
        mock_webhook_subscription_repository.get_matching_subscriptions.return_value = [subscription]
        mock_webhook_delivery_repository.save.return_value = None
        mock_http_adapter.deliver_webhook.return_value = MagicMock(
            success=True,
            status_code=200,
            response_body="OK",
            response_time_ms=150
        )
        
        # Dispatch event
        dispatched_count = await dispatcher.dispatch_event(event)
        assert dispatched_count == 1
        
        # Mock metrics data
        mock_webhook_delivery_repository.get_delivery_attempts_by_endpoint.return_value = [
            {
                'response_time_ms': 150,
                'status_code': 200,
                'success': True,
                'attempted_at': datetime.now(timezone.utc)
            }
        ]
        
        mock_webhook_delivery_repository.get_endpoint_delivery_stats.return_value = {
            'total_deliveries': 1,
            'successful_deliveries': 1,
            'failed_deliveries': 0,
            'average_response_time': 150.0
        }
        
        # Get metrics
        metrics = await metrics_service.calculate_endpoint_metrics(
            endpoint_id=subscription.endpoint_id,
            hours_back=24
        )
        
        assert metrics.success_rate == 100.0
        assert metrics.average_response_time == 150.0
        assert metrics.total_deliveries == 1