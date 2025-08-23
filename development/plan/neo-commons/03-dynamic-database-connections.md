# Dynamic Database Connection Management

## Overview

Neo-Commons implements a centralized, dynamic database connection management system that enables:
- Real-time connection configuration updates without service restarts
- Multi-region database support with automatic failover
- Connection pooling with health monitoring
- Tenant-to-database routing based on region and deployment type

## Core Architecture

### 1. Central Connection Registry

All database connections are managed centrally in the `admin.database_connections` table:

```sql
CREATE TABLE admin.database_connections (
    id UUID PRIMARY KEY DEFAULT platform_common.uuid_generate_v7(),
    region_id UUID NOT NULL REFERENCES admin.regions,
    connection_name VARCHAR(100) NOT NULL UNIQUE,
    connection_type admin.connection_type NOT NULL,  -- 'admin', 'shared', 'analytics', 'tenant'
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 5432,
    database_name VARCHAR(63) NOT NULL,
    ssl_mode VARCHAR(20) DEFAULT 'require',
    username VARCHAR(255) DEFAULT 'postgres' NOT NULL,
    encrypted_password VARCHAR(256),
    
    -- Pool Configuration
    pool_min_size INTEGER DEFAULT 5,
    pool_max_size INTEGER DEFAULT 20,
    pool_timeout_seconds INTEGER DEFAULT 30,
    pool_recycle_seconds INTEGER DEFAULT 3600,
    pool_pre_ping BOOLEAN DEFAULT true,
    
    -- Health Monitoring
    is_active BOOLEAN DEFAULT true,
    is_healthy BOOLEAN DEFAULT true,
    last_health_check TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    max_consecutive_failures INTEGER DEFAULT 3,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);
```

### 2. Connection Types

```sql
-- From admin schema types
CREATE TYPE admin.connection_type AS ENUM (
    'admin',      -- Admin database (single, global)
    'shared',     -- Regional shared databases for tenant schemas
    'analytics',  -- Regional analytics databases
    'tenant'      -- Dedicated tenant databases (for enterprise clients)
);
```

### 3. Region Configuration

```sql
-- From admin.regions table
CREATE TABLE admin.regions (
    id UUID PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,        -- 'us-east', 'eu-west', etc.
    name VARCHAR(100) NOT NULL,
    primary_endpoint VARCHAR(255) NOT NULL,
    backup_endpoints TEXT[],
    gdpr_region BOOLEAN DEFAULT false,
    accepts_new_tenants BOOLEAN DEFAULT true,
    capacity_percentage SMALLINT DEFAULT 0
);
```

## Connection Manager Implementation

### Core Connection Manager

