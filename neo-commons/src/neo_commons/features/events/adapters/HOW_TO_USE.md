# Event Adapters - HOW TO USE

This documentation provides comprehensive guidance for using the event adapters in the NeoMultiTenant platform's event system. The adapters handle external integrations and infrastructure patterns for event delivery.

## Overview

The adapters module provides infrastructure components that interface with external systems for event delivery and processing. Currently, it contains the HTTP webhook adapter which handles HTTP-based webhook delivery with enterprise-grade features including connection pooling, retry logic, and performance monitoring.

**Key Purpose**: Separate infrastructure concerns from domain logic, providing pluggable adapters that can be easily tested, replaced, or extended while maintaining consistent interfaces through protocol-based design.

## Architecture

### Design Patterns

#### Adapter Pattern
- **Purpose**: Translate domain entities into external service calls
- **Implementation**: `HttpWebhookAdapter` adapts webhook delivery entities to HTTP requests
- **Benefits**: Decouples domain logic from external service APIs

#### Connection Pool Pattern
- **Purpose**: Optimize HTTP connections through reuse and pooling
- **Implementation**: aiohttp `TCPConnector` with configurable pool limits
- **Benefits**: Improved performance, reduced latency, efficient resource usage

#### Circuit Breaker Pattern (Implicit)
- **Purpose**: Handle connection failures gracefully
- **Implementation**: Built-in connection pooling with timeout and error handling
- **Benefits**: System resilience and cascading failure prevention

#### Observer Pattern Integration
- **Purpose**: Monitoring and metrics collection
- **Implementation**: Connection statistics and performance tracking
- **Benefits**: Observability and performance optimization

## Core Components

### HttpWebhookAdapter

The primary adapter for HTTP-based webhook delivery with enterprise features.

#### Key Features

- **HTTP/1.1 and HTTP/2 Support**: Automatic protocol negotiation
- **Connection Pooling**: Configurable connection reuse with per-host limits
- **DNS Caching**: Reduces DNS lookup overhead
- **Keep-Alive Connections**: Optimizes connection reuse
- **Automatic Cleanup**: Handles closed connection cleanup
- **Performance Monitoring**: Tracks connection reuse, response times, and error rates
- **Flexible Timeouts**: Configurable connection, read, and total timeouts

#### Protocol Integration

The adapter implements implicit contracts expected by webhook delivery services:

```python
# Expected interface (implicit protocol)
async def deliver_webhook(delivery: WebhookDelivery, endpoint: WebhookEndpoint) -> Tuple[bool, Dict[str, Any]]
async def verify_endpoint(endpoint: WebhookEndpoint, test_payload: Optional[Dict] = None) -> Tuple[bool, Dict[str, Any]]
async def test_connectivity(url: str, timeout_seconds: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]
```

## Installation/Setup

### Basic Setup

```python
from neo_commons.features.events.adapters import HttpWebhookAdapter
from neo_commons.features.events.entities import WebhookDelivery, WebhookEndpoint

# Create adapter with default configuration
adapter = HttpWebhookAdapter()

# Use as async context manager (recommended)
async with adapter as http_adapter:
    success, response_info = await http_adapter.deliver_webhook(delivery, endpoint)
```

### Advanced Configuration

```python
# Create adapter with optimized settings for high-throughput
adapter = HttpWebhookAdapter(
    default_timeout_seconds=30,           # Request timeout
    max_concurrent_requests=20,           # Concurrent request limit
    connection_pool_size=200,             # Total connection pool
    connection_pool_size_per_host=50,     # Per-host connection limit
    keep_alive_timeout=60,                # Keep-alive duration
    dns_cache_ttl=600,                    # DNS cache TTL (10 minutes)
    enable_cleanup_closed=True            # Automatic cleanup
)
```

### Integration with Dependency Injection

```python
from typing import Protocol

class WebhookAdapter(Protocol):
    async def deliver_webhook(self, delivery: WebhookDelivery, endpoint: WebhookEndpoint) -> Tuple[bool, Dict[str, Any]]:
        ...

class WebhookDeliveryService:
    def __init__(self, adapter: WebhookAdapter):
        self._adapter = adapter
    
    async def deliver(self, delivery: WebhookDelivery, endpoint: WebhookEndpoint):
        return await self._adapter.deliver_webhook(delivery, endpoint)

# Service instantiation
http_adapter = HttpWebhookAdapter(max_concurrent_requests=15)
delivery_service = WebhookDeliveryService(http_adapter)
```

## Usage Examples

### Basic Webhook Delivery

