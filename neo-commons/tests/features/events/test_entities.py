"""Tests for events entities."""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import patch

from neo_commons.core.value_objects import (
    EventId, WebhookEndpointId, WebhookDeliveryId, WebhookEventTypeId,
    WebhookSubscriptionId, UserId, EventType
)
from neo_commons.features.events.entities.domain_event import DomainEvent
from neo_commons.features.events.entities.webhook_endpoint import WebhookEndpoint
from neo_commons.features.events.entities.webhook_event_type import WebhookEventType
from neo_commons.features.events.entities.webhook_subscription import WebhookSubscription
from neo_commons.features.events.entities.webhook_delivery import (
    WebhookDelivery, WebhookDeliveryAttempt, DeliveryStatus
)


class TestDomainEvent:
    """Test cases for DomainEvent entity."""
    
    def test_domain_event_creation(self, sample_domain_event):
        """Test domain event creation with valid data."""
        event = sample_domain_event
        
        assert isinstance(event.id, EventId)
        assert isinstance(event.event_type, EventType)
        assert event.event_name == "Test Event"
        assert event.aggregate_type == "test_aggregate"
        assert event.aggregate_version == 1
        assert event.event_data == {"key": "value", "number": 42}
        assert event.event_metadata == {"source": "test", "version": "1.0"}
        assert event.processed_at is None  # Should be None initially
    
    def test_domain_event_mark_as_processed(self, sample_domain_event):
        """Test marking domain event as processed."""
        event = sample_domain_event
        
        # Initially not processed
        assert not event.is_processed()
        
        # Mark as processed
        event.mark_as_processed()
        
        # Should now be processed
        assert event.is_processed()
        assert event.processed_at is not None
        assert isinstance(event.processed_at, datetime)
    
    def test_domain_event_to_dict(self, sample_domain_event):
        """Test domain event serialization."""
        event = sample_domain_event
        event_dict = event.to_dict()
        
        assert event_dict["id"] == str(event.id.value)
        assert event_dict["event_type"] == event.event_type.value
        assert event_dict["event_name"] == event.event_name
        assert event_dict["aggregate_type"] == event.aggregate_type
        assert event_dict["event_data"] == event.event_data
        assert event_dict["processed_at"] is None
    
    def test_domain_event_from_dict(self, sample_domain_event):
        """Test domain event deserialization."""
        original_event = sample_domain_event
        event_dict = original_event.to_dict()
        
        # Recreate event from dict
        recreated_event = DomainEvent.from_dict(event_dict)
        
        assert recreated_event.id.value == original_event.id.value
        assert recreated_event.event_type.value == original_event.event_type.value
        assert recreated_event.event_name == original_event.event_name
        assert recreated_event.event_data == original_event.event_data


class TestWebhookEndpoint:
    """Test cases for WebhookEndpoint entity."""
    
    def test_webhook_endpoint_creation(self, sample_webhook_endpoint):
        """Test webhook endpoint creation with valid data."""
        endpoint = sample_webhook_endpoint
        
        assert isinstance(endpoint.id, WebhookEndpointId)
        assert endpoint.name == "Test Webhook"
        assert endpoint.endpoint_url == "https://api.example.com/webhook"
        assert endpoint.http_method == "POST"
        assert endpoint.is_active is True
        assert endpoint.is_verified is True
        assert endpoint.timeout_seconds == 30
        assert endpoint.max_retry_attempts == 3
    
    def test_webhook_endpoint_validation(self, sample_user_id, sample_organization_id):
        """Test webhook endpoint validation."""
        # Test invalid URL
        with pytest.raises(ValueError, match="endpoint_url must be a valid HTTP/HTTPS URL"):
            WebhookEndpoint(
                id=WebhookEndpointId(uuid4()),
                name="Invalid Endpoint",
                endpoint_url="invalid-url",
                created_by_user_id=sample_user_id,
                context_id=sample_organization_id.value
            )
        
        # Test invalid HTTP method
        with pytest.raises(ValueError, match="http_method must be one of"):
            WebhookEndpoint(
                id=WebhookEndpointId(uuid4()),
                name="Invalid Method",
                endpoint_url="https://example.com/webhook",
                http_method="GET",  # Invalid for webhooks
                created_by_user_id=sample_user_id,
                context_id=sample_organization_id.value
            )
        
        # Test invalid timeout
        with pytest.raises(ValueError, match="timeout_seconds must be between"):
            WebhookEndpoint(
                id=WebhookEndpointId(uuid4()),
                name="Invalid Timeout",
                endpoint_url="https://example.com/webhook",
                timeout_seconds=400,  # Too high
                created_by_user_id=sample_user_id,
                context_id=sample_organization_id.value
            )
    
    def test_webhook_endpoint_deactivation(self, sample_webhook_endpoint):
        """Test webhook endpoint deactivation."""
        endpoint = sample_webhook_endpoint
        
        assert endpoint.is_active is True
        
        # Deactivate endpoint
        endpoint.deactivate()
        
        assert endpoint.is_active is False
    
    def test_webhook_endpoint_verification(self, sample_webhook_endpoint):
        """Test webhook endpoint verification."""
        endpoint = sample_webhook_endpoint
        
        # Initially verified (from fixture)
        assert endpoint.is_verified is True
        
        # Mark as unverified
        endpoint.mark_as_unverified()
        assert endpoint.is_verified is False
        
        # Verify endpoint
        endpoint.mark_as_verified()
        assert endpoint.is_verified is True
        assert endpoint.verified_at is not None
    
    def test_webhook_endpoint_update_last_used(self, sample_webhook_endpoint):
        """Test updating last used timestamp."""
        endpoint = sample_webhook_endpoint
        
        # Initially no last used time
        original_last_used = endpoint.last_used_at
        
        # Update last used
        endpoint.update_last_used()
        
        assert endpoint.last_used_at != original_last_used
        assert isinstance(endpoint.last_used_at, datetime)


