"""Webhook endpoint entity for platform events infrastructure.

This module defines the WebhookEndpoint entity that represents webhook configuration
for external service integration and event delivery.

Extracted from features/events to platform/events following enterprise
clean architecture patterns for maximum separation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .....core.value_objects import UserId
from .....utils import generate_uuid_v7, utc_now, ensure_utc
from ..value_objects import WebhookEndpointId


@dataclass
class WebhookEndpoint:
    """Webhook endpoint domain entity.
    
    Represents a webhook endpoint configuration for event subscriptions.
    Supports authentication, retry policies, and delivery tracking.
    
    Maps to webhook_endpoints table in both admin and tenant schemas.
    Pure platform infrastructure - used by all business features.
    """
    
    # Identification and naming (UUIDv7 for time-ordering)
    id: WebhookEndpointId = field(default_factory=lambda: WebhookEndpointId(UUID(generate_uuid_v7())))
    name: str = ""
    description: Optional[str] = None
    
    # Endpoint configuration
    endpoint_url: str = ""
    http_method: str = "POST"
    
    # Authentication and security
    secret_token: str = ""
    signature_header: str = "X-Webhook-Signature"
    
    # Custom headers (JSONB for flexibility)
    custom_headers: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration options
    timeout_seconds: int = 30
    follow_redirects: bool = False
    verify_ssl: bool = True
    
    # Retry configuration
    max_retry_attempts: int = 3
    retry_backoff_seconds: int = 5
    retry_backoff_multiplier: Decimal = field(default_factory=lambda: Decimal("2.0"))
    
    # Status and lifecycle
    is_active: bool = True
    is_verified: bool = False  # Endpoint verification status
    
    # Generic context
    created_by_user_id: Optional[UserId] = None
    context_id: Optional[UUID] = None  # Generic context (organization_id, team_id, etc.)
    
    # Timestamps
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_used_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Validate required fields
        if not self.name or not self.name.strip():
            raise ValueError("Webhook endpoint name cannot be empty")
        
        if not self.endpoint_url or not self.endpoint_url.strip():
            raise ValueError("Webhook endpoint URL cannot be empty")
        
        # Validate HTTP method (matches database check constraint)
        if self.http_method not in {"POST", "PUT", "PATCH"}:
            raise ValueError(f"Invalid HTTP method: {self.http_method}. Must be POST, PUT, or PATCH")
        
        # Validate timeout (matches database check constraint)
        if not (5 <= self.timeout_seconds <= 300):
            raise ValueError(f"Invalid timeout: {self.timeout_seconds}. Must be between 5 and 300 seconds")
        
        # Validate retry configuration (matches database check constraints)
        if not (0 <= self.max_retry_attempts <= 10):
            raise ValueError(f"Invalid max retry attempts: {self.max_retry_attempts}. Must be between 0 and 10")
        
        if not (1 <= self.retry_backoff_seconds <= 3600):
            raise ValueError(f"Invalid retry backoff: {self.retry_backoff_seconds}. Must be between 1 and 3600 seconds")
        
        if not (Decimal("1.0") <= self.retry_backoff_multiplier <= Decimal("5.0")):
            raise ValueError(f"Invalid backoff multiplier: {self.retry_backoff_multiplier}. Must be between 1.0 and 5.0")
        
        # Validate URL format (basic validation)
        if not self._is_valid_url(self.endpoint_url):
            raise ValueError(f"Invalid webhook URL format: {self.endpoint_url}")
        
        # Ensure timestamps are timezone-aware
        self.created_at = ensure_utc(self.created_at)
        self.updated_at = ensure_utc(self.updated_at)
        
        if self.last_used_at:
            self.last_used_at = ensure_utc(self.last_used_at)
        
        if self.verified_at:
            self.verified_at = ensure_utc(self.verified_at)
        
        # Generate secret token if not provided
        if not self.secret_token:
            self.secret_token = self._generate_secret_token()
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        import re
        # Basic URL pattern that requires http/https protocol
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return bool(url_pattern.match(url))
    
    def _generate_secret_token(self) -> str:
        """Generate a secure random secret token."""
        import secrets
        return secrets.token_urlsafe(32)
    
    def update_endpoint_url(self, new_url: str) -> None:
        """Update the endpoint URL with validation."""
        if not new_url or not new_url.strip():
            raise ValueError("Endpoint URL cannot be empty")
        
        if not self._is_valid_url(new_url):
            raise ValueError(f"Invalid webhook URL format: {new_url}")
        
        self.endpoint_url = new_url.strip()
        self.updated_at = utc_now()
        # Reset verification status when URL changes
        self.is_verified = False
        self.verified_at = None
    
    def mark_as_verified(self) -> None:
        """Mark the endpoint as verified."""
        self.is_verified = True
        self.verified_at = utc_now()
        self.updated_at = utc_now()
    
    def mark_as_unverified(self) -> None:
        """Mark the endpoint as unverified."""
        self.is_verified = False
        self.verified_at = None
        self.updated_at = utc_now()
    
    def activate(self) -> None:
        """Activate the webhook endpoint."""
        self.is_active = True
        self.updated_at = utc_now()
    
    def deactivate(self) -> None:
        """Deactivate the webhook endpoint."""
        self.is_active = False
        self.updated_at = utc_now()
    
    def update_last_used(self) -> None:
        """Update the last used timestamp."""
        self.last_used_at = utc_now()
    
    def regenerate_secret_token(self) -> str:
        """Regenerate the secret token and return the new one."""
        self.secret_token = self._generate_secret_token()
        self.updated_at = utc_now()
        # Reset verification status when secret changes
        self.is_verified = False
        self.verified_at = None
        return self.secret_token
    
    def update_custom_headers(self, headers: Dict[str, Any]) -> None:
        """Update custom headers with validation."""
        if not isinstance(headers, dict):
            raise ValueError("Custom headers must be a dictionary")
        
        # Validate header names and values
        for key, value in headers.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("Header names must be non-empty strings")
            if not isinstance(value, (str, int, float, bool)):
                raise ValueError("Header values must be strings, numbers, or booleans")
        
        self.custom_headers = headers
        self.updated_at = utc_now()
    
    def generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for the payload."""
        import hmac
        import hashlib
        
        signature = hmac.new(
            self.secret_token.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"sha256={signature}"
    
    def validate_signature(self, payload: str, received_signature: str) -> bool:
        """Validate received signature against payload."""
        expected_signature = self.generate_signature(payload)
        
        # Use constant-time comparison to prevent timing attacks
        import hmac
        return hmac.compare_digest(expected_signature, received_signature)
    
    def is_ready_for_delivery(self) -> bool:
        """Check if endpoint is ready for webhook delivery."""
        return (
            self.is_active and
            bool(self.endpoint_url.strip()) and
            bool(self.secret_token.strip())
        )
    
    @classmethod
    def create_new(cls, 
                   name: str,
                   endpoint_url: str,
                   created_by_user_id: Optional[UserId] = None,
                   **kwargs) -> "WebhookEndpoint":
        """Create a new webhook endpoint with UUIDv7 compliance.
        
        This factory method ensures all new endpoints use UUIDv7 for better
        database performance and time-ordering.
        
        Args:
            name: Human-readable name for the endpoint
            endpoint_url: The webhook URL to deliver to
            created_by_user_id: User who created this endpoint
            **kwargs: Additional fields (description, custom_headers, etc.)
        """
        return cls(
            name=name,
            endpoint_url=endpoint_url,
            created_by_user_id=created_by_user_id,
            **kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert endpoint to dictionary for serialization (matches database schema)."""
        return {
            "id": str(self.id.value),
            "name": self.name,
            "description": self.description,
            "endpoint_url": self.endpoint_url,
            "http_method": self.http_method,
            "secret_token": self.secret_token,
            "signature_header": self.signature_header,
            "custom_headers": self.custom_headers,
            "timeout_seconds": self.timeout_seconds,
            "follow_redirects": self.follow_redirects,
            "verify_ssl": self.verify_ssl,
            "max_retry_attempts": self.max_retry_attempts,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "retry_backoff_multiplier": float(self.retry_backoff_multiplier),
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_by_user_id": str(self.created_by_user_id.value) if self.created_by_user_id else None,
            "context_id": str(self.context_id) if self.context_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookEndpoint":
        """Create WebhookEndpoint from dictionary representation.
        
        Args:
            data: Dictionary with endpoint data (typically from database)
            
        Returns:
            WebhookEndpoint instance
        """
        from uuid import UUID
        from datetime import datetime
        
        # Convert string IDs back to value objects (UUIDs should be UUIDv7 from database)
        endpoint_id = WebhookEndpointId(UUID(data["id"]))
        created_by_user_id = UserId(UUID(data["created_by_user_id"])) if data.get("created_by_user_id") else None
        context_id = UUID(data["context_id"]) if data.get("context_id") else None
        
        # Parse datetime fields
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])
        last_used_at = datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None
        verified_at = datetime.fromisoformat(data["verified_at"]) if data.get("verified_at") else None
        
        return cls(
            id=endpoint_id,
            name=data["name"],
            description=data.get("description"),
            endpoint_url=data["endpoint_url"],
            http_method=data.get("http_method", "POST"),
            secret_token=data["secret_token"],
            signature_header=data.get("signature_header", "X-Webhook-Signature"),
            custom_headers=data.get("custom_headers", {}),
            timeout_seconds=data.get("timeout_seconds", 30),
            follow_redirects=data.get("follow_redirects", False),
            verify_ssl=data.get("verify_ssl", True),
            max_retry_attempts=data.get("max_retry_attempts", 3),
            retry_backoff_seconds=data.get("retry_backoff_seconds", 5),
            retry_backoff_multiplier=Decimal(str(data.get("retry_backoff_multiplier", "2.0"))),
            is_active=data.get("is_active", True),
            is_verified=data.get("is_verified", False),
            created_by_user_id=created_by_user_id,
            context_id=context_id,
            created_at=created_at,
            updated_at=updated_at,
            last_used_at=last_used_at,
            verified_at=verified_at,
        )