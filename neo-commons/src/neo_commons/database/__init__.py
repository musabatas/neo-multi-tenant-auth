"""Database utilities for NeoMultiTenant services."""

from .connection import (
    DatabaseManager,
    DynamicDatabaseManager,
    get_database,
    get_dynamic_database,
    init_database,
    close_database,
)
from .utils import (
    process_database_record,
    build_filter_conditions,
    build_order_by,
    build_pagination_query,
    build_count_query,
    escape_like_pattern,
    build_upsert_query,
)

__all__ = [
    # Connection management
    "DatabaseManager",
    "DynamicDatabaseManager", 
    "get_database",
    "get_dynamic_database",
    "init_database",
    "close_database",
    # Utilities
    "process_database_record",
    "build_filter_conditions",
    "build_order_by",
    "build_pagination_query",
    "build_count_query",
    "escape_like_pattern",
    "build_upsert_query",
]