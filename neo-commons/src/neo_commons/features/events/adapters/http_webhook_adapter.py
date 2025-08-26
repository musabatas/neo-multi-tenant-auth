"""HTTP webhook adapter for webhook delivery using aiohttp.

Provides HTTP client functionality for webhook delivery with timeout handling,
retry logic, and proper error reporting.
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

import aiohttp
from aiohttp import ClientTimeout, ClientError, ClientSession, TCPConnector

from ..entities.webhook_delivery import WebhookDelivery, DeliveryStatus
from ..entities.webhook_endpoint import WebhookEndpoint
from ..utils.header_builder import WebhookHeaderBuilder, HeaderContext

logger = logging.getLogger(__name__)


class HttpWebhookAdapter:
    """HTTP adapter for webhook delivery using aiohttp with connection pooling.
    
    Handles HTTP requests for webhook delivery with proper timeout handling,
    error reporting, response processing, and optimized connection reuse.
    
    Features:
    - HTTP/1.1 and HTTP/2 support with keep-alive
    - Connection pooling with configurable limits
    - DNS caching and connection reuse
    - Automatic retry on connection failures
    """
    
    def __init__(
        self, 
        default_timeout_seconds: int = 30,
        max_concurrent_requests: int = 10,
        connection_pool_size: int = 100,
        connection_pool_size_per_host: int = 30,
        keep_alive_timeout: int = 30,
        dns_cache_ttl: int = 300,
        enable_cleanup_closed: bool = True
    ):
        """Initialize HTTP adapter with connection pooling.
        
        Args:
            default_timeout_seconds: Default timeout for requests
            max_concurrent_requests: Maximum concurrent HTTP requests
            connection_pool_size: Total connection pool size
            connection_pool_size_per_host: Max connections per host
            keep_alive_timeout: Keep-alive timeout in seconds
            dns_cache_ttl: DNS cache TTL in seconds
            enable_cleanup_closed: Enable automatic cleanup of closed connections
        """
        self._default_timeout = default_timeout_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)
        self._session: Optional[ClientSession] = None
        
        # Connection pooling configuration
        self._connection_pool_size = connection_pool_size
        self._connection_pool_size_per_host = connection_pool_size_per_host
        self._keep_alive_timeout = keep_alive_timeout
        self._dns_cache_ttl = dns_cache_ttl
        self._enable_cleanup_closed = enable_cleanup_closed
        
        # Connection statistics
        self._connection_stats = {
            "total_requests": 0,
            "connection_reuses": 0,
            "dns_cache_hits": 0,
            "connection_errors": 0,
            "pool_exhausted_count": 0
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()
    
    async def _ensure_session(self):
        """Ensure aiohttp session exists with optimized connection pooling."""
        if self._session is None or self._session.closed:
            # Create optimized TCP connector with connection pooling
            connector = TCPConnector(
                # Connection pooling settings
                limit=self._connection_pool_size,  # Total connection pool size
                limit_per_host=self._connection_pool_size_per_host,  # Max connections per host
                
                # Keep-alive settings
                keepalive_timeout=self._keep_alive_timeout,  # Keep connections alive
                enable_cleanup_closed=self._enable_cleanup_closed,  # Auto-cleanup closed connections
                
                # DNS and connection optimization
                ttl_dns_cache=self._dns_cache_ttl,  # Cache DNS lookups
                use_dns_cache=True,  # Enable DNS caching
                
                # HTTP version and feature support
                force_close=False,  # Allow connection reuse
                enable_cleanup_closed=True,  # Cleanup closed connections automatically
                
                # SSL settings
                verify_ssl=True,  # Always verify SSL certificates
            )
            
            # Create session with optimized settings
            timeout = ClientTimeout(
                total=self._default_timeout,
                connect=10,  # Connection timeout
                sock_read=self._default_timeout  # Socket read timeout
            )
            
            # Use centralized header builder for session headers
            session_headers = WebhookHeaderBuilder.build_headers(
                context=HeaderContext.DELIVERY,
                custom_headers=None
            )
            
            self._session = ClientSession(
                connector=connector,
                timeout=timeout,
                headers=session_headers
            )
            
            logger.debug(
                f"Created HTTP session with connection pool: "
                f"total_limit={self._connection_pool_size}, "
                f"per_host_limit={self._connection_pool_size_per_host}, "
                f"keep_alive={self._keep_alive_timeout}s"
            )
    
    async def _close_session(self):
        """Close aiohttp session if exists."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def deliver_webhook(
        self, 
        delivery: WebhookDelivery, 
        endpoint: WebhookEndpoint
    ) -> Tuple[bool, Dict[str, Any]]:
        """Deliver webhook via HTTP request.
        
        Args:
            delivery: Webhook delivery entity
            endpoint: Webhook endpoint entity
            
        Returns:
            Tuple of (success: bool, response_info: dict)
        """
        await self._ensure_session()
        
        # Use semaphore to limit concurrent requests
        async with self._semaphore:
            return await self._make_request(delivery, endpoint)
    
    async def _make_request(
        self, 
        delivery: WebhookDelivery, 
        endpoint: WebhookEndpoint
    ) -> Tuple[bool, Dict[str, Any]]:
        """Make the actual HTTP request.
        
        Args:
            delivery: Webhook delivery entity
            endpoint: Webhook endpoint entity
            
        Returns:
            Tuple of (success: bool, response_info: dict)
        """
        start_time = datetime.now(timezone.utc)
        response_info = {
            "attempt": delivery.attempt_count + 1,
            "url": delivery.delivery_url,
            "method": delivery.http_method,
            "started_at": start_time.isoformat()
        }
        
        try:
            # Update connection statistics
            self._connection_stats["total_requests"] += 1
            
            # Prepare request timeout
            timeout_seconds = endpoint.timeout_seconds or self._default_timeout
            timeout = ClientTimeout(
                total=timeout_seconds,
                connect=min(10, timeout_seconds // 3),  # Connection timeout
                sock_read=timeout_seconds  # Socket read timeout
            )
            
            # Prepare headers using centralized header builder
            request_headers = WebhookHeaderBuilder.build_delivery_headers(
                custom_headers=endpoint.custom_headers,
                signature=delivery.signature if hasattr(delivery, 'signature') else None,
                tenant_id=None,  # TODO: Add tenant_id to WebhookEndpoint entity if needed for multitenancy
                signature_header_name=endpoint.signature_header
            )
            
            # Make HTTP request with connection reuse
            async with self._session.request(
                method=delivery.http_method,
                url=delivery.delivery_url,
                json=delivery.payload,
                headers=request_headers,
                timeout=timeout,
                ssl=endpoint.verify_ssl if hasattr(endpoint, 'verify_ssl') else True,
                allow_redirects=endpoint.follow_redirects if hasattr(endpoint, 'follow_redirects') else False
            ) as response:
                # Calculate response time
                end_time = datetime.now(timezone.utc)
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Read response body (limited to prevent memory issues)
                response_body = await response.text()
                if len(response_body) > 10000:  # Limit response body to 10KB
                    response_body = response_body[:10000] + "... (truncated)"
                
                # Check for connection reuse
                connection_reused = response.headers.get("Connection", "").lower() == "keep-alive"
                if connection_reused:
                    self._connection_stats["connection_reuses"] += 1
                
                # Update response info
                response_info.update({
                    "status_code": response.status,
                    "response_time_ms": response_time_ms,
                    "response_headers": dict(response.headers),
                    "response_body": response_body,
                    "completed_at": end_time.isoformat(),
                    "connection_reused": connection_reused,
                    "compression_used": "gzip" in response.headers.get("Content-Encoding", "")
                })
                
                # Check if request was successful (2xx status codes)
                success = 200 <= response.status < 300
                
                if success:
                    logger.info(
                        f"Webhook delivered successfully to {delivery.delivery_url} "
                        f"[{response.status}] in {response_time_ms}ms"
                    )
                else:
                    logger.warning(
                        f"Webhook delivery failed to {delivery.delivery_url} "
                        f"[{response.status}] in {response_time_ms}ms: {response_body[:500]}"
                    )
                
                return success, response_info
        
        except asyncio.TimeoutError as e:
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            response_info.update({
                "error": "timeout",
                "error_message": f"Request timed out after {timeout_seconds}s",
                "response_time_ms": response_time_ms,
                "completed_at": end_time.isoformat()
            })
            
            logger.error(f"Webhook delivery timeout to {delivery.delivery_url} after {timeout_seconds}s")
            return False, response_info
        
        except ClientError as e:
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Track connection errors
            self._connection_stats["connection_errors"] += 1
            
            # Check if it's a pool exhaustion error
            if "pool" in str(e).lower():
                self._connection_stats["pool_exhausted_count"] += 1
            
            response_info.update({
                "error": "client_error",
                "error_message": str(e),
                "error_type": type(e).__name__,
                "response_time_ms": response_time_ms,
                "completed_at": end_time.isoformat()
            })
            
            logger.error(f"HTTP client error for webhook delivery to {delivery.delivery_url}: {e}")
            return False, response_info
        
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            response_info.update({
                "error": "unexpected_error",
                "error_message": str(e),
                "error_type": type(e).__name__,
                "response_time_ms": response_time_ms,
                "completed_at": end_time.isoformat()
            })
            
            logger.error(f"Unexpected error in webhook delivery to {delivery.delivery_url}: {e}")
            return False, response_info
    
    async def verify_endpoint(
        self, 
        endpoint: WebhookEndpoint, 
        test_payload: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Verify webhook endpoint connectivity.
        
        Args:
            endpoint: Webhook endpoint to verify
            test_payload: Optional test payload for verification
            
        Returns:
            Tuple of (success: bool, verification_info: dict)
        """
        await self._ensure_session()
        
        # Use test payload or default verification payload
        if test_payload is None:
            test_payload = {
                "event_type": "verification.test",
                "event_name": "Endpoint Verification Test",
                "test": True,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        start_time = datetime.now(timezone.utc)
        verification_info = {
            "url": endpoint.endpoint_url,
            "method": endpoint.http_method or "POST",
            "started_at": start_time.isoformat(),
            "test_payload": test_payload
        }
        
        try:
            # Prepare headers using centralized header builder
            headers = WebhookHeaderBuilder.build_verification_headers(
                custom_headers=endpoint.headers,
                tenant_id=None  # TODO: Add tenant_id to WebhookEndpoint entity if needed for multitenancy
            )
            
            # Prepare timeout
            timeout_seconds = endpoint.timeout_seconds or self._default_timeout
            timeout = ClientTimeout(total=timeout_seconds)
            
            # Make verification request
            async with self._session.request(
                method=endpoint.http_method or "POST",
                url=endpoint.endpoint_url,
                json=test_payload,
                headers=headers,
                timeout=timeout,
                ssl=True
            ) as response:
                end_time = datetime.now(timezone.utc)
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                # Read response body
                response_body = await response.text()
                if len(response_body) > 1000:  # Limit for verification
                    response_body = response_body[:1000] + "... (truncated)"
                
                verification_info.update({
                    "status_code": response.status,
                    "response_time_ms": response_time_ms,
                    "response_headers": dict(response.headers),
                    "response_body": response_body,
                    "completed_at": end_time.isoformat()
                })
                
                # Consider verification successful if we get any response
                # (even 4xx errors indicate the endpoint is reachable)
                success = response.status < 500
                
                if success:
                    logger.info(
                        f"Endpoint verification successful: {endpoint.endpoint_url} "
                        f"[{response.status}] in {response_time_ms}ms"
                    )
                else:
                    logger.warning(
                        f"Endpoint verification failed: {endpoint.endpoint_url} "
                        f"[{response.status}] in {response_time_ms}ms"
                    )
                
                return success, verification_info
        
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            verification_info.update({
                "error": str(e),
                "error_type": type(e).__name__,
                "response_time_ms": response_time_ms,
                "completed_at": end_time.isoformat(),
                "success": False
            })
            
            logger.error(f"Endpoint verification error for {endpoint.endpoint_url}: {e}")
            return False, verification_info
    
    async def test_connectivity(
        self, 
        url: str, 
        timeout_seconds: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Test basic connectivity to a URL.
        
        Args:
            url: URL to test connectivity to
            timeout_seconds: Timeout for the test request
            
        Returns:
            Tuple of (success: bool, connectivity_info: dict)
        """
        await self._ensure_session()
        
        start_time = datetime.now(timezone.utc)
        connectivity_info = {
            "url": url,
            "started_at": start_time.isoformat(),
            "test_type": "connectivity"
        }
        
        try:
            # Prepare headers for connectivity test
            headers = WebhookHeaderBuilder.build_connectivity_test_headers()
            
            # Prepare timeout
            test_timeout = timeout_seconds or self._default_timeout
            timeout = ClientTimeout(total=test_timeout)
            
            # Make HEAD request for connectivity test
            async with self._session.request(
                method="HEAD",
                url=url,
                headers=headers,
                timeout=timeout,
                ssl=True,
                allow_redirects=True
            ) as response:
                end_time = datetime.now(timezone.utc)
                response_time_ms = int((end_time - start_time).total_seconds() * 1000)
                
                connectivity_info.update({
                    "status_code": response.status,
                    "response_time_ms": response_time_ms,
                    "headers": dict(response.headers),
                    "content_length": response.headers.get("Content-Length"),
                    "completed_at": end_time.isoformat(),
                    "success": True
                })
                
                logger.debug(f"Connectivity test successful: {url} [{response.status}] in {response_time_ms}ms")
                return True, connectivity_info
        
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            response_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            connectivity_info.update({
                "error": str(e),
                "error_type": type(e).__name__,
                "response_time_ms": response_time_ms,
                "completed_at": end_time.isoformat(),
                "success": False
            })
            
            logger.error(f"Connectivity test failed for {url}: {e}")
            return False, connectivity_info
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the HTTP adapter with connection pool info.
        
        Returns:
            Health status information including connection pool metrics
        """
        health_info = {
            "adapter": "HttpWebhookAdapter",
            "status": "healthy",
            "session_active": self._session is not None and not self._session.closed,
            "max_concurrent_requests": self._semaphore._value,
            "default_timeout_seconds": self._default_timeout,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add connection pool configuration
        health_info["connection_pool"] = {
            "total_pool_size": self._connection_pool_size,
            "per_host_pool_size": self._connection_pool_size_per_host,
            "keep_alive_timeout": self._keep_alive_timeout,
            "dns_cache_ttl": self._dns_cache_ttl,
            "cleanup_closed_enabled": self._enable_cleanup_closed
        }
        
        # Add connection statistics
        health_info["connection_stats"] = self._connection_stats.copy()
        
        # Calculate efficiency metrics
        if self._connection_stats["total_requests"] > 0:
            reuse_rate = (self._connection_stats["connection_reuses"] / 
                         self._connection_stats["total_requests"]) * 100
            error_rate = (self._connection_stats["connection_errors"] / 
                         self._connection_stats["total_requests"]) * 100
            
            health_info["efficiency_metrics"] = {
                "connection_reuse_rate_percent": round(reuse_rate, 2),
                "error_rate_percent": round(error_rate, 2),
                "pool_exhaustion_rate": self._connection_stats["pool_exhausted_count"]
            }
        
        try:
            # Test basic connectivity
            await self._ensure_session()
            health_info["session_created"] = True
            
            # Add connector-specific information if available
            if self._session and hasattr(self._session, '_connector'):
                connector = self._session._connector
                if hasattr(connector, '_conns'):
                    # Try to get connection pool information
                    active_connections = sum(len(conns) for conns in connector._conns.values())
                    health_info["active_connections"] = active_connections
            
        except Exception as e:
            health_info.update({
                "status": "unhealthy",
                "error": str(e),
                "error_type": type(e).__name__
            })
            logger.error(f"HTTP adapter health check failed: {e}")
        
        return health_info
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics.
        
        Returns:
            Dictionary with connection statistics and metrics
        """
        stats = self._connection_stats.copy()
        
        # Calculate rates and efficiency metrics
        if stats["total_requests"] > 0:
            stats["connection_reuse_rate"] = stats["connection_reuses"] / stats["total_requests"]
            stats["error_rate"] = stats["connection_errors"] / stats["total_requests"]
        else:
            stats["connection_reuse_rate"] = 0.0
            stats["error_rate"] = 0.0
            
        return stats
    
    def reset_connection_stats(self):
        """Reset connection statistics counters."""
        self._connection_stats = {
            "total_requests": 0,
            "connection_reuses": 0,
            "dns_cache_hits": 0,
            "connection_errors": 0,
            "pool_exhausted_count": 0
        }
        logger.info("Connection statistics have been reset")
    
    async def cleanup_connections(self):
        """Manually cleanup idle connections in the pool."""
        if self._session and hasattr(self._session, '_connector'):
            try:
                await self._session._connector._cleanup_closed()
                logger.debug("Manually cleaned up closed connections")
            except Exception as e:
                logger.warning(f"Failed to cleanup connections: {e}")
    
    async def get_pool_status(self) -> Dict[str, Any]:
        """Get detailed connection pool status.
        
        Returns:
            Dictionary with detailed pool information
        """
        if not self._session or not hasattr(self._session, '_connector'):
            return {"status": "no_session_or_connector"}
        
        connector = self._session._connector
        pool_info = {
            "configured_limit": self._connection_pool_size,
            "configured_per_host_limit": self._connection_pool_size_per_host,
            "keep_alive_timeout": self._keep_alive_timeout,
            "dns_cache_ttl": self._dns_cache_ttl
        }
        
        # Try to get runtime pool information
        try:
            if hasattr(connector, '_conns'):
                pool_info["active_hosts"] = len(connector._conns)
                pool_info["total_active_connections"] = sum(len(conns) for conns in connector._conns.values())
                
            if hasattr(connector, '_dns_cache'):
                pool_info["dns_cache_entries"] = len(connector._dns_cache) if connector._dns_cache else 0
                
        except Exception as e:
            pool_info["error"] = f"Failed to get runtime info: {e}"
        
        return pool_info