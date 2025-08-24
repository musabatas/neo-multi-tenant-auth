"""Database validation utilities to eliminate duplicate validation logic."""

from typing import Optional


def validate_pool_configuration(
    pool_min_size: int,
    pool_max_size: int,
    pool_timeout_seconds: Optional[int] = None,
    connection_name: Optional[str] = None
) -> None:
    """Validate pool configuration parameters.
    
    Args:
        pool_min_size: Minimum pool size
        pool_max_size: Maximum pool size
        pool_timeout_seconds: Pool timeout in seconds (optional)
        connection_name: Connection name for context (optional)
        
    Raises:
        ValueError: If validation fails
    """
    context = f" for connection '{connection_name}'" if connection_name else ""
    
    if pool_min_size < 0:
        raise ValueError(f"pool_min_size must be >= 0{context}")
    
    if pool_max_size < pool_min_size:
        raise ValueError(f"pool_max_size must be >= pool_min_size{context}")
    
    if pool_timeout_seconds is not None and pool_timeout_seconds <= 0:
        raise ValueError(f"pool_timeout_seconds must be > 0{context}")


def validate_connection_basic_fields(
    connection_name: str,
    host: str,
    database_name: Optional[str] = None
) -> None:
    """Validate basic connection fields.
    
    Args:
        connection_name: Connection name
        host: Database host
        database_name: Database name (optional)
        
    Raises:
        ValueError: If validation fails
    """
    if not connection_name or not connection_name.strip():
        raise ValueError("connection_name cannot be empty")
    
    if not host or not host.strip():
        raise ValueError("host cannot be empty")
    
    if database_name is not None and not database_name.strip():
        raise ValueError("database_name cannot be empty")


def validate_connection_timeouts(
    pool_timeout_seconds: int,
    pool_recycle_seconds: int,
    connection_name: Optional[str] = None
) -> None:
    """Validate connection timeout parameters.
    
    Args:
        pool_timeout_seconds: Pool connection timeout
        pool_recycle_seconds: Pool connection recycle time
        connection_name: Connection name for context (optional)
        
    Raises:
        ValueError: If validation fails
    """
    context = f" for connection '{connection_name}'" if connection_name else ""
    
    if pool_timeout_seconds <= 0:
        raise ValueError(f"pool_timeout_seconds must be > 0{context}")
    
    if pool_recycle_seconds <= 0:
        raise ValueError(f"pool_recycle_seconds must be > 0{context}")