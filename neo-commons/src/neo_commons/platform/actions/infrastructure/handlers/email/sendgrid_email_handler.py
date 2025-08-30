"""SendGrid email action handler implementation."""

import asyncio
import httpx
import json
from typing import Dict, Any, List, Optional

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult


class SendGridEmailHandler(ActionHandler):
    """
    Advanced email handler using SendGrid API.
    
    Configuration:
    - api_key: SendGrid API key (required)
    - from_email: From email address (required)
    - from_name: From display name (optional)
    - template_id: Dynamic template ID (optional)
    - api_timeout: API request timeout in seconds (default: 30)
    - sandbox_mode: Enable sandbox mode for testing (default: False)
    """
    
    def __init__(self):
        super().__init__()
        self._client = None
    
    @property
    def handler_name(self) -> str:
        return "sendgrid_email_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["email", "email_template"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate SendGrid handler configuration."""
        required_fields = ["api_key", "from_email"]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required SendGrid config field: {field}")
        
        # Validate email format
        from_email = config["from_email"]
        if "@" not in from_email:
            raise ValueError(f"Invalid from_email format: {from_email}")
        
        # Validate API key format (basic check)
        api_key = config["api_key"]
        if not api_key.startswith("SG."):
            raise ValueError("Invalid SendGrid API key format")
        
        # Validate timeout
        if "api_timeout" in config and not isinstance(config["api_timeout"], (int, float)):
            raise ValueError("api_timeout must be a number")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute SendGrid email sending.
        
        Expected input_data:
        - to_email: Recipient email address or list of addresses (required)
        - subject: Email subject (required if not using template)
        - content: Email content (required if not using template)
        - html_content: HTML email content (optional)
        - template_data: Dynamic template data (optional, for templates)
        - reply_to: Reply-to email (optional)
        - categories: Email categories for tracking (optional)
        - custom_args: Custom arguments for tracking (optional)
        - send_at: Unix timestamp for scheduled sending (optional)
        """
        try:
            # Extract and validate configuration
            api_key = config["api_key"]
            from_email = config["from_email"]
            from_name = config.get("from_name")
            template_id = config.get("template_id")
            api_timeout = config.get("api_timeout", 30)
            sandbox_mode = config.get("sandbox_mode", False)
            
            # Extract and validate input data
            to_email = input_data.get("to_email")
            if not to_email:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="Missing required field: to_email"
                )
            
            # Normalize recipients to list
            if isinstance(to_email, str):
                recipients = [{"email": to_email}]
            elif isinstance(to_email, list):
                recipients = [{"email": email} if isinstance(email, str) else email for email in to_email]
            else:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="to_email must be a string or list of strings/objects"
                )
            
            # Build message payload
            message_data = {
                "from": {
                    "email": from_email,
                    "name": from_name
                } if from_name else {"email": from_email},
                "personalizations": [
                    {
                        "to": recipients
                    }
                ]
            }
            
            # Handle template vs content
            if template_id:
                # Template-based email
                message_data["template_id"] = template_id
                
                # Add template data if provided
                template_data = input_data.get("template_data", {})
                if template_data:
                    message_data["personalizations"][0]["dynamic_template_data"] = template_data
                
            else:
                # Content-based email
                subject = input_data.get("subject")
                content = input_data.get("content")
                
                if not subject or not content:
                    return ExecutionResult(
                        success=False,
                        output_data={},
                        error_message="subject and content are required when not using template"
                    )
                
                message_data["personalizations"][0]["subject"] = subject
                
                # Add content
                content_list = [{"type": "text/plain", "value": content}]
                
                html_content = input_data.get("html_content")
                if html_content:
                    content_list.append({"type": "text/html", "value": html_content})
                
                message_data["content"] = content_list
            
            # Add optional fields
            reply_to = input_data.get("reply_to")
            if reply_to:
                message_data["reply_to"] = {"email": reply_to}
            
            categories = input_data.get("categories")
            if categories:
                message_data["categories"] = categories if isinstance(categories, list) else [categories]
            
            custom_args = input_data.get("custom_args")
            if custom_args:
                message_data["custom_args"] = custom_args
            
            send_at = input_data.get("send_at")
            if send_at:
                message_data["send_at"] = send_at
            
            # Add sandbox mode if enabled
            if sandbox_mode:
                message_data["mail_settings"] = {
                    "sandbox_mode": {
                        "enable": True
                    }
                }
            
            # Send email via SendGrid API
            async with httpx.AsyncClient(timeout=api_timeout) as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json=message_data
                )
                
                if response.status_code == 202:
                    # Success
                    message_id = response.headers.get("X-Message-Id", "unknown")
                    
                    return ExecutionResult(
                        success=True,
                        output_data={
                            "message_id": message_id,
                            "from_email": from_email,
                            "recipients_count": len(recipients),
                            "template_id": template_id,
                            "sandbox_mode": sandbox_mode,
                            "status_code": response.status_code
                        }
                    )
                else:
                    # Error response
                    error_data = {}
                    try:
                        error_data = response.json()
                    except:
                        pass
                    
                    return ExecutionResult(
                        success=False,
                        output_data={},
                        error_message=f"SendGrid API error: {response.status_code}",
                        error_details={
                            "status_code": response.status_code,
                            "response_body": error_data,
                            "request_data": message_data
                        }
                    )
        
        except httpx.TimeoutException:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message="SendGrid API timeout",
                error_details={
                    "timeout_seconds": api_timeout,
                    "error_type": "TimeoutException"
                }
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"SendGrid email sending failed: {str(e)}",
                error_details={
                    "error_type": type(e).__name__,
                    "to_email": input_data.get("to_email")
                }
            )
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for SendGrid email sending."""
        return config.get("api_timeout", 30) + 10  # Add buffer
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check by testing SendGrid API connectivity."""
        try:
            api_key = config["api_key"]
            api_timeout = config.get("api_timeout", 30)
            
            # Test API connectivity by calling stats endpoint
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.sendgrid.com/v3/stats",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    params={
                        "start_date": "2024-01-01",
                        "limit": 1
                    }
                )
                
                if response.status_code in [200, 401]:  # 401 means API key format is correct
                    status = "healthy" if response.status_code == 200 else "api_key_issue"
                    
                    return {
                        "healthy": response.status_code == 200,
                        "status": status,
                        "details": {
                            "api_status_code": response.status_code,
                            "api_endpoint": "https://api.sendgrid.com/v3/stats"
                        }
                    }
                else:
                    return {
                        "healthy": False,
                        "status": f"SendGrid API error: {response.status_code}",
                        "details": {
                            "api_status_code": response.status_code,
                            "error_type": "API_ERROR"
                        }
                    }
        
        except httpx.TimeoutException:
            return {
                "healthy": False,
                "status": "SendGrid API timeout",
                "details": {
                    "error_type": "TimeoutException",
                    "timeout_seconds": 10
                }
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "status": f"SendGrid health check failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for SendGrid handler."""
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "SendGrid API key",
                    "pattern": "^SG\\."
                },
                "from_email": {
                    "type": "string",
                    "format": "email",
                    "description": "From email address"
                },
                "from_name": {
                    "type": "string",
                    "description": "From display name (optional)"
                },
                "template_id": {
                    "type": "string",
                    "description": "Dynamic template ID (optional)"
                },
                "api_timeout": {
                    "type": "number",
                    "default": 30,
                    "description": "API request timeout in seconds"
                },
                "sandbox_mode": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable sandbox mode for testing"
                }
            },
            "required": ["api_key", "from_email"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for SendGrid handler."""
        return {
            "type": "object",
            "properties": {
                "to_email": {
                    "oneOf": [
                        {"type": "string", "format": "email"},
                        {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string", "format": "email"},
                                    {
                                        "type": "object",
                                        "properties": {
                                            "email": {"type": "string", "format": "email"},
                                            "name": {"type": "string"}
                                        },
                                        "required": ["email"]
                                    }
                                ]
                            }
                        }
                    ],
                    "description": "Recipient email address(es)"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject (required if not using template)"
                },
                "content": {
                    "type": "string",
                    "description": "Plain text email content (required if not using template)"
                },
                "html_content": {
                    "type": "string",
                    "description": "HTML email content (optional)"
                },
                "template_data": {
                    "type": "object",
                    "description": "Dynamic template data for SendGrid templates"
                },
                "reply_to": {
                    "type": "string",
                    "format": "email",
                    "description": "Reply-to email address"
                },
                "categories": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}}
                    ],
                    "description": "Email categories for tracking"
                },
                "custom_args": {
                    "type": "object",
                    "description": "Custom arguments for tracking"
                },
                "send_at": {
                    "type": "integer",
                    "description": "Unix timestamp for scheduled sending"
                }
            },
            "required": ["to_email"],
            "anyOf": [
                {"required": ["subject", "content"]},
                {"properties": {"template_id": {"type": "string"}}}
            ]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for SendGrid handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message_id": {"type": "string"},
                "from_email": {"type": "string"},
                "recipients_count": {"type": "integer"},
                "template_id": {"type": "string"},
                "sandbox_mode": {"type": "boolean"},
                "status_code": {"type": "integer"}
            },
            "required": ["success"]
        }