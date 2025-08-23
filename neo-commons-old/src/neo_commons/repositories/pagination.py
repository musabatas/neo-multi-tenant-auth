"""
Advanced pagination utilities for database repositories.

This module provides both offset-based and cursor-based pagination strategies
with support for complex queries, filtering, and sorting.
"""

import base64
import json
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ..models.base import PaginationMetadata
from ..database.utils import process_database_record


class PaginationType(Enum):
    """Pagination strategy types."""
    OFFSET = "offset"
    CURSOR = "cursor"
    KEYSET = "keyset"


@dataclass
class CursorInfo:
    """Cursor information for cursor-based pagination."""
    last_id: Optional[str] = None
    last_value: Optional[Any] = None
    direction: str = "next"
    limit: int = 20
    
    def encode(self) -> str:
        """Encode cursor information to base64 string."""
        cursor_data = {
            "id": self.last_id,
            "val": self.last_value,
            "dir": self.direction,
            "lim": self.limit
        }
        # Convert datetime to ISO format if present
        if isinstance(cursor_data["val"], datetime):
            cursor_data["val"] = cursor_data["val"].isoformat()
        
        json_str = json.dumps(cursor_data)
        return base64.b64encode(json_str.encode()).decode()
    
    @classmethod
    def decode(cls, cursor: str) -> 'CursorInfo':
        """Decode cursor string to CursorInfo object."""
        try:
            json_str = base64.b64decode(cursor.encode()).decode()
            cursor_data = json.loads(json_str)
            
            # Convert ISO string back to datetime if needed
            if cursor_data.get("val") and isinstance(cursor_data["val"], str):
                try:
                    cursor_data["val"] = datetime.fromisoformat(cursor_data["val"])
                except:
                    pass  # Keep as string if not a datetime
            
            return cls(
                last_id=cursor_data.get("id"),
                last_value=cursor_data.get("val"),
                direction=cursor_data.get("dir", "next"),
                limit=cursor_data.get("lim", 20)
            )
        except Exception:
            # Return default if cursor is invalid
            return cls()


@dataclass
class PaginationParams:
    """Unified pagination parameters supporting multiple strategies."""
    # Common parameters
    limit: int = 20
    order_by: str = "created_at"
    order_direction: str = "DESC"
    
    # Offset-based pagination
    page: Optional[int] = None
    offset: Optional[int] = None
    
    # Cursor-based pagination
    cursor: Optional[str] = None
    after: Optional[str] = None  # Cursor for next page
    before: Optional[str] = None  # Cursor for previous page
    
    # Keyset pagination
    last_id: Optional[str] = None
    last_value: Optional[Any] = None
    
    @property
    def pagination_type(self) -> PaginationType:
        """Determine pagination type based on parameters."""
        if self.cursor or self.after or self.before:
            return PaginationType.CURSOR
        elif self.last_id is not None:
            return PaginationType.KEYSET
        else:
            return PaginationType.OFFSET
    
    @property
    def calculated_offset(self) -> int:
        """Calculate offset for offset-based pagination."""
        if self.offset is not None:
            return self.offset
        elif self.page is not None:
            return (max(1, self.page) - 1) * self.limit
        return 0


