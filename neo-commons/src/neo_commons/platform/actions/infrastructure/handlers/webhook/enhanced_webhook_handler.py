"""Enhanced webhook handler with circuit breaker and advanced features."""

import asyncio
import json
import hashlib
import hmac
import base64
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import httpx

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult


class AuthType(Enum):
    """Supported authentication types."""
    NONE = "none"
    BASIC = "basic"
    BEARER = "bearer"
    API_KEY = "api_key"
    HMAC = "hmac"
    JWT = "jwt"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"  
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker implementation for webhook resilience."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func):
        """Decorator for circuit breaker."""
        async def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise Exception(f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}")
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
                
            except self.expected_exception as e:
                self._on_failure()
                raise
        
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset."""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN


class EnhancedWebhookHandler(ActionHandler):
    """
    Enhanced webhook handler with circuit breaker, advanced auth, and resilience features.
    
    Configuration:
    - webhook_url: Target URL for webhook (required)
    - method: HTTP method (default: POST)
    - auth_type: Authentication type (none, basic, bearer, api_key, hmac, jwt)
    - auth_config: Authentication configuration dict
    - headers: Custom headers dict (optional)
    - timeout_seconds: Request timeout (default: 30)
    - verify_ssl: Whether to verify SSL certificates (default: True)
    - circuit_breaker: Circuit breaker configuration
    - retry_config: Retry configuration with exponential backoff
    - payload_compression: Enable gzip compression (default: False)
    - include_metadata: Include event metadata in payload (default: True)
    """
    
    def __init__(self):
        super().__init__()
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
    
    @property
    def handler_name(self) -> str:
        return "enhanced_webhook_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["webhook", "enhanced_webhook", "webhook_secure"]
    
    def _get_circuit_breaker(self, webhook_url: str, config: Dict[str, Any]) -> CircuitBreaker:
        """Get or create circuit breaker for webhook URL."""
        if webhook_url not in self._circuit_breakers:
            cb_config = config.get("circuit_breaker", {})
            self._circuit_breakers[webhook_url] = CircuitBreaker(
                failure_threshold=cb_config.get("failure_threshold", 5),
                recovery_timeout=cb_config.get("recovery_timeout", 60),
                expected_exception=Exception
            )
        return self._circuit_breakers[webhook_url]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate enhanced webhook handler configuration."""
        if "webhook_url" not in config:
            raise ValueError("Missing required webhook config field: webhook_url")
        
        webhook_url = config["webhook_url"]
        if not webhook_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid webhook_url format: {webhook_url}")
        
        # Validate authentication configuration
        auth_type = config.get("auth_type", "none")
        if auth_type not in [e.value for e in AuthType]:
            raise ValueError(f"Unsupported auth_type: {auth_type}")
        
        if auth_type != "none":
            auth_config = config.get("auth_config", {})
            if not auth_config:
                raise ValueError(f"auth_config required for auth_type: {auth_type}")
            
            # Validate specific auth configurations
            if auth_type == "basic" and not all(k in auth_config for k in ["username", "password"]):
                raise ValueError("basic auth requires username and password")
            elif auth_type == "bearer" and "token" not in auth_config:
                raise ValueError("bearer auth requires token")
            elif auth_type == "api_key" and not all(k in auth_config for k in ["key", "value"]):
                raise ValueError("api_key auth requires key and value")
            elif auth_type == "hmac" and not all(k in auth_config for k in ["secret", "algorithm"]):
                raise ValueError("hmac auth requires secret and algorithm")
        
        # Validate method
        method = config.get("method", "POST").upper()
        if method not in ["POST", "PUT", "PATCH", "DELETE"]:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Validate timeout
        timeout = config.get("timeout_seconds", 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout_seconds must be a positive number")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute enhanced webhook request with circuit breaker and retry logic.
        """
        webhook_url = config["webhook_url"]
        circuit_breaker = self._get_circuit_breaker(webhook_url, config)
        
        # Configure retry settings
        retry_config = config.get("retry_config", {})
        max_retries = retry_config.get("max_retries", 3)
        base_delay = retry_config.get("base_delay_ms", 1000) / 1000.0  # Convert to seconds
        max_delay = retry_config.get("max_delay_ms", 30000) / 1000.0
        jitter = retry_config.get("jitter", True)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Use circuit breaker
                @circuit_breaker.call
                async def make_request():
                    return await self._make_webhook_request(config, input_data, context)
                
                result = await make_request()
                return result
                
            except Exception as e:
                last_exception = e
                
                # Don't retry on the last attempt
                if attempt == max_retries:
                    break
                
                # Calculate delay for exponential backoff
                delay = min(base_delay * (2 ** attempt), max_delay)
                if jitter:
                    import random
                    delay = delay * (0.5 + random.random() * 0.5)  # Add jitter
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        return ExecutionResult(
            success=False,
            output_data={},
            error_message=f"Webhook request failed after {max_retries + 1} attempts: {str(last_exception)}",
            error_details={
                "webhook_url": webhook_url,
                "attempts": max_retries + 1,
                "circuit_breaker_state": circuit_breaker.state.value,
                "last_error": str(last_exception),
                "error_type": type(last_exception).__name__ if last_exception else "Unknown"
            }
        )
    
    async def _make_webhook_request(
        self,
        config: Dict[str, Any],
        input_data: Dict[str, Any],
        context: ExecutionContext
    ) -> ExecutionResult:
        """Make the actual webhook request."""
        try:
            # Extract configuration
            webhook_url = config["webhook_url"]
            method = config.get("method", "POST").upper()
            auth_type = config.get("auth_type", "none")
            auth_config = config.get("auth_config", {})
            custom_headers = config.get("headers", {})
            timeout_seconds = config.get("timeout_seconds", 30)
            verify_ssl = config.get("verify_ssl", True)
            payload_compression = config.get("payload_compression", False)
            include_metadata = config.get("include_metadata", True)
            
            # Prepare payload
            if include_metadata:
                payload_data = {
                    "event_id": str(context.event.id.value) if hasattr(context, 'event') else None,
                    "event_type": context.event.event_type.value if hasattr(context, 'event') else None,
                    "schema": context.schema if hasattr(context, 'schema') else None,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "data": input_data,
                    "metadata": {
                        "handler": self.handler_name,
                        "version": self.handler_version,
                        "tenant_id": getattr(context, 'tenant_id', None),
                        "organization_id": getattr(context, 'organization_id', None),
                        "user_id": getattr(context, 'user_id', None)
                    }
                }
            else:
                payload_data = input_data
            
            # Serialize payload
            payload_json = json.dumps(payload_data, separators=(',', ':'), default=str)
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": f"neo-commons-actions/{self.handler_version}",
                **custom_headers
            }
            
            # Add compression if enabled
            content = payload_json.encode('utf-8')
            if payload_compression:
                import gzip
                content = gzip.compress(content)
                headers["Content-Encoding"] = "gzip"
            
            # Add authentication
            await self._add_authentication(headers, content, auth_type, auth_config, method, webhook_url)
            
            # Send webhook request
            async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=webhook_url,
                    content=content,
                    headers=headers
                )
                
                # Check response status
                response.raise_for_status()
                
                # Parse response
                try:
                    response_data = response.json()
                except (json.JSONDecodeError, ValueError):
                    response_data = {"raw_response": response.text[:1000]}  # Limit response size
                
                return ExecutionResult(
                    success=True,
                    output_data={
                        "webhook_url": webhook_url,
                        "method": method,
                        "status_code": response.status_code,
                        "response_headers": dict(response.headers),
                        "response_data": response_data,
                        "payload_size": len(content),
                        "compressed": payload_compression,
                        "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                    }
                )
        
        except httpx.TimeoutException as e:
            raise Exception(f"Request timeout after {timeout_seconds}s")
        except httpx.HTTPStatusError as e:
            raise Exception(f"HTTP {e.response.status_code}: {e.response.text[:500]}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")
    
    async def _add_authentication(
        self,
        headers: Dict[str, str],
        content: bytes,
        auth_type: str,
        auth_config: Dict[str, Any],
        method: str,
        url: str
    ):
        """Add authentication to request headers."""
        if auth_type == "basic":
            username = auth_config["username"]
            password = auth_config["password"]
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"
        
        elif auth_type == "bearer":
            token = auth_config["token"]
            headers["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "api_key":
            key = auth_config["key"]
            value = auth_config["value"]
            headers[key] = value
        
        elif auth_type == "hmac":
            secret = auth_config["secret"]
            algorithm = auth_config.get("algorithm", "sha256")
            header_name = auth_config.get("header_name", "X-HMAC-Signature")
            
            # Create HMAC signature
            if algorithm == "sha256":
                hash_func = hashlib.sha256
            elif algorithm == "sha512":
                hash_func = hashlib.sha512
            else:
                hash_func = hashlib.sha256  # Default fallback
            
            signature = hmac.new(
                secret.encode('utf-8'),
                content,
                hash_func
            ).hexdigest()
            
            headers[header_name] = f"{algorithm}={signature}"
        
        elif auth_type == "jwt":
            # For JWT, we expect a pre-signed token
            token = auth_config["token"]
            headers["Authorization"] = f"Bearer {token}"
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout including retry delays."""
        base_timeout = config.get("timeout_seconds", 30)
        retry_config = config.get("retry_config", {})
        max_retries = retry_config.get("max_retries", 3)
        max_delay = retry_config.get("max_delay_ms", 30000) / 1000.0
        
        # Account for retries and delays
        return int(base_timeout * (max_retries + 1) + max_delay * max_retries)
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check with circuit breaker status."""
        webhook_url = config["webhook_url"]
        circuit_breaker = self._get_circuit_breaker(webhook_url, config)
        
        try:
            if circuit_breaker.state == CircuitState.OPEN:
                return {
                    "healthy": False,
                    "status": "Circuit breaker is OPEN",
                    "details": {
                        "webhook_url": webhook_url,
                        "circuit_state": circuit_breaker.state.value,
                        "failure_count": circuit_breaker.failure_count,
                        "last_failure": circuit_breaker.last_failure_time
                    }
                }
            
            verify_ssl = config.get("verify_ssl", True)
            
            # Test basic connectivity
            async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
                try:
                    response = await client.head(webhook_url)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 405:  # Method not allowed
                        response = await client.get(webhook_url)
                    else:
                        response = e.response
                
                return {
                    "healthy": response.status_code < 500,
                    "status": f"Endpoint reachable (HTTP {response.status_code})",
                    "details": {
                        "webhook_url": webhook_url,
                        "status_code": response.status_code,
                        "circuit_state": circuit_breaker.state.value,
                        "failure_count": circuit_breaker.failure_count,
                        "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                    }
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Health check failed: {str(e)}",
                "details": {
                    "webhook_url": webhook_url,
                    "circuit_state": circuit_breaker.state.value,
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for enhanced webhook handler."""
        return {
            "type": "object",
            "properties": {
                "webhook_url": {
                    "type": "string",
                    "format": "uri",
                    "description": "Target URL for webhook"
                },
                "method": {
                    "type": "string",
                    "enum": ["POST", "PUT", "PATCH", "DELETE"],
                    "default": "POST",
                    "description": "HTTP method"
                },
                "auth_type": {
                    "type": "string",
                    "enum": ["none", "basic", "bearer", "api_key", "hmac", "jwt"],
                    "default": "none",
                    "description": "Authentication type"
                },
                "auth_config": {
                    "type": "object",
                    "description": "Authentication configuration",
                    "properties": {
                        "username": {"type": "string"},
                        "password": {"type": "string"},
                        "token": {"type": "string"},
                        "key": {"type": "string"},
                        "value": {"type": "string"},
                        "secret": {"type": "string"},
                        "algorithm": {"type": "string", "enum": ["sha256", "sha512"]},
                        "header_name": {"type": "string"}
                    }
                },
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Custom headers"
                },
                "timeout_seconds": {
                    "type": "number",
                    "default": 30,
                    "minimum": 1,
                    "description": "Request timeout in seconds"
                },
                "verify_ssl": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to verify SSL certificates"
                },
                "payload_compression": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable gzip compression"
                },
                "include_metadata": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include event metadata in payload"
                },
                "circuit_breaker": {
                    "type": "object",
                    "properties": {
                        "failure_threshold": {"type": "integer", "default": 5},
                        "recovery_timeout": {"type": "integer", "default": 60}
                    }
                },
                "retry_config": {
                    "type": "object",
                    "properties": {
                        "max_retries": {"type": "integer", "default": 3},
                        "base_delay_ms": {"type": "integer", "default": 1000},
                        "max_delay_ms": {"type": "integer", "default": 30000},
                        "jitter": {"type": "boolean", "default": True}
                    }
                }
            },
            "required": ["webhook_url"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for enhanced webhook handler."""
        return {
            "type": "object",
            "description": "Any JSON-serializable data to send in webhook payload",
            "additionalProperties": True
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for enhanced webhook handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "webhook_url": {"type": "string"},
                "method": {"type": "string"},
                "status_code": {"type": "integer"},
                "response_headers": {"type": "object"},
                "response_data": {"type": "object"},
                "payload_size": {"type": "integer"},
                "compressed": {"type": "boolean"},
                "response_time_ms": {"type": "integer"}
            },
            "required": ["success"]
        }