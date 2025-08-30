"""Template-based email action handler implementation."""

import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template, TemplateError

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult
from .simple_email_handler import SimpleEmailHandler


class TemplateEmailHandler(ActionHandler):
    """
    Template-based email handler using Jinja2 templates.
    
    Configuration:
    - template_dir: Directory containing email templates (required)
    - template_name: Template file name (required)
    - smtp_host: SMTP server hostname (required)
    - smtp_port: SMTP server port (default: 587)
    - smtp_username: SMTP username (required)
    - smtp_password: SMTP password (required)
    - use_tls: Whether to use TLS (default: True)
    - from_email: From email address (required)
    - from_name: From display name (optional)
    - template_cache: Enable template caching (default: True)
    """
    
    def __init__(self):
        super().__init__()
        self._jinja_env = None
        self._smtp_handler = SimpleEmailHandler()
    
    @property
    def handler_name(self) -> str:
        return "template_email_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["email_template", "template_email"]
    
    def _get_jinja_environment(self, template_dir: str, enable_cache: bool = True) -> Environment:
        """Get or create Jinja2 environment."""
        if self._jinja_env is None or not enable_cache:
            # Validate template directory exists
            template_path = Path(template_dir)
            if not template_path.exists():
                raise ValueError(f"Template directory does not exist: {template_dir}")
            if not template_path.is_dir():
                raise ValueError(f"Template path is not a directory: {template_dir}")
            
            # Create Jinja2 environment
            self._jinja_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
                enable_async=True,
                cache_size=100 if enable_cache else 0
            )
            
            # Add custom filters if needed
            self._jinja_env.filters['currency'] = self._currency_filter
            self._jinja_env.filters['date_format'] = self._date_format_filter
        
        return self._jinja_env
    
    def _currency_filter(self, value: float, currency: str = "USD", locale: str = "en_US") -> str:
        """Format currency values."""
        if currency == "USD":
            return f"${value:,.2f}"
        elif currency == "EUR":
            return f"€{value:,.2f}"
        else:
            return f"{value:,.2f} {currency}"
    
    def _date_format_filter(self, value, format_string: str = "%Y-%m-%d") -> str:
        """Format date values."""
        if hasattr(value, 'strftime'):
            return value.strftime(format_string)
        else:
            return str(value)
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate template email handler configuration."""
        required_fields = [
            "template_dir", "template_name", 
            "smtp_host", "smtp_username", "smtp_password", "from_email"
        ]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required template email config field: {field}")
        
        # Validate template directory and file
        template_dir = config["template_dir"]
        template_name = config["template_name"]
        
        template_path = Path(template_dir)
        if not template_path.exists():
            raise ValueError(f"Template directory does not exist: {template_dir}")
        
        template_file = template_path / template_name
        if not template_file.exists():
            raise ValueError(f"Template file does not exist: {template_file}")
        
        # Validate SMTP config using parent handler
        smtp_config = {
            k: v for k, v in config.items() 
            if k in ["smtp_host", "smtp_port", "smtp_username", "smtp_password", 
                    "use_tls", "from_email", "from_name"]
        }
        await self._smtp_handler.validate_config(smtp_config)
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute template-based email sending.
        
        Expected input_data:
        - to_email: Recipient email address (required)
        - template_data: Data to render in template (required)
        - subject_template: Subject template string (optional, can be in template file)
        - reply_to: Reply-to email (optional)
        - locale: Template locale for internationalization (optional, default: 'en')
        """
        try:
            # Extract configuration
            template_dir = config["template_dir"]
            template_name = config["template_name"]
            enable_cache = config.get("template_cache", True)
            
            # Extract input data
            to_email = input_data.get("to_email")
            template_data = input_data.get("template_data", {})
            subject_template = input_data.get("subject_template")
            reply_to = input_data.get("reply_to")
            locale = input_data.get("locale", "en")
            
            if not to_email:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message="Missing required field: to_email"
                )
            
            # Add context data to template data
            enhanced_template_data = {
                **template_data,
                "locale": locale,
                "tenant_id": context.tenant_id if hasattr(context, 'tenant_id') else None,
                "schema": context.schema if hasattr(context, 'schema') else None,
                "timestamp": context.created_at if hasattr(context, 'created_at') else None
            }
            
            # Get Jinja2 environment and load template
            jinja_env = self._get_jinja_environment(template_dir, enable_cache)
            
            try:
                template = jinja_env.get_template(template_name)
            except TemplateError as e:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message=f"Template loading error: {str(e)}",
                    error_details={
                        "template_dir": template_dir,
                        "template_name": template_name,
                        "error_type": "TemplateError"
                    }
                )
            
            # Render HTML content
            try:
                html_content = await template.render_async(**enhanced_template_data)
            except TemplateError as e:
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message=f"Template rendering error: {str(e)}",
                    error_details={
                        "template_name": template_name,
                        "error_type": "TemplateRenderError"
                    }
                )
            
            # Render subject
            subject = "Email Notification"  # Default subject
            
            if subject_template:
                # Use provided subject template
                try:
                    subject_tmpl = Template(subject_template)
                    subject = subject_tmpl.render(**enhanced_template_data)
                except TemplateError as e:
                    return ExecutionResult(
                        success=False,
                        output_data={},
                        error_message=f"Subject template rendering error: {str(e)}",
                        error_details={
                            "subject_template": subject_template,
                            "error_type": "SubjectRenderError"
                        }
                    )
            else:
                # Try to extract subject from template variables or blocks
                if 'email_subject' in enhanced_template_data:
                    subject = str(enhanced_template_data['email_subject'])
                elif hasattr(template.module, 'EMAIL_SUBJECT'):
                    subject = template.module.EMAIL_SUBJECT
            
            # Generate plain text version from HTML
            plain_text_content = self._html_to_text(html_content)
            
            # Prepare SMTP handler input
            smtp_input = {
                "to_email": to_email,
                "subject": subject,
                "body": plain_text_content,
                "html_body": html_content
            }
            
            if reply_to:
                smtp_input["reply_to"] = reply_to
            
            # Extract SMTP config
            smtp_config = {
                k: v for k, v in config.items() 
                if k in ["smtp_host", "smtp_port", "smtp_username", "smtp_password", 
                        "use_tls", "from_email", "from_name", "timeout_seconds"]
            }
            
            # Execute email sending via SMTP handler
            smtp_result = await self._smtp_handler.execute(smtp_config, smtp_input, context)
            
            if smtp_result.success:
                # Enhance success result with template info
                enhanced_output = {
                    **smtp_result.output_data,
                    "template_name": template_name,
                    "template_data_keys": list(template_data.keys()),
                    "locale": locale,
                    "content_length": len(html_content)
                }
                
                return ExecutionResult(
                    success=True,
                    output_data=enhanced_output
                )
            else:
                # Return SMTP error with template context
                return ExecutionResult(
                    success=False,
                    output_data={},
                    error_message=smtp_result.error_message,
                    error_details={
                        **smtp_result.error_details,
                        "template_name": template_name,
                        "template_dir": template_dir
                    }
                )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Template email sending failed: {str(e)}",
                error_details={
                    "error_type": type(e).__name__,
                    "template_name": config.get("template_name"),
                    "to_email": input_data.get("to_email")
                }
            )
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text."""
        try:
            # Simple HTML to text conversion
            import re
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            
            # Convert common HTML entities
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&#39;', "'")
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
            
        except Exception:
            # Fallback to original content if conversion fails
            return html_content
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for template email sending."""
        # Template rendering + SMTP sending
        return config.get("timeout_seconds", 30) + 15
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check by validating template and SMTP connection."""
        try:
            # Check template availability
            template_dir = config["template_dir"]
            template_name = config["template_name"]
            enable_cache = config.get("template_cache", True)
            
            template_path = Path(template_dir) / template_name
            if not template_path.exists():
                return {
                    "healthy": False,
                    "status": "Template file not found",
                    "details": {
                        "template_path": str(template_path),
                        "error_type": "TemplateNotFound"
                    }
                }
            
            # Test template loading
            try:
                jinja_env = self._get_jinja_environment(template_dir, enable_cache)
                template = jinja_env.get_template(template_name)
                
                # Test render with minimal data
                test_render = await template.render_async(test_data="health_check")
                
            except Exception as e:
                return {
                    "healthy": False,
                    "status": f"Template error: {str(e)}",
                    "details": {
                        "template_name": template_name,
                        "error_type": type(e).__name__
                    }
                }
            
            # Check SMTP health via parent handler
            smtp_config = {
                k: v for k, v in config.items() 
                if k in ["smtp_host", "smtp_port", "smtp_username", "smtp_password", 
                        "use_tls", "from_email", "from_name"]
            }
            
            smtp_health = await self._smtp_handler.health_check(smtp_config)
            
            if smtp_health["healthy"]:
                return {
                    "healthy": True,
                    "status": "Template and SMTP connection healthy",
                    "details": {
                        "template_name": template_name,
                        "template_size": len(test_render),
                        "smtp_status": smtp_health["status"]
                    }
                }
            else:
                return {
                    "healthy": False,
                    "status": f"SMTP connection issue: {smtp_health['status']}",
                    "details": {
                        "template_name": template_name,
                        "smtp_details": smtp_health["details"]
                    }
                }
        
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Template email health check failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__,
                    "template_name": config.get("template_name")
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for template email handler."""
        return {
            "type": "object",
            "properties": {
                "template_dir": {
                    "type": "string",
                    "description": "Directory containing email templates"
                },
                "template_name": {
                    "type": "string",
                    "description": "Template file name (e.g., 'welcome.html')"
                },
                "template_cache": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable template caching"
                },
                "smtp_host": {
                    "type": "string",
                    "description": "SMTP server hostname"
                },
                "smtp_port": {
                    "type": "integer",
                    "default": 587,
                    "description": "SMTP server port"
                },
                "smtp_username": {
                    "type": "string",
                    "description": "SMTP username"
                },
                "smtp_password": {
                    "type": "string",
                    "description": "SMTP password"
                },
                "use_tls": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to use TLS encryption"
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
                "timeout_seconds": {
                    "type": "integer",
                    "default": 30,
                    "description": "Execution timeout in seconds"
                }
            },
            "required": ["template_dir", "template_name", "smtp_host", "smtp_username", "smtp_password", "from_email"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for template email handler."""
        return {
            "type": "object",
            "properties": {
                "to_email": {
                    "type": "string",
                    "format": "email",
                    "description": "Recipient email address"
                },
                "template_data": {
                    "type": "object",
                    "description": "Data to render in template",
                    "default": {}
                },
                "subject_template": {
                    "type": "string",
                    "description": "Subject template string (optional)"
                },
                "reply_to": {
                    "type": "string",
                    "format": "email",
                    "description": "Reply-to email address (optional)"
                },
                "locale": {
                    "type": "string",
                    "default": "en",
                    "description": "Template locale for internationalization"
                }
            },
            "required": ["to_email", "template_data"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for template email handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message_id": {"type": "string"},
                "from_email": {"type": "string"},
                "to_email": {"type": "string"},
                "subject": {"type": "string"},
                "template_name": {"type": "string"},
                "template_data_keys": {"type": "array", "items": {"type": "string"}},
                "locale": {"type": "string"},
                "content_length": {"type": "integer"}
            },
            "required": ["success"]
        }