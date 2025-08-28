"""Webhook validator for platform events infrastructure.

This module handles ONLY webhook validation operations following maximum separation architecture.
Single responsibility: Validate webhook endpoints and deliveries for configuration integrity, security, and platform constraints.

Pure application layer - no infrastructure concerns.
Contains business validation logic that goes beyond basic entity validation.
"""

import re
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
from urllib.parse import urlparse

from ...core.entities import WebhookEndpoint, WebhookDelivery
from ...core.value_objects import WebhookEndpointId, WebhookDeliveryId, DeliveryStatus
from ...core.exceptions import InvalidEventConfiguration
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now


@dataclass
class WebhookValidationResult:
    """Result of webhook validation operation.
    
    Contains comprehensive validation feedback including all validation
    errors, warnings, and recommendations for webhook improvement.
    """
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    recommendations: List[str] = None
    validation_summary: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.recommendations is None:
            self.recommendations = []


class WebhookValidator:
    """Webhook validator for comprehensive webhook endpoint and delivery validation.
    
    Single responsibility: Validate webhook endpoints and deliveries against business rules,
    security constraints, and platform requirements. Provides detailed validation feedback
    for webhook configuration and delivery tracking.
    
    Following enterprise validation pattern with comprehensive rule checking.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    # URL validation patterns
    VALID_URL_PATTERN = r'^https?://[^\s/$.?#].[^\s]*$'
    SECURE_URL_PATTERN = r'^https://[^\s/$.?#].[^\s]*$'
    
    # Webhook name validation
    VALID_WEBHOOK_NAME_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9\s\-_\.]*[a-zA-Z0-9]$'
    
    # Maximum sizes for validation
    MAX_WEBHOOK_NAME_LENGTH = 255
    MAX_DESCRIPTION_LENGTH = 2000
    MAX_CUSTOM_HEADERS_SIZE_BYTES = 8 * 1024  # 8KB
    MAX_SECRET_TOKEN_LENGTH = 512
    MAX_SIGNATURE_HEADER_LENGTH = 100
    MAX_URL_LENGTH = 2048
    MAX_NESTED_DEPTH = 3
    
    # Timeout constraints (seconds) - matches database constraints
    MIN_TIMEOUT_SECONDS = 5
    MAX_TIMEOUT_SECONDS = 300
    RECOMMENDED_TIMEOUT_SECONDS = 30
    
    # Retry constraints - matches database constraints
    MIN_RETRY_ATTEMPTS = 0
    MAX_RETRY_ATTEMPTS = 10
    MIN_RETRY_BACKOFF = 1
    MAX_RETRY_BACKOFF = 3600  # 1 hour
    MIN_BACKOFF_MULTIPLIER = Decimal("1.0")
    MAX_BACKOFF_MULTIPLIER = Decimal("5.0")
    
    # HTTP methods - matches database constraints
    VALID_HTTP_METHODS = {"POST", "PUT", "PATCH"}
    
    # Delivery status values - matches database constraints
    VALID_DELIVERY_STATUSES = {"pending", "success", "failed", "timeout", "retrying", "cancelled"}
    
    # Security headers that should not be overridden
    PROTECTED_HEADERS = {
        'authorization', 'x-webhook-signature', 'content-type', 
        'content-length', 'host', 'user-agent'
    }
    
    # Dangerous URL patterns to warn about
    DANGEROUS_URL_PATTERNS = [
        r'localhost', r'127\.0\.0\.1', r'0\.0\.0\.0', r'10\.', r'192\.168\.', r'172\.(1[6-9]|2[0-9]|3[01])\.'
    ]
    
    # Common webhook services for recommendations
    COMMON_WEBHOOK_SERVICES = {
        'slack.com': 'Slack webhook',
        'discord.com': 'Discord webhook',
        'teams.microsoft.com': 'Microsoft Teams webhook',
        'hooks.zapier.com': 'Zapier webhook',
        'api.github.com': 'GitHub webhook',
        'webhooks.stripe.com': 'Stripe webhook'
    }
    
    def __init__(self):
        """Initialize webhook validator with validation rules."""
        pass
    
    def validate_webhook_endpoint(self, endpoint: WebhookEndpoint) -> WebhookValidationResult:
        """Validate a webhook endpoint comprehensively.
        
        Performs complete endpoint validation including:
        1. Basic field validation
        2. URL security validation
        3. Authentication validation
        4. Configuration validation
        5. Header validation
        6. Retry policy validation
        
        Args:
            endpoint: WebhookEndpoint to validate
            
        Returns:
            WebhookValidationResult with comprehensive validation feedback
        """
        result = WebhookValidationResult(is_valid=True)
        
        try:
            # 1. Basic field validation
            self._validate_endpoint_basic_fields(endpoint, result)
            
            # 2. URL security validation
            self._validate_endpoint_url(endpoint, result)
            
            # 3. Authentication validation
            self._validate_authentication_config(endpoint, result)
            
            # 4. Configuration validation
            self._validate_endpoint_configuration(endpoint, result)
            
            # 5. Header validation
            self._validate_custom_headers(endpoint, result)
            
            # 6. Retry policy validation
            self._validate_retry_policy(endpoint, result)
            
            # Final validation status
            result.is_valid = len(result.errors) == 0
            
            # Generate summary
            result.validation_summary = self._generate_validation_summary(result)
            
            return result
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Webhook endpoint validation failed with exception: {str(e)}")
            result.validation_summary = "Webhook endpoint validation failed due to unexpected error"
            return result
    
    def validate_webhook_delivery(self, delivery: WebhookDelivery) -> WebhookValidationResult:
        """Validate a webhook delivery comprehensively.
        
        Performs complete delivery validation including:
        1. Basic field validation
        2. Request validation
        3. Response validation
        4. Status validation
        5. Timing validation
        
        Args:
            delivery: WebhookDelivery to validate
            
        Returns:
            WebhookValidationResult with comprehensive validation feedback
        """
        result = WebhookValidationResult(is_valid=True)
        
        try:
            # 1. Basic field validation
            self._validate_delivery_basic_fields(delivery, result)
            
            # 2. Request validation
            self._validate_delivery_request(delivery, result)
            
            # 3. Response validation
            self._validate_delivery_response(delivery, result)
            
            # 4. Status validation
            self._validate_delivery_status(delivery, result)
            
            # 5. Timing validation
            self._validate_delivery_timing(delivery, result)
            
            # Final validation status
            result.is_valid = len(result.errors) == 0
            
            # Generate summary
            result.validation_summary = self._generate_validation_summary(result)
            
            return result
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Webhook delivery validation failed with exception: {str(e)}")
            result.validation_summary = "Webhook delivery validation failed due to unexpected error"
            return result
    
    def validate_webhook_url(self, url: str) -> WebhookValidationResult:
        """Validate webhook URL format and security.
        
        Convenience method for validating webhook URL without
        requiring a full webhook endpoint. Useful for API validation.
        
        Args:
            url: Webhook URL to validate
            
        Returns:
            WebhookValidationResult with URL validation feedback
        """
        result = WebhookValidationResult(is_valid=True)
        
        if not url:
            result.errors.append("Webhook URL cannot be empty")
            result.is_valid = False
            return result
        
        # Basic URL format validation
        if not re.match(self.VALID_URL_PATTERN, url, re.IGNORECASE):
            result.errors.append("Invalid webhook URL format. Must be a valid HTTP/HTTPS URL")
            result.is_valid = False
            return result
        
        # Length validation
        if len(url) > self.MAX_URL_LENGTH:
            result.errors.append(f"Webhook URL exceeds maximum length of {self.MAX_URL_LENGTH} characters")
            result.is_valid = False
        
        # Security validation
        self._validate_url_security(url, result)
        
        # Service-specific recommendations
        self._validate_url_service_patterns(url, result)
        
        return result
    
    def validate_custom_headers(self, headers: Dict[str, Any]) -> WebhookValidationResult:
        """Validate custom headers configuration.
        
        Convenience method for validating custom headers without
        requiring a full webhook endpoint. Useful for API validation.
        
        Args:
            headers: Custom headers dictionary to validate
            
        Returns:
            WebhookValidationResult with headers validation feedback
        """
        result = WebhookValidationResult(is_valid=True)
        
        if headers is None:
            headers = {}
        
        if not isinstance(headers, dict):
            result.errors.append("Custom headers must be a dictionary")
            result.is_valid = False
            return result
        
        # Validate individual headers
        for key, value in headers.items():
            self._validate_header_pair(key, value, result)
        
        # Structure validation
        self._validate_headers_structure(headers, result)
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def _validate_endpoint_basic_fields(self, endpoint: WebhookEndpoint, result: WebhookValidationResult) -> None:
        """Validate basic required fields of the webhook endpoint."""
        # Endpoint ID validation
        if not endpoint.id or not endpoint.id.value:
            result.errors.append("Webhook endpoint ID is required")
        
        # Name validation
        if not endpoint.name or not endpoint.name.strip():
            result.errors.append("Webhook endpoint name cannot be empty")
        elif len(endpoint.name) > self.MAX_WEBHOOK_NAME_LENGTH:
            result.errors.append(f"Webhook name exceeds maximum length of {self.MAX_WEBHOOK_NAME_LENGTH}")
        elif not re.match(self.VALID_WEBHOOK_NAME_PATTERN, endpoint.name):
            result.errors.append("Webhook name must start and end with alphanumeric characters and contain only letters, numbers, spaces, hyphens, underscores, and dots")
        
        # Description validation
        if endpoint.description and len(endpoint.description) > self.MAX_DESCRIPTION_LENGTH:
            result.errors.append(f"Webhook description exceeds maximum length of {self.MAX_DESCRIPTION_LENGTH}")
        
        # HTTP method validation
        if endpoint.http_method not in self.VALID_HTTP_METHODS:
            result.errors.append(f"Invalid HTTP method: {endpoint.http_method}. Must be one of: {', '.join(self.VALID_HTTP_METHODS)}")
        
        # User validation
        if endpoint.created_by_user_id and not endpoint.created_by_user_id.value:
            result.errors.append("Created by user ID cannot be empty if provided")
        
        # Timestamp validation
        self._validate_endpoint_timestamps(endpoint, result)
    
    def _validate_endpoint_url(self, endpoint: WebhookEndpoint, result: WebhookValidationResult) -> None:
        """Validate webhook endpoint URL."""
        url_validation = self.validate_webhook_url(endpoint.endpoint_url)
        result.errors.extend(url_validation.errors)
        result.warnings.extend(url_validation.warnings)
        result.recommendations.extend(url_validation.recommendations)
    
    def _validate_authentication_config(self, endpoint: WebhookEndpoint, result: WebhookValidationResult) -> None:
        """Validate authentication configuration."""
        # Secret token validation
        if not endpoint.secret_token:
            result.errors.append("Secret token is required for webhook authentication")
        elif len(endpoint.secret_token) > self.MAX_SECRET_TOKEN_LENGTH:
            result.errors.append(f"Secret token exceeds maximum length of {self.MAX_SECRET_TOKEN_LENGTH}")
        elif len(endpoint.secret_token) < 16:
            result.warnings.append("Secret token is short. Consider using at least 16 characters for better security")
        
        # Signature header validation
        if not endpoint.signature_header:
            result.errors.append("Signature header name is required")
        elif len(endpoint.signature_header) > self.MAX_SIGNATURE_HEADER_LENGTH:
            result.errors.append(f"Signature header name exceeds maximum length of {self.MAX_SIGNATURE_HEADER_LENGTH}")
        elif not re.match(r'^[a-zA-Z][a-zA-Z0-9\-_]*$', endpoint.signature_header):
            result.errors.append("Signature header name must start with a letter and contain only letters, numbers, hyphens, and underscores")
        
        # Standard signature header recommendations
        if endpoint.signature_header.lower() not in ['x-webhook-signature', 'x-signature', 'x-hub-signature']:
            result.recommendations.append("Consider using a standard signature header name like 'X-Webhook-Signature'")
    
    def _validate_endpoint_configuration(self, endpoint: WebhookEndpoint, result: WebhookValidationResult) -> None:
        """Validate endpoint configuration settings."""
        # Timeout validation
        if not (self.MIN_TIMEOUT_SECONDS <= endpoint.timeout_seconds <= self.MAX_TIMEOUT_SECONDS):
            result.errors.append(f"Timeout must be between {self.MIN_TIMEOUT_SECONDS} and {self.MAX_TIMEOUT_SECONDS} seconds")
        elif endpoint.timeout_seconds != self.RECOMMENDED_TIMEOUT_SECONDS:
            result.recommendations.append(f"Consider using the recommended timeout of {self.RECOMMENDED_TIMEOUT_SECONDS} seconds")
        
        # SSL verification recommendation
        if not endpoint.verify_ssl:
            result.warnings.append("SSL verification is disabled. This may expose your webhooks to man-in-the-middle attacks")
        
        # Redirect following warning
        if endpoint.follow_redirects:
            result.warnings.append("Following redirects is enabled. This may lead to unexpected behavior or security issues")
    
    def _validate_custom_headers(self, endpoint: WebhookEndpoint, result: WebhookValidationResult) -> None:
        """Validate custom headers configuration."""
        headers_validation = self.validate_custom_headers(endpoint.custom_headers)
        result.errors.extend(headers_validation.errors)
        result.warnings.extend(headers_validation.warnings)
        result.recommendations.extend(headers_validation.recommendations)
    
    def _validate_retry_policy(self, endpoint: WebhookEndpoint, result: WebhookValidationResult) -> None:
        """Validate retry policy configuration."""
        # Max retry attempts validation
        if not (self.MIN_RETRY_ATTEMPTS <= endpoint.max_retry_attempts <= self.MAX_RETRY_ATTEMPTS):
            result.errors.append(f"Max retry attempts must be between {self.MIN_RETRY_ATTEMPTS} and {self.MAX_RETRY_ATTEMPTS}")
        
        # Retry backoff validation
        if not (self.MIN_RETRY_BACKOFF <= endpoint.retry_backoff_seconds <= self.MAX_RETRY_BACKOFF):
            result.errors.append(f"Retry backoff must be between {self.MIN_RETRY_BACKOFF} and {self.MAX_RETRY_BACKOFF} seconds")
        
        # Backoff multiplier validation
        if not (self.MIN_BACKOFF_MULTIPLIER <= endpoint.retry_backoff_multiplier <= self.MAX_BACKOFF_MULTIPLIER):
            result.errors.append(f"Retry backoff multiplier must be between {self.MIN_BACKOFF_MULTIPLIER} and {self.MAX_BACKOFF_MULTIPLIER}")
        
        # Retry policy recommendations
        if endpoint.max_retry_attempts > 5:
            result.warnings.append("High retry attempts may cause delays. Consider using exponential backoff")
        
        if endpoint.retry_backoff_multiplier == Decimal("1.0"):
            result.recommendations.append("Consider using exponential backoff (multiplier > 1.0) for better retry behavior")
    
    def _validate_delivery_basic_fields(self, delivery: WebhookDelivery, result: WebhookValidationResult) -> None:
        """Validate basic required fields of the webhook delivery."""
        # Delivery ID validation
        if not delivery.id or not delivery.id.value:
            result.errors.append("Webhook delivery ID is required")
        
        # Endpoint and event references
        if not delivery.webhook_endpoint_id or not delivery.webhook_endpoint_id.value:
            result.errors.append("Webhook endpoint ID is required")
        
        if not delivery.event_id:
            result.errors.append("Event ID is required for delivery tracking")
        
        # Attempt number validation
        if delivery.attempt_number < 1:
            result.errors.append("Attempt number must be at least 1")
        elif delivery.attempt_number > 20:
            result.warnings.append("Very high attempt number may indicate delivery issues")
        
        # Status validation
        if not isinstance(delivery.status, DeliveryStatus):
            result.errors.append("Delivery status must be a valid DeliveryStatus")
    
    def _validate_delivery_request(self, delivery: WebhookDelivery, result: WebhookValidationResult) -> None:
        """Validate webhook delivery request details."""
        # Request URL validation
        if not delivery.request_url:
            result.errors.append("Request URL is required")
        else:
            url_validation = self.validate_webhook_url(delivery.request_url)
            if url_validation.errors:
                result.errors.extend([f"Request URL: {error}" for error in url_validation.errors])
        
        # Request method validation
        if delivery.request_method not in self.VALID_HTTP_METHODS:
            result.errors.append(f"Invalid request method: {delivery.request_method}")
        
        # Request headers validation
        if delivery.request_headers and not isinstance(delivery.request_headers, dict):
            result.errors.append("Request headers must be a dictionary")
        
        # Signature validation
        if not delivery.request_signature:
            result.warnings.append("No request signature provided. This may affect webhook verification")
        elif not delivery.request_signature.startswith(('sha256=', 'sha1=')):
            result.warnings.append("Request signature format may be invalid. Expected format: 'sha256=...'")
    
    def _validate_delivery_response(self, delivery: WebhookDelivery, result: WebhookValidationResult) -> None:
        """Validate webhook delivery response details."""
        # Response status code validation
        if delivery.response_status_code is not None:
            if not (100 <= delivery.response_status_code <= 599):
                result.errors.append(f"Invalid HTTP response status code: {delivery.response_status_code}")
            elif delivery.response_status_code >= 400:
                result.warnings.append(f"HTTP error response: {delivery.response_status_code}")
        
        # Response time validation
        if delivery.response_time_ms is not None:
            if delivery.response_time_ms < 0:
                result.errors.append("Response time cannot be negative")
            elif delivery.response_time_ms > 30000:  # 30 seconds
                result.warnings.append(f"Very slow response time: {delivery.response_time_ms}ms")
    
    def _validate_delivery_status(self, delivery: WebhookDelivery, result: WebhookValidationResult) -> None:
        """Validate delivery status consistency."""
        status_value = delivery.status.value if hasattr(delivery.status, 'value') else str(delivery.status)
        
        if status_value not in self.VALID_DELIVERY_STATUSES:
            result.errors.append(f"Invalid delivery status: {status_value}")
        
        # Status consistency checks
        if status_value == "success":
            if not delivery.response_status_code or delivery.response_status_code >= 400:
                result.warnings.append("Delivery marked as success but response indicates failure")
        elif status_value == "failed":
            if not delivery.error_message:
                result.recommendations.append("Failed deliveries should include an error message")
        elif status_value == "timeout":
            if delivery.response_time_ms and delivery.response_time_ms < 30000:
                result.warnings.append("Delivery marked as timeout but response time seems reasonable")
    
    def _validate_delivery_timing(self, delivery: WebhookDelivery, result: WebhookValidationResult) -> None:
        """Validate delivery timing consistency."""
        # Timestamp order validation
        if delivery.attempted_at and delivery.completed_at:
            if delivery.completed_at < delivery.attempted_at:
                result.errors.append("Completed at cannot be before attempted at")
        
        # Response time consistency
        if (delivery.attempted_at and delivery.completed_at and 
            delivery.response_time_ms is not None):
            calculated_time = int((delivery.completed_at - delivery.attempted_at).total_seconds() * 1000)
            if abs(calculated_time - delivery.response_time_ms) > 1000:  # 1 second tolerance
                result.warnings.append("Response time inconsistent with attempted/completed timestamps")
        
        # Retry timing validation
        if delivery.next_retry_at:
            if delivery.next_retry_at <= utc_now():
                result.recommendations.append("Next retry time has passed. Consider rescheduling")
    
    def _validate_url_security(self, url: str, result: WebhookValidationResult) -> None:
        """Validate URL security aspects."""
        try:
            parsed = urlparse(url)
            
            # HTTPS recommendation
            if parsed.scheme == 'http':
                result.warnings.append("HTTP URLs are not secure. Consider using HTTPS")
            
            # Check for dangerous internal networks
            hostname = parsed.hostname or parsed.netloc
            for pattern in self.DANGEROUS_URL_PATTERNS:
                if re.search(pattern, hostname, re.IGNORECASE):
                    result.warnings.append(f"URL appears to target internal network: {hostname}")
                    break
            
            # Port validation
            if parsed.port:
                if parsed.port in [22, 23, 25, 53, 110, 143, 993, 995]:
                    result.warnings.append(f"Unusual port for webhook: {parsed.port}")
        
        except Exception:
            result.warnings.append("Could not parse URL for security validation")
    
    def _validate_url_service_patterns(self, url: str, result: WebhookValidationResult) -> None:
        """Validate URL against known service patterns."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname or parsed.netloc
            
            # Check for known services
            for service_domain, service_name in self.COMMON_WEBHOOK_SERVICES.items():
                if service_domain in hostname.lower():
                    result.recommendations.append(f"Detected {service_name}. Ensure you follow their webhook guidelines")
                    break
            
            # URL pattern recommendations
            if not parsed.path or parsed.path == '/':
                result.recommendations.append("Consider using a specific path for webhook endpoints")
                
        except Exception:
            pass  # Skip service pattern validation if URL parsing fails
    
    def _validate_header_pair(self, key: str, value: Any, result: WebhookValidationResult) -> None:
        """Validate a single header key-value pair."""
        # Key validation
        if not isinstance(key, str) or not key.strip():
            result.errors.append("Header names must be non-empty strings")
            return
        
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9\-_]*$', key):
            result.errors.append(f"Invalid header name format: {key}")
        
        # Protected header warning
        if key.lower() in self.PROTECTED_HEADERS:
            result.warnings.append(f"Header '{key}' is typically managed by the system and should not be overridden")
        
        # Value validation
        if not isinstance(value, (str, int, float, bool)):
            result.errors.append(f"Header value for '{key}' must be a string, number, or boolean")
        
        # Value length check
        if isinstance(value, str) and len(value) > 2048:
            result.warnings.append(f"Very long header value for '{key}' may cause issues")
    
    def _validate_headers_structure(self, headers: Dict[str, Any], result: WebhookValidationResult) -> None:
        """Validate headers structure and size."""
        # Size validation
        headers_size = self._calculate_data_size(headers)
        if headers_size > self.MAX_CUSTOM_HEADERS_SIZE_BYTES:
            result.errors.append(f"Custom headers size ({headers_size} bytes) exceeds maximum ({self.MAX_CUSTOM_HEADERS_SIZE_BYTES} bytes)")
        
        # Depth validation
        headers_depth = self._get_max_depth(headers)
        if headers_depth > self.MAX_NESTED_DEPTH:
            result.errors.append(f"Custom headers nesting depth ({headers_depth}) exceeds maximum ({self.MAX_NESTED_DEPTH})")
        
        # JSON serialization check
        try:
            json.dumps(headers, default=str)
        except (TypeError, ValueError) as e:
            result.errors.append(f"Custom headers are not JSON serializable: {str(e)}")
    
    def _validate_endpoint_timestamps(self, endpoint: WebhookEndpoint, result: WebhookValidationResult) -> None:
        """Validate endpoint timestamps."""
        now = utc_now()
        
        # Created at validation
        if not endpoint.created_at:
            result.errors.append("Created at timestamp is required")
        
        # Updated at validation
        if not endpoint.updated_at:
            result.errors.append("Updated at timestamp is required")
        else:
            # Check timestamp order
            if endpoint.created_at and endpoint.updated_at < endpoint.created_at:
                result.errors.append("Updated at must be after or equal to created at")
        
        # Verification timestamp consistency
        if endpoint.verified_at and not endpoint.is_verified:
            result.warnings.append("Endpoint has verification timestamp but is marked as unverified")
        elif endpoint.is_verified and not endpoint.verified_at:
            result.warnings.append("Endpoint is marked as verified but has no verification timestamp")
        
        # Last used timestamp validation
        if endpoint.last_used_at:
            if endpoint.created_at and endpoint.last_used_at < endpoint.created_at:
                result.errors.append("Last used at cannot be before created at")
    
    def _calculate_data_size(self, data: Any) -> int:
        """Calculate approximate size of data in bytes."""
        try:
            return len(json.dumps(data, default=str, separators=(',', ':')).encode('utf-8'))
        except:
            return 0
    
    def _get_max_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Get maximum nesting depth of an object."""
        if current_depth > self.MAX_NESTED_DEPTH:
            return current_depth
        
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_max_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_max_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    def _generate_validation_summary(self, result: WebhookValidationResult) -> str:
        """Generate a human-readable validation summary."""
        if result.is_valid:
            summary_parts = ["Webhook is valid"]
            
            if result.warnings:
                summary_parts.append(f"with {len(result.warnings)} warning(s)")
            
            if result.recommendations:
                summary_parts.append(f"and {len(result.recommendations)} recommendation(s)")
            
            return " ".join(summary_parts) + "."
        else:
            return f"Webhook validation failed with {len(result.errors)} error(s)."