class PaginationHelper:
    """Helper class for building paginated queries."""
    
    @staticmethod
    def build_offset_pagination_query(
        base_query: str,
        params: List[Any],
        pagination: PaginationParams,
        order_clause: str
    ) -> Tuple[str, List[Any]]:
        """Build query for offset-based pagination.
        
        Args:
            base_query: Base SQL query without ORDER BY or LIMIT
            params: Query parameters
            pagination: Pagination parameters
            order_clause: ORDER BY clause
            
        Returns:
            Tuple of (query, parameters)
        """
        offset = pagination.calculated_offset
        limit = min(max(1, pagination.limit), 100)  # Cap at 100
        
        query = f"""
            {base_query}
            {order_clause}
            LIMIT {limit} OFFSET {offset}
        """
        
        return query, params
    
    @staticmethod
    def build_cursor_pagination_query(
        base_query: str,
        params: List[Any],
        pagination: PaginationParams,
        table_alias: str = "t"
    ) -> Tuple[str, List[Any], CursorInfo]:
        """Build query for cursor-based pagination.
        
        Args:
            base_query: Base SQL query
            params: Query parameters
            pagination: Pagination parameters
            table_alias: Table alias used in query
            
        Returns:
            Tuple of (query, parameters, cursor_info)
        """
        cursor_info = CursorInfo()
        
        # Decode cursor if provided
        if pagination.cursor:
            cursor_info = CursorInfo.decode(pagination.cursor)
        elif pagination.after:
            cursor_info = CursorInfo.decode(pagination.after)
            cursor_info.direction = "next"
        elif pagination.before:
            cursor_info = CursorInfo.decode(pagination.before)
            cursor_info.direction = "prev"
        
        # Build WHERE clause for cursor
        cursor_where = ""
        if cursor_info.last_id:
            param_num = len(params) + 1
            
            if pagination.order_direction.upper() == "DESC":
                if cursor_info.direction == "next":
                    cursor_where = f" AND ({table_alias}.{pagination.order_by} < ${param_num} OR ({table_alias}.{pagination.order_by} = ${param_num} AND {table_alias}.id < ${param_num + 1}))"
                else:
                    cursor_where = f" AND ({table_alias}.{pagination.order_by} > ${param_num} OR ({table_alias}.{pagination.order_by} = ${param_num} AND {table_alias}.id > ${param_num + 1}))"
            else:
                if cursor_info.direction == "next":
                    cursor_where = f" AND ({table_alias}.{pagination.order_by} > ${param_num} OR ({table_alias}.{pagination.order_by} = ${param_num} AND {table_alias}.id > ${param_num + 1}))"
                else:
                    cursor_where = f" AND ({table_alias}.{pagination.order_by} < ${param_num} OR ({table_alias}.{pagination.order_by} = ${param_num} AND {table_alias}.id < ${param_num + 1}))"
            
            params.extend([cursor_info.last_value, cursor_info.last_id])
        
        # Add cursor WHERE clause to base query
        if cursor_where:
            if " WHERE " in base_query:
                base_query = base_query.replace(" WHERE ", f" WHERE 1=1{cursor_where} AND ")
            else:
                base_query += f" WHERE 1=1{cursor_where}"
        
        # Build ORDER BY clause
        order_dir = pagination.order_direction.upper()
        if cursor_info.direction == "prev":
            # Reverse order for previous page
            order_dir = "ASC" if order_dir == "DESC" else "DESC"
        
        order_clause = f"ORDER BY {table_alias}.{pagination.order_by} {order_dir}, {table_alias}.id {order_dir}"
        
        # Add LIMIT
        limit = min(max(1, pagination.limit), 100)
        query = f"""
            {base_query}
            {order_clause}
            LIMIT {limit + 1}
        """
        
        return query, params, cursor_info
    
    @staticmethod
    def build_keyset_pagination_query(
        base_query: str,
        params: List[Any],
        pagination: PaginationParams,
        table_alias: str = "t"
    ) -> Tuple[str, List[Any]]:
        """Build query for keyset pagination.
        
        Args:
            base_query: Base SQL query
            params: Query parameters
            pagination: Pagination parameters
            table_alias: Table alias used in query
            
        Returns:
            Tuple of (query, parameters)
        """
        # Build WHERE clause for keyset
        if pagination.last_id and pagination.last_value is not None:
            param_num = len(params) + 1
            
            if pagination.order_direction.upper() == "DESC":
                keyset_where = f" AND ({table_alias}.{pagination.order_by} < ${param_num} OR ({table_alias}.{pagination.order_by} = ${param_num} AND {table_alias}.id < ${param_num + 1}))"
            else:
                keyset_where = f" AND ({table_alias}.{pagination.order_by} > ${param_num} OR ({table_alias}.{pagination.order_by} = ${param_num} AND {table_alias}.id > ${param_num + 1}))"
            
            params.extend([pagination.last_value, pagination.last_id])
            
            # Add keyset WHERE clause to base query
            if " WHERE " in base_query:
                base_query = base_query.replace(" WHERE ", f" WHERE 1=1{keyset_where} AND ")
            else:
                base_query += f" WHERE 1=1{keyset_where}"
        
        # Build ORDER BY clause
        order_clause = f"ORDER BY {table_alias}.{pagination.order_by} {pagination.order_direction}, {table_alias}.id {pagination.order_direction}"
        
        # Add LIMIT
        limit = min(max(1, pagination.limit), 100)
        query = f"""
            {base_query}
            {order_clause}
            LIMIT {limit}
        """
        
        return query, params


