"""Payload validator for platform events infrastructure.

This module handles ONLY payload validation logic following maximum separation architecture.
Single responsibility: Validate event payloads, webhook payloads, and data structures.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Union, Callable
from enum import Enum
import json
import re
from decimal import Decimal
from datetime import datetime

from .....utils import utc_now
from ...core.exceptions import EventValidationFailed


class PayloadValidationError(Enum):
    """Specific payload validation error types."""
    INVALID_JSON = "invalid_json"
    SCHEMA_VIOLATION = "schema_violation"
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_FIELD_TYPE = "invalid_field_type"
    INVALID_FIELD_VALUE = "invalid_field_value"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    PAYLOAD_TOO_DEEP = "payload_too_deep"
    FORBIDDEN_FIELD = "forbidden_field"
    MALICIOUS_CONTENT = "malicious_content"
    ENCODING_ERROR = "encoding_error"


@dataclass
class FieldValidationRule:
    """Validation rule for a specific field."""
    field_path: str
    required: bool = False
    field_type: Optional[type] = None
    allowed_values: Optional[Set[Any]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float, Decimal]] = None
    max_value: Optional[Union[int, float, Decimal]] = None
    pattern: Optional[str] = None
    custom_validator: Optional[Callable[[Any], bool]] = None
    description: Optional[str] = None


@dataclass
class PayloadValidationResult:
    """Result of payload validation."""
    is_valid: bool
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    sanitized_payload: Optional[Dict[str, Any]]
    validation_metadata: Dict[str, Any]
    
    def add_error(self, error_type: PayloadValidationError, message: str, 
                  field_path: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        """Add validation error with context."""
        self.errors.append({
            "type": error_type.value,
            "message": message,
            "field_path": field_path,
            "context": context or {},
            "timestamp": utc_now().isoformat()
        })
        self.is_valid = False
    
    def add_warning(self, message: str, field_path: Optional[str] = None, 
                   context: Optional[Dict[str, Any]] = None):
        """Add validation warning with context."""
        self.warnings.append({
            "message": message,
            "field_path": field_path,
            "context": context or {},
            "timestamp": utc_now().isoformat()
        })


@dataclass
class PayloadValidationSchema:
    """Schema definition for payload validation."""
    # Schema identification
    schema_name: str
    schema_version: str = "1.0.0"
    
    # Field validation rules
    field_rules: Dict[str, FieldValidationRule] = field(default_factory=dict)
    
    # Global constraints
    max_payload_size: int = 1024 * 1024  # 1MB
    max_nesting_depth: int = 10
    max_array_length: int = 1000
    max_string_length: int = 10000
    
    # Security settings
    forbidden_fields: Set[str] = field(default_factory=lambda: {
        "__proto__", "constructor", "prototype", "eval", "function"
    })
    allowed_content_types: Set[str] = field(default_factory=lambda: {
        "application/json", "text/plain", "application/x-www-form-urlencoded"
    })
    
    # Sanitization settings
    auto_sanitize: bool = False
    remove_forbidden_fields: bool = True
    normalize_strings: bool = True
    
    def add_field_rule(self, field_path: str, rule: FieldValidationRule):
        """Add field validation rule to schema."""
        self.field_rules[field_path] = rule
    
    def remove_field_rule(self, field_path: str):
        """Remove field validation rule from schema."""
        if field_path in self.field_rules:
            del self.field_rules[field_path]


class PayloadValidator:
    """Validator for event and webhook payloads.
    
    Provides comprehensive payload validation with schema-based rules,
    security checks, sanitization, and performance optimization.
    
    Single responsibility: ONLY payload validation and sanitization logic.
    Uses validation schemas for configurable rules and constraints.
    """
    
    # Common malicious patterns
    MALICIOUS_PATTERNS = [
        r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",  # Script tags
        r"javascript:",                                          # JavaScript protocol
        r"data:text\/html",                                     # HTML data URLs
        r"vbscript:",                                           # VBScript protocol
        r"on\w+\s*=",                                           # Event handlers
        r"eval\s*\(",                                           # Eval function
        r"document\.",                                          # Document object
        r"window\.",                                            # Window object
        r"alert\s*\(",                                          # Alert function
        r"<iframe\b",                                           # Iframe tags
        r"<object\b",                                           # Object tags
        r"<embed\b",                                            # Embed tags
    ]
    
    def __init__(self, schema: Optional[PayloadValidationSchema] = None):
        """Initialize validator with optional schema.
        
        Args:
            schema: Validation schema for payload rules
        """
        self.schema = schema or self._create_default_schema()
        self._compiled_patterns = None
        self._validation_start_time = None
    
    def validate_payload(self, payload: Any, content_type: str = "application/json") -> PayloadValidationResult:
        """Validate payload data against schema.
        
        Args:
            payload: Payload data to validate
            content_type: MIME type of payload content
            
        Returns:
            PayloadValidationResult with validation outcome and sanitized data
            
        Raises:
            EventValidationFailed: If validation encounters critical error
        """
        result = PayloadValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            sanitized_payload=None,
            validation_metadata={
                "schema_name": self.schema.schema_name,
                "schema_version": self.schema.schema_version,
                "content_type": content_type,
                "validation_timestamp": utc_now().isoformat()
            }
        )
        
        self._validation_start_time = utc_now()
        
        try:
            # Content type validation
            self._validate_content_type(content_type, result)
            
            # Parse and convert payload
            parsed_payload = self._parse_payload(payload, content_type, result)
            if not result.is_valid:
                return result
            
            # Size validation
            self._validate_payload_size(parsed_payload, result)
            
            # Structure validation
            self._validate_payload_structure(parsed_payload, result)
            
            # Field-specific validation
            self._validate_payload_fields(parsed_payload, result)
            
            # Security validation
            self._validate_payload_security(parsed_payload, result)
            
            # Sanitization (if enabled and valid)
            if result.is_valid and self.schema.auto_sanitize:
                result.sanitized_payload = self._sanitize_payload(parsed_payload, result)
            else:
                result.sanitized_payload = parsed_payload
            
            # Final validation metadata
            result.validation_metadata.update({
                "fields_validated": len(self.schema.field_rules),
                "payload_size_bytes": len(str(parsed_payload)),
                "nesting_depth": self._calculate_nesting_depth(parsed_payload),
                "validation_duration_ms": (utc_now() - self._validation_start_time).total_seconds() * 1000
            })
            
            return result
            
        except Exception as e:
            raise EventValidationFailed(f"Payload validation failed: {str(e)}")
    
    def validate_json_payload(self, json_data: Union[str, Dict[str, Any]]) -> PayloadValidationResult:
        """Validate JSON payload specifically.
        
        Args:
            json_data: JSON string or dictionary data
            
        Returns:
            PayloadValidationResult with validation outcome
        """
        return self.validate_payload(json_data, content_type="application/json")
    
    def validate_webhook_payload(self, payload: Dict[str, Any], 
                                headers: Optional[Dict[str, str]] = None) -> PayloadValidationResult:
        """Validate webhook payload with header information.
        
        Args:
            payload: Webhook payload dictionary
            headers: Optional HTTP headers for additional validation
            
        Returns:
            PayloadValidationResult with validation outcome
        """
        # Determine content type from headers
        content_type = "application/json"
        if headers:
            content_type = headers.get("content-type", "application/json").split(";")[0].strip()
        
        result = self.validate_payload(payload, content_type)
        
        # Add webhook-specific validations
        if headers:
            result.validation_metadata["webhook_headers"] = self._extract_webhook_metadata(headers)
        
        return result
    
    def _create_default_schema(self) -> PayloadValidationSchema:
        """Create default validation schema."""
        schema = PayloadValidationSchema(
            schema_name="default_payload_schema",
            schema_version="1.0.0",
            max_payload_size=512 * 1024,  # 512KB
            max_nesting_depth=8,
            max_array_length=500,
            max_string_length=5000
        )
        
        # Add common field rules
        schema.add_field_rule("timestamp", FieldValidationRule(
            field_path="timestamp",
            required=False,
            field_type=str,
            description="Event timestamp in ISO 8601 format"
        ))
        
        schema.add_field_rule("event_type", FieldValidationRule(
            field_path="event_type",
            required=False,
            field_type=str,
            min_length=1,
            max_length=100,
            description="Type of event"
        ))
        
        return schema
    
    def _validate_content_type(self, content_type: str, result: PayloadValidationResult):
        """Validate content type."""
        if content_type not in self.schema.allowed_content_types:
            result.add_warning(
                f"Content type '{content_type}' not in allowed types: {sorted(self.schema.allowed_content_types)}",
                context={"content_type": content_type, "allowed": sorted(self.schema.allowed_content_types)}
            )
    
    def _parse_payload(self, payload: Any, content_type: str, result: PayloadValidationResult) -> Dict[str, Any]:
        """Parse payload based on content type."""
        if content_type == "application/json":
            if isinstance(payload, str):
                try:
                    return json.loads(payload)
                except json.JSONDecodeError as e:
                    result.add_error(
                        PayloadValidationError.INVALID_JSON,
                        f"Invalid JSON format: {str(e)}",
                        context={"json_error": str(e)}
                    )
                    return {}
            elif isinstance(payload, dict):
                return payload
            else:
                result.add_error(
                    PayloadValidationError.INVALID_FIELD_TYPE,
                    f"Expected JSON string or dict, got {type(payload).__name__}",
                    context={"payload_type": type(payload).__name__}
                )
                return {}
        
        elif content_type == "application/x-www-form-urlencoded":
            if isinstance(payload, dict):
                return payload
            else:
                result.add_error(
                    PayloadValidationError.INVALID_FIELD_TYPE,
                    f"Expected dict for form data, got {type(payload).__name__}",
                    context={"payload_type": type(payload).__name__}
                )
                return {}
        
        else:
            # Try to convert to dict if possible
            if isinstance(payload, dict):
                return payload
            elif isinstance(payload, str):
                result.add_warning(
                    f"Treating string payload as plain text for content type '{content_type}'"
                )
                return {"content": payload}
            else:
                result.add_error(
                    PayloadValidationError.ENCODING_ERROR,
                    f"Cannot parse payload of type {type(payload).__name__} for content type '{content_type}'",
                    context={"payload_type": type(payload).__name__, "content_type": content_type}
                )
                return {}
    
    def _validate_payload_size(self, payload: Dict[str, Any], result: PayloadValidationResult):
        """Validate payload size constraints."""
        payload_size = len(json.dumps(payload, ensure_ascii=False).encode('utf-8'))
        
        if payload_size > self.schema.max_payload_size:
            result.add_error(
                PayloadValidationError.PAYLOAD_TOO_LARGE,
                f"Payload size {payload_size} bytes exceeds limit of {self.schema.max_payload_size} bytes",
                context={"payload_size": payload_size, "max_size": self.schema.max_payload_size}
            )
    
    def _validate_payload_structure(self, payload: Dict[str, Any], result: PayloadValidationResult):
        """Validate payload structure constraints."""
        # Check nesting depth
        nesting_depth = self._calculate_nesting_depth(payload)
        if nesting_depth > self.schema.max_nesting_depth:
            result.add_error(
                PayloadValidationError.PAYLOAD_TOO_DEEP,
                f"Payload nesting depth {nesting_depth} exceeds limit of {self.schema.max_nesting_depth}",
                context={"nesting_depth": nesting_depth, "max_depth": self.schema.max_nesting_depth}
            )
        
        # Check for forbidden fields
        forbidden_found = self._find_forbidden_fields(payload, "", set())
        for field_path in forbidden_found:
            result.add_error(
                PayloadValidationError.FORBIDDEN_FIELD,
                f"Forbidden field '{field_path}' found in payload",
                field_path=field_path
            )
    
    def _validate_payload_fields(self, payload: Dict[str, Any], result: PayloadValidationResult):
        """Validate individual fields against schema rules."""
        # Check required fields
        for field_path, rule in self.schema.field_rules.items():
            field_value = self._get_field_value(payload, field_path)
            
            if rule.required and field_value is None:
                result.add_error(
                    PayloadValidationError.REQUIRED_FIELD_MISSING,
                    f"Required field '{field_path}' is missing",
                    field_path=field_path,
                    context={"rule_description": rule.description}
                )
                continue
            
            if field_value is not None:
                self._validate_field_value(field_path, field_value, rule, result)
    
    def _validate_field_value(self, field_path: str, value: Any, rule: FieldValidationRule, 
                             result: PayloadValidationResult):
        """Validate single field value against rule."""
        # Type validation
        if rule.field_type and not isinstance(value, rule.field_type):
            result.add_error(
                PayloadValidationError.INVALID_FIELD_TYPE,
                f"Field '{field_path}' expected type {rule.field_type.__name__}, got {type(value).__name__}",
                field_path=field_path,
                context={"expected_type": rule.field_type.__name__, "actual_type": type(value).__name__}
            )
            return
        
        # Allowed values validation
        if rule.allowed_values and value not in rule.allowed_values:
            result.add_error(
                PayloadValidationError.INVALID_FIELD_VALUE,
                f"Field '{field_path}' value '{value}' not in allowed values: {sorted(rule.allowed_values)}",
                field_path=field_path,
                context={"value": value, "allowed_values": sorted(rule.allowed_values)}
            )
        
        # String-specific validations
        if isinstance(value, str):
            if rule.min_length and len(value) < rule.min_length:
                result.add_error(
                    PayloadValidationError.INVALID_FIELD_VALUE,
                    f"Field '{field_path}' length {len(value)} is less than minimum {rule.min_length}",
                    field_path=field_path
                )
            
            if rule.max_length and len(value) > rule.max_length:
                result.add_error(
                    PayloadValidationError.INVALID_FIELD_VALUE,
                    f"Field '{field_path}' length {len(value)} exceeds maximum {rule.max_length}",
                    field_path=field_path
                )
            
            if rule.pattern and not re.match(rule.pattern, value):
                result.add_error(
                    PayloadValidationError.INVALID_FIELD_VALUE,
                    f"Field '{field_path}' value does not match required pattern",
                    field_path=field_path,
                    context={"pattern": rule.pattern}
                )
        
        # Numeric validations
        if isinstance(value, (int, float, Decimal)):
            if rule.min_value is not None and value < rule.min_value:
                result.add_error(
                    PayloadValidationError.INVALID_FIELD_VALUE,
                    f"Field '{field_path}' value {value} is less than minimum {rule.min_value}",
                    field_path=field_path
                )
            
            if rule.max_value is not None and value > rule.max_value:
                result.add_error(
                    PayloadValidationError.INVALID_FIELD_VALUE,
                    f"Field '{field_path}' value {value} exceeds maximum {rule.max_value}",
                    field_path=field_path
                )
        
        # Custom validator
        if rule.custom_validator and not rule.custom_validator(value):
            result.add_error(
                PayloadValidationError.INVALID_FIELD_VALUE,
                f"Field '{field_path}' failed custom validation",
                field_path=field_path,
                context={"value": value}
            )
    
    def _validate_payload_security(self, payload: Dict[str, Any], result: PayloadValidationResult):
        """Validate payload for security concerns."""
        if self._compiled_patterns is None:
            self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.MALICIOUS_PATTERNS]
        
        # Check for malicious patterns in string values
        malicious_fields = []
        self._scan_for_malicious_content(payload, "", malicious_fields)
        
        for field_path in malicious_fields:
            result.add_error(
                PayloadValidationError.MALICIOUS_CONTENT,
                f"Potentially malicious content detected in field '{field_path}'",
                field_path=field_path
            )
    
    def _sanitize_payload(self, payload: Dict[str, Any], result: PayloadValidationResult) -> Dict[str, Any]:
        """Sanitize payload by removing/cleaning problematic content."""
        sanitized = self._deep_copy_dict(payload)
        
        # Remove forbidden fields
        if self.schema.remove_forbidden_fields:
            self._remove_forbidden_fields(sanitized, "")
        
        # Normalize strings
        if self.schema.normalize_strings:
            self._normalize_string_values(sanitized, "")
        
        return sanitized
    
    def _calculate_nesting_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of object."""
        if not isinstance(obj, (dict, list)):
            return current_depth
        
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._calculate_nesting_depth(value, current_depth + 1) for value in obj.values())
        
        if isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._calculate_nesting_depth(item, current_depth + 1) for item in obj)
        
        return current_depth
    
    def _find_forbidden_fields(self, obj: Dict[str, Any], path_prefix: str, found: Set[str]) -> Set[str]:
        """Find forbidden fields in nested object."""
        for key, value in obj.items():
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            
            if key in self.schema.forbidden_fields:
                found.add(current_path)
            
            if isinstance(value, dict):
                self._find_forbidden_fields(value, current_path, found)
        
        return found
    
    def _get_field_value(self, obj: Dict[str, Any], field_path: str) -> Any:
        """Get field value using dot notation path."""
        parts = field_path.split('.')
        current = obj
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _scan_for_malicious_content(self, obj: Any, path_prefix: str, malicious_fields: List[str]):
        """Scan object for malicious content patterns."""
        if isinstance(obj, str):
            for pattern in self._compiled_patterns:
                if pattern.search(obj):
                    malicious_fields.append(path_prefix)
                    break
        
        elif isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path_prefix}.{key}" if path_prefix else key
                self._scan_for_malicious_content(value, current_path, malicious_fields)
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path_prefix}[{i}]" if path_prefix else f"[{i}]"
                self._scan_for_malicious_content(item, current_path, malicious_fields)
    
    def _remove_forbidden_fields(self, obj: Dict[str, Any], path_prefix: str):
        """Remove forbidden fields from object."""
        keys_to_remove = []
        
        for key, value in obj.items():
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            
            if key in self.schema.forbidden_fields:
                keys_to_remove.append(key)
            elif isinstance(value, dict):
                self._remove_forbidden_fields(value, current_path)
        
        for key in keys_to_remove:
            del obj[key]
    
    def _normalize_string_values(self, obj: Any, path_prefix: str):
        """Normalize string values in object."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path_prefix}.{key}" if path_prefix else key
                if isinstance(value, str):
                    obj[key] = value.strip()
                elif isinstance(value, (dict, list)):
                    self._normalize_string_values(value, current_path)
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path_prefix}[{i}]" if path_prefix else f"[{i}]"
                if isinstance(item, str):
                    obj[i] = item.strip()
                elif isinstance(item, (dict, list)):
                    self._normalize_string_values(item, current_path)
    
    def _deep_copy_dict(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Create deep copy of dictionary."""
        return json.loads(json.dumps(obj))
    
    def _extract_webhook_metadata(self, headers: Dict[str, str]) -> Dict[str, Any]:
        """Extract relevant metadata from webhook headers."""
        return {
            "content_type": headers.get("content-type", ""),
            "content_length": headers.get("content-length", ""),
            "user_agent": headers.get("user-agent", ""),
            "signature": headers.get("x-signature", ""),
            "timestamp": headers.get("x-timestamp", ""),
            "event_type": headers.get("x-event-type", "")
        }


