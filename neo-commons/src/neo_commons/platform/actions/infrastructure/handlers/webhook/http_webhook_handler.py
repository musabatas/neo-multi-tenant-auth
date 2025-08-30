"""HTTP webhook action handler implementation."""

import json
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Any
import httpx

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult


class HTTPWebhookHandler(ActionHandler):
    """
    HTTP webhook handler for sending POST requests.
    
    Configuration:
    - webhook_url: Target URL for webhook (required)
    - method: HTTP method (default: POST)
    - headers: Custom headers dict (optional)
    - webhook_secret: Secret for HMAC signature (optional)
    - signature_header: Header name for signature (default: X-Webhook-Signature)
    - timeout_seconds: Request timeout (default: 30)
    - verify_ssl: Whether to verify SSL certificates (default: True)
    """
    
    @property
    def handler_name(self) -> str:
        return "http_webhook_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["webhook"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate webhook handler configuration."""
        if "webhook_url" not in config:
            raise ValueError("Missing required webhook config field: webhook_url")
        
        webhook_url = config["webhook_url"]
        if not webhook_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid webhook_url format: {webhook_url}")
        
        # Validate method if provided
        method = config.get("method", "POST").upper()
        if method not in ["POST", "PUT", "PATCH"]:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Validate timeout
        timeout = config.get("timeout_seconds", 30)
        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("timeout_seconds must be a positive integer")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute HTTP webhook request.
        
        Input data will be sent as JSON payload to the webhook URL.
        """
        try:
            # Extract configuration
            webhook_url = config["webhook_url"]
            method = config.get("method", "POST").upper()
            custom_headers = config.get("headers", {})
            webhook_secret = config.get("webhook_secret")
            signature_header = config.get("signature_header", "X-Webhook-Signature")
            timeout_seconds = config.get("timeout_seconds", 30)
            verify_ssl = config.get("verify_ssl", True)
            
            # Prepare payload
            payload_data = {
                "event_id": str(context.event.id.value),
                "event_type": context.event.event_type.value,
                "schema": context.schema,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": input_data
            }
            
            # Add context information if available
            if context.tenant_id:
                payload_data["tenant_id"] = context.tenant_id
            if context.organization_id:
                payload_data["organization_id"] = context.organization_id
            if context.user_id:
                payload_data["user_id"] = context.user_id
            
            payload_json = json.dumps(payload_data, separators=(',', ':'))
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "neo-commons-actions/1.0.0",
                **custom_headers
            }
            
            # Add HMAC signature if secret provided
            if webhook_secret:
                signature = hmac.new(
                    webhook_secret.encode('utf-8'),
                    payload_json.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                headers[signature_header] = f"sha256={signature}"
            
            # Send webhook request
            async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout_seconds) as client:
                response = await client.request(
                    method=method,
                    url=webhook_url,
                    content=payload_json,
                    headers=headers
                )
                
                # Check response status
                response.raise_for_status()
                
                # Try to parse response JSON
                try:
                    response_data = response.json()
                except (json.JSONDecodeError, ValueError):
                    response_data = {"raw_response": response.text}
                
                return ExecutionResult(
                    success=True,
                    output_data={
                        "webhook_url": webhook_url,
                        "method": method,
                        "status_code": response.status_code,
                        "response_headers": dict(response.headers),
                        "response_data": response_data,
                        "payload_size": len(payload_json)
                    }
                )
        
        except httpx.TimeoutException:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Webhook request timed out after {timeout_seconds} seconds",
                error_details={
                    "webhook_url": webhook_url,
                    "timeout_seconds": timeout_seconds,
                    "error_type": "TimeoutError"
                }
            )
            
        except httpx.HTTPStatusError as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Webhook request failed with status {e.response.status_code}",
                error_details={
                    "webhook_url": webhook_url,
                    "status_code": e.response.status_code,
                    "response_text": e.response.text,
                    "error_type": "HTTPStatusError"
                }
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Webhook request failed: {str(e)}",
                error_details={
                    "webhook_url": webhook_url,
                    "error_type": type(e).__name__
                }
            )
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for webhook requests."""
        return config.get("timeout_seconds", 30) + 5  # Add buffer for processing
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check by testing webhook endpoint."""
        try:
            webhook_url = config["webhook_url"]
            timeout_seconds = config.get("timeout_seconds", 30)
            verify_ssl = config.get("verify_ssl", True)
            
            # Test basic connectivity with HEAD request if possible
            async with httpx.AsyncClient(verify=verify_ssl, timeout=10) as client:
                try:
                    # Try HEAD first
                    response = await client.head(webhook_url)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 405:  # Method not allowed, try GET
                        response = await client.get(webhook_url)
                    else:
                        raise
                
                return {
                    "healthy": True,
                    "status": f"Webhook endpoint reachable (HTTP {response.status_code})",
                    "details": {
                        "webhook_url": webhook_url,
                        "status_code": response.status_code,
                        "response_time_ms": int(response.elapsed.total_seconds() * 1000)
                    }
                }
                
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Webhook endpoint unreachable: {str(e)}",
                "details": {
                    "webhook_url": config.get("webhook_url"),
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for webhook handler."""
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
                    "enum": ["POST", "PUT", "PATCH"],
                    "default": "POST",
                    "description": "HTTP method"
                },
                "headers": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Custom headers"
                },
                "webhook_secret": {
                    "type": "string",
                    "description": "Secret for HMAC signature"
                },
                "signature_header": {
                    "type": "string",
                    "default": "X-Webhook-Signature",
                    "description": "Header name for signature"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "default": 30,
                    "minimum": 1,
                    "description": "Request timeout in seconds"
                },
                "verify_ssl": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to verify SSL certificates"
                }
            },
            "required": ["webhook_url"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for webhook handler."""
        return {
            "type": "object",
            "description": "Any JSON-serializable data to send in webhook payload",
            "additionalProperties": True
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for webhook handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "webhook_url": {"type": "string"},
                "method": {"type": "string"},
                "status_code": {"type": "integer"},
                "response_headers": {"type": "object"},
                "response_data": {"type": "object"},
                "payload_size": {"type": "integer"}
            },
            "required": ["success"]
        }