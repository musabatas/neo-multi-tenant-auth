"""Handler type value object for platform actions infrastructure.

Pure platform infrastructure - used by all business features.
"""

from enum import Enum


class HandlerType(Enum):
    """Action handler type enumeration.
    
    Represents the type of handler that will execute the action:
    - WEBHOOK: HTTP webhook delivery
    - EMAIL: Email notification
    - FUNCTION: Function execution (local or serverless)
    - WORKFLOW: Workflow execution
    - SMS: SMS notification
    - SLACK: Slack integration
    - TEAMS: Microsoft Teams integration
    - CUSTOM: Custom handler type
    """
    
    WEBHOOK = "webhook"
    EMAIL = "email"
    FUNCTION = "function"
    WORKFLOW = "workflow"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    CUSTOM = "custom"
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    @property
    def requires_url(self) -> bool:
        """Check if this handler type requires a URL configuration."""
        return self in (HandlerType.WEBHOOK, HandlerType.SLACK, HandlerType.TEAMS)
    
    @property
    def is_notification_type(self) -> bool:
        """Check if this handler is a notification type."""
        return self in (HandlerType.EMAIL, HandlerType.SMS, HandlerType.SLACK, HandlerType.TEAMS)