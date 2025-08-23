"""
Protocol interfaces for service layer components.

Protocol-based interfaces for business logic services, CRUD operations,
and service-layer patterns across platform services.
"""
from typing import Protocol, Any, Dict, List, Optional, TypeVar, Generic, Union
from abc import abstractmethod


T = TypeVar('T')
CreateT = TypeVar('CreateT')
UpdateT = TypeVar('UpdateT')


class BaseServiceProtocol(Protocol[T]):
    """Protocol for base service operations."""
    
    def create_pagination_metadata(
        self,
        page: int,
        page_size: int,
        total_items: int
    ) -> Dict[str, Any]:
        """Create pagination metadata from parameters."""
        ...
    
    def validate_pagination_params(
        self,
        page: int,
        page_size: int,
        max_page_size: int = 100
    ) -> tuple[int, int]:
        """Validate and normalize pagination parameters."""
        ...
    
    def handle_not_found(
        self,
        resource_type: str,
        identifier: str
    ) -> None:
        """Handle resource not found scenarios."""
        ...
    
    def handle_validation_error(
        self,
        message: str,
        errors: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """Handle validation error scenarios."""
        ...


class CRUDServiceProtocol(Protocol[T, CreateT, UpdateT]):
    """Protocol for CRUD service operations."""
    
    async def create(self, data: CreateT, **kwargs) -> T:
        """Create a new resource."""
        ...
    
    async def get_by_id(self, id: str, **kwargs) -> Optional[T]:
        """Get resource by ID."""
        ...
    
    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        **kwargs
    ) -> Dict[str, Any]:
        """List resources with pagination and filtering."""
        ...
    
    async def update(self, id: str, data: UpdateT, **kwargs) -> Optional[T]:
        """Update existing resource."""
        ...
    
    async def delete(self, id: str, **kwargs) -> bool:
        """Delete resource by ID."""
        ...
    
    async def exists(self, id: str, **kwargs) -> bool:
        """Check if resource exists."""
        ...


class FilterableServiceProtocol(Protocol[T]):
    """Protocol for services that support filtering operations."""
    
    def get_allowed_filters(self) -> List[str]:
        """Get list of allowed filter fields."""
        ...
    
    def get_allowed_sort_fields(self) -> List[str]:
        """Get list of allowed sort fields."""
        ...
    
    def validate_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and sanitize filter parameters."""
        ...
    
    def validate_sort_params(self, sort_by: str, sort_order: str) -> tuple[str, str]:
        """Validate and normalize sort parameters."""
        ...


class CacheableServiceProtocol(Protocol[T]):
    """Protocol for services that support caching operations."""
    
    def get_cache_key(self, operation: str, **params) -> str:
        """Generate cache key for operation."""
        ...
    
    def get_cache_ttl(self, operation: str) -> int:
        """Get cache TTL for operation."""
        ...
    
    async def invalidate_cache(self, pattern: str) -> None:
        """Invalidate cache entries matching pattern."""
        ...
    
    async def warm_cache(self, **params) -> None:
        """Pre-populate cache with commonly accessed data."""
        ...


class AuditableServiceProtocol(Protocol[T]):
    """Protocol for services that support audit logging."""
    
    async def log_operation(
        self,
        operation: str,
        resource_id: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log operation for audit trail."""
        ...
    
    def get_audit_context(self) -> Dict[str, Any]:
        """Get audit context information."""
        ...


class TenantAwareServiceProtocol(Protocol[T]):
    """Protocol for services that support multi-tenancy."""
    
    def get_tenant_context(self) -> Optional[str]:
        """Get current tenant context."""
        ...
    
    def set_tenant_context(self, tenant_id: str) -> None:
        """Set tenant context for operations."""
        ...
    
    def validate_tenant_access(self, resource_id: str, tenant_id: str) -> bool:
        """Validate tenant has access to resource."""
        ...


class BatchServiceProtocol(Protocol[T]):
    """Protocol for services that support batch operations."""
    
    async def batch_create(self, items: List[CreateT], **kwargs) -> List[T]:
        """Create multiple resources in batch."""
        ...
    
    async def batch_update(
        self,
        updates: List[Dict[str, Any]],
        **kwargs
    ) -> List[T]:
        """Update multiple resources in batch."""
        ...
    
    async def batch_delete(self, ids: List[str], **kwargs) -> int:
        """Delete multiple resources in batch."""
        ...
    
    def get_batch_size_limit(self) -> int:
        """Get maximum batch size allowed."""
        ...