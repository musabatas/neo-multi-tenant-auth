"""
Identity Management Protocols for Neo-Commons

Protocol definitions for user identity resolution, mapping, and transformation
operations in multi-tenant environments with external authentication providers.
"""
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class UserIdentityResolverProtocol(Protocol):
    """Protocol for resolving user identity across different ID systems."""
    
    async def resolve_platform_user_id(
        self,
        external_provider: str,
        external_id: str,
        fallback_to_external: bool = True
    ) -> Optional[str]:
        """Resolve external authentication provider ID to platform user ID."""
        ...
    
    async def resolve_user_context(
        self,
        user_id: str,
        provider_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """Resolve user ID to complete user context with platform metadata."""
        ...
    
    async def cache_user_mapping(
        self,
        external_provider: str,
        external_id: str,
        platform_user_id: str,
        ttl: int = None
    ) -> None:
        """Cache user ID mapping for faster subsequent lookups."""
        ...
    
    async def invalidate_user_mapping(
        self,
        user_id: str,
        provider: Optional[str] = None
    ) -> None:
        """Invalidate cached user ID mappings."""
        ...
    
    async def get_supported_providers(self) -> List[str]:
        """Get list of supported authentication providers."""
        ...
    
    async def validate_user_exists(
        self,
        user_id: str,
        provider_hint: Optional[str] = None
    ) -> bool:
        """Validate that a user exists (either as platform user or via mapping)."""
        ...


@runtime_checkable
class UserIdentityMapperProtocol(Protocol):
    """Protocol for advanced user identity mapping operations."""
    
    async def map_user_identity(
        self,
        user_id: str,
        provider: Optional[str] = None,
        strategy: str = "prefer_platform",
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Map a single user identity with advanced options."""
        ...
    
    async def map_user_identities_bulk(
        self,
        user_ids: List[str],
        provider: Optional[str] = None,
        strategy: str = "prefer_platform",
        use_cache: bool = True,
        parallel: bool = True
    ) -> Dict[str, Any]:
        """Map multiple user identities efficiently."""
        ...
    
    async def invalidate_mapping_cache(
        self,
        user_id: str,
        provider: Optional[str] = None
    ) -> None:
        """Invalidate cached mapping for a user."""
        ...
    
    async def get_mapping_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for identity mapping operations."""
        ...
    
    async def reset_performance_metrics(self) -> None:
        """Reset performance metrics counters."""
        ...


@runtime_checkable
class IdentityTransformationProtocol(Protocol):
    """Protocol for user identity transformations and migrations."""
    
    async def transform_user_identity(
        self,
        source_id: str,
        source_provider: str,
        target_provider: str,
        transformation_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Transform user identity from one provider format to another."""
        ...
    
    async def migrate_user_identities(
        self,
        user_mappings: List[Dict[str, str]],
        migration_strategy: str = "safe"
    ) -> Dict[str, Any]:
        """Migrate multiple user identities between providers."""
        ...
    
    async def validate_identity_transformation(
        self,
        original_context: Dict[str, Any],
        transformed_context: Dict[str, Any]
    ) -> bool:
        """Validate that identity transformation preserved essential data."""
        ...


@runtime_checkable
class IdentityAuditProtocol(Protocol):
    """Protocol for auditing identity operations."""
    
    async def log_identity_access(
        self,
        user_id: str,
        operation: str,
        provider: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log identity access for audit trail."""
        ...
    
    async def log_identity_mapping(
        self,
        source_id: str,
        target_id: str,
        provider: str,
        operation_type: str,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log identity mapping operations."""
        ...
    
    async def get_identity_audit_trail(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get audit trail for user identity operations."""
        ...


__all__ = [
    "UserIdentityResolverProtocol",
    "UserIdentityMapperProtocol",
    "IdentityTransformationProtocol",
    "IdentityAuditProtocol",
]