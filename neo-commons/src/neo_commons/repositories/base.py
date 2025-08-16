"""
Enhanced Base Repository with Dynamic Schema Configuration

This module provides a schema-configurable base repository that eliminates
hardcoded schema references and supports dynamic configuration through
protocol-based dependency injection.
"""

from typing import Optional, List, Dict, Any, TypeVar, Generic, Tuple, Union
from abc import ABC, abstractmethod
import logging

from ..database.connection import DatabaseManager
from ..models.base import PaginationParams, PaginationMetadata
from ..database.utils import process_database_record
from .protocols import SchemaProvider, ConnectionProvider

T = TypeVar('T')

logger = logging.getLogger(__name__)


class DefaultSchemaProvider:
    """Default schema provider with configurable defaults."""
    
    def __init__(
        self, 
        admin_schema: str = "admin",
        platform_schema: str = "platform_common",
        tenant_schema_pattern: str = "tenant_{tenant_id}"
    ):
        self.admin_schema = admin_schema
        self.platform_schema = platform_schema  
        self.tenant_schema_pattern = tenant_schema_pattern
    
    def get_schema(self, context: Optional[str] = None) -> str:
        """Get schema based on context."""
        if context is None:
            return self.admin_schema
        
        if context.startswith("tenant_"):
            tenant_id = context[7:]  # Remove 'tenant_' prefix
            return self.get_tenant_schema(tenant_id)
        
        return context
    
    def get_tenant_schema(self, tenant_id: str) -> str:
        """Get tenant-specific schema."""
        return self.tenant_schema_pattern.format(tenant_id=tenant_id)
    
    def get_admin_schema(self) -> str:
        """Get admin schema."""
        return self.admin_schema
    
    def get_platform_schema(self) -> str:
        """Get platform common schema."""
        return self.platform_schema


