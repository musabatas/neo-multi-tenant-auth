"""WebhookEndpoint ID value object for platform events infrastructure.

Platform-specific value object following maximum separation architecture.
This value object is pure platform infrastructure - used by all business features.

Extracted to platform/events following enterprise clean architecture patterns.
"""

from dataclasses import dataclass
from uuid import UUID

from .....utils import generate_uuid_v7


@dataclass(frozen=True)
class WebhookEndpointId:
    """WebhookEndpoint ID value object with UUIDv7 support.
    
    Platform infrastructure value object for webhook endpoint identification.
    Uses UUIDv7 for time-ordering and better database performance.
    """
    
    value: UUID

    def __post_init__(self):
        """Validate WebhookEndpoint ID value."""
        if not isinstance(self.value, UUID):
            raise ValueError("WebhookEndpoint ID must be a UUID")

    @classmethod
    def generate(cls) -> "WebhookEndpointId":
        """Generate a new WebhookEndpoint ID using UUIDv7."""
        return cls(UUID(generate_uuid_v7()))
    
    @classmethod 
    def from_string(cls, id_str: str) -> "WebhookEndpointId":
        """Create WebhookEndpoint ID from string representation."""
        try:
            return cls(UUID(id_str))
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid WebhookEndpoint ID format: {id_str}") from e

    def __str__(self) -> str:
        """String representation of WebhookEndpoint ID."""
        return str(self.value)