class TestWebhookEventType:
    """Test cases for WebhookEventType entity."""
    
    def test_webhook_event_type_creation(self, sample_webhook_event_type):
        """Test webhook event type creation."""
        event_type = sample_webhook_event_type
        
        assert isinstance(event_type.id, WebhookEventTypeId)
        assert event_type.event_type == "test.event"
        assert event_type.category == "test"
        assert event_type.display_name == "Test Event"
        assert event_type.is_enabled is True
        assert event_type.requires_verification is False
    
    def test_webhook_event_type_validation(self):
        """Test webhook event type validation."""
        # Test invalid event type format
        with pytest.raises(ValueError, match="event_type must follow"):
            WebhookEventType(
                id=WebhookEventTypeId(uuid4()),
                event_type="invalid-format",  # Should use dot notation
                category="test",
                display_name="Invalid Event Type"
            )
    
    def test_is_subscription_allowed(self, sample_webhook_event_type):
        """Test subscription permission checking."""
        event_type = sample_webhook_event_type
        
        # Event type doesn't require verification
        assert event_type.is_subscription_allowed(endpoint_verified=True)
        assert event_type.is_subscription_allowed(endpoint_verified=False)
        
        # Set to require verification
        event_type.requires_verification = True
        
        assert event_type.is_subscription_allowed(endpoint_verified=True)
        assert not event_type.is_subscription_allowed(endpoint_verified=False)
    
    def test_webhook_event_type_enable_disable(self, sample_webhook_event_type):
        """Test enabling/disabling event type."""
        event_type = sample_webhook_event_type
        
        assert event_type.is_enabled is True
        
        # Disable
        event_type.disable()
        assert event_type.is_enabled is False
        
        # Enable
        event_type.enable()
        assert event_type.is_enabled is True


