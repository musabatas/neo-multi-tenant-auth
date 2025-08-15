"""
Base models for API requests and responses.

MIGRATED TO NEO-COMMONS: Now using neo-commons base models with NeoAdminApi-specific extensions.
Import compatibility maintained - all existing imports continue to work.
"""
from typing import Optional, Any, Dict, List, TypeVar, Generic
from datetime import datetime
from neo_commons.utils.datetime import utc_now

# NEO-COMMONS IMPORT: Use neo-commons base models as foundation
from neo_commons.models import (
    # Base schemas and mixins
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
    SoftDeleteMixin,
    AuditMixin,
    # Enums
    StatusEnum,
    SortOrder,
    HealthStatus,
    # API responses
    APIResponse as NeoCommonsAPIResponse,
    # Health check models
    ServiceHealth,
    HealthCheckResponse as NeoCommonsHealthCheckResponse,
    # Pagination models
    PaginationParams as NeoCommonsPaginationParams,
    PaginatedResponse as NeoCommonsPaginatedResponse,
)

# Type variable for generic responses
T = TypeVar('T')


class PaginationParams(NeoCommonsPaginationParams):
    """
    NeoAdminApi pagination parameters extending neo-commons.
    
    Maintains backward compatibility while leveraging neo-commons infrastructure.
    """
    pass


class PaginatedResponse(NeoCommonsPaginatedResponse[T]):
    """
    NeoAdminApi paginated response extending neo-commons.
    
    Maintains backward compatibility while leveraging neo-commons infrastructure.
    """
    pass


class APIResponse(NeoCommonsAPIResponse[T]):
    """
    NeoAdminApi API response extending neo-commons.
    
    Adds NeoAdminApi-specific metadata collection capabilities.
    """
    
    @classmethod
    def _collect_request_metadata(cls) -> Dict[str, Any]:
        """Collect metadata using the NeoAdminApi metadata collection system."""
        try:
            from src.common.utils.metadata import get_api_metadata
            return get_api_metadata(include_performance=True)
        except Exception:
            # Never fail the response due to metadata collection issues
            return {}


class HealthCheckResponse(NeoCommonsHealthCheckResponse):
    """
    NeoAdminApi health check response extending neo-commons.
    
    Uses NeoAdminApi's utc_now for timestamp generation.
    """
    timestamp: datetime = utc_now()  # Use NeoAdminApi's datetime utility


# Re-export all neo-commons models for backward compatibility
__all__ = [
    # Base schemas and mixins from neo-commons
    "BaseSchema",
    "TimestampMixin",
    "UUIDMixin", 
    "SoftDeleteMixin",
    "AuditMixin",
    
    # Enums from neo-commons
    "StatusEnum",
    "SortOrder",
    "HealthStatus",
    
    # NeoAdminApi-extended models
    "PaginationParams",
    "PaginatedResponse",
    "APIResponse",
    "HealthCheckResponse",
    
    # Direct neo-commons exports
    "ServiceHealth",
]