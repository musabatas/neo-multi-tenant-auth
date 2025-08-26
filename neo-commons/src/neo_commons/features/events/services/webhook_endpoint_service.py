"""Webhook endpoint service for endpoint management operations.

Handles webhook endpoint creation, updates, validation, and status management.
Follows single responsibility principle for endpoint operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from uuid import UUID

from ....core.value_objects import WebhookEndpointId, UserId
from ....core.exceptions import EntityNotFoundError, EntityAlreadyExistsError, ValidationError
from ....utils import generate_uuid_v7

from ..entities.webhook_endpoint import WebhookEndpoint
from ..entities.protocols import WebhookEndpointRepository
from ..utils.validation import WebhookValidationRules
from ..utils.error_handling import handle_endpoint_error

logger = logging.getLogger(__name__)


class WebhookEndpointService:
    """Service for webhook endpoint operations.
    
    Handles endpoint creation, updates, validation, and status management
    with proper validation and error handling.
    """
    
    def __init__(self, repository: WebhookEndpointRepository):
        """Initialize with repository dependency.
        
        Args:
            repository: Webhook endpoint repository implementation
        """
        self._repository = repository
    
    async def create_endpoint(
        self,
        name: str,
        endpoint_url: str,
        context_id: UUID,
        description: Optional[str] = None,
        secret_token: Optional[str] = None,
        is_active: bool = True,
        headers: Optional[Dict[str, str]] = None,
        http_method: str = "POST",
        timeout_seconds: int = 30,
        is_verified: bool = False
    ) -> WebhookEndpoint:
        """Create a new webhook endpoint.
        
        Args:
            name: Endpoint name
            endpoint_url: Webhook URL
            context_id: Context ID (organization, tenant, etc.)
            description: Optional description
            secret_token: Optional secret for HMAC signing
            is_active: Whether endpoint is active
            headers: Optional custom headers
            http_method: HTTP method (default: POST)
            timeout_seconds: Request timeout in seconds
            is_verified: Whether endpoint is verified
            
        Returns:
            Created webhook endpoint
        """
        try:
            # Validate inputs
            validated_name = WebhookValidationRules.validate_endpoint_name(name)
            validated_url = WebhookValidationRules.validate_webhook_url(endpoint_url)
            validated_method = WebhookValidationRules.validate_http_method(http_method)
            
            if secret_token:
                WebhookValidationRules.validate_secret_token(secret_token)
            
            if headers:
                WebhookValidationRules.validate_headers(headers)
            
            # Check for duplicate URLs in same context
            existing_endpoints = await self._repository.get_by_context(context_id, active_only=False)
            for existing in existing_endpoints:
                if existing.endpoint_url == validated_url:
                    raise EntityAlreadyExistsError(
                        "WebhookEndpoint", 
                        f"URL already exists in context: {validated_url}"
                    )
            
            # Create endpoint entity
            endpoint_id = WebhookEndpointId(value=generate_uuid_v7())
            
            endpoint = WebhookEndpoint(
                id=endpoint_id,
                name=validated_name,
                description=description,
                endpoint_url=validated_url,
                context_id=context_id,
                secret_token=secret_token,
                is_active=is_active,
                headers=headers,
                http_method=validated_method,
                timeout_seconds=timeout_seconds,
                is_verified=is_verified,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            # Save endpoint
            saved_endpoint = await self._repository.save(endpoint)
            
            logger.info(f"Created webhook endpoint {endpoint.id}: {validated_name} -> {validated_url}")
            return saved_endpoint
            
        except Exception as e:
            handle_endpoint_error("create_endpoint", None, e, {
                "name": name,
                "endpoint_url": endpoint_url,
                "context_id": str(context_id)
            })
            raise
    
    async def update_endpoint(
        self,
        endpoint_id: WebhookEndpointId,
        name: Optional[str] = None,
        description: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        secret_token: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        http_method: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> WebhookEndpoint:
        """Update a webhook endpoint.
        
        Args:
            endpoint_id: ID of endpoint to update
            name: Optional new name
            description: Optional new description
            endpoint_url: Optional new URL
            secret_token: Optional new secret token
            headers: Optional new headers
            http_method: Optional new HTTP method
            timeout_seconds: Optional new timeout
            
        Returns:
            Updated webhook endpoint
        """
        try:
            # Get existing endpoint
            endpoint = await self._repository.get_by_id(endpoint_id)
            if not endpoint:
                raise EntityNotFoundError("WebhookEndpoint", str(endpoint_id.value))
            
            # Validate and update fields
            if name is not None:
                endpoint.name = WebhookValidationRules.validate_endpoint_name(name)
            
            if description is not None:
                endpoint.description = description
            
            if endpoint_url is not None:
                validated_url = WebhookValidationRules.validate_webhook_url(endpoint_url)
                
                # Check for duplicates in same context (excluding current endpoint)
                existing_endpoints = await self._repository.get_by_context(endpoint.context_id, active_only=False)
                for existing in existing_endpoints:
                    if existing.id != endpoint.id and existing.endpoint_url == validated_url:
                        raise EntityAlreadyExistsError(
                            "WebhookEndpoint", 
                            f"URL already exists in context: {validated_url}"
                        )
                
                endpoint.endpoint_url = validated_url
                endpoint.is_verified = False  # Reset verification on URL change
            
            if secret_token is not None:
                if secret_token:  # Only validate if not empty
                    WebhookValidationRules.validate_secret_token(secret_token)
                endpoint.secret_token = secret_token
            
            if headers is not None:
                if headers:  # Only validate if not empty
                    WebhookValidationRules.validate_headers(headers)
                endpoint.headers = headers
            
            if http_method is not None:
                endpoint.http_method = WebhookValidationRules.validate_http_method(http_method)
            
            if timeout_seconds is not None:
                if timeout_seconds < 1 or timeout_seconds > 300:
                    raise ValidationError("Timeout must be between 1 and 300 seconds")
                endpoint.timeout_seconds = timeout_seconds
            
            # Update timestamp
            endpoint.updated_at = datetime.now(timezone.utc)
            
            # Save updated endpoint
            updated_endpoint = await self._repository.update(endpoint)
            
            logger.info(f"Updated webhook endpoint {endpoint_id}")
            return updated_endpoint
            
        except Exception as e:
            handle_endpoint_error("update_endpoint", endpoint_id, e, {})
            raise
    
    async def delete_endpoint(self, endpoint_id: WebhookEndpointId) -> bool:
        """Delete a webhook endpoint.
        
        Args:
            endpoint_id: ID of endpoint to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            result = await self._repository.delete(endpoint_id)
            
            if result:
                logger.info(f"Deleted webhook endpoint {endpoint_id}")
            else:
                logger.warning(f"Webhook endpoint {endpoint_id} not found for deletion")
            
            return result
            
        except Exception as e:
            handle_endpoint_error("delete_endpoint", endpoint_id, e, {})
            raise
    
    async def activate_endpoint(self, endpoint_id: WebhookEndpointId) -> WebhookEndpoint:
        """Activate a webhook endpoint.
        
        Args:
            endpoint_id: ID of endpoint to activate
            
        Returns:
            Updated webhook endpoint
        """
        try:
            endpoint = await self._repository.get_by_id(endpoint_id)
            if not endpoint:
                raise EntityNotFoundError("WebhookEndpoint", str(endpoint_id.value))
            
            if not endpoint.is_active:
                endpoint.is_active = True
                endpoint.updated_at = datetime.now(timezone.utc)
                endpoint = await self._repository.update(endpoint)
                logger.info(f"Activated webhook endpoint {endpoint_id}")
            
            return endpoint
            
        except Exception as e:
            handle_endpoint_error("activate_endpoint", endpoint_id, e, {})
            raise
    
    async def deactivate_endpoint(self, endpoint_id: WebhookEndpointId) -> WebhookEndpoint:
        """Deactivate a webhook endpoint.
        
        Args:
            endpoint_id: ID of endpoint to deactivate
            
        Returns:
            Updated webhook endpoint
        """
        try:
            endpoint = await self._repository.get_by_id(endpoint_id)
            if not endpoint:
                raise EntityNotFoundError("WebhookEndpoint", str(endpoint_id.value))
            
            if endpoint.is_active:
                endpoint.is_active = False
                endpoint.updated_at = datetime.now(timezone.utc)
                endpoint = await self._repository.update(endpoint)
                logger.info(f"Deactivated webhook endpoint {endpoint_id}")
            
            return endpoint
            
        except Exception as e:
            handle_endpoint_error("deactivate_endpoint", endpoint_id, e, {})
            raise
    
    async def verify_endpoint(self, endpoint_id: WebhookEndpointId) -> WebhookEndpoint:
        """Mark a webhook endpoint as verified.
        
        Args:
            endpoint_id: ID of endpoint to verify
            
        Returns:
            Updated webhook endpoint
        """
        try:
            endpoint = await self._repository.get_by_id(endpoint_id)
            if not endpoint:
                raise EntityNotFoundError("WebhookEndpoint", str(endpoint_id.value))
            
            if not endpoint.is_verified:
                endpoint.is_verified = True
                endpoint.updated_at = datetime.now(timezone.utc)
                endpoint = await self._repository.update(endpoint)
                logger.info(f"Verified webhook endpoint {endpoint_id}")
            
            return endpoint
            
        except Exception as e:
            handle_endpoint_error("verify_endpoint", endpoint_id, e, {})
            raise
    
    async def update_last_used(self, endpoint_id: WebhookEndpointId) -> bool:
        """Update the last used timestamp for an endpoint.
        
        Args:
            endpoint_id: ID of endpoint to update
            
        Returns:
            True if updated successfully
        """
        try:
            result = await self._repository.update_last_used(endpoint_id)
            
            if result:
                logger.debug(f"Updated last used timestamp for endpoint {endpoint_id}")
            
            return result
            
        except Exception as e:
            handle_endpoint_error("update_last_used", endpoint_id, e, {})
            raise
    
    async def get_endpoints_by_context(
        self, 
        context_id: UUID, 
        active_only: bool = True
    ) -> List[WebhookEndpoint]:
        """Get webhook endpoints by context ID.
        
        Args:
            context_id: Context ID to filter by
            active_only: Whether to return only active endpoints
            
        Returns:
            List of webhook endpoints
        """
        try:
            return await self._repository.get_by_context(context_id, active_only)
            
        except Exception as e:
            handle_endpoint_error("get_endpoints_by_context", None, e, {
                "context_id": str(context_id),
                "active_only": active_only
            })
            raise
    
    async def get_active_endpoints(self) -> List[WebhookEndpoint]:
        """Get all active webhook endpoints.
        
        Returns:
            List of active webhook endpoints
        """
        try:
            return await self._repository.get_active_endpoints()
            
        except Exception as e:
            handle_endpoint_error("get_active_endpoints", None, e, {})
            raise