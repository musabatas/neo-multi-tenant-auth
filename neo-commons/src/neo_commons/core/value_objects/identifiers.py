"""Value objects for identifiers in neo-commons.

This module defines immutable value objects for various identifiers
used throughout the system. Provides both basic validation and 
configurable runtime validation via ConfigurationProtocol.
"""

import re
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Pattern, Union, Callable
from abc import ABC, abstractmethod
from ..shared.application import ConfigurationProtocol
from ...utils import generate_uuid_v7


# Validation framework
class ValidationRule:
    """Represents a single validation rule."""
    
    def __init__(
        self, 
        name: str, 
        validator: Callable[[Any], bool], 
        error_message: str,
        severity: str = "error"
    ):
        """Initialize validation rule.
        
        Args:
            name: Rule identifier
            validator: Function that returns True if value is valid
            error_message: Error message for validation failures
            severity: Rule severity (error, warning, info)
        """
        self.name = name
        self.validator = validator
        self.error_message = error_message
        self.severity = severity
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate value against this rule.
        
        Args:
            value: Value to validate
            
        Returns:
            Error message if validation fails, None if valid
        """
        try:
            if not self.validator(value):
                return self.error_message
        except Exception as e:
            return f"Validation rule '{self.name}' failed: {str(e)}"
        return None


class ValidationRuleBuilder:
    """Builder for common validation rules."""
    
    @staticmethod
    def not_empty(field_name: str = "Value") -> ValidationRule:
        """Rule: value must not be empty."""
        return ValidationRule(
            name="not_empty",
            validator=lambda v: v and str(v).strip(),
            error_message=f"{field_name} must not be empty"
        )
    
    @staticmethod
    def string_type(field_name: str = "Value") -> ValidationRule:
        """Rule: value must be a string."""
        return ValidationRule(
            name="string_type",
            validator=lambda v: isinstance(v, str),
            error_message=f"{field_name} must be a string"
        )
    
    @staticmethod
    def min_length(min_len: int, field_name: str = "Value") -> ValidationRule:
        """Rule: string must have minimum length."""
        return ValidationRule(
            name="min_length",
            validator=lambda v: isinstance(v, str) and len(v) >= min_len,
            error_message=f"{field_name} must be at least {min_len} characters"
        )
    
    @staticmethod
    def max_length(max_len: int, field_name: str = "Value") -> ValidationRule:
        """Rule: string must not exceed maximum length."""
        return ValidationRule(
            name="max_length",
            validator=lambda v: isinstance(v, str) and len(v) <= max_len,
            error_message=f"{field_name} must be at most {max_len} characters"
        )
    
    @staticmethod
    def regex_pattern(pattern: Union[str, Pattern], field_name: str = "Value") -> ValidationRule:
        """Rule: string must match regex pattern."""
        compiled_pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        return ValidationRule(
            name="regex_pattern",
            validator=lambda v: isinstance(v, str) and bool(compiled_pattern.match(v)),
            error_message=f"{field_name} must match the required pattern"
        )
    
    @staticmethod
    def uuid_format(field_name: str = "ID") -> ValidationRule:
        """Rule: value must be valid UUID format."""
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        return ValidationRule(
            name="uuid_format",
            validator=lambda v: isinstance(v, str) and bool(uuid_pattern.match(v)),
            error_message=f"{field_name} must be a valid UUID format"
        )
    
    @staticmethod
    def alphanumeric_only(field_name: str = "Value", allow_hyphens: bool = False) -> ValidationRule:
        """Rule: value must be alphanumeric (optionally with hyphens)."""
        pattern = r'^[a-zA-Z0-9\\-]+$' if allow_hyphens else r'^[a-zA-Z0-9]+$'
        return ValidationRule(
            name="alphanumeric_only",
            validator=lambda v: isinstance(v, str) and bool(re.match(pattern, v)),
            error_message=f"{field_name} must contain only alphanumeric characters" + (" and hyphens" if allow_hyphens else "")
        )


# Base classes
class ValueObject(ABC):
    """Base class for value objects with configurable runtime validation.
    
    This class enables value objects to have their validation rules
    configured at runtime through ConfigurationProtocol.
    """
    
    _config: Optional[ConfigurationProtocol] = None
    _validation_cache: Dict[str, List[ValidationRule]] = {}
    
    def __init__(self, value: Any):
        """Initialize with runtime validation."""
        # Use object.__setattr__ for frozen dataclasses
        object.__setattr__(self, 'value', value)
        self._validate_value()
    
    @classmethod
    def set_configuration(cls, config: ConfigurationProtocol) -> None:
        """Set global configuration provider for all value objects.
        
        Args:
            config: Configuration provider instance
        """
        cls._config = config
        cls._validation_cache.clear()  # Clear cache when config changes
    
    @classmethod
    @abstractmethod
    def get_value_object_name(cls) -> str:
        """Get the name used in configuration keys.
        
        Returns:
            Configuration key name for this value object type
        """
        ...
    
    @classmethod
    @abstractmethod  
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Get default validation rules for this value object.
        
        Returns:
            List of default validation rules
        """
        ...
    
    @classmethod
    def get_validation_rules(cls) -> List[ValidationRule]:
        """Get validation rules with configuration overrides.
        
        Returns:
            List of validation rules (configured or default)
        """
        value_object_name = cls.get_value_object_name()
        
        # Check cache first
        if value_object_name in cls._validation_cache:
            return cls._validation_cache[value_object_name]
        
        # Start with default rules
        rules = cls.get_default_validation_rules()
        
        # Apply configuration overrides
        if cls._config:
            rules = cls._apply_configuration_overrides(rules, value_object_name)
        
        # Cache the result
        cls._validation_cache[value_object_name] = rules
        return rules
    
    @classmethod
    def _apply_configuration_overrides(
        cls, 
        default_rules: List[ValidationRule], 
        value_object_name: str
    ) -> List[ValidationRule]:
        """Apply configuration overrides to validation rules."""
        if not cls._config:
            return default_rules
        
        try:
            # Get configuration section for this value object
            config_key = f"value_object_validation.{value_object_name}"
            config_section = cls._config.get_section(config_key)
            
            if not config_section:
                return default_rules
            
            # Apply overrides
            modified_rules = []
            
            for rule in default_rules:
                # Check if this rule is disabled
                rule_disabled_key = f"{rule.name}.disabled"
                if config_section.get(rule_disabled_key, False):
                    continue  # Skip disabled rules
                
                # Check for custom error message
                custom_message_key = f"{rule.name}.error_message"
                custom_message = config_section.get(custom_message_key)
                
                if custom_message:
                    # Create new rule with custom message
                    modified_rule = ValidationRule(
                        name=rule.name,
                        validator=rule.validator,
                        error_message=custom_message,
                        severity=rule.severity
                    )
                    modified_rules.append(modified_rule)
                else:
                    modified_rules.append(rule)
            
            # Add custom rules from configuration
            custom_rules_config = config_section.get("custom_rules", {})
            for rule_name, rule_config in custom_rules_config.items():
                if isinstance(rule_config, dict) and "pattern" in rule_config:
                    # Custom regex rule
                    pattern = rule_config["pattern"]
                    error_msg = rule_config.get("error_message", f"Value must match pattern: {pattern}")
                    custom_rule = ValidationRuleBuilder.regex_pattern(pattern, cls.get_value_object_name())
                    custom_rule.error_message = error_msg
                    modified_rules.append(custom_rule)
            
            return modified_rules
            
        except Exception:
            # If configuration parsing fails, return default rules
            return default_rules
    
    def _validate_value(self) -> None:
        """Validate the value using configured rules."""
        rules = self.get_validation_rules()
        errors = []
        
        for rule in rules:
            error = rule.validate(self.value)
            if error:
                if rule.severity == "error":
                    errors.append(error)
                # Could handle warnings/info differently in the future
        
        if errors:
            raise ValueError("; ".join(errors))
    
    @classmethod
    def clear_validation_cache(cls) -> None:
        """Clear validation rule cache.
        
        Call this when configuration changes at runtime.
        """
        cls._validation_cache.clear()
    
    @classmethod
    def get_validation_statistics(cls) -> Dict[str, Any]:
        """Get validation configuration statistics.
        
        Returns:
            Statistics about validation configuration
        """
        return {
            "has_configuration": cls._config is not None,
            "cached_rule_sets": len(cls._validation_cache),
            "cached_value_objects": list(cls._validation_cache.keys())
        }
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"{self.__class__.__name__}(value={self.value!r})"
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, self.__class__):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.__class__.__name__, self.value))


