"""Configuration domain entities for neo-commons configuration feature.

Represents configuration values, settings, and metadata following domain-driven design
with support for multiple sources (environment, database, files, external services).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Literal
from dataclasses import dataclass, field
from enum import Enum

from ....core.exceptions import ConfigurationError


class ConfigScope(Enum):
    """Configuration scope levels."""
    GLOBAL = "global"
    SERVICE = "service"  
    TENANT = "tenant"
    USER = "user"
    FEATURE = "feature"


class ConfigType(Enum):
    """Configuration value types."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"
    SECRET = "secret"
    URL = "url"
    EMAIL = "email"


class ConfigSource(Enum):
    """Configuration sources."""
    ENVIRONMENT = "environment"
    DATABASE = "database"
    FILE = "file"
    EXTERNAL = "external"
    DEFAULT = "default"
    OVERRIDE = "override"


@dataclass(frozen=True)
class ConfigKey:
    """Immutable value object for configuration key with validation."""
    
    value: str
    scope: ConfigScope = ConfigScope.GLOBAL
    
    def __post_init__(self):
        """Validate configuration key format."""
        if not self.value:
            raise ConfigurationError("Configuration key cannot be empty")
        
        if len(self.value) > 200:
            raise ConfigurationError(f"Configuration key cannot exceed 200 characters: {len(self.value)}")
        
        # Validate key format (alphanumeric, underscores, dots, hyphens)
        import re
        if not re.match(r'^[a-zA-Z0-9._-]+$', self.value):
            raise ConfigurationError(f"Configuration key contains invalid characters: {self.value}")
        
        # Prevent reserved prefixes
        reserved_prefixes = ['__', 'SYSTEM_', 'INTERNAL_']
        if any(self.value.startswith(prefix) for prefix in reserved_prefixes):
            raise ConfigurationError(f"Configuration key uses reserved prefix: {self.value}")
    
    @property
    def namespace(self) -> str:
        """Extract namespace from key (everything before first dot)."""
        if '.' in self.value:
            return self.value.split('.')[0]
        return ''
    
    @property
    def name(self) -> str:
        """Extract name from key (everything after last dot)."""
        if '.' in self.value:
            return self.value.split('.')[-1]
        return self.value
    
    def __str__(self) -> str:
        return f"{self.scope.value}:{self.value}"


