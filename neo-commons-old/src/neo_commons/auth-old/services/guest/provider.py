"""
Guest Session Configuration Providers

Configurable providers for guest session business rules including TTL,
rate limits, and permissions.
"""
from typing import List, Protocol, runtime_checkable
from abc import ABC, abstractmethod


@runtime_checkable 
class GuestSessionProvider(Protocol):
    """Protocol for guest session configuration."""
    
    @property
    def session_ttl(self) -> int:
        """Session TTL in seconds."""
        ...
    
    @property
    def max_requests_per_session(self) -> int:
        """Maximum requests per session."""
        ...
    
    @property
    def max_requests_per_ip(self) -> int:
        """Maximum requests per IP per day."""
        ...
    
    def get_guest_permissions(self) -> List[str]:
        """Get default guest permissions."""
        ...


class DefaultGuestSessionProvider:
    """Default guest session configuration provider with standard settings."""
    
    def __init__(
        self,
        session_ttl: int = 3600,                    # 1 hour
        max_requests_per_session: int = 1000,       # 1K requests per session
        max_requests_per_ip: int = 5000,            # 5K requests per IP per day
        guest_permissions: List[str] = None
    ):
        """
        Initialize guest session provider.
        
        Args:
            session_ttl: Session lifetime in seconds
            max_requests_per_session: Request limit per session
            max_requests_per_ip: Request limit per IP per day
            guest_permissions: List of permissions for guest users
        """
        self._session_ttl = session_ttl
        self._max_requests_per_session = max_requests_per_session
        self._max_requests_per_ip = max_requests_per_ip
        self._guest_permissions = guest_permissions or ["reference_data:read"]
    
    @property
    def session_ttl(self) -> int:
        return self._session_ttl
    
    @property
    def max_requests_per_session(self) -> int:
        return self._max_requests_per_session
    
    @property
    def max_requests_per_ip(self) -> int:
        return self._max_requests_per_ip
    
    def get_guest_permissions(self) -> List[str]:
        return self._guest_permissions.copy()


class RestrictiveGuestSessionProvider(DefaultGuestSessionProvider):
    """Restrictive guest session provider for high-security environments."""
    
    def __init__(self):
        super().__init__(
            session_ttl=1800,                      # 30 minutes
            max_requests_per_session=100,          # 100 requests per session
            max_requests_per_ip=500,               # 500 requests per IP per day
            guest_permissions=["public_data:read"] # More restrictive permissions
        )


class LiberalGuestSessionProvider(DefaultGuestSessionProvider):
    """Liberal guest session provider for development/testing."""
    
    def __init__(self):
        super().__init__(
            session_ttl=7200,                      # 2 hours
            max_requests_per_session=5000,         # 5K requests per session
            max_requests_per_ip=50000,             # 50K requests per IP per day
            guest_permissions=[
                "reference_data:read",
                "public_content:read",
                "demo:access"
            ]
        )


def create_guest_session_provider(
    provider_type: str = "default",
    **kwargs
) -> GuestSessionProvider:
    """
    Factory function for creating guest session providers.
    
    Args:
        provider_type: Type of provider ("default", "restrictive", "liberal", "custom")
        **kwargs: Custom configuration for default provider
        
    Returns:
        Configured GuestSessionProvider instance
    """
    if provider_type == "restrictive":
        return RestrictiveGuestSessionProvider()
    elif provider_type == "liberal":
        return LiberalGuestSessionProvider()
    elif provider_type == "custom":
        return DefaultGuestSessionProvider(**kwargs)
    else:  # default
        return DefaultGuestSessionProvider()