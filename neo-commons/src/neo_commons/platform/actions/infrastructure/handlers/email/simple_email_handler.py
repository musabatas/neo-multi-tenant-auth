"""Simple email action handler implementation."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult


class SimpleEmailHandler(ActionHandler):
    """
    Simple email handler using SMTP.
    
    Configuration:
    - smtp_host: SMTP server hostname
    - smtp_port: SMTP server port (default: 587)
    - smtp_username: SMTP username
    - smtp_password: SMTP password  
    - use_tls: Whether to use TLS (default: True)
    - from_email: From email address
    - from_name: From display name (optional)
    """
    
    @property
    def handler_name(self) -> str:
        return "simple_email_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["email"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate email handler configuration."""
        required_fields = ["smtp_host", "smtp_username", "smtp_password", "from_email"]
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required email config field: {field}")
        
        # Validate email format (basic check)
        from_email = config["from_email"]
        if "@" not in from_email:
            raise ValueError(f"Invalid from_email format: {from_email}")
        
        # Validate port if provided
        if "smtp_port" in config and not isinstance(config["smtp_port"], int):
            raise ValueError("smtp_port must be an integer")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute email sending.
        
        Expected input_data:
        - to_email: Recipient email address (required)
        - subject: Email subject (required)
        - body: Email body content (required)
        - html_body: HTML email content (optional)
        - reply_to: Reply-to email (optional)
        """
        try:
            # Validate input data
            required_fields = ["to_email", "subject", "body"]
            for field in required_fields:
                if field not in input_data:
                    return ExecutionResult(
                        success=False,
                        output_data={},
                        error_message=f"Missing required email input field: {field}"
                    )
            
            # Extract configuration
            smtp_host = config["smtp_host"]
            smtp_port = config.get("smtp_port", 587)
            smtp_username = config["smtp_username"]
            smtp_password = config["smtp_password"]
            use_tls = config.get("use_tls", True)
            from_email = config["from_email"]
            from_name = config.get("from_name")
            
            # Extract input data
            to_email = input_data["to_email"]
            subject = input_data["subject"]
            body = input_data["body"]
            html_body = input_data.get("html_body")
            reply_to = input_data.get("reply_to")
            
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
            msg["To"] = to_email
            
            if reply_to:
                msg["Reply-To"] = reply_to
            
            # Add body parts
            text_part = MIMEText(body, "plain", "utf-8")
            msg.attach(text_part)
            
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if use_tls:
                    server.starttls()
                
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
            
            return ExecutionResult(
                success=True,
                output_data={
                    "message_id": f"sent-to-{to_email}",
                    "from_email": from_email,
                    "to_email": to_email,
                    "subject": subject
                }
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Email sending failed: {str(e)}",
                error_details={
                    "smtp_host": config.get("smtp_host"),
                    "to_email": input_data.get("to_email"),
                    "error_type": type(e).__name__
                }
            )
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for email sending."""
        return config.get("timeout_seconds", 30)
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check by testing SMTP connection."""
        try:
            smtp_host = config["smtp_host"]
            smtp_port = config.get("smtp_port", 587)
            smtp_username = config["smtp_username"]
            smtp_password = config["smtp_password"]
            use_tls = config.get("use_tls", True)
            
            # Test connection
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if use_tls:
                    server.starttls()
                server.login(smtp_username, smtp_password)
            
            return {
                "healthy": True,
                "status": "SMTP connection successful",
                "details": {
                    "smtp_host": smtp_host,
                    "smtp_port": smtp_port
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "status": f"SMTP connection failed: {str(e)}",
                "details": {
                    "smtp_host": config.get("smtp_host"),
                    "smtp_port": config.get("smtp_port", 587),
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for email handler."""
        return {
            "type": "object",
            "properties": {
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
            "required": ["smtp_host", "smtp_username", "smtp_password", "from_email"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for email handler."""
        return {
            "type": "object",
            "properties": {
                "to_email": {
                    "type": "string",
                    "format": "email", 
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Plain text email body"
                },
                "html_body": {
                    "type": "string",
                    "description": "HTML email body (optional)"
                },
                "reply_to": {
                    "type": "string", 
                    "format": "email",
                    "description": "Reply-to email address (optional)"
                }
            },
            "required": ["to_email", "subject", "body"]
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for email handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message_id": {"type": "string"},
                "from_email": {"type": "string"},
                "to_email": {"type": "string"},
                "subject": {"type": "string"}
            },
            "required": ["success"]
        }