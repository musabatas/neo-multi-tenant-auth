"""Organizations feature package.

Complete organization management feature with dynamic database support,
protocol-based dependency injection, caching, and service orchestration.
Follows DRY principles and integrates with existing neo-commons infrastructure.
"""

from .entities.organization import Organization
from .entities.protocols import (
    OrganizationRepository,
    OrganizationConfigResolver,
    OrganizationNotificationService,
    OrganizationValidationService
)
from .repositories import (
    OrganizationDatabaseRepository
)
from .services import OrganizationService
from .models import (
    # Request models
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    UpdateOrganizationBrandingRequest,
    UpdateOrganizationAddressRequest,
    VerifyOrganizationRequest,
    OrganizationSearchRequest,
    OrganizationMetadataRequest,
    OrganizationSearchByMetadataRequest,
    
    # Response models
    OrganizationResponse,
    OrganizationSummaryResponse,
    OrganizationListResponse,
    OrganizationSearchResponse,
    OrganizationConfigResponse,
    OrganizationMetadataResponse
)
from .utils.validation import OrganizationValidationRules
from .routers import (
    organization_router,
    organization_admin_router,
    get_organization_repository,
    get_organization_service,
    get_basic_organization_service,
    get_admin_organization_service
)

__all__ = [
    # Entities
    "Organization",
    
    # Protocols
    "OrganizationRepository",
    "OrganizationConfigResolver",
    "OrganizationNotificationService",
    "OrganizationValidationService",
    
    # Repositories
    "OrganizationDatabaseRepository",
    
    # Services
    "OrganizationService",
    
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
    
    # Utils
    "OrganizationValidationRules",
    
    # Routers
    "organization_router",
    "organization_admin_router",
    
    # Router dependencies
    "get_organization_repository",
    "get_organization_service",
    "get_basic_organization_service",
    "get_admin_organization_service",
]