class BaseRepository(ABC, Generic[T]):
    """
    Enhanced base repository with dynamic schema configuration.
    
    This class eliminates hardcoded schema references and provides:
    - Dynamic schema configuration through SchemaProvider protocol
    - Connection management through ConnectionProvider protocol
    - Common database operation patterns
    - Pagination and filtering utilities
    - Type-safe operations with generics
    """
    
    def __init__(
        self,
        table_name: str,
        schema_provider: Optional[SchemaProvider] = None,
        connection_provider: Optional[ConnectionProvider] = None,
        default_schema: Optional[str] = None
    ):
        """
        Initialize base repository with configurable schema.
        
        Args:
            table_name: The database table name
            schema_provider: Provider for dynamic schema configuration
            connection_provider: Provider for database connections
            default_schema: Default schema if no provider specified
        """
        self.table_name = table_name
        self.schema_provider = schema_provider or DefaultSchemaProvider()
        self.connection_provider = connection_provider
        self.default_schema = default_schema or "admin"
        
        # Current context for operations
        self._current_context: Optional[str] = None
        self._current_tenant_id: Optional[str] = None
    
    def set_context(self, context: str) -> None:
        """Set operation context for schema resolution."""
        self._current_context = context
    
    def set_tenant_context(self, tenant_id: str) -> None:
        """Set tenant context for multi-tenant operations."""
        self._current_tenant_id = tenant_id
        self._current_context = f"tenant_{tenant_id}"
    
    def get_current_schema(self) -> str:
        """Get current schema based on context."""
        if self._current_context:
            return self.schema_provider.get_schema(self._current_context)
        return self.schema_provider.get_schema()
    
    def get_full_table_name(self, schema: Optional[str] = None) -> str:
        """Get fully qualified table name."""
        effective_schema = schema or self.get_current_schema()
        return f"{effective_schema}.{self.table_name}"
    
    async def get_connection(self):
        """Get database connection."""
        if self.connection_provider:
            return await self.connection_provider.get_connection(self._current_context)
        
        # Fallback to default database manager
        return DatabaseManager()
    
    def build_where_clause(
        self,
        conditions: Dict[str, Any],
        param_offset: int = 0
    ) -> Tuple[str, List[Any], int]:
        """
        Build WHERE clause from conditions dictionary.
        
        Args:
            conditions: Dictionary of field names and values
            param_offset: Starting parameter number for placeholders
            
        Returns:
            Tuple of (where_clause, parameters, next_param_offset)
        """
        if not conditions:
            return "1=1", [], param_offset
        
        where_parts = []
        params = []
        param_count = param_offset
        
        for field, value in conditions.items():
            if value is None:
                continue
                
            param_count += 1
            
            # Handle different condition types
            if field.endswith('__ilike'):
                actual_field = field[:-7]  # Remove '__ilike'
                where_parts.append(f"{actual_field} ILIKE ${param_count}")
                params.append(f"%{value}%")
            elif field.endswith('__in'):
                actual_field = field[:-4]  # Remove '__in'
                where_parts.append(f"{actual_field} = ANY(${param_count})")
                params.append(value)
            elif field.endswith('__gte'):
                actual_field = field[:-5]  # Remove '__gte'
                where_parts.append(f"{actual_field} >= ${param_count}")
                params.append(value)
            elif field.endswith('__lte'):
                actual_field = field[:-5]  # Remove '__lte'
                where_parts.append(f"{actual_field} <= ${param_count}")
                params.append(value)
            elif field.endswith('__ne'):
                actual_field = field[:-4]  # Remove '__ne'
                where_parts.append(f"{actual_field} != ${param_count}")
                params.append(value)
            else:
                where_parts.append(f"{field} = ${param_count}")
                params.append(value)
        
        return " AND ".join(where_parts), params, param_count
    
    def build_order_clause(
        self, 
        sort_by: Optional[str] = None, 
        sort_order: str = "ASC"
    ) -> str:
        """Build ORDER BY clause."""
        if not sort_by:
            return "ORDER BY created_at DESC"
        
        # Validate sort order
        order = "DESC" if sort_order.upper() == "DESC" else "ASC"
        
        # Simple field name validation (prevent SQL injection)
        if not sort_by.replace('_', '').replace('.', '').isalnum():
            raise ValueError(f"Invalid sort field: {sort_by}")
        
        return f"ORDER BY {sort_by} {order}"
    
    async def count_with_filters(
        self, 
        filters: Optional[Dict[str, Any]] = None,
        schema: Optional[str] = None
    ) -> int:
        """Count records with optional filters."""
        table_name = self.get_full_table_name(schema)
        
        base_query = f"SELECT COUNT(*) FROM {table_name}"
        
        if filters:
            where_clause, params, _ = self.build_where_clause(filters)
            query = f"{base_query} WHERE {where_clause}"
        else:
            query = base_query
            params = []
        
        db = await self.get_connection()
        result = await db.fetchval(query, *params)
        return result or 0
    
    async def paginated_list(
        self,
        select_fields: str,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "ASC",
        additional_joins: str = "",
        schema: Optional[str] = None,
        uuid_fields: Optional[List[str]] = None,
        jsonb_fields: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], PaginationMetadata]:
        """
        Generic paginated list with dynamic schema support.
        
        Args:
            select_fields: SQL SELECT fields
            page: Page number (1-based)
            page_size: Items per page
            filters: Filter conditions
            sort_by: Field to sort by
            sort_order: Sort order (ASC/DESC)
            additional_joins: Additional JOIN clauses
            schema: Override schema for this operation
            uuid_fields: Fields to convert from UUID to string
            jsonb_fields: Fields to parse as JSON
            
        Returns:
            Tuple of (items, pagination_metadata)
        """
        # Validate pagination parameters
        page = max(1, page)
        page_size = min(max(1, page_size), 100)  # Cap at 100
        
        table_name = self.get_full_table_name(schema)
        
        # Build base query
        base_query = f"""
            SELECT {select_fields}
            FROM {table_name} t
            {additional_joins}
        """
        
        # Add WHERE clause if filters provided
        if filters:
            where_clause, params, _ = self.build_where_clause(filters)
            base_query += f" WHERE {where_clause}"
        else:
            params = []
        
        # Add ORDER BY clause
        order_clause = self.build_order_clause(sort_by, sort_order)
        
        # Build final query with pagination
        offset = (page - 1) * page_size
        query = f"""
            {base_query}
            {order_clause}
            LIMIT {page_size} OFFSET {offset}
        """
        
        # Get total count and data
        db = await self.get_connection()
        
        total_count = await self.count_with_filters(filters, schema)
        rows = await db.fetch(query, *params)
        
        # Process results
        items = []
        for row in rows:
            processed_row = process_database_record(
                row,
                uuid_fields=uuid_fields or [],
                jsonb_fields=jsonb_fields or []
            )
            items.append(processed_row)
        
        # Create pagination metadata
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
        
        pagination = PaginationMetadata(
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_items=total_count,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        return items, pagination
    
    async def get_by_id(
        self, 
        id: str,
        select_fields: str = "*",
        schema: Optional[str] = None,
        uuid_fields: Optional[List[str]] = None,
        jsonb_fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Get record by ID with dynamic schema support."""
        table_name = self.get_full_table_name(schema)
        
        query = f"SELECT {select_fields} FROM {table_name} WHERE id = $1"
        
        db = await self.get_connection()
        row = await db.fetchrow(query, id)
        
        if row:
            return process_database_record(
                row,
                uuid_fields=uuid_fields or ['id'],
                jsonb_fields=jsonb_fields or []
            )
        
        return None
    
    async def create(
        self,
        data: Dict[str, Any],
        returning_fields: str = "*",
        schema: Optional[str] = None,
        uuid_fields: Optional[List[str]] = None,
        jsonb_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create new record with dynamic schema support."""
        table_name = self.get_full_table_name(schema)
        
        fields = list(data.keys())
        placeholders = [f"${i+1}" for i in range(len(fields))]
        values = list(data.values())
        
        query = f"""
            INSERT INTO {table_name} ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
            RETURNING {returning_fields}
        """
        
        db = await self.get_connection()
        row = await db.fetchrow(query, *values)
        
        return process_database_record(
            row,
            uuid_fields=uuid_fields or ['id'],
            jsonb_fields=jsonb_fields or []
        )
    
    async def update(
        self,
        id: str,
        data: Dict[str, Any],
        returning_fields: str = "*",
        schema: Optional[str] = None,
        uuid_fields: Optional[List[str]] = None,
        jsonb_fields: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update record by ID with dynamic schema support."""
        if not data:
            return await self.get_by_id(id, returning_fields, schema, uuid_fields, jsonb_fields)
        
        table_name = self.get_full_table_name(schema)
        
        set_clauses = [f"{field} = ${i+2}" for i, field in enumerate(data.keys())]
        values = [id] + list(data.values())
        
        query = f"""
            UPDATE {table_name}
            SET {', '.join(set_clauses)}
            WHERE id = $1
            RETURNING {returning_fields}
        """
        
        db = await self.get_connection()
        row = await db.fetchrow(query, *values)
        
        if row:
            return process_database_record(
                row,
                uuid_fields=uuid_fields or ['id'],
                jsonb_fields=jsonb_fields or []
            )
        
        return None
    
    async def delete(
        self, 
        id: str,
        schema: Optional[str] = None
    ) -> bool:
        """Delete record by ID."""
        table_name = self.get_full_table_name(schema)
        
        query = f"DELETE FROM {table_name} WHERE id = $1"
        
        db = await self.get_connection()
        result = await db.execute(query, id)
        
        # Check if any rows were affected
        return result.split()[-1] == "1"
    
    async def soft_delete(
        self,
        id: str,
        schema: Optional[str] = None
    ) -> bool:
        """Soft delete record by setting is_active to false."""
        table_name = self.get_full_table_name(schema)
        
        query = f"""
            UPDATE {table_name} 
            SET is_active = false, updated_at = NOW()
            WHERE id = $1 AND is_active = true
        """
        
        db = await self.get_connection()
        result = await db.execute(query, id)
        
        return result.split()[-1] == "1"
    
    async def execute_query(
        self,
        query: str,
        *params,
        schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Execute custom query with schema context."""
        # Replace {schema} placeholder with actual schema
        if "{schema}" in query:
            effective_schema = schema or self.get_current_schema()
            query = query.format(schema=effective_schema)
        
        db = await self.get_connection()
        rows = await db.fetch(query, *params)
        
        return [dict(row) for row in rows]
    
    async def health_check(self) -> bool:
        """Check repository health."""
        try:
            if self.connection_provider:
                return await self.connection_provider.health_check()
            
            db = await self.get_connection()
            result = await db.fetchval("SELECT 1")
            return result == 1
        except Exception as e:
            logger.error(f"Repository health check failed: {e}")
            return False