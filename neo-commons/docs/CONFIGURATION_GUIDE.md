# Neo-Commons Core Dynamic Configuration Guide

This guide explains how to effectively use the neo-commons core module's dynamic configuration capabilities and patterns.

## Overview

The neo-commons core module provides several dynamic configuration mechanisms through protocols, value objects, and shared abstractions. This guide covers best practices for implementing and using these capabilities.

## Configuration Architecture

### Core Configuration Protocols

The core module provides foundational configuration contracts in `core/shared/application.py`:

```python
from neo_commons.core.shared.application import ConfigurationProtocol

# Example implementation
class DatabaseConfigurationProvider:
    def __init__(self, config_provider: ConfigurationProtocol):
        self.config = config_provider
    
    async def get_pool_settings(self, connection_name: str) -> Dict[str, Any]:
        # Load dynamic pool configuration
        return await self.config.get_section(f"database.pools.{connection_name}")
```

### RequestContext Dynamic Configuration

The `RequestContext` entity supports runtime configuration through metadata and features:

```python
from neo_commons.core.shared.context import RequestContext
from neo_commons.core.value_objects import TenantId, UserId

# Create context with dynamic features
context = RequestContext(
    tenant_id=TenantId("tenant-123"),
    user_id=UserId("user-456"),
    tenant_features={
        "advanced_permissions": True,
        "custom_schemas": True,
        "performance_monitoring": False
    },
    request_metadata={
        "deployment_tier": "enterprise",
        "region_preference": "us-east",
        "feature_flags": ["beta_ui", "new_auth_flow"]
    }
)

# Use context for dynamic behavior
if context.has_tenant_feature("advanced_permissions"):
    # Enable advanced permission checking
    pass

# Access runtime metadata
deployment_tier = context.get_request_metadata("deployment_tier", "standard")
```

## Configuration Patterns

### 1. Tenant-Specific Configuration

```python
from neo_commons.core.shared.application import ConfigurationProtocol

class TenantAwareConfiguration:
    def __init__(self, config: ConfigurationProtocol):
        self._config = config
        self._tenant_overrides = {}
    
    async def get_tenant_setting(
        self, 
        tenant_id: str, 
        setting_key: str, 
        default: Any = None
    ) -> Any:
        """Get tenant-specific setting with fallback to global default."""
        
        # Check tenant-specific override
        tenant_key = f"tenants.{tenant_id}.{setting_key}"
        tenant_value = await self._config.get(tenant_key)
        if tenant_value is not None:
            return tenant_value
        
        # Fall back to global setting
        global_key = f"global.{setting_key}"
        return await self._config.get(global_key, default)
    
    async def set_tenant_override(
        self, 
        tenant_id: str, 
        setting_key: str, 
        value: Any
    ) -> None:
        """Set tenant-specific configuration override."""
        tenant_key = f"tenants.{tenant_id}.{setting_key}"
        await self._config.set(tenant_key, value)
        
        # Cache for performance
        self._tenant_overrides[f"{tenant_id}.{setting_key}"] = value

# Usage example
config = TenantAwareConfiguration(config_provider)

# Get tenant-specific database pool size
pool_size = await config.get_tenant_setting(
    "tenant-123", 
    "database.pool_max_size", 
    default=20
)

# Override for specific tenant
await config.set_tenant_override(
    "enterprise-client", 
    "database.pool_max_size", 
    100
)
```

### 2. Feature Flag Configuration

```python
from typing import Dict, Set
from neo_commons.core.shared.context import RequestContext

class FeatureFlagManager:
    def __init__(self, config: ConfigurationProtocol):
        self._config = config
        self._global_flags: Set[str] = set()
        self._tenant_flags: Dict[str, Set[str]] = {}
    
    async def is_feature_enabled(
        self, 
        feature_name: str, 
        context: RequestContext
    ) -> bool:
        """Check if feature is enabled for context."""
        
        # Check context tenant features first
        if context.has_tenant_feature(feature_name):
            return True
        
        # Check request metadata flags
        metadata_flags = context.get_request_metadata("feature_flags", [])
        if feature_name in metadata_flags:
            return True
        
        # Check tenant-specific configuration
        if context.tenant_id:
            tenant_flags = await self._get_tenant_flags(context.tenant_id.value)
            if feature_name in tenant_flags:
                return True
        
        # Check global configuration
        return await self._config.get(f"features.{feature_name}.enabled", False)
    
    async def _get_tenant_flags(self, tenant_id: str) -> Set[str]:
        """Get cached tenant feature flags."""
        if tenant_id not in self._tenant_flags:
            flags = await self._config.get_list(f"tenants.{tenant_id}.features", [])
            self._tenant_flags[tenant_id] = set(flags)
        return self._tenant_flags[tenant_id]

# Usage in services
class UserService:
    def __init__(self, feature_manager: FeatureFlagManager):
        self.feature_manager = feature_manager
    
    async def get_user_profile(self, context: RequestContext) -> Dict[str, Any]:
        profile = await self._get_basic_profile(context.user_id)
        
        # Add enhanced features if enabled
        if await self.feature_manager.is_feature_enabled("enhanced_profiles", context):
            profile.update(await self._get_enhanced_profile_data(context.user_id))
        
        return profile
```

