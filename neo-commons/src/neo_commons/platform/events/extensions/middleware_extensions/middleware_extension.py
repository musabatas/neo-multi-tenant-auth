"""
Middleware extension interface.

ONLY handles middleware extension contracts and lifecycle.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from ....core.value_objects import TenantId, UserId, RequestId


class MiddlewareStage(Enum):
    """Middleware execution stages."""
    PRE_REQUEST = "pre_request"
    POST_REQUEST = "post_request"
    ON_ERROR = "on_error"


@dataclass
class MiddlewareContext:
    """Context provided to middleware extensions."""
    request_id: RequestId
    tenant_id: Optional[TenantId]
    user_id: Optional[UserId]
    request_path: str
    request_method: str
    stage: MiddlewareStage
    metadata: Dict[str, Any]
    processing_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "request_id": self.request_id.value,
            "tenant_id": self.tenant_id.value if self.tenant_id else None,
            "user_id": self.user_id.value if self.user_id else None,
            "request_path": self.request_path,
            "request_method": self.request_method,
            "stage": self.stage.value,
            "metadata": self.metadata,
            "processing_time_ms": self.processing_time_ms,
            "error_message": self.error_message,
        }


@dataclass
class MiddlewareResult:
    """Result from middleware extension processing."""
    success: bool = True
    continue_processing: bool = True
    additional_headers: Optional[Dict[str, str]] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "continue_processing": self.continue_processing,
            "additional_headers": self.additional_headers,
            "additional_metadata": self.additional_metadata,
            "error_message": self.error_message,
        }


class MiddlewareExtension(ABC):
    """
    Abstract base class for middleware extensions.
    
    Provides extension points for HTTP request/response processing.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Extension name for identification."""
        pass
        
    @property
    @abstractmethod
    def version(self) -> str:
        """Extension version."""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Extension description."""
        pass
        
    @property
    @abstractmethod
    def middleware_stages(self) -> list[MiddlewareStage]:
        """List of middleware stages this extension handles."""
        pass
        
    @property
    def priority(self) -> int:
        """
        Extension priority (lower numbers run first).
        
        Returns:
            Priority value (0-1000, default 500)
        """
        return 500
        
    @property
    def enabled(self) -> bool:
        """Whether this extension is enabled."""
        return True
        
    @property
    def path_patterns(self) -> Optional[list[str]]:
        """
        List of path patterns this middleware applies to.
        
        Returns:
            List of path patterns, or None for all paths
        """
        return None
        
    @abstractmethod
    async def process_request(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> MiddlewareResult:
        """
        Process incoming request.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            
        Returns:
            MiddlewareResult indicating processing outcome
        """
        pass
        
    async def process_response(
        self,
        context: MiddlewareContext,
        request: Request,
        response: Response
    ) -> MiddlewareResult:
        """
        Process outgoing response.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            response: HTTP response
            
        Returns:
            MiddlewareResult indicating processing outcome
        """
        return MiddlewareResult(success=True, continue_processing=True)
        
    async def process_error(
        self,
        context: MiddlewareContext,
        request: Request,
        error: Exception
    ) -> MiddlewareResult:
        """
        Process request error.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            error: Exception that occurred
            
        Returns:
            MiddlewareResult indicating processing outcome
        """
        return MiddlewareResult(success=True, continue_processing=True)
        
    async def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """
        Validate extension configuration.
        
        Args:
            config: Extension configuration
            
        Returns:
            True if configuration is valid
        """
        return True
        
    async def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initialize the extension with configuration.
        
        Args:
            config: Extension configuration
        """
        pass
        
    async def cleanup(self) -> None:
        """Clean up extension resources."""
        pass
        
    def matches_path(self, path: str) -> bool:
        """
        Check if extension applies to the given path.
        
        Args:
            path: Request path to check
            
        Returns:
            True if extension should process this path
        """
        if not self.path_patterns:
            return True  # Apply to all paths if no patterns specified
            
        for pattern in self.path_patterns:
            if self._matches_pattern(path, pattern):
                return True
                
        return False
        
    def supports_stage(self, stage: MiddlewareStage) -> bool:
        """
        Check if extension supports a specific middleware stage.
        
        Args:
            stage: Middleware stage to check
            
        Returns:
            True if stage is supported
        """
        return stage in self.middleware_stages
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get extension metadata."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "middleware_stages": [stage.value for stage in self.middleware_stages],
            "priority": self.priority,
            "enabled": self.enabled,
            "path_patterns": self.path_patterns,
        }
        
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Check if path matches pattern.
        
        Supports basic wildcard matching.
        
        Args:
            path: Request path
            pattern: Pattern to match against
            
        Returns:
            True if path matches pattern
        """
        if pattern == "*":
            return True
            
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return path.startswith(prefix)
            
        if pattern.startswith("*"):
            suffix = pattern[1:]
            return path.endswith(suffix)
            
        return path == pattern


class RequestLoggingExtension(MiddlewareExtension):
    """
    Middleware extension for request logging.
    
    Logs incoming requests and responses.
    """
    
    @property
    def name(self) -> str:
        return "request_logging"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "Logs HTTP requests and responses"
        
    @property
    def middleware_stages(self) -> list[MiddlewareStage]:
        """Logging extension handles all stages."""
        return [MiddlewareStage.PRE_REQUEST, MiddlewareStage.POST_REQUEST, MiddlewareStage.ON_ERROR]
        
    @abstractmethod
    async def log_request(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> None:
        """
        Log incoming request.
        
        Args:
            context: Middleware processing context
            request: HTTP request
        """
        pass
        
    @abstractmethod
    async def log_response(
        self,
        context: MiddlewareContext,
        request: Request,
        response: Response
    ) -> None:
        """
        Log outgoing response.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            response: HTTP response
        """
        pass
        
    @abstractmethod
    async def log_error(
        self,
        context: MiddlewareContext,
        request: Request,
        error: Exception
    ) -> None:
        """
        Log request error.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            error: Exception that occurred
        """
        pass
        
    async def process_request(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> MiddlewareResult:
        """Log incoming request."""
        try:
            await self.log_request(context, request)
            return MiddlewareResult(success=True, continue_processing=True)
        except Exception as e:
            return MiddlewareResult(
                success=False,
                continue_processing=True,  # Continue despite logging failure
                error_message=f"Request logging failed: {str(e)}"
            )
            
    async def process_response(
        self,
        context: MiddlewareContext,
        request: Request,
        response: Response
    ) -> MiddlewareResult:
        """Log outgoing response."""
        try:
            await self.log_response(context, request, response)
            return MiddlewareResult(success=True, continue_processing=True)
        except Exception as e:
            return MiddlewareResult(
                success=False,
                continue_processing=True,  # Continue despite logging failure
                error_message=f"Response logging failed: {str(e)}"
            )
            
    async def process_error(
        self,
        context: MiddlewareContext,
        request: Request,
        error: Exception
    ) -> MiddlewareResult:
        """Log request error."""
        try:
            await self.log_error(context, request, error)
            return MiddlewareResult(success=True, continue_processing=True)
        except Exception as e:
            return MiddlewareResult(
                success=False,
                continue_processing=True,  # Continue despite logging failure
                error_message=f"Error logging failed: {str(e)}"
            )


class SecurityHeadersExtension(MiddlewareExtension):
    """
    Middleware extension for security headers.
    
    Adds security-related headers to responses.
    """
    
    @property
    def name(self) -> str:
        return "security_headers"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "Adds security headers to HTTP responses"
        
    @property
    def middleware_stages(self) -> list[MiddlewareStage]:
        """Security headers extension handles post_request stage."""
        return [MiddlewareStage.POST_REQUEST]
        
    @abstractmethod
    async def get_security_headers(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> Dict[str, str]:
        """
        Get security headers to add to response.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            
        Returns:
            Dictionary of security headers
        """
        pass
        
    async def process_request(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> MiddlewareResult:
        """Security headers don't process requests."""
        return MiddlewareResult(success=True, continue_processing=True)
        
    async def process_response(
        self,
        context: MiddlewareContext,
        request: Request,
        response: Response
    ) -> MiddlewareResult:
        """Add security headers to response."""
        try:
            security_headers = await self.get_security_headers(context, request)
            
            return MiddlewareResult(
                success=True,
                continue_processing=True,
                additional_headers=security_headers
            )
            
        except Exception as e:
            return MiddlewareResult(
                success=False,
                continue_processing=True,  # Continue despite header failure
                error_message=f"Security headers failed: {str(e)}"
            )


class RateLimitExtension(MiddlewareExtension):
    """
    Middleware extension for rate limiting.
    
    Enforces rate limits on incoming requests.
    """
    
    @property
    def name(self) -> str:
        return "rate_limit"
        
    @property
    def version(self) -> str:
        return "1.0.0"
        
    @property
    def description(self) -> str:
        return "Enforces rate limits on HTTP requests"
        
    @property
    def middleware_stages(self) -> list[MiddlewareStage]:
        """Rate limit extension handles pre_request stage."""
        return [MiddlewareStage.PRE_REQUEST]
        
    @abstractmethod
    async def is_rate_limited(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> bool:
        """
        Check if request is rate limited.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            
        Returns:
            True if request is rate limited
        """
        pass
        
    @abstractmethod
    async def get_rate_limit_headers(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> Dict[str, str]:
        """
        Get rate limit headers to add to response.
        
        Args:
            context: Middleware processing context
            request: HTTP request
            
        Returns:
            Dictionary of rate limit headers
        """
        pass
        
    async def process_request(
        self,
        context: MiddlewareContext,
        request: Request
    ) -> MiddlewareResult:
        """Check rate limits for incoming request."""
        try:
            if await self.is_rate_limited(context, request):
                headers = await self.get_rate_limit_headers(context, request)
                
                return MiddlewareResult(
                    success=False,
                    continue_processing=False,  # Block rate limited requests
                    additional_headers=headers,
                    error_message="Rate limit exceeded"
                )
                
            return MiddlewareResult(success=True, continue_processing=True)
            
        except Exception as e:
            return MiddlewareResult(
                success=False,
                continue_processing=True,  # Continue despite rate limit failure
                error_message=f"Rate limit check failed: {str(e)}"
            )