```python
from neo_commons.features.events.adapters import HttpWebhookAdapter
from neo_commons.features.events.entities import WebhookDelivery, WebhookEndpoint, DeliveryStatus
from neo_commons.core.value_objects import WebhookDeliveryId, WebhookEndpointId, EventId, UserId
import asyncio

async def deliver_single_webhook():
    # Create webhook delivery entity
    delivery = WebhookDelivery(
        id=WebhookDeliveryId.generate(),
        webhook_endpoint_id=WebhookEndpointId.generate(),
        webhook_event_id=EventId.generate(),
        current_attempt=1,
        overall_status=DeliveryStatus.PENDING,
        max_attempts=3,
        base_backoff_seconds=5,
        backoff_multiplier=2.0
    )
    
    # Create webhook endpoint entity
    endpoint = WebhookEndpoint(
        id=WebhookEndpointId.generate(),
        name="Order Processing Webhook",
        endpoint_url="https://api.example.com/webhooks/orders",
        http_method="POST",
        secret_token="secure-token-here",
        timeout_seconds=30,
        created_by_user_id=UserId.generate()
    )
    
    # Deliver webhook
    async with HttpWebhookAdapter() as adapter:
        success, response_info = await adapter.deliver_webhook(delivery, endpoint)
        
        if success:
            print(f"✅ Delivery successful: {response_info['status_code']}")
            print(f"Response time: {response_info['response_time_ms']}ms")
        else:
            print(f"❌ Delivery failed: {response_info.get('error_message')}")

# Run the example
asyncio.run(deliver_single_webhook())
```

### High-Performance Batch Processing

```python
import asyncio
from typing import List, Tuple

async def process_webhook_batch(deliveries_and_endpoints: List[Tuple[WebhookDelivery, WebhookEndpoint]]):
    # Configure for high throughput
    adapter = HttpWebhookAdapter(
        max_concurrent_requests=50,        # High concurrency
        connection_pool_size=300,          # Large pool
        connection_pool_size_per_host=100, # Per-host optimization
        keep_alive_timeout=120,            # Extended keep-alive
        dns_cache_ttl=900                  # 15-minute DNS cache
    )
    
    async with adapter:
        # Process batch concurrently
        tasks = []
        for delivery, endpoint in deliveries_and_endpoints:
            task = adapter.deliver_webhook(delivery, endpoint)
            tasks.append(task)
        
        # Execute all deliveries concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_deliveries = 0
        failed_deliveries = 0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Delivery {i} raised exception: {result}")
                failed_deliveries += 1
            else:
                success, response_info = result
                if success:
                    successful_deliveries += 1
                else:
                    failed_deliveries += 1
                    print(f"Delivery {i} failed: {response_info.get('error_message')}")
        
        print(f"Batch complete: {successful_deliveries} successful, {failed_deliveries} failed")
        
        # Get connection statistics
        stats = adapter.get_connection_stats()
        print(f"Connection reuse rate: {stats['connection_reuse_rate']:.2%}")
        print(f"Error rate: {stats['error_rate']:.2%}")

# Example usage
async def run_batch_example():
    # Create sample batch (you would load real data)
    batch = []
    for i in range(100):
        delivery = WebhookDelivery(
            id=WebhookDeliveryId.generate(),
            webhook_endpoint_id=WebhookEndpointId.generate(),
            webhook_event_id=EventId.generate()
        )
        endpoint = WebhookEndpoint(
            id=WebhookEndpointId.generate(),
            name=f"Webhook {i}",
            endpoint_url=f"https://api{i % 5}.example.com/webhook",  # Distribute across hosts
            secret_token="secure-token",
            created_by_user_id=UserId.generate()
        )
        batch.append((delivery, endpoint))
    
    await process_webhook_batch(batch)

asyncio.run(run_batch_example())
```

### Endpoint Verification

```python
async def verify_webhook_endpoints(endpoints: List[WebhookEndpoint]):
    """Verify multiple webhook endpoints for connectivity and configuration."""
    
    adapter = HttpWebhookAdapter(
        default_timeout_seconds=10,  # Shorter timeout for verification
        max_concurrent_requests=10   # Moderate concurrency for verification
    )
    
    async with adapter:
        verification_results = []
        
        for endpoint in endpoints:
            print(f"Verifying: {endpoint.name} ({endpoint.endpoint_url})")
            
            # Test basic connectivity
            connectivity_success, connectivity_info = await adapter.test_connectivity(
                endpoint.endpoint_url, 
                timeout_seconds=5
            )
            
            if not connectivity_success:
                print(f"❌ Connectivity failed: {connectivity_info.get('error')}")
                continue
            
            # Test endpoint verification with payload
            test_payload = {
                "event_type": "verification.test",
                "timestamp": "2024-01-15T10:30:00Z",
                "data": {"test": True}
            }
            
            verify_success, verify_info = await adapter.verify_endpoint(
                endpoint, 
                test_payload
            )
            
            result = {
                "endpoint": endpoint.name,
                "url": endpoint.endpoint_url,
                "connectivity": connectivity_success,
                "verification": verify_success,
                "response_time_ms": verify_info.get('response_time_ms'),
                "status_code": verify_info.get('status_code')
            }
            
            if verify_success:
                print(f"✅ Verification successful: HTTP {result['status_code']} in {result['response_time_ms']}ms")
            else:
                print(f"❌ Verification failed: {verify_info.get('error_message', 'Unknown error')}")
            
            verification_results.append(result)
        
        return verification_results
```

