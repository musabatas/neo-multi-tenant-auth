"""Search events query for platform events infrastructure.

This module handles ONLY event search operations following maximum separation architecture.
Single responsibility: Search and retrieve events with advanced filtering from neo_commons.platform system.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

from ...core.protocols import EventRepository
from ...core.entities import DomainEvent
from ...core.value_objects import EventId
from ...core.exceptions import EventDispatchFailed
from .....core.value_objects import UserId
from .....utils import utc_now


class SearchScope(Enum):
    """Search scope options."""
    ALL = "all"                    # Search all events
    ACTIVE = "active"              # Search only active/recent events
    ARCHIVED = "archived"          # Search archived events
    FAILED = "failed"              # Search failed events only


class SearchOperator(Enum):
    """Search operators for field matching."""
    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class SearchFilter:
    """Individual search filter."""
    field: str
    operator: SearchOperator
    value: Union[str, int, float, List[Any], datetime]
    case_sensitive: bool = False


@dataclass
class SearchEventsData:
    """Data required to search events.
    
    Contains all the search criteria and options for event retrieval.
    Separates query parameters from business logic following CQRS patterns.
    """
    # Text search
    query_text: Optional[str] = None          # Full-text search query
    search_fields: List[str] = field(default_factory=lambda: ["event_type", "source", "payload"])
    
    # Structured filtering
    filters: List[SearchFilter] = field(default_factory=list)
    event_types: Optional[List[str]] = None
    sources: Optional[List[str]] = None
    
    # Time range filtering
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    last_hours: Optional[int] = None
    last_days: Optional[int] = None
    
    # Status and scope
    search_scope: SearchScope = SearchScope.ALL
    include_archived: bool = False
    include_failed: bool = True
    
    # Payload search
    payload_filters: Dict[str, Any] = field(default_factory=dict)
    payload_contains: Optional[str] = None
    
    # Context filtering
    tenant_id: Optional[str] = None
    user_id: Optional[UserId] = None
    correlation_id: Optional[str] = None
    
    # Result options
    include_payload: bool = True
    include_metadata: bool = True
    include_related_actions: bool = False
    
    # Pagination and sorting
    limit: int = 100
    offset: int = 0
    sort_by: str = "occurred_at"
    sort_order: str = "desc"
    
    # Advanced options
    highlight_matches: bool = False           # Highlight search matches in results
    faceted_search: bool = False             # Include faceted search results
    aggregations: List[str] = field(default_factory=list)  # Fields to aggregate
    
    def __post_init__(self):
        """Validate search parameters after initialization."""
        # Set time range based on last_hours or last_days
        if self.last_hours:
            self.start_date = utc_now() - timedelta(hours=self.last_hours)
            self.end_date = utc_now()
        elif self.last_days:
            self.start_date = utc_now() - timedelta(days=self.last_days)
            self.end_date = utc_now()
        
        # Validate time range
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        
        # Validate pagination
        if self.limit < 1 or self.limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        
        if self.offset < 0:
            raise ValueError("offset must be non-negative")
        
        # Validate sort options
        valid_sort_fields = ["occurred_at", "event_type", "source", "created_at"]
        if self.sort_by not in valid_sort_fields:
            raise ValueError(f"Invalid sort_by field. Must be one of: {valid_sort_fields}")
        
        if self.sort_order not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        
        # Set default search fields if empty
        if not self.search_fields:
            self.search_fields = ["event_type", "source", "payload"]


@dataclass
class EventSearchMatch:
    """Individual event search result with match information."""
    event: DomainEvent
    match_score: float                        # Relevance score (0.0-1.0)
    matched_fields: List[str]                 # Fields that matched the search
    highlights: Dict[str, List[str]] = field(default_factory=dict)  # Search highlights
    
    # Additional context
    related_events_count: Optional[int] = None
    action_executions_count: Optional[int] = None


@dataclass
class SearchFacet:
    """Faceted search result for a field."""
    field: str
    values: List[Dict[str, Any]]              # [{"value": "...", "count": N}, ...]


@dataclass
class SearchAggregation:
    """Aggregation result for a field."""
    field: str
    aggregation_type: str                     # count, sum, avg, min, max
    value: Union[int, float, str]


@dataclass
class SearchEventsResult:
    """Result of event search query.
    
    Contains the search results with relevance scoring and metadata.
    Provides comprehensive search information for analysis and debugging.
    """
    events: List[EventSearchMatch]
    total_count: int
    has_more: bool
    next_offset: Optional[int]
    
    # Search metadata
    query_duration_ms: float
    search_query: str
    filters_applied: Dict[str, Any]
    
    # Search analytics
    facets: List[SearchFacet] = field(default_factory=list)
    aggregations: List[SearchAggregation] = field(default_factory=list)
    
    # Query suggestions (for typos, etc.)
    suggestions: List[str] = field(default_factory=list)
    
    success: bool = True
    message: str = "Event search completed successfully"


class SearchEventsQuery:
    """Query to search events with advanced filtering and relevance.
    
    Handles event search with full-text search, structured filtering,
    faceted search, and performance optimization for large datasets.
    
    Single responsibility: ONLY event search logic.
    Uses dependency injection through protocols for clean architecture.
    """
    
    def __init__(self, repository: EventRepository):
        """Initialize query with required dependencies.
        
        Args:
            repository: Event repository for event search access
        """
        self._repository = repository
    
    async def execute(self, data: SearchEventsData) -> SearchEventsResult:
        """Execute event search query.
        
        Performs comprehensive event search with text search, filtering,
        relevance scoring, and optional faceted search.
        
        Args:
            data: Search parameters and criteria
            
        Returns:
            SearchEventsResult with events and metadata
            
        Raises:
            EventDispatchFailed: If search operation fails
            ValueError: If search parameters are invalid
        """
        start_time = utc_now()
        
        try:
            # Build search query
            search_query = self._build_search_query(data)
            
            # Execute search with repository
            search_result = await self._execute_search(data, search_query)
            
            # Process and score results
            scored_matches = self._score_and_process_results(search_result, data)
            
            # Get facets if requested
            facets = []
            if data.faceted_search:
                facets = await self._get_search_facets(data, search_query)
            
            # Get aggregations if requested
            aggregations = []
            if data.aggregations:
                aggregations = await self._get_aggregations(data, search_query)
            
            # Calculate search duration
            duration_ms = (utc_now() - start_time).total_seconds() * 1000
            
            # Determine pagination info
            has_more = len(scored_matches) == data.limit
            next_offset = data.offset + len(scored_matches) if has_more else None
            
            # Generate query suggestions (basic implementation)
            suggestions = self._generate_suggestions(data.query_text) if data.query_text else []
            
            # Create result
            result = SearchEventsResult(
                events=scored_matches,
                total_count=search_result.get("total_count", len(scored_matches)),
                has_more=has_more,
                next_offset=next_offset,
                query_duration_ms=duration_ms,
                search_query=data.query_text or "",
                filters_applied=self._get_applied_filters(data),
                facets=facets,
                aggregations=aggregations,
                suggestions=suggestions,
                success=True,
                message=f"Found {len(scored_matches)} events matching search criteria"
            )
            
            return result
            
        except ValueError as e:
            raise EventDispatchFailed(f"Invalid event search query: {str(e)}")
        except Exception as e:
            raise EventDispatchFailed(f"Failed to search events: {str(e)}")
    
    def _build_search_query(self, data: SearchEventsData) -> Dict[str, Any]:
        """Build comprehensive search query from search data.
        
        Args:
            data: Search parameters
            
        Returns:
            Structured search query for repository
        """
        query = {}
        
        # Text search
        if data.query_text:
            query["text_search"] = {
                "query": data.query_text,
                "fields": data.search_fields,
                "highlight": data.highlight_matches
            }
        
        # Structured filters
        if data.filters:
            query["filters"] = []
            for filter_item in data.filters:
                query["filters"].append({
                    "field": filter_item.field,
                    "operator": filter_item.operator.value,
                    "value": filter_item.value,
                    "case_sensitive": filter_item.case_sensitive
                })
        
        # Event type filtering
        if data.event_types:
            query["event_types"] = data.event_types
        
        # Source filtering
        if data.sources:
            query["sources"] = data.sources
        
        # Time range
        if data.start_date:
            query["start_date"] = data.start_date
        
        if data.end_date:
            query["end_date"] = data.end_date
        
        # Scope and status
        query["search_scope"] = data.search_scope.value
        query["include_archived"] = data.include_archived
        query["include_failed"] = data.include_failed
        
        # Payload search
        if data.payload_filters:
            query["payload_filters"] = data.payload_filters
        
        if data.payload_contains:
            query["payload_contains"] = data.payload_contains
        
        # Context filtering
        if data.tenant_id:
            query["tenant_id"] = data.tenant_id
        
        if data.user_id:
            query["user_id"] = str(data.user_id)
        
        if data.correlation_id:
            query["correlation_id"] = data.correlation_id
        
        # Include options
        query["include_payload"] = data.include_payload
        query["include_metadata"] = data.include_metadata
        query["include_related_actions"] = data.include_related_actions
        
        return query
    
    async def _execute_search(self, data: SearchEventsData, search_query: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the search query against the repository.
        
        Args:
            data: Search parameters
            search_query: Built search query
            
        Returns:
            Repository search result
        """
        # Use repository's advanced search method
        result = await self._repository.search_events(
            filters=search_query,
            sort_by=data.sort_by,
            sort_order=data.sort_order,
            limit=data.limit,
            offset=data.offset
        )
        
        return result
    
    def _score_and_process_results(self, search_result: Dict[str, Any], data: SearchEventsData) -> List[EventSearchMatch]:
        """Score and process search results for relevance.
        
        Args:
            search_result: Raw repository search result
            data: Search parameters
            
        Returns:
            List of scored event matches
        """
        events = search_result.get("events", [])
        matches = []
        
        for event in events:
            # Calculate relevance score
            score = self._calculate_relevance_score(event, data)
            
            # Identify matched fields
            matched_fields = self._identify_matched_fields(event, data)
            
            # Generate highlights if requested
            highlights = {}
            if data.highlight_matches and data.query_text:
                highlights = self._generate_highlights(event, data.query_text, data.search_fields)
            
            # Get additional context if requested
            related_events_count = None
            action_executions_count = None
            
            if data.include_related_actions:
                # In a complete implementation, query for related actions
                action_executions_count = 0  # Placeholder
            
            # Create search match
            match = EventSearchMatch(
                event=event,
                match_score=score,
                matched_fields=matched_fields,
                highlights=highlights,
                related_events_count=related_events_count,
                action_executions_count=action_executions_count
            )
            
            matches.append(match)
        
        # Sort by relevance score if text search was used
        if data.query_text:
            matches.sort(key=lambda m: m.match_score, reverse=True)
        
        return matches
    
    def _calculate_relevance_score(self, event: DomainEvent, data: SearchEventsData) -> float:
        """Calculate relevance score for an event.
        
        Args:
            event: Event to score
            data: Search parameters
            
        Returns:
            Relevance score (0.0-1.0)
        """
        if not data.query_text:
            return 1.0  # No text search, all results equally relevant
        
        score = 0.0
        query_lower = data.query_text.lower()
        
        # Score based on exact matches in different fields
        if query_lower in event.event_type.lower():
            score += 0.4
        
        if query_lower in event.source.lower():
            score += 0.3
        
        # Score based on payload content (basic implementation)
        payload_str = str(event.payload).lower()
        if query_lower in payload_str:
            score += 0.2
        
        # Time-based boost (more recent events get higher scores)
        age_hours = (utc_now() - event.occurred_at).total_seconds() / 3600
        if age_hours < 24:
            score += 0.1  # Recent events get boost
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _identify_matched_fields(self, event: DomainEvent, data: SearchEventsData) -> List[str]:
        """Identify which fields matched the search query.
        
        Args:
            event: Event to analyze
            data: Search parameters
            
        Returns:
            List of field names that matched
        """
        if not data.query_text:
            return []
        
        matched = []
        query_lower = data.query_text.lower()
        
        if query_lower in event.event_type.lower():
            matched.append("event_type")
        
        if query_lower in event.source.lower():
            matched.append("source")
        
        if query_lower in str(event.payload).lower():
            matched.append("payload")
        
        return matched
    
    def _generate_highlights(self, event: DomainEvent, query: str, search_fields: List[str]) -> Dict[str, List[str]]:
        """Generate search result highlights.
        
        Args:
            event: Event to highlight
            query: Search query
            search_fields: Fields to search in
            
        Returns:
            Dictionary of highlighted snippets by field
        """
        highlights = {}
        query_lower = query.lower()
        
        for field in search_fields:
            if field == "event_type" and query_lower in event.event_type.lower():
                highlights["event_type"] = [f"<mark>{query}</mark>"]
            
            elif field == "source" and query_lower in event.source.lower():
                highlights["source"] = [f"<mark>{query}</mark>"]
            
            elif field == "payload":
                payload_str = str(event.payload)
                if query_lower in payload_str.lower():
                    # Simple highlight implementation
                    highlights["payload"] = [f"...{query}..."]
        
        return highlights
    
    async def _get_search_facets(self, data: SearchEventsData, search_query: Dict[str, Any]) -> List[SearchFacet]:
        """Get faceted search results.
        
        Args:
            data: Search parameters
            search_query: Built search query
            
        Returns:
            List of search facets
        """
        facets = []
        
        # Get facets from repository (if supported)
        # This would typically use a specialized search service like Elasticsearch
        
        # Example facets
        facets.append(SearchFacet(
            field="event_type",
            values=[
                {"value": "user.created", "count": 45},
                {"value": "order.placed", "count": 32},
                {"value": "payment.processed", "count": 28}
            ]
        ))
        
        return facets
    
    async def _get_aggregations(self, data: SearchEventsData, search_query: Dict[str, Any]) -> List[SearchAggregation]:
        """Get search aggregations.
        
        Args:
            data: Search parameters
            search_query: Built search query
            
        Returns:
            List of aggregations
        """
        aggregations = []
        
        for field in data.aggregations:
            # Calculate aggregation (placeholder implementation)
            if field == "event_count_by_day":
                aggregations.append(SearchAggregation(
                    field=field,
                    aggregation_type="count",
                    value=150
                ))
        
        return aggregations
    
    def _generate_suggestions(self, query_text: str) -> List[str]:
        """Generate search suggestions for query improvement.
        
        Args:
            query_text: Original search query
            
        Returns:
            List of suggested queries
        """
        # Basic suggestion implementation
        suggestions = []
        
        # Common typo corrections (placeholder)
        common_corrections = {
            "usr": "user",
            "ordr": "order", 
            "paymnt": "payment"
        }
        
        words = query_text.lower().split()
        corrected = []
        
        for word in words:
            if word in common_corrections:
                corrected.append(common_corrections[word])
            else:
                corrected.append(word)
        
        corrected_query = " ".join(corrected)
        if corrected_query != query_text.lower():
            suggestions.append(corrected_query)
        
        return suggestions
    
    def _get_applied_filters(self, data: SearchEventsData) -> Dict[str, Any]:
        """Get summary of applied filters for result metadata.
        
        Args:
            data: Search parameters
            
        Returns:
            Dictionary of applied filters
        """
        applied = {}
        
        if data.query_text:
            applied["query_text"] = data.query_text
        
        if data.event_types:
            applied["event_types"] = data.event_types
        
        if data.sources:
            applied["sources"] = data.sources
        
        if data.search_scope != SearchScope.ALL:
            applied["search_scope"] = data.search_scope.value
        
        if data.start_date:
            applied["start_date"] = data.start_date.isoformat()
        
        if data.end_date:
            applied["end_date"] = data.end_date.isoformat()
        
        if data.tenant_id:
            applied["tenant_id"] = data.tenant_id
        
        if data.filters:
            applied["custom_filters"] = len(data.filters)
        
        applied["limit"] = data.limit
        applied["offset"] = data.offset
        applied["sort_by"] = data.sort_by
        applied["sort_order"] = data.sort_order
        
        return applied


def create_search_events_query(repository: EventRepository) -> SearchEventsQuery:
    """Factory function to create SearchEventsQuery instance.
    
    Args:
        repository: Event repository for event search access
        
    Returns:
        Configured SearchEventsQuery instance
    """
    return SearchEventsQuery(repository=repository)