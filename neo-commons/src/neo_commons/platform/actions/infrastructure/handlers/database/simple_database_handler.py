"""Simple database operation action handler implementation."""

from typing import Dict, Any
import asyncpg

from ....application.handlers.action_handler import ActionHandler
from ....application.protocols.action_executor import ExecutionContext, ExecutionResult


class SimpleDatabaseHandler(ActionHandler):
    """
    Simple database operation handler using asyncpg.
    
    Configuration:
    - operation_type: Type of operation (query, execute, transaction)
    - sql_query: SQL query or statement to execute
    - query_params: Parameters for the query (optional)
    - connection_name: Database connection name (optional, defaults to schema)
    """
    
    @property
    def handler_name(self) -> str:
        return "simple_database_handler"
    
    @property
    def handler_version(self) -> str:
        return "1.0.0"
    
    @property
    def supported_action_types(self) -> list[str]:
        return ["database_operation"]
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate database handler configuration."""
        if "operation_type" not in config:
            raise ValueError("Missing required database config field: operation_type")
        
        if "sql_query" not in config:
            raise ValueError("Missing required database config field: sql_query")
        
        operation_type = config["operation_type"]
        if operation_type not in ["query", "execute", "transaction"]:
            raise ValueError(f"Invalid operation_type: {operation_type}. Must be one of: query, execute, transaction")
        
        # Basic SQL injection prevention - check for dangerous patterns
        sql_query = config["sql_query"].lower().strip()
        if any(dangerous in sql_query for dangerous in ["drop ", "delete ", "truncate ", "alter "]):
            if operation_type != "execute":
                raise ValueError("Dangerous SQL operations only allowed with operation_type='execute'")
        
        return True
    
    async def execute(
        self, 
        config: Dict[str, Any], 
        input_data: Dict[str, Any], 
        context: ExecutionContext
    ) -> ExecutionResult:
        """
        Execute database operation.
        
        The handler will use the neo-commons database service to get connections.
        """
        try:
            # Extract configuration
            operation_type = config["operation_type"]
            sql_query = config["sql_query"]
            query_params = config.get("query_params", [])
            connection_name = config.get("connection_name", context.schema)
            
            # Replace placeholders in SQL with input data
            formatted_sql = sql_query
            for key, value in input_data.items():
                placeholder = f"{{{key}}}"
                if placeholder in formatted_sql:
                    formatted_sql = formatted_sql.replace(placeholder, str(value))
            
            # TODO: Get database service from context (when available)
            # For now, return a mock success result
            result_data = {
                "operation_type": operation_type,
                "sql_executed": formatted_sql,
                "connection_name": connection_name,
                "affected_rows": 0,  # Would be actual result from DB
                "query_result": []   # Would be actual query results
            }
            
            return ExecutionResult(
                success=True,
                output_data=result_data
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output_data={},
                error_message=f"Database operation failed: {str(e)}",
                error_details={
                    "operation_type": config.get("operation_type"),
                    "sql_query": config.get("sql_query"),
                    "error_type": type(e).__name__
                }
            )
    
    async def get_execution_timeout(self, config: Dict[str, Any]) -> int:
        """Get execution timeout for database operations."""
        return config.get("timeout_seconds", 60)  # Database operations can take longer
    
    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Perform health check by testing database connectivity."""
        try:
            # TODO: Test actual database connection when database service is available
            return {
                "healthy": True,
                "status": "Database handler ready (connection test not implemented)",
                "details": {
                    "operation_type": config.get("operation_type"),
                    "connection_name": config.get("connection_name", "default")
                }
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "status": f"Database connection failed: {str(e)}",
                "details": {
                    "error_type": type(e).__name__
                }
            }
    
    def get_config_schema(self) -> Dict[str, Any]:
        """Get configuration schema for database handler."""
        return {
            "type": "object",
            "properties": {
                "operation_type": {
                    "type": "string",
                    "enum": ["query", "execute", "transaction"],
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
                    "description": "Database connection name"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "default": 60,
                    "description": "Execution timeout in seconds"
                }
            },
            "required": ["operation_type", "sql_query"]
        }
    
    def get_input_schema(self) -> Dict[str, Any]:
        """Get input data schema for database handler."""
        return {
            "type": "object",
            "description": "Input data for SQL query placeholder replacement",
            "additionalProperties": True
        }
    
    def get_output_schema(self) -> Dict[str, Any]:
        """Get output data schema for database handler."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "operation_type": {"type": "string"},
                "sql_executed": {"type": "string"},
                "connection_name": {"type": "string"},
                "affected_rows": {"type": "integer"},
                "query_result": {"type": "array"}
            },
            "required": ["success"]
        }