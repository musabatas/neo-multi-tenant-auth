"""Webhook subscription entity for neo-commons events feature.

This module defines the WebhookSubscription entity that represents
the subscription relationship between webhook endpoints and event types.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from uuid import UUID

from ....core.value_objects import WebhookSubscriptionId, WebhookEndpointId, WebhookEventTypeId


@dataclass
class WebhookSubscription:
    """Webhook subscription entity for managing endpoint-to-event-type subscriptions.
    
    Represents a subscription relationship between a webhook endpoint and an event type,
    including filtering rules and subscription metadata.
    """
    
    # Subscription identification
    id: WebhookSubscriptionId
    endpoint_id: WebhookEndpointId
    event_type_id: WebhookEventTypeId
    
    # Subscription configuration
    event_type: str  # e.g., 'organization.created', 'user.updated'
    event_filters: Dict[str, Any] = field(default_factory=dict)  # Filtering criteria
    is_active: bool = True
    
    # Context information
    context_id: Optional[UUID] = None  # Optional context restriction
    
    # Subscription metadata
    subscription_name: Optional[str] = None
    description: Optional[str] = None
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_triggered_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Post-init validation and normalization."""
        from ..utils.validation import WebhookValidationRules
        
        # Validate event_type format using centralized validation
        try:
            WebhookValidationRules.validate_event_type(self.event_type)
        except ValueError as e:
            raise ValueError(f"Invalid event type in subscription: {e}")
        
        # Validate event_filters if present
        if self.event_filters:
            if not isinstance(self.event_filters, dict):
                raise ValueError("event_filters must be a dictionary")
            
            # Validate filter keys and values
            for key, value in self.event_filters.items():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError(f"Filter key must be a non-empty string: {key}")
                
                # Basic value validation (can be extended)
                if value is None:
                    continue
                elif isinstance(value, (str, int, float, bool)):
                    continue
                elif isinstance(value, (list, dict)):
                    continue  # Allow complex filters
                else:
                    raise ValueError(f"Invalid filter value type for key {key}: {type(value)}")
        
        # Ensure subscription_name is not empty if provided
        if self.subscription_name is not None and not self.subscription_name.strip():
            self.subscription_name = None
        
        # Ensure timestamps are timezone-aware
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
        
        if self.last_triggered_at and self.last_triggered_at.tzinfo is None:
            self.last_triggered_at = self.last_triggered_at.replace(tzinfo=timezone.utc)
    
    def activate(self) -> None:
        """Activate this subscription."""
        if not self.is_active:
            self.is_active = True
            self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate this subscription."""
        if self.is_active:
            self.is_active = False
            self.updated_at = datetime.now(timezone.utc)
    
    def update_last_triggered(self) -> None:
        """Update the last triggered timestamp."""
        self.last_triggered_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_filters(self, event_filters: Dict[str, Any]) -> None:
        """Update the event filters for this subscription."""
        # Validate new filters
        if event_filters and not isinstance(event_filters, dict):
            raise ValueError("event_filters must be a dictionary")
        
        # Validate filter contents (same logic as __post_init__)
        if event_filters:
            for key, value in event_filters.items():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError(f"Filter key must be a non-empty string: {key}")
                
                if value is not None and not isinstance(value, (str, int, float, bool, list, dict)):
                    raise ValueError(f"Invalid filter value type for key {key}: {type(value)}")
        
        self.event_filters = event_filters or {}
        self.updated_at = datetime.now(timezone.utc)
    
    def matches_event(self, event_type: str, event_data: Dict[str, Any], 
                     context_id: Optional[UUID] = None) -> bool:
        """Check if this subscription matches the given event.
        
        Args:
            event_type: The event type to match against
            event_data: The event data to filter against
            context_id: Optional context ID to match
            
        Returns:
            True if the event matches this subscription
        """
        # Check if subscription is active
        if not self.is_active:
            return False
        
        # Check event type match
        if self.event_type != event_type:
            return False
        
        # Check context restriction if specified
        if self.context_id is not None and self.context_id != context_id:
            return False
        
        # Check event filters
        if self.event_filters:
            for filter_key, filter_value in self.event_filters.items():
                # Get the value from event data using dot notation support
                event_value = self._get_nested_value(event_data, filter_key)
                
                # Apply filter logic
                if not self._matches_filter_value(event_value, filter_value):
                    return False
        
        return True
    
    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Any:
        """Get value from nested dictionary using dot notation.
        
        Args:
            data: Dictionary to search in
            key: Key with optional dot notation (e.g., 'user.email')
            
        Returns:
            Value if found, None if not found
        """
        if '.' not in key:
            return data.get(key)
        
        keys = key.split('.')
        current = data
        
        for k in keys:
            if not isinstance(current, dict) or k not in current:
                return None
            current = current[k]
        
        return current
    
    def _matches_filter_value(self, event_value: Any, filter_value: Any) -> bool:
        """Check if event value matches filter value.
        
        Args:
            event_value: Value from event data
            filter_value: Expected value from filter
            
        Returns:
            True if values match according to filter rules
        """
        # Exact match for simple types
        if isinstance(filter_value, (str, int, float, bool)):
            return event_value == filter_value
        
        # List match (event value should be in the list)
        elif isinstance(filter_value, list):
            return event_value in filter_value
        
        # Dictionary match (more complex filtering rules)
        elif isinstance(filter_value, dict):
            # Support for operators like {"$gt": 100}, {"$in": [1, 2, 3]}
            for operator, operand in filter_value.items():
                if operator == "$eq":
                    return event_value == operand
                elif operator == "$ne":
                    return event_value != operand
                elif operator == "$in":
                    return event_value in operand if isinstance(operand, list) else False
                elif operator == "$gt":
                    return event_value > operand if isinstance(event_value, (int, float)) else False
                elif operator == "$gte":
                    return event_value >= operand if isinstance(event_value, (int, float)) else False
                elif operator == "$lt":
                    return event_value < operand if isinstance(event_value, (int, float)) else False
                elif operator == "$lte":
                    return event_value <= operand if isinstance(event_value, (int, float)) else False
                elif operator == "$contains":
                    return operand in event_value if isinstance(event_value, str) else False
                elif operator == "$exists":
                    return (event_value is not None) == operand
                # Add more operators as needed
            
            # If no recognized operators, treat as exact match
            return event_value == filter_value
        
        # Default to exact match
        return event_value == filter_value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary representation."""
        return {
            "id": str(self.id.value),
            "endpoint_id": str(self.endpoint_id.value),
            "event_type_id": str(self.event_type_id.value),
            "event_type": self.event_type,
            "event_filters": self.event_filters,
            "is_active": self.is_active,
            "context_id": str(self.context_id) if self.context_id else None,
            "subscription_name": self.subscription_name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WebhookSubscription':
        """Create WebhookSubscription from dictionary representation."""
        from uuid import UUID
        from datetime import datetime
        
        # Convert string IDs back to value objects
        subscription_id = WebhookSubscriptionId(UUID(data["id"]))
        endpoint_id = WebhookEndpointId(UUID(data["endpoint_id"]))
        event_type_id = WebhookEventTypeId(UUID(data["event_type_id"]))
        
        # Parse datetime fields
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])
        last_triggered_at = datetime.fromisoformat(data["last_triggered_at"]) if data.get("last_triggered_at") else None
        
        return cls(
            id=subscription_id,
            endpoint_id=endpoint_id,
            event_type_id=event_type_id,
            event_type=data["event_type"],
            event_filters=data.get("event_filters", {}),
            is_active=data.get("is_active", True),
            context_id=UUID(data["context_id"]) if data.get("context_id") else None,
            subscription_name=data.get("subscription_name"),
            description=data.get("description"),
            created_at=created_at,
            updated_at=updated_at,
            last_triggered_at=last_triggered_at,
        )