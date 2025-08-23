"""Protocol interfaces for configuration feature dependency injection.

Defines contracts for configuration management, sources, caching, and validation
following clean architecture and protocol-based dependency injection patterns.
"""

from abc import abstractmethod
from typing import Protocol, runtime_checkable, List, Optional, Dict, Any, Set
from datetime import datetime

from .config import ConfigKey, ConfigValue, ConfigSchema, ConfigGroup, ConfigScope, ConfigSource


@runtime_checkable
class ConfigurationProvider(Protocol):
    """Protocol for configuration value providers from various sources."""
    
    @abstractmethod
    async def get_config(self, key: ConfigKey) -> Optional[ConfigValue]:
        """Get a configuration value by key."""
        ...
    
    @abstractmethod
    async def get_configs(self, keys: List[ConfigKey]) -> Dict[str, ConfigValue]:
        """Get multiple configuration values by keys."""
        ...
    
    @abstractmethod
    async def get_configs_by_scope(self, scope: ConfigScope) -> List[ConfigValue]:
        """Get all configuration values for a specific scope."""
        ...
    
    @abstractmethod
    async def get_configs_by_namespace(self, namespace: str, scope: ConfigScope = ConfigScope.GLOBAL) -> List[ConfigValue]:
        """Get all configuration values for a specific namespace."""
        ...
    
    @abstractmethod
    async def set_config(self, config: ConfigValue) -> bool:
        """Set a configuration value."""
        ...
    
    @abstractmethod
    async def delete_config(self, key: ConfigKey) -> bool:
        """Delete a configuration value."""
        ...
    
    @abstractmethod
    async def search_configs(
        self,
        query: str,
        scope: Optional[ConfigScope] = None,
        namespace: Optional[str] = None
    ) -> List[ConfigValue]:
        """Search configuration values by key or description."""
        ...


