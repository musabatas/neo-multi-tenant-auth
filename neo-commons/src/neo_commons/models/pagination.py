"""
Pagination utilities and patterns for the NeoMultiTenant platform.

This module provides reusable pagination logic that can be used across all services
to implement consistent pagination patterns.
"""
from typing import Generic, TypeVar, List, Optional, Any, Dict
from .base import BaseSchema, PaginationParams, PaginationMetadata, PaginatedResponse

T = TypeVar('T')


class PaginationHelper(Generic[T]):
    """Helper class for implementing consistent pagination patterns."""
    
    @staticmethod
    def create_metadata(
        page: int,
        page_size: int,
        total_items: int
    ) -> PaginationMetadata:
        """Create pagination metadata from basic parameters."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        
        return PaginationMetadata(
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_items=total_items,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    
    @staticmethod
    def create_response(
        items: List[T],
        page: int,
        page_size: int,
        total_items: int
    ) -> PaginatedResponse[T]:
        """Create a complete paginated response."""
        metadata = PaginationHelper.create_metadata(page, page_size, total_items)
        return PaginatedResponse(items=items, pagination=metadata)
    
    @staticmethod
    def validate_params(page: int, page_size: int, max_page_size: int = 100) -> None:
        """Validate pagination parameters and raise appropriate errors."""
        from ..exceptions.base import ValidationError
        
        errors = []
        
        if page < 1:
            errors.append({
                "field": "page",
                "value": page,
                "requirement": "Must be >= 1"
            })
        
        if page_size < 1:
            errors.append({
                "field": "page_size", 
                "value": page_size,
                "requirement": "Must be >= 1"
            })
        
        if page_size > max_page_size:
            errors.append({
                "field": "page_size",
                "value": page_size,
                "requirement": f"Must be <= {max_page_size}"
            })
        
        if errors:
            raise ValidationError(
                message="Invalid pagination parameters",
                errors=errors
            )
    
    @staticmethod
    def calculate_offset(page: int, page_size: int) -> int:
        """Calculate database offset from page parameters."""
        return (page - 1) * page_size
    
    @staticmethod
    def extract_params(
        pagination_params: Optional[PaginationParams] = None,
        default_page: int = 1,
        default_page_size: int = 20
    ) -> tuple[int, int, int]:
        """Extract and validate pagination parameters, returning (page, page_size, offset)."""
        if pagination_params:
            page = pagination_params.page
            page_size = pagination_params.page_size
        else:
            page = default_page
            page_size = default_page_size
        
        PaginationHelper.validate_params(page, page_size)
        offset = PaginationHelper.calculate_offset(page, page_size)
        
        return page, page_size, offset


class FilterBuilder:
    """Helper class for building database filter conditions consistently."""
    
    @staticmethod
    def build_where_conditions(
        filters: Dict[str, Any],
        search_fields: Optional[List[str]] = None,
        schema: str = "public"
    ) -> tuple[str, List[Any]]:
        """
        Build WHERE clause and parameters for database queries.
        
        Args:
            filters: Dictionary of filter conditions
            search_fields: List of fields to search in for 'search' filter
            schema: Database schema name
            
        Returns:
            Tuple of (where_clause, parameters)
        """
        conditions = []
        params = []
        param_counter = 1
        
        for field, value in filters.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
                
            if field == "search" and search_fields:
                # Build search condition across multiple fields
                search_conditions = []
                for search_field in search_fields:
                    search_conditions.append(f"{search_field} ILIKE ${param_counter}")
                    params.append(f"%{value}%")
                    param_counter += 1
                
                if search_conditions:
                    conditions.append(f"({' OR '.join(search_conditions)})")
                    
            elif field == "is_active" and isinstance(value, bool):
                conditions.append(f"is_active = ${param_counter}")
                params.append(value)
                param_counter += 1
                
            elif field == "created_after" and value:
                conditions.append(f"created_at >= ${param_counter}")
                params.append(value)
                param_counter += 1
                
            elif field == "created_before" and value:
                conditions.append(f"created_at <= ${param_counter}")
                params.append(value)
                param_counter += 1
                
            else:
                # Generic equality filter
                conditions.append(f"{field} = ${param_counter}")
                params.append(value)
                param_counter += 1
        
        where_clause = " AND ".join(conditions) if conditions else "TRUE"
        return where_clause, params
    
    @staticmethod
    def build_order_clause(
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        default_sort: str = "created_at"
    ) -> str:
        """Build ORDER BY clause for queries."""
        sort_field = sort_by or default_sort
        order_direction = "DESC" if sort_order.lower() == "desc" else "ASC"
        return f"ORDER BY {sort_field} {order_direction}"


class ListQueryBuilder:
    """Helper for building standardized list queries with pagination and filtering."""
    
    @staticmethod
    def build_list_query(
        base_table: str,
        select_fields: str = "*",
        filters: Optional[Dict[str, Any]] = None,
        search_fields: Optional[List[str]] = None,
        pagination: Optional[PaginationParams] = None,
        schema: str = "public"
    ) -> tuple[str, str, List[Any]]:
        """
        Build complete list query with filtering, pagination and count query.
        
        Returns:
            Tuple of (list_query, count_query, parameters)
        """
        filters = filters or {}
        
        # Build WHERE conditions
        where_clause, params = FilterBuilder.build_where_conditions(
            filters, search_fields, schema
        )
        
        # Build ORDER clause
        sort_by = getattr(pagination, 'sort_by', None) if pagination else None
        sort_order = getattr(pagination, 'sort_order', 'asc') if pagination else 'asc'
        order_clause = FilterBuilder.build_order_clause(sort_by, sort_order)
        
        # Build pagination
        limit_offset = ""
        if pagination:
            page, page_size, offset = PaginationHelper.extract_params(pagination)
            limit_offset = f"LIMIT {page_size} OFFSET {offset}"
        
        # Construct queries
        list_query = f"""
            SELECT {select_fields}
            FROM {schema}.{base_table}
            WHERE {where_clause}
            {order_clause}
            {limit_offset}
        """.strip()
        
        count_query = f"""
            SELECT COUNT(*)
            FROM {schema}.{base_table}
            WHERE {where_clause}
        """.strip()
        
        return list_query, count_query, params