### Custom Headers and Authentication

```python
async def deliver_with_custom_auth():
    """Example showing custom headers and authentication patterns."""
    
    # Endpoint with custom authentication headers
    endpoint = WebhookEndpoint(
        id=WebhookEndpointId.generate(),
        name="Authenticated API Webhook",
        endpoint_url="https://secure-api.example.com/webhooks/events",
        secret_token="webhook-hmac-secret",
        custom_headers={
            "X-API-Key": "your-api-key-here",
            "X-Client-Version": "v1.2.3",
            "Authorization": "Bearer jwt-token-here"
        },
        timeout_seconds=45,
        created_by_user_id=UserId.generate()
    )
    
    delivery = WebhookDelivery(
        id=WebhookDeliveryId.generate(),
        webhook_endpoint_id=endpoint.id,
        webhook_event_id=EventId.generate(),
        payload={
            "event_type": "order.completed",
            "order_id": "order-123",
            "customer_id": "cust-456",
            "total_amount": 99.99,
            "currency": "USD"
        }
    )
    
    async with HttpWebhookAdapter() as adapter:
        success, response_info = await adapter.deliver_webhook(delivery, endpoint)
        
        print(f"Delivery result: {'Success' if success else 'Failed'}")
        print(f"Request headers included custom auth: {bool(endpoint.custom_headers)}")
        print(f"Response headers: {response_info.get('response_headers', {})}")
        
        # Check if connection was reused (performance indicator)
        connection_reused = response_info.get('connection_reused', False)
        print(f"Connection reused: {'Yes' if connection_reused else 'No'}")
```

## API Reference

### HttpWebhookAdapter Class

#### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `default_timeout_seconds` | `int` | `30` | Default request timeout |
| `max_concurrent_requests` | `int` | `10` | Maximum concurrent HTTP requests |
| `connection_pool_size` | `int` | `100` | Total connection pool size |
| `connection_pool_size_per_host` | `int` | `30` | Maximum connections per host |
| `keep_alive_timeout` | `int` | `30` | Keep-alive timeout in seconds |
| `dns_cache_ttl` | `int` | `300` | DNS cache TTL in seconds |
| `enable_cleanup_closed` | `bool` | `True` | Enable automatic cleanup of closed connections |

#### Primary Methods

##### `async deliver_webhook(delivery: WebhookDelivery, endpoint: WebhookEndpoint) -> Tuple[bool, Dict[str, Any]]`

Delivers a webhook using HTTP request with full retry and monitoring support.

**Parameters:**
- `delivery`: WebhookDelivery entity with attempt tracking
- `endpoint`: WebhookEndpoint entity with configuration

**Returns:**
- `success`: Boolean indicating delivery success (2xx status codes)
- `response_info`: Dictionary with detailed response information

**Response Info Structure:**
```python
{
    "attempt": 1,                          # Attempt number
    "url": "https://api.example.com/hook", # Target URL
    "method": "POST",                      # HTTP method
    "started_at": "2024-01-15T10:30:00Z",  # Start timestamp
    "status_code": 200,                    # HTTP status code
    "response_time_ms": 150,               # Response time in milliseconds
    "response_headers": {...},             # Response headers dict
    "response_body": "...",                # Response body (truncated if > 10KB)
    "completed_at": "2024-01-15T10:30:01Z", # Completion timestamp
    "connection_reused": True,             # Whether connection was reused
    "compression_used": False              # Whether response was compressed
}
```

##### `async verify_endpoint(endpoint: WebhookEndpoint, test_payload: Optional[Dict[str, Any]] = None) -> Tuple[bool, Dict[str, Any]]`

Verifies endpoint connectivity and responsiveness with test payload.

**Parameters:**
- `endpoint`: WebhookEndpoint to verify
- `test_payload`: Optional custom test payload (defaults to verification payload)

**Returns:**
- `success`: Boolean indicating verification success (< 500 status codes)
- `verification_info`: Dictionary with verification details

##### `async test_connectivity(url: str, timeout_seconds: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]`

Tests basic connectivity to a URL using HEAD request.

**Parameters:**
- `url`: URL to test connectivity
- `timeout_seconds`: Optional timeout override

**Returns:**
- `success`: Boolean indicating connectivity success
- `connectivity_info`: Dictionary with connectivity test results

##### `async health_check() -> Dict[str, Any]`

Performs comprehensive health check including connection pool metrics.

**Returns:**
Dictionary with health status, connection pool information, and performance metrics.

##### `get_connection_stats() -> Dict[str, Any]`

Retrieves current connection statistics and performance metrics.

**Returns:**
```python
{
    "total_requests": 1234,           # Total requests made
    "connection_reuses": 1100,        # Successful connection reuses
    "dns_cache_hits": 980,            # DNS cache hits
    "connection_errors": 45,          # Connection errors encountered
    "pool_exhausted_count": 2,        # Pool exhaustion events
    "connection_reuse_rate": 0.891,   # Reuse rate (0.0-1.0)
    "error_rate": 0.036              # Error rate (0.0-1.0)
}
```

