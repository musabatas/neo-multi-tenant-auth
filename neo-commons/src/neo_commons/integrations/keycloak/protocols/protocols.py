"""
Protocol definitions for Keycloak integration.

Provides protocol-based interfaces for flexible Keycloak integration.
"""
from typing import Protocol, runtime_checkable, Optional, Dict, Any, List
from datetime import timedelta


@runtime_checkable
class KeycloakConfigProtocol(Protocol):
    """Protocol for Keycloak configuration implementations."""
    
    @property
    def server_url(self) -> str:
        """Keycloak server URL."""
        ...
    
    @property
    def admin_realm(self) -> str:
        """Admin realm name."""
        ...
    
    @property
    def client_id(self) -> str:
        """Client ID for authentication."""
        ...
    
    @property
    def client_secret(self) -> str:
        """Client secret for authentication."""
        ...
    
    @property
    def admin_username(self) -> Optional[str]:
        """Admin username for admin operations."""
        ...
    
    @property
    def admin_password(self) -> Optional[str]:
        """Admin password for admin operations."""
        ...
    
    @property
    def connection_timeout(self) -> int:
        """Connection timeout in seconds."""
        ...
    
    @property
    def max_connections(self) -> int:
        """Maximum number of connections."""
        ...
    
    @property
    def verify_ssl(self) -> bool:
        """Whether to verify SSL certificates."""
        ...


@runtime_checkable
class HttpClientProtocol(Protocol):
    """Protocol for HTTP client implementations."""
    
    async def get(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        ...
    
    async def post(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        ...
    
    async def put(
        self, 
        url: str, 
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        ...
    
    async def delete(
        self, 
        url: str, 
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        ...
    
    async def close(self):
        """Close the HTTP client."""
        ...


@runtime_checkable
class KeycloakTokenProtocol(Protocol):
    """Protocol for token operations."""
    
    async def authenticate(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None,
        client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate user and get tokens."""
        ...
    
    async def introspect_token(
        self,
        token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Introspect token validity."""
        ...
    
    async def refresh_token(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refresh access token."""
        ...
    
    async def logout(
        self,
        refresh_token: str,
        realm: Optional[str] = None
    ) -> bool:
        """Logout user."""
        ...


@runtime_checkable
class KeycloakUserProtocol(Protocol):
    """Protocol for user management operations."""
    
    async def get_user_by_username(
        self,
        username: str,
        realm: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        ...
    
    async def create_or_update_user(
        self,
        user_data: Dict[str, Any],
        realm: Optional[str] = None,
        update_if_exists: bool = True
    ) -> Dict[str, Any]:
        """Create or update user."""
        ...
    
    async def set_user_password(
        self,
        user_id: str,
        password: str,
        realm: Optional[str] = None,
        temporary: bool = False
    ) -> bool:
        """Set user password."""
        ...


@runtime_checkable
class KeycloakRealmProtocol(Protocol):
    """Protocol for realm management operations."""
    
    async def create_realm(
        self,
        realm_name: str,
        realm_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new realm."""
        ...
    
    async def get_realm_public_key(
        self,
        realm: str
    ) -> str:
        """Get realm public key for token validation."""
        ...


@runtime_checkable
class KeycloakAdminProtocol(Protocol):
    """Protocol for admin operations."""
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Keycloak health."""
        ...
    
    async def get_client_statistics(self) -> Dict[str, Any]:
        """Get client usage statistics."""
        ...
    
    async def clear_cache(self, cache_type: Optional[str] = None) -> bool:
        """Clear Keycloak cache."""
        ...