@runtime_checkable
class ConfigurationRepository(Protocol):
    """Protocol for configuration data persistence operations."""
    
    @abstractmethod
    async def save_config(self, config: ConfigValue) -> ConfigValue:
        """Save a configuration value to persistent storage."""
        ...
    
    @abstractmethod
    async def load_config(self, key: ConfigKey) -> Optional[ConfigValue]:
        """Load a configuration value from persistent storage."""
        ...
    
    @abstractmethod
    async def load_configs_by_scope(self, scope: ConfigScope) -> List[ConfigValue]:
        """Load all configuration values for a scope."""
        ...
    
    @abstractmethod
    async def load_configs_by_keys(self, keys: List[ConfigKey]) -> List[ConfigValue]:
        """Load multiple configuration values by keys."""
        ...
    
    @abstractmethod
    async def update_config(self, key: ConfigKey, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update a configuration value."""
        ...
    
    @abstractmethod
    async def delete_config(self, key: ConfigKey) -> bool:
        """Delete a configuration value from persistent storage."""
        ...
    
    @abstractmethod
    async def list_keys_by_pattern(self, pattern: str, scope: Optional[ConfigScope] = None) -> List[ConfigKey]:
        """List configuration keys matching a pattern."""
        ...
    
    @abstractmethod
    async def get_config_history(self, key: ConfigKey, limit: int = 10) -> List[ConfigValue]:
        """Get configuration value history."""
        ...
    
    @abstractmethod
    async def cleanup_expired_configs(self) -> int:
        """Clean up expired configuration values."""
        ...


@runtime_checkable
class ConfigurationCache(Protocol):
    """Protocol for configuration caching operations."""
    
    @abstractmethod
    async def get_cached_config(self, key: ConfigKey) -> Optional[ConfigValue]:
        """Get a cached configuration value."""
        ...
    
    @abstractmethod
    async def cache_config(self, config: ConfigValue, ttl: Optional[int] = None) -> bool:
        """Cache a configuration value with optional TTL."""
        ...
    
    @abstractmethod
    async def invalidate_config(self, key: ConfigKey) -> bool:
        """Invalidate a cached configuration value."""
        ...
    
    @abstractmethod
    async def invalidate_namespace(self, namespace: str, scope: ConfigScope = ConfigScope.GLOBAL) -> bool:
        """Invalidate all cached configurations for a namespace."""
        ...
    
    @abstractmethod
    async def invalidate_scope(self, scope: ConfigScope) -> bool:
        """Invalidate all cached configurations for a scope."""
        ...
    
    @abstractmethod
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        ...
    
    @abstractmethod
    async def clear_cache(self) -> bool:
        """Clear all cached configurations."""
        ...


@runtime_checkable
class ConfigurationValidator(Protocol):
    """Protocol for configuration validation and schema management."""
    
    @abstractmethod
    async def validate_config(self, config: ConfigValue) -> List[str]:
        """Validate a configuration value, returning list of errors."""
        ...
    
    @abstractmethod
    async def validate_configs(self, configs: List[ConfigValue]) -> Dict[str, List[str]]:
        """Validate multiple configuration values."""
        ...
    
    @abstractmethod
    async def register_schema(self, schema: ConfigSchema) -> bool:
        """Register a configuration schema for validation."""
        ...
    
    @abstractmethod
    async def get_schema(self, key: ConfigKey) -> Optional[ConfigSchema]:
        """Get configuration schema for a key."""
        ...
    
    @abstractmethod
    async def list_schemas(self, scope: Optional[ConfigScope] = None) -> List[ConfigSchema]:
        """List all registered schemas."""
        ...
    
    @abstractmethod
    async def validate_against_schema(self, config: ConfigValue) -> List[str]:
        """Validate configuration against registered schema."""
        ...


@runtime_checkable
class ConfigurationSource(Protocol):
    """Protocol for configuration sources (environment, files, external APIs)."""
    
    @abstractmethod
    async def load_configs(self) -> List[ConfigValue]:
        """Load all configurations from this source."""
        ...
    
    @abstractmethod
    async def load_config(self, key: ConfigKey) -> Optional[ConfigValue]:
        """Load a specific configuration from this source."""
        ...
    
    @abstractmethod
    async def is_available(self) -> bool:
        """Check if this configuration source is available."""
        ...
    
    @abstractmethod
    async def get_source_info(self) -> Dict[str, Any]:
        """Get information about this configuration source."""
        ...
    
    @abstractmethod
    async def watch_changes(self, callback) -> bool:
        """Watch for configuration changes in this source."""
        ...
    
    @abstractmethod
    async def stop_watching(self) -> bool:
        """Stop watching for configuration changes."""
        ...


@runtime_checkable
class ConfigurationWatcher(Protocol):
    """Protocol for watching configuration changes."""
    
    @abstractmethod
    async def watch_config(self, key: ConfigKey, callback) -> bool:
        """Watch for changes to a specific configuration."""
        ...
    
    @abstractmethod
    async def watch_namespace(self, namespace: str, scope: ConfigScope, callback) -> bool:
        """Watch for changes to all configurations in a namespace."""
        ...
    
    @abstractmethod
    async def watch_scope(self, scope: ConfigScope, callback) -> bool:
        """Watch for changes to all configurations in a scope."""
        ...
    
    @abstractmethod
    async def stop_watching(self, key: ConfigKey) -> bool:
        """Stop watching a specific configuration."""
        ...
    
    @abstractmethod
    async def stop_all_watching(self) -> bool:
        """Stop all configuration watching."""
        ...
    
    @abstractmethod
    async def get_watched_configs(self) -> List[ConfigKey]:
        """Get list of currently watched configurations."""
        ...


@runtime_checkable
class ConfigurationExporter(Protocol):
    """Protocol for exporting and importing configuration sets."""
    
    @abstractmethod
    async def export_configs(
        self,
        scope: Optional[ConfigScope] = None,
        namespace: Optional[str] = None,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Export configurations to a dictionary."""
        ...
    
    @abstractmethod
    async def export_to_file(
        self,
        file_path: str,
        scope: Optional[ConfigScope] = None,
        namespace: Optional[str] = None,
        include_sensitive: bool = False,
        format: str = "json"
    ) -> bool:
        """Export configurations to a file."""
        ...
    
    @abstractmethod
    async def import_configs(
        self,
        data: Dict[str, Any],
        scope: ConfigScope = ConfigScope.GLOBAL,
        override_existing: bool = False
    ) -> List[str]:
        """Import configurations from a dictionary."""
        ...
    
    @abstractmethod
    async def import_from_file(
        self,
        file_path: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        override_existing: bool = False,
        format: str = "json"
    ) -> List[str]:
        """Import configurations from a file."""
        ...


@runtime_checkable
class ConfigurationAuditor(Protocol):
    """Protocol for configuration audit and compliance tracking."""
    
    @abstractmethod
    async def log_config_change(
        self,
        key: ConfigKey,
        old_value: Optional[Any],
        new_value: Any,
        changed_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Log a configuration change for audit purposes."""
        ...
    
    @abstractmethod
    async def get_config_audit_log(
        self,
        key: ConfigKey,
        limit: int = 100,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log for a specific configuration."""
        ...
    
    @abstractmethod
    async def get_audit_summary(
        self,
        scope: Optional[ConfigScope] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit summary for configurations."""
        ...
    
    @abstractmethod
    async def check_compliance(self, scope: Optional[ConfigScope] = None) -> Dict[str, Any]:
        """Check configuration compliance against security policies."""
        ...


@runtime_checkable
class ConfigurationManager(Protocol):
    """Main protocol for comprehensive configuration management."""
    
    @abstractmethod
    async def get(self, key: str, scope: ConfigScope = ConfigScope.GLOBAL, default: Any = None) -> Any:
        """Get configuration value with automatic type conversion."""
        ...
    
    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.GLOBAL,
        config_type: Optional[str] = None,
        is_sensitive: bool = False
    ) -> bool:
        """Set configuration value with automatic type detection."""
        ...
    
    @abstractmethod
    async def delete(self, key: str, scope: ConfigScope = ConfigScope.GLOBAL) -> bool:
        """Delete a configuration value."""
        ...
    
    @abstractmethod
    async def get_group(self, name: str, scope: ConfigScope = ConfigScope.GLOBAL) -> Optional[ConfigGroup]:
        """Get a configuration group."""
        ...
    
    @abstractmethod
    async def create_group(self, name: str, description: str, scope: ConfigScope = ConfigScope.GLOBAL) -> ConfigGroup:
        """Create a new configuration group."""
        ...
    
    @abstractmethod
    async def list_groups(self, scope: Optional[ConfigScope] = None) -> List[ConfigGroup]:
        """List all configuration groups."""
        ...
    
    @abstractmethod
    async def refresh_from_sources(self) -> int:
        """Refresh configurations from all sources."""
        ...
    
    @abstractmethod
    async def validate_all(self, scope: Optional[ConfigScope] = None) -> Dict[str, List[str]]:
        """Validate all configurations."""
        ...
    
    @abstractmethod
    async def get_health_status(self) -> Dict[str, Any]:
        """Get configuration system health status."""
        ...