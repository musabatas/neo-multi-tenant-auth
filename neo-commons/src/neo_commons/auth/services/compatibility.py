"""
Backward Compatibility Service Wrappers

Service wrappers maintaining backward compatibility for existing NeoAdminApi services while
providing protocol-based implementations for service independence.

These wrappers allow gradual migration from hardcoded dependencies to protocol-based
dependency injection without breaking existing code.
"""

from typing import Optional, Dict, Any, List, Union
from datetime import timedelta
from loguru import logger

from ..protocols import (
    TokenValidatorProtocol,
    PermissionCheckerProtocol,
    GuestAuthServiceProtocol,
    AuthConfigProtocol,
    CacheServiceProtocol,
    ValidationStrategy
)
from ...exceptions import UnauthorizedError, ForbiddenError, RateLimitError


class AuthServiceWrapper:
    """
    Backward compatibility wrapper for AuthService.
    
    Maintains the existing AuthService API while delegating to protocol-based
    implementations for service independence and testability.
    
    This allows NeoAdminApi to gradually migrate to protocol-based dependency
    injection without breaking existing code.
    """
    
    def __init__(
        self,
        token_validator: TokenValidatorProtocol,
        permission_checker: PermissionCheckerProtocol,
        auth_config: AuthConfigProtocol,
        cache_service: CacheServiceProtocol
    ):
        """
        Initialize authentication service wrapper.
        
        Args:
            token_validator: Token validation service
            permission_checker: Permission checking service
            auth_config: Authentication configuration
            cache_service: Cache service implementation
        """
        self.token_validator = token_validator
        self.permission_checker = permission_checker
        self.auth_config = auth_config
        self.cache = cache_service
        
        # Session cache patterns (matching source)
        self.SESSION_KEY = "auth:session:{session_id}"
        self.USER_SESSION_KEY = "auth:user:{user_id}:sessions"
        self.SESSION_TTL = 86400  # 24 hours
    
    async def authenticate(
        self,
        username: str,
        password: str,
        realm: Optional[str] = None,
        user_sync_callback = None
    ) -> Dict[str, Any]:
        """
        Authenticate user credentials with optional user synchronization.
        
        Args:
            username: User's username
            password: User's password
            realm: Authentication realm (optional)
            user_sync_callback: Optional callback for user database sync
            
        Returns:
            Authentication result with user data and tokens
            
        Raises:
            UnauthorizedError: Invalid credentials
        """
        # Use configured realm or default
        target_realm = realm or self.auth_config.default_realm
        
        try:
            # Delegate to protocol-based token validator for authentication
            auth_result = await self.token_validator.authenticate_user(
                username=username,
                password=password,
                realm=target_realm
            )
            
            # Get user data from authentication result
            user_data = auth_result.get("user_data", {})
            token_claims = auth_result.get("token_claims", {})
            
            # If user sync callback is provided, sync user to database
            synced_user = None
            if user_sync_callback:
                try:
                    synced_user = await user_sync_callback(user_data)
                except Exception as e:
                    logger.warning(f"User sync failed for {username}: {e}")
                    # Continue without sync - authentication still valid
            
            # Build user info (use synced user data if available)
            if synced_user:
                user_info = {
                    "id": synced_user.get("id"),
                    "username": synced_user.get("username"),
                    "email": synced_user.get("email"),
                    "first_name": synced_user.get("first_name"),
                    "last_name": synced_user.get("last_name"),
                    "display_name": synced_user.get("display_name"),
                    "is_active": synced_user.get("is_active", True),
                    "is_superadmin": synced_user.get("is_superadmin", False),
                    "external_user_id": user_data.get("external_user_id"),
                    "realm": target_realm,
                    "keycloak": user_data.get("metadata", {})
                }
            else:
                # Fallback to token data if no sync callback
                user_info = {
                    "id": user_data.get("external_user_id"),
                    "username": user_data.get("username"),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                    "display_name": user_data.get("display_name"),
                    "is_active": True,  # Assume active since user authenticated successfully
                    "external_user_id": user_data.get("external_user_id"),
                    "realm": target_realm,
                    "keycloak": user_data.get("metadata", {})
                }
            
            # Cache user session (maintaining existing pattern)
            session_id = f"session_{user_info['id']}_{int(token_claims.get('iat', 0))}"
            cache_key = self.SESSION_KEY.format(session_id=session_id)
            await self.cache.set(cache_key, user_info, ttl=self.SESSION_TTL)
            
            logger.info(f"User {username} authenticated successfully in realm {target_realm}")
            
            return {
                "user": user_info,
                "session_id": session_id,
                "access_token": auth_result.get("access_token"),
                "refresh_token": auth_result.get("refresh_token"),
                "token_type": auth_result.get("token_type", "Bearer"),
                "expires_in": auth_result.get("expires_in", 3600),
                "realm": target_realm,
                "authenticated_at": auth_result.get("authenticated_at")
            }
            
        except UnauthorizedError:
            raise
        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            raise UnauthorizedError(f"Authentication failed: {str(e)}")
    
    async def get_current_user(
        self,
        token: str,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get current user from token with optional caching.
        
        Args:
            token: Access token
            use_cache: Whether to use cached user data
            
        Returns:
            User information if token is valid, None otherwise
        """
        try:
            # Validate token using protocol-based validator
            token_data = await self.token_validator.validate_token(
                token=token,
                realm=self.auth_config.default_realm,
                strategy=ValidationStrategy.LOCAL,
                critical=False
            )
            
            user_id = token_data.get("sub", "")
            if not user_id:
                return None
            
            # Check cache first if enabled (maintaining existing pattern)
            if use_cache:
                cache_key = f"user:{user_id}:profile"
                cached_user = await self.cache.get(cache_key)
                if cached_user:
                    return cached_user
            
            # Build user profile from token data
            user_info = {
                "id": user_id,
                "username": token_data.get("preferred_username", ""),
                "email": token_data.get("email", ""),
                "first_name": token_data.get("given_name"),
                "last_name": token_data.get("family_name"),
                "display_name": token_data.get("name"),
                "realm": token_data.get("iss", "").split("/")[-1] if token_data.get("iss") else "",
                "is_active": True,
                "last_login": token_data.get("iat"),
                "permissions": []  # Will be loaded separately via permission service
            }
            
            # Cache user info if caching enabled
            if use_cache:
                cache_key = f"user:{user_id}:profile"
                await self.cache.set(cache_key, user_info, ttl=600)  # 10 minutes
            
            return user_info
            
        except Exception as e:
            print(f"Debug: Failed to get current user from token: {e}")
            return None
    
    async def logout(self, session_id: str) -> bool:
        """
        Logout user and invalidate session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if logout successful
        """
        try:
            # Remove session from cache (maintaining existing pattern)
            cache_key = self.SESSION_KEY.format(session_id=session_id)
            await self.cache.delete(cache_key)
            
            print(f"Session {session_id} logged out successfully")
            return True
            
        except Exception as e:
            print(f"Error: Failed to logout session {session_id}: {e}")
            return False


class PermissionServiceWrapper:
    """
    Backward compatibility wrapper for PermissionService.
    
    Maintains existing permission checking API while using protocol-based
    permission checking for service independence.
    """
    
    def __init__(
        self,
        permission_checker: PermissionCheckerProtocol,
        cache_service: CacheServiceProtocol
    ):
        """
        Initialize permission service wrapper.
        
        Args:
            permission_checker: Permission checking service
            cache_service: Cache service implementation
        """
        self.permission_checker = permission_checker
        self.cache = cache_service
    
    async def check_permission(
        self,
        user_id: str,
        permissions: Union[str, List[str]],
        scope: str = "platform",
        tenant_id: Optional[str] = None,
        any_of: bool = False
    ) -> bool:
        """
        Check if user has required permissions.
        
        Args:
            user_id: User identifier
            permissions: Permission code(s) to check
            scope: Permission scope
            tenant_id: Tenant context
            any_of: If True, requires ANY permission; if False, requires ALL
            
        Returns:
            True if user has required permissions
        """
        # Normalize permissions to list
        permission_list = [permissions] if isinstance(permissions, str) else permissions
        
        # Delegate to protocol-based permission checker
        return await self.permission_checker.check_permission(
            user_id=user_id,
            permissions=permission_list,
            scope=scope,
            tenant_id=tenant_id,
            any_of=any_of
        )
    
    async def get_user_permissions(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all permissions for a user.
        
        Args:
            user_id: User identifier
            tenant_id: Tenant context
            use_cache: Whether to use cached permissions
            
        Returns:
            List of user permissions
        """
        # Check cache first if enabled
        if use_cache:
            cache_key = f"permissions:user:{user_id}:tenant:{tenant_id or 'platform'}"
            cached_permissions = await self.cache.get(cache_key)
            if cached_permissions:
                return cached_permissions
        
        # Delegate to protocol-based permission checker
        permissions = await self.permission_checker.get_user_permissions(
            user_id=user_id,
            tenant_id=tenant_id
        )
        
        # Cache permissions if caching enabled
        if use_cache:
            cache_key = f"permissions:user:{user_id}:tenant:{tenant_id or 'platform'}"
            await self.cache.set(cache_key, permissions, ttl=600)  # 10 minutes
        
        return permissions


class GuestAuthServiceWrapper:
    """
    Backward compatibility wrapper for GuestAuthService.
    
    Maintains existing guest authentication API while using protocol-based
    services for implementation independence.
    """
    
    def __init__(
        self,
        guest_service: GuestAuthServiceProtocol,
        cache_service: CacheServiceProtocol
    ):
        """
        Initialize guest authentication service wrapper.
        
        Args:
            guest_service: Guest authentication service
            cache_service: Cache service implementation
        """
        self.guest_service = guest_service
        self.cache = cache_service
    
    async def get_or_create_guest_session(
        self,
        session_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get or create guest session.
        
        Args:
            session_token: Existing session token
            ip_address: Client IP address
            user_agent: Client user agent
            referrer: Request referrer
            
        Returns:
            Guest session data
            
        Raises:
            RateLimitError: If rate limits exceeded
        """
        # Delegate to protocol-based guest service
        return await self.guest_service.get_or_create_guest_session(
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            referrer=referrer
        )
    
    async def get_session_stats(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get guest session statistics.
        
        Args:
            session_token: Session token
            
        Returns:
            Session statistics if found
        """
        # Delegate to protocol-based guest service
        return await self.guest_service.get_session_stats(session_token)


# Simple default implementations for missing dependencies
class SimpleAuthConfig:
    """Simple default auth config implementation."""
    
    def __init__(self):
        import os
        self.default_realm = os.getenv("KEYCLOAK_ADMIN_REALM", "neo-admin")
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
        self.admin_client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "admin-api")
        self.admin_client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "admin-secret")
        # Note: These are only used for admin operations, not client authentication
        self.admin_username = os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin")
        self.admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin")
        self.jwt_algorithm = "RS256"
        self.jwt_verify_audience = False
        self.jwt_verify_issuer = False
        self.jwt_issuer = None
        self.jwt_audience = None

