"""
Built-in Event Action Handlers

This module provides built-in implementations of common event action handlers
including webhook, email, function, and workflow handlers.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

import httpx
from httpx import AsyncClient

from ..entities.action_handlers import (
    BaseEventActionHandler, 
    BaseAsyncEventActionHandler,
    ExecutionContext,
    HandlerResult
)
from ..entities.event_action import EventAction, ExecutionMode


logger = logging.getLogger(__name__)


@dataclass
class WebhookConfig:
    """Configuration for webhook handler."""
    url: str
    method: str = "POST"
    headers: Optional[Dict[str, str]] = None
    timeout: int = 30
    verify_ssl: bool = True
    signature_header: Optional[str] = None
    secret: Optional[str] = None


class WebhookEventActionHandler(BaseEventActionHandler):
    """Handler for webhook actions."""
    
    def __init__(self):
        super().__init__("webhook")
        self._client: Optional[AsyncClient] = None
    
    async def _get_client(self) -> AsyncClient:
        """Get HTTP client (lazy initialization)."""
        if self._client is None:
            self._client = AsyncClient(
                timeout=httpx.Timeout(30.0),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=100)
            )
        return self._client
    
    async def execute(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> HandlerResult:
        """Execute webhook action."""
        try:
            config = WebhookConfig(**action.configuration)
            
            # Prepare payload
            payload = {
                "event_type": context.event_type,
                "event_data": context.event_data,
                "action_id": str(context.action_id),
                "execution_id": str(context.execution_id),
                "tenant_id": context.tenant_id,
                "timestamp": context.execution_metadata.get("timestamp"),
                "correlation_id": context.correlation_id
            }
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "NeoMultiTenant-Webhooks/1.0",
                **(config.headers or {})
            }
            
            # Add signature if configured
            if config.signature_header and config.secret:
                import hmac
                import hashlib
                payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
                signature = hmac.new(
                    config.secret.encode('utf-8'),
                    payload_str.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                headers[config.signature_header] = f"sha256={signature}"
            
            # Make HTTP request
            client = await self._get_client()
            response = await client.request(
                method=config.method,
                url=config.url,
                json=payload,
                headers=headers,
                timeout=config.timeout
            )
            
            response.raise_for_status()
            
            # Return success result
            return self._create_success_result(
                message=f"Webhook delivered successfully to {config.url}",
                metadata={
                    "response_status": response.status_code,
                    "response_headers": dict(response.headers),
                    "response_size": len(response.content),
                    "url": config.url,
                    "method": config.method
                }
            )
            
        except httpx.HTTPStatusError as e:
            return self._create_error_result(
                error=f"Webhook HTTP error: {e.response.status_code} - {e.response.text}",
                metadata={
                    "status_code": e.response.status_code,
                    "url": config.url if 'config' in locals() else action.configuration.get('url')
                }
            )
        except httpx.RequestError as e:
            return self._create_error_result(
                error=f"Webhook connection error: {str(e)}",
                metadata={
                    "url": config.url if 'config' in locals() else action.configuration.get('url')
                }
            )
        except Exception as e:
            return self._create_error_result(
                error=f"Webhook execution failed: {str(e)}",
                metadata={
                    "url": action.configuration.get('url'),
                    "error_type": type(e).__name__
                }
            )
    
    async def validate_configuration(self, configuration: Dict[str, Any]) -> List[str]:
        """Validate webhook configuration."""
        errors = self._validate_required_fields(configuration, ["url"])
        
        if not errors:
            url = configuration.get("url", "")
            try:
                parsed = urlparse(url)
                if not parsed.scheme or not parsed.netloc:
                    errors.append("URL must be a valid HTTP/HTTPS URL")
                elif parsed.scheme not in ("http", "https"):
                    errors.append("URL must use HTTP or HTTPS scheme")
            except Exception:
                errors.append("Invalid URL format")
        
        # Validate optional fields
        method = configuration.get("method", "POST")
        if method not in ("GET", "POST", "PUT", "PATCH", "DELETE"):
            errors.append("Method must be GET, POST, PUT, PATCH, or DELETE")
        
        timeout = configuration.get("timeout", 30)
        if not isinstance(timeout, int) or timeout <= 0 or timeout > 300:
            errors.append("Timeout must be between 1 and 300 seconds")
        
        return errors
    
    async def get_default_configuration(self) -> Dict[str, Any]:
        """Get default webhook configuration."""
        return {
            "url": "",
            "method": "POST",
            "headers": {},
            "timeout": 30,
            "verify_ssl": True
        }
    
    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()


@dataclass
class EmailConfig:
    """Configuration for email handler."""
    to: List[str]
    subject: str
    template: str
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    from_address: Optional[str] = None
    template_variables: Optional[Dict[str, str]] = None


class EmailEventActionHandler(BaseEventActionHandler):
    """Handler for email actions."""
    
    def __init__(self, email_service: Optional[Any] = None):
        super().__init__("email")
        self._email_service = email_service
    
    async def execute(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> HandlerResult:
        """Execute email action."""
        if not self._email_service:
            return self._create_error_result(
                error="Email service not configured",
                metadata={"handler_type": "email"}
            )
        
        try:
            config = EmailConfig(**action.configuration)
            
            # Build template variables
            template_vars = {
                "event_type": context.event_type,
                "event_data": context.event_data,
                "action_name": action.name,
                "execution_id": str(context.execution_id),
                "tenant_id": context.tenant_id or "system",
                "timestamp": context.execution_metadata.get("timestamp", ""),
                **(config.template_variables or {})
            }
            
            # Send email through service
            result = await self._email_service.send_template_email(
                to=config.to,
                subject=config.subject,
                template=config.template,
                template_variables=template_vars,
                cc=config.cc,
                bcc=config.bcc,
                from_address=config.from_address
            )
            
            return self._create_success_result(
                message=f"Email sent successfully to {len(config.to)} recipients",
                metadata={
                    "recipients": config.to,
                    "template": config.template,
                    "message_id": result.get("message_id") if isinstance(result, dict) else None
                }
            )
            
        except Exception as e:
            return self._create_error_result(
                error=f"Email execution failed: {str(e)}",
                metadata={
                    "template": action.configuration.get("template"),
                    "error_type": type(e).__name__
                }
            )
    
    async def validate_configuration(self, configuration: Dict[str, Any]) -> List[str]:
        """Validate email configuration."""
        errors = self._validate_required_fields(configuration, ["to", "subject", "template"])
        
        if not errors:
            to_addresses = configuration.get("to", [])
            if not isinstance(to_addresses, list) or not to_addresses:
                errors.append("'to' must be a non-empty list of email addresses")
            else:
                # Basic email validation
                import re
                email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
                for email in to_addresses:
                    if not isinstance(email, str) or not email_pattern.match(email):
                        errors.append(f"Invalid email address: {email}")
                        break
        
        # Validate optional CC and BCC
        for field in ["cc", "bcc"]:
            if field in configuration:
                addresses = configuration[field]
                if addresses and not isinstance(addresses, list):
                    errors.append(f"'{field}' must be a list of email addresses")
        
        return errors
    
    async def get_default_configuration(self) -> Dict[str, Any]:
        """Get default email configuration."""
        return {
            "to": [],
            "subject": "Event Notification: {event_type}",
            "template": "default_event_notification",
            "template_variables": {}
        }


@dataclass
class FunctionConfig:
    """Configuration for function handler."""
    module: str
    function: str
    args: Optional[Dict[str, Any]] = None
    timeout: int = 30


class FunctionEventActionHandler(BaseAsyncEventActionHandler):
    """Handler for function actions."""
    
    def __init__(self):
        super().__init__("function")
    
    async def execute(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> HandlerResult:
        """Execute function action."""
        try:
            config = FunctionConfig(**action.configuration)
            
            # Dynamic import of the function
            module_parts = config.module.split('.')
            module = __import__(config.module, fromlist=[module_parts[-1]])
            func = getattr(module, config.function)
            
            # Prepare function arguments
            func_args = {
                "event_type": context.event_type,
                "event_data": context.event_data,
                "action_id": str(context.action_id),
                "execution_id": str(context.execution_id),
                "context": context.execution_metadata,
                **(config.args or {})
            }
            
            # Execute function with timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(**func_args), 
                    timeout=config.timeout
                )
            else:
                # Run sync function in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None, 
                    lambda: func(**func_args)
                )
            
            return self._create_success_result(
                message=f"Function {config.module}.{config.function} executed successfully",
                metadata={
                    "module": config.module,
                    "function": config.function,
                    "result": result if isinstance(result, (str, int, float, bool, dict, list)) else str(result)
                }
            )
            
        except asyncio.TimeoutError:
            return self._create_error_result(
                error=f"Function execution timed out after {config.timeout} seconds",
                metadata={
                    "module": config.module,
                    "function": config.function,
                    "timeout": config.timeout
                }
            )
        except ImportError as e:
            return self._create_error_result(
                error=f"Could not import module or function: {str(e)}",
                metadata={
                    "module": action.configuration.get("module"),
                    "function": action.configuration.get("function")
                }
            )
        except Exception as e:
            return self._create_error_result(
                error=f"Function execution failed: {str(e)}",
                metadata={
                    "module": action.configuration.get("module"),
                    "function": action.configuration.get("function"),
                    "error_type": type(e).__name__
                }
            )
    
    async def validate_configuration(self, configuration: Dict[str, Any]) -> List[str]:
        """Validate function configuration."""
        errors = self._validate_required_fields(configuration, ["module", "function"])
        
        if not errors:
            module_name = configuration.get("module", "")
            if not module_name or not isinstance(module_name, str):
                errors.append("Module must be a valid module name")
            
            function_name = configuration.get("function", "")
            if not function_name or not isinstance(function_name, str):
                errors.append("Function must be a valid function name")
            
            # Try to validate module exists (optional - may not be available at config time)
            try:
                __import__(module_name)
            except ImportError:
                # Don't fail validation - module might not be available at config time
                pass
        
        timeout = configuration.get("timeout", 30)
        if not isinstance(timeout, int) or timeout <= 0 or timeout > 300:
            errors.append("Timeout must be between 1 and 300 seconds")
        
        return errors
    
    async def get_default_configuration(self) -> Dict[str, Any]:
        """Get default function configuration."""
        return {
            "module": "",
            "function": "",
            "args": {},
            "timeout": 30
        }


class WorkflowEventActionHandler(BaseAsyncEventActionHandler):
    """Handler for workflow actions (sequential steps)."""
    
    def __init__(self, handler_registry):
        super().__init__("workflow")
        self._handler_registry = handler_registry
    
    async def execute(
        self, 
        action: EventAction, 
        context: ExecutionContext
    ) -> HandlerResult:
        """Execute workflow action."""
        try:
            steps = action.configuration.get("steps", [])
            results = []
            
            for i, step in enumerate(steps):
                step_handler_type = step.get("handler_type")
                step_config = step.get("configuration", {})
                
                # Get handler for this step
                handler = await self._handler_registry.get_handler(step_handler_type)
                if not handler:
                    return self._create_error_result(
                        error=f"No handler found for step {i+1}: {step_handler_type}",
                        metadata={
                            "step_index": i,
                            "step_handler_type": step_handler_type,
                            "completed_steps": len(results)
                        }
                    )
                
                # Create step action
                from ..entities.event_action import EventAction
                step_action = EventAction(
                    id=action.id,  # Reuse action ID
                    name=f"{action.name} - Step {i+1}",
                    handler_type=step_handler_type,
                    configuration=step_config,
                    event_types=action.event_types,
                    conditions=[],
                    execution_mode=action.execution_mode,
                    priority=action.priority,
                    timeout_seconds=step.get("timeout_seconds", action.timeout_seconds),
                    max_retries=0,  # No retries for individual steps
                    retry_delay_seconds=0,
                    status=action.status,
                    is_enabled=True
                )
                
                # Execute step
                step_result = await handler.execute(step_action, context)
                results.append({
                    "step_index": i,
                    "handler_type": step_handler_type,
                    "success": step_result.success,
                    "message": step_result.message,
                    "error": step_result.error,
                    "metadata": step_result.metadata
                })
                
                # Stop on first failure if configured
                if not step_result.success and action.configuration.get("stop_on_failure", True):
                    return self._create_error_result(
                        error=f"Workflow failed at step {i+1}: {step_result.error}",
                        metadata={
                            "step_index": i,
                            "completed_steps": results,
                            "total_steps": len(steps)
                        }
                    )
            
            # All steps completed successfully
            success_count = sum(1 for r in results if r["success"])
            return self._create_success_result(
                message=f"Workflow completed successfully: {success_count}/{len(steps)} steps succeeded",
                metadata={
                    "total_steps": len(steps),
                    "successful_steps": success_count,
                    "results": results
                }
            )
            
        except Exception as e:
            return self._create_error_result(
                error=f"Workflow execution failed: {str(e)}",
                metadata={
                    "error_type": type(e).__name__,
                    "completed_steps": len(results) if 'results' in locals() else 0
                }
            )
    
    async def validate_configuration(self, configuration: Dict[str, Any]) -> List[str]:
        """Validate workflow configuration."""
        errors = self._validate_required_fields(configuration, ["steps"])
        
        if not errors:
            steps = configuration.get("steps", [])
            if not isinstance(steps, list) or not steps:
                errors.append("Steps must be a non-empty list")
            else:
                for i, step in enumerate(steps):
                    if not isinstance(step, dict):
                        errors.append(f"Step {i+1} must be an object")
                        continue
                    
                    if "handler_type" not in step:
                        errors.append(f"Step {i+1} missing required field: handler_type")
                    
                    if "configuration" not in step:
                        errors.append(f"Step {i+1} missing required field: configuration")
        
        return errors
    
    async def get_default_configuration(self) -> Dict[str, Any]:
        """Get default workflow configuration."""
        return {
            "steps": [],
            "stop_on_failure": True
        }