"""Webhook delivered handler for platform events infrastructure.

This module handles ONLY webhook delivered notifications following maximum separation architecture.
Single responsibility: Handle post-delivery webhook processing, response analysis, and delivery metrics.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from ...core.entities import WebhookDelivery, WebhookEndpoint
from ...core.value_objects import WebhookDeliveryId, WebhookEndpointId, EventId, DeliveryStatus
from ...core.events import WebhookDelivered
from ...core.protocols import WebhookRepository, EventRepository, NotificationService
from ...core.exceptions import EventHandlerFailed
from .....utils import utc_now


class DeliveryAnalysisType(Enum):
    """Types of webhook delivery analysis."""
    SUCCESS_METRICS = "success_metrics"
    FAILURE_ANALYSIS = "failure_analysis"
    RESPONSE_ANALYSIS = "response_analysis"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    ENDPOINT_HEALTH = "endpoint_health"


@dataclass
class WebhookDeliveredHandlerResult:
    """Result of webhook delivered handling."""
    success: bool
    processed_at: datetime
    delivery_analyzed: bool
    endpoint_health_updated: bool
    retry_scheduled: bool
    notifications_sent: List[str]
    metrics_recorded: Dict[str, Any]
    analysis_results: Dict[str, Any]
    errors: List[str]
    processing_duration_ms: float
    
    message: str = "Webhook delivered processing completed"


class WebhookDeliveredHandler:
    """Handler for webhook delivered notifications.
    
    Processes webhooks after delivery attempts, analyzing responses,
    updating endpoint health metrics, and scheduling retries if needed.
    
    Single responsibility: ONLY post-delivery webhook processing logic.
    Uses dependency injection through protocols for clean architecture.
    """
    
    def __init__(self, 
                 webhook_repository: WebhookRepository,
                 event_repository: EventRepository,
                 notification_service: Optional[NotificationService] = None):
        """Initialize handler with required dependencies.
        
        Args:
            webhook_repository: Repository for webhook operations
            event_repository: Repository for event operations
            notification_service: Optional service for sending notifications
        """
        self._webhook_repository = webhook_repository
        self._event_repository = event_repository
        self._notification_service = notification_service
    
    async def handle(self, webhook_delivered: WebhookDelivered) -> WebhookDeliveredHandlerResult:
        """Handle webhook delivered notification.
        
        Processes the delivered webhook by:
        1. Analyzing delivery response and performance
        2. Recording delivery metrics and outcomes
        3. Updating webhook endpoint health status
        4. Scheduling retries for failed deliveries
        5. Sending notifications if configured
        6. Updating delivery status and metadata
        
        Args:
            webhook_delivered: Webhook delivered notification
            
        Returns:
            WebhookDeliveredHandlerResult with processing outcome
            
        Raises:
            EventHandlerFailed: If handler processing fails
        """
        start_time = utc_now()
        result = WebhookDeliveredHandlerResult(
            success=True,
            processed_at=start_time,
            delivery_analyzed=False,
            endpoint_health_updated=False,
            retry_scheduled=False,
            notifications_sent=[],
            metrics_recorded={},
            analysis_results={},
            errors=[],
            processing_duration_ms=0.0
        )
        
        try:
            # Retrieve the webhook delivery
            delivery = await self._get_webhook_delivery(webhook_delivered.delivery_id, result)
            if not delivery:
                result.success = False
                result.message = f"Webhook delivery {webhook_delivered.delivery_id} not found for post-delivery processing"
                return result
            
            # Analyze delivery response and performance
            await self._analyze_webhook_delivery(delivery, webhook_delivered, result)
            
            # Record delivery metrics
            await self._record_delivery_metrics(delivery, webhook_delivered, result)
            
            # Update webhook endpoint health
            await self._update_endpoint_health(delivery, webhook_delivered, result)
            
            # Handle retry scheduling for failures
            await self._handle_delivery_retry(delivery, webhook_delivered, result)
            
            # Send delivery notifications if configured
            await self._send_delivery_notifications(delivery, webhook_delivered, result)
            
            # Update delivery status and metadata
            await self._update_delivery_status(delivery, webhook_delivered, result)
            
            # Calculate processing duration
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            result.message = f"Webhook delivery {webhook_delivered.delivery_id} processing completed successfully"
            return result
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Handler processing failed: {str(e)}")
            result.message = f"Webhook delivery processing failed: {str(e)}"
            
            # Calculate duration even on failure
            end_time = utc_now()
            result.processing_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log error but don't re-raise to avoid breaking event flow
            await self._log_handler_error(webhook_delivered.delivery_id, str(e))
            
            return result
    
    async def _get_webhook_delivery(self, delivery_id: WebhookDeliveryId, 
                                   result: WebhookDeliveredHandlerResult) -> Optional[WebhookDelivery]:
        """Retrieve the webhook delivery from repository.
        
        Args:
            delivery_id: ID of the delivery to retrieve
            result: Result object to update with errors
            
        Returns:
            WebhookDelivery if found, None otherwise
        """
        try:
            return await self._webhook_repository.get_delivery_by_id(delivery_id)
        except Exception as e:
            result.errors.append(f"Failed to retrieve webhook delivery {delivery_id}: {str(e)}")
            return None
    
    async def _analyze_webhook_delivery(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered,
                                       result: WebhookDeliveredHandlerResult):
        """Analyze the webhook delivery response and performance.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Result object to update with analysis
        """
        try:
            analysis = {}
            
            # Basic delivery analysis
            analysis["delivery_successful"] = delivery.delivery_status == DeliveryStatus.SUCCESS
            analysis["response_time_ms"] = webhook_delivered.response_time_ms
            analysis["http_status_code"] = webhook_delivered.http_status_code
            analysis["attempt_number"] = webhook_delivered.attempt_number
            
            # Response analysis
            if webhook_delivered.http_status_code:
                analysis.update(await self._analyze_http_response(webhook_delivered))
            
            # Performance analysis
            analysis.update(await self._analyze_delivery_performance(delivery, webhook_delivered))
            
            # Failure analysis (if delivery failed)
            if delivery.delivery_status != DeliveryStatus.SUCCESS:
                analysis.update(await self._analyze_delivery_failure(delivery, webhook_delivered))
            
            # Success metrics (if delivery succeeded)
            else:
                analysis.update(await self._analyze_delivery_success(delivery, webhook_delivered))
            
            result.analysis_results = analysis
            result.delivery_analyzed = True
            
        except Exception as e:
            result.errors.append(f"Failed to analyze webhook delivery: {str(e)}")
            result.delivery_analyzed = False
    
    async def _analyze_http_response(self, webhook_delivered: WebhookDelivered) -> Dict[str, Any]:
        """Analyze HTTP response from webhook endpoint.
        
        Args:
            webhook_delivered: Delivery notification
            
        Returns:
            Dictionary of response analysis
        """
        analysis = {
            "analysis_type": DeliveryAnalysisType.RESPONSE_ANALYSIS.value
        }
        
        status_code = webhook_delivered.http_status_code
        
        if status_code:
            # Categorize response
            if 200 <= status_code < 300:
                analysis["response_category"] = "success"
                analysis["response_quality"] = "good"
            elif 300 <= status_code < 400:
                analysis["response_category"] = "redirect"
                analysis["response_quality"] = "needs_attention"
            elif 400 <= status_code < 500:
                analysis["response_category"] = "client_error"
                analysis["response_quality"] = "bad"
            elif 500 <= status_code < 600:
                analysis["response_category"] = "server_error"
                analysis["response_quality"] = "poor"
            else:
                analysis["response_category"] = "unknown"
                analysis["response_quality"] = "unknown"
            
            # Specific status code analysis
            analysis["requires_retry"] = status_code in [500, 502, 503, 504, 408, 429]
            analysis["permanent_failure"] = status_code in [400, 401, 403, 404, 410, 422]
            analysis["rate_limited"] = status_code == 429
            analysis["endpoint_down"] = status_code in [500, 502, 503, 504]
        
        # Analyze response body if available
        if webhook_delivered.response_body:
            analysis["has_response_body"] = True
            analysis["response_size_bytes"] = len(webhook_delivered.response_body)
            analysis["response_format"] = self._detect_response_format(webhook_delivered.response_body)
        else:
            analysis["has_response_body"] = False
            analysis["response_size_bytes"] = 0
        
        return analysis
    
    async def _analyze_delivery_performance(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered) -> Dict[str, Any]:
        """Analyze performance metrics of the delivery.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            
        Returns:
            Dictionary of performance analysis
        """
        analysis = {
            "analysis_type": DeliveryAnalysisType.PERFORMANCE_ANALYSIS.value,
            "response_time_ms": webhook_delivered.response_time_ms
        }
        
        if webhook_delivered.response_time_ms is not None:
            # Rate response time performance
            if webhook_delivered.response_time_ms < 500:  # < 500ms
                analysis["performance_rating"] = "excellent"
            elif webhook_delivered.response_time_ms < 1000:  # < 1s
                analysis["performance_rating"] = "good"
            elif webhook_delivered.response_time_ms < 3000:  # < 3s
                analysis["performance_rating"] = "acceptable"
            elif webhook_delivered.response_time_ms < 10000:  # < 10s
                analysis["performance_rating"] = "slow"
            else:
                analysis["performance_rating"] = "poor"
            
            # Check if response time is degrading
            analysis["performance_degradation"] = await self._check_performance_degradation(
                delivery.webhook_endpoint_id, webhook_delivered.response_time_ms
            )
        
        return analysis
    
    async def _analyze_delivery_failure(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered) -> Dict[str, Any]:
        """Analyze details of failed delivery.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            
        Returns:
            Dictionary of failure analysis
        """
        analysis = {
            "analysis_type": DeliveryAnalysisType.FAILURE_ANALYSIS.value,
            "failure_reason": delivery.error_message or "Unknown failure",
            "failure_category": self._categorize_delivery_failure(delivery, webhook_delivered)
        }
        
        # Determine if retry is recommended
        analysis["retry_recommended"] = self._should_retry_delivery(delivery, webhook_delivered)
        
        # Check for recurring failures
        analysis["recurring_failure"] = await self._check_recurring_delivery_failures(delivery.webhook_endpoint_id)
        
        # Analyze failure patterns
        analysis["failure_pattern"] = await self._analyze_failure_pattern(delivery, webhook_delivered)
        
        return analysis
    
    async def _analyze_delivery_success(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered) -> Dict[str, Any]:
        """Analyze metrics for successful delivery.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            
        Returns:
            Dictionary of success metrics
        """
        analysis = {
            "analysis_type": DeliveryAnalysisType.SUCCESS_METRICS.value,
            "delivery_quality_score": self._calculate_delivery_quality_score(webhook_delivered),
            "endpoint_reliability": await self._calculate_endpoint_reliability(delivery.webhook_endpoint_id)
        }
        
        # Check delivery consistency
        analysis["consistent_performance"] = await self._check_delivery_consistency(
            delivery.webhook_endpoint_id, webhook_delivered.response_time_ms
        )
        
        return analysis
    
    async def _record_delivery_metrics(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered,
                                     result: WebhookDeliveredHandlerResult):
        """Record metrics about the webhook delivery.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Result object to update with metrics
        """
        try:
            metrics = {
                "delivery_id": str(delivery.id),
                "webhook_endpoint_id": str(delivery.webhook_endpoint_id),
                "event_id": str(delivery.event_id) if delivery.event_id else None,
                "delivery_status": delivery.delivery_status.value,
                "http_status_code": webhook_delivered.http_status_code,
                "response_time_ms": webhook_delivered.response_time_ms,
                "attempt_number": webhook_delivered.attempt_number,
                "delivered_at": webhook_delivered.delivered_at.isoformat() if webhook_delivered.delivered_at else None,
                "delivered_by": str(webhook_delivered.delivered_by) if webhook_delivered.delivered_by else None,
                "response_size_bytes": len(webhook_delivered.response_body) if webhook_delivered.response_body else 0,
                "endpoint_url": delivery.endpoint_url,
                "http_method": delivery.http_method
            }
            
            # Add success-specific metrics
            if delivery.delivery_status == DeliveryStatus.SUCCESS:
                metrics.update({
                    "delivery_quality_score": result.analysis_results.get("delivery_quality_score", 0.0),
                    "performance_rating": result.analysis_results.get("performance_rating", "unknown")
                })
            
            # Add failure-specific metrics
            else:
                metrics.update({
                    "failure_reason": delivery.error_message,
                    "failure_category": result.analysis_results.get("failure_category", "unknown"),
                    "retry_recommended": result.analysis_results.get("retry_recommended", False)
                })
            
            result.metrics_recorded.update(metrics)
            
            # TODO: Send metrics to monitoring system
            # This would integrate with monitoring service when available
            
        except Exception as e:
            result.errors.append(f"Failed to record delivery metrics: {str(e)}")
    
    async def _update_endpoint_health(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered,
                                    result: WebhookDeliveredHandlerResult):
        """Update webhook endpoint health metrics.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Result object to update with health status
        """
        try:
            # Calculate health metrics
            health_update = {
                "last_delivery_at": webhook_delivered.delivered_at or utc_now(),
                "last_response_time_ms": webhook_delivered.response_time_ms,
                "last_http_status": webhook_delivered.http_status_code
            }
            
            # Update success/failure counters
            if delivery.delivery_status == DeliveryStatus.SUCCESS:
                health_update["successful_deliveries"] = 1  # Increment
                health_update["consecutive_failures"] = 0  # Reset
            else:
                health_update["failed_deliveries"] = 1  # Increment
                health_update["consecutive_failures"] = 1  # Increment
                
                # Check if endpoint should be marked as unhealthy
                consecutive_failures = await self._get_consecutive_failures(delivery.webhook_endpoint_id)
                if consecutive_failures >= 5:  # 5 consecutive failures
                    health_update["health_status"] = "unhealthy"
                    health_update["unhealthy_since"] = utc_now()
            
            # Update endpoint health in repository
            await self._webhook_repository.update_endpoint_health(delivery.webhook_endpoint_id, health_update)
            result.endpoint_health_updated = True
            
        except Exception as e:
            result.errors.append(f"Failed to update endpoint health: {str(e)}")
            result.endpoint_health_updated = False
    
    async def _handle_delivery_retry(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered,
                                   result: WebhookDeliveredHandlerResult):
        """Handle retry scheduling for failed deliveries.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Result object to update with retry status
        """
        try:
            # Only schedule retry for failed deliveries
            if delivery.delivery_status == DeliveryStatus.SUCCESS:
                return
            
            # Check if retry is recommended and attempts remain
            if (result.analysis_results.get("retry_recommended", False) and
                webhook_delivered.attempt_number < delivery.max_retry_attempts):
                
                # Calculate retry delay (exponential backoff)
                base_delay = 60  # 1 minute base
                retry_delay_seconds = min(base_delay * (2 ** (webhook_delivered.attempt_number - 1)), 3600)  # Max 1 hour
                
                # Schedule retry
                retry_at = utc_now()
                retry_at = retry_at.replace(second=retry_at.second + retry_delay_seconds)
                
                retry_data = {
                    "delivery_id": delivery.id,
                    "retry_attempt": webhook_delivered.attempt_number + 1,
                    "retry_at": retry_at,
                    "retry_reason": result.analysis_results.get("failure_category", "unknown_failure")
                }
                
                await self._webhook_repository.schedule_delivery_retry(retry_data)
                result.retry_scheduled = True
                
                # Update delivery status to RETRYING
                await self._webhook_repository.update_delivery_status(
                    delivery.id, DeliveryStatus.RETRYING, retry_at
                )
            
            else:
                # No more retries, mark as permanently failed
                if webhook_delivered.attempt_number >= delivery.max_retry_attempts:
                    await self._webhook_repository.update_delivery_status(
                        delivery.id, DeliveryStatus.FAILED, None
                    )
                    
        except Exception as e:
            result.errors.append(f"Failed to handle delivery retry: {str(e)}")
    
    async def _send_delivery_notifications(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered,
                                         result: WebhookDeliveredHandlerResult):
        """Send notifications about webhook delivery results.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Result object to update with notification results
        """
        if not self._notification_service:
            return
        
        try:
            # Determine notification recipients
            recipients = await self._determine_delivery_notification_recipients(delivery, webhook_delivered, result)
            
            for recipient in recipients:
                try:
                    notification_id = await self._send_delivery_notification(
                        recipient, delivery, webhook_delivered, result
                    )
                    result.notifications_sent.append(notification_id)
                except Exception as e:
                    result.errors.append(f"Failed to send notification to {recipient}: {str(e)}")
                    
        except Exception as e:
            result.errors.append(f"Failed to process delivery notifications: {str(e)}")
    
    async def _determine_delivery_notification_recipients(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered,
                                                        result: WebhookDeliveredHandlerResult) -> List[str]:
        """Determine who should receive delivery notifications.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Handler result
            
        Returns:
            List of notification recipient identifiers
        """
        recipients = []
        
        # Notify on delivery failures
        if delivery.delivery_status != DeliveryStatus.SUCCESS:
            recipients.append("admin:webhook_failures")
            
            # Notify on endpoint health issues
            if result.analysis_results.get("recurring_failure", False):
                recipients.append("ops:webhook_health")
        
        # Notify on performance degradation
        if result.analysis_results.get("performance_degradation", False):
            recipients.append("ops:performance_alerts")
        
        # Notify webhook owner (if specified)
        if hasattr(delivery, "owner_id") and delivery.owner_id:
            recipients.append(f"user:{delivery.owner_id}")
        
        return recipients
    
    async def _send_delivery_notification(self, recipient: str, delivery: WebhookDelivery, 
                                        webhook_delivered: WebhookDelivered,
                                        result: WebhookDeliveredHandlerResult) -> str:
        """Send delivery notification to specific recipient.
        
        Args:
            recipient: Notification recipient
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Handler result
            
        Returns:
            Notification ID
        """
        notification_data = {
            "type": "webhook_delivered",
            "delivery_id": str(delivery.id),
            "webhook_endpoint_id": str(delivery.webhook_endpoint_id),
            "endpoint_url": delivery.endpoint_url,
            "delivery_status": delivery.delivery_status.value,
            "http_status_code": webhook_delivered.http_status_code,
            "response_time_ms": webhook_delivered.response_time_ms,
            "attempt_number": webhook_delivered.attempt_number,
            "delivered_at": webhook_delivered.delivered_at.isoformat() if webhook_delivered.delivered_at else None,
            "performance_rating": result.analysis_results.get("performance_rating", "unknown"),
            "recipient": recipient
        }
        
        # Add failure-specific details
        if delivery.delivery_status != DeliveryStatus.SUCCESS:
            notification_data.update({
                "failure_reason": delivery.error_message,
                "failure_category": result.analysis_results.get("failure_category", "unknown"),
                "retry_scheduled": result.retry_scheduled
            })
        
        return await self._notification_service.send_notification(
            recipient=recipient,
            notification_type="webhook_delivered",
            data=notification_data
        )
    
    async def _update_delivery_status(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered,
                                    result: WebhookDeliveredHandlerResult):
        """Update delivery status and metadata after processing.
        
        Args:
            delivery: The webhook delivery
            webhook_delivered: Delivery notification
            result: Processing result
        """
        try:
            metadata_updates = {
                "post_delivery_processed_at": utc_now().isoformat(),
                "delivery_analyzed": result.delivery_analyzed,
                "endpoint_health_updated": result.endpoint_health_updated,
                "retry_scheduled": result.retry_scheduled,
                "notifications_sent": len(result.notifications_sent),
                "analysis_results": result.analysis_results,
                "delivery_metrics": result.metrics_recorded,
                "processing_duration_ms": result.processing_duration_ms
            }
            
            if result.errors:
                metadata_updates["post_delivery_errors"] = result.errors
            
            await self._webhook_repository.update_delivery_metadata(delivery.id, metadata_updates)
            
        except Exception as e:
            result.errors.append(f"Failed to update delivery status: {str(e)}")
    
    # Helper methods for analysis
    
    def _detect_response_format(self, response_body: str) -> str:
        """Detect format of response body."""
        if not response_body:
            return "empty"
        
        response_body = response_body.strip()
        
        if response_body.startswith('{') and response_body.endswith('}'):
            return "json"
        elif response_body.startswith('<') and response_body.endswith('>'):
            return "xml"
        elif response_body.startswith('<!DOCTYPE html') or response_body.startswith('<html'):
            return "html"
        else:
            return "text"
    
    async def _check_performance_degradation(self, endpoint_id: WebhookEndpointId, current_response_time: Optional[float]) -> bool:
        """Check if endpoint performance is degrading."""
        if not current_response_time:
            return False
        
        try:
            # Get recent average response time
            # This would query recent deliveries to calculate average
            # For now, return False as placeholder
            return False
        except:
            return False
    
    def _categorize_delivery_failure(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered) -> str:
        """Categorize the type of delivery failure."""
        if webhook_delivered.http_status_code:
            status = webhook_delivered.http_status_code
            
            if status == 404:
                return "endpoint_not_found"
            elif status in [401, 403]:
                return "authentication_failed"
            elif status == 429:
                return "rate_limited"
            elif status in [500, 502, 503, 504]:
                return "server_error"
            elif status == 408:
                return "timeout"
            elif 400 <= status < 500:
                return "client_error"
            elif 500 <= status < 600:
                return "server_error"
        
        # Check error message
        if delivery.error_message:
            error_msg = delivery.error_message.lower()
            if "timeout" in error_msg:
                return "timeout"
            elif "connection" in error_msg:
                return "connection_failed"
            elif "dns" in error_msg:
                return "dns_resolution_failed"
            elif "ssl" in error_msg or "tls" in error_msg:
                return "ssl_error"
        
        return "unknown_error"
    
    def _should_retry_delivery(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered) -> bool:
        """Determine if delivery should be retried."""
        # Don't retry if no attempts left
        if webhook_delivered.attempt_number >= delivery.max_retry_attempts:
            return False
        
        # Check HTTP status code
        if webhook_delivered.http_status_code:
            status = webhook_delivered.http_status_code
            
            # Retry on server errors and timeouts
            if status in [500, 502, 503, 504, 408, 429]:
                return True
            
            # Don't retry on client errors (except rate limiting)
            if 400 <= status < 500 and status != 429:
                return False
        
        # Check failure category
        failure_category = self._categorize_delivery_failure(delivery, webhook_delivered)
        
        # Retry on transient failures
        retryable_categories = ["timeout", "connection_failed", "server_error", "rate_limited"]
        return failure_category in retryable_categories
    
    async def _check_recurring_delivery_failures(self, endpoint_id: WebhookEndpointId) -> bool:
        """Check if endpoint has recurring delivery failures."""
        try:
            # This would query recent failures for the endpoint
            # For now, return False as placeholder
            return False
        except:
            return False
    
    async def _analyze_failure_pattern(self, delivery: WebhookDelivery, webhook_delivered: WebhookDelivered) -> Dict[str, Any]:
        """Analyze failure patterns for the endpoint."""
        return {
            "failure_type": self._categorize_delivery_failure(delivery, webhook_delivered),
            "time_of_day": webhook_delivered.delivered_at.hour if webhook_delivered.delivered_at else None,
            "day_of_week": webhook_delivered.delivered_at.weekday() if webhook_delivered.delivered_at else None
        }
    
    def _calculate_delivery_quality_score(self, webhook_delivered: WebhookDelivered) -> float:
        """Calculate quality score for successful delivery."""
        score = 1.0
        
        # Reduce score for slow responses
        if webhook_delivered.response_time_ms:
            if webhook_delivered.response_time_ms > 5000:  # > 5s
                score -= 0.3
            elif webhook_delivered.response_time_ms > 2000:  # > 2s
                score -= 0.1
        
        # Reduce score for non-2xx status codes
        if webhook_delivered.http_status_code:
            if not (200 <= webhook_delivered.http_status_code < 300):
                score -= 0.2
        
        # Reduce score for multiple attempts
        if webhook_delivered.attempt_number > 1:
            score -= 0.1 * (webhook_delivered.attempt_number - 1)
        
        return max(score, 0.0)
    
    async def _calculate_endpoint_reliability(self, endpoint_id: WebhookEndpointId) -> float:
        """Calculate reliability score for endpoint."""
        try:
            # This would calculate success rate over recent deliveries
            # For now, return default value
            return 0.95
        except:
            return 0.0
    
    async def _check_delivery_consistency(self, endpoint_id: WebhookEndpointId, response_time: Optional[float]) -> bool:
        """Check if delivery performance is consistent."""
        try:
            # This would check variance in response times
            # For now, return True as placeholder
            return True
        except:
            return False
    
    async def _get_consecutive_failures(self, endpoint_id: WebhookEndpointId) -> int:
        """Get count of consecutive failures for endpoint."""
        try:
            # This would query recent delivery failures
            # For now, return 0 as placeholder
            return 0
        except:
            return 0
    
    async def _log_handler_error(self, delivery_id: WebhookDeliveryId, error_message: str):
        """Log handler error for monitoring and debugging."""
        error_log = {
            "handler": "WebhookDeliveredHandler",
            "delivery_id": str(delivery_id),
            "error": error_message,
            "timestamp": utc_now().isoformat(),
            "level": "error"
        }
        
        # In a real implementation, this would be sent to a logging service
        print(f"Handler Error: {error_log}")


def create_webhook_delivered_handler(
    webhook_repository: WebhookRepository,
    event_repository: EventRepository,
    notification_service: Optional[NotificationService] = None
) -> WebhookDeliveredHandler:
    """Factory function to create WebhookDeliveredHandler instance.
    
    Args:
        webhook_repository: Repository for webhook operations
        event_repository: Repository for event operations
        notification_service: Optional service for sending notifications
        
    Returns:
        Configured WebhookDeliveredHandler instance
    """
    return WebhookDeliveredHandler(
        webhook_repository=webhook_repository,
        event_repository=event_repository,
        notification_service=notification_service
    )