## Configuration

### Environment-Specific Configuration

The adapter can be optimized for different environments:

```python
# Development environment (permissive, debugging-friendly)
dev_adapter = HttpWebhookAdapter(
    default_timeout_seconds=60,      # Longer timeouts for debugging
    max_concurrent_requests=5,       # Lower concurrency
    connection_pool_size=20,         # Smaller pool
    dns_cache_ttl=60                 # Shorter DNS cache
)

# Production environment (high-performance, optimized)
prod_adapter = HttpWebhookAdapter(
    default_timeout_seconds=30,      # Balanced timeout
    max_concurrent_requests=100,     # High concurrency
    connection_pool_size=500,        # Large pool
    connection_pool_size_per_host=50, # Per-host optimization
    keep_alive_timeout=300,          # Extended keep-alive
    dns_cache_ttl=1800              # 30-minute DNS cache
)

# Testing environment (fast, isolated)
test_adapter = HttpWebhookAdapter(
    default_timeout_seconds=5,       # Fast timeouts
    max_concurrent_requests=3,       # Limited concurrency
    connection_pool_size=10,         # Minimal pool
    enable_cleanup_closed=False      # Disable cleanup for predictability
)
```

### Performance Tuning Guidelines

#### Connection Pool Sizing

```python
# Calculate optimal pool size based on expected load
expected_rps = 1000  # Requests per second
avg_response_time_s = 0.5  # Average response time

# Rule of thumb: pool_size = RPS * avg_response_time * safety_factor
optimal_pool_size = int(expected_rps * avg_response_time_s * 2)

adapter = HttpWebhookAdapter(
    connection_pool_size=optimal_pool_size,
    connection_pool_size_per_host=min(optimal_pool_size // 4, 100)
)
```

#### Timeout Configuration

```python
# Configure timeouts based on SLA requirements
adapter = HttpWebhookAdapter(
    default_timeout_seconds=30,      # Total request timeout
    # Internal timeouts are calculated:
    # - Connection timeout: min(10, total_timeout // 3)
    # - Socket read timeout: total_timeout
)
```

## Best Practices

### DRY-Compliant Usage

#### 1. Centralized Adapter Configuration

```python
# config/webhook_adapter.py
from neo_commons.features.events.adapters import HttpWebhookAdapter
from typing import Dict, Any

class WebhookAdapterFactory:
    """Factory for creating configured webhook adapters."""
    
    _adapters: Dict[str, HttpWebhookAdapter] = {}
    
    @classmethod
    def get_adapter(cls, profile: str = "default") -> HttpWebhookAdapter:
        """Get adapter for specific profile, creating if needed."""
        if profile not in cls._adapters:
            cls._adapters[profile] = cls._create_adapter(profile)
        return cls._adapters[profile]
    
    @classmethod
    def _create_adapter(cls, profile: str) -> HttpWebhookAdapter:
        """Create adapter with profile-specific configuration."""
        configs = {
            "default": {
                "max_concurrent_requests": 10,
                "connection_pool_size": 100
            },
            "high_throughput": {
                "max_concurrent_requests": 50,
                "connection_pool_size": 300,
                "connection_pool_size_per_host": 100
            },
            "low_latency": {
                "keep_alive_timeout": 120,
                "dns_cache_ttl": 900,
                "default_timeout_seconds": 15
            }
        }
        
        config = configs.get(profile, configs["default"])
        return HttpWebhookAdapter(**config)

# Usage across services
adapter = WebhookAdapterFactory.get_adapter("high_throughput")
```

#### 2. Reusable Delivery Patterns

```python
# services/webhook_patterns.py
from typing import List, Dict, Any, Optional
from neo_commons.features.events.adapters import HttpWebhookAdapter
from neo_commons.features.events.entities import WebhookDelivery, WebhookEndpoint

class WebhookDeliveryPatterns:
    """Reusable patterns for webhook delivery scenarios."""
    
    def __init__(self, adapter: HttpWebhookAdapter):
        self._adapter = adapter
    
    async def deliver_with_retry_logic(
        self,
        delivery: WebhookDelivery,
        endpoint: WebhookEndpoint,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """Standard delivery with built-in retry logic."""
        
        for attempt in range(max_retries):
            success, response_info = await self._adapter.deliver_webhook(delivery, endpoint)
            
            if success:
                return {"status": "success", "attempts": attempt + 1, "response": response_info}
            
            # Check if error is retryable
            if not self._is_retryable_error(response_info):
                break
                
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) * delivery.base_backoff_seconds
                await asyncio.sleep(min(wait_time, 300))  # Cap at 5 minutes
        
        return {"status": "failed", "attempts": max_retries, "response": response_info}
    
    async def batch_verify_endpoints(
        self,
        endpoints: List[WebhookEndpoint],
        concurrency_limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Verify multiple endpoints with controlled concurrency."""
        
        semaphore = asyncio.Semaphore(concurrency_limit)
        
        async def verify_single(endpoint: WebhookEndpoint) -> Dict[str, Any]:
            async with semaphore:
                success, info = await self._adapter.verify_endpoint(endpoint)
                return {
                    "endpoint_id": str(endpoint.id.value),
                    "endpoint_name": endpoint.name,
                    "success": success,
                    "response_time_ms": info.get('response_time_ms'),
                    "error": info.get('error_message') if not success else None
                }
        
        tasks = [verify_single(endpoint) for endpoint in endpoints]
        return await asyncio.gather(*tasks)
    
    def _is_retryable_error(self, response_info: Dict[str, Any]) -> bool:
        """Determine if error is retryable based on response."""
        
        # Network errors are retryable
        if response_info.get('error') in ['timeout', 'client_error']:
            return True
        
        # HTTP status codes that are retryable
        status_code = response_info.get('status_code')
        if status_code:
            retryable_codes = [429, 500, 502, 503, 504]
            return status_code in retryable_codes
        
        return False
```