# Basic identifier value objects (simple validation)
@dataclass(frozen=True)
class UserId:
    """User identifier value object with UUIDv7 support."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"UserId must be a valid UUID, got: {self.value}")
    
    @classmethod
    def generate(cls) -> 'UserId':
        """Generate a new UserId using UUIDv7 for time-ordering."""
        return cls(generate_uuid_v7())
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"UserId(value={self.value!r})"


@dataclass(frozen=True)
class TenantId:
    """Tenant identifier value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Tenant ID must be a non-empty string")


@dataclass(frozen=True)
class OrganizationId:
    """Organization identifier value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Organization ID must be a non-empty string")


@dataclass(frozen=True)
class PermissionCode:
    """Permission code value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Permission code must be a non-empty string")


@dataclass(frozen=True)
class RoleCode:
    """Role code value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Role code must be a non-empty string")


@dataclass(frozen=True)
class DatabaseConnectionId:
    """Database connection identifier value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Database connection ID must be a non-empty string")


@dataclass(frozen=True)
class RegionId:
    """Region identifier value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Region ID must be a non-empty string")


@dataclass(frozen=True)
class RealmId:
    """Keycloak realm identifier value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Realm ID must be a non-empty string")


@dataclass(frozen=True)
class KeycloakUserId:
    """Keycloak user identifier value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Keycloak User ID must be a non-empty string")


@dataclass(frozen=True)
class TokenId:
    """Token identifier value object with basic validation."""
    value: str
    
    def __post_init__(self):
        if not self.value or not isinstance(self.value, str):
            raise ValueError("Token ID must be a non-empty string")


# Advanced identifier value objects (configurable validation)
@dataclass(frozen=True)
class AdvancedUserId(ValueObject):
    """User identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize user ID with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for user ID validation."""
        return "user_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for user ID."""
        return [
            ValidationRuleBuilder.not_empty("User ID"),
            ValidationRuleBuilder.string_type("User ID"),
            ValidationRuleBuilder.uuid_format("User ID")
        ]


