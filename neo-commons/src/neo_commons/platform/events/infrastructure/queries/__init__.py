"""SQL queries for events infrastructure."""

from .event_queries import *

__all__ = [
    # Insert queries
    "EVENT_INSERT",
    
    # Update queries
    "EVENT_UPDATE",
    
    # Select queries
    "EVENT_GET_BY_ID",
    "EVENT_LIST_ALL",
    "EVENT_LIST_FILTERED", 
    "EVENT_COUNT_FILTERED",
    "EVENT_GET_HISTORY",
    "EVENT_GET_PENDING",
    "EVENT_GET_FAILED",
    
    # Delete queries
    "EVENT_DELETE_SOFT",
    
    # Utility queries
    "EVENT_EXISTS_BY_ID",
]