class TestWebhookSubscription:
    """Test cases for WebhookSubscription entity."""
    
    def test_webhook_subscription_creation(self, sample_webhook_subscription):
        """Test webhook subscription creation."""
        subscription = sample_webhook_subscription
        
        assert isinstance(subscription.id, WebhookSubscriptionId)
        assert isinstance(subscription.endpoint_id, WebhookEndpointId)
        assert isinstance(subscription.event_type_id, WebhookEventTypeId)
        assert subscription.event_type == "test.event"
        assert subscription.is_active is True
        assert subscription.event_filters == {"status": {"$eq": "active"}}
    
    def test_webhook_subscription_matches_event(self, sample_webhook_subscription):
        """Test event matching logic."""
        subscription = sample_webhook_subscription
        
        # Test matching event
        matching_event_data = {
            "status": "active",
            "other_field": "value"
        }
        assert subscription.matches_event(matching_event_data)
        
        # Test non-matching event
        non_matching_event_data = {
            "status": "inactive",
            "other_field": "value"
        }
        assert not subscription.matches_event(non_matching_event_data)
        
        # Test event with missing field
        missing_field_event = {
            "other_field": "value"
        }
        assert not subscription.matches_event(missing_field_event)
    
    def test_webhook_subscription_complex_filters(
        self, 
        sample_subscription_id,
        sample_endpoint_id,
        sample_event_type_id
    ):
        """Test complex event filtering."""
        # Create subscription with complex filters
        subscription = WebhookSubscription(
            id=sample_subscription_id,
            endpoint_id=sample_endpoint_id,
            event_type_id=sample_event_type_id,
            event_type="user.updated",
            event_filters={
                "user.role": {"$in": ["admin", "moderator"]},
                "user.status": {"$eq": "active"},
                "changes.permissions": {"$exists": True}
            },
            is_active=True
        )
        
        # Test matching event
        matching_event = {
            "user": {
                "role": "admin",
                "status": "active"
            },
            "changes": {
                "permissions": ["read", "write"]
            }
        }
        assert subscription.matches_event(matching_event)
        
        # Test non-matching role
        non_matching_event = {
            "user": {
                "role": "user",  # Not in allowed roles
                "status": "active"
            },
            "changes": {
                "permissions": ["read"]
            }
        }
        assert not subscription.matches_event(non_matching_event)
    
    def test_webhook_subscription_activation(self, sample_webhook_subscription):
        """Test subscription activation/deactivation."""
        subscription = sample_webhook_subscription
        
        assert subscription.is_active is True
        
        # Deactivate
        subscription.deactivate()
        assert subscription.is_active is False
        
        # Activate
        subscription.activate()
        assert subscription.is_active is True
    
    def test_webhook_subscription_update_filters(self, sample_webhook_subscription):
        """Test updating subscription filters."""
        subscription = sample_webhook_subscription
        
        new_filters = {
            "priority": {"$gte": 5},
            "category": {"$eq": "urgent"}
        }
        
        subscription.update_filters(new_filters)
        assert subscription.event_filters == new_filters


class TestWebhookDelivery:
    """Test cases for WebhookDelivery entity."""
    
    def test_webhook_delivery_creation(self, sample_webhook_delivery):
        """Test webhook delivery creation."""
        delivery = sample_webhook_delivery
        
        assert isinstance(delivery.id, WebhookDeliveryId)
        assert isinstance(delivery.webhook_endpoint_id, WebhookEndpointId)
        assert isinstance(delivery.webhook_event_id, EventId)
        assert delivery.current_attempt == 1
        assert delivery.overall_status == DeliveryStatus.PENDING
        assert delivery.max_attempts == 3
        assert not delivery.max_attempts_reached
    
    def test_webhook_delivery_add_attempt(self, sample_webhook_delivery):
        """Test adding delivery attempts."""
        delivery = sample_webhook_delivery
        
        # Create an attempt
        attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.SUCCESS,
            request_url="https://api.example.com/webhook",
            request_method="POST",
            response_status_code=200,
            response_time_ms=250
        )
        
        delivery.add_attempt(attempt)
        
        assert len(delivery.attempts) == 1
        assert delivery.attempts[0] == attempt
        assert delivery.current_attempt == 2  # Should increment
        assert delivery.overall_status == DeliveryStatus.SUCCESS
    
    def test_webhook_delivery_should_retry(self, sample_webhook_delivery):
        """Test retry logic."""
        delivery = sample_webhook_delivery
        
        # Initially should not retry (no failed attempts)
        assert not delivery.should_retry()
        
        # Add a failed attempt
        failed_attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.FAILED,
            request_url="https://api.example.com/webhook",
            request_method="POST",
            error_message="Connection timeout"
        )
        
        delivery.add_attempt(failed_attempt)
        
        # Should retry after first failure
        assert delivery.should_retry()
        
        # Add more failed attempts to reach max
        for i in range(2, delivery.max_attempts + 1):
            delivery.add_attempt(WebhookDeliveryAttempt(
                attempt_number=i,
                delivery_status=DeliveryStatus.FAILED,
                request_url="https://api.example.com/webhook",
                request_method="POST"
            ))
        
        # Should not retry after max attempts
        assert not delivery.should_retry()
        assert delivery.max_attempts_reached
    
    def test_webhook_delivery_calculate_next_retry(self, sample_webhook_delivery):
        """Test retry timing calculation."""
        delivery = sample_webhook_delivery
        
        # Add failed attempt
        failed_attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.FAILED,
            request_url="https://api.example.com/webhook",
            request_method="POST"
        )
        
        delivery.add_attempt(failed_attempt)
        next_retry = delivery.calculate_next_retry_time()
        
        assert next_retry is not None
        assert next_retry > datetime.now(timezone.utc)
        
        # For attempt 2, should wait base_backoff_seconds (5s)
        expected_wait = timedelta(seconds=delivery.base_backoff_seconds)
        tolerance = timedelta(seconds=1)
        
        actual_wait = next_retry - datetime.now(timezone.utc)
        assert abs(actual_wait - expected_wait) < tolerance
    
    def test_webhook_delivery_is_complete(self, sample_webhook_delivery):
        """Test delivery completion status."""
        delivery = sample_webhook_delivery
        
        # Initially not complete
        assert not delivery.is_complete()
        
        # Add successful attempt
        successful_attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.SUCCESS,
            request_url="https://api.example.com/webhook",
            request_method="POST",
            response_status_code=200
        )
        
        delivery.add_attempt(successful_attempt)
        
        # Should now be complete
        assert delivery.is_complete()


