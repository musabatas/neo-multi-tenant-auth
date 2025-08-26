"""Webhook event type entity for neo-commons events feature.

This module defines the WebhookEventType entity that represents
configurable event types for webhook subscriptions.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from ....core.value_objects import WebhookEventTypeId


@dataclass
class WebhookEventType:
    """Webhook event type entity for managing event type configurations.
    
    Represents an event type that can be subscribed to by webhook endpoints.
    Matches the webhook_event_types table structure in both admin and tenant schemas.
    """
    
    # Event identification
    id: WebhookEventTypeId
    event_type: str  # e.g., 'organization.created', 'customer.updated'
    category: str    # e.g., 'organization', 'customer', 'order'
    
    # Event metadata
    display_name: str
    description: Optional[str] = None
    
    # Event configuration
    is_enabled: bool = True
    requires_verification: bool = False  # Some events need verified endpoints
    
    # Payload schema (for documentation/validation)
    payload_schema: Optional[Dict[str, Any]] = None
    example_payload: Optional[Dict[str, Any]] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Post-init validation and normalization."""
        from ..utils.validation import WebhookValidationRules
        
        # Validate event_type format using centralized validation
        try:
            WebhookValidationRules.validate_event_type(self.event_type)
        except ValueError as e:
            raise ValueError(f"Invalid event type: {e}")
        
        # Extract category from event_type if not provided
        if not self.category:
            self.category = self.event_type.split('.')[0]
        
        # Validate category matches event_type prefix
        expected_category = self.event_type.split('.')[0]
        if self.category != expected_category:
            raise ValueError(f"category '{self.category}' doesn't match event_type prefix '{expected_category}'")
        
        # Normalize category to lowercase
        if self.category:
            self.category = self.category.lower()
        
        # Validate display_name is not empty
        if not self.display_name or not self.display_name.strip():
            raise ValueError("display_name cannot be empty")
        
        # Ensure timestamps are timezone-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
    
    def enable(self) -> None:
        """Enable this event type for subscriptions."""
        if not self.is_enabled:
            self.is_enabled = True
            self.updated_at = datetime.now(timezone.utc)
    
    def disable(self) -> None:
        """Disable this event type from new subscriptions."""
        if self.is_enabled:
            self.is_enabled = False
            self.updated_at = datetime.now(timezone.utc)
    
    def require_verification(self) -> None:
        """Require webhook endpoints to be verified to subscribe to this event."""
        if not self.requires_verification:
            self.requires_verification = True
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_verification_requirement(self) -> None:
        """Remove verification requirement for this event type."""
        if self.requires_verification:
            self.requires_verification = False
            self.updated_at = datetime.now(timezone.utc)
    
    def update_schema(self, payload_schema: Optional[Dict[str, Any]], 
                     example_payload: Optional[Dict[str, Any]] = None) -> None:
        """Update the payload schema and example for this event type."""
        self.payload_schema = payload_schema
        if example_payload is not None:
            self.example_payload = example_payload
        self.updated_at = datetime.now(timezone.utc)
    
    def get_event_category(self) -> str:
        """Get the event category (same as category field)."""
        return self.category
    
    def get_event_action(self) -> str:
        """Get the event action (part after the dot in event_type)."""
        parts = self.event_type.split('.', 1)
        return parts[1] if len(parts) > 1 else ""
    
    def is_subscription_allowed(self, endpoint_is_verified: bool) -> bool:
        """Check if subscription is allowed based on verification requirements."""
        if not self.is_enabled:
            return False
        
        if self.requires_verification and not endpoint_is_verified:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event type to dictionary representation."""
        return {
            "id": str(self.id.value),
            "event_type": self.event_type,
            "category": self.category,
            "display_name": self.display_name,
            "description": self.description,
            "is_enabled": self.is_enabled,
            "requires_verification": self.requires_verification,
            "payload_schema": self.payload_schema,
            "example_payload": self.example_payload,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebhookEventType':
        """Create WebhookEventType from dictionary representation."""
        from uuid import UUID
        from datetime import datetime
        
        # Convert string ID back to value object
        event_type_id = WebhookEventTypeId(UUID(data["id"]))
        
        # Parse datetime fields
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])
        
        return cls(
            id=event_type_id,
            event_type=data["event_type"],
            category=data["category"],
            display_name=data["display_name"],
            description=data.get("description"),
            is_enabled=data.get("is_enabled", True),
            requires_verification=data.get("requires_verification", False),
            payload_schema=data.get("payload_schema"),
            example_payload=data.get("example_payload"),
            created_at=created_at,
            updated_at=updated_at,
        )