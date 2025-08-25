"""Organization request/response models.

Provides Pydantic models that can be used across services with override
capability for service-specific customizations.
"""

from .requests import (
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    UpdateOrganizationBrandingRequest,
    UpdateOrganizationAddressRequest,
    VerifyOrganizationRequest,
    OrganizationSearchRequest,
    OrganizationMetadataRequest,
    OrganizationSearchByMetadataRequest
)
from .responses import (
    OrganizationResponse,
    OrganizationSummaryResponse,
    OrganizationListResponse,
    OrganizationSearchResponse,
    OrganizationConfigResponse,
    OrganizationMetadataResponse
)

__all__ = [
    # Request models
    "CreateOrganizationRequest",
    "UpdateOrganizationRequest", 
    "UpdateOrganizationBrandingRequest",
    "UpdateOrganizationAddressRequest",
    "VerifyOrganizationRequest",
    "OrganizationSearchRequest",
    "OrganizationMetadataRequest",
    "OrganizationSearchByMetadataRequest",
    
    # Response models
    "OrganizationResponse",
    "OrganizationSummaryResponse",
    "OrganizationListResponse",
    "OrganizationSearchResponse", 
    "OrganizationConfigResponse",
    "OrganizationMetadataResponse",
]