"""
NeoAdminApi metadata collection utilities.

This module provides a service-specific wrapper around neo-commons metadata
utilities, handling NeoAdminApi-specific middleware integration and request context.
"""

from typing import Dict, Any
from neo_commons.utils.metadata import (
    MetadataCollector as BaseMetadataCollector,
    track_db_operation,
    track_cache_operation,
    get_basic_metadata,
    get_performance_summary,
)

# Re-export the base class and utilities
MetadataCollector = BaseMetadataCollector


def get_api_metadata(include_performance: bool = True) -> Dict[str, Any]:
    """Get metadata for API responses with NeoAdminApi middleware integration.
    
    Args:
        include_performance: Whether to include performance counters
        
    Returns:
        Dictionary with metadata from middleware and performance counters
    """
    try:
        # Import here to avoid circular imports
        from src.common.middleware.logging import get_request_context
        from src.common.utils import utc_now
        
        # Get context from existing logging middleware
        context = get_request_context()
        metadata = {}
        
        # Add request tracking (lightweight)
        if context.get('request_id'):
            metadata['request_id'] = context['request_id']
        
        # Add user context if available
        if context.get('user_id'):
            metadata['user_id'] = context['user_id']
        
        if context.get('tenant_id'):
            metadata['tenant_id'] = context['tenant_id']
        
        # Add performance data if enabled
        if include_performance:
            perf_data = MetadataCollector.get_performance_metadata()
            if perf_data:
                metadata.update(perf_data)
        
        # Add response timestamp
        metadata['timestamp'] = utc_now().isoformat()
        
        return metadata
        
    except Exception:
        # Never fail response due to metadata collection - fallback to basic metadata
        return get_basic_metadata(include_performance=include_performance)


def collect_request_metadata(include_performance: bool = True) -> Dict[str, Any]:
    """
    Collect comprehensive metadata from existing middleware.
    
    This is an alias for get_api_metadata for backward compatibility.
    
    Args:
        include_performance: Whether to include performance counters
        
    Returns:
        Dictionary with metadata or empty dict if collection fails
    """
    return get_api_metadata(include_performance)