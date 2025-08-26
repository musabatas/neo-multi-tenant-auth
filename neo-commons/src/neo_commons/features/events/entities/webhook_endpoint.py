"""Webhook endpoint domain entity.

This module defines the WebhookEndpoint entity and related business logic.
Matches webhook_endpoints table structure from the database migrations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
import secrets
import hashlib
import hmac

from ....core.value_objects import WebhookEndpointId, UserId


@dataclass
class WebhookEndpoint:
    """Webhook endpoint domain entity.
    
    Represents a webhook endpoint configuration for event subscriptions.
    Matches webhook_endpoints table structure in both admin and tenant schemas.
    """
    
    # Identification and naming
    id: WebhookEndpointId
    name: str
    description: Optional[str] = None
    
    # Endpoint configuration
    endpoint_url: str
    http_method: str = "POST"
    
    # Authentication and security
    secret_token: str
    signature_header: str = "X-Webhook-Signature"
    
    # Custom headers (for API keys, etc.)
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Configuration options
    timeout_seconds: int = 30
    follow_redirects: bool = False
    verify_ssl: bool = True
    
    # Retry configuration
    max_retry_attempts: int = 3
    retry_backoff_seconds: int = 5
    retry_backoff_multiplier: Decimal = Decimal("2.0")
    
    # Status and lifecycle
    is_active: bool = True
    is_verified: bool = False
    
    # Generic context
    created_by_user_id: UserId
    context_id: Optional[UUID] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization validation."""
        from ..utils.validation import WebhookValidationRules
        
        # Validate endpoint name
        try:
            WebhookValidationRules.validate_endpoint_name(self.name)
        except ValueError as e:
            raise ValueError(f"Invalid endpoint name: {e}")
        
        # Validate endpoint URL
        try:
            WebhookValidationRules.validate_webhook_url(self.endpoint_url)
        except ValueError as e:
            raise ValueError(f"Invalid endpoint URL: {e}")
        
        # Validate HTTP method
        if self.http_method not in ["POST", "PUT", "PATCH"]:
            raise ValueError(f"Invalid HTTP method: {self.http_method}")
        
        # Validate configurations using centralized validation
        WebhookValidationRules.validate_timeout_seconds(self.timeout_seconds)
        WebhookValidationRules.validate_retry_config(
            self.max_retry_attempts, 
            self.retry_backoff_seconds, 
            float(self.retry_backoff_multiplier)
        )
        WebhookValidationRules.validate_secret_token(self.secret_token)
        WebhookValidationRules.validate_custom_headers(self.custom_headers)
        
        # Generate secret token if not provided
        if not self.secret_token:
            self.secret_token = self._generate_secret_token()
        
        # Ensure timestamps are timezone-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
    
    @classmethod
    def _generate_secret_token(cls) -> str:
        """Generate a secure random secret token."""
        return secrets.token_urlsafe(64)
    
    def generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            self.secret_token.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_signature(self, payload: str, received_signature: str) -> bool:
        """Verify webhook payload signature."""
        expected_signature = self.generate_signature(payload)
        return hmac.compare_digest(expected_signature, received_signature)
    
    def activate(self) -> None:
        """Activate the webhook endpoint."""
        if not self.is_active:
            self.is_active = True
            self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate the webhook endpoint."""
        if self.is_active:
            self.is_active = False
            self.updated_at = datetime.now(timezone.utc)
    
    def verify(self) -> None:
        """Mark endpoint as verified."""
        if not self.is_verified:
            self.is_verified = True
            self.verified_at = datetime.now(timezone.utc)
            self.updated_at = datetime.now(timezone.utc)
    
    def unverify(self) -> None:
        """Mark endpoint as unverified."""
        if self.is_verified:
            self.is_verified = False
            self.verified_at = None
            self.updated_at = datetime.now(timezone.utc)
    
    def mark_used(self) -> None:
        """Update last used timestamp."""
        self.last_used_at = datetime.now(timezone.utc)
    
    def update_url(self, new_url: str) -> None:
        """Update endpoint URL and reset verification status."""
        from ..utils.validation import WebhookValidationRules
        
        WebhookValidationRules.validate_webhook_url(new_url)
        
        self.endpoint_url = new_url
        self.is_verified = False
        self.verified_at = None
        self.updated_at = datetime.now(timezone.utc)
    
    def rotate_secret(self) -> str:
        """Rotate the secret token and return the new one."""
        old_secret = self.secret_token
        self.secret_token = self._generate_secret_token()
        self.updated_at = datetime.now(timezone.utc)
        return old_secret
    
    def update_headers(self, headers: Dict[str, str]) -> None:
        """Update custom headers."""
        from ..utils.validation import WebhookValidationRules
        
        WebhookValidationRules.validate_custom_headers(headers)
        self.custom_headers.update(headers)
        self.updated_at = datetime.now(timezone.utc)
    
    def set_retry_config(self, max_attempts: int, backoff_seconds: int, multiplier: float) -> None:
        """Update retry configuration."""
        from ..utils.validation import WebhookValidationRules
        
        WebhookValidationRules.validate_retry_config(max_attempts, backoff_seconds, multiplier)
        
        self.max_retry_attempts = max_attempts
        self.retry_backoff_seconds = backoff_seconds
        self.retry_backoff_multiplier = Decimal(str(multiplier))
        self.updated_at = datetime.now(timezone.utc)
    
    def calculate_retry_delay(self, attempt_number: int) -> int:
        """Calculate retry delay for given attempt number."""
        if attempt_number <= 0:
            return 0
        
        # Exponential backoff: delay = base_delay * (multiplier ^ (attempt - 1))
        delay = self.retry_backoff_seconds * (float(self.retry_backoff_multiplier) ** (attempt_number - 1))
        return min(int(delay), 3600)  # Cap at 1 hour
    
    def can_subscribe_to_verified_events(self) -> bool:
        """Check if endpoint can subscribe to events requiring verification."""
        return self.is_active and self.is_verified
    
    def get_request_headers(self) -> Dict[str, str]:
        """Get all headers for webhook request including signature header."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "NeoWebhook/1.0",
            **self.custom_headers
        }
        return headers