"""
Security headers middleware for enhanced application security.

MIGRATED TO NEO-COMMONS: Now using neo-commons security middleware patterns.
Import compatibility maintained - all existing middleware configurations continue to work.
Enhanced with better environment detection, configurable app name, and improved CSP defaults.
"""
from typing import Callable, Dict, Optional, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# NEO-COMMONS IMPORT: Use neo-commons security middleware directly
from neo_commons.middleware.security import (
    SecurityHeadersMiddleware as NeoCommonsSecurityHeadersMiddleware,
    CORSSecurityMiddleware as NeoCommonsCORSSecurityMiddleware,
    RateLimitMiddleware as NeoCommonsRateLimitMiddleware,
)

# Import settings for backward compatibility
from src.common.config.settings import settings


class SecurityHeadersMiddleware(NeoCommonsSecurityHeadersMiddleware):
    """
    NeoAdminApi security headers middleware extending neo-commons SecurityHeadersMiddleware.
    
    Maintains backward compatibility while leveraging enhanced neo-commons features:
    - Auto-detection of production environment from NeoAdminApi settings
    - Custom server header branding for NeoAdmin
    - Integration with NeoAdminApi configuration patterns
    """
    
    def __init__(
        self,
        app,
        *,
        force_https: bool = None,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        content_security_policy: Optional[str] = None,
        frame_options: str = "DENY",
        content_type_options: bool = True,
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy: Optional[Dict[str, List[str]]] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        exclude_paths: Optional[List[str]] = None,
        is_production: bool = None
    ):
        # Integrate with NeoAdminApi settings for environment detection
        if is_production is None:
            is_production = getattr(settings, 'is_production', False)
        
        # Set force_https based on NeoAdminApi settings if not explicitly provided
        if force_https is None:
            force_https = is_production
        
        # Add custom headers for NeoAdmin branding if not provided
        if custom_headers is None:
            custom_headers = {}
        
        # Add NeoAdmin server header
        if "Server" not in custom_headers:
            custom_headers["Server"] = "NeoAdmin"
        
        # Initialize neo-commons middleware with NeoAdminApi-specific settings
        super().__init__(
            app,
            force_https=force_https,
            hsts_max_age=hsts_max_age,
            hsts_include_subdomains=hsts_include_subdomains,
            hsts_preload=hsts_preload,
            content_security_policy=content_security_policy,
            frame_options=frame_options,
            content_type_options=content_type_options,
            xss_protection=xss_protection,
            referrer_policy=referrer_policy,
            permissions_policy=permissions_policy,
            custom_headers=custom_headers,
            exclude_paths=exclude_paths,
            is_production=is_production
        )


class CORSSecurityMiddleware(NeoCommonsCORSSecurityMiddleware):
    """
    NeoAdminApi CORS security middleware extending neo-commons CORSSecurityMiddleware.
    
    Maintains backward compatibility while leveraging enhanced neo-commons features:
    - Improved security validation and error handling
    - Better logging and debugging capabilities
    - Integration with NeoAdminApi configuration patterns
    """
    
    def __init__(
        self,
        app,
        *,
        allowed_origins: List[str],
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        exposed_headers: List[str] = None,
        allow_credentials: bool = False,
        max_age: int = 600,
        strict_origin_check: bool = True
    ):
        # Use neo-commons CORS middleware with same interface
        super().__init__(
            app,
            allowed_origins=allowed_origins,
            allowed_methods=allowed_methods,
            allowed_headers=allowed_headers,
            exposed_headers=exposed_headers,
            allow_credentials=allow_credentials,
            max_age=max_age,
            strict_origin_check=strict_origin_check
        )


class RateLimitMiddleware(NeoCommonsRateLimitMiddleware):
    """
    NeoAdminApi rate limiting middleware extending neo-commons RateLimitMiddleware.
    
    Maintains backward compatibility while leveraging enhanced neo-commons features:
    - Better rate limiting algorithms and performance
    - Improved error responses and logging
    - Integration with NeoAdminApi configuration patterns
    """
    
    def __init__(
        self,
        app,
        *,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        exclude_paths: List[str] = None
    ):
        # Use neo-commons rate limit middleware with same interface
        super().__init__(
            app,
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            exclude_paths=exclude_paths
        )


# Ensure all required imports are available for backward compatibility
__all__ = [
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware", 
    "RateLimitMiddleware"
]