"""
NeoAdminApi Base Repository - Service Wrapper for neo-commons

This module provides backward-compatible service wrappers that use the enhanced
neo-commons BaseRepository with dynamic schema configuration while maintaining
existing API compatibility.
"""

from typing import Optional, List, Dict, Any, TypeVar, Generic, Tuple
from abc import ABC, abstractmethod
import logging

# Import from neo-commons for the enhanced implementation
from neo_commons import BaseRepository as NeoBaseRepository
from neo_commons.protocols import SchemaProvider
from neo_commons.models.base import PaginationMetadata

from src.common.database.connection import get_database
from src.common.models import PaginationParams

T = TypeVar('T')

logger = logging.getLogger(__name__)


class AdminSchemaProvider:
    """Schema provider specific to NeoAdminApi with admin-focused defaults."""
    
    def __init__(self):
        self.admin_schema = "admin"
        self.platform_schema = "platform_common"
    
    def get_schema(self, context: Optional[str] = None) -> str:
        """Always returns admin schema for NeoAdminApi operations."""
        return self.admin_schema
    
    def get_tenant_schema(self, tenant_id: str) -> str:
        """Get tenant schema - for future multi-tenant operations."""
        return f"tenant_{tenant_id}"
    
    def get_admin_schema(self) -> str:
        """Get admin schema."""
        return self.admin_schema
    
    def get_platform_schema(self) -> str:
        """Get platform common schema."""
        return self.platform_schema


class BaseRepository(NeoBaseRepository[T]):
    """
    Service wrapper for neo-commons BaseRepository with NeoAdminApi defaults.
    
    This class maintains backward compatibility while using the enhanced
    neo-commons BaseRepository with dynamic schema configuration.
    
    Key improvements:
    - Dynamic schema configuration (no more hardcoded 'admin')
    - Protocol-based dependency injection
    - Enhanced pagination and filtering
    - Type-safe operations
    """
    
    def __init__(self, table_name: str, schema: str = "admin"):
        """
        Initialize NeoAdminApi repository with service-specific defaults.
        
        Args:
            table_name: The database table name
            schema: The database schema (default: admin) - now configurable!
        """
        # Create service-specific schema provider
        schema_provider = AdminSchemaProvider()
        
        # Override default schema if specified
        if schema != "admin":
            schema_provider.admin_schema = schema
        
        # Import connection provider for neo-commons integration
        from src.common.database.connection_provider import neo_admin_connection_provider
        
        # Initialize enhanced neo-commons BaseRepository
        super().__init__(
            table_name=table_name,
            schema_provider=schema_provider,
            connection_provider=neo_admin_connection_provider,
            default_schema=schema
        )
        
        # Maintain backward compatibility properties
        self.db = get_database()
        self.schema = schema
        self.full_table_name = f"{schema}.{table_name}"
    
    # Backward compatibility methods that delegate to neo-commons implementation
    
    def build_where_clause(
        self,
        conditions: Dict[str, Any],
        param_offset: int = 0
    ) -> Tuple[str, List[Any], int]:
        """
        Build WHERE clause - delegates to enhanced neo-commons implementation.
        
        Args:
            conditions: Dictionary of field names and values
            param_offset: Starting parameter number for placeholders
            
        Returns:
            Tuple of (where_clause, parameters, next_param_offset)
        """
        return super().build_where_clause(conditions, param_offset)
    
    async def count_with_filters(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        additional_where: Optional[str] = None
    ) -> int:
        """
        Count records with filters - enhanced version with additional WHERE support.
        
        Args:
            filters: Filter conditions dictionary
            additional_where: Additional WHERE clause
            
        Returns:
            Count of matching records
        """
        # Use neo-commons implementation as base
        base_count = await super().count_with_filters(filters)
        
        # If additional_where provided, need custom query
        if additional_where:
            table_name = self.get_full_table_name()
            
            if filters:
                where_clause, params, _ = self.build_where_clause(filters)
                where_clause = f"({where_clause}) AND ({additional_where})"
            else:
                where_clause = additional_where
                params = []
            
            query = f"SELECT COUNT(*) FROM {table_name} WHERE {where_clause}"
            db = await self.get_connection()
            result = await db.fetchval(query, *params)
            return result or 0
        
        return base_count
    
    async def paginated_list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        select_columns: Optional[str] = None,
        additional_joins: Optional[str] = None,
        additional_where: Optional[str] = None,
        order_by: str = "created_at DESC"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Legacy paginated list method - converts to neo-commons format.
        
        Args:
            pagination: Legacy pagination parameters
            filters: Filter conditions
            select_columns: Columns to select
            additional_joins: Additional JOIN clauses
            additional_where: Additional WHERE clause
            order_by: ORDER BY clause
            
        Returns:
            Tuple of (records, total_count)
        """
        # Parse order_by clause
        sort_by = None
        sort_order = "ASC"
        
        if order_by:
            parts = order_by.split()
            if len(parts) >= 1:
                sort_by = parts[0]
            if len(parts) >= 2:
                sort_order = parts[1]
        
        # Use enhanced neo-commons paginated_list
        select_fields = select_columns or "*"
        
        items, pagination_meta = await super().paginated_list(
            select_fields=select_fields,
            page=pagination.page,
            page_size=pagination.limit,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order,
            additional_joins=additional_joins or ""
        )
        
        return items, pagination_meta.total_items
    
    async def get_by_id(
        self,
        record_id: str,
        select_columns: Optional[str] = None,
        additional_joins: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get record by ID - enhanced version with JOIN support.
        
        Args:
            record_id: The record ID
            select_columns: Columns to select
            additional_joins: Additional JOIN clauses
            
        Returns:
            Record as dictionary or None if not found
        """
        select_fields = select_columns or "*"
        
        if additional_joins:
            # Custom query for JOIN support
            table_name = self.get_full_table_name()
            
            query = f"""
                SELECT {select_fields}
                FROM {table_name} t
                {additional_joins}
                WHERE t.id = $1 AND t.deleted_at IS NULL
            """
            
            db = await self.get_connection()
            row = await db.fetchrow(query, record_id)
            return dict(row) if row else None
        else:
            # Use enhanced neo-commons implementation
            return await super().get_by_id(record_id, select_fields)
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record. Must be implemented by subclasses."""
        pass
    
    async def soft_delete(self, record_id: str) -> bool:
        """
        Soft delete a record by setting deleted_at.
        
        Args:
            record_id: The record ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Use enhanced neo-commons soft_delete implementation
        return await super().soft_delete(record_id)
    
    async def hard_delete(self, record_id: str) -> bool:
        """
        Hard delete a record permanently.
        
        Args:
            record_id: The record ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Use enhanced neo-commons delete implementation
        return await super().delete(record_id)
    
    async def restore(self, record_id: str) -> bool:
        """
        Restore a soft-deleted record.
        
        Args:
            record_id: The record ID to restore
            
        Returns:
            True if restored, False if not found
        """
        table_name = self.get_full_table_name()
        
        query = f"""
            UPDATE {table_name}
            SET deleted_at = NULL, updated_at = NOW()
            WHERE id = $1 AND deleted_at IS NOT NULL
        """
        
        db = await self.get_connection()
        result = await db.execute(query, record_id)
        return result.split()[-1] == "1"
    
    async def health_check(self) -> bool:
        """Check repository health."""
        return await super().health_check()
    
    # Additional legacy compatibility methods
    
    def get_table_name(self) -> str:
        """Get the full table name including schema."""
        return self.full_table_name
    
    def get_schema_name(self) -> str:
        """Get the current schema name."""
        return self.schema