#### 3. Monitoring and Observability Integration

```python
# monitoring/webhook_monitor.py
from typing import Dict, Any, List
import time
import logging

logger = logging.getLogger(__name__)

class WebhookPerformanceMonitor:
    """Monitor webhook adapter performance and health."""
    
    def __init__(self, adapter: HttpWebhookAdapter):
        self._adapter = adapter
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time_ms": 0,
            "connection_pool_stats": []
        }
    
    async def monitor_delivery(
        self,
        delivery: WebhookDelivery,
        endpoint: WebhookEndpoint
    ) -> Dict[str, Any]:
        """Monitor a single webhook delivery with metrics collection."""
        
        start_time = time.time()
        
        try:
            success, response_info = await self._adapter.deliver_webhook(delivery, endpoint)
            
            # Update metrics
            self._metrics["total_requests"] += 1
            if success:
                self._metrics["successful_requests"] += 1
            else:
                self._metrics["failed_requests"] += 1
            
            response_time_ms = response_info.get('response_time_ms', 0)
            self._metrics["total_response_time_ms"] += response_time_ms
            
            # Log performance metrics
            logger.info(
                f"Webhook delivery completed",
                extra={
                    "delivery_id": str(delivery.id.value),
                    "endpoint_url": endpoint.endpoint_url,
                    "success": success,
                    "response_time_ms": response_time_ms,
                    "connection_reused": response_info.get('connection_reused', False)
                }
            )
            
            return response_info
            
        except Exception as e:
            self._metrics["total_requests"] += 1
            self._metrics["failed_requests"] += 1
            
            logger.error(
                f"Webhook delivery exception: {e}",
                extra={
                    "delivery_id": str(delivery.id.value),
                    "endpoint_url": endpoint.endpoint_url,
                    "exception_type": type(e).__name__
                }
            )
            raise
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        
        total_requests = self._metrics["total_requests"]
        if total_requests == 0:
            return {"status": "no_requests", "metrics": self._metrics}
        
        success_rate = self._metrics["successful_requests"] / total_requests
        avg_response_time = self._metrics["total_response_time_ms"] / total_requests
        
        # Get connection stats from adapter
        connection_stats = self._adapter.get_connection_stats()
        
        return {
            "status": "active",
            "request_metrics": {
                "total_requests": total_requests,
                "success_rate": round(success_rate, 3),
                "average_response_time_ms": round(avg_response_time, 2)
            },
            "connection_metrics": connection_stats,
            "performance_indicators": {
                "high_error_rate": success_rate < 0.95,
                "slow_responses": avg_response_time > 1000,
                "connection_issues": connection_stats.get("error_rate", 0) > 0.1
            }
        }
```

### Dynamic and Flexible Usage

#### 1. Runtime Configuration