### 3. Environment-Specific Configuration

```python
from enum import Enum
from neo_commons.core.shared.application import ConfigurationProtocol

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging" 
    PRODUCTION = "production"

class EnvironmentAwareConfig:
    def __init__(self, config: ConfigurationProtocol, environment: Environment):
        self._config = config
        self._environment = environment
    
    async def get_environment_setting(
        self, 
        setting_key: str, 
        default: Any = None
    ) -> Any:
        """Get environment-specific setting with fallback hierarchy."""
        
        # Try environment-specific setting first
        env_key = f"environments.{self._environment.value}.{setting_key}"
        env_value = await self._config.get(env_key)
        if env_value is not None:
            return env_value
        
        # Fall back to general setting
        return await self._config.get(setting_key, default)
    
    async def get_database_config(self) -> Dict[str, Any]:
        """Get environment-appropriate database configuration."""
        base_config = {
            "pool_min_size": await self.get_environment_setting("database.pool_min_size", 5),
            "pool_max_size": await self.get_environment_setting("database.pool_max_size", 20),
            "pool_timeout": await self.get_environment_setting("database.pool_timeout", 30),
            "ssl_mode": await self.get_environment_setting("database.ssl_mode", "require"),
        }
        
        # Environment-specific adjustments
        if self._environment == Environment.DEVELOPMENT:
            base_config.update({
                "ssl_mode": "disable",
                "pool_min_size": 1,
                "debug_queries": True
            })
        elif self._environment == Environment.PRODUCTION:
            base_config.update({
                "ssl_mode": "require",
                "pool_min_size": 10,
                "pool_max_size": 50,
                "connection_retry_attempts": 3
            })
        
        return base_config
```

### 4. Schema Resolution Configuration

```python
from neo_commons.core.value_objects import TenantId

class DynamicSchemaConfiguration:
    def __init__(self, config: ConfigurationProtocol):
        self._config = config
        self._schema_patterns = {}
    
    async def get_schema_pattern(self, tenant_tier: str = "standard") -> str:
        """Get schema naming pattern based on tenant tier."""
        pattern_key = f"schema_patterns.{tenant_tier}"
        return await self._config.get(
            pattern_key, 
            default="tenant_{tenant_slug}"  # Default pattern
        )
    
    async def resolve_tenant_schema(
        self, 
        tenant_id: TenantId, 
        tenant_slug: str,
        context: RequestContext
    ) -> str:
        """Resolve schema name with dynamic configuration."""
        
        # Get tenant tier from metadata or configuration
        tier = context.get_request_metadata("tenant_tier", "standard")
        
        # Get appropriate schema pattern
        pattern = await self.get_schema_pattern(tier)
        
        # Support different patterns based on tier
        if tier == "enterprise":
            # Enterprise clients get dedicated databases
            return f"enterprise_{tenant_slug}"
        elif tier == "premium": 
            # Premium clients get separate schemas in shared DB
            return f"premium_{tenant_slug}"
        else:
            # Standard clients use basic pattern
            return f"tenant_{tenant_slug}"
    
    async def get_schema_limits(self, tenant_tier: str) -> Dict[str, int]:
        """Get schema resource limits based on tier."""
        limits_key = f"schema_limits.{tenant_tier}"
        return await self._config.get(limits_key, {
            "max_tables": 100,
            "max_connections": 20,
            "storage_mb": 1000
        })

# Usage in schema resolver
class ConfigurableSchemaResolver:
    def __init__(self, schema_config: DynamicSchemaConfiguration):
        self._schema_config = schema_config
    
    async def resolve_schema(
        self, 
        context: RequestContext,
        tenant_slug: str
    ) -> str:
        """Resolve schema with dynamic configuration."""
        if not context.tenant_id:
            return "admin"
        
        return await self._schema_config.resolve_tenant_schema(
            context.tenant_id,
            tenant_slug, 
            context
        )
```

## Best Practices

### 1. Configuration Hierarchy

Always implement configuration with proper fallback hierarchy:

1. **Context-specific** (highest priority)
2. **Tenant-specific** 
3. **Environment-specific**
4. **Global defaults** (lowest priority)

```python
async def get_setting(self, key: str, context: RequestContext) -> Any:
    # 1. Check context metadata
    if context.has_request_metadata(key):
        return context.get_request_metadata(key)
    
    # 2. Check tenant configuration
    if context.tenant_id:
        tenant_value = await self.get_tenant_setting(context.tenant_id.value, key)
        if tenant_value is not None:
            return tenant_value
    
    # 3. Check environment configuration
    env_value = await self.get_environment_setting(key)
    if env_value is not None:
        return env_value
    
    # 4. Return global default
    return await self.get_global_setting(key)
```

### 2. Configuration Caching

Implement intelligent caching to avoid repeated configuration lookups:

