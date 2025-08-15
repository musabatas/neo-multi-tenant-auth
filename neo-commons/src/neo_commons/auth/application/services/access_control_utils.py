"""
Access control utilities and helpers.

Provides common utilities for access control operations.
"""
from typing import Optional, List
from ...domain.entities.access_control import AccessLevel
from ...domain.value_objects.user_context import UserContext
from ...domain.value_objects.tenant_context import TenantContext


class AccessControlUtils:
    """Utility functions for access control operations."""
    
    @staticmethod
    def build_access_cache_key(
        user_id: str,
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel,
        tenant_id: Optional[str]
    ) -> str:
        """Build cache key for resource access."""
        tenant_part = f"{tenant_id}:" if tenant_id else "platform:"
        return f"access:{tenant_part}{user_id}:{resource_type}:{resource_id}:{access_level.value}"
    
    @staticmethod
    def can_perform_admin_operations(user_context: UserContext) -> bool:
        """Check if user can perform administrative operations."""
        return user_context.is_superadmin or user_context.user_type.value >= 3
    
    @staticmethod
    def validate_resource_access_params(
        resource_type: str,
        resource_id: str,
        access_level: AccessLevel
    ) -> bool:
        """Validate resource access parameters."""
        if not resource_type or not resource_type.strip():
            return False
        if not resource_id or not resource_id.strip():
            return False
        if not isinstance(access_level, AccessLevel):
            return False
        return True
    
    @staticmethod
    def is_ownership_operation(access_level: AccessLevel) -> bool:
        """Check if operation requires ownership."""
        return access_level == AccessLevel.OWNER
    
    @staticmethod
    def get_tenant_context_id(tenant_context: Optional[TenantContext]) -> Optional[str]:
        """Safely extract tenant ID from context."""
        return tenant_context.tenant_id if tenant_context else None
    
    @staticmethod
    def build_resource_cache_patterns(
        user_id: str,
        resource_type: str,
        resource_id: str,
        tenant_id: Optional[str]
    ) -> List[str]:
        """Build cache key patterns for invalidation."""
        tenant_part = f"{tenant_id}:" if tenant_id else "platform:"
        base_pattern = f"access:{tenant_part}{user_id}:{resource_type}:{resource_id}"
        
        # Return patterns for all access levels
        return [
            f"{base_pattern}:{level.value}"
            for level in AccessLevel
        ]