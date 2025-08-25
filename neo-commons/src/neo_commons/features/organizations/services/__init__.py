"""Organization services.

Provides business logic services using single-responsibility principle.
Main OrganizationService acts as orchestrator for specialized services.
"""

# Main orchestrator service
from .organization_service import OrganizationService

# Specialized single-responsibility services
from .query_service import OrganizationQueryService
from .command_service import OrganizationCommandService
from .status_service import OrganizationStatusService
from .branding_service import OrganizationBrandingService
from .metadata_service import OrganizationMetadataService
from .notification_service import OrganizationNotificationService
from .validation_service import OrganizationValidationService

__all__ = [
    # Main orchestrator service (use this for full functionality)
    "OrganizationService",
    
    # Specialized services (use these for specific operations)
    "OrganizationQueryService",
    "OrganizationCommandService", 
    "OrganizationStatusService",
    "OrganizationBrandingService",
    "OrganizationMetadataService",
    "OrganizationNotificationService",
    "OrganizationValidationService",
]