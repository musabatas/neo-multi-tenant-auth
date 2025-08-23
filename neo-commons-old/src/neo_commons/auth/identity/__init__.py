"""
Identity Management Module for Neo-Commons

Provides sophisticated user identity resolution and mapping capabilities
for multi-tenant environments with external authentication providers.

Key Features:
- User ID mapping between external providers and platform IDs
- Intelligent caching with configurable TTL strategies
- Bulk mapping operations with parallel processing
- Multiple mapping strategies for conflict resolution
- Performance metrics and audit trails
- Support for Keycloak, OAuth2, and SAML providers
"""

# Core identity resolution
from .resolver import (
    DefaultUserIdentityResolver,
    AuthRepositoryProtocol,
    create_user_identity_resolver,
)

# Enhanced identity mapping
from .mapper import (
    DefaultUserIdentityMapper,
    MappingResult,
    BulkMappingResult,
    MappingStatus,
    MappingStrategy,
    create_user_identity_mapper,
)

# Protocol definitions
from .protocols import (
    UserIdentityResolverProtocol,
    UserIdentityMapperProtocol,
    IdentityTransformationProtocol,
    IdentityAuditProtocol,
)


# Factory functions for dependency injection
def create_identity_management_suite(
    auth_repository,
    cache_service,
    config=None
):
    """
    Create a complete identity management suite.
    
    Args:
        auth_repository: Repository for user data access
        cache_service: Cache service implementation
        config: Optional configuration
        
    Returns:
        Tuple of (resolver, mapper) instances
    """
    resolver = create_user_identity_resolver(
        auth_repository=auth_repository,
        cache_service=cache_service,
        config=config
    )
    
    mapper = create_user_identity_mapper(
        user_resolver=resolver,
        cache_service=cache_service,
        config=config
    )
    
    return resolver, mapper


def create_identity_resolver_with_mapping(
    auth_repository,
    cache_service,
    config=None
):
    """
    Create an identity resolver with enhanced mapping capabilities.
    
    Args:
        auth_repository: Repository for user data access
        cache_service: Cache service implementation
        config: Optional configuration
        
    Returns:
        DefaultUserIdentityMapper instance with full capabilities
    """
    resolver, mapper = create_identity_management_suite(
        auth_repository=auth_repository,
        cache_service=cache_service,
        config=config
    )
    
    return mapper




__all__ = [
    # Core implementations
    "DefaultUserIdentityResolver",
    "DefaultUserIdentityMapper",
    
    # Data structures
    "MappingResult",
    "BulkMappingResult",
    "MappingStatus",
    "MappingStrategy",
    "AuthRepositoryProtocol",
    
    # Protocols
    "UserIdentityResolverProtocol",
    "UserIdentityMapperProtocol",
    "IdentityTransformationProtocol",
    "IdentityAuditProtocol",
    
    # Factory functions
    "create_user_identity_resolver",
    "create_user_identity_mapper",
    "create_identity_management_suite",
    "create_identity_resolver_with_mapping",
]