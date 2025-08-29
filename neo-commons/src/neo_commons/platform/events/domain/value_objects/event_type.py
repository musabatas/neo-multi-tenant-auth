"""Event type value object using existing core implementation."""

from neo_commons.core.value_objects.identifiers import EventType as CoreEventType

# Re-export core EventType to maintain domain layer naming
EventType = CoreEventType