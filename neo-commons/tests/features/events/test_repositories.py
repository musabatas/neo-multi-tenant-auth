"""Tests for event repositories."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from neo_commons.features.events.repositories.domain_event_repository import DomainEventRepository
from neo_commons.features.events.repositories.webhook_endpoint_repository import WebhookEndpointRepository
from neo_commons.features.events.repositories.webhook_event_type_repository import WebhookEventTypeRepository
from neo_commons.features.events.repositories.webhook_subscription_repository import WebhookSubscriptionRepository
from neo_commons.features.events.repositories.webhook_delivery_repository import WebhookDeliveryRepository
from neo_commons.features.events.entities.domain_event import DomainEvent
from neo_commons.features.events.entities.webhook_endpoint import WebhookEndpoint
from neo_commons.features.events.entities.webhook_event_type import WebhookEventType
from neo_commons.features.events.entities.webhook_subscription import WebhookSubscription
from neo_commons.features.events.entities.webhook_delivery import WebhookDelivery, DeliveryStatus
from neo_commons.core.value_objects import (
    EventId, WebhookEndpointId, WebhookEventTypeId, WebhookSubscriptionId,
    WebhookDeliveryId, UserId, OrganizationId, EventType
)


class TestDomainEventRepository:
    """Test domain event repository operations."""
    
    @pytest.fixture
    def repository(self, mock_database_repository):
        return DomainEventRepository(mock_database_repository)
    
    @pytest.mark.asyncio
    async def test_save_domain_event(self, repository, sample_domain_event, mock_database_repository):
        """Test saving a domain event."""
        mock_database_repository.execute.return_value = None
        
        await repository.save(sample_domain_event)
        
        mock_database_repository.execute.assert_called_once()
        call_args = mock_database_repository.execute.call_args[0]
        assert "INSERT INTO" in call_args[0]
        assert "domain_events" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, repository, sample_event_id, mock_database_repository):
        """Test getting domain event by ID."""
        mock_row = {
            'id': sample_event_id.value,
            'event_type': 'test.event',
            'event_name': 'Test Event',
            'aggregate_id': uuid4(),
            'aggregate_type': 'test_aggregate',
            'aggregate_version': 1,
            'event_data': {'key': 'value'},
            'event_metadata': {'source': 'test'},
            'correlation_id': uuid4(),
            'causation_id': uuid4(),
            'triggered_by_user_id': uuid4(),
            'context_id': uuid4(),
            'occurred_at': datetime.now(timezone.utc),
            'created_at': datetime.now(timezone.utc),
            'processed_at': None
        }
        mock_database_repository.fetchrow.return_value = mock_row
        
        result = await repository.get_by_id(sample_event_id)
        
        assert result is not None
        assert result.id == sample_event_id
        assert result.event_type.value == 'test.event'
        mock_database_repository.fetchrow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_unprocessed_events(self, repository, mock_database_repository):
        """Test getting unprocessed events."""
        mock_rows = [
            {
                'id': uuid4(),
                'event_type': 'test.event',
                'event_name': 'Test Event',
                'aggregate_id': uuid4(),
                'aggregate_type': 'test_aggregate',
                'aggregate_version': 1,
                'event_data': {'key': 'value'},
                'event_metadata': {'source': 'test'},
                'correlation_id': uuid4(),
                'causation_id': uuid4(),
                'triggered_by_user_id': uuid4(),
                'context_id': uuid4(),
                'occurred_at': datetime.now(timezone.utc),
                'created_at': datetime.now(timezone.utc),
                'processed_at': None
            }
        ]
        mock_database_repository.fetch.return_value = mock_rows
        
        result = await repository.get_unprocessed(limit=10)
        
        assert len(result) == 1
        assert result[0].processed_at is None
        mock_database_repository.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_as_processed(self, repository, sample_event_id, mock_database_repository):
        """Test marking event as processed."""
        mock_database_repository.execute.return_value = None
        
        await repository.mark_as_processed(sample_event_id)
        
        mock_database_repository.execute.assert_called_once()
        call_args = mock_database_repository.execute.call_args[0]
        assert "UPDATE" in call_args[0]
        assert "processed_at" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_mark_multiple_as_processed(self, repository, mock_database_repository):
        """Test marking multiple events as processed."""
        event_ids = [EventId(uuid4()), EventId(uuid4())]
        mock_database_repository.execute.return_value = None
        
        await repository.mark_multiple_as_processed(event_ids)
        
        mock_database_repository.execute.assert_called_once()
        call_args = mock_database_repository.execute.call_args[0]
        assert "UPDATE" in call_args[0]
        assert "WHERE id = ANY($1)" in call_args[0]


class TestWebhookEndpointRepository:
    """Test webhook endpoint repository operations."""
    
    @pytest.fixture
    def repository(self, mock_database_repository):
        return WebhookEndpointRepository(mock_database_repository)
    
    @pytest.mark.asyncio
    async def test_save_webhook_endpoint(self, repository, sample_webhook_endpoint, mock_database_repository):
        """Test saving a webhook endpoint."""
        mock_database_repository.execute.return_value = None
        
        await repository.save(sample_webhook_endpoint)
        
        mock_database_repository.execute.assert_called_once()
        call_args = mock_database_repository.execute.call_args[0]
        assert "INSERT INTO" in call_args[0]
        assert "webhook_endpoints" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_get_active_endpoints(self, repository, mock_database_repository):
        """Test getting active webhook endpoints."""
        context_id = uuid4()
        mock_rows = [
            {
                'id': uuid4(),
                'name': 'Test Webhook',
                'description': 'Test webhook endpoint',
                'endpoint_url': 'https://api.example.com/webhook',
                'http_method': 'POST',
                'secret_token': 'test-secret',
                'signature_header': 'X-Webhook-Signature',
                'custom_headers': {'Authorization': 'Bearer token'},
                'timeout_seconds': 30,
                'follow_redirects': False,
                'verify_ssl': True,
                'max_retry_attempts': 3,
                'retry_backoff_seconds': 5,
                'retry_backoff_multiplier': 2.0,
                'is_active': True,
                'is_verified': True,
                'created_by_user_id': uuid4(),
                'context_id': context_id,
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
        ]
        mock_database_repository.fetch.return_value = mock_rows
        
        result = await repository.get_active_endpoints(context_id)
        
        assert len(result) == 1
        assert result[0].is_active is True
        mock_database_repository.fetch.assert_called_once()


class TestWebhookSubscriptionRepository:
    """Test webhook subscription repository operations."""
    
    @pytest.fixture
    def repository(self, mock_database_repository):
        return WebhookSubscriptionRepository(mock_database_repository)
    
    @pytest.mark.asyncio
    async def test_get_matching_subscriptions(self, repository, sample_domain_event, mock_database_repository):
        """Test getting matching subscriptions for an event."""
        mock_rows = [
            {
                'id': uuid4(),
                'endpoint_id': uuid4(),
                'event_type_id': uuid4(),
                'event_type': 'test.event',
                'event_filters': {'status': {'$eq': 'active'}},
                'is_active': True,
                'context_id': sample_domain_event.context_id,
                'subscription_name': 'Test Subscription',
                'description': 'Test subscription',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
        ]
        mock_database_repository.fetch.return_value = mock_rows
        
        result = await repository.get_matching_subscriptions(
            event_type=sample_domain_event.event_type,
            context_id=sample_domain_event.context_id
        )
        
        assert len(result) == 1
        assert result[0].event_type == 'test.event'
        mock_database_repository.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_soft_delete(self, repository, sample_subscription_id, mock_database_repository):
        """Test soft deleting a subscription."""
        mock_database_repository.execute.return_value = None
        
        await repository.soft_delete(sample_subscription_id)
        
        mock_database_repository.execute.assert_called_once()
        call_args = mock_database_repository.execute.call_args[0]
        assert "UPDATE" in call_args[0]
        assert "deleted_at" in call_args[0]


class TestWebhookDeliveryRepository:
    """Test webhook delivery repository operations."""
    
    @pytest.fixture
    def repository(self, mock_database_repository):
        return WebhookDeliveryRepository(mock_database_repository)
    
    @pytest.mark.asyncio
    async def test_get_pending_retries(self, repository, mock_database_repository):
        """Test getting pending retry deliveries."""
        mock_rows = [
            {
                'id': uuid4(),
                'webhook_endpoint_id': uuid4(),
                'webhook_event_id': uuid4(),
                'current_attempt': 1,
                'overall_status': DeliveryStatus.PENDING.value,
                'max_attempts': 3,
                'base_backoff_seconds': 5,
                'backoff_multiplier': 2.0,
                'next_retry_at': datetime.now(timezone.utc),
                'max_attempts_reached': False,
                'attempts': [],
                'created_at': datetime.now(timezone.utc)
            }
        ]
        mock_database_repository.fetch.return_value = mock_rows
        
        result = await repository.get_pending_retries(limit=10)
        
        assert len(result) == 1
        assert result[0].overall_status == DeliveryStatus.PENDING
        mock_database_repository.fetch.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_delivery(self, repository, sample_webhook_delivery, mock_database_repository):
        """Test updating a delivery."""
        mock_database_repository.execute.return_value = None
        
        await repository.update(sample_webhook_delivery)
        
        mock_database_repository.execute.assert_called_once()
        call_args = mock_database_repository.execute.call_args[0]
        assert "UPDATE" in call_args[0]
        assert "webhook_deliveries" in call_args[0]


class TestWebhookEventTypeRepository:
    """Test webhook event type repository operations."""
    
    @pytest.fixture
    def repository(self, mock_database_repository):
        return WebhookEventTypeRepository(mock_database_repository)
    
    @pytest.mark.asyncio
    async def test_get_by_event_type(self, repository, mock_database_repository):
        """Test getting webhook event type by event type string."""
        event_type = "test.event"
        mock_row = {
            'id': uuid4(),
            'event_type': event_type,
            'category': 'test',
            'display_name': 'Test Event',
            'description': 'A test event type',
            'is_enabled': True,
            'requires_verification': False,
            'payload_schema': {'type': 'object'},
            'example_payload': {'key': 'value'},
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        mock_database_repository.fetchrow.return_value = mock_row
        
        result = await repository.get_by_event_type(event_type)
        
        assert result is not None
        assert result.event_type == event_type
        mock_database_repository.fetchrow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_enabled_types(self, repository, mock_database_repository):
        """Test getting enabled event types."""
        mock_rows = [
            {
                'id': uuid4(),
                'event_type': 'test.event',
                'category': 'test',
                'display_name': 'Test Event',
                'description': 'A test event type',
                'is_enabled': True,
                'requires_verification': False,
                'payload_schema': {'type': 'object'},
                'example_payload': {'key': 'value'},
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
        ]
        mock_database_repository.fetch.return_value = mock_rows
        
        result = await repository.get_enabled_types()
        
        assert len(result) == 1
        assert result[0].is_enabled is True
        mock_database_repository.fetch.assert_called_once()


class TestRepositoryIntegration:
    """Test repository integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_event_processing_workflow(self, mock_database_repository):
        """Test complete event processing workflow across repositories."""
        # Setup repositories
        event_repo = DomainEventRepository(mock_database_repository)
        subscription_repo = WebhookSubscriptionRepository(mock_database_repository)
        delivery_repo = WebhookDeliveryRepository(mock_database_repository)
        
        # Mock database responses
        event_id = EventId(uuid4())
        context_id = uuid4()
        
        # Mock unprocessed events
        mock_database_repository.fetch.return_value = [
            {
                'id': event_id.value,
                'event_type': 'test.event',
                'event_name': 'Test Event',
                'aggregate_id': uuid4(),
                'aggregate_type': 'test_aggregate',
                'aggregate_version': 1,
                'event_data': {'key': 'value'},
                'event_metadata': {'source': 'test'},
                'correlation_id': uuid4(),
                'causation_id': uuid4(),
                'triggered_by_user_id': uuid4(),
                'context_id': context_id,
                'occurred_at': datetime.now(timezone.utc),
                'created_at': datetime.now(timezone.utc),
                'processed_at': None
            }
        ]
        
        # Get unprocessed events
        events = await event_repo.get_unprocessed(limit=10)
        assert len(events) == 1
        
        # Mock matching subscriptions
        mock_database_repository.fetch.return_value = [
            {
                'id': uuid4(),
                'endpoint_id': uuid4(),
                'event_type_id': uuid4(),
                'event_type': 'test.event',
                'event_filters': {},
                'is_active': True,
                'context_id': context_id,
                'subscription_name': 'Test Subscription',
                'description': 'Test subscription',
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc)
            }
        ]
        
        # Get matching subscriptions
        subscriptions = await subscription_repo.get_matching_subscriptions(
            event_type=events[0].event_type,
            context_id=events[0].context_id
        )
        assert len(subscriptions) == 1
        
        # Mock execute for marking processed
        mock_database_repository.execute.return_value = None
        
        # Mark event as processed
        await event_repo.mark_as_processed(event_id)
        
        # Verify database interactions
        assert mock_database_repository.fetch.call_count >= 2
        assert mock_database_repository.execute.call_count >= 1