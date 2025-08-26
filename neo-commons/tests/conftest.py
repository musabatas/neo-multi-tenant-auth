"""Pytest configuration and fixtures for neo-commons tests."""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from neo_commons.core.value_objects import (
    EventId, WebhookEndpointId, WebhookDeliveryId, WebhookEventTypeId,
    WebhookSubscriptionId, UserId, TenantId, OrganizationId, EventType
)
from neo_commons.features.events.entities.domain_event import DomainEvent
from neo_commons.features.events.entities.webhook_endpoint import WebhookEndpoint
from neo_commons.features.events.entities.webhook_event_type import WebhookEventType
from neo_commons.features.events.entities.webhook_subscription import WebhookSubscription
from neo_commons.features.events.entities.webhook_delivery import WebhookDelivery, DeliveryStatus


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_database_repository():
    """Mock database repository for testing."""
    mock_db = AsyncMock()
    mock_db.fetchrow = AsyncMock()
    mock_db.fetch = AsyncMock()
    mock_db.execute = AsyncMock()
    return mock_db


@pytest.fixture
def sample_event_id():
    """Sample event ID for testing."""
    return EventId(uuid4())


@pytest.fixture
def sample_endpoint_id():
    """Sample webhook endpoint ID for testing."""
    return WebhookEndpointId(uuid4())


@pytest.fixture
def sample_delivery_id():
    """Sample webhook delivery ID for testing."""
    return WebhookDeliveryId(uuid4())


@pytest.fixture
def sample_event_type_id():
    """Sample webhook event type ID for testing."""
    return WebhookEventTypeId(uuid4())


@pytest.fixture
def sample_subscription_id():
    """Sample webhook subscription ID for testing."""
    return WebhookSubscriptionId(uuid4())


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return UserId(uuid4())


@pytest.fixture
def sample_organization_id():
    """Sample organization ID for testing."""
    return OrganizationId(uuid4())


@pytest.fixture
def sample_domain_event(sample_event_id, sample_user_id, sample_organization_id):
    """Sample domain event for testing."""
    return DomainEvent(
        id=sample_event_id,
        event_type=EventType("test.event"),
        event_name="Test Event",
        aggregate_id=uuid4(),
        aggregate_type="test_aggregate",
        aggregate_version=1,
        event_data={"key": "value", "number": 42},
        event_metadata={"source": "test", "version": "1.0"},
        correlation_id=uuid4(),
        causation_id=uuid4(),
        triggered_by_user_id=sample_user_id,
        context_id=sample_organization_id.value,
        occurred_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_webhook_endpoint(sample_endpoint_id, sample_user_id, sample_organization_id):
    """Sample webhook endpoint for testing."""
    return WebhookEndpoint(
        id=sample_endpoint_id,
        name="Test Webhook",
        description="Test webhook endpoint",
        endpoint_url="https://api.example.com/webhook",
        http_method="POST",
        secret_token="test-secret-token",
        signature_header="X-Webhook-Signature",
        custom_headers={"Authorization": "Bearer token123"},
        timeout_seconds=30,
        follow_redirects=False,
        verify_ssl=True,
        max_retry_attempts=3,
        retry_backoff_seconds=5,
        retry_backoff_multiplier=2.0,
        is_active=True,
        is_verified=True,
        created_by_user_id=sample_user_id,
        context_id=sample_organization_id.value,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_webhook_event_type(sample_event_type_id):
    """Sample webhook event type for testing."""
    return WebhookEventType(
        id=sample_event_type_id,
        event_type="test.event",
        category="test",
        display_name="Test Event",
        description="A test event type",
        is_enabled=True,
        requires_verification=False,
        payload_schema={"type": "object", "properties": {"key": {"type": "string"}}},
        example_payload={"key": "example_value"},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_webhook_subscription(
    sample_subscription_id, 
    sample_endpoint_id, 
    sample_event_type_id,
    sample_organization_id
):
    """Sample webhook subscription for testing."""
    return WebhookSubscription(
        id=sample_subscription_id,
        endpoint_id=sample_endpoint_id,
        event_type_id=sample_event_type_id,
        event_type="test.event",
        event_filters={"status": {"$eq": "active"}},
        is_active=True,
        context_id=sample_organization_id.value,
        subscription_name="Test Subscription",
        description="A test subscription",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def sample_webhook_delivery(
    sample_delivery_id,
    sample_endpoint_id,
    sample_event_id
):
    """Sample webhook delivery for testing."""
    return WebhookDelivery(
        id=sample_delivery_id,
        webhook_endpoint_id=sample_endpoint_id,
        webhook_event_id=sample_event_id,
        current_attempt=1,
        overall_status=DeliveryStatus.PENDING,
        max_attempts=3,
        base_backoff_seconds=5,
        backoff_multiplier=2.0,
        next_retry_at=None,
        max_attempts_reached=False,
        attempts=[],
        created_at=datetime.now(timezone.utc)
    )


@pytest.fixture
def mock_event_repository():
    """Mock event repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_unprocessed = AsyncMock()
    repo.mark_as_processed = AsyncMock()
    repo.mark_multiple_as_processed = AsyncMock()
    return repo


@pytest.fixture
def mock_webhook_endpoint_repository():
    """Mock webhook endpoint repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_active_endpoints = AsyncMock()
    repo.get_by_context = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_webhook_delivery_repository():
    """Mock webhook delivery repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_pending_retries = AsyncMock()
    repo.update = AsyncMock()
    return repo


@pytest.fixture
def mock_webhook_event_type_repository():
    """Mock webhook event type repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_event_type = AsyncMock()
    repo.get_enabled_types = AsyncMock()
    return repo


@pytest.fixture
def mock_webhook_subscription_repository():
    """Mock webhook subscription repository for testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_endpoint_id = AsyncMock()
    repo.get_matching_subscriptions = AsyncMock()
    repo.update = AsyncMock()
    repo.soft_delete = AsyncMock()
    return repo


@pytest.fixture
def mock_http_adapter():
    """Mock HTTP webhook adapter for testing."""
    adapter = AsyncMock()
    adapter.deliver_webhook = AsyncMock()
    adapter.verify_endpoint = AsyncMock()
    adapter.health_check = AsyncMock()
    adapter.get_connection_stats = AsyncMock(return_value={
        "total_requests": 0,
        "connection_reuses": 0,
        "connection_reuse_rate": 0.0,
        "error_rate": 0.0
    })
    return adapter