"""Tests for event adapters."""

import pytest
import asyncio
import json
import hashlib
import hmac
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession, ClientResponse, ClientConnectorError, ClientTimeout
from aiohttp.client_exceptions import ServerTimeoutError

from neo_commons.features.events.adapters.http_webhook_adapter import HttpWebhookAdapter
from neo_commons.features.events.entities.webhook_endpoint import WebhookEndpoint
from neo_commons.features.events.entities.domain_event import DomainEvent
from neo_commons.features.events.entities.webhook_delivery_attempt import (
    WebhookDeliveryAttempt, AttemptStatus
)
from neo_commons.core.value_objects import (
    EventId, WebhookEndpointId, UserId, EventType
)


class TestHttpWebhookAdapter:
    """Test HTTP webhook adapter functionality."""
    
    @pytest.fixture
    def adapter(self):
        """Create HTTP webhook adapter with test configuration."""
        return HttpWebhookAdapter(
            connection_pool_size=10,
            connection_pool_size_per_host=5,
            keep_alive_timeout=30,
            dns_cache_ttl=300
        )
    
    @pytest.fixture
    def sample_endpoint(self):
        """Create sample webhook endpoint."""
        return WebhookEndpoint(
            id=WebhookEndpointId(uuid4()),
            name="Test Webhook",
            description="Test webhook endpoint",
            endpoint_url="https://api.example.com/webhook",
            http_method="POST",
            secret_token="test-secret-123",
            signature_header="X-Webhook-Signature",
            custom_headers={"Authorization": "Bearer token123", "User-Agent": "NeoWebhook/1.0"},
            timeout_seconds=30,
            follow_redirects=False,
            verify_ssl=True,
            max_retry_attempts=3,
            retry_backoff_seconds=5,
            retry_backoff_multiplier=2.0,
            is_active=True,
            is_verified=True,
            created_by_user_id=UserId(uuid4()),
            context_id=uuid4(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
    
    @pytest.fixture
    def sample_event(self):
        """Create sample domain event."""
        return DomainEvent(
            id=EventId(uuid4()),
            event_type=EventType("test.event"),
            event_name="Test Event",
            aggregate_id=uuid4(),
            aggregate_type="test",
            aggregate_version=1,
            event_data={"key": "value", "number": 42},
            event_metadata={"source": "test", "version": "1.0"},
            correlation_id=uuid4(),
            causation_id=uuid4(),
            triggered_by_user_id=UserId(uuid4()),
            context_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
    
    @pytest.mark.asyncio
    async def test_successful_webhook_delivery(self, adapter, sample_endpoint, sample_event):
        """Test successful webhook delivery."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"message": "success"}')
        mock_response.headers = {"Content-Type": "application/json"}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            with patch('time.time', side_effect=[1000.0, 1000.15]):  # 150ms response time
                result = await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        assert result.success is True
        assert result.status_code == 200
        assert result.response_body == '{"message": "success"}'
        assert result.response_time_ms == 150
        assert result.error_message is None
        
        # Verify request was made with correct parameters
        mock_session.request.assert_called_once()
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "https://api.example.com/webhook"
    
    @pytest.mark.asyncio
    async def test_webhook_signature_generation(self, adapter, sample_endpoint, sample_event):
        """Test HMAC signature generation for webhook security."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            result = await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        # Verify signature was included in headers
        call_args = mock_session.request.call_args
        headers = call_args[1]['headers']
        
        assert 'X-Webhook-Signature' in headers
        
        # Verify signature format
        signature = headers['X-Webhook-Signature']
        assert signature.startswith('sha256=')
        
        # Verify signature is correct
        payload = json.dumps({
            'event_id': str(sample_event.id.value),
            'event_type': sample_event.event_type.value,
            'event_name': sample_event.event_name,
            'event_data': sample_event.event_data,
            'event_metadata': sample_event.event_metadata,
            'occurred_at': sample_event.occurred_at.isoformat(),
            'context_id': str(sample_event.context_id)
        }, sort_keys=True)
        
        expected_signature = hmac.new(
            sample_endpoint.secret_token.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        assert signature == f"sha256={expected_signature}"
    
    @pytest.mark.asyncio
    async def test_custom_headers_included(self, adapter, sample_endpoint, sample_event):
        """Test that custom headers are included in the request."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        # Verify custom headers were included
        call_args = mock_session.request.call_args
        headers = call_args[1]['headers']
        
        assert headers['Authorization'] == 'Bearer token123'
        assert headers['User-Agent'] == 'NeoWebhook/1.0'
        assert headers['Content-Type'] == 'application/json'
    
    @pytest.mark.asyncio
    async def test_http_timeout_handling(self, adapter, sample_endpoint, sample_event):
        """Test handling of HTTP timeout errors."""
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(side_effect=asyncio.TimeoutError("Request timeout"))
            
            result = await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        assert result.success is False
        assert result.status_code is None
        assert "timeout" in result.error_message.lower()
        assert result.response_time_ms > 0  # Should still record time
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, adapter, sample_endpoint, sample_event):
        """Test handling of connection errors."""
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(
                side_effect=ClientConnectorError(connection_key=None, os_error=OSError("Connection refused"))
            )
            
            result = await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        assert result.success is False
        assert result.status_code is None
        assert "connection" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_http_error_status_codes(self, adapter, sample_endpoint, sample_event):
        """Test handling of HTTP error status codes."""
        error_codes = [400, 401, 403, 404, 500, 502, 503, 504]
        
        for status_code in error_codes:
            mock_response = MagicMock(spec=ClientResponse)
            mock_response.status = status_code
            mock_response.text = AsyncMock(return_value=f'Error {status_code}')
            mock_response.headers = {}
            
            with patch.object(adapter, '_session') as mock_session:
                mock_session.request = AsyncMock(return_value=mock_response)
                
                result = await adapter.deliver_webhook(sample_endpoint, sample_event)
            
            assert result.success is False
            assert result.status_code == status_code
            assert result.response_body == f'Error {status_code}'
    
    @pytest.mark.asyncio
    async def test_ssl_verification_settings(self, sample_endpoint, sample_event):
        """Test SSL verification settings."""
        # Test with SSL verification enabled (default)
        adapter_ssl_on = HttpWebhookAdapter()
        
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter_ssl_on, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            await adapter_ssl_on.deliver_webhook(sample_endpoint, sample_event)
        
        # Verify SSL verification was enabled
        call_args = mock_session.request.call_args
        assert call_args[1]['ssl'] is True
        
        # Test with SSL verification disabled
        sample_endpoint.verify_ssl = False
        
        with patch.object(adapter_ssl_on, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            await adapter_ssl_on.deliver_webhook(sample_endpoint, sample_event)
        
        # Verify SSL verification was disabled
        call_args = mock_session.request.call_args
        assert call_args[1]['ssl'] is False
    
    @pytest.mark.asyncio
    async def test_redirect_handling(self, adapter, sample_endpoint, sample_event):
        """Test redirect handling settings."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        # Verify redirect handling
        call_args = mock_session.request.call_args
        assert call_args[1]['allow_redirects'] is False
        
        # Test with redirects enabled
        sample_endpoint.follow_redirects = True
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        call_args = mock_session.request.call_args
        assert call_args[1]['allow_redirects'] is True
    
    @pytest.mark.asyncio
    async def test_endpoint_verification(self, adapter, sample_endpoint):
        """Test webhook endpoint verification."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            result = await adapter.verify_endpoint(sample_endpoint)
        
        assert result.success is True
        assert result.status_code == 200
        
        # Verify verification request was made with HEAD method
        call_args = mock_session.request.call_args
        assert call_args[0][0] == "HEAD"
        assert call_args[0][1] == sample_endpoint.endpoint_url
    
    @pytest.mark.asyncio
    async def test_health_check(self, adapter, sample_endpoint):
        """Test adapter health check functionality."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            is_healthy = await adapter.health_check()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_connection_statistics(self, adapter):
        """Test connection pool statistics."""
        # Mock connection pool statistics
        mock_connector = MagicMock()
        mock_connector._conns = {
            ('example.com', 443, True): [MagicMock(), MagicMock()],
            ('api.test.com', 443, True): [MagicMock()]
        }
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.connector = mock_connector
            
            stats = await adapter.get_connection_stats()
        
        assert 'total_connections' in stats
        assert 'connection_reuse_rate' in stats
        assert isinstance(stats['total_connections'], int)
    
    @pytest.mark.asyncio
    async def test_concurrent_deliveries(self, adapter, sample_endpoint):
        """Test concurrent webhook deliveries."""
        # Create multiple events
        events = []
        for i in range(5):
            event = DomainEvent(
                id=EventId(uuid4()),
                event_type=EventType("concurrent.test"),
                event_name=f"Concurrent Test Event {i}",
                aggregate_id=uuid4(),
                aggregate_type="test",
                aggregate_version=1,
                event_data={"index": i},
                event_metadata={"source": "concurrent_test"},
                correlation_id=uuid4(),
                causation_id=uuid4(),
                triggered_by_user_id=UserId(uuid4()),
                context_id=uuid4(),
                occurred_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc)
            )
            events.append(event)
        
        # Mock responses
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            # Deliver webhooks concurrently
            tasks = [
                adapter.deliver_webhook(sample_endpoint, event)
                for event in events
            ]
            
            results = await asyncio.gather(*tasks)
        
        # Verify all deliveries were successful
        assert len(results) == 5
        for result in results:
            assert result.success is True
            assert result.status_code == 200
        
        # Verify all requests were made
        assert mock_session.request.call_count == 5
    
    @pytest.mark.asyncio
    async def test_payload_serialization(self, adapter, sample_endpoint, sample_event):
        """Test webhook payload serialization."""
        mock_response = MagicMock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        mock_response.headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(return_value=mock_response)
            
            await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        # Verify payload was properly serialized
        call_args = mock_session.request.call_args
        payload_data = call_args[1]['data']
        
        # Should be valid JSON
        payload_dict = json.loads(payload_data)
        
        assert payload_dict['event_id'] == str(sample_event.id.value)
        assert payload_dict['event_type'] == sample_event.event_type.value
        assert payload_dict['event_name'] == sample_event.event_name
        assert payload_dict['event_data'] == sample_event.event_data
        assert payload_dict['event_metadata'] == sample_event.event_metadata
        assert payload_dict['context_id'] == str(sample_event.context_id)
        assert 'occurred_at' in payload_dict
    
    @pytest.mark.asyncio
    async def test_adapter_cleanup(self, adapter):
        """Test proper cleanup of adapter resources."""
        # Ensure session is created
        await adapter._ensure_session()
        assert adapter._session is not None
        
        # Mock session close method
        with patch.object(adapter._session, 'close') as mock_close:
            await adapter.close()
            mock_close.assert_called_once()
        
        assert adapter._session is None
    
    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, adapter, sample_endpoint, sample_event):
        """Test retry mechanism with exponential backoff."""
        # Mock first two requests to fail, third to succeed
        responses = [
            AsyncMock(side_effect=ClientConnectorError(connection_key=None, os_error=OSError("Connection refused"))),
            AsyncMock(side_effect=asyncio.TimeoutError("Timeout")),
            MagicMock(spec=ClientResponse)
        ]
        
        # Configure successful response
        responses[2].status = 200
        responses[2].text = AsyncMock(return_value="OK")
        responses[2].headers = {}
        
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request.side_effect = responses
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        # Should eventually succeed after retries
        assert result.success is True
        assert result.status_code == 200
        
        # Verify exponential backoff was used
        expected_delays = [5, 10]  # 5 * 1, 5 * 2
        actual_delays = [call[0][0] for call in mock_sleep.call_args_list]
        
        for expected, actual in zip(expected_delays, actual_delays):
            assert actual >= expected * 0.8  # Allow some jitter
            assert actual <= expected * 1.2
    
    @pytest.mark.asyncio
    async def test_max_retry_attempts_reached(self, adapter, sample_endpoint, sample_event):
        """Test behavior when maximum retry attempts are reached."""
        # Configure endpoint with max 2 retry attempts
        sample_endpoint.max_retry_attempts = 2
        
        # Mock all requests to fail
        with patch.object(adapter, '_session') as mock_session:
            mock_session.request = AsyncMock(
                side_effect=ClientConnectorError(connection_key=None, os_error=OSError("Connection refused"))
            )
            
            with patch('asyncio.sleep') as mock_sleep:
                result = await adapter.deliver_webhook(sample_endpoint, sample_event)
        
        # Should fail after max attempts
        assert result.success is False
        assert "max retry attempts" in result.error_message.lower()
        
        # Verify correct number of attempts (initial + retries)
        assert mock_session.request.call_count == 3  # 1 initial + 2 retries
        
        # Verify correct number of sleep calls (one less than attempts)
        assert mock_sleep.call_count == 2