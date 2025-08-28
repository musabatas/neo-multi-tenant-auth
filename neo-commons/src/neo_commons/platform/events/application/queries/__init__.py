"""Platform events application queries.

Queries handle read operations in the platform events system.
Following CQRS pattern - queries are separated from commands.

Each query file has single responsibility:
- get_event.py: ONLY single event retrieval
- get_event_history.py: ONLY event history retrieval
- get_delivery_stats.py: ONLY delivery statistics retrieval
- get_webhook_logs.py: ONLY webhook logs retrieval
- search_events.py: ONLY event search operations

Action-related queries have been moved to platform/actions module.
"""

# Import queries as they are created
from .get_event import GetEventQuery, GetEventData, GetEventResult
from .get_event_history import GetEventHistoryQuery, GetEventHistoryData, GetEventHistoryResult
from .get_delivery_stats import GetDeliveryStatsQuery, GetDeliveryStatsData, GetDeliveryStatsResult
from .get_webhook_logs import GetWebhookLogsQuery, GetWebhookLogsData, GetWebhookLogsResult
from .search_events import SearchEventsQuery, SearchEventsData, SearchEventsResult

__all__ = [
    "GetEventQuery",
    "GetEventData", 
    "GetEventResult",
    "GetEventHistoryQuery",
    "GetEventHistoryData",
    "GetEventHistoryResult",
    "GetDeliveryStatsQuery",
    "GetDeliveryStatsData",
    "GetDeliveryStatsResult",
    "GetWebhookLogsQuery",
    "GetWebhookLogsData",
    "GetWebhookLogsResult",
    "SearchEventsQuery",
    "SearchEventsData",
    "SearchEventsResult",
]