```python
# Dynamic adapter configuration based on runtime conditions
class DynamicWebhookAdapter:
    """Adapter wrapper that adjusts configuration based on runtime conditions."""
    
    def __init__(self):
        self._base_config = {
            "default_timeout_seconds": 30,
            "max_concurrent_requests": 10,
            "connection_pool_size": 100
        }
        self._current_adapter: Optional[HttpWebhookAdapter] = None
        self._last_config_hash: Optional[str] = None
    
    async def get_adapter(self, load_metrics: Dict[str, Any]) -> HttpWebhookAdapter:
        """Get adapter configured for current load conditions."""
        
        # Calculate configuration based on load metrics
        config = self._calculate_config(load_metrics)
        config_hash = hash(str(sorted(config.items())))
        
        # Create new adapter if configuration changed
        if config_hash != self._last_config_hash:
            if self._current_adapter:
                await self._current_adapter._close_session()
            
            self._current_adapter = HttpWebhookAdapter(**config)
            self._last_config_hash = config_hash
        
        return self._current_adapter
    
    def _calculate_config(self, load_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate optimal configuration based on load metrics."""
        
        config = self._base_config.copy()
        
        # Adjust based on current request rate
        current_rps = load_metrics.get('requests_per_second', 10)
        if current_rps > 100:
            config['max_concurrent_requests'] = min(50, current_rps // 2)
            config['connection_pool_size'] = min(500, current_rps * 3)
        
        # Adjust based on error rate
        error_rate = load_metrics.get('error_rate', 0)
        if error_rate > 0.1:  # High error rate
            config['default_timeout_seconds'] = min(60, config['default_timeout_seconds'] * 2)
        
        # Adjust based on response time
        avg_response_time = load_metrics.get('avg_response_time_ms', 500)
        if avg_response_time > 2000:  # Slow responses
            config['keep_alive_timeout'] = 60  # Shorter keep-alive
            config['dns_cache_ttl'] = 120      # Shorter DNS cache
        
        return config

# Usage
dynamic_adapter = DynamicWebhookAdapter()

# Get adapter optimized for current conditions
load_metrics = {
    "requests_per_second": 150,
    "error_rate": 0.05,
    "avg_response_time_ms": 800
}
adapter = await dynamic_adapter.get_adapter(load_metrics)
```

#### 2. Protocol-Based Integration

```python
# Protocol-based design for flexible adapter usage
from typing import Protocol, runtime_checkable

@runtime_checkable
class WebhookDeliveryAdapter(Protocol):
    """Protocol for webhook delivery adapters."""
    
    async def deliver_webhook(
        self, 
        delivery: WebhookDelivery, 
        endpoint: WebhookEndpoint
    ) -> Tuple[bool, Dict[str, Any]]:
        """Deliver webhook to endpoint."""
        ...
    
    async def verify_endpoint(
        self, 
        endpoint: WebhookEndpoint, 
        test_payload: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verify endpoint connectivity."""
        ...
    
    async def health_check(self) -> Dict[str, Any]:
        """Check adapter health."""
        ...

# Service using protocol-based dependency injection
class WebhookService:
    """Service that uses any webhook adapter implementation."""
    
    def __init__(self, adapter: WebhookDeliveryAdapter):
        self._adapter = adapter
    
    async def process_event(self, event: DomainEvent, endpoints: List[WebhookEndpoint]):
        """Process event by delivering to all endpoints."""
        
        results = []
        for endpoint in endpoints:
            # Create delivery entity
            delivery = WebhookDelivery(
                id=WebhookDeliveryId.generate(),
                webhook_endpoint_id=endpoint.id,
                webhook_event_id=event.id,
                payload=event.event_data
            )
            
            # Deliver using injected adapter
            success, info = await self._adapter.deliver_webhook(delivery, endpoint)
            results.append({
                "endpoint_id": str(endpoint.id.value),
                "success": success,
                "info": info
            })
        
        return results

# Multiple adapter implementations
http_adapter = HttpWebhookAdapter()
# Could also have: SqsWebhookAdapter, MockWebhookAdapter, etc.

# Service works with any adapter
service = WebhookService(http_adapter)
```

## Testing

### Unit Testing with Mocks

```python
# tests/test_webhook_adapter.py
import pytest
from unittest.mock import AsyncMock, patch
from neo_commons.features.events.adapters import HttpWebhookAdapter

@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session for testing."""
    session = AsyncMock()
    
    # Mock successful response
    response_mock = AsyncMock()
    response_mock.status = 200
    response_mock.headers = {"Content-Type": "application/json"}
    response_mock.text = AsyncMock(return_value='{"success": true}')
    
    session.request.return_value.__aenter__.return_value = response_mock
    session.closed = False
    
    return session

@pytest.mark.asyncio
async def test_successful_webhook_delivery(mock_aiohttp_session):
    """Test successful webhook delivery."""
    
    with patch('aiohttp.ClientSession', return_value=mock_aiohttp_session):
        adapter = HttpWebhookAdapter()
        
        # Create test entities
        delivery = WebhookDelivery(
            id=WebhookDeliveryId.generate(),
            webhook_endpoint_id=WebhookEndpointId.generate(),
            webhook_event_id=EventId.generate(),
            payload={"test": "data"}
        )
        
        endpoint = WebhookEndpoint(
            id=WebhookEndpointId.generate(),
            name="Test Endpoint",
            endpoint_url="https://api.example.com/webhook",
            secret_token="test-secret",
            created_by_user_id=UserId.generate()
        )
        
        # Execute delivery
        success, response_info = await adapter.deliver_webhook(delivery, endpoint)
        
        # Assertions
        assert success is True
        assert response_info["status_code"] == 200
        assert "response_time_ms" in response_info
        
        # Verify session was used correctly
        mock_aiohttp_session.request.assert_called_once()

@pytest.mark.asyncio
async def test_connection_pooling_statistics():
    """Test connection pooling and statistics tracking."""
    
    adapter = HttpWebhookAdapter(
        connection_pool_size=50,
        connection_pool_size_per_host=10
    )
    
    # Get initial stats
    initial_stats = adapter.get_connection_stats()
    assert initial_stats["total_requests"] == 0
    
    # Simulate requests (would need actual mock setup for full test)
    # This is a simplified example showing the pattern
    
    # Verify configuration was applied
    health_info = await adapter.health_check()
    assert health_info["connection_pool"]["total_pool_size"] == 50
    assert health_info["connection_pool"]["per_host_pool_size"] == 10
```

