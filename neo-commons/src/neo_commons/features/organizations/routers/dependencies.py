"""Organization router dependencies.

Provides dependency injection for organization routers using existing
neo-commons infrastructure without duplicating service setup logic.

Note: This module provides basic dependencies. Services should extend
these dependencies with their own implementations for full functionality.
"""

from typing import Optional


# Note: Services will need to provide their own database dependencies
# These are placeholder functions that services should override

def get_database_repository():
    """Placeholder for database repository dependency.
    
    Services should override this dependency to provide their actual
    database repository implementation.
    """
    raise NotImplementedError(
        "Services must provide their own database repository dependency"
    )


def get_organization_repository():
    """Placeholder for organization repository dependency.
    
    Services should override this to provide configured repository.
    """
    raise NotImplementedError(
        "Services must provide their own organization repository dependency"
    )


def get_organization_service():
    """Placeholder for organization service dependency.
    
    Services should override this to provide configured service.
    """
    raise NotImplementedError(
        "Services must provide their own organization service dependency"
    )


# For services to import and use
def get_basic_organization_service():
    """Placeholder for basic organization service dependency."""
    raise NotImplementedError(
        "Services must provide their own organization service dependency"
    )


def get_admin_organization_service():
    """Placeholder for admin organization service dependency.""" 
    raise NotImplementedError(
        "Services must provide their own admin organization service dependency"
    )


# Organization cache removed - database queries are sufficient for occasional access patterns