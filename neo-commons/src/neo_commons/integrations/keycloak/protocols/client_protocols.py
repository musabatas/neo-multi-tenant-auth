"""
Protocol definitions for Keycloak client operations.

Provides protocol interfaces for token validation and HTTP client operations.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any


@runtime_checkable
class TokenValidationConfigProtocol(Protocol):
    """Protocol for token validation configuration."""
    
    def get_jwt_algorithm(self) -> str:
        """Get JWT algorithm for validation."""
        ...
    
    def get_jwt_audience(self) -> Optional[str]:
        """Get expected JWT audience."""
        ...
    
    def is_jwt_audience_verification_enabled(self) -> bool:
        """Check if audience verification is enabled."""
        ...
    
    def should_fallback_without_audience(self) -> bool:
        """Check if fallback without audience is allowed."""
        ...
    
    def is_debug_claims_enabled(self) -> bool:
        """Check if debug claims logging is enabled."""
        ...


@runtime_checkable
class HttpClientProtocol(Protocol):
    """Protocol for HTTP client operations."""
    
    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Make POST request."""
        ...
    
    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Make GET request."""
        ...
    
    async def put(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Make PUT request."""
        ...
    
    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        auth: Optional[tuple] = None
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        ...