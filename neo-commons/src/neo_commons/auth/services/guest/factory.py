"""
Guest Authentication Service Factory

Factory functions for creating guest authentication service instances with
proper dependency injection and configuration.
"""
from typing import Optional
from loguru import logger

from ...protocols import GuestAuthServiceProtocol
from ....cache.protocols import TenantAwareCacheProtocol
from ...rate_limiting import AuthRateLimitManager
from .service import DefaultGuestAuthService
from .provider import GuestSessionProvider, create_guest_session_provider


def create_guest_auth_service(
    cache_service: Optional[TenantAwareCacheProtocol] = None,
    session_provider: Optional[GuestSessionProvider] = None,
    rate_limiter: Optional[AuthRateLimitManager] = None,
    provider_type: str = "default",
    **provider_kwargs
) -> GuestAuthServiceProtocol:
    """
    Create guest authentication service instance with dependency injection.
    
    Args:
        cache_service: Cache service for session storage
        session_provider: Session configuration provider
        rate_limiter: Rate limiter for session and IP limits
        provider_type: Type of session provider if session_provider not provided
        **provider_kwargs: Additional arguments for session provider
        
    Returns:
        Configured GuestAuthService instance
    """
    # Create default cache service if not provided
    if cache_service is None:
        try:
            # Try to get cache service from neo-commons
            from ....cache import get_cache_manager
            cache_manager = get_cache_manager()
            # Wrap in tenant-aware cache service
            from ....cache.implementations.tenant_aware_cache import TenantAwareCacheService
            cache_service = TenantAwareCacheService(cache_manager)
            logger.info("Created default cache service for guest auth")
        except ImportError as e:
            logger.error(f"Failed to create default cache service: {e}")
            raise ValueError("Cache service is required for guest authentication")
    
    # Create session provider if not provided
    if session_provider is None:
        session_provider = create_guest_session_provider(
            provider_type=provider_type,
            **provider_kwargs
        )
        logger.info(f"Created {provider_type} session provider for guest auth")
    
    return DefaultGuestAuthService(
        cache_service=cache_service,
        session_provider=session_provider,
        rate_limiter=rate_limiter
    )


def create_default_guest_service(
    cache_service: TenantAwareCacheProtocol
) -> GuestAuthServiceProtocol:
    """
    Create guest service with default configuration.
    
    Args:
        cache_service: Cache service for session storage
        
    Returns:
        Default guest authentication service
    """
    return create_guest_auth_service(
        cache_service=cache_service,
        provider_type="default"
    )


def create_restrictive_guest_service(
    cache_service: TenantAwareCacheProtocol
) -> GuestAuthServiceProtocol:
    """
    Create guest service with restrictive configuration.
    
    Args:
        cache_service: Cache service for session storage
        
    Returns:
        Restrictive guest authentication service
    """
    return create_guest_auth_service(
        cache_service=cache_service,
        provider_type="restrictive"
    )


def create_liberal_guest_service(
    cache_service: TenantAwareCacheProtocol
) -> GuestAuthServiceProtocol:
    """
    Create guest service with liberal configuration.
    
    Args:
        cache_service: Cache service for session storage
        
    Returns:
        Liberal guest authentication service
    """
    return create_guest_auth_service(
        cache_service=cache_service,
        provider_type="liberal"
    )