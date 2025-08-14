"""
Database utility functions for common operations.
"""

from typing import Dict, Any, List, Tuple
import json
from uuid import UUID


def process_database_record(
    data: Any,  # Can be Dict or asyncpg.Record
    uuid_fields: List[str] = None, 
    jsonb_fields: List[str] = None,
    list_jsonb_fields: List[str] = None
) -> Dict[str, Any]:
    """Process a database record for domain model conversion.
    
    This function handles common database record processing:
    - Converts asyncpg.Record to dict if necessary
    - Converts UUID fields to strings
    - Parses JSONB fields from strings
    - Handles null values appropriately
    
    Args:
        data: Raw database record (Dict or asyncpg.Record)
        uuid_fields: List of field names that contain UUIDs (if None, auto-detects)
        jsonb_fields: List of field names that contain JSONB data (if None, auto-detects)
        list_jsonb_fields: List of field names that contain JSONB data as lists
        
    Returns:
        Processed data ready for domain model
    """
    # Convert asyncpg.Record to dict if necessary
    if hasattr(data, 'items'):
        # It's already a dict-like object, convert to actual dict
        data = dict(data)
    
    if uuid_fields is None:
        # Auto-detect common UUID fields
        uuid_fields = [
            'id', 'region_id', 'organization_id', 'tenant_id', 'user_id',
            'created_by', 'updated_by', 'deleted_by', 'connection_id',
            'parent_id', 'role_id', 'team_id', 'plan_id'
        ]
    
    if jsonb_fields is None:
        # Auto-detect common JSONB fields
        jsonb_fields = [
            'metadata', 'config', 'settings', 'permissions', 'tags_metadata',
            'configuration', 'preferences', 'attributes', 'properties'
        ]
    
    if list_jsonb_fields is None:
        # Auto-detect common JSONB fields that should be lists
        list_jsonb_fields = [
            'tags', 'compliance_certifications', 'availability_zones', 
            'backup_endpoints', 'allowed_origins', 'permissions_list',
            'capabilities', 'features', 'roles'
        ]
    
    # Process UUID fields
    for field in uuid_fields:
        if field in data and data[field] is not None:
            if isinstance(data[field], UUID):
                data[field] = str(data[field])
    
    # Process JSONB fields
    for field in jsonb_fields:
        if field in data:
            if isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field]) if data[field] else {}
                except json.JSONDecodeError:
                    # If it fails to parse, leave it as is
                    pass
            elif data[field] is None:
                data[field] = {}
            elif isinstance(data[field], dict) and not data[field]:
                # Empty dict - keep as is for dict-type fields
                pass
    
    # Process list-type JSONB fields
    for field in list_jsonb_fields:
        if field in data:
            if isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field]) if data[field] else []
                except json.JSONDecodeError:
                    data[field] = []
            elif data[field] is None:
                data[field] = []
            elif isinstance(data[field], dict) and not data[field]:
                # Empty dict from database - convert to empty list
                data[field] = []
    
    return data


def build_filter_conditions(
    filters: Dict[str, Any],
    table_alias: str = "t",
    param_prefix: str = "$"
) -> Tuple[List[str], List[Any]]:
    """Build WHERE conditions from filter dictionary.
    
    Args:
        filters: Dictionary of filter conditions
        table_alias: Table alias to use in conditions
        param_prefix: Parameter prefix for SQL placeholders ($1, $2, etc.)
        
    Returns:
        Tuple of (where_conditions list, parameters list)
    """
    where_conditions = []
    params = []
    param_count = 1
    
    for field, value in filters.items():
        if value is None:
            continue
        
        # Handle special filter operators
        if field.endswith('__ilike'):
            actual_field = field[:-7]
            where_conditions.append(f"{table_alias}.{actual_field} ILIKE {param_prefix}{param_count}")
            params.append(f"%{value}%")
        elif field.endswith('__in'):
            actual_field = field[:-4]
            where_conditions.append(f"{table_alias}.{actual_field} = ANY({param_prefix}{param_count})")
            params.append(value)
        elif field.endswith('__gte'):
            actual_field = field[:-5]
            where_conditions.append(f"{table_alias}.{actual_field} >= {param_prefix}{param_count}")
            params.append(value)
        elif field.endswith('__lte'):
            actual_field = field[:-5]
            where_conditions.append(f"{table_alias}.{actual_field} <= {param_prefix}{param_count}")
            params.append(value)
        elif field.endswith('__gt'):
            actual_field = field[:-4]
            where_conditions.append(f"{table_alias}.{actual_field} > {param_prefix}{param_count}")
            params.append(value)
        elif field.endswith('__lt'):
            actual_field = field[:-4]
            where_conditions.append(f"{table_alias}.{actual_field} < {param_prefix}{param_count}")
            params.append(value)
        elif field.endswith('__ne'):
            actual_field = field[:-4]
            where_conditions.append(f"{table_alias}.{actual_field} != {param_prefix}{param_count}")
            params.append(value)
        elif field.endswith('__is_null'):
            actual_field = field[:-9]
            if value:
                where_conditions.append(f"{table_alias}.{actual_field} IS NULL")
            else:
                where_conditions.append(f"{table_alias}.{actual_field} IS NOT NULL")
            # Don't increment param_count for IS NULL/IS NOT NULL
            continue
        elif isinstance(value, list):
            where_conditions.append(f"{table_alias}.{field} && {param_prefix}{param_count}")
            params.append(value)
        else:
            where_conditions.append(f"{table_alias}.{field} = {param_prefix}{param_count}")
            params.append(value)
        
        param_count += 1
    
    return where_conditions, params