class PaginatedRepository:
    """Mixin class for repositories with advanced pagination support."""
    
    async def paginated_list_advanced(
        self,
        select_fields: str,
        table_name: str,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        additional_joins: str = "",
        additional_where: Optional[str] = None,
        uuid_fields: Optional[List[str]] = None,
        jsonb_fields: Optional[List[str]] = None,
        get_connection_func=None,
        build_where_func=None
    ) -> Dict[str, Any]:
        """Advanced paginated list supporting multiple pagination strategies.
        
        Args:
            select_fields: SQL SELECT fields
            table_name: Fully qualified table name
            pagination: Pagination parameters
            filters: Filter conditions
            additional_joins: Additional JOIN clauses
            additional_where: Additional WHERE clause
            uuid_fields: Fields to convert from UUID to string
            jsonb_fields: Fields to parse as JSON
            get_connection_func: Function to get database connection
            build_where_func: Function to build WHERE clause from filters
            
        Returns:
            Dictionary with items, pagination metadata, and cursors
        """
        # Build base query
        base_query = f"""
            SELECT {select_fields}
            FROM {table_name} t
            {additional_joins}
        """
        
        # Build WHERE clause
        where_parts = []
        params = []
        
        if filters and build_where_func:
            where_clause, params, _ = build_where_func(filters)
            where_parts.append(where_clause)
        
        if additional_where:
            where_parts.append(f"({additional_where})")
        
        # Add WHERE clause to query
        if where_parts:
            combined_where = " AND ".join(where_parts)
            base_query += f" WHERE {combined_where}"
        
        # Build pagination query based on type
        if pagination.pagination_type == PaginationType.CURSOR:
            query, params, cursor_info = PaginationHelper.build_cursor_pagination_query(
                base_query, params, pagination
            )
            
            # Execute query
            db = await get_connection_func() if get_connection_func else None
            rows = await db.fetch(query, *params) if db else []
            
            # Process results
            items = []
            for row in rows[:pagination.limit]:  # Exclude extra row used for has_more
                processed_row = process_database_record(
                    row,
                    uuid_fields=uuid_fields or [],
                    jsonb_fields=jsonb_fields or []
                )
                items.append(processed_row)
            
            # Determine if there are more pages
            has_next = len(rows) > pagination.limit
            has_previous = cursor_info.last_id is not None
            
            # Create cursors for next/previous pages
            next_cursor = None
            prev_cursor = None
            
            if items and has_next:
                last_item = items[-1]
                next_info = CursorInfo(
                    last_id=last_item.get("id"),
                    last_value=last_item.get(pagination.order_by),
                    direction="next",
                    limit=pagination.limit
                )
                next_cursor = next_info.encode()
            
            if items and has_previous:
                first_item = items[0]
                prev_info = CursorInfo(
                    last_id=first_item.get("id"),
                    last_value=first_item.get(pagination.order_by),
                    direction="prev",
                    limit=pagination.limit
                )
                prev_cursor = prev_info.encode()
            
            # Reverse items if we were going backwards
            if cursor_info.direction == "prev":
                items.reverse()
            
            return {
                "items": items,
                "pagination": {
                    "type": "cursor",
                    "has_next": has_next,
                    "has_previous": has_previous,
                    "next_cursor": next_cursor,
                    "previous_cursor": prev_cursor,
                    "limit": pagination.limit
                }
            }
            
        elif pagination.pagination_type == PaginationType.KEYSET:
            query, params = PaginationHelper.build_keyset_pagination_query(
                base_query, params, pagination
            )
            
            # Execute query
            db = await get_connection_func() if get_connection_func else None
            rows = await db.fetch(query, *params) if db else []
            
            # Process results
            items = []
            for row in rows:
                processed_row = process_database_record(
                    row,
                    uuid_fields=uuid_fields or [],
                    jsonb_fields=jsonb_fields or []
                )
                items.append(processed_row)
            
            # Get last item for next page keyset
            last_item = items[-1] if items else None
            
            return {
                "items": items,
                "pagination": {
                    "type": "keyset",
                    "last_id": last_item.get("id") if last_item else None,
                    "last_value": last_item.get(pagination.order_by) if last_item else None,
                    "limit": pagination.limit,
                    "has_more": len(items) == pagination.limit
                }
            }
            
        else:  # OFFSET pagination
            order_clause = f"ORDER BY t.{pagination.order_by} {pagination.order_direction}"
            query, params = PaginationHelper.build_offset_pagination_query(
                base_query, params, pagination, order_clause
            )
            
            # Get total count for offset pagination
            count_query = f"""
                SELECT COUNT(*) 
                FROM {table_name} t
                {additional_joins}
            """
            if where_parts:
                count_query += f" WHERE {' AND '.join(where_parts)}"
            
            # Execute queries
            db = await get_connection_func() if get_connection_func else None
            if db:
                total_count = await db.fetchval(count_query, *params[:len(params)])
                rows = await db.fetch(query, *params)
            else:
                total_count = 0
                rows = []
            
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
            page = pagination.page or 1
            total_pages = (total_count + pagination.limit - 1) // pagination.limit if total_count > 0 else 0
            
            return {
                "items": items,
                "pagination": PaginationMetadata(
                    page=page,
                    page_size=pagination.limit,
                    total_pages=total_pages,
                    total_items=total_count,
                    has_next=page < total_pages,
                    has_previous=page > 1
                ).__dict__
            }