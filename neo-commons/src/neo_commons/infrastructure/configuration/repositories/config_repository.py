"""AsyncPG-based configuration repository implementation.

Concrete implementation of ConfigurationRepository protocol using AsyncPG
for high-performance configuration persistence with dynamic schema support.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
import json
import logging

from ....core.exceptions.database import DatabaseError
from ..entities import (
    ConfigKey, ConfigValue, ConfigScope, ConfigType, ConfigSource,
    ConfigurationRepository
)


logger = logging.getLogger(__name__)


class AsyncPGConfigurationRepository:
    """AsyncPG implementation of ConfigurationRepository protocol."""
    
    def __init__(self, connection_manager, schema: str = "admin"):
        """Initialize with connection manager and target schema."""
        self.connection_manager = connection_manager
        self.schema = schema
    
    async def _get_connection(self) -> asyncpg.Connection:
        """Get database connection for configuration schema."""
        return await self.connection_manager.get_connection(self.schema)
    
    def _build_config_from_row(self, row: asyncpg.Record) -> ConfigValue:
        """Build ConfigValue entity from database row."""
        return ConfigValue(
            key=ConfigKey(row['config_key'], ConfigScope(row['scope'])),
            value=self._deserialize_value(row['value'], ConfigType(row['config_type'])),
            config_type=ConfigType(row['config_type']),
            source=ConfigSource(row['source']),
            description=row['description'],
            is_sensitive=row['is_sensitive'],
            is_required=row['is_required'],
            default_value=self._deserialize_value(row['default_value'], ConfigType(row['config_type'])) if row['default_value'] else None,
            validation_pattern=row['validation_pattern'],
            allowed_values=json.loads(row['allowed_values']) if row['allowed_values'] else None,
            min_value=row['min_value'],
            max_value=row['max_value'],
            expires_at=row['expires_at'],
            metadata=row['metadata'] or {},
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            version=row['version']
        )
    
    def _serialize_value(self, value: Any, config_type: ConfigType) -> str:
        """Serialize configuration value for database storage."""
        if value is None:
            return None
        
        if config_type in (ConfigType.JSON, ConfigType.LIST):
            return json.dumps(value)
        elif config_type == ConfigType.BOOLEAN:
            return str(value).lower()
        else:
            return str(value)
    
    def _deserialize_value(self, value: str, config_type: ConfigType) -> Any:
        """Deserialize configuration value from database storage."""
        if value is None:
            return None
        
        try:
            if config_type == ConfigType.INTEGER:
                return int(value)
            elif config_type == ConfigType.FLOAT:
                return float(value)
            elif config_type == ConfigType.BOOLEAN:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif config_type in (ConfigType.JSON, ConfigType.LIST):
                return json.loads(value)
            else:
                return value
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to deserialize config value '{value}' as {config_type}: {e}")
            return value
    
    async def save_config(self, config: ConfigValue) -> ConfigValue:
        """Save a configuration value to persistent storage."""
        try:
            conn = await self._get_connection()
            
            # Check if config already exists
            existing_query = f"""
                SELECT version FROM {self.schema}.configurations
                WHERE config_key = $1 AND scope = $2
            """
            existing = await conn.fetchrow(existing_query, config.key.value, config.key.scope.value)
            
            if existing:
                # Update existing configuration
                query = f"""
                    UPDATE {self.schema}.configurations
                    SET value = $3,
                        config_type = $4,
                        source = $5,
                        description = $6,
                        is_sensitive = $7,
                        is_required = $8,
                        default_value = $9,
                        validation_pattern = $10,
                        allowed_values = $11,
                        min_value = $12,
                        max_value = $13,
                        expires_at = $14,
                        metadata = $15,
                        updated_at = NOW(),
                        version = version + 1
                    WHERE config_key = $1 AND scope = $2
                    RETURNING version, updated_at
                """
                
                row = await conn.fetchrow(
                    query,
                    config.key.value,
                    config.key.scope.value,
                    self._serialize_value(config.value, config.config_type),
                    config.config_type.value,
                    config.source.value,
                    config.description,
                    config.is_sensitive,
                    config.is_required,
                    self._serialize_value(config.default_value, config.config_type),
                    config.validation_pattern,
                    json.dumps(config.allowed_values) if config.allowed_values else None,
                    config.min_value,
                    config.max_value,
                    config.expires_at,
                    config.metadata
                )
                
                # Return updated config with new version and timestamp
                return ConfigValue(
                    key=config.key,
                    value=config.value,
                    config_type=config.config_type,
                    source=config.source,
                    description=config.description,
                    is_sensitive=config.is_sensitive,
                    is_required=config.is_required,
                    default_value=config.default_value,
                    validation_pattern=config.validation_pattern,
                    allowed_values=config.allowed_values,
                    min_value=config.min_value,
                    max_value=config.max_value,
                    expires_at=config.expires_at,
                    metadata=config.metadata,
                    created_at=config.created_at,
                    updated_at=row['updated_at'],
                    version=row['version']
                )
            else:
                # Insert new configuration
                query = f"""
                    INSERT INTO {self.schema}.configurations (
                        config_key, scope, value, config_type, source, description,
                        is_sensitive, is_required, default_value, validation_pattern,
                        allowed_values, min_value, max_value, expires_at, metadata,
                        created_at, updated_at, version
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                        NOW(), NOW(), 1
                    )
                    RETURNING created_at, updated_at
                """
                
                row = await conn.fetchrow(
                    query,
                    config.key.value,
                    config.key.scope.value,
                    self._serialize_value(config.value, config.config_type),
                    config.config_type.value,
                    config.source.value,
                    config.description,
                    config.is_sensitive,
                    config.is_required,
                    self._serialize_value(config.default_value, config.config_type),
                    config.validation_pattern,
                    json.dumps(config.allowed_values) if config.allowed_values else None,
                    config.min_value,
                    config.max_value,
                    config.expires_at,
                    config.metadata
                )
                
                # Return created config with timestamps
                return ConfigValue(
                    key=config.key,
                    value=config.value,
                    config_type=config.config_type,
                    source=config.source,
                    description=config.description,
                    is_sensitive=config.is_sensitive,
                    is_required=config.is_required,
                    default_value=config.default_value,
                    validation_pattern=config.validation_pattern,
                    allowed_values=config.allowed_values,
                    min_value=config.min_value,
                    max_value=config.max_value,
                    expires_at=config.expires_at,
                    metadata=config.metadata,
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    version=1
                )
                
        except Exception as e:
            logger.error(f"Failed to save config {config.key}: {e}")
            raise DatabaseError(f"Failed to save configuration: {e}")
    
    async def load_config(self, key: ConfigKey) -> Optional[ConfigValue]:
        """Load a configuration value from persistent storage."""
        try:
            conn = await self._get_connection()
            
            query = f"""
                SELECT config_key, scope, value, config_type, source, description,
                       is_sensitive, is_required, default_value, validation_pattern,
                       allowed_values, min_value, max_value, expires_at, metadata,
                       created_at, updated_at, version
                FROM {self.schema}.configurations
                WHERE config_key = $1 AND scope = $2
                AND (expires_at IS NULL OR expires_at > NOW())
            """
            
            row = await conn.fetchrow(query, key.value, key.scope.value)
            return self._build_config_from_row(row) if row else None
            
        except Exception as e:
            logger.error(f"Failed to load config {key}: {e}")
            raise DatabaseError(f"Failed to load configuration: {e}")
    
    async def load_configs_by_scope(self, scope: ConfigScope) -> List[ConfigValue]:
        """Load all configuration values for a scope."""
        try:
            conn = await self._get_connection()
            
            query = f"""
                SELECT config_key, scope, value, config_type, source, description,
                       is_sensitive, is_required, default_value, validation_pattern,
                       allowed_values, min_value, max_value, expires_at, metadata,
                       created_at, updated_at, version
                FROM {self.schema}.configurations
                WHERE scope = $1
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY config_key
            """
            
            rows = await conn.fetch(query, scope.value)
            return [self._build_config_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to load configs for scope {scope}: {e}")
            raise DatabaseError(f"Failed to load configurations: {e}")
    
    async def load_configs_by_keys(self, keys: List[ConfigKey]) -> List[ConfigValue]:
        """Load multiple configuration values by keys."""
        if not keys:
            return []
        
        try:
            conn = await self._get_connection()
            
            # Build parameter lists
            key_values = [(key.value, key.scope.value) for key in keys]
            
            query = f"""
                SELECT config_key, scope, value, config_type, source, description,
                       is_sensitive, is_required, default_value, validation_pattern,
                       allowed_values, min_value, max_value, expires_at, metadata,
                       created_at, updated_at, version
                FROM {self.schema}.configurations
                WHERE (config_key, scope) = ANY($1)
                AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY config_key, scope
            """
            
            rows = await conn.fetch(query, key_values)
            return [self._build_config_from_row(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to load configs by keys: {e}")
            raise DatabaseError(f"Failed to load configurations: {e}")
    
    async def update_config(
        self,
        key: ConfigKey,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update a configuration value."""
        try:
            conn = await self._get_connection()
            
            # Get existing config to preserve type and other settings
            existing = await self.load_config(key)
            if not existing:
                return False
            
            # Update value and metadata
            update_metadata = existing.metadata.copy()
            if metadata:
                update_metadata.update(metadata)
            
            query = f"""
                UPDATE {self.schema}.configurations
                SET value = $3,
                    metadata = $4,
                    updated_at = NOW(),
                    version = version + 1
                WHERE config_key = $1 AND scope = $2
            """
            
            result = await conn.execute(
                query,
                key.value,
                key.scope.value,
                self._serialize_value(value, existing.config_type),
                update_metadata
            )
            
            return result.split()[-1] == "1"  # Check if one row was updated
            
        except Exception as e:
            logger.error(f"Failed to update config {key}: {e}")
            raise DatabaseError(f"Failed to update configuration: {e}")
    
    async def delete_config(self, key: ConfigKey) -> bool:
        """Delete a configuration value from persistent storage."""
        try:
            conn = await self._get_connection()
            
            query = f"""
                DELETE FROM {self.schema}.configurations
                WHERE config_key = $1 AND scope = $2
            """
            
            result = await conn.execute(query, key.value, key.scope.value)
            return result.split()[-1] == "1"  # Check if one row was deleted
            
        except Exception as e:
            logger.error(f"Failed to delete config {key}: {e}")
            raise DatabaseError(f"Failed to delete configuration: {e}")
    
    async def list_keys_by_pattern(
        self,
        pattern: str,
        scope: Optional[ConfigScope] = None
    ) -> List[ConfigKey]:
        """List configuration keys matching a pattern."""
        try:
            conn = await self._get_connection()
            
            conditions = ["config_key ILIKE $1"]
            params = [f"%{pattern}%"]
            
            if scope:
                conditions.append("scope = $2")
                params.append(scope.value)
            
            where_clause = " AND ".join(conditions)
            
            query = f"""
                SELECT DISTINCT config_key, scope
                FROM {self.schema}.configurations
                WHERE {where_clause}
                ORDER BY config_key, scope
            """
            
            rows = await conn.fetch(query, *params)
            return [ConfigKey(row['config_key'], ConfigScope(row['scope'])) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to list keys by pattern {pattern}: {e}")
            raise DatabaseError(f"Failed to list configuration keys: {e}")
    
    async def get_config_history(self, key: ConfigKey, limit: int = 10) -> List[ConfigValue]:
        """Get configuration value history."""
        try:
            conn = await self._get_connection()
            
            # This would require a separate history table in a full implementation
            # For now, just return the current version
            current = await self.load_config(key)
            return [current] if current else []
            
        except Exception as e:
            logger.error(f"Failed to get config history for {key}: {e}")
            return []
    
    async def cleanup_expired_configs(self) -> int:
        """Clean up expired configuration values."""
        try:
            conn = await self._get_connection()
            
            query = f"""
                DELETE FROM {self.schema}.configurations
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            """
            
            result = await conn.execute(query)
            count = int(result.split()[-1])
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired configurations")
            
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired configs: {e}")
            return 0