```python
from functools import lru_cache
from typing import Optional
import asyncio

class CachedConfigurationProvider:
    def __init__(self, config: ConfigurationProtocol):
        self._config = config
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def get_cached(self, key: str, ttl: Optional[int] = None) -> Any:
        """Get configuration value with caching."""
        cache_key = f"config:{key}"
        
        # Check cache
        if cache_key in self._cache:
            value, timestamp = self._cache[cache_key]
            if time.time() - timestamp < (ttl or self._cache_ttl):
                return value
        
        # Fetch from source
        value = await self._config.get(key)
        self._cache[cache_key] = (value, time.time())
        
        return value
    
    async def invalidate_cache(self, key_pattern: str = None) -> None:
        """Invalidate cached configuration values."""
        if key_pattern:
            keys_to_remove = [k for k in self._cache.keys() if key_pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()
```

### 3. Configuration Validation

Always validate configuration values to prevent runtime errors:

```python
from pydantic import BaseModel, Field
from typing import Literal

class DatabasePoolConfig(BaseModel):
    min_size: int = Field(ge=1, le=50, default=5)
    max_size: int = Field(ge=1, le=200, default=20)
    timeout_seconds: int = Field(ge=5, le=300, default=30)
    ssl_mode: Literal["disable", "allow", "prefer", "require"] = "require"
    
    def validate_pool_sizing(self):
        if self.min_size > self.max_size:
            raise ValueError("min_size cannot be greater than max_size")
        return self

class ValidatedConfigurationProvider:
    def __init__(self, config: ConfigurationProtocol):
        self._config = config
    
    async def get_database_pool_config(
        self, 
        connection_name: str
    ) -> DatabasePoolConfig:
        """Get validated database pool configuration."""
        raw_config = await self._config.get_section(f"database.pools.{connection_name}")
        
        # Validate and return typed configuration
        return DatabasePoolConfig(**raw_config).validate_pool_sizing()
```

### 4. Configuration Hot Reload

Support runtime configuration updates without service restart:

```python
import asyncio
from typing import Callable, Dict, Any

class HotReloadableConfig:
    def __init__(self, config: ConfigurationProtocol):
        self._config = config
        self._watchers: Dict[str, List[Callable]] = {}
        self._reload_task = None
    
    def watch_configuration(self, key: str, callback: Callable[[Any], None]) -> None:
        """Register callback for configuration changes."""
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)
    
    async def start_watching(self, poll_interval: int = 30) -> None:
        """Start watching for configuration changes."""
        self._reload_task = asyncio.create_task(
            self._poll_for_changes(poll_interval)
        )
    
    async def _poll_for_changes(self, interval: int) -> None:
        """Poll for configuration changes and notify watchers."""
        last_values = {}
        
        while True:
            try:
                for key in self._watchers.keys():
                    current_value = await self._config.get(key)
                    
                    if key not in last_values or last_values[key] != current_value:
                        # Configuration changed, notify watchers
                        for callback in self._watchers[key]:
                            try:
                                await callback(current_value)
                            except Exception as e:
                                logger.error(f"Configuration watcher error for {key}: {e}")
                        
                        last_values[key] = current_value
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Configuration polling error: {e}")
                await asyncio.sleep(interval)

# Usage example
config_manager = HotReloadableConfig(config_provider)

# Watch for database pool size changes
async def update_pool_size(new_size: int):
    logger.info(f"Updating database pool size to {new_size}")
    await database_service.update_pool_configuration({"max_size": new_size})

config_manager.watch_configuration("database.pool_max_size", update_pool_size)
await config_manager.start_watching()
```

## Integration with Features

### Database Feature Integration

```python
# Configure database connections dynamically
from neo_commons.features.database.services import DatabaseService

class ConfigurableDatabaseService(DatabaseService):
    def __init__(self, config: ConfigurationProtocol):
        self._config = config
        super().__init__(
            connection_manager=self._create_configured_manager(),
            schema_resolver=self._create_configured_schema_resolver()
        )
    
    async def _create_configured_manager(self) -> ConnectionManager:
        # Load dynamic connection configurations
        db_configs = await self._config.get_section("database.connections")
        return ConnectionManager(configs=db_configs)
```

### Auth Feature Integration

```python
# Configure authentication dynamically
from neo_commons.features.auth.services import AuthService

class ConfigurableAuthService(AuthService):
    async def get_keycloak_config(self, context: RequestContext) -> KeycloakConfig:
        # Select realm based on tenant tier
        tier = context.get_request_metadata("tenant_tier", "standard")
        realm_config_key = f"auth.realms.{tier}"
        
        realm_config = await self._config.get_section(realm_config_key)
        return KeycloakConfig(**realm_config)
```

## Summary

The neo-commons core dynamic configuration system provides:

1. **Hierarchical Configuration**: Context → Tenant → Environment → Global
2. **Runtime Flexibility**: Feature flags, metadata, tenant features
3. **Performance Optimization**: Caching, lazy loading, hot reload
4. **Type Safety**: Pydantic validation, typed configuration models
5. **Feature Integration**: Seamless integration with feature modules

Use these patterns to build flexible, maintainable, and performant configuration systems that adapt to your application's runtime needs while maintaining clean architectural boundaries.