def create_payload_validator(schema: Optional[PayloadValidationSchema] = None) -> PayloadValidator:
    """Factory function to create PayloadValidator instance.
    
    Args:
        schema: Optional validation schema for payload rules
        
    Returns:
        Configured PayloadValidator instance
    """
    return PayloadValidator(schema=schema)


def create_strict_payload_validator() -> PayloadValidator:
    """Factory function to create strict PayloadValidator with restrictive settings.
    
    Returns:
        PayloadValidator configured with strict validation rules
    """
    strict_schema = PayloadValidationSchema(
        schema_name="strict_payload_schema",
        schema_version="1.0.0",
        max_payload_size=256 * 1024,  # 256KB
        max_nesting_depth=6,
        max_array_length=200,
        max_string_length=2000,
        forbidden_fields={
            "__proto__", "constructor", "prototype", "eval", "function",
            "script", "iframe", "object", "embed", "form", "input"
        },
        allowed_content_types={"application/json"},
        auto_sanitize=True,
        remove_forbidden_fields=True,
        normalize_strings=True
    )
    
    return PayloadValidator(schema=strict_schema)


def create_webhook_payload_validator() -> PayloadValidator:
    """Factory function to create PayloadValidator optimized for webhooks.
    
    Returns:
        PayloadValidator configured for webhook payload validation
    """
    webhook_schema = PayloadValidationSchema(
        schema_name="webhook_payload_schema",
        schema_version="1.0.0",
        max_payload_size=1024 * 1024,  # 1MB for webhook payloads
        max_nesting_depth=8,
        max_array_length=1000,
        max_string_length=10000,
        auto_sanitize=False,  # Don't modify webhook payloads
        remove_forbidden_fields=False,
        normalize_strings=False
    )
    
    # Add common webhook field rules
    webhook_schema.add_field_rule("event", FieldValidationRule(
        field_path="event",
        required=True,
        field_type=str,
        min_length=1,
        max_length=100,
        description="Webhook event type"
    ))
    
    webhook_schema.add_field_rule("data", FieldValidationRule(
        field_path="data",
        required=True,
        field_type=dict,
        description="Webhook event data"
    ))
    
    return PayloadValidator(schema=webhook_schema)