```python
from asyncpg import create_pool, Pool
from typing import Dict, Optional
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ConnectionConfig:
    """Database connection configuration"""
    id: str
    region_id: str
    connection_name: str
    connection_type: str
    host: str
    port: int
    database_name: str
    username: str
    encrypted_password: str
    ssl_mode: str
    pool_config: PoolConfig
    is_active: bool
    is_healthy: bool
    metadata: dict

@dataclass
class PoolConfig:
    """Connection pool configuration"""
    min_size: int = 5
    max_size: int = 20
    timeout: int = 30
    recycle: int = 3600
    pre_ping: bool = True

class DynamicConnectionManager:
    """Manages database connections dynamically from central registry"""
    
    def __init__(self, admin_db_url: str, encryption_key: str):
        self._admin_db_url = admin_db_url
        self._encryption_key = encryption_key
        self._admin_pool: Optional[Pool] = None
        self._connection_pools: Dict[str, Pool] = {}
        self._connection_configs: Dict[str, ConnectionConfig] = {}
        self._last_config_refresh = datetime.min
        self._config_refresh_interval = timedelta(minutes=5)
        self._health_check_task: Optional[asyncio.Task] = None
    
    async def initialize(self):
        """Initialize connection manager"""
        # Create admin pool first (bootstrap connection)
        self._admin_pool = await create_pool(
            self._admin_db_url,
            min_size=2,
            max_size=10,
            command_timeout=60
        )
        
        # Load all connection configurations
        await self._load_configurations()
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor_loop())
        
        # Start configuration watcher
        asyncio.create_task(self._config_watcher_loop())
    
    async def _load_configurations(self):
        """Load all connection configurations from admin database"""
        query = """
        SELECT 
            dc.*, 
            r.code as region_code,
            pgp_sym_decrypt(dc.encrypted_password::bytea, $1) as decrypted_password
        FROM admin.database_connections dc
        JOIN admin.regions r ON dc.region_id = r.id
        WHERE dc.is_active = true AND dc.deleted_at IS NULL
        ORDER BY dc.connection_name
        """
        
        async with self._admin_pool.acquire() as conn:
            rows = await conn.fetch(query, self._encryption_key)
            
            for row in rows:
                config = self._create_connection_config(row)
                self._connection_configs[config.connection_name] = config
        
        self._last_config_refresh = datetime.now()
    
    async def get_connection_for_tenant(self, tenant_id: str) -> Pool:
        """Get appropriate connection pool for a tenant"""
        # First, get tenant configuration
        tenant_info = await self._get_tenant_info(tenant_id)
        
        if tenant_info['deployment_type'] == 'dedicated':
            # Enterprise tenant with dedicated database
            connection_name = f"tenant_{tenant_info['slug']}"
        else:
            # Standard tenant using shared regional database
            connection_name = f"shared_{tenant_info['region_code']}"
        
        return await self.get_connection(connection_name)
    
    async def get_connection(self, connection_name: str) -> Pool:
        """Get or create connection pool by name"""
        # Check if configurations need refresh
        if datetime.now() - self._last_config_refresh > self._config_refresh_interval:
            await self._load_configurations()
        
        # Get connection configuration
        if connection_name not in self._connection_configs:
            raise ConnectionNotFoundError(f"Connection {connection_name} not found")
        
        config = self._connection_configs[connection_name]
        
        # Check health status
        if not config.is_healthy:
            # Try to find a backup connection
            backup = await self._find_backup_connection(config)
            if backup:
                config = backup
            else:
                raise ConnectionUnhealthyError(f"Connection {connection_name} is unhealthy")
        
        # Get or create pool
        if connection_name not in self._connection_pools:
            self._connection_pools[connection_name] = await self._create_pool(config)
        
        return self._connection_pools[connection_name]
    
    async def _create_pool(self, config: ConnectionConfig) -> Pool:
        """Create a new connection pool"""
        dsn = f"postgresql://{config.username}:{config.decrypted_password}@{config.host}:{config.port}/{config.database_name}"
        
        return await create_pool(
            dsn,
            min_size=config.pool_config.min_size,
            max_size=config.pool_config.max_size,
            command_timeout=config.pool_config.timeout,
            max_inactive_connection_lifetime=config.pool_config.recycle,
            ssl=config.ssl_mode if config.ssl_mode != 'disable' else None
        )
    
    async def _get_tenant_info(self, tenant_id: str) -> dict:
        """Get tenant configuration from admin database"""
        query = """
        SELECT 
            t.id, t.slug, t.schema_name, t.deployment_type,
            t.database_connection_id, t.region_id,
            r.code as region_code
        FROM admin.tenants t
        JOIN admin.regions r ON t.region_id = r.id
        WHERE t.id = $1 AND t.status = 'active'
        """
        
        async with self._admin_pool.acquire() as conn:
            row = await conn.fetchrow(query, tenant_id)
            if not row:
                raise TenantNotFoundError(f"Tenant {tenant_id} not found")
            return dict(row)
```

### Health Monitoring System

```python
class HealthMonitor:
    """Monitors connection health and updates registry"""
    
    def __init__(self, connection_manager: DynamicConnectionManager):
        self._manager = connection_manager
        self._check_interval = 30  # seconds
        self._health_timeout = 5   # seconds
    
    async def check_connection_health(self, config: ConnectionConfig) -> bool:
        """Check if a connection is healthy"""
        try:
            pool = self._manager._connection_pools.get(config.connection_name)
            if not pool:
                return True  # Not yet created, assume healthy
            
            async with asyncio.timeout(self._health_timeout):
                async with pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
            
            await self._update_health_status(config.id, True)
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed for {config.connection_name}: {e}")
            await self._update_health_status(config.id, False)
            return False
    
    async def _update_health_status(self, connection_id: str, is_healthy: bool):
        """Update health status in admin database"""
        if is_healthy:
            query = """
            UPDATE admin.database_connections
            SET is_healthy = true,
                consecutive_failures = 0,
                last_health_check = NOW()
            WHERE id = $1
            """
        else:
            query = """
            UPDATE admin.database_connections
            SET consecutive_failures = consecutive_failures + 1,
                is_healthy = CASE 
                    WHEN consecutive_failures + 1 >= max_consecutive_failures 
                    THEN false 
                    ELSE is_healthy 
                END,
                last_health_check = NOW()
            WHERE id = $1
            """
        
        async with self._manager._admin_pool.acquire() as conn:
            await conn.execute(query, connection_id)
```

### Failover Management

