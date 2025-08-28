"""JSON cache serializer.

ONLY JSON serialization - implements JSON serialization for cache values
with type preservation and compression support.

Following maximum separation architecture - one file = one purpose.
"""

import json
import gzip
import time
import sys
from dataclasses import dataclass
from typing import Any, Optional, Dict
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from ...core.exceptions.serialization_error import SerializationError
from ...core.exceptions.deserialization_error import DeserializationError


@dataclass
class JSONSerializerStats:
    """JSON serializer performance statistics."""
    
    serialization_count: int = 0
    deserialization_count: int = 0
    total_serialization_time: float = 0.0
    total_deserialization_time: float = 0.0
    total_bytes_serialized: int = 0
    total_bytes_deserialized: int = 0
    compression_ratio: float = 0.0
    error_count: int = 0


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for extended type support."""
    
    def default(self, obj: Any) -> Any:
        """Handle non-standard JSON types."""
        if isinstance(obj, datetime):
            return {"__datetime__": obj.isoformat()}
        elif isinstance(obj, date):
            return {"__date__": obj.isoformat()}
        elif isinstance(obj, Decimal):
            return {"__decimal__": str(obj)}
        elif isinstance(obj, UUID):
            return {"__uuid__": str(obj)}
        elif isinstance(obj, set):
            return {"__set__": list(obj)}
        elif isinstance(obj, frozenset):
            return {"__frozenset__": list(obj)}
        elif isinstance(obj, bytes):
            return {"__bytes__": obj.hex()}
        elif hasattr(obj, '__dict__'):
            # Handle simple objects with __dict__
            return {"__object__": {
                "class": obj.__class__.__name__,
                "module": obj.__class__.__module__,
                "data": obj.__dict__
            }}
        
        # Fallback to string representation
        return {"__repr__": repr(obj)}


def decode_json_object(obj: Dict[str, Any]) -> Any:
    """Decode custom JSON objects back to Python types."""
    if "__datetime__" in obj:
        return datetime.fromisoformat(obj["__datetime__"])
    elif "__date__" in obj:
        return date.fromisoformat(obj["__date__"])
    elif "__decimal__" in obj:
        return Decimal(obj["__decimal__"])
    elif "__uuid__" in obj:
        return UUID(obj["__uuid__"])
    elif "__set__" in obj:
        return set(obj["__set__"])
    elif "__frozenset__" in obj:
        return frozenset(obj["__frozenset__"])
    elif "__bytes__" in obj:
        return bytes.fromhex(obj["__bytes__"])
    elif "__object__" in obj:
        # Simple object reconstruction - limited support
        return obj  # Return as dict for safety
    elif "__repr__" in obj:
        # Can't safely reconstruct from repr
        return f"<Unparseable: {obj['__repr__']}>"
    
    return obj


class JSONCacheSerializer:
    """JSON cache serializer with extended type support and compression.
    
    Features:
    - JSON serialization with extended type support
    - Optional gzip compression
    - Type preservation for common Python types
    - Performance monitoring and statistics
    - Configuration options for JSON encoding
    """
    
    def __init__(
        self,
        ensure_ascii: bool = False,
        indent: Optional[int] = None,
        separators: Optional[tuple] = None,
        sort_keys: bool = False,
        use_compression: bool = False,
        compression_level: int = 6,
        compression_threshold: int = 1024  # Compress if > 1KB
    ):
        """Initialize JSON serializer.
        
        Args:
            ensure_ascii: If True, escape non-ASCII characters
            indent: JSON indentation (None for compact)
            separators: Item and key separators 
            sort_keys: Sort dictionary keys
            use_compression: Enable gzip compression
            compression_level: Gzip compression level (1-9)
            compression_threshold: Minimum size for compression
        """
        self._ensure_ascii = ensure_ascii
        self._indent = indent
        self._separators = separators or (',', ':') if indent is None else None
        self._sort_keys = sort_keys
        self._use_compression = use_compression
        self._compression_level = compression_level
        self._compression_threshold = compression_threshold
        self._stats = JSONSerializerStats()
    
    def serialize(self, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bytes:
        """Serialize value to JSON bytes."""
        start_time = time.time()
        
        try:
            # Serialize to JSON string
            json_str = json.dumps(
                value,
                cls=CustomJSONEncoder,
                ensure_ascii=self._ensure_ascii,
                indent=self._indent,
                separators=self._separators,
                sort_keys=self._sort_keys
            )
            
            # Convert to bytes
            json_bytes = json_str.encode('utf-8')
            
            # Apply compression if enabled and beneficial
            if (self._use_compression and 
                len(json_bytes) >= self._compression_threshold):
                compressed = gzip.compress(json_bytes, compresslevel=self._compression_level)
                # Only use compression if it actually reduces size
                if len(compressed) < len(json_bytes):
                    result_bytes = b'GZIP:' + compressed
                    compression_ratio = len(json_bytes) / len(result_bytes)
                    self._stats.compression_ratio = (
                        (self._stats.compression_ratio * self._stats.serialization_count + compression_ratio) /
                        (self._stats.serialization_count + 1)
                    )
                else:
                    result_bytes = json_bytes
            else:
                result_bytes = json_bytes
            
            # Update statistics
            elapsed = time.time() - start_time
            self._stats.serialization_count += 1
            self._stats.total_serialization_time += elapsed
            self._stats.total_bytes_serialized += len(result_bytes)
            
            return result_bytes
            
        except (TypeError, ValueError, OverflowError) as e:
            self._stats.error_count += 1
            raise SerializationError(
                f"JSON serialization failed: {str(e)}",
                value=value,
                serializer_type="json",
                original_error=e,
                metadata=metadata
            )
        except Exception as e:
            self._stats.error_count += 1
            raise SerializationError(
                f"Unexpected JSON serialization error: {str(e)}",
                value=value,
                serializer_type="json",
                original_error=e,
                metadata=metadata
            )
    
    def deserialize(self, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Deserialize JSON bytes back to Python object."""
        start_time = time.time()
        
        try:
            # Check for compression
            if data.startswith(b'GZIP:'):
                json_bytes = gzip.decompress(data[5:])  # Remove 'GZIP:' prefix
            else:
                json_bytes = data
            
            # Decode from bytes to string
            json_str = json_bytes.decode('utf-8')
            
            # Parse JSON with custom object hook
            result = json.loads(json_str, object_hook=decode_json_object)
            
            # Update statistics
            elapsed = time.time() - start_time
            self._stats.deserialization_count += 1
            self._stats.total_deserialization_time += elapsed
            self._stats.total_bytes_deserialized += len(data)
            
            return result
            
        except (json.JSONDecodeError, UnicodeDecodeError, gzip.BadGzipFile) as e:
            self._stats.error_count += 1
            raise DeserializationError(
                f"JSON deserialization failed: {str(e)}",
                data=data,
                serializer_type="json",
                original_error=e,
                metadata=metadata
            )
        except Exception as e:
            self._stats.error_count += 1
            raise DeserializationError(
                f"Unexpected JSON deserialization error: {str(e)}",
                data=data,
                serializer_type="json",
                original_error=e,
                metadata=metadata
            )
    
    def get_format_name(self) -> str:
        """Get serialization format name."""
        return "json"
    
    def supports_compression(self) -> bool:
        """Check if serializer supports compression."""
        return True
    
    def get_content_type(self) -> str:
        """Get MIME content type."""
        return "application/json"
    
    def estimate_serialized_size(self, value: Any) -> int:
        """Estimate serialized size without actually serializing."""
        try:
            # Quick size estimation based on repr length
            # This is rough but fast
            base_size = len(repr(value)) * 1.2  # JSON overhead factor
            
            # Account for compression if enabled
            if self._use_compression and base_size >= self._compression_threshold:
                # Assume ~30% compression ratio
                base_size *= 0.7
            
            return int(base_size)
            
        except Exception:
            # Fallback to conservative estimate
            return sys.getsizeof(value) * 2
    
    def can_serialize(self, value: Any) -> bool:
        """Check if value can be serialized."""
        try:
            # Quick test serialization
            json.dumps(value, cls=CustomJSONEncoder, ensure_ascii=True)
            return True
        except Exception:
            return False
    
    def get_serialization_metadata(self, value: Any) -> Dict[str, Any]:
        """Get serialization metadata."""
        return {
            "estimated_size": self.estimate_serialized_size(value),
            "type_info": type(value).__name__,
            "compression_recommended": (
                self.estimate_serialized_size(value) >= self._compression_threshold
            ),
            "serializer_version": "1.0",
            "format": self.get_format_name(),
            "content_type": self.get_content_type()
        }
    
    async def serialize_stream(self, value: Any, chunk_size: int = 8192) -> bytes:
        """Serialize in streaming fashion (fallback to regular serialize)."""
        return self.serialize(value)
    
    async def deserialize_stream(self, data: bytes, chunk_size: int = 8192) -> Any:
        """Deserialize in streaming fashion (fallback to regular deserialize)."""
        return self.deserialize(data)
    
    def configure(self, **options) -> None:
        """Configure serializer options."""
        if 'ensure_ascii' in options:
            self._ensure_ascii = options['ensure_ascii']
        if 'indent' in options:
            self._indent = options['indent']
        if 'separators' in options:
            self._separators = options['separators']
        if 'sort_keys' in options:
            self._sort_keys = options['sort_keys']
        if 'use_compression' in options:
            self._use_compression = options['use_compression']
        if 'compression_level' in options:
            self._compression_level = max(1, min(9, options['compression_level']))
        if 'compression_threshold' in options:
            self._compression_threshold = max(0, options['compression_threshold'])
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "ensure_ascii": self._ensure_ascii,
            "indent": self._indent,
            "separators": self._separators,
            "sort_keys": self._sort_keys,
            "use_compression": self._use_compression,
            "compression_level": self._compression_level,
            "compression_threshold": self._compression_threshold
        }
    
    def reset_configuration(self) -> None:
        """Reset to default configuration."""
        self.__init__()
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {
            "serialization_count": self._stats.serialization_count,
            "deserialization_count": self._stats.deserialization_count,
            "total_serialization_time": self._stats.total_serialization_time,
            "total_deserialization_time": self._stats.total_deserialization_time,
            "total_bytes_serialized": self._stats.total_bytes_serialized,
            "total_bytes_deserialized": self._stats.total_bytes_deserialized,
            "compression_ratio": self._stats.compression_ratio,
            "error_count": self._stats.error_count
        }
        
        # Calculate averages
        if self._stats.serialization_count > 0:
            stats["average_serialization_time"] = (
                self._stats.total_serialization_time / self._stats.serialization_count
            )
        
        if self._stats.deserialization_count > 0:
            stats["average_deserialization_time"] = (
                self._stats.total_deserialization_time / self._stats.deserialization_count
            )
        
        return stats
    
    def reset_performance_stats(self) -> None:
        """Reset performance statistics."""
        self._stats = JSONSerializerStats()


# Factory function for dependency injection
def create_json_serializer(
    ensure_ascii: bool = False,
    use_compression: bool = False,
    compression_level: int = 6,
    **options
) -> JSONCacheSerializer:
    """Create JSON cache serializer with configuration.
    
    Args:
        ensure_ascii: If True, escape non-ASCII characters
        use_compression: Enable gzip compression
        compression_level: Gzip compression level (1-9)
        **options: Additional configuration options
        
    Returns:
        Configured JSON cache serializer
    """
    return JSONCacheSerializer(
        ensure_ascii=ensure_ascii,
        use_compression=use_compression,
        compression_level=compression_level,
        **options
    )