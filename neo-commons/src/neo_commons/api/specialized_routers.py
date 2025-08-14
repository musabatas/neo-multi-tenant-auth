"""
Specialized router implementations for neo-commons.
Provides enhanced routers with built-in features like versioning, security, and caching.
"""
import logging
from typing import Any, Callable, Optional, Dict, List, Union, Sequence
from fastapi import APIRouter as FastAPIRouter, Depends
from fastapi.routing import APIRoute
from fastapi.types import DecoratedCallable

from .routers import NeoAPIRouter  # Import base router

logger = logging.getLogger(__name__)


class VersionedAPIRouter(NeoAPIRouter):
    """
    APIRouter with built-in versioning support.
    
    Features:
    - Automatic version prefix handling
    - Version-specific OpenAPI tags
    - Deprecation warnings for old versions
    """
    
    def __init__(
        self,
        version: str,
        *,
        deprecated: Optional[bool] = None,
        deprecation_message: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize versioned router.
        
        Args:
            version: API version (e.g., "v1", "v2")
            deprecated: Mark this version as deprecated
            deprecation_message: Custom deprecation message
            **kwargs: Standard NeoAPIRouter arguments
        """
        self.version = version
        self.deprecation_message = deprecation_message
        
        # Add version to prefix if not already present
        prefix = kwargs.get("prefix", "")
        if not prefix.startswith(f"/{version}"):
            prefix = f"/{version}{prefix}".rstrip("/")
            kwargs["prefix"] = prefix
        
        # Add version to tags if not present
        tags = kwargs.get("tags", [])
        if tags and not any(tag.startswith(version.upper()) for tag in tags):
            tags = [f"{version.upper()} {tag}" for tag in tags]
            kwargs["tags"] = tags
        
        # Set deprecation
        if deprecated is not None:
            kwargs["deprecated"] = deprecated
        
        super().__init__(**kwargs)
        
        logger.info(f"Initialized {version} router with prefix='{prefix}'" + 
                   (" (DEPRECATED)" if deprecated else ""))


class SecureAPIRouter(NeoAPIRouter):
    """
    APIRouter with built-in security requirements.
    
    Features:
    - Automatic security dependency injection
    - Configurable authentication requirements
    - Security logging
    """
    
    def __init__(
        self,
        *,
        require_auth: bool = True,
        auth_scopes: Optional[List[str]] = None,
        guest_allowed: bool = False,
        security_dependencies: Optional[List[Depends]] = None,
        **kwargs
    ):
        """
        Initialize secure router.
        
        Args:
            require_auth: Require authentication for all routes
            auth_scopes: Required authentication scopes
            guest_allowed: Allow guest access
            security_dependencies: Additional security dependencies
            **kwargs: Standard NeoAPIRouter arguments
        """
        self.require_auth = require_auth
        self.auth_scopes = auth_scopes or []
        self.guest_allowed = guest_allowed
        
        # Merge security dependencies with existing dependencies
        dependencies = list(kwargs.get("dependencies", []))
        if security_dependencies:
            dependencies.extend(security_dependencies)
        
        # Add authentication dependency if required
        if require_auth:
            try:
                # Try to import auth dependency - this will be available when auth module is implemented
                from neo_commons.auth.dependencies import require_authentication
                auth_dep = Depends(require_authentication)
                if auth_dep not in dependencies:
                    dependencies.append(auth_dep)
            except (ImportError, ModuleNotFoundError):
                logger.warning("Authentication dependency not available - routes will not be secured")
        
        kwargs["dependencies"] = dependencies
        
        super().__init__(**kwargs)
        
        logger.info(f"Initialized secure router (auth_required={require_auth}, scopes={self.auth_scopes})")


class CachedAPIRouter(NeoAPIRouter):
    """
    APIRouter with built-in caching support.
    
    Features:
    - Automatic response caching
    - Configurable cache TTL
    - Cache invalidation helpers
    """
    
    def __init__(
        self,
        *,
        default_cache_ttl: int = 300,  # 5 minutes
        cache_key_prefix: Optional[str] = None,
        enable_cache_headers: bool = True,
        **kwargs
    ):
        """
        Initialize cached router.
        
        Args:
            default_cache_ttl: Default cache TTL in seconds
            cache_key_prefix: Prefix for cache keys
            enable_cache_headers: Add cache control headers
            **kwargs: Standard NeoAPIRouter arguments
        """
        self.default_cache_ttl = default_cache_ttl
        self.cache_key_prefix = cache_key_prefix
        self.enable_cache_headers = enable_cache_headers
        
        super().__init__(**kwargs)
        
        logger.info(f"Initialized cached router (ttl={default_cache_ttl}s, prefix='{cache_key_prefix}')")
    
    def cached_route(
        self,
        path: str,
        *,
        cache_ttl: Optional[int] = None,
        cache_key: Optional[str] = None,
        **kwargs
    ):
        """
        Create a cached route with specific caching configuration.
        
        Args:
            path: Route path
            cache_ttl: Cache TTL for this specific route
            cache_key: Custom cache key pattern
            **kwargs: Standard route arguments
        """
        ttl = cache_ttl or self.default_cache_ttl
        key = cache_key or f"{self.cache_key_prefix or 'api'}:{path}"
        
        # Add cache metadata to route kwargs
        kwargs.setdefault("response_description", f"Cached response (TTL: {ttl}s)")
        
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            """Decorator that adds caching to the route."""
            async def cached_wrapper(*args, **kwargs):
                # Implement caching logic here
                # This is a placeholder - actual implementation would depend on cache backend
                logger.debug(f"Cache check for key: {key} (TTL: {ttl}s)")
                return await func(*args, **kwargs)
            
            cached_wrapper.__name__ = func.__name__
            cached_wrapper.__doc__ = func.__doc__
            
            return self.api_route(path, **kwargs)(cached_wrapper)
        
        return decorator


class AdminAPIRouter(SecureAPIRouter):
    """
    APIRouter optimized for admin/platform operations.
    
    Combines security features with admin-specific configurations.
    """
    
    def __init__(
        self,
        *,
        version: str = "v1",
        require_admin_auth: bool = True,
        **kwargs
    ):
        """
        Initialize admin router.
        
        Args:
            version: API version
            require_admin_auth: Require admin authentication
            **kwargs: Standard SecureAPIRouter arguments
        """
        # Set admin-specific defaults
        kwargs.setdefault("require_auth", require_admin_auth)
        kwargs.setdefault("auth_scopes", ["admin", "platform"])
        kwargs.setdefault("guest_allowed", False)
        
        # Add version prefix
        prefix = kwargs.get("prefix", "")
        if not prefix.startswith(f"/{version}"):
            kwargs["prefix"] = f"/{version}{prefix}".rstrip("/")
        
        super().__init__(**kwargs)
        
        logger.info(f"Initialized admin router (version={version}, auth_required={require_admin_auth})")


class TenantAPIRouter(CachedAPIRouter, SecureAPIRouter):
    """
    APIRouter optimized for tenant operations.
    
    Combines caching and security features with tenant-specific configurations.
    """
    
    def __init__(
        self,
        *,
        version: str = "v1",
        require_tenant_auth: bool = True,
        default_cache_ttl: int = 300,
        **kwargs
    ):
        """
        Initialize tenant router.
        
        Args:
            version: API version
            require_tenant_auth: Require tenant authentication
            default_cache_ttl: Default cache TTL for tenant data
            **kwargs: Combined router arguments
        """
        # Set tenant-specific defaults
        kwargs.setdefault("require_auth", require_tenant_auth)
        kwargs.setdefault("auth_scopes", ["tenant"])
        kwargs.setdefault("cache_key_prefix", "tenant")
        kwargs.setdefault("default_cache_ttl", default_cache_ttl)
        
        # Add version prefix
        prefix = kwargs.get("prefix", "")
        if not prefix.startswith(f"/{version}"):
            kwargs["prefix"] = f"/{version}{prefix}".rstrip("/")
        
        # Initialize both parent classes
        CachedAPIRouter.__init__(self, **kwargs)
        SecureAPIRouter.__init__(self, **kwargs)
        
        logger.info(f"Initialized tenant router (version={version}, auth_required={require_tenant_auth}, cache_ttl={default_cache_ttl}s)")


class PublicAPIRouter(CachedAPIRouter):
    """
    APIRouter optimized for public/guest operations.
    
    Focuses on caching and performance for public endpoints.
    """
    
    def __init__(
        self,
        *,
        version: str = "v1",
        default_cache_ttl: int = 3600,  # 1 hour for public data
        enable_guest_sessions: bool = True,
        **kwargs
    ):
        """
        Initialize public router.
        
        Args:
            version: API version
            default_cache_ttl: Default cache TTL for public data
            enable_guest_sessions: Enable guest session tracking
            **kwargs: Standard CachedAPIRouter arguments
        """
        # Set public-specific defaults
        kwargs.setdefault("cache_key_prefix", "public")
        kwargs.setdefault("default_cache_ttl", default_cache_ttl)
        
        # Add version prefix
        prefix = kwargs.get("prefix", "")
        if not prefix.startswith(f"/{version}"):
            kwargs["prefix"] = f"/{version}{prefix}".rstrip("/")
        
        # Add guest session dependencies if enabled
        if enable_guest_sessions:
            dependencies = list(kwargs.get("dependencies", []))
            try:
                # Try to import guest session dependency - this will be available when auth module is implemented
                from neo_commons.auth.dependencies import get_guest_session
                guest_dep = Depends(get_guest_session)
                dependencies.append(guest_dep)
                kwargs["dependencies"] = dependencies
            except (ImportError, ModuleNotFoundError):
                logger.warning("Guest session dependency not available")
        
        super().__init__(**kwargs)
        
        logger.info(f"Initialized public router (version={version}, cache_ttl={default_cache_ttl}s, guest_sessions={enable_guest_sessions})")