```python
class FailoverStrategy:
    """Handles connection failover scenarios"""
    
    async def find_backup_connection(self, 
                                    failed_config: ConnectionConfig,
                                    all_configs: Dict[str, ConnectionConfig]) -> Optional[ConnectionConfig]:
        """Find a backup connection for failed primary"""
        
        # Strategy 1: Same region, different host (replica)
        same_region_backup = self._find_same_region_backup(failed_config, all_configs)
        if same_region_backup:
            return same_region_backup
        
        # Strategy 2: Different region, same type (cross-region failover)
        if failed_config.metadata.get('allow_cross_region_failover'):
            cross_region_backup = self._find_cross_region_backup(failed_config, all_configs)
            if cross_region_backup:
                logger.warning(f"Using cross-region failover for {failed_config.connection_name}")
                return cross_region_backup
        
        return None
    
    def _find_same_region_backup(self, 
                                 failed_config: ConnectionConfig,
                                 all_configs: Dict[str, ConnectionConfig]) -> Optional[ConnectionConfig]:
        """Find backup in same region"""
        for config in all_configs.values():
            if (config.region_id == failed_config.region_id and
                config.connection_type == failed_config.connection_type and
                config.connection_name != failed_config.connection_name and
                config.is_healthy and
                config.metadata.get('is_replica')):
                return config
        return None
    
    def _find_cross_region_backup(self,
                                  failed_config: ConnectionConfig,
                                  all_configs: Dict[str, ConnectionConfig]) -> Optional[ConnectionConfig]:
        """Find backup in different region"""
        # Prefer geographically close regions
        preferred_regions = failed_config.metadata.get('failover_regions', [])
        
        for region in preferred_regions:
            for config in all_configs.values():
                if (config.metadata.get('region_code') == region and
                    config.connection_type == failed_config.connection_type and
                    config.is_healthy):
                    return config
        return None
```

## Usage Patterns

### FastAPI Integration

```python
from neo_commons.infrastructure.database import DynamicConnectionManager
from fastapi import Depends, Request

# Global connection manager instance
connection_manager = DynamicConnectionManager(
    admin_db_url=settings.ADMIN_DATABASE_URL,
    encryption_key=settings.DB_ENCRYPTION_KEY
)

async def get_db_connection(request: Request):
    """FastAPI dependency to get database connection for current context"""
    # Extract tenant_id from request (JWT token, header, etc.)
    tenant_id = extract_tenant_id(request)
    
    if tenant_id:
        # Get tenant-specific connection
        pool = await connection_manager.get_connection_for_tenant(tenant_id)
    else:
        # Admin context - use admin connection
        pool = await connection_manager.get_connection("admin-primary")
    
    async with pool.acquire() as conn:
        yield conn

# Usage in routes
@router.get("/users")
async def list_users(db: Connection = Depends(get_db_connection)):
    # Connection is automatically selected based on context
    users = await db.fetch("SELECT * FROM users")
    return users
```

### Repository Pattern Integration

```python
class DynamicRepository:
    """Base repository with dynamic connection management"""
    
    def __init__(self, connection_manager: DynamicConnectionManager):
        self._connection_manager = connection_manager
    
    async def _get_connection(self, context: RequestContext) -> Pool:
        """Get appropriate connection based on context"""
        if context.tenant_id:
            return await self._connection_manager.get_connection_for_tenant(context.tenant_id)
        else:
            return await self._connection_manager.get_connection("admin-primary")
    
    async def execute_query(self, query: str, context: RequestContext, *args):
        """Execute query with appropriate connection"""
        pool = await self._get_connection(context)
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)
```

## Connection Pool Optimization

### Pool Sizing Strategy

```python
def calculate_optimal_pool_size(config: ConnectionConfig) -> PoolConfig:
    """Calculate optimal pool size based on usage patterns"""
    base_config = PoolConfig()
    
    # Adjust based on connection type
    if config.connection_type == 'admin':
        # Admin connections need smaller pools
        base_config.min_size = 2
        base_config.max_size = 20
    elif config.connection_type == 'shared':
        # Shared databases need larger pools
        base_config.min_size = 10
        base_config.max_size = 50
    elif config.connection_type == 'tenant':
        # Dedicated tenant databases
        base_config.min_size = 5
        base_config.max_size = 20
    
    # Adjust based on region capacity
    if config.metadata.get('region_capacity_percentage', 0) > 80:
        # High capacity region needs more connections
        base_config.max_size = int(base_config.max_size * 1.5)
    
    return base_config
```

### Connection Recycling

