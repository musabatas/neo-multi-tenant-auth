"""Action condition validator for platform events infrastructure.

This module handles ONLY condition validation logic following maximum separation architecture.
Single responsibility: Validate ActionCondition value objects and condition data.

Pure application layer - no infrastructure concerns.
Uses protocols for dependency injection and clean architecture compliance.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Union
from enum import Enum

from ....actions.core.value_objects import ActionCondition
from ...core.exceptions import EventValidationFailed
from .....utils import utc_now


class ConditionValidationError(Enum):
    """Specific condition validation error types."""
    EMPTY_FIELD = "empty_field"
    INVALID_OPERATOR = "invalid_operator"
    INVALID_VALUE_TYPE = "invalid_value_type"
    INVALID_FIELD_PATH = "invalid_field_path"
    CIRCULAR_REFERENCE = "circular_reference"
    INCOMPATIBLE_OPERATOR_VALUE = "incompatible_operator_value"
    RESERVED_FIELD = "reserved_field"
    NESTED_TOO_DEEP = "nested_too_deep"


@dataclass
class ConditionValidationResult:
    """Result of condition validation."""
    is_valid: bool
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    field_paths_used: Set[str]
    operators_used: Set[str]
    
    def add_error(self, error_type: ConditionValidationError, message: str, 
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
class ConditionValidationContext:
    """Context for condition validation."""
    # Field path validation
    allowed_field_prefixes: Optional[List[str]] = None
    reserved_fields: Optional[Set[str]] = None
    max_nesting_depth: int = 10
    
    # Value validation
    max_string_length: int = 1000
    max_array_length: int = 100
    allowed_value_types: Optional[Set[type]] = None
    
    # Operator restrictions
    restricted_operators: Optional[Set[str]] = None
    required_operators: Optional[Set[str]] = None
    
    # Performance limits
    max_conditions_per_validation: int = 100
    validation_timeout_seconds: int = 30


class ConditionValidator:
    """Validator for ActionCondition objects.
    
    Provides comprehensive validation of condition fields, operators, values,
    and field paths with performance optimization and security checks.
    
    Single responsibility: ONLY condition validation logic.
    Uses validation context for configurable rules and limits.
    """
    
    VALID_OPERATORS = {
        "equals", "contains", "gt", "lt", "in", "not_in", 
        "exists", "not_exists", "starts_with", "ends_with",
        "regex_match", "between", "gte", "lte"
    }
    
    RESERVED_FIELDS = {
        "__proto__", "__constructor__", "constructor", "prototype",
        "eval", "function", "script", "javascript", "sql", "exec"
    }
    
    COMPARISON_OPERATORS = {"gt", "lt", "gte", "lte", "between"}
    ARRAY_OPERATORS = {"in", "not_in"}
    STRING_OPERATORS = {"contains", "starts_with", "ends_with", "regex_match"}
    EXISTENCE_OPERATORS = {"exists", "not_exists"}
    
    def __init__(self, context: Optional[ConditionValidationContext] = None):
        """Initialize validator with optional context.
        
        Args:
            context: Validation context for configurable rules
        """
        self.context = context or ConditionValidationContext()
        self._validation_start_time = None
    
    def validate_condition(self, condition: ActionCondition) -> ConditionValidationResult:
        """Validate a single ActionCondition.
        
        Args:
            condition: ActionCondition to validate
            
        Returns:
            ConditionValidationResult with validation outcome
            
        Raises:
            EventValidationFailed: If validation times out or critical error occurs
        """
        result = ConditionValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            field_paths_used=set(),
            operators_used=set()
        )
        
        self._validation_start_time = utc_now()
        
        try:
            # Validate field path
            self._validate_field_path(condition.field, result)
            
            # Validate operator
            self._validate_operator(condition.operator, result)
            
            # Validate value compatibility with operator
            self._validate_value_compatibility(condition, result)
            
            # Security validation
            self._validate_security_concerns(condition, result)
            
            # Performance validation
            self._validate_performance_concerns(condition, result)
            
            # Track usage for analysis
            result.field_paths_used.add(condition.field)
            result.operators_used.add(condition.operator)
            
            return result
            
        except Exception as e:
            raise EventValidationFailed(f"Condition validation failed: {str(e)}")
    
    def validate_conditions(self, conditions: List[ActionCondition]) -> ConditionValidationResult:
        """Validate multiple conditions with batch optimization.
        
        Args:
            conditions: List of ActionCondition objects to validate
            
        Returns:
            ConditionValidationResult with combined validation results
            
        Raises:
            EventValidationFailed: If validation fails or exceeds limits
        """
        if len(conditions) > self.context.max_conditions_per_validation:
            raise EventValidationFailed(
                f"Too many conditions: {len(conditions)} > {self.context.max_conditions_per_validation}"
            )
        
        combined_result = ConditionValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            field_paths_used=set(),
            operators_used=set()
        )
        
        self._validation_start_time = utc_now()
        
        # Validate each condition
        for i, condition in enumerate(conditions):
            condition_result = self.validate_condition(condition)
            
            # Combine results
            combined_result.errors.extend(condition_result.errors)
            combined_result.warnings.extend(condition_result.warnings)
            combined_result.field_paths_used.update(condition_result.field_paths_used)
            combined_result.operators_used.update(condition_result.operators_used)
            
            if not condition_result.is_valid:
                combined_result.is_valid = False
            
            # Check timeout
            self._check_validation_timeout()
        
        # Additional batch validations
        self._validate_condition_interactions(conditions, combined_result)
        
        return combined_result
    
    def validate_condition_data(self, field: str, operator: str, value: Any) -> ConditionValidationResult:
        """Validate condition data before creating ActionCondition.
        
        Args:
            field: Field path string
            operator: Operator string
            value: Condition value
            
        Returns:
            ConditionValidationResult with validation outcome
        """
        result = ConditionValidationResult(
            is_valid=True,
            errors=[],
            warnings=[],
            field_paths_used=set(),
            operators_used=set()
        )
        
        # Basic validation
        if not field or not field.strip():
            result.add_error(
                ConditionValidationError.EMPTY_FIELD,
                "Field path cannot be empty",
                field_path=field
            )
        
        if not operator or not operator.strip():
            result.add_error(
                ConditionValidationError.INVALID_OPERATOR,
                "Operator cannot be empty",
                field_path=field
            )
        
        # Try to create ActionCondition for full validation
        if result.is_valid:
            try:
                condition = ActionCondition(field=field, operator=operator, value=value)
                condition_result = self.validate_condition(condition)
                
                # Merge results
                result.errors.extend(condition_result.errors)
                result.warnings.extend(condition_result.warnings)
                result.field_paths_used.update(condition_result.field_paths_used)
                result.operators_used.update(condition_result.operators_used)
                
                if not condition_result.is_valid:
                    result.is_valid = False
                    
            except ValueError as e:
                result.add_error(
                    ConditionValidationError.INVALID_VALUE_TYPE,
                    f"Invalid condition data: {str(e)}",
                    field_path=field
                )
        
        return result
    
    def _validate_field_path(self, field_path: str, result: ConditionValidationResult):
        """Validate field path string."""
        # Check for reserved fields
        if field_path.lower() in self.RESERVED_FIELDS:
            result.add_error(
                ConditionValidationError.RESERVED_FIELD,
                f"Field path '{field_path}' is reserved and not allowed",
                field_path=field_path
            )
        
        # Check nesting depth
        nesting_depth = len(field_path.split('.'))
        if nesting_depth > self.context.max_nesting_depth:
            result.add_error(
                ConditionValidationError.NESTED_TOO_DEEP,
                f"Field path nesting too deep: {nesting_depth} > {self.context.max_nesting_depth}",
                field_path=field_path
            )
        
        # Check allowed prefixes
        if self.context.allowed_field_prefixes:
            allowed = any(field_path.startswith(prefix) for prefix in self.context.allowed_field_prefixes)
            if not allowed:
                result.add_error(
                    ConditionValidationError.INVALID_FIELD_PATH,
                    f"Field path '{field_path}' does not start with allowed prefix",
                    field_path=field_path,
                    context={"allowed_prefixes": self.context.allowed_field_prefixes}
                )
        
        # Check reserved fields from context
        if self.context.reserved_fields and field_path in self.context.reserved_fields:
            result.add_error(
                ConditionValidationError.RESERVED_FIELD,
                f"Field path '{field_path}' is reserved in current context",
                field_path=field_path
            )
    
    def _validate_operator(self, operator: str, result: ConditionValidationResult):
        """Validate operator string."""
        # Check if operator is valid
        valid_operators = self.VALID_OPERATORS
        if self.context.restricted_operators:
            valid_operators = valid_operators - self.context.restricted_operators
        
        if operator not in valid_operators:
            result.add_error(
                ConditionValidationError.INVALID_OPERATOR,
                f"Invalid operator '{operator}'. Valid operators: {sorted(valid_operators)}",
                context={"operator": operator, "valid_operators": sorted(valid_operators)}
            )
        
        # Check required operators
        if self.context.required_operators and operator not in self.context.required_operators:
            result.add_warning(
                f"Operator '{operator}' is not in required set: {sorted(self.context.required_operators)}",
                context={"operator": operator, "required_operators": sorted(self.context.required_operators)}
            )
    
    def _validate_value_compatibility(self, condition: ActionCondition, result: ConditionValidationResult):
        """Validate value compatibility with operator."""
        operator = condition.operator
        value = condition.value
        
        # Array operators need list/tuple values
        if operator in self.ARRAY_OPERATORS:
            if not isinstance(value, (list, tuple)):
                result.add_error(
                    ConditionValidationError.INCOMPATIBLE_OPERATOR_VALUE,
                    f"Operator '{operator}' requires array value, got {type(value).__name__}",
                    field_path=condition.field,
                    context={"operator": operator, "value_type": type(value).__name__}
                )
            elif len(value) > self.context.max_array_length:
                result.add_error(
                    ConditionValidationError.INCOMPATIBLE_OPERATOR_VALUE,
                    f"Array value too large: {len(value)} > {self.context.max_array_length}",
                    field_path=condition.field
                )
        
        # Comparison operators need comparable values
        if operator in self.COMPARISON_OPERATORS:
            if operator == "between":
                if not isinstance(value, (list, tuple)) or len(value) != 2:
                    result.add_error(
                        ConditionValidationError.INCOMPATIBLE_OPERATOR_VALUE,
                        f"Operator 'between' requires array with exactly 2 values",
                        field_path=condition.field
                    )
            else:
                # Value should be comparable (number, string, date)
                if not isinstance(value, (int, float, str)) and value is not None:
                    result.add_warning(
                        f"Comparison operator '{operator}' with non-comparable value type: {type(value).__name__}",
                        field_path=condition.field
                    )
        
        # String operators need string values
        if operator in self.STRING_OPERATORS:
            if not isinstance(value, str):
                result.add_error(
                    ConditionValidationError.INCOMPATIBLE_OPERATOR_VALUE,
                    f"String operator '{operator}' requires string value, got {type(value).__name__}",
                    field_path=condition.field
                )
            elif len(value) > self.context.max_string_length:
                result.add_error(
                    ConditionValidationError.INCOMPATIBLE_OPERATOR_VALUE,
                    f"String value too long: {len(value)} > {self.context.max_string_length}",
                    field_path=condition.field
                )
        
        # Existence operators don't really need specific values
        if operator in self.EXISTENCE_OPERATORS:
            # Value is typically ignored for existence checks, but can warn if complex
            if isinstance(value, (dict, list)) and len(str(value)) > 100:
                result.add_warning(
                    f"Existence operator '{operator}' with complex value that will be ignored",
                    field_path=condition.field
                )
        
        # Check allowed value types
        if self.context.allowed_value_types and type(value) not in self.context.allowed_value_types:
            result.add_error(
                ConditionValidationError.INVALID_VALUE_TYPE,
                f"Value type {type(value).__name__} not allowed",
                field_path=condition.field,
                context={"allowed_types": [t.__name__ for t in self.context.allowed_value_types]}
            )
    
    def _validate_security_concerns(self, condition: ActionCondition, result: ConditionValidationResult):
        """Validate security-related concerns."""
        # Check for potential injection patterns in string values
        if isinstance(condition.value, str):
            suspicious_patterns = [
                "javascript:", "data:", "vbscript:", "file:",
                "<script", "eval(", "function(", "setTimeout(",
                "setInterval(", "alert(", "document.",
                "window.", "location.", "history."
            ]
            
            value_lower = condition.value.lower()
            for pattern in suspicious_patterns:
                if pattern in value_lower:
                    result.add_warning(
                        f"Potentially suspicious pattern '{pattern}' found in condition value",
                        field_path=condition.field,
                        context={"pattern": pattern, "operator": condition.operator}
                    )
        
        # Check field path for injection attempts
        if any(char in condition.field for char in ["'", '"', ";", "--", "/*", "*/"]):
            result.add_warning(
                "Field path contains potentially suspicious characters",
                field_path=condition.field
            )
    
    def _validate_performance_concerns(self, condition: ActionCondition, result: ConditionValidationResult):
        """Validate performance-related concerns."""
        # Regex operations can be expensive
        if condition.operator == "regex_match":
            result.add_warning(
                "Regex matching can be performance-intensive",
                field_path=condition.field,
                context={"suggestion": "Consider using contains or starts_with for better performance"}
            )
        
        # Very large arrays can impact performance
        if isinstance(condition.value, (list, tuple)) and len(condition.value) > 50:
            result.add_warning(
                f"Large array value ({len(condition.value)} items) may impact performance",
                field_path=condition.field
            )
        
        # Deep field paths can be slower to evaluate
        if len(condition.field.split('.')) > 5:
            result.add_warning(
                "Deep field path may impact evaluation performance",
                field_path=condition.field
            )
    
    def _validate_condition_interactions(self, conditions: List[ActionCondition], 
                                       result: ConditionValidationResult):
        """Validate interactions between multiple conditions."""
        # Check for duplicate conditions
        condition_signatures = []
        for condition in conditions:
            signature = (condition.field, condition.operator, str(condition.value))
            if signature in condition_signatures:
                result.add_warning(
                    f"Duplicate condition detected: {condition.field} {condition.operator} {condition.value}",
                    field_path=condition.field
                )
            condition_signatures.append(signature)
        
        # Check for contradictory conditions on same field
        field_conditions = {}
        for condition in conditions:
            if condition.field not in field_conditions:
                field_conditions[condition.field] = []
            field_conditions[condition.field].append(condition)
        
        for field_path, field_condition_list in field_conditions.items():
            if len(field_condition_list) > 1:
                self._check_contradictory_conditions(field_condition_list, result)
    
    def _check_contradictory_conditions(self, conditions: List[ActionCondition], 
                                       result: ConditionValidationResult):
        """Check for contradictory conditions on the same field."""
        # Look for exists + not_exists on same field
        has_exists = any(c.operator == "exists" for c in conditions)
        has_not_exists = any(c.operator == "not_exists" for c in conditions)
        
        if has_exists and has_not_exists:
            field_path = conditions[0].field
            result.add_error(
                ConditionValidationError.CIRCULAR_REFERENCE,
                f"Contradictory conditions: field '{field_path}' has both exists and not_exists conditions",
                field_path=field_path
            )
    
    def _check_validation_timeout(self):
        """Check if validation has exceeded timeout."""
        if self._validation_start_time:
            elapsed = (utc_now() - self._validation_start_time).total_seconds()
            if elapsed > self.context.validation_timeout_seconds:
                raise EventValidationFailed(
                    f"Validation timeout exceeded: {elapsed}s > {self.context.validation_timeout_seconds}s"
                )


def create_condition_validator(context: Optional[ConditionValidationContext] = None) -> ConditionValidator:
    """Factory function to create ConditionValidator instance.
    
    Args:
        context: Optional validation context for configurable rules
        
    Returns:
        Configured ConditionValidator instance
    """
    return ConditionValidator(context=context)


def create_strict_condition_validator() -> ConditionValidator:
    """Factory function to create strict ConditionValidator with restrictive settings.
    
    Returns:
        ConditionValidator configured with strict validation rules
    """
    strict_context = ConditionValidationContext(
        allowed_field_prefixes=["data.", "metadata.", "context."],
        reserved_fields={"admin", "system", "internal", "__system__"},
        max_nesting_depth=5,
        max_string_length=500,
        max_array_length=50,
        allowed_value_types={str, int, float, bool, list, type(None)},
        restricted_operators={"regex_match"},  # Disable regex for security
        max_conditions_per_validation=50,
        validation_timeout_seconds=15
    )
    
    return ConditionValidator(context=strict_context)