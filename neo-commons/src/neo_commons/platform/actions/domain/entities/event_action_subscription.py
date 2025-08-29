"""Event Action Subscription entity for dynamic event-action mapping."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID
import fnmatch

from ..value_objects.subscription_id import SubscriptionId
from ..value_objects.action_id import ActionId
from ....utils import generate_uuid_v7


@dataclass
class EventActionSubscription:
    """
    Event Action Subscription entity for dynamic event-action mapping.
    
    Represents a subscription that maps events to actions based on patterns and conditions.
    Maps to the admin.event_subscriptions and tenant_template.event_subscriptions database tables.
    """
    
    # Core Identity (immutable after creation)
    id: SubscriptionId
    action_id: ActionId
    
    # Subscription Configuration (mutable for configuration updates)
    event_pattern: str
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Subscription Settings (mutable for operational tuning)
    is_active: bool = True
    priority: int = 0
    
    # Filtering and Routing (mutable for filtering updates)
    tenant_filter: List[UUID] = field(default_factory=list)
    organization_filter: List[UUID] = field(default_factory=list)
    source_service_filter: List[str] = field(default_factory=list)
    
    # Rate Limiting (mutable for rate limit tuning)
    rate_limit_per_minute: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None
    rate_limit_window_start: Optional[datetime] = None
    current_rate_count: int = 0
    
    # Metadata (mutable for operational management)
    name: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[UUID] = None
    
    # Audit Fields (auto-updated)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None
    
    @classmethod
    def create(
        cls,
        action_id: ActionId,
        event_pattern: str,
        conditions: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        priority: int = 0,
        tenant_filter: Optional[List[UUID]] = None,
        organization_filter: Optional[List[UUID]] = None,
        source_service_filter: Optional[List[str]] = None,
        rate_limit_per_minute: Optional[int] = None,
        rate_limit_per_hour: Optional[int] = None,
        created_by: Optional[UUID] = None
    ) -> 'EventActionSubscription':
        """
        Create a new EventActionSubscription.
        
        Args:
            action_id: ID of the action to execute
            event_pattern: Event pattern to match (supports wildcards)
            conditions: Additional filtering conditions
            name: Subscription name for identification
            description: Subscription description
            is_active: Whether subscription is active
            priority: Subscription priority (higher = more priority)
            tenant_filter: Limit to specific tenants
            organization_filter: Limit to specific organizations
            source_service_filter: Limit to specific services
            rate_limit_per_minute: Rate limit per minute
            rate_limit_per_hour: Rate limit per hour
            created_by: User who created this subscription
            
        Returns:
            New EventActionSubscription instance
        """
        return cls(
            id=SubscriptionId.generate(),
            action_id=action_id,
            event_pattern=event_pattern,
            conditions=conditions.copy() if conditions else {},
            name=name,
            description=description,
            is_active=is_active,
            priority=priority,
            tenant_filter=tenant_filter.copy() if tenant_filter else [],
            organization_filter=organization_filter.copy() if organization_filter else [],
            source_service_filter=source_service_filter.copy() if source_service_filter else [],
            rate_limit_per_minute=rate_limit_per_minute,
            rate_limit_per_hour=rate_limit_per_hour,
            created_by=created_by
        )
    
    def matches_event_type(self, event_type: str) -> bool:
        """Check if event type matches the subscription pattern."""
        return fnmatch.fnmatch(event_type, self.event_pattern)
    
    def matches_tenant(self, tenant_id: Optional[UUID]) -> bool:
        """Check if tenant matches the filter."""
        if not self.tenant_filter:
            return True  # No filter means match all
        return tenant_id is not None and tenant_id in self.tenant_filter
    
    def matches_organization(self, organization_id: Optional[UUID]) -> bool:
        """Check if organization matches the filter."""
        if not self.organization_filter:
            return True  # No filter means match all
        return organization_id is not None and organization_id in self.organization_filter
    
    def matches_source_service(self, source_service: Optional[str]) -> bool:
        """Check if source service matches the filter."""
        if not self.source_service_filter:
            return True  # No filter means match all
        return source_service is not None and source_service in self.source_service_filter
    
    def matches_conditions(self, event_data: Dict[str, Any]) -> bool:
        """Check if event data matches the subscription conditions."""
        if not self.conditions:
            return True
        
        # Simple condition matching - can be extended for complex logic
        for key, expected_value in self.conditions.items():
            if key not in event_data:
                return False
            
            actual_value = event_data[key]
            
            # Support for different condition types
            if isinstance(expected_value, dict):
                if "$eq" in expected_value:
                    if actual_value != expected_value["$eq"]:
                        return False
                elif "$ne" in expected_value:
                    if actual_value == expected_value["$ne"]:
                        return False
                elif "$in" in expected_value:
                    if actual_value not in expected_value["$in"]:
                        return False
                elif "$nin" in expected_value:
                    if actual_value in expected_value["$nin"]:
                        return False
                elif "$gt" in expected_value:
                    if not (actual_value > expected_value["$gt"]):
                        return False
                elif "$gte" in expected_value:
                    if not (actual_value >= expected_value["$gte"]):
                        return False
                elif "$lt" in expected_value:
                    if not (actual_value < expected_value["$lt"]):
                        return False
                elif "$lte" in expected_value:
                    if not (actual_value <= expected_value["$lte"]):
                        return False
                elif "$regex" in expected_value:
                    import re
                    if not re.search(expected_value["$regex"], str(actual_value)):
                        return False
            else:
                # Simple equality check
                if actual_value != expected_value:
                    return False
        
        return True
    
    def matches_event(
        self, 
        event_type: str, 
        event_data: Dict[str, Any],
        tenant_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        source_service: Optional[str] = None
    ) -> bool:
        """Check if event matches all subscription criteria."""
        if not self.is_active:
            return False
        
        return (
            self.matches_event_type(event_type) and
            self.matches_conditions(event_data) and
            self.matches_tenant(tenant_id) and
            self.matches_organization(organization_id) and
            self.matches_source_service(source_service)
        )
    
    def is_rate_limited(self) -> bool:
        """Check if subscription is currently rate limited."""
        now = datetime.now(timezone.utc)
        
        # Check if we need to reset the rate limit window
        if self.rate_limit_window_start is None:
            self.rate_limit_window_start = now
            self.current_rate_count = 0
            return False
        
        # Check minute-based rate limit
        if self.rate_limit_per_minute:
            minute_ago = now.replace(second=0, microsecond=0)
            if self.rate_limit_window_start < minute_ago:
                # Reset minute window
                self.rate_limit_window_start = minute_ago
                self.current_rate_count = 0
            
            if self.current_rate_count >= self.rate_limit_per_minute:
                return True
        
        # Check hour-based rate limit
        if self.rate_limit_per_hour:
            hour_ago = now.replace(minute=0, second=0, microsecond=0)
            if self.rate_limit_window_start < hour_ago:
                # Reset hour window
                self.rate_limit_window_start = hour_ago
                self.current_rate_count = 0
            
            if self.current_rate_count >= self.rate_limit_per_hour:
                return True
        
        return False
    
    def increment_rate_count(self) -> None:
        """Increment the rate limit counter."""
        self.current_rate_count += 1
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate the subscription."""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate the subscription."""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def update_priority(self, priority: int) -> None:
        """Update subscription priority."""
        self.priority = priority
        self.updated_at = datetime.now(timezone.utc)
    
    def update_pattern(self, event_pattern: str) -> None:
        """Update event pattern."""
        self.event_pattern = event_pattern
        self.updated_at = datetime.now(timezone.utc)
    
    def update_conditions(self, conditions: Dict[str, Any]) -> None:
        """Update subscription conditions."""
        self.conditions = conditions.copy()
        self.updated_at = datetime.now(timezone.utc)
    
    def add_tenant_filter(self, tenant_id: UUID) -> None:
        """Add tenant to filter list."""
        if tenant_id not in self.tenant_filter:
            self.tenant_filter.append(tenant_id)
            self.updated_at = datetime.now(timezone.utc)
    
    def remove_tenant_filter(self, tenant_id: UUID) -> None:
        """Remove tenant from filter list."""
        if tenant_id in self.tenant_filter:
            self.tenant_filter.remove(tenant_id)
            self.updated_at = datetime.now(timezone.utc)
    
    def soft_delete(self) -> None:
        """Soft delete the subscription."""
        self.deleted_at = datetime.now(timezone.utc)
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary representation."""
        return {
            'id': str(self.id.value),
            'action_id': str(self.action_id.value),
            'event_pattern': self.event_pattern,
            'conditions': self.conditions,
            'is_active': self.is_active,
            'priority': self.priority,
            'tenant_filter': [str(tid) for tid in self.tenant_filter],
            'organization_filter': [str(oid) for oid in self.organization_filter],
            'source_service_filter': self.source_service_filter,
            'rate_limit_per_minute': self.rate_limit_per_minute,
            'rate_limit_per_hour': self.rate_limit_per_hour,
            'rate_limit_window_start': self.rate_limit_window_start.isoformat() if self.rate_limit_window_start else None,
            'current_rate_count': self.current_rate_count,
            'name': self.name,
            'description': self.description,
            'created_by': str(self.created_by) if self.created_by else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }
    
    def __post_init__(self):
        """Validate subscription after initialization."""
        # Validate priority
        if self.priority < 0:
            raise ValueError(f"priority cannot be negative: {self.priority}")
        
        # Validate rate limits
        if self.rate_limit_per_minute is not None and self.rate_limit_per_minute <= 0:
            raise ValueError(f"rate_limit_per_minute must be positive: {self.rate_limit_per_minute}")
        
        if self.rate_limit_per_hour is not None and self.rate_limit_per_hour <= 0:
            raise ValueError(f"rate_limit_per_hour must be positive: {self.rate_limit_per_hour}")
        
        # Validate event pattern
        if not self.event_pattern or not self.event_pattern.strip():
            raise ValueError("event_pattern cannot be empty")
        
        # Validate current rate count
        if self.current_rate_count < 0:
            raise ValueError(f"current_rate_count cannot be negative: {self.current_rate_count}")
    
    def __str__(self) -> str:
        return f"EventActionSubscription(id={self.id}, action_id={self.action_id}, pattern={self.event_pattern})"
    
    def __repr__(self) -> str:
        return (f"EventActionSubscription(id={self.id!r}, action_id={self.action_id!r}, "
                f"event_pattern={self.event_pattern!r}, is_active={self.is_active}, priority={self.priority})")