```python
class ConnectionRecycler:
    """Manages connection lifecycle and recycling"""
    
    async def recycle_idle_connections(self, pool: Pool, idle_time: int = 300):
        """Recycle connections idle for more than specified time"""
        # This is typically handled by asyncpg's max_inactive_connection_lifetime
        # But we can add custom logic if needed
        pass
    
    async def warm_pool(self, pool: Pool, target_size: int = None):
        """Pre-create connections to warm the pool"""
        target_size = target_size or pool._minsize
        
        tasks = []
        for _ in range(target_size):
            tasks.append(pool.acquire())
        
        # Acquire connections to force creation
        connections = await asyncio.gather(*tasks)
        
        # Immediately release them back to pool
        for conn in connections:
            await pool.release(conn)
```

## Security Considerations

### Password Encryption

```python
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class PasswordEncryption:
    """Handles password encryption for database connections"""
    
    @staticmethod
    def derive_key(master_key: str, salt: bytes) -> bytes:
        """Derive encryption key from master key"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
    
    @staticmethod
    def encrypt_password(password: str, master_key: str) -> str:
        """Encrypt database password"""
        salt = os.urandom(16)
        key = PasswordEncryption.derive_key(master_key, salt)
        f = Fernet(key)
        encrypted = f.encrypt(password.encode())
        # Store salt with encrypted password
        return base64.b64encode(salt + encrypted).decode()
    
    @staticmethod
    def decrypt_password(encrypted: str, master_key: str) -> str:
        """Decrypt database password"""
        data = base64.b64decode(encrypted)
        salt = data[:16]
        encrypted_password = data[16:]
        key = PasswordEncryption.derive_key(master_key, salt)
        f = Fernet(key)
        return f.decrypt(encrypted_password).decode()
```

### Connection Security

```yaml
SSL Configuration:
  - Always use SSL/TLS for database connections
  - Verify server certificates in production
  - Use connection-level encryption for sensitive data

Access Control:
  - Implement IP allowlisting for database servers
  - Use IAM-based authentication where possible
  - Rotate credentials regularly

Audit Logging:
  - Log all connection attempts
  - Track connection pool metrics
  - Monitor for unusual connection patterns
```

## Monitoring and Metrics

### Key Metrics to Track

```python
class ConnectionMetrics:
    """Tracks connection pool metrics"""
    
    def __init__(self):
        self.metrics = {
            'pool_size': Gauge('db_pool_size', 'Current pool size'),
            'active_connections': Gauge('db_active_connections', 'Active connections'),
            'waiting_requests': Gauge('db_waiting_requests', 'Requests waiting for connection'),
            'connection_errors': Counter('db_connection_errors', 'Connection errors'),
            'health_check_failures': Counter('db_health_check_failures', 'Health check failures'),
            'failover_events': Counter('db_failover_events', 'Failover events triggered'),
        }
    
    async def record_pool_stats(self, pool_name: str, pool: Pool):
        """Record pool statistics"""
        stats = pool.get_stats()
        self.metrics['pool_size'].labels(pool=pool_name).set(stats['size'])
        self.metrics['active_connections'].labels(pool=pool_name).set(stats['used'])
        self.metrics['waiting_requests'].labels(pool=pool_name).set(stats['waiting'])
```

## Performance Targets

| Metric | Target | Description |
|--------|--------|-------------|
| Connection Establishment | < 50ms | Time to establish new connection |
| Pool Acquisition | < 5ms | Time to get connection from pool |
| Health Check | < 5s | Maximum time for health check |
| Failover Time | < 10s | Time to detect and failover |
| Configuration Refresh | < 100ms | Time to reload configurations |
| Encryption/Decryption | < 10ms | Password encryption overhead |

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
- [ ] Implement `DynamicConnectionManager` class
- [ ] Create connection pool management
- [ ] Add basic health checking

### Phase 2: Advanced Features (Week 2)
- [ ] Implement failover strategies
- [ ] Add connection recycling
- [ ] Create monitoring and metrics

### Phase 3: Security & Optimization (Week 3)
- [ ] Implement password encryption
- [ ] Add SSL/TLS configuration
- [ ] Optimize pool sizing algorithms

### Phase 4: Integration (Week 4)
- [ ] FastAPI dependency injection
- [ ] Repository pattern integration
- [ ] Testing and validation

## Conclusion

This dynamic database connection management system provides:
- **Zero-downtime** configuration updates
- **Automatic failover** for high availability
- **Multi-region support** with intelligent routing
- **Security-first** approach with encryption
- **Performance optimization** through pooling and caching

The system seamlessly integrates with neo-commons to provide transparent database access across all services while maintaining isolation, security, and performance.