### Integration Testing

```python
# tests/integration/test_webhook_integration.py
import pytest
import asyncio
from aioresponses import aioresponses

@pytest.mark.asyncio
async def test_real_webhook_delivery_with_retry():
    """Integration test with real HTTP calls (mocked)."""
    
    with aioresponses() as m:
        # Mock webhook endpoint responses
        webhook_url = "https://api.example.com/webhook"
        
        # First attempt fails with 503
        m.post(webhook_url, status=503, payload={"error": "Service unavailable"})
        
        # Second attempt succeeds
        m.post(webhook_url, status=200, payload={"received": True})
        
        # Create adapter and entities
        adapter = HttpWebhookAdapter(default_timeout_seconds=10)
        
        delivery = WebhookDelivery(
            id=WebhookDeliveryId.generate(),
            webhook_endpoint_id=WebhookEndpointId.generate(),
            webhook_event_id=EventId.generate(),
            max_attempts=2,
            payload={"event": "test.event", "data": {"id": 123}}
        )
        
        endpoint = WebhookEndpoint(
            id=WebhookEndpointId.generate(),
            name="Integration Test Endpoint",
            endpoint_url=webhook_url,
            secret_token="integration-test-secret",
            created_by_user_id=UserId.generate()
        )
        
        # First delivery attempt (should fail)
        async with adapter:
            success, response_info = await adapter.deliver_webhook(delivery, endpoint)
            assert success is False
            assert response_info["status_code"] == 503
            
            # Retry delivery (should succeed)
            success, response_info = await adapter.deliver_webhook(delivery, endpoint)
            assert success is True
            assert response_info["status_code"] == 200
        
        # Verify both requests were made
        assert len(m.requests) == 2
```

### Performance Testing

```python
# tests/performance/test_webhook_performance.py
import pytest
import asyncio
import time
from statistics import mean, stdev

@pytest.mark.asyncio
async def test_connection_pool_performance():
    """Test connection pooling performance benefits."""
    
    webhook_urls = [
        "https://api1.example.com/webhook",
        "https://api2.example.com/webhook", 
        "https://api3.example.com/webhook"
    ]
    
    # Test with connection pooling
    pooled_adapter = HttpWebhookAdapter(
        connection_pool_size=50,
        connection_pool_size_per_host=20,
        keep_alive_timeout=60
    )
    
    # Test without connection pooling (force close connections)
    no_pool_adapter = HttpWebhookAdapter(
        connection_pool_size=1,
        connection_pool_size_per_host=1,
        keep_alive_timeout=0  # Minimal keep-alive
    )
    
    async def measure_delivery_time(adapter: HttpWebhookAdapter, url: str):
        """Measure delivery time for single request."""
        start_time = time.time()
        
        delivery = WebhookDelivery(
            id=WebhookDeliveryId.generate(),
            webhook_endpoint_id=WebhookEndpointId.generate(),
            webhook_event_id=EventId.generate(),
            payload={"performance_test": True}
        )
        
        endpoint = WebhookEndpoint(
            id=WebhookEndpointId.generate(),
            name="Performance Test",
            endpoint_url=url,
            secret_token="perf-test",
            created_by_user_id=UserId.generate()
        )
        
        # Mock the actual request for testing
        with patch.object(adapter, '_make_request') as mock_request:
            mock_request.return_value = (True, {"status_code": 200, "response_time_ms": 50})
            await adapter.deliver_webhook(delivery, endpoint)
        
        return (time.time() - start_time) * 1000  # Return milliseconds
    
    # Measure performance with both configurations
    pooled_times = []
    no_pool_times = []
    
    # Warm up both adapters
    for adapter in [pooled_adapter, no_pool_adapter]:
        await adapter._ensure_session()
    
    # Run performance test
    for _ in range(10):
        for url in webhook_urls:
            pooled_time = await measure_delivery_time(pooled_adapter, url)
            no_pool_time = await measure_delivery_time(no_pool_adapter, url)
            
            pooled_times.append(pooled_time)
            no_pool_times.append(no_pool_time)
    
    # Calculate statistics
    pooled_avg = mean(pooled_times)
    no_pool_avg = mean(no_pool_times)
    
    # Connection pooling should show performance benefits
    # (This assertion might not hold in a mocked test, but shows the concept)
    print(f"Pooled average: {pooled_avg:.2f}ms")
    print(f"No pool average: {no_pool_avg:.2f}ms")
    
    # Get connection statistics
    pooled_stats = pooled_adapter.get_connection_stats()
    no_pool_stats = no_pool_adapter.get_connection_stats()
    
    print(f"Pooled connection reuse rate: {pooled_stats['connection_reuse_rate']:.2%}")
    print(f"No pool connection reuse rate: {no_pool_stats['connection_reuse_rate']:.2%}")
```