@dataclass(frozen=True) 
class AdvancedTenantId(ValueObject):
    """Tenant identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize tenant ID with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for tenant ID validation."""
        return "tenant_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for tenant ID."""
        return [
            ValidationRuleBuilder.not_empty("Tenant ID"),
            ValidationRuleBuilder.string_type("Tenant ID"),
            ValidationRuleBuilder.uuid_format("Tenant ID")
        ]


@dataclass(frozen=True)
class AdvancedOrganizationId(ValueObject):
    """Organization identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize organization ID with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for organization ID validation."""
        return "organization_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for organization ID."""
        return [
            ValidationRuleBuilder.not_empty("Organization ID"),
            ValidationRuleBuilder.string_type("Organization ID"),
            ValidationRuleBuilder.uuid_format("Organization ID")
        ]


@dataclass(frozen=True)
class AdvancedPermissionCode(ValueObject):
    """Permission code with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize permission code with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for permission code validation."""
        return "permission_code"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for permission code."""
        return [
            ValidationRuleBuilder.not_empty("Permission code"),
            ValidationRuleBuilder.string_type("Permission code"),
            ValidationRuleBuilder.min_length(3, "Permission code"),
            ValidationRuleBuilder.max_length(100, "Permission code"),
            # Permission codes often follow patterns like "users:read", "admin:write"
            ValidationRuleBuilder.regex_pattern(
                r'^[a-zA-Z0-9_\\-]+:[a-zA-Z0-9_\\-]+$',
                "Permission code"
            )
        ]


@dataclass(frozen=True)
class AdvancedRoleCode(ValueObject):
    """Role code with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize role code with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for role code validation."""
        return "role_code"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for role code."""
        return [
            ValidationRuleBuilder.not_empty("Role code"),
            ValidationRuleBuilder.string_type("Role code"),
            ValidationRuleBuilder.min_length(2, "Role code"),
            ValidationRuleBuilder.max_length(100, "Role code"),
            ValidationRuleBuilder.alphanumeric_only("Role code", allow_hyphens=True)
        ]


