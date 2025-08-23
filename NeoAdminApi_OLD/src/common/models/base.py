"""
Base models for API requests and responses.

Service wrapper for neo-commons base models with NeoAdminApi-specific functionality.
"""
from typing import Optional, Any, Dict, List

# Import all base models from neo-commons
from neo_commons.models.base import (
    BaseSchema,
    TimestampMixin,
    UUIDMixin,
    SoftDeleteMixin,
    AuditMixin,
    StatusEnum,
    SortOrder,
    PaginationParams,
    PaginatedResponse,
    APIResponse as BaseAPIResponse,
    HealthStatus,
    ServiceHealth,
    HealthCheckResponse,
    T
)


# Service-specific APIResponse with NeoAdminApi metadata collection
class APIResponse(BaseAPIResponse[T]):
    """Service wrapper for APIResponse with NeoAdminApi-specific metadata collection."""
    
    @classmethod
    def _collect_request_metadata(cls) -> Dict[str, Any]:
        """Collect metadata using the NeoAdminApi metadata collection system."""
        try:
            from src.common.utils.metadata import get_api_metadata
            return get_api_metadata(include_performance=True)
        except Exception:
            # Never fail the response due to metadata collection issues
            return {}