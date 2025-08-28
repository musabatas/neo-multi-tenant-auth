"""
Register webhook request model.

ONLY handles webhook registration API request validation and transformation.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator, HttpUrl

from neo_commons.core.value_objects import TenantId


class WebhookConfigRequest(BaseModel):
    """Webhook configuration details."""
    
    secret: Optional[str] = Field(
        None,
        description="Webhook secret for HMAC verification",
        min_length=16
    )
    
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Additional headers to include in webhook calls"
    )
    
    timeout_seconds: Optional[int] = Field(
        30,
        description="Timeout for webhook calls",
        ge=1,
        le=300
    )
    
    retry_count: Optional[int] = Field(
        3,
        description="Number of retries on failure",
        ge=0,
        le=10
    )
    
    retry_backoff: Optional[str] = Field(
        "exponential",
        description="Retry backoff strategy"
    )
    
    @validator('retry_backoff')
    def validate_retry_backoff(cls, v):
        """Validate retry backoff strategy."""
        valid_strategies = ["linear", "exponential", "fixed"]
        if v not in valid_strategies:
            raise ValueError(f"Retry backoff must be one of: {valid_strategies}")
        return v


class RegisterWebhookRequest(BaseModel):
    """Request model for registering webhook endpoints."""
    
    name: str = Field(
        ...,
        description="Name of the webhook endpoint",
        example="user_events_webhook"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the webhook",
        example="Webhook for user lifecycle events"
    )
    
    url: HttpUrl = Field(
        ...,
        description="Webhook endpoint URL",
        example="https://api.example.com/webhooks/events"
    )
    
    event_types: List[str] = Field(
        ...,
        description="Event types to send to this webhook",
        example=["user.created", "user.updated", "user.deleted"]
    )
    
    tenant_id: str = Field(
        ...,
        description="Tenant identifier",
        example="tenant_123"
    )
    
    configuration: WebhookConfigRequest = Field(
        default_factory=WebhookConfigRequest,
        description="Webhook configuration settings"
    )
    
    enabled: bool = Field(
        default=True,
        description="Whether the webhook is enabled"
    )
    
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Tags for organizing webhooks"
    )
    
    @validator('event_types')
    def validate_event_types(cls, v):
        """Validate event types format."""
        if not v:
            raise ValueError("At least one event type must be specified")
        
        for event_type in v:
            if not event_type or '.' not in event_type:
                raise ValueError("Event types must be in format 'domain.action'")
        return list(set(v))  # Remove duplicates
    
    @validator('name')
    def validate_name(cls, v):
        """Validate webhook name."""
        if not v.strip():
            raise ValueError("Webhook name cannot be empty")
        return v.strip()
    
    @validator('url')
    def validate_url(cls, v):
        """Validate webhook URL."""
        if not str(v).startswith(('http://', 'https://')):
            raise ValueError("Webhook URL must use HTTP or HTTPS")
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags format."""
        if v:
            # Remove empty strings and duplicates
            return list(set(tag.strip() for tag in v if tag.strip()))
        return []
    
    def to_domain(self) -> Dict[str, Any]:
        """Convert to domain representation."""
        return {
            "name": self.name,
            "description": self.description,
            "url": str(self.url),
            "event_types": self.event_types,
            "tenant_id": TenantId(self.tenant_id),
            "configuration": {
                "secret": self.configuration.secret,
                "headers": self.configuration.headers or {},
                "timeout_seconds": self.configuration.timeout_seconds or 30,
                "retry_count": self.configuration.retry_count or 3,
                "retry_backoff": self.configuration.retry_backoff or "exponential",
            },
            "enabled": self.enabled,
            "tags": self.tags or [],
        }
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "name": "user_lifecycle_webhook",
                "description": "Webhook for user lifecycle events",
                "url": "https://api.example.com/webhooks/user-events",
                "event_types": ["user.created", "user.updated", "user.deleted"],
                "tenant_id": "tenant_123",
                "configuration": {
                    "secret": "wh_secret_1234567890abcdef",
                    "headers": {
                        "Authorization": "Bearer token_123",
                        "Content-Type": "application/json"
                    },
                    "timeout_seconds": 30,
                    "retry_count": 3,
                    "retry_backoff": "exponential"
                },
                "enabled": True,
                "tags": ["user-management", "core-events"]
            }
        }