def build_order_by(
    sort_by: str = None,
    sort_order: str = "asc",
    table_alias: str = "t",
    default_sort: str = "created_at"
) -> str:
    """Build ORDER BY clause.
    
    Args:
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)
        table_alias: Table alias to use
        default_sort: Default sort field if none provided
        
    Returns:
        ORDER BY clause string
    """
    if not sort_by:
        sort_by = default_sort
    
    # Validate sort order
    sort_order = sort_order.lower()
    if sort_order not in ['asc', 'desc']:
        sort_order = 'asc'
    
    return f"ORDER BY {table_alias}.{sort_by} {sort_order.upper()}"


def build_pagination_query(
    base_query: str,
    where_conditions: List[str] = None,
    order_by: str = None,
    limit: int = 20,
    offset: int = 0
) -> str:
    """Build a complete paginated query.
    
    Args:
        base_query: Base SELECT query
        where_conditions: List of WHERE conditions
        order_by: ORDER BY clause
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        Complete paginated SQL query
    """
    query_parts = [base_query]
    
    if where_conditions:
        query_parts.append("WHERE " + " AND ".join(where_conditions))
    
    if order_by:
        query_parts.append(order_by)
    
    query_parts.append(f"LIMIT {limit} OFFSET {offset}")
    
    return " ".join(query_parts)


def build_count_query(
    base_query: str,
    where_conditions: List[str] = None
) -> str:
    """Build a count query from a base query.
    
    Args:
        base_query: Base SELECT query
        where_conditions: List of WHERE conditions
        
    Returns:
        COUNT query string
    """
    # Extract FROM clause from base query
    from_index = base_query.upper().find('FROM')
    if from_index == -1:
        raise ValueError("Base query must contain a FROM clause")
    
    from_clause = base_query[from_index:]
    count_query = f"SELECT COUNT(*) {from_clause}"
    
    if where_conditions:
        count_query += " WHERE " + " AND ".join(where_conditions)
    
    return count_query


def escape_like_pattern(pattern: str) -> str:
    """Escape special characters in LIKE patterns.
    
    Args:
        pattern: The pattern to escape
        
    Returns:
        Escaped pattern safe for use in LIKE queries
    """
    return pattern.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def build_upsert_query(
    table: str,
    data: Dict[str, Any],
    conflict_columns: List[str],
    update_columns: List[str] = None
) -> Tuple[str, List[Any]]:
    """Build an UPSERT (INSERT ... ON CONFLICT) query.
    
    Args:
        table: Table name
        data: Data to insert/update
        conflict_columns: Columns that define the conflict
        update_columns: Columns to update on conflict (if None, updates all except conflict columns)
        
    Returns:
        Tuple of (query string, parameter list)
    """
    if not data:
        raise ValueError("Data dictionary cannot be empty")
    
    if not conflict_columns:
        raise ValueError("Conflict columns must be specified")
    
    columns = list(data.keys())
    values = list(data.values())
    
    # Build placeholders for values
    placeholders = ', '.join(f'${i+1}' for i in range(len(values)))
    
    # Build INSERT part
    insert_query = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({placeholders})
    """
    
    # Build ON CONFLICT part
    conflict_clause = f"ON CONFLICT ({', '.join(conflict_columns)})"
    
    if update_columns is None:
        # Update all columns except conflict columns
        update_columns = [col for col in columns if col not in conflict_columns]
    
    if update_columns:
        update_sets = [f"{col} = EXCLUDED.{col}" for col in update_columns]
        conflict_clause += f" DO UPDATE SET {', '.join(update_sets)}"
    else:
        conflict_clause += " DO NOTHING"
    
    query = f"{insert_query} {conflict_clause}"
    
    return query, values