## Common Pitfalls

### ❌ Anti-Patterns to Avoid

#### 1. **Session Management Issues**

```python
# DON'T: Create adapter without proper session management
async def bad_delivery_pattern():
    adapter = HttpWebhookAdapter()
    # Forgetting to use context manager or ensure_session
    success, info = await adapter.deliver_webhook(delivery, endpoint)
    # Session may not be properly configured

# DO: Always use context manager or ensure session
async def good_delivery_pattern():
    async with HttpWebhookAdapter() as adapter:
        success, info = await adapter.deliver_webhook(delivery, endpoint)
    # Session properly managed
```

#### 2. **Connection Pool Abuse**

```python
# DON'T: Create new adapter for each request
async def inefficient_batch_processing(deliveries):
    results = []
    for delivery, endpoint in deliveries:
        adapter = HttpWebhookAdapter()  # New adapter each time!
        async with adapter:
            success, info = await adapter.deliver_webhook(delivery, endpoint)
            results.append((success, info))

# DO: Reuse adapter across requests
async def efficient_batch_processing(deliveries):
    async with HttpWebhookAdapter() as adapter:
        results = []
        for delivery, endpoint in deliveries:
            success, info = await adapter.deliver_webhook(delivery, endpoint)
            results.append((success, info))
```

#### 3. **Ignoring Connection Statistics**

```python
# DON'T: Ignore performance metrics
async def unmonitored_delivery():
    async with HttpWebhookAdapter() as adapter:
        success, info = await adapter.deliver_webhook(delivery, endpoint)
        return success  # Missing performance insights

# DO: Monitor and log performance metrics
async def monitored_delivery():
    async with HttpWebhookAdapter() as adapter:
        success, info = await adapter.deliver_webhook(delivery, endpoint)
        
        # Log performance metrics
        if info.get('connection_reused'):
            logger.debug("Connection reused, good performance")
        
        if info.get('response_time_ms', 0) > 1000:
            logger.warning(f"Slow response: {info['response_time_ms']}ms")
        
        # Check adapter health periodically
        stats = adapter.get_connection_stats()
        if stats['error_rate'] > 0.1:
            logger.error(f"High error rate: {stats['error_rate']:.2%}")
        
        return success, info
```

#### 4. **Incorrect Configuration for Load**

```python
# DON'T: Use default configuration for all scenarios
high_volume_adapter = HttpWebhookAdapter()  # Default settings won't handle load

# DO: Configure appropriately for expected load
high_volume_adapter = HttpWebhookAdapter(
    max_concurrent_requests=50,      # Match expected concurrency
    connection_pool_size=300,        # Size for throughput
    connection_pool_size_per_host=100, # Per-host optimization
    keep_alive_timeout=120,          # Extended reuse
    dns_cache_ttl=900               # Reduce DNS overhead
)
```

## Migration Guide

### From Simple HTTP Requests

If migrating from basic HTTP client usage:

```python
# Old pattern with direct aiohttp usage
import aiohttp

async def old_webhook_delivery(url: str, payload: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            return response.status == 200

# New pattern with HttpWebhookAdapter
from neo_commons.features.events.adapters import HttpWebhookAdapter

async def new_webhook_delivery(delivery: WebhookDelivery, endpoint: WebhookEndpoint):
    async with HttpWebhookAdapter() as adapter:
        success, response_info = await adapter.deliver_webhook(delivery, endpoint)
        return success, response_info
```

### From Other Webhook Libraries

Key differences when migrating:

1. **Entity-Based**: Uses domain entities instead of raw dictionaries
2. **Connection Pooling**: Built-in optimization without manual configuration
3. **Monitoring**: Automatic performance and statistics tracking
4. **Protocol Integration**: Designed for dependency injection patterns

## Related Components

### Core Dependencies

- **Entities**: `WebhookDelivery`, `WebhookEndpoint` from `neo_commons.features.events.entities`
- **Value Objects**: ID types from `neo_commons.core.value_objects`
- **Header Builder**: `WebhookHeaderBuilder` from `neo_commons.features.events.utils.header_builder`

### Service Integration

- **WebhookDeliveryService**: Uses adapters for actual HTTP delivery
- **WebhookEndpointService**: Uses adapters for endpoint verification
- **EventDispatcherService**: Orchestrates adapter usage for event processing

### Infrastructure Integration

- **Configuration Service**: Provides environment-specific adapter configuration
- **Monitoring Services**: Consume adapter metrics for observability
- **Circuit Breaker Services**: May wrap adapters for resilience patterns

This comprehensive documentation provides all the necessary information for effectively using the event adapters while following DRY principles, maintaining flexibility, and ensuring high performance in the NeoMultiTenant platform.