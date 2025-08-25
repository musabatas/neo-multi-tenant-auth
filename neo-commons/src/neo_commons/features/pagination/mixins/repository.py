"""Repository mixins providing reusable pagination logic."""

import base64
import json
from typing import List, Optional, Dict, Any, TypeVar, Generic
from datetime import datetime
from ..entities import (
    OffsetPaginationRequest,
    OffsetPaginationResponse,
    CursorPaginationRequest, 
    CursorPaginationResponse,
    PaginationMetadata
)

T = TypeVar('T')


class PaginatedRepositoryMixin(Generic[T]):
    """Mixin providing offset-based pagination for repositories.
    
    Requires implementing class to have:
    - _db: Database connection
    - _schema: Schema name
    - _map_row_to_entity: Method to convert row to entity
    """
    
    async def find_paginated(
        self,
        pagination: OffsetPaginationRequest,
        base_query: str,
        count_query: str,
        query_params: Optional[List[Any]] = None
    ) -> OffsetPaginationResponse[T]:
        """Execute paginated query with performance metadata.
        
        Args:
            pagination: Pagination request
            base_query: Base SQL query without LIMIT/OFFSET (use {schema} placeholder)
            count_query: Count SQL query (use {schema} placeholder)
            query_params: Query parameters for both queries
            
        Returns:
            Paginated response with items and metadata
        """
        if query_params is None:
            query_params = []
            
        query_start = datetime.utcnow()
        
        # Build paginated query
        paginated_query = f"{base_query} {pagination.get_order_by_sql()} LIMIT ${len(query_params) + 1} OFFSET ${len(query_params) + 2}"
        paginated_params = query_params + [pagination.limit, pagination.offset]
        
        # Execute main query
        formatted_query = paginated_query.format(schema=self._schema)
        results = await self._db.fetch_all(formatted_query, paginated_params)
        query_end = datetime.utcnow()
        
        # Execute count query
        count_start = datetime.utcnow()
        formatted_count_query = count_query.format(schema=self._schema)
        count_result = await self._db.fetch_one(formatted_count_query, query_params)
        count_end = datetime.utcnow()
        
        # Convert results
        items = [self._map_row_to_entity(row) for row in results]
        total_count = count_result['count'] if count_result else 0
        
        # Create metadata
        metadata = PaginationMetadata.create_performance_metadata(
            query_start=query_start,
            query_end=query_end,
            count_start=count_start,
            count_end=count_end
        )
        
        return OffsetPaginationResponse(
            items=items,
            total=total_count,
            page=pagination.page,
            per_page=pagination.per_page,
            metadata=metadata
        )
    
    async def count_filtered(
        self,
        pagination: OffsetPaginationRequest,
        count_query: str,
        query_params: Optional[List[Any]] = None
    ) -> int:
        """Count total items matching pagination filters.
        
        Args:
            pagination: Pagination request with filters
            count_query: SQL count query (use {schema} placeholder)
            query_params: Query parameters
            
        Returns:
            Total count of matching items
        """
        if query_params is None:
            query_params = []
            
        formatted_query = count_query.format(schema=self._schema)
        result = await self._db.fetch_one(formatted_query, query_params)
        return result['count'] if result else 0


