"""
User Identity Resolver for Neo-Commons

Provides user ID mapping between external authentication providers (e.g., Keycloak)
and internal platform user IDs with intelligent caching and fallback strategies.
"""
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from loguru import logger

from ..core import (
    AuthConfigProtocol,
    ExternalServiceError,
    UserNotFoundError,
)
from .protocols import UserIdentityResolverProtocol


@runtime_checkable
class AuthRepositoryProtocol(Protocol):
    """Protocol for authentication repository operations."""
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by platform user ID."""
        ...
    
    async def get_user_by_external_id(
        self, 
        provider: str, 
        external_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user by external provider ID."""
        ...


class DefaultUserIdentityResolver:
    """
    Default implementation of UserIdentityResolverProtocol.
    
    This implementation provides user ID mapping between external authentication
    providers and internal platform user IDs. It includes intelligent caching
    to minimize database lookups and supports multiple fallback strategies.
    
    Features:
    - Automatic detection of platform vs external user IDs
    - Redis caching with configurable TTL
    - Multiple authentication provider support
    - Graceful fallback when mappings are not found
    - Comprehensive error handling and logging
    """
    
    def __init__(
        self,
        auth_repository: AuthRepositoryProtocol,
        cache_service,  # TenantAwareCacheProtocol - avoiding import for now
        config: Optional[AuthConfigProtocol] = None
    ):
        """
        Initialize user identity resolver.
        
        Args:
            auth_repository: Repository for user data access
            cache_service: Cache service for performance optimization
            config: Optional configuration
        """
        self.auth_repo = auth_repository
        self.cache = cache_service
        self.config = config
        
        # Configuration with defaults
        self.default_ttl = 3600  # 1 hour
        self.cache_prefix = "user_identity"
        
        # Load from config if available
        if config:
            self.default_ttl = getattr(config, 'USER_IDENTITY_CACHE_TTL', 3600)
            self.cache_prefix = getattr(config, 'USER_IDENTITY_CACHE_PREFIX', 'user_identity')
        
        # Supported authentication providers
        self.supported_providers = ["keycloak", "oauth2", "saml"]
        
        logger.info(
            f"Initialized DefaultUserIdentityResolver with cache TTL: {self.default_ttl}s, "
            f"supported providers: {self.supported_providers}"
        )
    
    def _build_cache_key(self, provider: str, external_id: str) -> str:
        """Build cache key for user mapping."""
        return f"{self.cache_prefix}:mapping:{provider}:{external_id}"
    
    def _build_context_cache_key(self, user_id: str) -> str:
        """Build cache key for user context."""
        return f"{self.cache_prefix}:context:{user_id}"
    
    async def resolve_platform_user_id(
        self,
        external_provider: str,
        external_id: str,
        fallback_to_external: bool = True
    ) -> Optional[str]:
        """
        Resolve external authentication provider ID to platform user ID.
        
        This method implements a multi-layer lookup strategy:
        1. Check cache for existing mapping
        2. Query database for user by external ID
        3. Cache successful mappings
        4. Apply fallback strategy if configured
        
        Args:
            external_provider: Authentication provider name (e.g., "keycloak")
            external_id: External user ID from the provider
            fallback_to_external: If True, return external_id when no mapping found
            
        Returns:
            Platform user ID if mapping exists, external_id if fallback enabled, None otherwise
            
        Raises:
            ExternalServiceError: Provider lookup failed
        """
        if not external_provider or not external_id:
            logger.warning(f"Invalid input: provider='{external_provider}', external_id='{external_id}'")
            return external_id if fallback_to_external else None
        
        if external_provider not in self.supported_providers:
            logger.warning(f"Unsupported provider: {external_provider}")
            return external_id if fallback_to_external else None
        
        cache_key = self._build_cache_key(external_provider, external_id)
        
        try:
            # 1. Check cache first
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit: {external_provider}:{external_id} -> {cached_result}")
                return cached_result
            
            # 2. Query database
            logger.debug(f"Cache miss, querying database for {external_provider}:{external_id}")
            platform_user = await self.auth_repo.get_user_by_external_id(
                provider=external_provider,
                external_id=external_id
            )
            
            if platform_user:
                platform_user_id = platform_user['id']
                
                # 3. Cache successful mapping
                await self.cache.set(
                    cache_key, 
                    platform_user_id, 
                    ttl=self.default_ttl
                )
                
                logger.debug(f"Mapped {external_provider}:{external_id} -> {platform_user_id}")
                return platform_user_id
            
            # 4. Apply fallback strategy
            if fallback_to_external:
                # Cache the fallback decision to avoid repeated lookups
                await self.cache.set(
                    cache_key, 
                    external_id, 
                    ttl=300  # Shorter TTL for fallback cases
                )
                logger.debug(f"No mapping found, using fallback: {external_id}")
                return external_id
            
            logger.debug(f"No mapping found for {external_provider}:{external_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to resolve {external_provider}:{external_id}: {e}")
            raise ExternalServiceError(f"User ID resolution failed: {e}")
    
    async def resolve_user_context(
        self,
        user_id: str,
        provider_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resolve user ID to complete user context with platform metadata.
        
        This method attempts to determine if the provided user_id is already
        a platform user ID or needs mapping from an external provider.
        
        Algorithm:
        1. Check cache for existing context
        2. Try to fetch as platform user ID
        3. If not found, try mapping from external provider
        4. Build comprehensive context dictionary
        5. Cache result for future lookups
        
        Args:
            user_id: User ID (could be platform or external)
            provider_hint: Optional hint about the likely provider
            
        Returns:
            Dictionary containing user context and mapping information
            
        Raises:
            UserNotFoundError: User not found in any context
        """
        if not user_id:
            raise UserNotFoundError("User ID is required")
        
        context_cache_key = self._build_context_cache_key(user_id)
        
        try:
            # 1. Check cache first
            cached_context = await self.cache.get(context_cache_key)
            if cached_context:
                logger.debug(f"Context cache hit for user: {user_id}")
                return cached_context
            
            # 2. Try to fetch as platform user ID
            try:
                platform_user = await self.auth_repo.get_user_by_id(user_id)
                if platform_user:
                    context = {
                        "platform_user_id": user_id,
                        "external_user_id": platform_user.get("external_user_id"),
                        "provider": platform_user.get("external_auth_provider", "platform"),
                        "user_metadata": {
                            "id": platform_user.get("id"),
                            "email": platform_user.get("email"),
                            "username": platform_user.get("username"),
                            "is_active": platform_user.get("is_active", True)
                        },
                        "is_mapped": False  # Already platform user ID
                    }
                    
                    # Cache successful context
                    await self.cache.set(context_cache_key, context, ttl=self.default_ttl)
                    logger.debug(f"Resolved as platform user: {user_id}")
                    return context
                    
            except Exception as e:
                logger.debug(f"User {user_id} not found as platform user: {e}")
            
            # 3. Try mapping from external provider
            providers_to_try = [provider_hint] if provider_hint else self.supported_providers
            
            for provider in providers_to_try:
                if not provider:
                    continue
                    
                try:
                    platform_user_id = await self.resolve_platform_user_id(
                        external_provider=provider,
                        external_id=user_id,
                        fallback_to_external=False
                    )
                    
                    if platform_user_id and platform_user_id != user_id:
                        # Found mapping, get platform user details
                        platform_user = await self.auth_repo.get_user_by_id(platform_user_id)
                        if platform_user:
                            context = {
                                "platform_user_id": platform_user_id,
                                "external_user_id": user_id,
                                "provider": provider,
                                "user_metadata": {
                                    "id": platform_user.get("id"),
                                    "email": platform_user.get("email"),
                                    "username": platform_user.get("username"),
                                    "is_active": platform_user.get("is_active", True)
                                },
                                "is_mapped": True  # ID mapping was performed
                            }
                            
                            # Cache successful context
                            await self.cache.set(context_cache_key, context, ttl=self.default_ttl)
                            logger.debug(f"Resolved via {provider} mapping: {user_id} -> {platform_user_id}")
                            return context
                            
                except Exception as e:
                    logger.debug(f"Failed to resolve via {provider}: {e}")
                    continue
            
            # 4. No mapping found
            raise UserNotFoundError(f"User not found: {user_id}")
            
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to resolve user context for {user_id}: {e}")
            raise ExternalServiceError(f"User context resolution failed: {e}")
    
    async def cache_user_mapping(
        self,
        external_provider: str,
        external_id: str,
        platform_user_id: str,
        ttl: int = None
    ) -> None:
        """
        Cache user ID mapping for faster subsequent lookups.
        
        Args:
            external_provider: Authentication provider name
            external_id: External user ID
            platform_user_id: Platform user ID
            ttl: Cache time-to-live in seconds (uses default if None)
        """
        if not external_provider or not external_id or not platform_user_id:
            logger.warning("Invalid mapping data provided for caching")
            return
        
        cache_key = self._build_cache_key(external_provider, external_id)
        cache_ttl = ttl or self.default_ttl
        
        try:
            await self.cache.set(cache_key, platform_user_id, ttl=cache_ttl)
            logger.debug(f"Cached mapping: {external_provider}:{external_id} -> {platform_user_id}")
        except Exception as e:
            logger.warning(f"Failed to cache user mapping: {e}")
    
    async def invalidate_user_mapping(
        self,
        user_id: str,
        provider: Optional[str] = None
    ) -> None:
        """
        Invalidate cached user ID mappings.
        
        Args:
            user_id: User ID (platform or external)
            provider: Optional provider to limit invalidation scope
        """
        if not user_id:
            return
        
        try:
            # Invalidate context cache
            context_cache_key = self._build_context_cache_key(user_id)
            await self.cache.delete(context_cache_key)
            
            # Invalidate mapping caches
            if provider:
                # Invalidate specific provider mapping
                mapping_cache_key = self._build_cache_key(provider, user_id)
                await self.cache.delete(mapping_cache_key)
            else:
                # Invalidate all provider mappings for this user
                for prov in self.supported_providers:
                    mapping_cache_key = self._build_cache_key(prov, user_id)
                    await self.cache.delete(mapping_cache_key)
            
            logger.debug(f"Invalidated user mapping cache for: {user_id}")
            
        except Exception as e:
            logger.warning(f"Failed to invalidate user mapping cache: {e}")
    
    async def get_supported_providers(self) -> List[str]:
        """
        Get list of supported authentication providers.
        
        Returns:
            List of provider names
        """
        return self.supported_providers.copy()
    
    async def validate_user_exists(
        self,
        user_id: str,
        provider_hint: Optional[str] = None
    ) -> bool:
        """
        Validate that a user exists (either as platform user or via mapping).
        
        Args:
            user_id: User ID to validate
            provider_hint: Optional provider hint for external IDs
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            context = await self.resolve_user_context(user_id, provider_hint)
            return context is not None
        except UserNotFoundError:
            return False
        except Exception as e:
            logger.warning(f"Error validating user existence for {user_id}: {e}")
            return False


# Factory function for dependency injection
def create_user_identity_resolver(
    auth_repository: AuthRepositoryProtocol,
    cache_service,
    config: Optional[AuthConfigProtocol] = None
) -> DefaultUserIdentityResolver:
    """
    Create a user identity resolver instance.
    
    Args:
        auth_repository: Repository for user data access
        cache_service: Cache service implementation
        config: Optional configuration
        
    Returns:
        Configured DefaultUserIdentityResolver instance
    """
    return DefaultUserIdentityResolver(
        auth_repository=auth_repository,
        cache_service=cache_service,
        config=config
    )


__all__ = [
    "DefaultUserIdentityResolver",
    "AuthRepositoryProtocol",
    "create_user_identity_resolver",
]