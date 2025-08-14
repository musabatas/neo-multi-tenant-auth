"""
Base repository pattern for database operations.
"""

from typing import Optional, List, Dict, Any, TypeVar, Generic
from abc import ABC, abstractmethod
import logging

from neo_commons.database.connection import DatabaseManager
from neo_commons.models.pagination import PaginationParams

T = TypeVar('T')

logger = logging.getLogger(__name__)


class BaseRepository(ABC, Generic[T]):
    """
    Base repository class providing common database operations.
    
    This class implements common patterns for:
    - Database connection management
    - Pagination query building
    - Error handling and logging
    - Query parameter binding
    """
    
    def __init__(
        self, 
        table_name: str, 
        schema: str = "admin",
        db_manager: Optional[DatabaseManager] = None
    ):
        """Initialize base repository.
        
        Args:
            table_name: The database table name
            schema: The database schema (default: admin)
            db_manager: Optional database manager (for dependency injection)
        """
        self.db = db_manager
        self.table_name = table_name
        self.schema = schema
        self.full_table_name = f"{schema}.{table_name}"
    
    def set_database_manager(self, db_manager: DatabaseManager):
        """Set the database manager (for dependency injection)."""
        self.db = db_manager
    
    def build_where_clause(
        self,
        conditions: Dict[str, Any],
        param_offset: int = 0
    ) -> tuple[str, List[Any], int]:
        """Build WHERE clause from conditions dictionary.
        
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
            elif field.endswith('__gt'):
                actual_field = field[:-4]  # Remove '__gt'
                where_parts.append(f"{actual_field} > ${param_count}")
                params.append(value)
            elif field.endswith('__lt'):
                actual_field = field[:-4]  # Remove '__lt'
                where_parts.append(f"{actual_field} < ${param_count}")
                params.append(value)
            elif field.endswith('__ne'):
                actual_field = field[:-4]  # Remove '__ne'
                where_parts.append(f"{actual_field} != ${param_count}")
                params.append(value)
            elif isinstance(value, bool):
                where_parts.append(f"{field} = ${param_count}")
                params.append(value)
            elif isinstance(value, list):
                where_parts.append(f"{field} && ${param_count}")
                params.append(value)
            else:
                where_parts.append(f"{field} = ${param_count}")
                params.append(value)
        
        where_clause = " AND ".join(where_parts) if where_parts else "1=1"
        return where_clause, params, param_count
    
    async def count_with_filters(
        self,
        filters: Dict[str, Any],
        additional_where: Optional[str] = None,
        include_deleted: bool = False
    ) -> int:
        """Count records with filters.
        
        Args:
            filters: Dictionary of filter conditions
            additional_where: Additional WHERE clause to append
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Total count of matching records
        """
        if not self.db:
            raise RuntimeError("Database manager not set. Call set_database_manager() first.")
            
        # Build base WHERE clause
        where_clause, params, _ = self.build_where_clause(filters)
        
        # Add soft delete check unless including deleted records
        if not include_deleted:
            where_clause = f"({where_clause}) AND deleted_at IS NULL"
        
        # Add additional WHERE if provided
        if additional_where:
            where_clause = f"({where_clause}) AND ({additional_where})"
        
        query = f"""
            SELECT COUNT(*) as total
            FROM {self.full_table_name}
            WHERE {where_clause}
        """
        
        result = await self.db.fetchval(query, *params)
        return result or 0
    
    async def paginated_list(
        self,
        pagination: PaginationParams,
        filters: Dict[str, Any],
        order_by: str = "created_at DESC",
        select_columns: Optional[str] = None,
        additional_joins: Optional[str] = None,
        additional_where: Optional[str] = None,
        include_deleted: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get paginated list with filters.
        
        Args:
            pagination: Pagination parameters
            filters: Filter conditions
            order_by: ORDER BY clause
            select_columns: Columns to select (default: *)
            additional_joins: Additional JOIN clauses
            additional_where: Additional WHERE conditions
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Tuple of (records, total_count)
        """
        if not self.db:
            raise RuntimeError("Database manager not set. Call set_database_manager() first.")
            
        # Get total count
        total_count = await self.count_with_filters(filters, additional_where, include_deleted)
        
        # Build WHERE clause
        where_clause, params, param_count = self.build_where_clause(filters)
        
        # Add soft delete check unless including deleted records
        if not include_deleted:
            where_clause = f"({where_clause}) AND t.deleted_at IS NULL"
        
        # Add additional WHERE if provided
        if additional_where:
            where_clause = f"({where_clause}) AND ({additional_where})"
        
        # Add pagination parameters
        param_count += 1
        limit_param = param_count
        params.append(pagination.limit)
        
        param_count += 1
        offset_param = param_count
        params.append(pagination.offset)
        
        # Build query
        select_clause = select_columns or "t.*"
        joins_clause = additional_joins or ""
        
        query = f"""
            SELECT {select_clause}
            FROM {self.full_table_name} t
            {joins_clause}
            WHERE {where_clause}
            ORDER BY t.{order_by}
            LIMIT ${limit_param}
            OFFSET ${offset_param}
        """
        
        records = await self.db.fetch(query, *params)
        
        # Convert records to dict
        result = [dict(record) for record in records]
        
        return result, total_count
    
    async def get_by_id(
        self,
        record_id: str,
        select_columns: Optional[str] = None,
        additional_joins: Optional[str] = None,
        include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get a single record by ID.
        
        Args:
            record_id: The record ID
            select_columns: Columns to select
            additional_joins: Additional JOIN clauses
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            Record as dictionary or None if not found
        """
        if not self.db:
            raise RuntimeError("Database manager not set. Call set_database_manager() first.")
            
        select_clause = select_columns or "t.*"
        joins_clause = additional_joins or ""
        
        # Build WHERE clause for soft delete
        soft_delete_clause = "" if include_deleted else "AND t.deleted_at IS NULL"
        
        query = f"""
            SELECT {select_clause}
            FROM {self.full_table_name} t
            {joins_clause}
            WHERE t.id = $1 {soft_delete_clause}
        """
        
        record = await self.db.fetchrow(query, record_id)
        return dict(record) if record else None
    
    async def exists(
        self,
        conditions: Dict[str, Any],
        exclude_id: Optional[str] = None,
        include_deleted: bool = False
    ) -> bool:
        """Check if a record exists with given conditions.
        
        Args:
            conditions: Conditions to check
            exclude_id: ID to exclude from check (for updates)
            include_deleted: Whether to include soft-deleted records
            
        Returns:
            True if record exists, False otherwise
        """
        if not self.db:
            raise RuntimeError("Database manager not set. Call set_database_manager() first.")
            
        where_clause, params, param_count = self.build_where_clause(conditions)
        
        # Add soft delete check unless including deleted records
        if not include_deleted:
            where_clause = f"({where_clause}) AND deleted_at IS NULL"
        
        # Exclude specific ID if provided (for update operations)
        if exclude_id:
            param_count += 1
            where_clause = f"({where_clause}) AND id != ${param_count}"
            params.append(exclude_id)
        
        query = f"""
            SELECT EXISTS(
                SELECT 1 FROM {self.full_table_name}
                WHERE {where_clause}
            )
        """
        
        return await self.db.fetchval(query, *params)
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new record. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    async def update(self, record_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a record. Must be implemented by subclasses."""
        pass
    
    async def soft_delete(self, record_id: str, deleted_by: Optional[str] = None) -> bool:
        """Soft delete a record by setting deleted_at.
        
        Args:
            record_id: The record ID to delete
            deleted_by: ID of user performing the deletion
            
        Returns:
            True if deleted, False if not found
        """
        if not self.db:
            raise RuntimeError("Database manager not set. Call set_database_manager() first.")
            
        # Build update fields
        update_fields = ["deleted_at = NOW()"]
        params = [record_id]
        
        if deleted_by:
            update_fields.append("deleted_by = $2")
            params.append(deleted_by)
        
        query = f"""
            UPDATE {self.full_table_name}
            SET {', '.join(update_fields)}
            WHERE id = $1 AND deleted_at IS NULL
            RETURNING id
        """
        
        result = await self.db.fetchval(query, *params)
        return result is not None
    
    async def restore(self, record_id: str) -> bool:
        """Restore a soft-deleted record.
        
        Args:
            record_id: The record ID to restore
            
        Returns:
            True if restored, False if not found
        """
        if not self.db:
            raise RuntimeError("Database manager not set. Call set_database_manager() first.")
            
        query = f"""
            UPDATE {self.full_table_name}
            SET deleted_at = NULL, deleted_by = NULL
            WHERE id = $1 AND deleted_at IS NOT NULL
            RETURNING id
        """
        
        result = await self.db.fetchval(query, record_id)
        return result is not None