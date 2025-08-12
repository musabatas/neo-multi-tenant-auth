"""
Database utility functions for common operations.
"""

from typing import Dict, Any, List
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
        
    Returns:
        Processed data ready for domain model
    """
    # Convert asyncpg.Record to dict if necessary
    if hasattr(data, 'items'):
        # It's already a dict-like object, convert to actual dict
        data = dict(data)
    if uuid_fields is None:
        # Auto-detect common UUID fields
        uuid_fields = ['id', 'region_id', 'organization_id', 'tenant_id', 'user_id', 
                      'created_by', 'updated_by', 'deleted_by']
    
    if jsonb_fields is None:
        # Auto-detect common JSONB fields
        jsonb_fields = ['metadata', 'config', 'settings', 'permissions', 'tags_metadata']
    
    if list_jsonb_fields is None:
        # Auto-detect common JSONB fields that should be lists
        list_jsonb_fields = ['tags', 'compliance_certifications', 'availability_zones', 'backup_endpoints']
    
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
    table_alias: str = "t"
) -> tuple[List[str], List[Any]]:
    """Build WHERE conditions from filter dictionary.
    
    Args:
        filters: Dictionary of filter conditions
        table_alias: Table alias to use in conditions
        
    Returns:
        Tuple of (where_conditions list, parameters list)
    """
    where_conditions = []
    params = []
    
    for field, value in filters.items():
        if value is None:
            continue
        
        # Handle special filter operators
        if field.endswith('__ilike'):
            actual_field = field[:-7]
            where_conditions.append(f"{table_alias}.{actual_field} ILIKE %s")
            params.append(f"%{value}%")
        elif field.endswith('__in'):
            actual_field = field[:-4]
            where_conditions.append(f"{table_alias}.{actual_field} = ANY(%s)")
            params.append(value)
        elif field.endswith('__gte'):
            actual_field = field[:-5]
            where_conditions.append(f"{table_alias}.{actual_field} >= %s")
            params.append(value)
        elif field.endswith('__lte'):
            actual_field = field[:-5]
            where_conditions.append(f"{table_alias}.{actual_field} <= %s")
            params.append(value)
        elif isinstance(value, list):
            where_conditions.append(f"{table_alias}.{field} && %s")
            params.append(value)
        else:
            where_conditions.append(f"{table_alias}.{field} = %s")
            params.append(value)
    
    return where_conditions, params