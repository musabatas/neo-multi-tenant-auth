"""Event Action Subscription repository protocol for data persistence."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from ...domain.entities.event_action_subscription import EventActionSubscription
from ...domain.value_objects.subscription_id import SubscriptionId
from ...domain.value_objects.action_id import ActionId


class EventActionSubscriptionRepositoryProtocol(ABC):
    """Protocol for event action subscription persistence operations."""
    
    @abstractmethod
    async def save(self, subscription: EventActionSubscription, schema: str) -> EventActionSubscription:
        """
        Save a subscription to the specified schema.
        
        Args:
            subscription: Subscription to save
            schema: Database schema name (admin, tenant_xxx, etc.)
            
        Returns:
            Saved subscription with any database-generated fields
        """
        ...
    
    @abstractmethod
    async def get_by_id(self, subscription_id: SubscriptionId, schema: str) -> Optional[EventActionSubscription]:
        """
        Get subscription by ID from the specified schema.
        
        Args:
            subscription_id: Subscription ID to retrieve
            schema: Database schema name
            
        Returns:
            Subscription if found, None otherwise
        """
        ...
    
    @abstractmethod
    async def update(self, subscription: EventActionSubscription, schema: str) -> EventActionSubscription:
        """
        Update an existing subscription in the specified schema.
        
        Args:
            subscription: Subscription with updated values
            schema: Database schema name
            
        Returns:
            Updated subscription
        """
        ...
    
    @abstractmethod
    async def delete(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """
        Delete subscription by ID from the specified schema (hard delete).
        
        Args:
            subscription_id: Subscription ID to delete
            schema: Database schema name
            
        Returns:
            True if subscription was deleted, False if not found
        """
        ...
    
    @abstractmethod
    async def soft_delete(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """
        Soft delete subscription by setting deleted_at timestamp.
        
        Args:
            subscription_id: Subscription ID to soft delete
            schema: Database schema name
            
        Returns:
            True if subscription was soft deleted, False if not found
        """
        ...
    
    @abstractmethod
    async def list_subscriptions(
        self, 
        schema: str,
        limit: int = 50, 
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False
    ) -> List[EventActionSubscription]:
        """
        List subscriptions from the specified schema with optional filtering.
        
        Args:
            schema: Database schema name
            limit: Maximum number of subscriptions to return
            offset: Number of subscriptions to skip
            filters: Optional filters (action_id, is_active, event_pattern, etc.)
            include_deleted: Include soft-deleted subscriptions
            
        Returns:
            List of subscriptions matching criteria
        """
        ...
    
    @abstractmethod
    async def find_by_action_id(
        self, 
        action_id: ActionId, 
        schema: str,
        active_only: bool = True
    ) -> List[EventActionSubscription]:
        """
        Find subscriptions for a specific action.
        
        Args:
            action_id: Action ID to find subscriptions for
            schema: Database schema name
            active_only: If True, only return active subscriptions
            
        Returns:
            List of subscriptions for the action
        """
        ...
    
    @abstractmethod
    async def find_matching_subscriptions(
        self, 
        event_type: str, 
        schema: str,
        tenant_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        source_service: Optional[str] = None,
        active_only: bool = True
    ) -> List[EventActionSubscription]:
        """
        Find subscriptions that match an event type and context.
        
        Args:
            event_type: Event type to match
            schema: Database schema name
            tenant_id: Optional tenant ID for filtering
            organization_id: Optional organization ID for filtering
            source_service: Optional source service for filtering
            active_only: If True, only return active subscriptions
            
        Returns:
            List of matching subscriptions sorted by priority
        """
        ...
    
    @abstractmethod
    async def find_by_event_pattern(
        self, 
        pattern: str, 
        schema: str,
        active_only: bool = True
    ) -> List[EventActionSubscription]:
        """
        Find subscriptions with a specific event pattern.
        
        Args:
            pattern: Event pattern to match
            schema: Database schema name
            active_only: If True, only return active subscriptions
            
        Returns:
            List of subscriptions with matching pattern
        """
        ...
    
    @abstractmethod
    async def find_active_subscriptions(self, schema: str) -> List[EventActionSubscription]:
        """
        Find all active subscriptions in the specified schema.
        
        Args:
            schema: Database schema name
            
        Returns:
            List of active subscriptions
        """
        ...
    
    @abstractmethod
    async def find_subscriptions_by_tenant(
        self, 
        tenant_id: UUID, 
        schema: str,
        active_only: bool = True
    ) -> List[EventActionSubscription]:
        """
        Find subscriptions filtered for a specific tenant.
        
        Args:
            tenant_id: Tenant ID to filter by
            schema: Database schema name
            active_only: If True, only return active subscriptions
            
        Returns:
            List of subscriptions applicable to the tenant
        """
        ...
    
    @abstractmethod
    async def find_subscriptions_by_organization(
        self, 
        organization_id: UUID, 
        schema: str,
        active_only: bool = True
    ) -> List[EventActionSubscription]:
        """
        Find subscriptions filtered for a specific organization.
        
        Args:
            organization_id: Organization ID to filter by
            schema: Database schema name
            active_only: If True, only return active subscriptions
            
        Returns:
            List of subscriptions applicable to the organization
        """
        ...
    
    @abstractmethod
    async def activate_subscription(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """
        Activate a subscription.
        
        Args:
            subscription_id: Subscription ID to activate
            schema: Database schema name
            
        Returns:
            True if activated successfully, False if not found
        """
        ...
    
    @abstractmethod
    async def deactivate_subscription(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """
        Deactivate a subscription.
        
        Args:
            subscription_id: Subscription ID to deactivate
            schema: Database schema name
            
        Returns:
            True if deactivated successfully, False if not found
        """
        ...
    
    @abstractmethod
    async def update_priority(
        self, 
        subscription_id: SubscriptionId, 
        priority: int, 
        schema: str
    ) -> bool:
        """
        Update subscription priority.
        
        Args:
            subscription_id: Subscription ID to update
            priority: New priority value
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if not found
        """
        ...
    
    @abstractmethod
    async def increment_rate_count(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """
        Increment the rate limit counter for a subscription.
        
        Args:
            subscription_id: Subscription ID to update
            schema: Database schema name
            
        Returns:
            True if updated successfully, False if not found
        """
        ...
    
    @abstractmethod
    async def reset_rate_limit_window(self, subscription_id: SubscriptionId, schema: str) -> bool:
        """
        Reset the rate limit window and counter for a subscription.
        
        Args:
            subscription_id: Subscription ID to reset
            schema: Database schema name
            
        Returns:
            True if reset successfully, False if not found
        """
        ...
    
    @abstractmethod
    async def get_subscription_statistics(
        self, 
        schema: str,
        action_id: Optional[ActionId] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get subscription statistics.
        
        Args:
            schema: Database schema name
            action_id: Optional action ID to filter statistics
            start_date: Optional start date for time range
            end_date: Optional end date for time range
            
        Returns:
            Statistics dictionary with counts, patterns, etc.
        """
        ...
    
    @abstractmethod
    async def count_subscriptions(
        self, 
        schema: str, 
        filters: Optional[Dict[str, Any]] = None,
        include_deleted: bool = False
    ) -> int:
        """
        Count subscriptions in the specified schema.
        
        Args:
            schema: Database schema name
            filters: Optional filters
            include_deleted: Include soft-deleted subscriptions
            
        Returns:
            Number of subscriptions matching criteria
        """
        ...
    
    @abstractmethod
    async def cleanup_old_subscriptions(
        self, 
        schema: str,
        older_than_days: int = 365
    ) -> int:
        """
        Clean up old soft-deleted subscriptions.
        
        Args:
            schema: Database schema name
            older_than_days: Delete subscriptions soft-deleted longer than this
            
        Returns:
            Number of subscriptions permanently deleted
        """
        ...