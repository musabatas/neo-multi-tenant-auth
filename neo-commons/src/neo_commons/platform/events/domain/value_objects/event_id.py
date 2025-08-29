"""Event ID value object using existing core implementation."""

from neo_commons.core.value_objects.identifiers import EventId as CoreEventId

# Re-export core EventId to maintain domain layer naming
EventId = CoreEventId