"""Platform events infrastructure adapters.

External service adapters for event-driven notifications and integrations.
Each adapter handles a single external service following single responsibility principle.

Maximum separation architecture:
- http_webhook_adapter.py: HTTP webhook delivery only
- email_notification_adapter.py: SMTP email notifications only
- slack_notification_adapter.py: Slack webhook messages only  
- sms_notification_adapter.py: Twilio SMS delivery only

Pure platform infrastructure - used by all business features.
"""

# HTTP Webhook Adapter
from .http_webhook_adapter import (
    WebhookConfiguration,
    HTTPWebhookAdapter,
    create_webhook_adapter
)

# Email Notification Adapter
from .email_notification_adapter import (
    EmailConfiguration,
    EmailTemplate,
    EmailNotificationAdapter,
    create_email_adapter
)

# Slack Notification Adapter
from .slack_notification_adapter import (
    SlackConfiguration,
    SlackMessage,
    SlackNotificationAdapter,
    create_slack_adapter
)

# SMS Notification Adapter  
from .sms_notification_adapter import (
    TwilioConfiguration,
    SMSMessage,
    SMSNotificationAdapter,
    create_sms_adapter
)

__all__ = [
    # HTTP Webhook
    "WebhookConfiguration",
    "HTTPWebhookAdapter", 
    "create_webhook_adapter",
    
    # Email Notifications
    "EmailConfiguration",
    "EmailTemplate",
    "EmailNotificationAdapter",
    "create_email_adapter",
    
    # Slack Notifications
    "SlackConfiguration",
    "SlackMessage", 
    "SlackNotificationAdapter",
    "create_slack_adapter",
    
    # SMS Notifications
    "TwilioConfiguration",
    "SMSMessage",
    "SMSNotificationAdapter",
    "create_sms_adapter",
]