@dataclass(frozen=True)
class AdvancedDatabaseConnectionId(ValueObject):
    """Database connection identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize database connection ID with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for database connection ID validation."""
        return "database_connection_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for database connection ID."""
        return [
            ValidationRuleBuilder.not_empty("Database connection ID"),
            ValidationRuleBuilder.string_type("Database connection ID"),
            ValidationRuleBuilder.uuid_format("Database connection ID")
        ]


@dataclass(frozen=True)
class AdvancedRegionId(ValueObject):
    """Region identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize region ID with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for region ID validation."""
        return "region_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for region ID."""
        return [
            ValidationRuleBuilder.not_empty("Region ID"),
            ValidationRuleBuilder.string_type("Region ID"),
            ValidationRuleBuilder.min_length(2, "Region ID"),
            ValidationRuleBuilder.max_length(20, "Region ID"),
            # Regions follow patterns like "us-east-1", "eu-west-2"
            ValidationRuleBuilder.regex_pattern(
                r'^[a-z]{2,3}-[a-z]+-\\d+$',
                "Region ID"
            )
        ]


@dataclass(frozen=True) 
class AdvancedRealmId(ValueObject):
    """Keycloak realm identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize realm ID with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for realm ID validation."""
        return "realm_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for realm ID."""
        return [
            ValidationRuleBuilder.not_empty("Realm ID"),
            ValidationRuleBuilder.string_type("Realm ID"),
            ValidationRuleBuilder.min_length(3, "Realm ID"),
            ValidationRuleBuilder.max_length(100, "Realm ID"),
            ValidationRuleBuilder.alphanumeric_only("Realm ID", allow_hyphens=True)
        ]


@dataclass(frozen=True)
class AdvancedKeycloakUserId(ValueObject):
    """Keycloak user identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize Keycloak user ID with runtime validation."""
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for Keycloak user ID validation."""
        return "keycloak_user_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for Keycloak user ID."""
        return [
            ValidationRuleBuilder.not_empty("Keycloak User ID"),
            ValidationRuleBuilder.string_type("Keycloak User ID"),
            ValidationRuleBuilder.uuid_format("Keycloak User ID")
        ]


@dataclass(frozen=True)
class AdvancedTokenId(ValueObject):
    """Token identifier with advanced configurable validation."""
    
    def __init__(self, value: str):
        """Initialize token ID with runtime validation.""" 
        super().__init__(value)
    
    @classmethod
    def get_value_object_name(cls) -> str:
        """Configuration key name for token ID validation."""
        return "token_id"
    
    @classmethod
    def get_default_validation_rules(cls) -> List[ValidationRule]:
        """Default validation rules for token ID."""
        return [
            ValidationRuleBuilder.not_empty("Token ID"),
            ValidationRuleBuilder.string_type("Token ID"),
            ValidationRuleBuilder.uuid_format("Token ID")
        ]


