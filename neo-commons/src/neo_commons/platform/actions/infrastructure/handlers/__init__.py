"""Platform actions infrastructure handlers.

Action handler implementations that bridge between action execution and external adapters.
Each handler focuses on single action type following maximum separation architecture.

Maximum separation architecture:
- webhook_handler.py: ONLY webhook action handling
- email_handler.py: ONLY email action handling  
- sms_handler.py: ONLY SMS action handling
- slack_handler.py: ONLY Slack action handling

Pure platform infrastructure - used by all business features.
"""

# Webhook Handler
from .webhook_handler import (
    WebhookHandler,
    create_webhook_handler
)

# Email Handler
from .email_handler import (
    EmailHandler,
    create_email_handler
)

# SMS Handler
from .sms_handler import (
    SMSHandler,
    create_sms_handler
)

# Slack Handler  
from .slack_handler import (
    SlackHandler,
    create_slack_handler
)

__all__ = [
    # Webhook Handler
    "WebhookHandler",
    "create_webhook_handler",
    
    # Email Handler
    "EmailHandler", 
    "create_email_handler",
    
    # SMS Handler
    "SMSHandler",
    "create_sms_handler",
    
    # Slack Handler
    "SlackHandler",
    "create_slack_handler",
]