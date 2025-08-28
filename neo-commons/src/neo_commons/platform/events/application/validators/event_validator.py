"""Event validator for platform events infrastructure.

This module handles ONLY event validation operations following maximum separation architecture.
Single responsibility: Validate domain events for business rules, data integrity, and platform constraints.

Pure application layer - no infrastructure concerns.
Contains business validation logic that goes beyond basic entity validation.
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from uuid import UUID

from ...core.entities import DomainEvent
from ...core.value_objects import EventId, EventType
from ...core.exceptions import InvalidEventConfiguration
from neo_commons.core.value_objects import UserId
from neo_commons.utils import utc_now


@dataclass
class EventValidationResult:
    """Result of event validation operation.
    
    Contains comprehensive validation feedback including all validation
    errors, warnings, and recommendations for event improvement.
    """
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    recommendations: List[str] = None
    validation_summary: Optional[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        if self.recommendations is None:
            self.recommendations = []


class EventValidator:
    """Event validator for comprehensive domain event validation.
    
    Single responsibility: Validate domain events against business rules,
    platform constraints, and data integrity requirements. Provides detailed
    validation feedback for event processing and webhook delivery.
    
    Following enterprise validation pattern with comprehensive rule checking.
    Pure application logic - delegates infrastructure concerns to protocols.
    """
    
    # Valid event type patterns
    VALID_CATEGORY_PATTERN = r'^[a-z_][a-z0-9_]*$'
    VALID_ACTION_PATTERN = r'^[a-z_][a-z0-9_]*$'
    
    # Maximum sizes for validation
    MAX_EVENT_TYPE_LENGTH = 100
    MAX_AGGREGATE_TYPE_LENGTH = 50
    MAX_EVENT_NAME_LENGTH = 255
    MAX_PAYLOAD_SIZE_BYTES = 1024 * 1024  # 1MB
    MAX_METADATA_SIZE_BYTES = 64 * 1024  # 64KB
    MAX_NESTED_DEPTH = 10
    
    # Reserved field names
    RESERVED_METADATA_FIELDS = {
        'id', 'event_type', 'aggregate_id', 'aggregate_type', 
        'occurred_at', 'created_at', 'processed_at'
    }
    
    # Common event categories and actions for validation
    COMMON_CATEGORIES = {
        'user', 'organization', 'team', 'project', 'order', 'payment',
        'subscription', 'notification', 'audit', 'system'
    }
    
    COMMON_ACTIONS = {
        'created', 'updated', 'deleted', 'activated', 'deactivated',
        'suspended', 'restored', 'archived', 'published', 'cancelled',
        'started', 'completed', 'failed', 'expired', 'renewed'
    }
    
    def __init__(self):
        """Initialize event validator with validation rules."""
        pass
    
    def validate_event(self, event: DomainEvent) -> EventValidationResult:
        """Validate a domain event comprehensively.
        
        Performs complete event validation including:
        1. Basic field validation
        2. Event type validation
        3. Data payload validation
        4. Metadata validation
        5. Business rule validation
        6. Performance validation
        
        Args:
            event: Domain event to validate
            
        Returns:
            EventValidationResult with comprehensive validation feedback
        """
        result = EventValidationResult(is_valid=True)
        
        try:
            # 1. Basic field validation
            self._validate_basic_fields(event, result)
            
            # 2. Event type validation
            self._validate_event_type(event, result)
            
            # 3. Data payload validation
            self._validate_event_data(event, result)
            
            # 4. Metadata validation
            self._validate_event_metadata(event, result)
            
            # 5. Business rule validation
            self._validate_business_rules(event, result)
            
            # 6. Performance validation
            self._validate_performance_constraints(event, result)
            
            # Final validation status
            result.is_valid = len(result.errors) == 0
            
            # Generate summary
            result.validation_summary = self._generate_validation_summary(result)
            
            return result
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation failed with exception: {str(e)}")
            result.validation_summary = "Event validation failed due to unexpected error"
            return result
    
    def validate_event_type_format(self, event_type: str) -> EventValidationResult:
        """Validate event type format only.
        
        Convenience method for validating event type format without
        requiring a full domain event. Useful for API validation.
        
        Args:
            event_type: Event type string to validate
            
        Returns:
            EventValidationResult with event type validation feedback
        """
        result = EventValidationResult(is_valid=True)
        
        if not event_type:
            result.errors.append("Event type cannot be empty")
            result.is_valid = False
            return result
        
        try:
            # Create temporary EventType to leverage existing validation
            temp_event_type = EventType(event_type)
            self._validate_event_type_business_rules(temp_event_type, result)
        except ValueError as e:
            result.errors.append(f"Invalid event type format: {str(e)}")
            result.is_valid = False
        
        return result
    
    def validate_payload_structure(self, payload: Dict[str, Any]) -> EventValidationResult:
        """Validate event payload structure only.
        
        Convenience method for validating payload structure without
        requiring a full domain event. Useful for API validation.
        
        Args:
            payload: Event payload dictionary to validate
            
        Returns:
            EventValidationResult with payload validation feedback
        """
        result = EventValidationResult(is_valid=True)
        
        if payload is None:
            payload = {}
        
        # Validate payload structure
        self._validate_payload_structure(payload, result, "event_data")
        self._validate_payload_size(payload, result, self.MAX_PAYLOAD_SIZE_BYTES, "event_data")
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def _validate_basic_fields(self, event: DomainEvent, result: EventValidationResult) -> None:
        """Validate basic required fields of the domain event."""
        # Event ID validation
        if not event.id or not event.id.value:
            result.errors.append("Event ID is required")
        
        # Aggregate ID validation
        if not event.aggregate_id:
            result.errors.append("Aggregate ID is required")
        else:
            # Check if aggregate_id looks like UUIDv7 (time-ordered)
            if not self._is_likely_uuid_v7(event.aggregate_id):
                result.warnings.append("Aggregate ID should be UUIDv7 for better performance")
        
        # Aggregate type validation
        if not event.aggregate_type:
            result.errors.append("Aggregate type is required")
        elif len(event.aggregate_type) > self.MAX_AGGREGATE_TYPE_LENGTH:
            result.errors.append(f"Aggregate type exceeds maximum length of {self.MAX_AGGREGATE_TYPE_LENGTH}")
        elif not re.match(r'^[a-z_][a-z0-9_]*$', event.aggregate_type):
            result.errors.append("Aggregate type must contain only lowercase letters, numbers, and underscores")
        
        # Aggregate version validation
        if event.aggregate_version < 1:
            result.errors.append("Aggregate version must be >= 1")
        elif event.aggregate_version > 1000000:
            result.warnings.append("Very high aggregate version may indicate data issues")
        
        # Event name validation
        if event.event_name and len(event.event_name) > self.MAX_EVENT_NAME_LENGTH:
            result.errors.append(f"Event name exceeds maximum length of {self.MAX_EVENT_NAME_LENGTH}")
        
        # Timestamp validation
        self._validate_timestamps(event, result)
    
    def _validate_event_type(self, event: DomainEvent, result: EventValidationResult) -> None:
        """Validate event type format and business rules."""
        if not event.event_type:
            result.errors.append("Event type is required")
            return
        
        # Length validation
        if len(event.event_type.value) > self.MAX_EVENT_TYPE_LENGTH:
            result.errors.append(f"Event type exceeds maximum length of {self.MAX_EVENT_TYPE_LENGTH}")
        
        # Business rule validation
        self._validate_event_type_business_rules(event.event_type, result)
    
    def _validate_event_type_business_rules(self, event_type: EventType, result: EventValidationResult) -> None:
        """Validate event type against business rules and conventions."""
        category = event_type.category
        action = event_type.action
        
        # Category validation
        if not re.match(self.VALID_CATEGORY_PATTERN, category):
            result.errors.append(f"Event category '{category}' contains invalid characters")
        
        # Action validation
        if not re.match(self.VALID_ACTION_PATTERN, action):
            result.errors.append(f"Event action '{action}' contains invalid characters")
        
        # Business convention recommendations
        if category not in self.COMMON_CATEGORIES:
            result.recommendations.append(f"Consider using a standard category. Common categories: {', '.join(sorted(self.COMMON_CATEGORIES))}")
        
        if action not in self.COMMON_ACTIONS:
            result.recommendations.append(f"Consider using a standard action. Common actions: {', '.join(sorted(self.COMMON_ACTIONS))}")
        
        # Semantic validation
        if action.endswith('ed') and not action.endswith(('created', 'updated', 'deleted', 'activated', 'completed')):
            result.recommendations.append(f"Action '{action}' should use past tense consistently")
    
    def _validate_event_data(self, event: DomainEvent, result: EventValidationResult) -> None:
        """Validate event data payload."""
        if event.event_data is None:
            result.warnings.append("Event data is null - consider using empty dict instead")
            return
        
        if not isinstance(event.event_data, dict):
            result.errors.append("Event data must be a dictionary")
            return
        
        # Structure validation
        self._validate_payload_structure(event.event_data, result, "event_data")
        
        # Size validation
        self._validate_payload_size(event.event_data, result, self.MAX_PAYLOAD_SIZE_BYTES, "event_data")
        
        # Reserved field validation
        reserved_found = set(event.event_data.keys()) & self.RESERVED_METADATA_FIELDS
        if reserved_found:
            result.errors.append(f"Event data contains reserved fields: {', '.join(reserved_found)}")
    
    def _validate_event_metadata(self, event: DomainEvent, result: EventValidationResult) -> None:
        """Validate event metadata."""
        if event.event_metadata is None:
            # This is acceptable, but we recommend using empty dict
            result.recommendations.append("Consider using empty dict instead of null for event_metadata")
            return
        
        if not isinstance(event.event_metadata, dict):
            result.errors.append("Event metadata must be a dictionary")
            return
        
        # Structure validation
        self._validate_payload_structure(event.event_metadata, result, "event_metadata")
        
        # Size validation
        self._validate_payload_size(event.event_metadata, result, self.MAX_METADATA_SIZE_BYTES, "event_metadata")
        
        # Check for recommended metadata fields
        self._validate_recommended_metadata(event.event_metadata, result)
    
    def _validate_business_rules(self, event: DomainEvent, result: EventValidationResult) -> None:
        """Validate business rules for the event."""
        # Context validation
        if event.context_id and not self._is_likely_uuid_v7(event.context_id):
            result.warnings.append("Context ID should be UUIDv7 for better performance")
        
        # Correlation validation
        if event.correlation_id and not self._is_likely_uuid_v7(event.correlation_id):
            result.warnings.append("Correlation ID should be UUIDv7 for better performance")
        
        # Causation validation
        if event.causation_id and not self._is_likely_uuid_v7(event.causation_id):
            result.warnings.append("Causation ID should be UUIDv7 for better performance")
        
        # Event chain validation
        if event.causation_id and event.causation_id == event.id.value:
            result.errors.append("Event cannot be its own cause")
        
        # User context validation
        if event.triggered_by_user_id and not event.triggered_by_user_id.value:
            result.errors.append("Triggered by user ID cannot be empty if provided")
    
    def _validate_performance_constraints(self, event: DomainEvent, result: EventValidationResult) -> None:
        """Validate performance-related constraints."""
        # Check for potentially expensive operations
        total_data_size = self._calculate_data_size(event.event_data) + self._calculate_data_size(event.event_metadata)
        
        if total_data_size > 500 * 1024:  # 500KB warning
            result.warnings.append(f"Large event payload ({total_data_size} bytes) may impact performance")
        
        # Check for deeply nested structures
        max_depth_data = self._get_max_depth(event.event_data)
        max_depth_metadata = self._get_max_depth(event.event_metadata)
        max_depth = max(max_depth_data, max_depth_metadata)
        
        if max_depth > 5:
            result.warnings.append(f"Deep nesting (depth: {max_depth}) may impact performance")
        elif max_depth > self.MAX_NESTED_DEPTH:
            result.errors.append(f"Nesting depth ({max_depth}) exceeds maximum allowed ({self.MAX_NESTED_DEPTH})")
    
    def _validate_timestamps(self, event: DomainEvent, result: EventValidationResult) -> None:
        """Validate event timestamps."""
        now = utc_now()
        
        # Occurred at validation
        if not event.occurred_at:
            result.errors.append("Occurred at timestamp is required")
        else:
            # Check if occurred_at is too far in the future
            if event.occurred_at > now + timedelta(minutes=5):
                result.warnings.append("Event occurred_at is in the future")
            
            # Check if occurred_at is very old
            if event.occurred_at < now - timedelta(days=365):
                result.warnings.append("Event occurred_at is more than 1 year old")
        
        # Created at validation
        if not event.created_at:
            result.errors.append("Created at timestamp is required")
        else:
            # Check timestamp order
            if event.occurred_at and event.created_at < event.occurred_at:
                result.errors.append("Created at must be after or equal to occurred at")
        
        # Processed at validation
        if event.processed_at:
            if event.created_at and event.processed_at < event.created_at:
                result.errors.append("Processed at must be after or equal to created at")
    
    def _validate_payload_structure(self, payload: Dict[str, Any], result: EventValidationResult, field_name: str) -> None:
        """Validate payload structure for JSON compatibility and safety."""
        if not isinstance(payload, dict):
            return
        
        try:
            import json
            # Test JSON serialization
            json.dumps(payload, default=str)
        except (TypeError, ValueError) as e:
            result.errors.append(f"{field_name} is not JSON serializable: {str(e)}")
        
        # Check for circular references
        if self._has_circular_reference(payload):
            result.errors.append(f"{field_name} contains circular references")
    
    def _validate_payload_size(self, payload: Dict[str, Any], result: EventValidationResult, max_size: int, field_name: str) -> None:
        """Validate payload size constraints."""
        size = self._calculate_data_size(payload)
        if size > max_size:
            result.errors.append(f"{field_name} size ({size} bytes) exceeds maximum ({max_size} bytes)")
    
    def _validate_recommended_metadata(self, metadata: Dict[str, Any], result: EventValidationResult) -> None:
        """Validate recommended metadata fields."""
        recommended_fields = ['source', 'version', 'environment']
        missing_recommended = [field for field in recommended_fields if field not in metadata]
        
        if missing_recommended:
            result.recommendations.append(f"Consider adding recommended metadata fields: {', '.join(missing_recommended)}")
        
        # Validate specific metadata field formats
        if 'source' in metadata and not isinstance(metadata['source'], str):
            result.warnings.append("Metadata 'source' should be a string")
        
        if 'version' in metadata and not isinstance(metadata['version'], (str, int, float)):
            result.warnings.append("Metadata 'version' should be a string or number")
    
    def _is_likely_uuid_v7(self, uuid_obj: UUID) -> bool:
        """Check if UUID is likely to be UUIDv7 (time-ordered)."""
        try:
            # UUIDv7 has version bits set to 0111 (7) in the most significant 4 bits of the third group
            version_bits = (uuid_obj.time_hi_version >> 12) & 0xF
            return version_bits == 7
        except:
            return False
    
    def _calculate_data_size(self, data: Any) -> int:
        """Calculate approximate size of data in bytes."""
        try:
            import json
            return len(json.dumps(data, default=str, separators=(',', ':')).encode('utf-8'))
        except:
            return 0
    
    def _get_max_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Get maximum nesting depth of an object."""
        if current_depth > self.MAX_NESTED_DEPTH:
            return current_depth
        
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_max_depth(v, current_depth + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_max_depth(item, current_depth + 1) for item in obj)
        else:
            return current_depth
    
    def _has_circular_reference(self, obj: Any, seen: Optional[Set] = None) -> bool:
        """Check for circular references in nested data structures."""
        if seen is None:
            seen = set()
        
        obj_id = id(obj)
        if obj_id in seen:
            return True
        
        if isinstance(obj, (dict, list)):
            seen.add(obj_id)
            try:
                if isinstance(obj, dict):
                    for value in obj.values():
                        if self._has_circular_reference(value, seen):
                            return True
                elif isinstance(obj, list):
                    for item in obj:
                        if self._has_circular_reference(item, seen):
                            return True
            finally:
                seen.remove(obj_id)
        
        return False
    
    def _generate_validation_summary(self, result: EventValidationResult) -> str:
        """Generate a human-readable validation summary."""
        if result.is_valid:
            summary_parts = ["Event is valid"]
            
            if result.warnings:
                summary_parts.append(f"with {len(result.warnings)} warning(s)")
            
            if result.recommendations:
                summary_parts.append(f"and {len(result.recommendations)} recommendation(s)")
            
            return " ".join(summary_parts) + "."
        else:
            return f"Event validation failed with {len(result.errors)} error(s)."