# Utility functions for global configuration
def set_value_object_configuration(config: ConfigurationProtocol) -> None:
    """Set global configuration for all configurable value objects.
    
    Args:
        config: Configuration provider instance
    """
    ValueObject.set_configuration(config)


def clear_value_object_cache() -> None:
    """Clear validation rule cache for all value objects.
    
    Call this when configuration changes at runtime.
    """
    ValueObject.clear_validation_cache()


def get_value_object_statistics() -> Dict[str, Any]:
    """Get statistics about value object validation configuration.
    
    Returns:
        Dictionary with validation statistics
    """
    return ValueObject.get_validation_statistics()


# Backward compatibility aliases
ConfigurableValueObject = ValueObject
ConfigurableUserId = AdvancedUserId
ConfigurableTenantId = AdvancedTenantId
ConfigurableOrganizationId = AdvancedOrganizationId
ConfigurablePermissionCode = AdvancedPermissionCode
ConfigurableRoleCode = AdvancedRoleCode
ConfigurableDatabaseConnectionId = AdvancedDatabaseConnectionId
ConfigurableRegionId = AdvancedRegionId
ConfigurableRealmId = AdvancedRealmId
ConfigurableKeycloakUserId = AdvancedKeycloakUserId
ConfigurableTokenId = AdvancedTokenId


# Event-related value objects
from uuid import UUID, uuid4

@dataclass(frozen=True)
class EventId(ValueObject):
    """Event identifier value object."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"EventId must be a valid UUID, got: {self.value}")

@dataclass(frozen=True) 
class WebhookEndpointId(ValueObject):
    """Webhook endpoint identifier value object."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"WebhookEndpointId must be a valid UUID, got: {self.value}")

@dataclass(frozen=True)
class WebhookEventTypeId(ValueObject):
    """Webhook event type identifier value object."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"WebhookEventTypeId must be a valid UUID, got: {self.value}")

@dataclass(frozen=True)
class WebhookDeliveryId(ValueObject):
    """Webhook delivery identifier value object."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"WebhookDeliveryId must be a valid UUID, got: {self.value}")

@dataclass(frozen=True)
class WebhookSubscriptionId(ValueObject):
    """Webhook subscription identifier value object."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"WebhookSubscriptionId must be a valid UUID, got: {self.value}")

@dataclass(frozen=True)
class EventType(ValueObject):
    """Event type value object (e.g., 'organization.created')."""
    value: str
    
    def __post_init__(self):
        if not isinstance(self.value, str):
            raise ValueError("EventType must be a string")
        
        if not self.value or not self.value.strip():
            raise ValueError("EventType cannot be empty")
            
        # Event type format: category.action (e.g., organization.created)
        if '.' not in self.value or self.value.count('.') != 1:
            raise ValueError("EventType must be in format 'category.action'")
        
        # Clean and validate format
        clean_value = self.value.strip().lower()
        if not re.match(r'^[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*$', clean_value):
            raise ValueError("EventType must contain only lowercase letters, numbers, and underscores")
        
        object.__setattr__(self, 'value', clean_value)
    
    @property
    def category(self) -> str:
        """Get event category (part before the dot)."""
        return self.value.split('.')[0]
    
    @property  
    def action(self) -> str:
        """Get event action (part after the dot)."""
        return self.value.split('.')[1]

@dataclass(frozen=True)
class ActionId(ValueObject):
    """Event action identifier value object."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"ActionId must be a valid UUID, got: {self.value}")

@dataclass(frozen=True)
class ActionExecutionId(ValueObject):
    """Action execution identifier value object."""
    value: UUID
    
    def __post_init__(self):
        if not isinstance(self.value, UUID):
            try:
                object.__setattr__(self, 'value', UUID(self.value))
            except (ValueError, TypeError):
                raise ValueError(f"ActionExecutionId must be a valid UUID, got: {self.value}")
