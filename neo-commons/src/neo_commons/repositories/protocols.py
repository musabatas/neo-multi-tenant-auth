"""
Repository Protocol Definitions

Protocol interfaces for repository layer components including schema providers,
connection management, and specialized repository capabilities.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable, TypeVar, Generic, Tuple
from abc import ABC

T = TypeVar('T')
CreateT = TypeVar('CreateT')
UpdateT = TypeVar('UpdateT')


@runtime_checkable
class SchemaProvider(Protocol):
    """Protocol for providing dynamic schema configuration."""
    
    def get_schema(self, context: Optional[str] = None) -> str:
        """
        Get schema name based on context.
        
        Args:
            context: Optional context identifier (tenant_id, region, etc.)
            
        Returns:
            Schema name to use for database operations
        """
        ...
    
    def get_tenant_schema(self, tenant_id: str) -> str:
        """
        Get schema name for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant-specific schema name
        """
        ...
    
    def get_admin_schema(self) -> str:
        """Get admin schema name."""
        ...
    
    def get_platform_schema(self) -> str:
        """Get platform common schema name."""
        ...


@runtime_checkable
class ConnectionProvider(Protocol):
    """Protocol for providing database connections."""
    
    async def get_connection(self, context: Optional[str] = None):
        """
        Get database connection based on context.
        
        Args:
            context: Optional context for connection selection
            
        Returns:
            Database connection or pool
        """
        ...
    
    async def health_check(self) -> bool:
        """Check if connection is healthy."""
        ...


@runtime_checkable
class RepositoryProtocol(Protocol[T]):
    """Protocol for base repository operations."""
    
    async def get_by_id(self, id: str, **kwargs) -> Optional[T]:
        """Get entity by ID."""
        ...
    
    async def create(self, data: Dict[str, Any], **kwargs) -> T:
        """Create new entity."""
        ...
    
    async def update(self, id: str, data: Dict[str, Any], **kwargs) -> T:
        """Update existing entity."""
        ...
    
    async def delete(self, id: str, **kwargs) -> bool:
        """Delete entity by ID."""
        ...
    
    async def list_with_pagination(
        self, 
        page: int, 
        page_size: int, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Tuple[List[T], int]:
        """List entities with pagination."""
        ...


@runtime_checkable
class CacheableRepositoryProtocol(Protocol):
    """Protocol for repositories with caching capabilities."""
    
    async def get_cached(self, key: str, ttl: int = 300) -> Optional[Any]:
        """Get cached value."""
        ...
    
    async def set_cached(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set cached value."""
        ...
    
    async def invalidate_cache(self, pattern: str) -> None:
        """Invalidate cache by pattern."""
        ...


@runtime_checkable
class AuditableRepositoryProtocol(Protocol):
    """Protocol for repositories with audit trail capabilities."""
    
    async def create_audit_log(
        self, 
        entity_id: str, 
        action: str, 
        user_id: str,
        changes: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create audit log entry."""
        ...
    
    async def get_audit_trail(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get audit trail for entity."""
        ...


@runtime_checkable
class TenantAwareRepositoryProtocol(Protocol):
    """Protocol for repositories with tenant isolation."""
    
    def set_tenant_context(self, tenant_id: str) -> None:
        """Set tenant context for operations."""
        ...
    
    def get_tenant_context(self) -> Optional[str]:
        """Get current tenant context."""
        ...
    
    async def list_by_tenant(
        self, 
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[Any], int]:
        """List entities scoped to specific tenant."""
        ...


@runtime_checkable
class CRUDRepositoryProtocol(RepositoryProtocol[T], Protocol[T, CreateT, UpdateT]):
    """Extended CRUD repository protocol with typed create/update operations."""
    
    async def create_from_schema(self, data: CreateT, **kwargs) -> T:
        """Create entity from typed schema."""
        ...
    
    async def update_from_schema(self, id: str, data: UpdateT, **kwargs) -> T:
        """Update entity from typed schema."""
        ...
    
    async def bulk_create(self, data_list: List[CreateT], **kwargs) -> List[T]:
        """Create multiple entities."""
        ...
    
    async def bulk_update(self, updates: List[Tuple[str, UpdateT]], **kwargs) -> List[T]:
        """Update multiple entities."""
        ...


@runtime_checkable
class FilterableRepositoryProtocol(Protocol):
    """Protocol for repositories with advanced filtering capabilities."""
    
    def build_where_clause(
        self, 
        conditions: Dict[str, Any], 
        param_offset: int = 0
    ) -> Tuple[str, List[Any], int]:
        """Build WHERE clause from conditions."""
        ...
    
    def build_order_clause(self, sort_by: Optional[str] = None, sort_order: str = "ASC") -> str:
        """Build ORDER BY clause."""
        ...
    
    async def count_with_filters(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with filters."""
        ...
    
    async def search(
        self, 
        query: str, 
        fields: List[str],
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Any], int]:
        """Full-text search across specified fields."""
        ...