class TestWebhookDeliveryAttempt:
    """Test cases for WebhookDeliveryAttempt entity."""
    
    def test_webhook_delivery_attempt_creation(self):
        """Test webhook delivery attempt creation."""
        attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.SUCCESS,
            request_url="https://api.example.com/webhook",
            request_method="POST",
            response_status_code=200,
            response_time_ms=150
        )
        
        assert attempt.attempt_number == 1
        assert attempt.delivery_status == DeliveryStatus.SUCCESS
        assert attempt.request_url == "https://api.example.com/webhook"
        assert attempt.response_status_code == 200
        assert attempt.response_time_ms == 150
    
    def test_webhook_delivery_attempt_validation(self):
        """Test webhook delivery attempt validation."""
        # Test invalid attempt number
        with pytest.raises(ValueError, match="attempt_number must be >= 1"):
            WebhookDeliveryAttempt(
                attempt_number=0,
                delivery_status=DeliveryStatus.PENDING,
                request_url="https://api.example.com/webhook",
                request_method="POST"
            )
        
        # Test invalid HTTP method
        with pytest.raises(ValueError, match="request_method must be one of"):
            WebhookDeliveryAttempt(
                attempt_number=1,
                delivery_status=DeliveryStatus.PENDING,
                request_url="https://api.example.com/webhook",
                request_method="GET"
            )
        
        # Test invalid URL
        with pytest.raises(ValueError, match="request_url must be a valid HTTP/HTTPS URL"):
            WebhookDeliveryAttempt(
                attempt_number=1,
                delivery_status=DeliveryStatus.PENDING,
                request_url="invalid-url",
                request_method="POST"
            )
    
    def test_webhook_delivery_attempt_status_checks(self):
        """Test delivery attempt status checking methods."""
        # Successful attempt
        successful_attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.SUCCESS,
            request_url="https://api.example.com/webhook",
            request_method="POST"
        )
        
        assert successful_attempt.is_successful()
        assert not successful_attempt.is_failed()
        assert not successful_attempt.is_retryable()
        
        # Failed attempt
        failed_attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.FAILED,
            request_url="https://api.example.com/webhook",
            request_method="POST"
        )
        
        assert not failed_attempt.is_successful()
        assert failed_attempt.is_failed()
        assert failed_attempt.is_retryable()
        
        # Timeout attempt
        timeout_attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.TIMEOUT,
            request_url="https://api.example.com/webhook",
            request_method="POST"
        )
        
        assert not timeout_attempt.is_successful()
        assert timeout_attempt.is_failed()
        assert timeout_attempt.is_retryable()
    
    def test_webhook_delivery_attempt_mark_completed(self):
        """Test marking attempt as completed."""
        attempt = WebhookDeliveryAttempt(
            attempt_number=1,
            delivery_status=DeliveryStatus.PENDING,
            request_url="https://api.example.com/webhook",
            request_method="POST"
        )
        
        # Initially not completed
        assert attempt.completed_at is None
        
        # Mark as completed
        attempt.mark_completed()
        
        # Should now have completion timestamp
        assert attempt.completed_at is not None
        assert isinstance(attempt.completed_at, datetime)