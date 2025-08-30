"""Enhanced database operation handler with neo-commons integration."""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import asyncpg

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult
from ....features.database.services.database_service import get_database_service

logger = logging.getLogger(__name__)


class EnhancedDatabaseHandler(ActionHandler):
    """
    Enhanced database operation handler using neo-commons database service.
    
    Configuration:
    - operation_type: Type of operation (query, execute, transaction, schema_operation, bulk_operation)
    - sql_query: SQL query or statement to execute (required)
    - query_params: Parameters for parameterized queries (optional)
    - connection_name: Database connection name (optional, defaults to schema-based routing)
    - transaction_isolation: Transaction isolation level (optional)
    - query_timeout: Query timeout in seconds (optional, default: 30)
    - batch_size: Batch size for bulk operations (optional, default: 1000)
    - return_format: Result format ('records', 'dict_list', 'json', 'count_only')
    - dry_run: If true, validate but don't execute (default: False)
    """
    
    @property
    def handler_name(self) -> str:
        return "enhanced_database_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["database_operation", "database_query", "database_transaction", "schema_operation"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate enhanced database handler configuration."""
        if "operation_type" not in config:
            raise ValueError("Missing required database config field: operation_type")
        
        if "sql_query" not in config:
            raise ValueError("Missing required database config field: sql_query")
        
        operation_type = config["operation_type"]
        valid_operations = ["query", "execute", "transaction", "schema_operation", "bulk_operation"]
        if operation_type not in valid_operations:
            raise ValueError(f"Invalid operation_type: {operation_type}. Must be one of: {', '.join(valid_operations)}")
        
        # Validate SQL query structure
        sql_query = config["sql_query"].strip()
        if not sql_query:
            raise ValueError("sql_query cannot be empty")
        
        # Enhanced security validation
        if operation_type == "schema_operation":
            # Allow schema operations but log them for security monitoring
            dangerous_patterns = ["drop database", "drop user", "create user", "grant all"]
            sql_lower = sql_query.lower()
            for pattern in dangerous_patterns:
                if pattern in sql_lower:
                    logger.warning(f"Potentially dangerous schema operation detected: {pattern}")
        
        # Validate return format
        return_format = config.get("return_format", "records")
        valid_formats = ["records", "dict_list", "json", "count_only"]
        if return_format not in valid_formats:
            raise ValueError(f"Invalid return_format: {return_format}. Must be one of: {', '.join(valid_formats)}")
        
        # Validate transaction isolation level
        isolation_level = config.get("transaction_isolation")
        if isolation_level:
            valid_levels = ["read_uncommitted", "read_committed", "repeatable_read", "serializable"]
            if isolation_level not in valid_levels:
                raise ValueError(f"Invalid transaction_isolation: {isolation_level}. Must be one of: {', '.join(valid_levels)}")
        
        # Validate batch size for bulk operations
        if operation_type == "bulk_operation":
            batch_size = config.get("batch_size", 1000)
            if not isinstance(batch_size, int) or batch_size < 1 or batch_size > 10000:
                raise ValueError("batch_size must be an integer between 1 and 10000")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute enhanced database operation with neo-commons integration.
        
        Input data can include:
        - Dynamic parameters for SQL query placeholders
        - bulk_data: List of records for bulk operations
        - schema_name: Override schema for operation
        - tenant_id: For tenant-specific operations
        """
        operation_start = datetime.utcnow()
        
        try:
            # Extract configuration
            operation_type = config["operation_type"]
            sql_query = config["sql_query"]
            query_params = config.get("query_params", [])
            connection_name = config.get("connection_name")
            transaction_isolation = config.get("transaction_isolation")
            query_timeout = config.get("query_timeout", 30)
            batch_size = config.get("batch_size", 1000)
            return_format = config.get("return_format", "records")
            dry_run = config.get("dry_run", False)
            
            # Extract input data
            schema_name = input_data.get("schema_name", getattr(context, 'schema', None))
            tenant_id = input_data.get("tenant_id", getattr(context, 'tenant_id', None))
            bulk_data = input_data.get("bulk_data", [])
            
            # Process SQL query with input data placeholders
            processed_sql, processed_params = await self._process_sql_query(
                sql_query, input_data, query_params
            )
            
            if dry_run:
                return ExecutionResult(
                    success=True,
                    output_data={
                        "dry_run": True,
                        "processed_sql": processed_sql,
                        "processed_params": processed_params,
                        "operation_type": operation_type,
                        "would_execute": True
                    }
                )
            
            # Get database service
            db_service = await get_database_service()
            
            # Route to appropriate operation
            if operation_type == "bulk_operation":
                result = await self._execute_bulk_operation(
                    db_service, processed_sql, bulk_data, batch_size,
                    connection_name, schema_name, tenant_id, query_timeout
                )
            elif operation_type == "transaction":
                result = await self._execute_transaction(
                    db_service, processed_sql, processed_params, transaction_isolation,
                    connection_name, schema_name, tenant_id, query_timeout
                )
            else:
                result = await self._execute_simple_operation(
                    db_service, processed_sql, processed_params, operation_type,
                    connection_name, schema_name, tenant_id, query_timeout, return_format
                )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - operation_start).total_seconds()
            
            # Enhance result with metadata
            result.update({
                "operation_type": operation_type,
                "execution_time_seconds": execution_time,
                "connection_used": connection_name or "auto-routed",
                "schema_used": schema_name,
                "query_hash": str(hash(processed_sql))
            })
            
            return ExecutionResult(
                success=True,
                output_data=result
            )
            
        except asyncpg.PostgresError as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"PostgreSQL error: {str(e)}",
                error_details={
                    "error_code": e.pgcode if hasattr(e, 'pgcode') else None,
                    "error_severity": getattr(e, 'severity', None),
                    "operation_type": config.get("operation_type"),
                    "sql_query": config.get("sql_query"),
                    "error_type": "PostgresError"
                }
            )
        
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Database operation failed: {str(e)}",
                error_details={
                    "operation_type": config.get("operation_type"),
                    "error_type": type(e).__name__,
                    "connection_name": config.get("connection_name")
                }
            )
    
    async def _process_sql_query(
        self, 
        sql_query: str, 
        input_data: Dict[str, Any], 
        query_params: List[Any]
    ) -> tuple[str, List[Any]]:
        """Process SQL query with input data placeholders and parameters."""
        processed_sql = sql_query
        processed_params = list(query_params)  # Copy existing params
        
        # Handle placeholder replacement for named parameters
        placeholder_count = len(query_params)
        
        for key, value in input_data.items():
            # Skip special keys
            if key in ["schema_name", "tenant_id", "bulk_data"]:
                continue
            
            # Handle positional placeholders like {param_name}
            placeholder = f"{{{key}}}"
            if placeholder in processed_sql:
                placeholder_count += 1
                processed_sql = processed_sql.replace(placeholder, f"${placeholder_count}")
                processed_params.append(value)
        
        return processed_sql, processed_params
    
    async def _execute_simple_operation(
        self,
        db_service,
        sql_query: str,
        params: List[Any],
        operation_type: str,
        connection_name: Optional[str],
        schema_name: Optional[str], 
        tenant_id: Optional[str],
        query_timeout: int,
        return_format: str
    ) -> Dict[str, Any]:
        """Execute simple database operation."""
        
        # Determine connection strategy
        if tenant_id and not connection_name:
            # Use tenant-specific connection
            async with db_service.get_tenant_connection(tenant_id) as conn:
                return await self._execute_query_on_connection(
                    conn, sql_query, params, operation_type, return_format, query_timeout
                )
        else:
            # Use specific connection or schema-based routing
            conn_name = connection_name or schema_name or "admin"
            async with db_service.get_connection(conn_name) as conn:
                # Set schema if specified and different from connection default
                if schema_name and schema_name != conn_name:
                    await conn.execute(f'SET search_path TO "{schema_name}"')
                
                return await self._execute_query_on_connection(
                    conn, sql_query, params, operation_type, return_format, query_timeout
                )
    
    async def _execute_query_on_connection(
        self,
        conn,
        sql_query: str,
        params: List[Any],
        operation_type: str,
        return_format: str,
        query_timeout: int
    ) -> Dict[str, Any]:
        """Execute query on a specific connection."""
        
        if operation_type == "query" or sql_query.strip().lower().startswith("select"):
            # Query operation - fetch results
            rows = await conn.fetch(sql_query, *params, timeout=query_timeout)
            
            if return_format == "count_only":
                return {
                    "affected_rows": len(rows),
                    "result_count": len(rows)
                }
            elif return_format == "dict_list":
                return {
                    "query_result": [dict(row) for row in rows],
                    "result_count": len(rows)
                }
            elif return_format == "json":
                return {
                    "query_result_json": json.dumps([dict(row) for row in rows], default=str),
                    "result_count": len(rows)
                }
            else:  # records
                return {
                    "query_result": [dict(row) for row in rows],
                    "result_count": len(rows),
                    "columns": list(rows[0].keys()) if rows else []
                }
        
        else:
            # Execute operation - return affected rows
            if operation_type == "schema_operation":
                # Schema operations may not return a row count
                await conn.execute(sql_query, *params, timeout=query_timeout)
                return {
                    "operation_completed": True,
                    "schema_operation": True,
                    "sql_executed": sql_query
                }
            else:
                result = await conn.execute(sql_query, *params, timeout=query_timeout)
                # Parse result string like "UPDATE 5" or "INSERT 0 3"
                affected_rows = self._parse_execute_result(result)
                
                return {
                    "affected_rows": affected_rows,
                    "sql_executed": sql_query,
                    "operation_completed": True
                }
    
    async def _execute_transaction(
        self,
        db_service,
        sql_query: str,
        params: List[Any], 
        isolation_level: Optional[str],
        connection_name: Optional[str],
        schema_name: Optional[str],
        tenant_id: Optional[str],
        query_timeout: int
    ) -> Dict[str, Any]:
        """Execute operation within a transaction."""
        
        # Determine connection strategy for transaction
        if tenant_id and not connection_name:
            async with db_service.tenant_transaction(tenant_id) as conn:
                return await self._execute_transaction_on_connection(
                    conn, sql_query, params, isolation_level, query_timeout
                )
        else:
            conn_name = connection_name or schema_name or "admin"  
            async with db_service.transaction(conn_name) as conn:
                if schema_name and schema_name != conn_name:
                    await conn.execute(f'SET search_path TO "{schema_name}"')
                
                return await self._execute_transaction_on_connection(
                    conn, sql_query, params, isolation_level, query_timeout
                )
    
    async def _execute_transaction_on_connection(
        self,
        conn,
        sql_query: str,
        params: List[Any],
        isolation_level: Optional[str],
        query_timeout: int
    ) -> Dict[str, Any]:
        """Execute transaction on a specific connection."""
        
        # Set isolation level if specified
        if isolation_level:
            isolation_map = {
                "read_uncommitted": "READ UNCOMMITTED",
                "read_committed": "READ COMMITTED", 
                "repeatable_read": "REPEATABLE READ",
                "serializable": "SERIALIZABLE"
            }
            await conn.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_map[isolation_level]}")
        
        # Execute the query within transaction
        if sql_query.strip().lower().startswith("select"):
            rows = await conn.fetch(sql_query, *params, timeout=query_timeout)
            return {
                "transaction_completed": True,
                "query_result": [dict(row) for row in rows],
                "result_count": len(rows),
                "isolation_level": isolation_level
            }
        else:
            result = await conn.execute(sql_query, *params, timeout=query_timeout)
            affected_rows = self._parse_execute_result(result)
            
            return {
                "transaction_completed": True,
                "affected_rows": affected_rows,
                "isolation_level": isolation_level
            }
    
    async def _execute_bulk_operation(
        self,
        db_service,
        sql_query: str,
        bulk_data: List[Dict[str, Any]],
        batch_size: int,
        connection_name: Optional[str],
        schema_name: Optional[str],
        tenant_id: Optional[str],
        query_timeout: int
    ) -> Dict[str, Any]:
        """Execute bulk operation with batching."""
        
        if not bulk_data:
            return {
                "bulk_operation_completed": True,
                "total_records": 0,
                "batches_processed": 0,
                "affected_rows": 0
            }
        
        total_affected = 0
        batches_processed = 0
        batch_errors = []
        
        # Process in batches
        for i in range(0, len(bulk_data), batch_size):
            batch = bulk_data[i:i + batch_size]
            
            try:
                if tenant_id and not connection_name:
                    async with db_service.tenant_transaction(tenant_id) as conn:
                        batch_affected = await self._execute_batch_on_connection(
                            conn, sql_query, batch, query_timeout
                        )
                else:
                    conn_name = connection_name or schema_name or "admin"
                    async with db_service.transaction(conn_name) as conn:
                        if schema_name and schema_name != conn_name:
                            await conn.execute(f'SET search_path TO "{schema_name}"')
                        
                        batch_affected = await self._execute_batch_on_connection(
                            conn, sql_query, batch, query_timeout
                        )
                
                total_affected += batch_affected
                batches_processed += 1
                
            except Exception as e:
                batch_errors.append({
                    "batch_start": i,
                    "batch_size": len(batch),
                    "error": str(e)
                })
        
        return {
            "bulk_operation_completed": True,
            "total_records": len(bulk_data),
            "batches_processed": batches_processed,
            "affected_rows": total_affected,
            "batch_size": batch_size,
            "batch_errors": batch_errors,
            "success_rate": batches_processed / ((len(bulk_data) + batch_size - 1) // batch_size)
        }
    
    async def _execute_batch_on_connection(
        self,
        conn,
        sql_query: str,
        batch_data: List[Dict[str, Any]],
        query_timeout: int
    ) -> int:
        """Execute a batch of records on connection."""
        total_affected = 0
        
        for record in batch_data:
            # Convert record to parameters for the query
            # Assuming SQL query uses named placeholders like {field_name}
            params = []
            processed_sql = sql_query
            
            param_count = 0
            for key, value in record.items():
                placeholder = f"{{{key}}}"
                if placeholder in processed_sql:
                    param_count += 1
                    processed_sql = processed_sql.replace(placeholder, f"${param_count}")
                    params.append(value)
            
            result = await conn.execute(processed_sql, *params, timeout=query_timeout)
            total_affected += self._parse_execute_result(result)
        
        return total_affected
    
    def _parse_execute_result(self, result: str) -> int:
        """Parse asyncpg execute result string to get affected rows."""
        try:
            # Result strings look like "UPDATE 5" or "INSERT 0 3" or "DELETE 2"
            parts = result.split()
            if len(parts) >= 2:
                # For INSERT, the last number is the affected rows
                # For UPDATE/DELETE, the second part is affected rows
                if parts[0] == "INSERT" and len(parts) >= 3:
                    return int(parts[2])
                else:
                    return int(parts[1])
            return 0
        except (ValueError, IndexError):
            return 0
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for database operations."""
        base_timeout = config.get("query_timeout", 30)
        operation_type = config.get("operation_type", "query")
        
        # Add extra time for complex operations
        if operation_type == "bulk_operation":
            batch_size = config.get("batch_size", 1000)
            # Estimate extra time based on batch size
            return base_timeout + (batch_size // 100) * 10  # Extra 10s per 100 records
        elif operation_type == "transaction":
            return base_timeout + 30  # Extra time for transaction overhead
        elif operation_type == "schema_operation":
            return base_timeout + 60  # Extra time for schema changes
        else:
            return base_timeout
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check using neo-commons database service."""
        try:
            db_service = await get_database_service()
            health_status = await db_service.health_check()
            
            # Test specific connection if specified
            connection_name = config.get("connection_name")
            connection_health = None
            
            if connection_name:
                try:
                    async with db_service.get_connection(connection_name) as conn:
                        # Simple health check query
                        await conn.fetchval("SELECT 1", timeout=5)
                        connection_health = {
                            "connection_name": connection_name,
                            "healthy": True,
                            "response_time_ms": "<5000"
                        }
                except Exception as e:
                    connection_health = {
                        "connection_name": connection_name,
                        "healthy": False,
                        "error": str(e)
                    }
            
            return {
                "healthy": health_status.get("overall_healthy", False),
                "status": "Database service integration healthy" if health_status.get("overall_healthy") else "Database service issues detected",
                "details": {
                    "database_service_health": health_status,
                    "specific_connection": connection_health,
                    "total_connections": health_status.get("total_connections", 0)
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Database service health check failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for enhanced database handler."""
        return {
            "type": "object",
            "properties": {
                "operation_type": {
                    "type": "string",
                    "enum": ["query", "execute", "transaction", "schema_operation", "bulk_operation"],
                    "description": "Type of database operation"
                },
                "sql_query": {
                    "type": "string",
                    "description": "SQL query or statement to execute"
                },
                "query_params": {
                    "type": "array",
                    "items": {"type": ["string", "number", "boolean", "null"]},
                    "description": "Parameters for parameterized query"
                },
                "connection_name": {
                    "type": "string",
                    "description": "Database connection name (optional, auto-routed if not specified)"
                },
                "transaction_isolation": {
                    "type": "string",
                    "enum": ["read_uncommitted", "read_committed", "repeatable_read", "serializable"],
                    "description": "Transaction isolation level"
                },
                "query_timeout": {
                    "type": "integer",
                    "default": 30,
                    "description": "Query timeout in seconds"
                },
                "batch_size": {
                    "type": "integer",
                    "default": 1000,
                    "minimum": 1,
                    "maximum": 10000,
                    "description": "Batch size for bulk operations"
                },
                "return_format": {
                    "type": "string",
                    "enum": ["records", "dict_list", "json", "count_only"],
                    "default": "records",
                    "description": "Result format for query operations"
                },
                "dry_run": {
                    "type": "boolean",
                    "default": False,
                    "description": "Validate but don't execute"
                }
            },
            "required": ["operation_type", "sql_query"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for enhanced database handler."""
        return {
            "type": "object",
            "properties": {
                "schema_name": {
                    "type": "string",
                    "description": "Override schema for operation"
                },
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant ID for tenant-specific operations"
                },
                "bulk_data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Array of records for bulk operations"
                }
            },
            "additionalProperties": True,
            "description": "Input data for SQL query placeholders and operation parameters"
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for enhanced database handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "operation_type": {"type": "string"},
                "execution_time_seconds": {"type": "number"},
                "connection_used": {"type": "string"},
                "schema_used": {"type": "string"},
                "affected_rows": {"type": "integer"},
                "result_count": {"type": "integer"},
                "query_result": {"type": "array"},
                "transaction_completed": {"type": "boolean"},
                "bulk_operation_completed": {"type": "boolean"},
                "total_records": {"type": "integer"},
                "batches_processed": {"type": "integer"},
                "success_rate": {"type": "number"},
                "batch_errors": {"type": "array"}
            },
            "required": ["success"]
        }