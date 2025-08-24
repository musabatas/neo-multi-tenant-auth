"""Database query constants to eliminate duplicate queries."""

from typing import Dict

# Basic health check queries
BASIC_HEALTH_CHECK = "SELECT 1"

# Schema existence checks
SCHEMA_EXISTENCE_CHECK = "SELECT 1 FROM information_schema.schemata WHERE schema_name = $1"
LIST_ALL_SCHEMAS = "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('information_schema', 'pg_catalog')"

# Connection and activity monitoring
DATABASE_ACTIVITY_STATS = """
    SELECT 
        (SELECT count(*) FROM pg_stat_activity) as active_connections,
        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
        current_database() as database_name,
        version() as database_version
"""

DATABASE_DETAILED_ACTIVITY = """
    SELECT 
        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') as active_queries,
        (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle in transaction') as idle_in_transaction,
        (SELECT count(*) FROM pg_stat_activity WHERE state = 'idle') as idle_connections,
        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max_connections,
        current_database() as database_name
"""

# Database size and statistics
DATABASE_SIZE_STATS = """
    SELECT 
        pg_size_pretty(pg_database_size(current_database())) as database_size,
        (SELECT sum(pg_total_relation_size(c.oid)) FROM pg_class c, pg_namespace n 
         WHERE c.relnamespace = n.oid AND n.nspname NOT IN ('information_schema', 'pg_catalog')) as user_data_size,
        current_database() as database_name
"""

# Lock monitoring
DATABASE_LOCKS_CHECK = """
    SELECT 
        mode,
        count(*) as lock_count
    FROM pg_locks 
    WHERE NOT granted 
    GROUP BY mode
"""

# Performance monitoring
DATABASE_PERFORMANCE_STATS = """
    SELECT 
        numbackends as active_connections,
        xact_commit as transactions_committed,
        xact_rollback as transactions_rolled_back,
        blks_read as blocks_read,
        blks_hit as blocks_hit,
        tup_returned as tuples_returned,
        tup_fetched as tuples_fetched,
        tup_inserted as tuples_inserted,
        tup_updated as tuples_updated,
        tup_deleted as tuples_deleted
    FROM pg_stat_database 
    WHERE datname = current_database()
"""

# Replication status (for replicated databases)
REPLICATION_STATUS_CHECK = """
    SELECT 
        client_addr,
        state,
        sync_state,
        pg_wal_lsn_diff(pg_current_wal_lsn(), flush_lsn) as flush_lag_bytes,
        pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) as replay_lag_bytes
    FROM pg_stat_replication
"""

# Query templates for tenant operations
TENANT_SCHEMA_EXISTS = "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)"
TENANT_SCHEMA_LIST = """
    SELECT schema_name 
    FROM information_schema.schemata 
    WHERE schema_name ~ '^tenant_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
    ORDER BY schema_name
"""

# Connection registry queries (without connection_options field for compatibility)
CONNECTION_REGISTRY_LOAD = """
    SELECT 
        id, connection_name, connection_type, region_id,
        host, port, database_name, username, encrypted_password,
        ssl_mode, is_active, is_healthy,
        pool_min_size, pool_max_size, pool_timeout_seconds,
        pool_recycle_seconds, pool_pre_ping, created_at, updated_at
    FROM admin.database_connections 
    WHERE is_active = true AND deleted_at IS NULL
    ORDER BY connection_name
"""

CONNECTION_REGISTRY_BY_NAME = """
    SELECT 
        id, connection_name, connection_type, region_id,
        host, port, database_name, username, encrypted_password,
        ssl_mode, is_active, is_healthy,
        pool_min_size, pool_max_size, pool_timeout_seconds,
        pool_recycle_seconds, pool_pre_ping, created_at, updated_at
    FROM admin.database_connections 
    WHERE connection_name = $1 AND is_active = true AND deleted_at IS NULL
"""

# Load all connections except admin (common pattern)
CONNECTION_REGISTRY_LOAD_NON_ADMIN = """
    SELECT 
        id, connection_name, connection_type, region_id,
        host, port, database_name, username, encrypted_password,
        ssl_mode, is_active, is_healthy,
        pool_min_size, pool_max_size, pool_timeout_seconds,
        pool_recycle_seconds, pool_pre_ping, created_at, updated_at
    FROM admin.database_connections 
    WHERE is_active = true AND deleted_at IS NULL AND connection_name != 'admin'
    ORDER BY connection_name
"""

# Extended connection registry queries (with connection_options field for future use)
CONNECTION_REGISTRY_LOAD_EXTENDED = """
    SELECT 
        id, connection_name, connection_type, region_id,
        host, port, database_name, username, encrypted_password,
        ssl_mode, connection_options, is_active, is_healthy,
        pool_min_size, pool_max_size, pool_timeout_seconds,
        pool_recycle_seconds, pool_pre_ping, created_at, updated_at
    FROM admin.database_connections 
    WHERE is_active = true AND deleted_at IS NULL
    ORDER BY connection_name
"""

CONNECTION_REGISTRY_BY_NAME_EXTENDED = """
    SELECT 
        id, connection_name, connection_type, region_id,
        host, port, database_name, username, encrypted_password,
        ssl_mode, connection_options, is_active, is_healthy,
        pool_min_size, pool_max_size, pool_timeout_seconds,
        pool_recycle_seconds, pool_pre_ping, created_at, updated_at
    FROM admin.database_connections 
    WHERE connection_name = $1 AND is_active = true AND deleted_at IS NULL
"""

# Health check query sets by type
HEALTH_CHECK_QUERIES: Dict[str, Dict[str, str]] = {
    "basic": {
        "connectivity": BASIC_HEALTH_CHECK,
        "description": "Basic connectivity test"
    },
    "standard": {
        "connectivity": BASIC_HEALTH_CHECK,
        "activity": DATABASE_ACTIVITY_STATS,
        "description": "Standard health check with activity monitoring"
    },
    "comprehensive": {
        "connectivity": BASIC_HEALTH_CHECK,
        "activity": DATABASE_DETAILED_ACTIVITY,
        "performance": DATABASE_PERFORMANCE_STATS,
        "locks": DATABASE_LOCKS_CHECK,
        "description": "Comprehensive health check with full monitoring"
    },
    "minimal": {
        "ping": BASIC_HEALTH_CHECK,
        "description": "Minimal ping test"
    }
}