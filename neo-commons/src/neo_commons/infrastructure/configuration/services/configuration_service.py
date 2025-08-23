"""Configuration service for business logic orchestration.

Coordinates configuration management across multiple sources, caching, validation,
and change tracking following clean architecture principles.
"""

from typing import Any, Dict, List, Optional, Set, Union
from datetime import datetime, timedelta
import asyncio
import logging

from ....core.exceptions import ConfigurationError
from ..entities import (
    ConfigKey, ConfigValue, ConfigSchema, ConfigGroup,
    ConfigScope, ConfigType, ConfigSource,
    ConfigurationProvider, ConfigurationRepository, ConfigurationCache,
    ConfigurationValidator, ConfigurationSource as ConfigSourceProtocol,
    ConfigurationWatcher, ConfigurationAuditor, ConfigurationManager
)


logger = logging.getLogger(__name__)


class ConfigurationService:
    """Service orchestrating configuration operations with multiple sources and caching."""
    
    def __init__(
        self,
        repository: ConfigurationRepository,
        cache: Optional[ConfigurationCache] = None,
        validator: Optional[ConfigurationValidator] = None,
        auditor: Optional[ConfigurationAuditor] = None,
        sources: Optional[List[ConfigSourceProtocol]] = None,
        watcher: Optional[ConfigurationWatcher] = None
    ):
        self.repository = repository
        self.cache = cache
        self.validator = validator
        self.auditor = auditor
        self.sources = sources or []
        self.watcher = watcher
        
        # Source priority (higher priority sources override lower ones)
        self._source_priority = {
            ConfigSource.OVERRIDE: 100,
            ConfigSource.ENVIRONMENT: 90,
            ConfigSource.DATABASE: 80,
            ConfigSource.EXTERNAL: 70,
            ConfigSource.FILE: 60,
            ConfigSource.DEFAULT: 10
        }
        
        # Internal state
        self._groups: Dict[str, ConfigGroup] = {}
        self._schemas: Dict[str, ConfigSchema] = {}
        self._change_listeners: Dict[str, List] = {}
        self._last_refresh: Optional[datetime] = None
    
    # Core Configuration Operations
    
    async def get_config(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        default: Any = None,
        use_cache: bool = True
    ) -> Any:
        """Get configuration value with automatic type conversion and caching."""
        config_key = ConfigKey(key, scope)
        
        try:
            # Try cache first if enabled
            config_value = None
            if use_cache and self.cache:
                config_value = await self.cache.get_cached_config(config_key)
                if config_value and config_value.is_valid():
                    logger.debug(f"Cache hit for config: {config_key}")
                    return config_value.get_typed_value()
            
            # Load from repository
            config_value = await self.repository.load_config(config_key)
            
            if not config_value:
                # Try loading from sources
                config_value = await self._load_from_sources(config_key)
            
            if config_value and config_value.is_valid():
                # Cache the result
                if self.cache:
                    await self.cache.cache_config(config_value)
                
                return config_value.get_typed_value()
            
            # Return default if no valid config found
            return default
            
        except Exception as e:
            logger.error(f"Failed to get config {config_key}: {e}")
            return default
    
    async def set_config(
        self,
        key: str,
        value: Any,
        scope: ConfigScope = ConfigScope.GLOBAL,
        config_type: Optional[ConfigType] = None,
        is_sensitive: bool = False,
        description: Optional[str] = None,
        expires_in: Optional[timedelta] = None,
        changed_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Set configuration value with validation and auditing."""
        config_key = ConfigKey(key, scope)
        
        try:
            # Auto-detect type if not provided
            if config_type is None:
                config_type = self._detect_config_type(value)
            
            # Get old value for auditing
            old_config = await self.repository.load_config(config_key)
            old_value = old_config.value if old_config else None
            
            # Create new config value
            expires_at = datetime.utcnow() + expires_in if expires_in else None
            
            config_value = ConfigValue(
                key=config_key,
                value=value,
                config_type=config_type,
                source=ConfigSource.DATABASE,
                description=description,
                is_sensitive=is_sensitive,
                expires_at=expires_at
            )
            
            # Validate the configuration
            if self.validator:
                errors = await self.validator.validate_config(config_value)
                if errors:
                    raise ConfigurationError(f"Configuration validation failed: {', '.join(errors)}")
            
            # Save to repository
            saved_config = await self.repository.save_config(config_value)
            
            # Update cache
            if self.cache:
                await self.cache.cache_config(saved_config)
            
            # Log audit trail
            if self.auditor:
                await self.auditor.log_config_change(
                    config_key, old_value, value, changed_by, reason
                )
            
            # Notify change listeners
            await self._notify_change_listeners(config_key, old_value, value)
            
            logger.info(f"Set config: {config_key} = {config_value.get_safe_value()}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set config {config_key}: {e}")
            raise ConfigurationError(f"Failed to set configuration: {e}")
    
    async def delete_config(
        self,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        changed_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Delete configuration value with auditing."""
        config_key = ConfigKey(key, scope)
        
        try:
            # Get current value for auditing
            old_config = await self.repository.load_config(config_key)
            old_value = old_config.value if old_config else None
            
            # Delete from repository
            success = await self.repository.delete_config(config_key)
            
            if success:
                # Invalidate cache
                if self.cache:
                    await self.cache.invalidate_config(config_key)
                
                # Log audit trail
                if self.auditor:
                    await self.auditor.log_config_change(
                        config_key, old_value, None, changed_by, reason
                    )
                
                # Notify change listeners
                await self._notify_change_listeners(config_key, old_value, None)
                
                logger.info(f"Deleted config: {config_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete config {config_key}: {e}")
            return False
    
    async def get_configs_by_namespace(
        self,
        namespace: str,
        scope: ConfigScope = ConfigScope.GLOBAL
    ) -> Dict[str, Any]:
        """Get all configuration values for a namespace."""
        try:
            configs = await self.repository.load_configs_by_scope(scope)
            
            result = {}
            for config in configs:
                if config.key.namespace == namespace and config.is_valid():
                    result[config.key.name] = config.get_typed_value()
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get configs for namespace {namespace}: {e}")
            return {}
    
    # Group Management
    
    async def create_group(
        self,
        name: str,
        description: str,
        scope: ConfigScope = ConfigScope.GLOBAL
    ) -> ConfigGroup:
        """Create a new configuration group."""
        if name in self._groups:
            raise ConfigurationError(f"Configuration group already exists: {name}")
        
        group = ConfigGroup(
            name=name,
            description=description,
            scope=scope,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self._groups[name] = group
        logger.info(f"Created configuration group: {name}")
        return group
    
    async def get_group(self, name: str) -> Optional[ConfigGroup]:
        """Get a configuration group by name."""
        return self._groups.get(name)
    
    async def add_config_to_group(self, group_name: str, config: ConfigValue) -> bool:
        """Add a configuration to a group."""
        group = self._groups.get(group_name)
        if not group:
            raise ConfigurationError(f"Configuration group not found: {group_name}")
        
        group.add_config(config)
        return True
    
    # Schema Management
    
    async def register_schema(self, schema: ConfigSchema) -> bool:
        """Register a configuration schema for validation."""
        if self.validator:
            success = await self.validator.register_schema(schema)
            if success:
                self._schemas[schema.key.value] = schema
                logger.info(f"Registered schema for: {schema.key}")
            return success
        
        self._schemas[schema.key.value] = schema
        return True
    
    async def validate_config_value(self, key: str, value: Any, scope: ConfigScope = ConfigScope.GLOBAL) -> List[str]:
        """Validate a configuration value against its schema."""
        config_key = ConfigKey(key, scope)
        
        if self.validator:
            # Create temporary config for validation
            config_type = self._detect_config_type(value)
            temp_config = ConfigValue(
                key=config_key,
                value=value,
                config_type=config_type,
                source=ConfigSource.DEFAULT
            )
            return await self.validator.validate_config(temp_config)
        
        return []
    
    # Source Management
    
    async def refresh_from_sources(self) -> int:
        """Refresh configurations from all configured sources."""
        total_loaded = 0
        
        for source in self.sources:
            try:
                if await source.is_available():
                    configs = await source.load_configs()
                    
                    for config in configs:
                        # Only update if source has higher priority
                        existing = await self.repository.load_config(config.key)
                        
                        if not existing or self._should_override(existing.source, config.source):
                            await self.repository.save_config(config)
                            
                            # Update cache
                            if self.cache:
                                await self.cache.cache_config(config)
                            
                            total_loaded += 1
                    
                    logger.info(f"Loaded {len(configs)} configs from source: {source}")
                else:
                    logger.warning(f"Configuration source unavailable: {source}")
                    
            except Exception as e:
                logger.error(f"Failed to load from source {source}: {e}")
        
        self._last_refresh = datetime.utcnow()
        logger.info(f"Refreshed {total_loaded} configurations from {len(self.sources)} sources")
        return total_loaded
    
    async def _load_from_sources(self, key: ConfigKey) -> Optional[ConfigValue]:
        """Load specific configuration from sources."""
        best_config = None
        best_priority = -1
        
        for source in self.sources:
            try:
                if await source.is_available():
                    config = await source.load_config(key)
                    if config:
                        priority = self._source_priority.get(config.source, 0)
                        if priority > best_priority:
                            best_config = config
                            best_priority = priority
            except Exception as e:
                logger.error(f"Failed to load {key} from source {source}: {e}")
        
        return best_config
    
    # Validation and Health
    
    async def validate_all_configs(self, scope: Optional[ConfigScope] = None) -> Dict[str, List[str]]:
        """Validate all configurations."""
        if not self.validator:
            return {}
        
        configs = []
        if scope:
            configs = await self.repository.load_configs_by_scope(scope)
        else:
            # Load all configs from all scopes
            for config_scope in ConfigScope:
                scope_configs = await self.repository.load_configs_by_scope(config_scope)
                configs.extend(scope_configs)
        
        return await self.validator.validate_configs(configs)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get configuration system health status."""
        status = {
            "healthy": True,
            "last_refresh": self._last_refresh,
            "sources": {},
            "cache": {},
            "repository": {"available": True},
            "total_configs": 0,
            "expired_configs": 0,
            "invalid_configs": 0
        }
        
        try:
            # Check sources
            for i, source in enumerate(self.sources):
                source_available = await source.is_available()
                status["sources"][f"source_{i}"] = {
                    "available": source_available,
                    "info": await source.get_source_info() if source_available else {}
                }
                if not source_available:
                    status["healthy"] = False
            
            # Check cache
            if self.cache:
                cache_stats = await self.cache.get_cache_stats()
                status["cache"] = cache_stats
            
            # Count configurations
            total_configs = 0
            expired_configs = 0
            invalid_configs = 0
            
            for scope in ConfigScope:
                configs = await self.repository.load_configs_by_scope(scope)
                total_configs += len(configs)
                
                for config in configs:
                    if config.is_expired():
                        expired_configs += 1
                    if not config.is_valid():
                        invalid_configs += 1
            
            status["total_configs"] = total_configs
            status["expired_configs"] = expired_configs
            status["invalid_configs"] = invalid_configs
            
            if expired_configs > 0 or invalid_configs > 0:
                status["healthy"] = False
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            status["healthy"] = False
            status["error"] = str(e)
        
        return status
    
    # Change Watching
    
    async def watch_config(self, key: str, scope: ConfigScope, callback) -> bool:
        """Watch for changes to a specific configuration."""
        config_key = ConfigKey(key, scope)
        key_str = str(config_key)
        
        if key_str not in self._change_listeners:
            self._change_listeners[key_str] = []
        
        self._change_listeners[key_str].append(callback)
        
        # Register with watcher if available
        if self.watcher:
            return await self.watcher.watch_config(config_key, callback)
        
        return True
    
    async def _notify_change_listeners(self, key: ConfigKey, old_value: Any, new_value: Any) -> None:
        """Notify all listeners of configuration changes."""
        key_str = str(key)
        listeners = self._change_listeners.get(key_str, [])
        
        for callback in listeners:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(key, old_value, new_value)
                else:
                    callback(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Error notifying config change listener: {e}")
    
    # Utility Methods
    
    def _detect_config_type(self, value: Any) -> ConfigType:
        """Auto-detect configuration type from value."""
        if isinstance(value, bool):
            return ConfigType.BOOLEAN
        elif isinstance(value, int):
            return ConfigType.INTEGER
        elif isinstance(value, float):
            return ConfigType.FLOAT
        elif isinstance(value, list):
            return ConfigType.LIST
        elif isinstance(value, dict):
            return ConfigType.JSON
        elif isinstance(value, str):
            if '@' in value and '.' in value:
                return ConfigType.EMAIL
            elif '://' in value:
                return ConfigType.URL
            else:
                return ConfigType.STRING
        else:
            return ConfigType.STRING
    
    def _should_override(self, existing_source: ConfigSource, new_source: ConfigSource) -> bool:
        """Check if new source should override existing configuration."""
        existing_priority = self._source_priority.get(existing_source, 0)
        new_priority = self._source_priority.get(new_source, 0)
        return new_priority > existing_priority
    
    # Maintenance Operations
    
    async def cleanup_expired_configs(self) -> int:
        """Clean up expired configuration values."""
        count = await self.repository.cleanup_expired_configs()
        
        if count > 0:
            logger.info(f"Cleaned up {count} expired configurations")
            
            # Clear cache to ensure consistency
            if self.cache:
                await self.cache.clear_cache()
        
        return count
    
    async def backup_configs(
        self,
        scope: Optional[ConfigScope] = None,
        include_sensitive: bool = False
    ) -> Dict[str, Any]:
        """Create a backup of configurations."""
        backup = {
            "timestamp": datetime.utcnow().isoformat(),
            "scope": scope.value if scope else "all",
            "include_sensitive": include_sensitive,
            "configs": {}
        }
        
        configs = []
        if scope:
            configs = await self.repository.load_configs_by_scope(scope)
        else:
            for config_scope in ConfigScope:
                scope_configs = await self.repository.load_configs_by_scope(config_scope)
                configs.extend(scope_configs)
        
        for config in configs:
            if not include_sensitive and config.is_sensitive:
                continue
            
            backup["configs"][str(config.key)] = {
                "value": config.value,
                "type": config.config_type.value,
                "source": config.source.value,
                "description": config.description,
                "metadata": config.metadata
            }
        
        logger.info(f"Created backup of {len(backup['configs'])} configurations")
        return backup