"""
Repository for database connection operations.
"""

from typing import List, Optional, Dict, Any
from datetime import timedelta
from src.common.utils.datetime import utc_now
import logging

from src.common.database.connection import get_database
from src.common.database.utils import process_database_record
from ..models.domain import DatabaseConnection

logger = logging.getLogger(__name__)


class DatabaseConnectionRepository:
    """Repository for managing database connections."""
    
    def __init__(self):
        self.db = get_database()
    
    async def list_connections(
        self,
        page: int = 1,
        page_size: int = 20,
        region_id: Optional[str] = None,
        connection_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_healthy: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        search: Optional[str] = None
    ) -> tuple[List[DatabaseConnection], int]:
        """
        List database connections with pagination and filtering.
        
        Returns:
            Tuple of (connections list, total count)
        """
        # Build WHERE clause
        where_conditions = ["dc.deleted_at IS NULL"]
        params = []
        param_count = 0
        
        if region_id:
            param_count += 1
            where_conditions.append(f"dc.region_id = ${param_count}")
            params.append(region_id)
        
        if connection_type:
            param_count += 1
            where_conditions.append(f"dc.connection_type = ${param_count}")
            params.append(connection_type)
        
        if is_active is not None:
            param_count += 1
            where_conditions.append(f"dc.is_active = ${param_count}")
            params.append(is_active)
        
        if is_healthy is not None:
            param_count += 1
            where_conditions.append(f"dc.is_healthy = ${param_count}")
            params.append(is_healthy)
        
        if tags:
            param_count += 1
            where_conditions.append(f"dc.tags && ${param_count}")
            params.append(tags)
        
        if search:
            param_count += 1
            where_conditions.append(
                f"(dc.connection_name ILIKE ${param_count} OR dc.database_name ILIKE ${param_count})"
            )
            params.append(f"%{search}%")
        
        where_clause = " AND ".join(where_conditions)
        
        # Count query
        count_query = f"""
            SELECT COUNT(*) as total
            FROM admin.database_connections dc
            WHERE {where_clause}
        """
        
        # Data query with pagination
        offset = (page - 1) * page_size
        param_count += 1
        limit_param = param_count
        param_count += 1
        offset_param = param_count
        
        data_query = f"""
            SELECT 
                dc.*,
                r.name as region_name,
                r.display_name as region_display_name,
                r.is_active as region_active
            FROM admin.database_connections dc
            JOIN admin.regions r ON dc.region_id = r.id
            WHERE {where_clause}
            ORDER BY dc.created_at DESC
            LIMIT ${limit_param} OFFSET ${offset_param}
        """
        
        # Execute queries
        count_result = await self.db.fetchrow(count_query, *params)
        total_count = count_result['total']
        
        params.extend([page_size, offset])
        rows = await self.db.fetch(data_query, *params)
        
        # Convert to domain models with proper type conversion
        connections = []
        for row in rows:
            data = process_database_record(
                dict(row),
                uuid_fields=['id', 'region_id'],
                jsonb_fields=['metadata']
            )
            connections.append(DatabaseConnection(**data))
        
        return connections, total_count
    
    async def get_connection(self, connection_id: str) -> Optional[DatabaseConnection]:
        """Get a single database connection by ID."""
        query = """
            SELECT 
                dc.*,
                r.name as region_name,
                r.display_name as region_display_name,
                r.is_active as region_active
            FROM admin.database_connections dc
            JOIN admin.regions r ON dc.region_id = r.id
            WHERE dc.id = $1 AND dc.deleted_at IS NULL
        """
        
        row = await self.db.fetchrow(query, connection_id)
        if row:
            data = process_database_record(
                dict(row),
                uuid_fields=['id', 'region_id'],
                jsonb_fields=['metadata']
            )
            return DatabaseConnection(**data)
        return None
    
    async def update_health_status(
        self,
        connection_id: str,
        is_healthy: bool,
        response_time_ms: Optional[float] = None
    ) -> bool:
        """Update health status of a database connection with history tracking."""
        # For now, use simpler approach without history tracking in metadata
        # TODO: Implement separate health_check_history table for better tracking
        if response_time_ms is not None:
            query = """
                UPDATE admin.database_connections
                SET 
                    is_healthy = $2,
                    last_health_check = NOW(),
                    consecutive_failures = CASE 
                        WHEN $2 = true THEN 0
                        ELSE consecutive_failures + 1
                    END,
                    metadata = jsonb_set(COALESCE(metadata, '{}'::jsonb), '{last_response_time_ms}', to_jsonb($3::float)),
                    updated_at = NOW()
                WHERE id = $1::uuid AND deleted_at IS NULL
                RETURNING id
            """
            result = await self.db.fetchrow(query, connection_id, is_healthy, response_time_ms)
        else:
            query = """
                UPDATE admin.database_connections
                SET 
                    is_healthy = $2,
                    last_health_check = NOW(),
                    consecutive_failures = CASE 
                        WHEN $2 = true THEN 0
                        ELSE consecutive_failures + 1
                    END,
                    updated_at = NOW()
                WHERE id = $1::uuid AND deleted_at IS NULL
                RETURNING id
            """
            result = await self.db.fetchrow(query, connection_id, is_healthy)
        
        return result is not None
    
    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics for all database connections."""
        # Main statistics query
        stats_query = """
            SELECT 
                COUNT(*) as total_databases,
                COUNT(*) FILTER (WHERE is_active = true) as active_databases,
                COUNT(*) FILTER (WHERE is_healthy = true AND is_active = true) as healthy_databases,
                COUNT(*) FILTER (
                    WHERE is_active = true 
                    AND is_healthy = true 
                    AND consecutive_failures > 0
                ) as degraded_databases,
                COUNT(*) FILTER (WHERE is_healthy = false AND is_active = true) as unhealthy_databases
            FROM admin.database_connections
            WHERE deleted_at IS NULL
        """
        
        result = await self.db.fetchrow(stats_query)
        
        # Separate queries for aggregations
        type_query = """
            SELECT connection_type, COUNT(*) as count
            FROM admin.database_connections
            WHERE deleted_at IS NULL
            GROUP BY connection_type
        """
        
        region_query = """
            SELECT r.name, COUNT(*) as count
            FROM admin.database_connections dc
            JOIN admin.regions r ON dc.region_id = r.id
            WHERE dc.deleted_at IS NULL
            GROUP BY r.name
        """
        
        type_results = await self.db.fetch(type_query)
        region_results = await self.db.fetch(region_query)
        
        by_type = {row['connection_type']: row['count'] for row in type_results}
        by_region = {row['name']: row['count'] for row in region_results}
        
        # Calculate overall health score
        total = result['total_databases'] or 1
        healthy = result['healthy_databases'] or 0
        degraded = result['degraded_databases'] or 0
        
        health_score = (
            (healthy * 100) +
            (degraded * 50)
        ) / total if total > 0 else 0
        
        return {
            'total_databases': result['total_databases'] or 0,
            'active_databases': result['active_databases'] or 0,
            'healthy_databases': result['healthy_databases'] or 0,
            'degraded_databases': result['degraded_databases'] or 0,
            'unhealthy_databases': result['unhealthy_databases'] or 0,
            'by_type': by_type,
            'by_region': by_region,
            'overall_health_score': round(health_score, 2)
        }
    
    async def get_connections_for_health_check(
        self,
        connection_ids: Optional[List[str]] = None,
        force_check: bool = False
    ) -> List[DatabaseConnection]:
        """Get connections that need health check."""
        if connection_ids:
            # Get specific connections
            query = """
                SELECT 
                    dc.*,
                    r.name as region_name,
                    r.display_name as region_display_name,
                    r.is_active as region_active
                FROM admin.database_connections dc
                JOIN admin.regions r ON dc.region_id = r.id
                WHERE dc.id = ANY($1) 
                    AND dc.deleted_at IS NULL
                    AND dc.is_active = true
            """
            rows = await self.db.fetch(query, connection_ids)
        else:
            # Get all active connections that need checking
            check_interval = timedelta(minutes=5)  # Check every 5 minutes
            
            if force_check:
                query = """
                    SELECT 
                        dc.*,
                        r.name as region_name,
                        r.display_name as region_display_name,
                        r.is_active as region_active
                    FROM admin.database_connections dc
                    JOIN admin.regions r ON dc.region_id = r.id
                    WHERE dc.deleted_at IS NULL AND dc.is_active = true
                    ORDER BY dc.last_health_check ASC NULLS FIRST
                """
                rows = await self.db.fetch(query)
            else:
                query = """
                    SELECT 
                        dc.*,
                        r.name as region_name,
                        r.display_name as region_display_name,
                        r.is_active as region_active
                    FROM admin.database_connections dc
                    JOIN admin.regions r ON dc.region_id = r.id
                    WHERE dc.deleted_at IS NULL 
                        AND dc.is_active = true 
                        AND (
                            dc.last_health_check IS NULL 
                            OR dc.last_health_check < $1
                        )
                    ORDER BY dc.last_health_check ASC NULLS FIRST
                """
                cutoff_time = utc_now() - check_interval
                rows = await self.db.fetch(query, cutoff_time)
        
        # Convert to domain models with proper type conversion
        connections = []
        for row in rows:
            data = process_database_record(
                dict(row),
                uuid_fields=['id', 'region_id'],
                jsonb_fields=['metadata']
            )
            connections.append(DatabaseConnection(**data))
        return connections