@dataclass
class ConfigValue:
    """Domain entity representing a configuration value with metadata."""
    
    key: ConfigKey
    value: Any
    config_type: ConfigType
    source: ConfigSource
    description: Optional[str] = None
    is_sensitive: bool = False
    is_required: bool = False
    default_value: Any = None
    validation_pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Validate configuration value consistency."""
        if self.metadata is None:
            self.metadata = {}
        
        # Validate value against type
        self._validate_value_type()
        
        # Validate against constraints
        self._validate_constraints()
        
        # Mark secrets as sensitive
        if self.config_type == ConfigType.SECRET:
            object.__setattr__(self, 'is_sensitive', True)
    
    def _validate_value_type(self) -> None:
        """Validate that value matches declared type."""
        if self.value is None and not self.is_required:
            return
        
        try:
            if self.config_type == ConfigType.STRING:
                if not isinstance(self.value, str):
                    raise ConfigurationError(f"Value must be string, got {type(self.value)}")
            
            elif self.config_type == ConfigType.INTEGER:
                if not isinstance(self.value, int):
                    raise ConfigurationError(f"Value must be integer, got {type(self.value)}")
            
            elif self.config_type == ConfigType.FLOAT:
                if not isinstance(self.value, (int, float)):
                    raise ConfigurationError(f"Value must be float, got {type(self.value)}")
            
            elif self.config_type == ConfigType.BOOLEAN:
                if not isinstance(self.value, bool):
                    raise ConfigurationError(f"Value must be boolean, got {type(self.value)}")
            
            elif self.config_type == ConfigType.LIST:
                if not isinstance(self.value, list):
                    raise ConfigurationError(f"Value must be list, got {type(self.value)}")
            
            elif self.config_type == ConfigType.JSON:
                if not isinstance(self.value, (dict, list)):
                    raise ConfigurationError(f"Value must be dict or list for JSON type, got {type(self.value)}")
            
            elif self.config_type == ConfigType.URL:
                if not isinstance(self.value, str):
                    raise ConfigurationError(f"URL value must be string, got {type(self.value)}")
                # Basic URL validation
                if not (self.value.startswith(('http://', 'https://', 'ftp://')) or '://' in self.value):
                    raise ConfigurationError(f"Invalid URL format: {self.value}")
            
            elif self.config_type == ConfigType.EMAIL:
                if not isinstance(self.value, str):
                    raise ConfigurationError(f"Email value must be string, got {type(self.value)}")
                # Basic email validation
                if '@' not in self.value or '.' not in self.value.split('@')[1]:
                    raise ConfigurationError(f"Invalid email format: {self.value}")
        
        except Exception as e:
            raise ConfigurationError(f"Type validation failed for {self.key}: {e}")
    
    def _validate_constraints(self) -> None:
        """Validate value against defined constraints."""
        if self.value is None:
            if self.is_required:
                raise ConfigurationError(f"Required configuration value is missing: {self.key}")
            return
        
        # Validate allowed values
        if self.allowed_values and self.value not in self.allowed_values:
            raise ConfigurationError(f"Value {self.value} not in allowed values: {self.allowed_values}")
        
        # Validate numeric ranges
        if self.config_type in (ConfigType.INTEGER, ConfigType.FLOAT):
            if self.min_value is not None and self.value < self.min_value:
                raise ConfigurationError(f"Value {self.value} below minimum {self.min_value}")
            if self.max_value is not None and self.value > self.max_value:
                raise ConfigurationError(f"Value {self.value} above maximum {self.max_value}")
        
        # Validate string length for strings
        if self.config_type == ConfigType.STRING and isinstance(self.value, str):
            if self.min_value is not None and len(self.value) < self.min_value:
                raise ConfigurationError(f"String length {len(self.value)} below minimum {self.min_value}")
            if self.max_value is not None and len(self.value) > self.max_value:
                raise ConfigurationError(f"String length {len(self.value)} above maximum {self.max_value}")
        
        # Validate regex pattern
        if self.validation_pattern and isinstance(self.value, str):
            import re
            if not re.match(self.validation_pattern, self.value):
                raise ConfigurationError(f"Value does not match validation pattern: {self.validation_pattern}")
    
    def is_expired(self) -> bool:
        """Check if configuration value has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if configuration value is valid and not expired."""
        try:
            self._validate_value_type()
            self._validate_constraints()
            return not self.is_expired()
        except ConfigurationError:
            return False
    
    def get_safe_value(self) -> Any:
        """Get value with sensitive data masked."""
        if self.is_sensitive:
            if isinstance(self.value, str):
                return "***" if len(self.value) <= 8 else f"{self.value[:3]}***{self.value[-2:]}"
            return "***"
        return self.value
    
    def get_typed_value(self) -> Any:
        """Get value converted to appropriate Python type."""
        if self.value is None:
            return self.default_value
        
        if self.config_type == ConfigType.BOOLEAN and isinstance(self.value, str):
            return self.value.lower() in ('true', '1', 'yes', 'on')
        
        return self.value
    
    def clone_with_new_value(self, new_value: Any) -> 'ConfigValue':
        """Create a new ConfigValue with updated value and incremented version."""
        return ConfigValue(
            key=self.key,
            value=new_value,
            config_type=self.config_type,
            source=self.source,
            description=self.description,
            is_sensitive=self.is_sensitive,
            is_required=self.is_required,
            default_value=self.default_value,
            validation_pattern=self.validation_pattern,
            allowed_values=self.allowed_values,
            min_value=self.min_value,
            max_value=self.max_value,
            expires_at=self.expires_at,
            metadata=self.metadata.copy(),
            created_at=self.created_at,
            updated_at=datetime.utcnow(),
            version=self.version + 1
        )
    
    def __str__(self) -> str:
        value_display = self.get_safe_value()
        return f"Config({self.key}={value_display})"
    
    def __repr__(self) -> str:
        flags = []
        if self.is_sensitive:
            flags.append("sensitive")
        if self.is_required:
            flags.append("required")
        if self.is_expired():
            flags.append("expired")
        
        flag_info = f" [{', '.join(flags)}]" if flags else ""
        return f"ConfigValue({self.key}, type={self.config_type.value}, source={self.source.value}{flag_info})"


@dataclass
class ConfigSchema:
    """Configuration schema definition for validation and documentation."""
    
    key: ConfigKey
    config_type: ConfigType
    description: str
    is_required: bool = False
    default_value: Any = None
    validation_pattern: Optional[str] = None
    allowed_values: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    is_sensitive: bool = False
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def create_config_value(self, value: Any, source: ConfigSource) -> ConfigValue:
        """Create a ConfigValue instance from this schema."""
        return ConfigValue(
            key=self.key,
            value=value,
            config_type=self.config_type,
            source=source,
            description=self.description,
            is_sensitive=self.is_sensitive,
            is_required=self.is_required,
            default_value=self.default_value,
            validation_pattern=self.validation_pattern,
            allowed_values=self.allowed_values,
            min_value=self.min_value,
            max_value=self.max_value
        )
    
    def validate_value(self, value: Any) -> bool:
        """Validate a value against this schema."""
        try:
            config_value = self.create_config_value(value, ConfigSource.DEFAULT)
            return config_value.is_valid()
        except ConfigurationError:
            return False


@dataclass
class ConfigGroup:
    """Group of related configuration values with metadata."""
    
    name: str
    description: str
    scope: ConfigScope
    configs: Dict[str, ConfigValue] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def add_config(self, config: ConfigValue) -> None:
        """Add a configuration value to this group."""
        if config.key.scope != self.scope:
            raise ConfigurationError(f"Config scope {config.key.scope} doesn't match group scope {self.scope}")
        
        self.configs[config.key.value] = config
        self.updated_at = datetime.utcnow()
        self.version += 1
    
    def get_config(self, key: str) -> Optional[ConfigValue]:
        """Get a configuration value by key."""
        return self.configs.get(key)
    
    def remove_config(self, key: str) -> bool:
        """Remove a configuration value by key."""
        if key in self.configs:
            del self.configs[key]
            self.updated_at = datetime.utcnow()
            self.version += 1
            return True
        return False
    
    def get_all_configs(self) -> List[ConfigValue]:
        """Get all configuration values in this group."""
        return list(self.configs.values())
    
    def get_valid_configs(self) -> List[ConfigValue]:
        """Get all valid (non-expired) configuration values."""
        return [config for config in self.configs.values() if config.is_valid()]
    
    def has_required_configs(self) -> bool:
        """Check if all required configurations are present and valid."""
        for config in self.configs.values():
            if config.is_required and (config.value is None or not config.is_valid()):
                return False
        return True
    
    def __len__(self) -> int:
        return len(self.configs)
    
    def __contains__(self, key: str) -> bool:
        return key in self.configs