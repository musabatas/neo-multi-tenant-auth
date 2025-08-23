"""
Database utility functions for common operations.

Service wrapper that imports from neo-commons database utilities
while maintaining backward compatibility for NeoAdminApi.
"""

# Import all utilities from neo-commons
from neo_commons.database.utils import (
    process_database_record,
    build_filter_conditions
)

# Re-export for backward compatibility
__all__ = ["process_database_record", "build_filter_conditions"]