class CursorPaginatedRepositoryMixin(Generic[T]):
    """Mixin providing cursor-based pagination for repositories.
    
    Requires implementing class to have:
    - _db: Database connection
    - _schema: Schema name
    - _map_row_to_entity: Method to convert row to entity
    """
    
    def _encode_cursor(self, data: Dict[str, Any]) -> str:
        """Encode cursor data to base64 string."""
        json_str = json.dumps(data, separators=(',', ':'), sort_keys=True)
        return base64.urlsafe_b64encode(json_str.encode()).decode().rstrip('=')
    
    def _decode_cursor(self, cursor: str) -> Dict[str, Any]:
        """Decode cursor from base64 string."""
        # Add padding if needed
        padding = 4 - (len(cursor) % 4)
        if padding != 4:
            cursor += '=' * padding
            
        try:
            json_str = base64.urlsafe_b64decode(cursor.encode()).decode()
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid cursor format: {e}")
    
    async def find_cursor_paginated(
        self,
        pagination: CursorPaginationRequest,
        base_query: str,
        cursor_field: str = "id",
        query_params: Optional[List[Any]] = None
    ) -> CursorPaginationResponse[T]:
        """Execute cursor-based paginated query.
        
        Args:
            pagination: Cursor pagination request
            base_query: Base SQL query without cursor conditions (use {schema} placeholder)
            cursor_field: Field to use for cursor-based pagination
            query_params: Query parameters
            
        Returns:
            Cursor paginated response
        """
        if query_params is None:
            query_params = []
            
        query_start = datetime.utcnow()
        
        # Build cursor conditions
        cursor_conditions = []
        cursor_params = []
        
        if pagination.cursor_after:
            cursor_data = self._decode_cursor(pagination.cursor_after)
            cursor_value = cursor_data.get(cursor_field)
            if cursor_value:
                cursor_conditions.append(f"{cursor_field} > ${len(query_params) + len(cursor_params) + 1}")
                cursor_params.append(cursor_value)
        
        if pagination.cursor_before:
            cursor_data = self._decode_cursor(pagination.cursor_before)
            cursor_value = cursor_data.get(cursor_field)
            if cursor_value:
                cursor_conditions.append(f"{cursor_field} < ${len(query_params) + len(cursor_params) + 1}")
                cursor_params.append(cursor_value)
        
        # Build final query
        where_clause = ""
        if cursor_conditions:
            where_clause = f" AND ({' AND '.join(cursor_conditions)})"
            
        # Add extra item to check for more results
        limit = pagination.limit + 1
        final_query = f"{base_query}{where_clause} {pagination.get_order_by_sql()} LIMIT ${len(query_params) + len(cursor_params) + 1}"
        final_params = query_params + cursor_params + [limit]
        
        # Execute query
        formatted_query = final_query.format(schema=self._schema)
        results = await self._db.fetch_all(formatted_query, final_params)
        query_end = datetime.utcnow()
        
        # Check if there are more results
        has_more = len(results) > pagination.limit
        if has_more:
            results = results[:-1]  # Remove extra item
        
        # Convert results
        items = [self._map_row_to_entity(row) for row in results]
        
        # Generate cursors
        next_cursor = None
        prev_cursor = None
        
        if items and has_more:
            last_item = results[-1]
            next_cursor = self._encode_cursor({cursor_field: last_item[cursor_field]})
            
        if items and pagination.cursor_after:
            first_item = results[0]
            prev_cursor = self._encode_cursor({cursor_field: first_item[cursor_field]})
        
        # Create metadata
        metadata = PaginationMetadata.create_performance_metadata(
            query_start=query_start,
            query_end=query_end
        )
        
        return CursorPaginationResponse(
            items=items,
            next_cursor=next_cursor,
            prev_cursor=prev_cursor,
            has_more=has_more,
            metadata=metadata
        )
    
    async def estimate_total(
        self,
        pagination: CursorPaginationRequest,
        estimate_query: str,
        query_params: Optional[List[Any]] = None
    ) -> Optional[int]:
        """Get estimated total count for cursor pagination.
        
        Args:
            pagination: Cursor pagination request
            estimate_query: SQL query for count estimation (use {schema} placeholder)
            query_params: Query parameters
            
        Returns:
            Estimated total count, or None if not available
        """
        if query_params is None:
            query_params = []
            
        try:
            formatted_query = estimate_query.format(schema=self._schema)
            result = await self._db.fetch_one(formatted_query, query_params)
            return result['estimate'] if result else None
        except Exception:
            # If estimation fails, return None
            return None