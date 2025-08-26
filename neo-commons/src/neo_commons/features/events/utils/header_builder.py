"""
Webhook Header Builder

Provides centralized HTTP header construction for webhook delivery and verification,
eliminating duplication between service and adapter layers while ensuring consistency
across all webhook-related HTTP operations.
"""

from typing import Dict, Optional, Any
from enum import Enum


class HeaderContext(Enum):
    """Context for header construction."""
    DELIVERY = "delivery"
    VERIFICATION = "verification"
    HEALTH_CHECK = "health_check"
    CONNECTIVITY_TEST = "connectivity_test"


class WebhookHeaderBuilder:
    """Centralized builder for webhook HTTP headers.
    
    Eliminates duplication between service and adapter layers by providing
    a single source of truth for header construction with context-aware customization.
    """
    
    # Standard headers used across all webhook operations
    _BASE_HEADERS = {
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Accept-Encoding": "gzip, deflate"
    }
    
    # Context-specific user agent strings
    _USER_AGENTS = {
        HeaderContext.DELIVERY: "NeoMultiTenant-Webhooks/1.0",
        HeaderContext.VERIFICATION: "NeoMultiTenant-Webhooks/1.0 (Verification)",
        HeaderContext.HEALTH_CHECK: "NeoMultiTenant-Webhooks/1.0 (Health-Check)",
        HeaderContext.CONNECTIVITY_TEST: "NeoMultiTenant-Webhooks/1.0 (Connectivity-Test)"
    }
    
    # Context-specific special headers
    _CONTEXT_HEADERS = {
        HeaderContext.VERIFICATION: {
            "X-Neo-Verification": "true"
        },
        HeaderContext.HEALTH_CHECK: {
            "X-Neo-Health-Check": "true"
        },
        HeaderContext.CONNECTIVITY_TEST: {
            "X-Neo-Connectivity-Test": "true"
        }
    }
    
    @classmethod
    def build_headers(
        cls,
        context: HeaderContext,
        custom_headers: Optional[Dict[str, str]] = None,
        signature: Optional[str] = None,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, str]:
        """Build HTTP headers for webhook operations.
        
        Args:
            context: Context for header construction (delivery, verification, etc.)
            custom_headers: Custom headers from endpoint configuration
            signature: HMAC signature for webhook delivery
            tenant_id: Tenant ID for multi-tenant context
            request_id: Request ID for tracing
            **kwargs: Additional context-specific parameters
            
        Returns:
            Dictionary of HTTP headers ready for HTTP requests
        """
        # Start with base headers
        headers = cls._BASE_HEADERS.copy()
        
        # Add context-appropriate user agent
        headers["User-Agent"] = cls._USER_AGENTS.get(
            context, 
            cls._USER_AGENTS[HeaderContext.DELIVERY]
        )
        
        # Add context-specific headers
        context_headers = cls._CONTEXT_HEADERS.get(context, {})
        headers.update(context_headers)
        
        # Add signature if present (for delivery context)
        if signature and context == HeaderContext.DELIVERY:
            # Use configurable signature header name, fallback to X-Neo-Signature
            signature_header = kwargs.get('signature_header_name', 'X-Neo-Signature')
            headers[signature_header] = signature
        
        # Add tenant context headers
        if tenant_id:
            headers["X-Neo-Tenant-ID"] = tenant_id
        
        # Add request tracing headers
        if request_id:
            headers["X-Neo-Request-ID"] = request_id
        
        # Add custom headers from endpoint (with conflict resolution)
        if custom_headers:
            # Custom headers can override defaults except protected headers
            protected_headers = {"content-type", "user-agent", "connection"}
            
            for key, value in custom_headers.items():
                # Allow override of non-protected headers
                if key.lower() not in protected_headers:
                    headers[key] = value
                else:
                    # Protected headers are prefixed to avoid conflicts
                    headers[f"X-Endpoint-{key}"] = value
        
        # Add context-specific customizations
        cls._add_context_customizations(headers, context, kwargs)
        
        return headers
    
    @classmethod
    def build_delivery_headers(
        cls,
        custom_headers: Optional[Dict[str, str]] = None,
        signature: Optional[str] = None,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        signature_header_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Build headers specifically for webhook delivery.
        
        Args:
            custom_headers: Custom headers from endpoint configuration
            signature: HMAC signature for payload verification
            tenant_id: Tenant ID for multi-tenant context
            request_id: Request ID for tracing
            signature_header_name: Custom signature header name (defaults to X-Neo-Signature)
            
        Returns:
            Headers optimized for webhook delivery
        """
        return cls.build_headers(
            context=HeaderContext.DELIVERY,
            custom_headers=custom_headers,
            signature=signature,
            tenant_id=tenant_id,
            request_id=request_id,
            signature_header_name=signature_header_name
        )
    
    @classmethod
    def build_verification_headers(
        cls,
        custom_headers: Optional[Dict[str, str]] = None,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        verification_level: Optional[str] = None
    ) -> Dict[str, str]:
        """Build headers specifically for endpoint verification.
        
        Args:
            custom_headers: Custom headers from endpoint configuration
            tenant_id: Tenant ID for multi-tenant context
            request_id: Request ID for tracing
            verification_level: Level of verification (basic, standard, comprehensive)
            
        Returns:
            Headers optimized for endpoint verification
        """
        kwargs = {}
        if verification_level:
            kwargs["verification_level"] = verification_level
        
        return cls.build_headers(
            context=HeaderContext.VERIFICATION,
            custom_headers=custom_headers,
            tenant_id=tenant_id,
            request_id=request_id,
            **kwargs
        )
    
    @classmethod
    def build_health_check_headers(
        cls,
        request_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Build headers specifically for health check requests.
        
        Args:
            request_id: Request ID for tracing
            
        Returns:
            Headers optimized for health checks
        """
        return cls.build_headers(
            context=HeaderContext.HEALTH_CHECK,
            request_id=request_id
        )
    
    @classmethod
    def build_connectivity_test_headers(
        cls,
        request_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Build headers specifically for connectivity testing.
        
        Args:
            request_id: Request ID for tracing
            
        Returns:
            Headers optimized for connectivity tests
        """
        return cls.build_headers(
            context=HeaderContext.CONNECTIVITY_TEST,
            request_id=request_id
        )
    
    @classmethod
    def _add_context_customizations(
        cls, 
        headers: Dict[str, str], 
        context: HeaderContext, 
        kwargs: Dict[str, Any]
    ) -> None:
        """Add context-specific header customizations.
        
        Args:
            headers: Headers dictionary to modify
            context: Context for customization
            kwargs: Additional context-specific parameters
        """
        if context == HeaderContext.VERIFICATION:
            # Add verification level if specified
            verification_level = kwargs.get("verification_level")
            if verification_level:
                headers["X-Neo-Verification-Level"] = verification_level
        
        elif context == HeaderContext.HEALTH_CHECK:
            # Add health check timestamp
            from datetime import datetime, timezone
            headers["X-Neo-Health-Check-Timestamp"] = datetime.now(timezone.utc).isoformat()
        
        elif context == HeaderContext.CONNECTIVITY_TEST:
            # Add test identifier
            test_id = kwargs.get("test_id")
            if test_id:
                headers["X-Neo-Test-ID"] = test_id
    
    @classmethod
    def merge_headers(
        cls, 
        base_headers: Dict[str, str], 
        additional_headers: Dict[str, str],
        allow_override: bool = False
    ) -> Dict[str, str]:
        """Merge two header dictionaries with conflict resolution.
        
        Args:
            base_headers: Base headers to start with
            additional_headers: Additional headers to merge
            allow_override: Whether to allow additional headers to override base headers
            
        Returns:
            Merged headers dictionary
        """
        merged = base_headers.copy()
        
        for key, value in additional_headers.items():
            if allow_override or key not in merged:
                merged[key] = value
            else:
                # Conflict resolution: prefix with source indicator
                merged[f"X-Additional-{key}"] = value
        
        return merged
    
    @classmethod
    def get_protected_headers(cls) -> set:
        """Get set of headers that should not be overridden.
        
        Returns:
            Set of protected header names (lowercase)
        """
        return {
            "content-type",
            "user-agent", 
            "connection",
            "accept-encoding",
            "x-neo-signature",
            "x-neo-verification",
            "x-neo-health-check",
            "x-neo-connectivity-test"
        }
    
    @classmethod
    def validate_headers(cls, headers: Dict[str, str]) -> tuple[bool, list[str]]:
        """Validate headers for common issues.
        
        Args:
            headers: Headers to validate
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        is_valid = True
        
        # Check for required headers
        if "Content-Type" not in headers:
            warnings.append("Missing Content-Type header")
        
        if "User-Agent" not in headers:
            warnings.append("Missing User-Agent header")
        
        # Check for potentially problematic headers
        for key, value in headers.items():
            # Check for empty values
            if not value.strip():
                warnings.append(f"Empty value for header: {key}")
            
            # Check for very long values
            if len(value) > 1000:
                warnings.append(f"Very long value for header {key} ({len(value)} chars)")
            
            # Check for common header name typos
            if key.lower() in ["content_type", "user_agent", "accept_encoding"]:
                warnings.append(f"Header name uses underscores instead of hyphens: {key}")
        
        return is_valid, warnings