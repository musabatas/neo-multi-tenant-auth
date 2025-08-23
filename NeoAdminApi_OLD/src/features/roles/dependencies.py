"""
Dependency injection for roles feature.
"""

from src.features.roles.services.role_service import RoleService


def get_role_service() -> RoleService:
    """
    Create and return a RoleService instance.
    
    Returns:
        RoleService: Service instance for role operations
    """
    return RoleService()