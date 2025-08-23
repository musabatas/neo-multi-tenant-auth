"""
Security headers middleware for enhanced application security.

Service wrapper that imports from neo-commons and provides NeoAdminApi-specific
security functionality while maintaining backward compatibility.
"""
from typing import List

# Import from neo-commons
from neo_commons.middleware.security import (
    SecurityHeadersMiddleware as NeoSecurityHeadersMiddleware,
    CORSSecurityMiddleware,
    RateLimitMiddleware,
    SecurityConfig
)

# Import service-specific settings
from src.common.config.settings import settings


class AdminSecurityConfig:
    """Service-specific security configuration for NeoAdminApi."""
    
    @property
    def is_production(self) -> bool:
        return settings.is_production
    
    @property
    def is_development(self) -> bool:
        return settings.is_development


class SecurityHeadersMiddleware(NeoSecurityHeadersMiddleware):
    """
    Service wrapper for NeoAdminApi that extends neo-commons SecurityHeadersMiddleware.
    
    Provides NeoAdminApi-specific security functionality while maintaining
    full compatibility with existing code.
    """
    
    def __init__(
        self,
        app,
        *,
        force_https: bool = False,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        content_security_policy: str = None,
        frame_options: str = "DENY",
        content_type_options: bool = True,
        xss_protection: str = "1; mode=block",
        referrer_policy: str = "strict-origin-when-cross-origin",
        permissions_policy = None,
        custom_headers = None,
        exclude_paths: List[str] = None
    ):
        # Create service-specific configuration
        security_config = AdminSecurityConfig()
        
        # NeoAdminApi-specific defaults
        if exclude_paths is None:
            exclude_paths = ["/health", "/metrics", "/docs", "/openapi.json", "/swagger", "/redoc"]
        
        # Initialize with service configuration
        super().__init__(
            app,
            security_config=security_config,
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
            server_header="NeoAdmin"  # Service-specific server header
        )


# Re-export other classes for backward compatibility
__all__ = [
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware", 
    "RateLimitMiddleware"
]