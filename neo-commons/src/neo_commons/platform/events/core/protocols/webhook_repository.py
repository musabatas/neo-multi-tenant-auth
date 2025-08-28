"""Webhook repository protocol for platform events infrastructure.

This module defines the WebhookRepository protocol contract following maximum separation architecture.
Single responsibility: Webhook endpoint and delivery data access operations.

Pure platform infrastructure protocol - used by all business features.
"""

from abc import abstractmethod
from typing import List, Optional, Protocol, runtime_checkable

from ..entities import WebhookEndpoint, WebhookDelivery
from ..value_objects import WebhookEndpointId, WebhookDeliveryId, EventId


@runtime_checkable
class WebhookRepository(Protocol):
    """Webhook repository protocol for webhook endpoint and delivery data access.
    
    This protocol defines the contract for webhook data operations following
    maximum separation architecture. Single responsibility: manage webhook
    endpoints, deliveries, subscriptions, and delivery tracking.
    
    Supports:
    - Webhook endpoint management
    - Delivery tracking and history
    - Subscription management
    - Health status monitoring
    """
    
    # Webhook endpoint operations
    @abstractmethod
    async def get_endpoint_by_id(self, endpoint_id: WebhookEndpointId) -> Optional[WebhookEndpoint]:
        """Retrieve a webhook endpoint by ID.
        
        Args:
            endpoint_id: The webhook endpoint ID
            
        Returns:
            WebhookEndpoint if found, None otherwise
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    async def save_endpoint(self, endpoint: WebhookEndpoint) -> WebhookEndpoint:
        """Save a webhook endpoint.
        
        Args:
            endpoint: The webhook endpoint to save
            
        Returns:
            The saved webhook endpoint
            
        Raises:
            RepositoryError: If save operation fails
        """
        pass
    
    @abstractmethod
    async def list_endpoints_by_event_type(self, event_type: str) -> List[WebhookEndpoint]:
        """List webhook endpoints subscribed to an event type.
        
        Args:
            event_type: The event type to filter by
            
        Returns:
            List of webhook endpoints subscribed to the event type
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    # Webhook delivery operations
    @abstractmethod
    async def get_delivery_by_id(self, delivery_id: WebhookDeliveryId) -> Optional[WebhookDelivery]:
        """Retrieve a webhook delivery by ID.
        
        Args:
            delivery_id: The webhook delivery ID
            
        Returns:
            WebhookDelivery if found, None otherwise
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    async def save_delivery(self, delivery: WebhookDelivery) -> WebhookDelivery:
        """Save a webhook delivery.
        
        Args:
            delivery: The webhook delivery to save
            
        Returns:
            The saved webhook delivery
            
        Raises:
            RepositoryError: If save operation fails
        """
        pass
    
    @abstractmethod
    async def list_deliveries_by_event(self, event_id: EventId) -> List[WebhookDelivery]:
        """List webhook deliveries for an event.
        
        Args:
            event_id: The event ID
            
        Returns:
            List of webhook deliveries for the event
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    async def list_deliveries_by_endpoint(
        self, 
        endpoint_id: WebhookEndpointId,
        limit: int = 100,
        offset: int = 0
    ) -> List[WebhookDelivery]:
        """List webhook deliveries for an endpoint.
        
        Args:
            endpoint_id: The webhook endpoint ID
            limit: Maximum number of deliveries to return
            offset: Number of deliveries to skip
            
        Returns:
            List of webhook deliveries for the endpoint
            
        Raises:
            RepositoryError: If data access fails
        """
        pass
    
    @abstractmethod
    async def count_consecutive_failures(self, endpoint_id: WebhookEndpointId) -> int:
        """Count consecutive delivery failures for an endpoint.
        
        Args:
            endpoint_id: The webhook endpoint ID
            
        Returns:
            Number of consecutive failures
            
        Raises:
            RepositoryError: If data access fails
        """
        pass