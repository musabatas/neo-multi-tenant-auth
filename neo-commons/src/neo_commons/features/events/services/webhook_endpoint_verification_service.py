"""Webhook endpoint verification service with automated health checks.

Provides comprehensive endpoint verification, health monitoring, and automated
validation workflows to ensure webhook endpoints are reachable, properly configured,
and responding correctly to webhook deliveries.
"""

import asyncio
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4

from ....core.value_objects import WebhookEndpointId
from ....features.database.entities.protocols import DatabaseRepository
from ..entities.webhook_endpoint import WebhookEndpoint
from ..entities.webhook_event import WebhookEvent
from ..entities.protocols import WebhookEndpointRepository
from ..adapters.http_webhook_adapter import HttpWebhookAdapter
from ..utils.validation import WebhookValidationRules
from ..utils.error_handling import handle_delivery_error
from ..utils.header_builder import WebhookHeaderBuilder
from .webhook_config_service import get_webhook_config


logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Status of endpoint verification."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SSL_ERROR = "ssl_error"
    DNS_ERROR = "dns_error"
    CONNECTION_ERROR = "connection_error"
    INVALID_RESPONSE = "invalid_response"
    RATE_LIMITED = "rate_limited"
    CANCELLED = "cancelled"


class HealthStatus(Enum):
    """Health status of webhook endpoint."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class VerificationLevel(Enum):
    """Level of verification to perform."""
    BASIC = "basic"          # URL validation and basic connectivity
    STANDARD = "standard"    # Basic + SSL verification + response validation
    COMPREHENSIVE = "comprehensive"  # Standard + payload validation + security checks


@dataclass
class VerificationResult:
    """Result of endpoint verification."""
    
    endpoint_id: WebhookEndpointId
    verification_id: str = field(default_factory=lambda: str(uuid4()))
    status: VerificationStatus = VerificationStatus.PENDING
    level: VerificationLevel = VerificationLevel.STANDARD
    
    # Timing metrics
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    
    # Connection metrics
    dns_resolution_ms: Optional[int] = None
    ssl_handshake_ms: Optional[int] = None
    connection_time_ms: Optional[int] = None
    response_time_ms: Optional[int] = None
    
    # Response details
    http_status_code: Optional[int] = None
    response_headers: Optional[Dict[str, str]] = None
    response_body: Optional[str] = None
    response_size_bytes: Optional[int] = None
    
    # Security validation
    ssl_certificate_valid: Optional[bool] = None
    ssl_certificate_expires_at: Optional[datetime] = None
    security_headers_present: List[str] = field(default_factory=list)
    
    # Webhook-specific validation
    accepts_webhook_payload: Optional[bool] = None
    validates_signature: Optional[bool] = None
    returns_expected_status: Optional[bool] = None
    
    # Error details
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    error_details: Dict[str, Any] = field(default_factory=dict)
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def mark_completed(self) -> None:
        """Mark verification as completed and calculate duration."""
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            duration = self.completed_at - self.started_at
            self.total_duration_ms = int(duration.total_seconds() * 1000)
    
    def is_successful(self) -> bool:
        """Check if verification was successful."""
        return self.status == VerificationStatus.SUCCESS
    
    def get_health_score(self) -> float:
        """Calculate health score based on verification results (0-100)."""
        if not self.is_successful():
            return 0.0
        
        score = 100.0
        
        # Response time penalty
        if self.response_time_ms:
            if self.response_time_ms > 5000:  # > 5s
                score -= 30
            elif self.response_time_ms > 2000:  # > 2s
                score -= 15
            elif self.response_time_ms > 1000:  # > 1s
                score -= 5
        
        # SSL validation bonus/penalty
        if self.ssl_certificate_valid is True:
            score += 5
        elif self.ssl_certificate_valid is False:
            score -= 20
        
        # Security headers bonus
        if len(self.security_headers_present) >= 3:
            score += 5
        
        # Webhook-specific validation
        if self.validates_signature is True:
            score += 10
        elif self.validates_signature is False:
            score -= 10
        
        # Apply warnings penalty
        score -= len(self.warnings) * 2
        
        return max(0.0, min(100.0, score))


@dataclass
class EndpointHealthStatus:
    """Health status tracking for webhook endpoint."""
    
    endpoint_id: WebhookEndpointId
    current_status: HealthStatus = HealthStatus.UNKNOWN
    last_verified_at: Optional[datetime] = None
    next_check_at: Optional[datetime] = None
    
    # Verification history (last 10 results)
    recent_verifications: List[VerificationResult] = field(default_factory=list)
    
    # Health metrics
    success_rate_24h: float = 0.0
    avg_response_time_24h: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    # Availability tracking
    uptime_percentage_24h: float = 0.0
    total_downtime_minutes_24h: float = 0.0
    
    # Status changes
    status_changed_at: Optional[datetime] = None
    previous_status: Optional[HealthStatus] = None
    
    def add_verification_result(self, result: VerificationResult) -> None:
        """Add a new verification result and update health status."""
        self.recent_verifications.append(result)
        
        # Keep only last 10 results
        if len(self.recent_verifications) > 10:
            self.recent_verifications = self.recent_verifications[-10:]
        
        # Update timestamps
        self.last_verified_at = result.completed_at or datetime.now(timezone.utc)
        
        # Update consecutive counters
        if result.is_successful():
            self.consecutive_successes += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
            self.consecutive_successes = 0
        
        # Determine new health status
        new_status = self._calculate_health_status()
        
        if new_status != self.current_status:
            self.previous_status = self.current_status
            self.current_status = new_status
            self.status_changed_at = datetime.now(timezone.utc)
    
    def _calculate_health_status(self) -> HealthStatus:
        """Calculate health status based on recent verification results."""
        if not self.recent_verifications:
            return HealthStatus.UNKNOWN
        
        # Get recent success rate
        recent_results = self.recent_verifications[-5:]  # Last 5 results
        success_count = sum(1 for r in recent_results if r.is_successful())
        success_rate = success_count / len(recent_results)
        
        # Get average response time
        response_times = [r.response_time_ms for r in recent_results if r.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else None
        
        # Determine status
        if success_rate >= 0.8:  # >= 80% success rate
            if avg_response_time and avg_response_time > 3000:  # > 3s response time
                return HealthStatus.DEGRADED
            return HealthStatus.HEALTHY
        elif success_rate >= 0.4:  # >= 40% success rate
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary."""
        return {
            "endpoint_id": str(self.endpoint_id.value),
            "current_status": self.current_status.value,
            "health_score": self._calculate_health_score(),
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "success_rate_24h": self.success_rate_24h,
            "avg_response_time_24h": self.avg_response_time_24h,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "uptime_percentage_24h": self.uptime_percentage_24h,
            "status_changed_at": self.status_changed_at.isoformat() if self.status_changed_at else None,
            "recent_verification_count": len(self.recent_verifications)
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate overall health score (0-100)."""
        if not self.recent_verifications:
            return 0.0
        
        # Base score from recent verification results
        recent_scores = [r.get_health_score() for r in self.recent_verifications[-5:]]
        base_score = sum(recent_scores) / len(recent_scores)
        
        # Apply availability modifier
        availability_modifier = self.uptime_percentage_24h / 100.0
        
        return base_score * availability_modifier


class WebhookEndpointVerificationService:
    """Service for webhook endpoint verification and health monitoring."""
    
    def __init__(
        self,
        endpoint_repository: WebhookEndpointRepository,
        database_repository: DatabaseRepository,
        http_adapter: Optional[HttpWebhookAdapter] = None,
        schema: str = "public"
    ):
        """Initialize verification service.
        
        Args:
            endpoint_repository: Webhook endpoint repository
            database_repository: Database repository for health tracking
            http_adapter: HTTP adapter for verification requests
            schema: Database schema name
        """
        self._endpoint_repo = endpoint_repository
        self._db = database_repository
        self._http_adapter = http_adapter
        self._schema = schema
        
        # Get configuration
        self._config = get_webhook_config()
        
        # Verification settings
        self._verification_timeout = self._config.monitoring.health_check_timeout_seconds
        self._health_check_interval = self._config.monitoring.health_check_interval_seconds
        
        # In-memory health status cache
        self._health_status_cache: Dict[str, EndpointHealthStatus] = {}
        
        # Background tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def verify_endpoint(
        self,
        endpoint: WebhookEndpoint,
        level: VerificationLevel = VerificationLevel.STANDARD,
        include_payload_test: bool = True
    ) -> VerificationResult:
        """Verify a webhook endpoint with specified verification level.
        
        Args:
            endpoint: Webhook endpoint to verify
            level: Verification level to perform
            include_payload_test: Whether to include payload delivery test
            
        Returns:
            Comprehensive verification result
        """
        logger.info(f"Starting {level.value} verification for endpoint {endpoint.id}")
        
        result = VerificationResult(
            endpoint_id=endpoint.id,
            level=level
        )
        
        try:
            # Step 1: Basic URL validation
            await self._validate_url(endpoint, result)
            if result.status == VerificationStatus.FAILED:
                result.mark_completed()
                return result
            
            # Step 2: DNS resolution check
            if level in [VerificationLevel.STANDARD, VerificationLevel.COMPREHENSIVE]:
                await self._check_dns_resolution(endpoint, result)
                if result.status == VerificationStatus.FAILED:
                    result.mark_completed()
                    return result
            
            # Step 3: Basic connectivity test
            await self._test_connectivity(endpoint, result)
            if result.status == VerificationStatus.FAILED:
                result.mark_completed()
                return result
            
            # Step 4: SSL certificate validation (for HTTPS endpoints)
            if level in [VerificationLevel.STANDARD, VerificationLevel.COMPREHENSIVE]:
                if endpoint.endpoint_url.startswith('https://'):
                    await self._validate_ssl_certificate(endpoint, result)
            
            # Step 5: Security headers check
            if level == VerificationLevel.COMPREHENSIVE:
                await self._check_security_headers(endpoint, result)
            
            # Step 6: Webhook payload test
            if include_payload_test:
                await self._test_webhook_payload(endpoint, result)
            
            # Step 7: Generate recommendations
            await self._generate_recommendations(endpoint, result)
            
            # Mark as successful if we got this far without failures
            if result.status == VerificationStatus.PENDING:
                result.status = VerificationStatus.SUCCESS
            
            result.mark_completed()
            
            logger.info(
                f"Verification completed for endpoint {endpoint.id}: {result.status.value} "
                f"(score: {result.get_health_score():.1f})"
            )
            
            # Update health status
            await self._update_endpoint_health(endpoint.id, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error during endpoint verification {endpoint.id}: {e}")
            result.status = VerificationStatus.FAILED
            result.error_message = str(e)
            result.error_code = type(e).__name__
            result.mark_completed()
            return result
    
    async def verify_multiple_endpoints(
        self,
        endpoints: List[WebhookEndpoint],
        level: VerificationLevel = VerificationLevel.STANDARD,
        max_concurrent: int = 10
    ) -> List[VerificationResult]:
        """Verify multiple endpoints concurrently.
        
        Args:
            endpoints: List of endpoints to verify
            level: Verification level for all endpoints
            max_concurrent: Maximum concurrent verifications
            
        Returns:
            List of verification results
        """
        logger.info(f"Starting batch verification of {len(endpoints)} endpoints")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def verify_with_semaphore(endpoint: WebhookEndpoint) -> VerificationResult:
            async with semaphore:
                return await self.verify_endpoint(endpoint, level)
        
        # Execute verifications concurrently
        tasks = [verify_with_semaphore(endpoint) for endpoint in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        verification_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error verifying endpoint {endpoints[i].id}: {result}")
                error_result = VerificationResult(
                    endpoint_id=endpoints[i].id,
                    level=level,
                    status=VerificationStatus.FAILED,
                    error_message=str(result),
                    error_code=type(result).__name__
                )
                error_result.mark_completed()
                verification_results.append(error_result)
            else:
                verification_results.append(result)
        
        logger.info(f"Batch verification completed: {len(verification_results)} results")
        return verification_results
    
    async def get_endpoint_health_status(self, endpoint_id: WebhookEndpointId) -> EndpointHealthStatus:
        """Get current health status for an endpoint.
        
        Args:
            endpoint_id: Webhook endpoint ID
            
        Returns:
            Current health status with metrics
        """
        endpoint_key = str(endpoint_id.value)
        
        # Return cached status if available
        if endpoint_key in self._health_status_cache:
            return self._health_status_cache[endpoint_key]
        
        # Load from database if not cached
        health_status = await self._load_health_status(endpoint_id)
        if health_status:
            self._health_status_cache[endpoint_key] = health_status
            return health_status
        
        # Create new health status if none exists
        health_status = EndpointHealthStatus(endpoint_id=endpoint_id)
        self._health_status_cache[endpoint_key] = health_status
        return health_status
    
    async def start_automated_health_checks(self) -> None:
        """Start automated health check background task."""
        if self._is_running:
            logger.warning("Automated health checks are already running")
            return
        
        logger.info(f"Starting automated health checks (interval: {self._health_check_interval}s)")
        self._is_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop_automated_health_checks(self) -> None:
        """Stop automated health check background task."""
        if not self._is_running:
            logger.warning("Automated health checks are not running")
            return
        
        logger.info("Stopping automated health checks")
        self._is_running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                logger.info("Health check task cancelled successfully")
    
    async def get_health_summary(self) -> Dict[str, Any]:
        """Get comprehensive health summary for all endpoints.
        
        Returns:
            Summary of endpoint health across the system
        """
        try:
            # Get all active endpoints
            active_endpoints = await self._endpoint_repo.get_active_endpoints()
            
            summary = {
                "total_endpoints": len(active_endpoints),
                "healthy_count": 0,
                "degraded_count": 0,
                "unhealthy_count": 0,
                "unknown_count": 0,
                "average_health_score": 0.0,
                "last_check_completed": None,
                "endpoints_by_status": {
                    "healthy": [],
                    "degraded": [],
                    "unhealthy": [],
                    "unknown": []
                }
            }
            
            total_health_score = 0.0
            latest_check = None
            
            for endpoint in active_endpoints:
                health_status = await self.get_endpoint_health_status(endpoint.id)
                health_summary = health_status.get_health_summary()
                
                # Count by status
                status = health_status.current_status
                summary[f"{status.value}_count"] += 1
                summary["endpoints_by_status"][status.value].append(health_summary)
                
                # Track health scores
                total_health_score += health_summary["health_score"]
                
                # Track latest check time
                if health_status.last_verified_at:
                    if not latest_check or health_status.last_verified_at > latest_check:
                        latest_check = health_status.last_verified_at
            
            # Calculate averages
            if active_endpoints:
                summary["average_health_score"] = total_health_score / len(active_endpoints)
            
            if latest_check:
                summary["last_check_completed"] = latest_check.isoformat()
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating health summary: {e}")
            return {"error": str(e)}
    
    # Verification helper methods
    
    async def _validate_url(self, endpoint: WebhookEndpoint, result: VerificationResult) -> None:
        """Validate URL format and accessibility."""
        try:
            WebhookValidationRules.validate_webhook_url(endpoint.endpoint_url)
            logger.debug(f"URL validation passed for {endpoint.endpoint_url}")
        except ValueError as e:
            result.status = VerificationStatus.FAILED
            result.error_message = f"URL validation failed: {e}"
            result.error_code = "INVALID_URL"
            result.recommendations.append("Fix the endpoint URL format")
    
    async def _check_dns_resolution(self, endpoint: WebhookEndpoint, result: VerificationResult) -> None:
        """Check DNS resolution for the endpoint."""
        import socket
        from urllib.parse import urlparse
        
        try:
            parsed_url = urlparse(endpoint.endpoint_url)
            hostname = parsed_url.hostname
            
            if not hostname:
                result.status = VerificationStatus.FAILED
                result.error_message = "Cannot extract hostname from URL"
                result.error_code = "INVALID_HOSTNAME"
                return
            
            start_time = datetime.now(timezone.utc)
            
            # Perform DNS resolution
            socket.getaddrinfo(hostname, None)
            
            end_time = datetime.now(timezone.utc)
            result.dns_resolution_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.debug(f"DNS resolution successful for {hostname} ({result.dns_resolution_ms}ms)")
            
        except socket.gaierror as e:
            result.status = VerificationStatus.DNS_ERROR
            result.error_message = f"DNS resolution failed: {e}"
            result.error_code = "DNS_RESOLUTION_FAILED"
            result.recommendations.append("Check if the hostname is correct and accessible")
    
    async def _test_connectivity(self, endpoint: WebhookEndpoint, result: VerificationResult) -> None:
        """Test basic connectivity to the endpoint."""
        if not self._http_adapter:
            # Simple connectivity test without HTTP adapter
            result.warnings.append("HTTP adapter not available - limited connectivity testing")
            return
        
        try:
            start_time = datetime.now(timezone.utc)
            
            # Use HTTP adapter for connectivity test
            async with self._http_adapter:
                success, response_info = await self._http_adapter.test_connectivity(
                    endpoint.endpoint_url,
                    timeout_seconds=self._verification_timeout
                )
            
            end_time = datetime.now(timezone.utc)
            result.connection_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            if success:
                result.http_status_code = response_info.get('status_code')
                result.response_time_ms = response_info.get('response_time_ms')
                result.response_headers = response_info.get('headers', {})
                result.response_size_bytes = response_info.get('content_length')
                
                logger.debug(f"Connectivity test passed for {endpoint.endpoint_url}")
            else:
                error_msg = response_info.get('error', 'Unknown connection error')
                if 'timeout' in error_msg.lower():
                    result.status = VerificationStatus.TIMEOUT
                elif 'ssl' in error_msg.lower():
                    result.status = VerificationStatus.SSL_ERROR
                else:
                    result.status = VerificationStatus.CONNECTION_ERROR
                
                result.error_message = error_msg
                result.error_code = "CONNECTIVITY_FAILED"
                result.recommendations.append("Check if the endpoint is running and accessible")
                
        except Exception as e:
            result.status = VerificationStatus.FAILED
            result.error_message = f"Connectivity test failed: {e}"
            result.error_code = "CONNECTIVITY_TEST_ERROR"

    async def _validate_ssl_certificate(self, endpoint: WebhookEndpoint, result: VerificationResult) -> None:
        """Validate SSL certificate for HTTPS endpoints."""
        from urllib.parse import urlparse
        import ssl
        import socket
        
        try:
            parsed_url = urlparse(endpoint.endpoint_url)
            if parsed_url.scheme != 'https':
                result.warnings.append("Endpoint is not using HTTPS - SSL validation skipped")
                return
            
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            if not hostname:
                result.warnings.append("Cannot extract hostname for SSL validation")
                return
            
            # Create SSL context for validation
            context = ssl.create_default_context()
            
            # Connect and get certificate
            with socket.create_connection((hostname, port), timeout=self._verification_timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()
                    
                    if cert:
                        # Extract certificate info
                        subject = dict(x[0] for x in cert.get('subject', []))
                        issuer = dict(x[0] for x in cert.get('issuer', []))
                        
                        result.ssl_info = {
                            'subject': subject.get('commonName', 'Unknown'),
                            'issuer': issuer.get('organizationName', 'Unknown'),
                            'expires': cert.get('notAfter', 'Unknown'),
                            'version': cert.get('version', 'Unknown')
                        }
                        
                        # Check certificate validity
                        import datetime
                        not_after = datetime.datetime.strptime(cert.get('notAfter'), '%b %d %H:%M:%S %Y %Z')
                        days_until_expiry = (not_after - datetime.datetime.now()).days
                        
                        if days_until_expiry < 7:
                            result.warnings.append(f"SSL certificate expires in {days_until_expiry} days")
                        elif days_until_expiry < 30:
                            result.recommendations.append("Consider renewing SSL certificate soon")
                        
                        logger.debug(f"SSL validation passed for {hostname}")
                    else:
                        result.warnings.append("Could not retrieve SSL certificate information")
                        
        except ssl.SSLError as e:
            result.status = VerificationStatus.SSL_ERROR
            result.error_message = f"SSL validation failed: {e}"
            result.error_code = "SSL_VALIDATION_FAILED"
            result.recommendations.append("Check SSL certificate configuration")
        except Exception as e:
            result.warnings.append(f"SSL validation error: {e}")

    async def _check_security_headers(self, endpoint: WebhookEndpoint, result: VerificationResult) -> None:
        """Check security headers in the response."""
        if not result.response_headers:
            result.warnings.append("No response headers available for security check")
            return
        
        try:
            security_headers = [
                'strict-transport-security',
                'content-security-policy',
                'x-frame-options',
                'x-content-type-options',
                'x-xss-protection',
                'referrer-policy'
            ]
            
            missing_headers = []
            found_headers = {}
            
            # Convert headers to lowercase for case-insensitive comparison
            headers_lower = {k.lower(): v for k, v in result.response_headers.items()}
            
            for header in security_headers:
                if header in headers_lower:
                    found_headers[header] = headers_lower[header]
                else:
                    missing_headers.append(header)
            
            # Store security header analysis
            result.security_headers = {
                'found': found_headers,
                'missing': missing_headers,
                'security_score': len(found_headers) / len(security_headers) * 100
            }
            
            # Add recommendations for missing critical headers
            if 'strict-transport-security' in missing_headers:
                result.recommendations.append("Add HSTS header for improved security")
            
            if len(missing_headers) > len(security_headers) // 2:
                result.recommendations.append("Consider implementing more security headers")
            
            logger.debug(f"Security headers checked - found {len(found_headers)}/{len(security_headers)}")
            
        except Exception as e:
            result.warnings.append(f"Security header analysis error: {e}")

    async def _test_webhook_payload(self, endpoint: WebhookEndpoint, result: VerificationResult) -> None:
        """Test webhook delivery with sample payload."""
        if not self._http_adapter:
            result.warnings.append("HTTP adapter not available - payload test skipped")
            return
        
        try:
            # Create test webhook event
            test_event = WebhookEvent(
                event_id=WebhookEventId(str(uuid4())),
                event_type="test.verification",
                tenant_id=endpoint.tenant_id,
                payload={
                    "verification_test": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "endpoint_id": str(endpoint.id),
                    "message": "This is a verification test"
                },
                metadata={"test": True, "verification": True}
            )
            
            start_time = datetime.now(timezone.utc)
            
            # Attempt delivery
            delivery_result = await self._http_adapter.deliver_webhook(
                event=test_event,
                endpoint=endpoint,
                retry_count=0
            )
            
            end_time = datetime.now(timezone.utc)
            result.payload_delivery_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Analyze delivery result
            if delivery_result.success:
                result.payload_test_success = True
                result.payload_response_code = delivery_result.response_code
                result.payload_response_body = delivery_result.response_body
                
                # Validate webhook signature if configured
                if endpoint.signing_secret and delivery_result.response_headers:
                    signature_header = delivery_result.response_headers.get('x-webhook-signature')
                    if signature_header:
                        result.signature_validation_success = True
                    else:
                        result.warnings.append("Webhook signature not found in response")
                        result.signature_validation_success = False
                else:
                    result.warnings.append("No signing secret configured - signature validation skipped")
                
                logger.debug(f"Payload test successful for {endpoint.endpoint_url}")
            else:
                result.payload_test_success = False
                result.error_message = delivery_result.error_message or "Payload delivery failed"
                result.recommendations.append("Check webhook endpoint handler implementation")
                
        except Exception as e:
            result.payload_test_success = False
            result.warnings.append(f"Payload test error: {e}")

    async def _generate_recommendations(self, endpoint: WebhookEndpoint, result: VerificationResult) -> None:
        """Generate actionable recommendations based on verification results."""
        try:
            # Performance recommendations
            if result.response_time_ms and result.response_time_ms > 5000:
                result.recommendations.append("Optimize endpoint response time (currently > 5s)")
            elif result.response_time_ms and result.response_time_ms > 2000:
                result.recommendations.append("Consider optimizing endpoint response time")
            
            # DNS recommendations
            if result.dns_resolution_ms and result.dns_resolution_ms > 1000:
                result.recommendations.append("DNS resolution is slow - consider using a faster DNS provider")
            
            # SSL recommendations
            if result.ssl_info and 'expires' in result.ssl_info:
                result.recommendations.append("Monitor SSL certificate expiration")
            
            # Security recommendations
            if result.security_headers and result.security_headers['security_score'] < 50:
                result.recommendations.append("Implement additional security headers")
            
            # Payload recommendations
            if not result.payload_test_success:
                result.recommendations.append("Fix webhook payload handling")
            
            if not result.signature_validation_success and endpoint.signing_secret:
                result.recommendations.append("Implement proper webhook signature validation")
            
            # Connectivity recommendations
            if result.status == VerificationStatus.TIMEOUT:
                result.recommendations.append("Increase endpoint timeout or optimize response time")
            
            # General recommendations
            if result.get_health_score() < 70:
                result.recommendations.append("Address health issues to improve reliability")
            
            # Remove duplicates
            result.recommendations = list(set(result.recommendations))
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")

    async def _update_endpoint_health(self, endpoint_id: WebhookEndpointId, result: VerificationResult) -> None:
        """Update endpoint health status based on verification result."""
        try:
            health_status = await self.get_endpoint_health_status(endpoint_id)
            
            # Update verification history
            health_status.verification_history.append(result)
            
            # Keep only last 100 verifications
            if len(health_status.verification_history) > 100:
                health_status.verification_history = health_status.verification_history[-100:]
            
            # Update current status
            if result.status == VerificationStatus.SUCCESS:
                if result.get_health_score() >= 80:
                    health_status.current_status = EndpointHealthStatus.HealthStatus.HEALTHY
                elif result.get_health_score() >= 60:
                    health_status.current_status = EndpointHealthStatus.HealthStatus.DEGRADED
                else:
                    health_status.current_status = EndpointHealthStatus.HealthStatus.UNHEALTHY
            else:
                health_status.current_status = EndpointHealthStatus.HealthStatus.UNHEALTHY
            
            # Update metrics
            health_status.last_verified_at = result.verified_at
            health_status.total_checks += 1
            
            if result.status == VerificationStatus.SUCCESS:
                health_status.successful_checks += 1
            else:
                health_status.failed_checks += 1
            
            # Update uptime percentage
            health_status.uptime_percentage = (
                (health_status.successful_checks / health_status.total_checks) * 100
                if health_status.total_checks > 0 else 0.0
            )
            
            # Update average response time
            if result.response_time_ms:
                if health_status.average_response_time_ms == 0:
                    health_status.average_response_time_ms = result.response_time_ms
                else:
                    # Moving average
                    health_status.average_response_time_ms = (
                        (health_status.average_response_time_ms * 0.9) + 
                        (result.response_time_ms * 0.1)
                    )
            
            # Update last error
            if result.status != VerificationStatus.SUCCESS:
                health_status.last_error_at = result.verified_at
                health_status.last_error_message = result.error_message
            
            # Cache updated health status
            endpoint_key = f"endpoint_{endpoint_id}"
            self._health_status_cache[endpoint_key] = health_status
            
            logger.debug(f"Updated health status for endpoint {endpoint_id}")
            
        except Exception as e:
            logger.error(f"Error updating endpoint health: {e}")

    async def _health_check_loop(self) -> None:
        """Background task for automated health checks."""
        logger.info("Health check loop started")
        
        while self._is_running:
            try:
                # Get all active endpoints
                active_endpoints = await self._endpoint_repo.get_active_endpoints()
                
                if not active_endpoints:
                    logger.debug("No active endpoints found for health checks")
                    await asyncio.sleep(self._health_check_interval)
                    continue
                
                logger.info(f"Starting health check cycle for {len(active_endpoints)} endpoints")
                
                # Create verification tasks for all endpoints
                tasks = []
                semaphore = asyncio.Semaphore(self._concurrent_verifications)
                
                async def verify_with_semaphore(endpoint):
                    async with semaphore:
                        try:
                            result = await self.verify_endpoint(
                                endpoint,
                                level=VerificationLevel.BASIC,
                                include_payload_test=False  # Skip payload tests in automated checks
                            )
                            return endpoint.id, result
                        except Exception as e:
                            logger.error(f"Health check failed for endpoint {endpoint.id}: {e}")
                            return endpoint.id, None
                
                # Execute health checks concurrently
                for endpoint in active_endpoints:
                    tasks.append(verify_with_semaphore(endpoint))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                successful_checks = 0
                failed_checks = 0
                
                for endpoint_id, result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Health check exception for {endpoint_id}: {result}")
                        failed_checks += 1
                    elif result and result.status == VerificationStatus.SUCCESS:
                        successful_checks += 1
                    else:
                        failed_checks += 1
                
                logger.info(
                    f"Health check cycle completed - "
                    f"Success: {successful_checks}, Failed: {failed_checks}"
                )
                
                # Wait for next cycle
                await asyncio.sleep(self._health_check_interval)
                
            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                # Continue running despite errors
                await asyncio.sleep(min(self._health_check_interval, 60))
        
        logger.info("Health check loop stopped")

    async def _load_health_status(self, endpoint_id: WebhookEndpointId) -> Optional[EndpointHealthStatus]:
        """Load endpoint health status from database."""
        try:
            # This would typically load from database
            # For now, return None to create fresh status
            # TODO: Implement database persistence for health status
            return None
            
        except Exception as e:
            logger.error(f"Error loading health status for endpoint {endpoint_id}: {e}")
            return None