class SimplePermissionChecker:
    """Simple default permission checker implementation."""
    
    async def check_permission(self, user_id: str, permissions: list, scope: str = "platform", tenant_id: str = None, any_of: bool = False) -> bool:
        # Default implementation - always allow (for testing)
        return True
    
    async def get_user_permissions(self, user_id: str, tenant_id: str = None) -> List[Dict[str, Any]]:
        # Default implementation - return empty permissions
        return []

class SimpleCacheKeyProvider:
    """Simple default cache key provider implementation."""
    
    def get_introspection_cache_key(self, token_hash: str) -> str:
        return f"auth:token_introspection:{token_hash}"
    
    def get_public_key_cache_key(self, realm: str) -> str:
        return f"auth:public_key:{realm}"
    
    def get_revocation_cache_key(self, token_hash: str) -> str:
        return f"auth:revoked_token:{token_hash}"

# Factory functions for creating configured service wrappers
def create_auth_service(
    token_validator: Optional[TokenValidatorProtocol] = None,
    permission_checker: Optional[PermissionCheckerProtocol] = None,
    auth_config: Optional[AuthConfigProtocol] = None,
    cache_service: Optional[CacheServiceProtocol] = None
) -> AuthServiceWrapper:
    """
    Create configured AuthService wrapper with optional default implementations.
    
    If any parameters are None, will use simple default implementations.
    """
    # Import implementations that exist
    from ..implementations import DualStrategyTokenValidator, KeycloakAsyncClient
    from ...cache import CacheManager
    
    # Reduce verbose initialization logging
    
    try:
        # Create default implementations if not provided
        if auth_config is None:
            auth_config = SimpleAuthConfig()
        
        if cache_service is None:
            cache_service = CacheManager()
        
        if permission_checker is None:
            permission_checker = SimplePermissionChecker()
        
        if token_validator is None:
            # Create default KeycloakClient and TokenValidator
            cache_key_provider = SimpleCacheKeyProvider()
            
            keycloak_client = KeycloakAsyncClient(
                config=auth_config,
                cache_service=cache_service,
                cache_key_provider=cache_key_provider,
                default_realm=auth_config.default_realm
            )
            
            token_validator = DualStrategyTokenValidator(
                keycloak_client=keycloak_client,
                config=auth_config,
                cache_service=cache_service,
                cache_key_provider=cache_key_provider
            )
            logger.info("Created DualStrategyTokenValidator")
        
        return AuthServiceWrapper(
            token_validator, permission_checker, auth_config, cache_service
        )
        
    except Exception as e:
        logger.error(f"Failed to create auth service: {e}")
        raise


def create_permission_service(
    permission_checker: PermissionCheckerProtocol,
    cache_service: CacheServiceProtocol
) -> PermissionServiceWrapper:
    """Create configured PermissionService wrapper."""
    return PermissionServiceWrapper(permission_checker, cache_service)


def create_guest_auth_service(
    guest_service: GuestAuthServiceProtocol,
    cache_service: CacheServiceProtocol
) -> GuestAuthServiceWrapper:
    """Create configured GuestAuthService wrapper."""
    return GuestAuthServiceWrapper(guest_service, cache_service)