"""Database-related exceptions for neo-commons."""

from .base import NeoCommonsError


class DatabaseError(NeoCommonsError):
    """Base class for database-related errors."""
    pass


class ConnectionError(DatabaseError):
    """Base class for connection-related errors."""
    pass


class ConnectionNotFoundError(ConnectionError):
    """Raised when a database connection is not found."""
    
    def __init__(self, connection_name: str):
        self.connection_name = connection_name
        super().__init__(f"Database connection '{connection_name}' not found")


class ConnectionUnavailableError(ConnectionError):
    """Raised when a database connection is unavailable."""
    
    def __init__(self, connection_name: str, reason: str = ""):
        self.connection_name = connection_name
        self.reason = reason
        message = f"Database connection '{connection_name}' is unavailable"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class ConnectionPoolError(ConnectionError):
    """Raised when there's an error with the connection pool."""
    pass


class ConnectionTimeoutError(ConnectionError):
    """Raised when a database connection times out."""
    
    def __init__(self, connection_name: str, timeout_seconds: int):
        self.connection_name = connection_name
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Connection to '{connection_name}' timed out after {timeout_seconds} seconds"
        )


class HealthCheckFailedError(DatabaseError):
    """Raised when a database health check fails."""
    
    def __init__(self, connection_name: str, error: str):
        self.connection_name = connection_name
        self.health_error = error
        super().__init__(f"Health check failed for '{connection_name}': {error}")


class SchemaError(DatabaseError):
    """Base class for schema-related errors."""
    pass


class SchemaNotFoundError(SchemaError):
    """Raised when a database schema is not found."""
    
    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        super().__init__(f"Schema '{schema_name}' not found")


class InvalidSchemaError(SchemaError):
    """Raised when a schema name is invalid or unsafe."""
    
    def __init__(self, schema_name: str, reason: str = ""):
        self.schema_name = schema_name
        self.reason = reason
        message = f"Invalid schema name '{schema_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class SchemaResolutionError(SchemaError):
    """Raised when schema resolution fails."""
    pass


class FailoverError(DatabaseError):
    """Raised when database failover fails."""
    
    def __init__(self, connection_name: str, reason: str = ""):
        self.connection_name = connection_name
        self.reason = reason
        message = f"Failover failed for connection '{connection_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class QueryError(DatabaseError):
    """Base class for query execution errors."""
    pass


class QueryTimeoutError(QueryError):
    """Raised when a database query times out."""
    
    def __init__(self, query: str, timeout_seconds: int):
        self.query = query
        self.timeout_seconds = timeout_seconds
        # Truncate query for error message
        query_preview = query[:100] + "..." if len(query) > 100 else query
        super().__init__(f"Query timed out after {timeout_seconds}s: {query_preview}")


class QuerySyntaxError(QueryError):
    """Raised when a database query has syntax errors."""
    
    def __init__(self, query: str, error: str):
        self.query = query
        self.syntax_error = error
        # Truncate query for error message
        query_preview = query[:100] + "..." if len(query) > 100 else query
        super().__init__(f"Query syntax error: {error}\nQuery: {query_preview}")


class TransactionError(DatabaseError):
    """Base class for transaction-related errors."""
    pass


class TransactionRollbackError(TransactionError):
    """Raised when a transaction rollback fails."""
    pass


class TransactionCommitError(TransactionError):
    """Raised when a transaction commit fails."""
    pass


class MigrationError(DatabaseError):
    """Base class for database migration errors."""
    pass


class MigrationNotFoundError(MigrationError):
    """Raised when a migration is not found."""
    
    def __init__(self, migration_id: str):
        self.migration_id = migration_id
        super().__init__(f"Migration '{migration_id}' not found")


class MigrationFailedError(MigrationError):
    """Raised when a migration fails to execute."""
    
    def __init__(self, migration_id: str, error: str):
        self.migration_id = migration_id
        self.migration_error = error
        super().__init__(f"Migration '{migration_id}' failed: {error}")


class RepositoryError(DatabaseError):
    """Base class for repository-related errors."""
    pass


class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found in the repository."""
    
    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} with identifier '{identifier}' not found")


class EntityAlreadyExistsError(RepositoryError):
    """Raised when trying to create an entity that already exists."""
    
    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(f"{entity_type} with identifier '{identifier}' already exists")


class ConcurrencyError(RepositoryError):
    """Raised when a concurrency conflict occurs."""
    
    def __init__(self, entity_type: str, identifier: str):
        self.entity_type = entity_type
        self.identifier = identifier
        super().__init__(
            f"Concurrency conflict for {entity_type} '{identifier}'. "
            f"Entity was modified by another process."
        )


class DatabaseValidationError(RepositoryError):
    """Raised when database data validation fails."""
    
    def __init__(self, field: str, value: str, reason: str):
        self.field = field
        self.value = value
        self.reason = reason
        super().__init__(f"Database validation failed for field '{field}' with value '{value}': {reason}")


class DatabaseConfigurationError(DatabaseError):
    """Raised when there's a database configuration error."""
    pass


class EncryptionError(DatabaseError):
    """Raised when password encryption/decryption fails."""
    
    def __init__(self, operation: str, reason: str = ""):
        self.operation = operation
        self.reason = reason
        message = f"Encryption {operation} failed"
        if reason:
            message += f": {reason}"
        super().__init__(message)