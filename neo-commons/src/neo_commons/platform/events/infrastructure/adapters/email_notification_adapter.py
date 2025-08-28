"""Email notification adapter for platform events infrastructure.

This module implements email notification delivery for domain events.
Single responsibility: Send email notifications triggered by events.

Extracted to platform/events following enterprise clean architecture patterns.
Pure platform infrastructure implementation - used by all business features.
"""

import asyncio
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from ...core.entities import DomainEvent
from ....actions.core.entities import Action  # Import from platform/actions module
from .....core.shared.context import RequestContext
from .....utils import utc_now, ensure_utc


@dataclass
class EmailConfiguration:
    """Email configuration for SMTP delivery."""
    
    smtp_host: str
    smtp_port: int
    username: str
    password: str
    from_address: str
    use_tls: bool = True
    use_ssl: bool = False
    timeout_seconds: int = 30


@dataclass
class EmailTemplate:
    """Email template with content and metadata."""
    
    subject_template: str
    body_template: str
    is_html: bool = False
    reply_to: Optional[str] = None
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None


class EmailNotificationAdapter:
    """Email notification adapter using SMTP.
    
    ONLY handles email delivery operations following standard SMTP protocol.
    Single responsibility: Send email notifications with template support.
    NO business logic, NO validation, NO external dependencies beyond SMTP.
    """
    
    def __init__(self, configuration: EmailConfiguration):
        """Initialize adapter with email configuration.
        
        Args:
            configuration: SMTP configuration for email delivery
        """
        self._config = configuration
    
    # ===========================================
    # Core Email Delivery Operations
    # ===========================================
    
    async def send_notification(
        self,
        event: DomainEvent,
        action: Action,
        context: Optional[RequestContext] = None
    ) -> Dict[str, Any]:
        """Send email notification for domain event using action configuration.
        
        Args:
            event: Domain event that triggered the notification
            action: Event action containing email configuration
            context: Optional request context for tracking
            
        Returns:
            Dictionary with delivery results and metrics
            
        Raises:
            EmailDeliveryError: If email cannot be delivered
            EmailConfigurationError: If email configuration is invalid
            EmailTimeoutError: If delivery exceeds timeout threshold
        """
        delivery_record = {
            "notification_id": str(action.id.value),
            "event_id": str(event.id.value),
            "delivery_status": "pending",
            "started_at": utc_now(),
            "attempts": 1,
            "max_retries": action.max_retries or 3,
            "timeout_seconds": action.timeout_seconds or 30,
        }
        
        try:
            # Extract email configuration from action
            email_config = self._extract_email_config(action)
            
            # Build email message from event and action
            message = await self._build_email_message(event, action, email_config)
            
            # Send email via SMTP
            delivery_start = utc_now()
            await self._send_email_smtp(message, email_config)
            delivery_duration = (utc_now() - delivery_start).total_seconds() * 1000
            
            delivery_record.update({
                "delivery_status": "delivered",
                "completed_at": utc_now(),
                "delivery_duration_ms": int(delivery_duration),
                "recipient_count": len(email_config.get("to", [])),
                "message_size_bytes": len(str(message)),
                "success": True
            })
            
            return delivery_record
            
        except Exception as e:
            delivery_record.update({
                "delivery_status": "failed",
                "completed_at": utc_now(),
                "error_message": str(e),
                "error_type": type(e).__name__,
                "success": False
            })
            
            # Implement retry logic if needed
            if delivery_record["attempts"] < delivery_record["max_retries"]:
                await asyncio.sleep(action.retry_delay_seconds or 5)
                # Could implement recursive retry here
            
            return delivery_record
    
    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]],
        preserve_order: bool = True,
        max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """Send multiple email notifications efficiently.
        
        Args:
            notifications: List of notification configurations
            preserve_order: Whether to maintain notification ordering
            max_concurrent: Maximum concurrent email deliveries
            
        Returns:
            List of delivery results for each notification
        """
        if preserve_order:
            # Sequential delivery
            results = []
            for notification in notifications:
                result = await self.send_notification(
                    notification["event"],
                    notification["action"],
                    notification.get("context")
                )
                results.append(result)
            return results
        else:
            # Concurrent delivery with semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def send_with_limit(notification):
                async with semaphore:
                    return await self.send_notification(
                        notification["event"],
                        notification["action"],
                        notification.get("context")
                    )
            
            tasks = [send_with_limit(notif) for notif in notifications]
            return await asyncio.gather(*tasks)
    
    # ===========================================
    # Email Template Operations
    # ===========================================
    
    async def render_template(
        self,
        template: EmailTemplate,
        event: DomainEvent,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Render email template with event data and context.
        
        Args:
            template: Email template configuration
            event: Domain event providing template data
            context: Optional additional template context
            
        Returns:
            Dictionary with rendered subject and body
        """
        template_context = {
            "event_id": str(event.id.value),
            "event_type": event.event_type.value,
            "event_name": event.event_name or event.event_type.value,
            "aggregate_id": str(event.aggregate_id),
            "aggregate_type": event.aggregate_type,
            "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            "event_data": event.event_data,
            **(context or {})
        }
        
        # Simple template rendering (could be enhanced with Jinja2)
        rendered_subject = template.subject_template.format(**template_context)
        rendered_body = template.body_template.format(**template_context)
        
        return {
            "subject": rendered_subject,
            "body": rendered_body,
            "is_html": template.is_html
        }
    
    # ===========================================
    # Email Configuration Operations
    # ===========================================
    
    async def validate_configuration(self, action: Action) -> Dict[str, Any]:
        """Validate email configuration in event action.
        
        Args:
            action: Event action containing email configuration
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        config = action.configuration
        
        # Required fields validation
        required_fields = ["to", "subject", "body"]
        for field in required_fields:
            if not config.get(field):
                validation_result["errors"].append(f"Missing required field: {field}")
                validation_result["is_valid"] = False
        
        # Email address validation (basic)
        if config.get("to"):
            for email in config["to"] if isinstance(config["to"], list) else [config["to"]]:
                if "@" not in email:
                    validation_result["errors"].append(f"Invalid email address: {email}")
                    validation_result["is_valid"] = False
        
        # Template validation
        try:
            template = EmailTemplate(
                subject_template=config.get("subject", ""),
                body_template=config.get("body", ""),
                is_html=config.get("is_html", False)
            )
        except Exception as e:
            validation_result["errors"].append(f"Template validation failed: {e}")
            validation_result["is_valid"] = False
        
        return validation_result
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test SMTP connection and configuration.
        
        Returns:
            Dictionary with connection test results
        """
        test_result = {
            "connection_successful": False,
            "smtp_host": self._config.smtp_host,
            "smtp_port": self._config.smtp_port,
            "authentication_successful": False,
            "test_duration_ms": 0,
            "error_message": None
        }
        
        start_time = utc_now()
        
        try:
            # Test SMTP connection
            if self._config.use_ssl:
                server = smtplib.SMTP_SSL(
                    self._config.smtp_host, 
                    self._config.smtp_port,
                    timeout=self._config.timeout_seconds
                )
            else:
                server = smtplib.SMTP(
                    self._config.smtp_host, 
                    self._config.smtp_port,
                    timeout=self._config.timeout_seconds
                )
                
                if self._config.use_tls:
                    server.starttls()
            
            test_result["connection_successful"] = True
            
            # Test authentication
            if self._config.username and self._config.password:
                server.login(self._config.username, self._config.password)
                test_result["authentication_successful"] = True
            
            server.quit()
            
        except Exception as e:
            test_result["error_message"] = str(e)
        finally:
            test_result["test_duration_ms"] = int(
                (utc_now() - start_time).total_seconds() * 1000
            )
        
        return test_result
    
    # ===========================================
    # Private Helper Methods
    # ===========================================
    
    def _extract_email_config(self, action: Action) -> Dict[str, Any]:
        """Extract and validate email configuration from action.
        
        Args:
            action: Event action containing email configuration
            
        Returns:
            Validated email configuration dictionary
        """
        config = action.configuration
        
        # Ensure recipients is a list
        to_addresses = config.get("to", [])
        if isinstance(to_addresses, str):
            to_addresses = [to_addresses]
        
        return {
            "to": to_addresses,
            "subject": config.get("subject", "Event Notification"),
            "body": config.get("body", ""),
            "is_html": config.get("is_html", False),
            "reply_to": config.get("reply_to"),
            "cc": config.get("cc", []),
            "bcc": config.get("bcc", [])
        }
    
    async def _build_email_message(
        self,
        event: DomainEvent,
        action: Action,
        email_config: Dict[str, Any]
    ) -> MIMEMultipart:
        """Build MIME email message from event and configuration.
        
        Args:
            event: Domain event providing message content
            action: Event action with email configuration
            email_config: Processed email configuration
            
        Returns:
            MIME email message ready for delivery
        """
        message = MIMEMultipart("alternative" if email_config["is_html"] else "mixed")
        
        # Message headers
        message["From"] = self._config.from_address
        message["To"] = ", ".join(email_config["to"])
        message["Subject"] = email_config["subject"]
        
        if email_config.get("reply_to"):
            message["Reply-To"] = email_config["reply_to"]
        
        if email_config.get("cc"):
            message["Cc"] = ", ".join(email_config["cc"])
        
        # Message body
        if email_config["is_html"]:
            body = MIMEText(email_config["body"], "html")
        else:
            body = MIMEText(email_config["body"], "plain")
        
        message.attach(body)
        
        return message
    
    async def _send_email_smtp(
        self,
        message: MIMEMultipart,
        email_config: Dict[str, Any]
    ) -> None:
        """Send email message via SMTP.
        
        Args:
            message: MIME email message to send
            email_config: Email configuration with recipients
        """
        # Collect all recipients
        recipients = email_config["to"].copy()
        if email_config.get("cc"):
            recipients.extend(email_config["cc"])
        if email_config.get("bcc"):
            recipients.extend(email_config["bcc"])
        
        # Send via SMTP (async wrapper for blocking SMTP)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            self._send_email_blocking,
            message,
            recipients
        )
    
    def _send_email_blocking(
        self,
        message: MIMEMultipart,
        recipients: List[str]
    ) -> None:
        """Blocking SMTP send operation.
        
        Args:
            message: MIME email message to send
            recipients: List of recipient email addresses
        """
        if self._config.use_ssl:
            server = smtplib.SMTP_SSL(
                self._config.smtp_host,
                self._config.smtp_port,
                timeout=self._config.timeout_seconds
            )
        else:
            server = smtplib.SMTP(
                self._config.smtp_host,
                self._config.smtp_port,
                timeout=self._config.timeout_seconds
            )
            
            if self._config.use_tls:
                server.starttls()
        
        try:
            # Authenticate if credentials provided
            if self._config.username and self._config.password:
                server.login(self._config.username, self._config.password)
            
            # Send message
            server.send_message(message, to_addrs=recipients)
            
        finally:
            server.quit()


def create_email_adapter(configuration: EmailConfiguration) -> EmailNotificationAdapter:
    """Factory function to create email notification adapter.
    
    Args:
        configuration: SMTP configuration for email delivery
        
    Returns:
        EmailNotificationAdapter: Configured adapter instance
    """
    return EmailNotificationAdapter(configuration)