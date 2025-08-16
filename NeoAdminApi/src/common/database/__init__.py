"""
Database layer components for NeoAdminApi.

Service wrapper that provides database utilities and connection management
while importing shared functionality from neo-commons.
"""

from .utils import process_database_record, build_filter_conditions
from .connection import DatabaseManager, get_database

__all__ = ["process_database_record", "build_filter_conditions", "DatabaseManager", "get_database"]