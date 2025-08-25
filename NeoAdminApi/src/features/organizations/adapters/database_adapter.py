"""Database adapter to bridge DatabaseService and DatabaseRepository interfaces."""

import json
from typing import Any, List, Optional, Dict
from neo_commons.features.database.entities.protocols import DatabaseRepository


class DatabaseServiceAdapter(DatabaseRepository):
    """Adapter that wraps DatabaseService to provide DatabaseRepository interface."""
    
    # JSON/JSONB fields that need parsing
    JSON_FIELDS = {'brand_colors', 'metadata', 'verification_documents'}

    def __init__(self, database_service, connection_name: str = "admin"):
        """Initialize adapter with database service and connection name.
        
        Args:
            database_service: DatabaseService instance
            connection_name: Connection name to use for queries
        """
        self._service = database_service
        self._connection_name = connection_name
    
    def _convert_row_values(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert database row values to proper Python types."""
        for key, value in row_dict.items():
            # Convert UUID objects to strings
            if hasattr(value, '__class__') and 'UUID' in value.__class__.__name__:
                row_dict[key] = str(value)
            # Parse JSON fields
            elif key in self.JSON_FIELDS and isinstance(value, str):
                try:
                    row_dict[key] = json.loads(value) if value else {}
                except (json.JSONDecodeError, TypeError):
                    row_dict[key] = {}
        return row_dict

    async def execute_query(self, query: str, params: Optional[List[Any]] = None) -> Any:
        """Execute a query and return result."""
        if params is None:
            params = []
        return await self._service.execute_query(self._connection_name, query, *params)
    
    async def fetch_all(self, query: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Fetch all results from a query."""
        if params is None:
            params = []
        result = await self._service.execute_query(self._connection_name, query, *params)
        # Convert asyncpg Records to dict format expected by repository
        if result:
            converted_result = []
            for row in result:
                row_dict = dict(row)
                # Convert values using helper method
                row_dict = self._convert_row_values(row_dict)
                converted_result.append(row_dict)
            return converted_result
        return []
    
    async def fetch_one(self, query: str, params: Optional[List[Any]] = None) -> Optional[Dict[str, Any]]:
        """Fetch one result from a query."""
        if params is None:
            params = []
        result = await self._service.execute_query(self._connection_name, query, *params)
        if result and len(result) > 0:
            row_dict = dict(result[0])
            # Convert values using helper method
            row_dict = self._convert_row_values(row_dict)
            return row_dict
        return None
    
    async def execute(self, query: str, params: Optional[List[Any]] = None) -> bool:
        """Execute a query without returning results."""
        if params is None:
            params = []
        try:
            await self._service.execute_query(self._connection_name, query, *params)
            return True
        except Exception:
            return False
    
    async def execute_command(self, 
                             command: str, 
                             *args: Any,
                             schema_name: Optional[str] = None) -> str:
        """Execute a command (INSERT, UPDATE, DELETE) and return status."""
        # If schema_name is provided, format the command to use it
        if schema_name and "{schema}" in command:
            command = command.format(schema=schema_name)
        
        # Use the connection manager's execute_command if available
        if hasattr(self._service, 'connection_manager') and hasattr(self._service.connection_manager, 'execute_command'):
            return await self._service.connection_manager.execute_command(self._connection_name, command, *args)
        else:
            # Fallback to execute_query for compatibility
            await self._service.execute_query(self._connection_name, command, *args)
            return "OK"
    
    async def execute_fetchrow(self, 
                              query: str, 
                              *args: Any,
                              schema_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Execute a query and return single row."""
        # If schema_name is provided, format the query to use it
        if schema_name and "{schema}" in query:
            query = query.format(schema=schema_name)
        
        # Use the connection manager's execute_fetchrow if available
        if hasattr(self._service, 'connection_manager') and hasattr(self._service.connection_manager, 'execute_fetchrow'):
            row_dict = await self._service.connection_manager.execute_fetchrow(self._connection_name, query, *args)
            if row_dict:
                # Convert UUID objects to strings for compatibility
                for key, value in row_dict.items():
                    if hasattr(value, '__class__') and 'UUID' in value.__class__.__name__:
                        row_dict[key] = str(value)
            return row_dict
        else:
            # Fallback to execute_query and take first result
            result = await self._service.execute_query(self._connection_name, query, *args)
            if result and len(result) > 0:
                row_dict = dict(result[0])
                # Convert UUID objects to strings for compatibility
                for key, value in row_dict.items():
                    if hasattr(value, '__class__') and 'UUID' in value.__class__.__name__:
                        row_dict[key] = str(value)
                return row_dict
            return None
    
    async def execute_fetchval(self, 
                              query: str, 
                              *args: Any,
                              schema_name: Optional[str] = None) -> Any:
        """Execute a query and return single value."""
        # If schema_name is provided, format the query to use it
        if schema_name and "{schema}" in query:
            query = query.format(schema=schema_name)
        
        # Use the connection manager's execute_fetchval if available
        if hasattr(self._service, 'connection_manager') and hasattr(self._service.connection_manager, 'execute_fetchval'):
            return await self._service.connection_manager.execute_fetchval(self._connection_name, query, *args)
        else:
            # Fallback to execute_query and extract first value
            result = await self._service.execute_query(self._connection_name, query, *args)
            if result and len(result) > 0:
                row = dict(result[0])
                # Return the first value from the first row
                return next(iter(row.values())) if row else None
            return None