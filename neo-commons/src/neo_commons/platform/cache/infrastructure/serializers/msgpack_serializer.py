"""MessagePack cache serializer.

ONLY msgpack serialization - implements MessagePack serialization for cache values
with binary efficiency and compression support.

Following maximum separation architecture - one file = one purpose.
"""

import time
import sys
import gzip
from dataclasses import dataclass
from typing import Any, Optional, Dict
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

try:
    import msgpack
except ImportError:
    msgpack = None

from ...core.exceptions.serialization_error import SerializationError
from ...core.exceptions.deserialization_error import DeserializationError


@dataclass
class MessagePackSerializerStats:
    """MessagePack serializer performance statistics."""
    
    serialization_count: int = 0
    deserialization_count: int = 0
    total_serialization_time: float = 0.0
    total_deserialization_time: float = 0.0
    total_bytes_serialized: int = 0
    total_bytes_deserialized: int = 0
    compression_ratio: float = 0.0
    error_count: int = 0


def default_encoder(obj: Any) -> Any:
    """Default encoder for non-MessagePack types."""
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
    elif isinstance(obj, complex):
        return {"__complex__": [obj.real, obj.imag]}
    elif hasattr(obj, '__dict__'):
        # Handle simple objects with __dict__
        return {"__object__": {
            "class": obj.__class__.__name__,
            "module": obj.__class__.__module__,
            "data": obj.__dict__
        }}
    
    # Fallback to string representation
    return {"__repr__": repr(obj)}


def decode_msgpack_object(obj: Any) -> Any:
    """Decode custom MessagePack objects back to Python types."""
    if isinstance(obj, dict):
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
        elif "__complex__" in obj:
            real, imag = obj["__complex__"]
            return complex(real, imag)
        elif "__object__" in obj:
            # Simple object reconstruction - return as dict for safety
            return obj
        elif "__repr__" in obj:
            # Can't safely reconstruct from repr
            return f"<Unparseable: {obj['__repr__']}>"
    
    return obj


class MessagePackCacheSerializer:
    """MessagePack cache serializer with binary efficiency and compression.
    
    Features:
    - MessagePack binary serialization
    - Extended type support with custom encoders
    - Optional gzip compression
    - High performance for structured data
    - Smaller output than JSON, safer than pickle
    """
    
    def __init__(
        self,
        use_single_float: bool = False,
        use_bin_type: bool = True,
        strict_map_key: bool = False,
        datetime_format: str = 'iso',
        use_compression: bool = False,
        compression_level: int = 6,
        compression_threshold: int = 1024  # Compress if > 1KB
    ):
        """Initialize MessagePack serializer.
        
        Args:
            use_single_float: Use single precision for floats
            use_bin_type: Use bin type for binary data (recommended)
            strict_map_key: Only allow string/binary keys in maps
            datetime_format: Format for datetime encoding ('iso' or 'timestamp')
            use_compression: Enable gzip compression
            compression_level: Gzip compression level (1-9)
            compression_threshold: Minimum size for compression
        """
        if msgpack is None:
            raise ImportError(
                "msgpack is required for MessagePack serialization. "
                "Install with: pip install msgpack"
            )
        
        self._use_single_float = use_single_float
        self._use_bin_type = use_bin_type
        self._strict_map_key = strict_map_key
        self._datetime_format = datetime_format
        self._use_compression = use_compression
        self._compression_level = max(1, min(9, compression_level))
        self._compression_threshold = max(0, compression_threshold)
        self._stats = MessagePackSerializerStats()
    
    def serialize(self, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bytes:
        """Serialize value to MessagePack bytes."""
        if msgpack is None:
            raise SerializationError(
                "msgpack library not available",
                value=value,
                serializer_type="msgpack"
            )
        
        start_time = time.time()
        
        try:
            # Serialize with MessagePack
            msgpack_bytes = msgpack.packb(
                value,
                default=default_encoder,
                use_single_float=self._use_single_float,
                use_bin_type=self._use_bin_type,
                strict_map_key=self._strict_map_key
            )
            
            # Apply compression if enabled and beneficial
            if (self._use_compression and 
                len(msgpack_bytes) >= self._compression_threshold):
                compressed = gzip.compress(msgpack_bytes, compresslevel=self._compression_level)
                # Only use compression if it actually reduces size
                if len(compressed) < len(msgpack_bytes):
                    result_bytes = b'GZIP:' + compressed
                    compression_ratio = len(msgpack_bytes) / len(result_bytes)
                    self._stats.compression_ratio = (
                        (self._stats.compression_ratio * self._stats.serialization_count + compression_ratio) /
                        (self._stats.serialization_count + 1)
                    )
                else:
                    result_bytes = msgpack_bytes
            else:
                result_bytes = msgpack_bytes
            
            # Update statistics
            elapsed = time.time() - start_time
            self._stats.serialization_count += 1
            self._stats.total_serialization_time += elapsed
            self._stats.total_bytes_serialized += len(result_bytes)
            
            return result_bytes
            
        except (msgpack.PackException, TypeError, ValueError, OverflowError) as e:
            self._stats.error_count += 1
            raise SerializationError(
                f"MessagePack serialization failed: {str(e)}",
                value=value,
                serializer_type="msgpack",
                original_error=e,
                metadata=metadata
            )
        except Exception as e:
            self._stats.error_count += 1
            raise SerializationError(
                f"Unexpected MessagePack serialization error: {str(e)}",
                value=value,
                serializer_type="msgpack",
                original_error=e,
                metadata=metadata
            )
    
    def deserialize(self, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Deserialize MessagePack bytes back to Python object."""
        if msgpack is None:
            raise DeserializationError(
                "msgpack library not available",
                data=data,
                serializer_type="msgpack"
            )
        
        start_time = time.time()
        
        try:
            # Check for compression
            if data.startswith(b'GZIP:'):
                msgpack_bytes = gzip.decompress(data[5:])  # Remove 'GZIP:' prefix
            else:
                msgpack_bytes = data
            
            # Deserialize with MessagePack
            result = msgpack.unpackb(
                msgpack_bytes,
                object_hook=decode_msgpack_object,
                strict_map_key=False,  # More lenient during unpacking
                raw=False  # Decode bytes to str when possible
            )
            
            # Update statistics
            elapsed = time.time() - start_time
            self._stats.deserialization_count += 1
            self._stats.total_deserialization_time += elapsed
            self._stats.total_bytes_deserialized += len(data)
            
            return result
            
        except (msgpack.exceptions.ExtraData, msgpack.exceptions.UnpackException,
                msgpack.exceptions.UnpackValueError, ValueError, gzip.BadGzipFile) as e:
            self._stats.error_count += 1
            raise DeserializationError(
                f"MessagePack deserialization failed: {str(e)}",
                data=data,
                serializer_type="msgpack",
                original_error=e,
                metadata=metadata
            )
        except Exception as e:
            self._stats.error_count += 1
            raise DeserializationError(
                f"Unexpected MessagePack deserialization error: {str(e)}",
                data=data,
                serializer_type="msgpack",
                original_error=e,
                metadata=metadata
            )
    
    def get_format_name(self) -> str:
        """Get serialization format name."""
        return "msgpack"
    
    def supports_compression(self) -> bool:
        """Check if serializer supports compression."""
        return True
    
    def get_content_type(self) -> str:
        """Get MIME content type."""
        return "application/x-msgpack"
    
    def estimate_serialized_size(self, value: Any) -> int:
        """Estimate serialized size without actually serializing."""
        try:
            # MessagePack is typically more compact than JSON
            # Use a more accurate estimation based on value type
            
            if isinstance(value, (int, float, bool)) or value is None:
                # Primitives are very compact
                return 8  # Conservative estimate
            elif isinstance(value, str):
                # Strings have minimal overhead
                return len(value.encode('utf-8')) + 5
            elif isinstance(value, bytes):
                return len(value) + 5
            elif isinstance(value, (list, tuple)):
                # Collections have array overhead
                base_size = sum(self.estimate_serialized_size(item) for item in value)
                return base_size + len(value) * 2
            elif isinstance(value, dict):
                # Maps have key-value overhead
                base_size = sum(
                    self.estimate_serialized_size(k) + self.estimate_serialized_size(v)
                    for k, v in value.items()
                )
                return base_size + len(value) * 3
            else:
                # Complex objects - conservative estimate
                base_size = sys.getsizeof(value)
            
            # Account for compression if enabled
            if self._use_compression and base_size >= self._compression_threshold:
                # MessagePack often compresses well, assume 35% reduction
                base_size = int(base_size * 0.65)
            
            return base_size
            
        except Exception:
            # Fallback to conservative estimate
            return sys.getsizeof(value)
    
    def can_serialize(self, value: Any) -> bool:
        """Check if value can be serialized."""
        if msgpack is None:
            return False
        
        try:
            # Quick test serialization
            msgpack.packb(value, default=default_encoder)
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
            "content_type": self.get_content_type(),
            "binary_format": True,
            "msgpack_available": msgpack is not None
        }
    
    async def serialize_stream(self, value: Any, chunk_size: int = 8192) -> bytes:
        """Serialize in streaming fashion (fallback to regular serialize)."""
        return self.serialize(value)
    
    async def deserialize_stream(self, data: bytes, chunk_size: int = 8192) -> Any:
        """Deserialize in streaming fashion (fallback to regular deserialize)."""
        return self.deserialize(data)
    
    def configure(self, **options) -> None:
        """Configure serializer options."""
        if 'use_single_float' in options:
            self._use_single_float = options['use_single_float']
        if 'use_bin_type' in options:
            self._use_bin_type = options['use_bin_type']
        if 'strict_map_key' in options:
            self._strict_map_key = options['strict_map_key']
        if 'datetime_format' in options:
            self._datetime_format = options['datetime_format']
        if 'use_compression' in options:
            self._use_compression = options['use_compression']
        if 'compression_level' in options:
            self._compression_level = max(1, min(9, options['compression_level']))
        if 'compression_threshold' in options:
            self._compression_threshold = max(0, options['compression_threshold'])
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "use_single_float": self._use_single_float,
            "use_bin_type": self._use_bin_type,
            "strict_map_key": self._strict_map_key,
            "datetime_format": self._datetime_format,
            "use_compression": self._use_compression,
            "compression_level": self._compression_level,
            "compression_threshold": self._compression_threshold,
            "msgpack_available": msgpack is not None
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
        self._stats = MessagePackSerializerStats()
    
    def is_available(self) -> bool:
        """Check if MessagePack library is available."""
        return msgpack is not None
    
    def get_library_info(self) -> Dict[str, Any]:
        """Get MessagePack library information."""
        if msgpack is None:
            return {
                "available": False,
                "install_command": "pip install msgpack"
            }
        
        return {
            "available": True,
            "version": getattr(msgpack, 'version', 'unknown'),
            "module_path": msgpack.__file__ if hasattr(msgpack, '__file__') else 'unknown'
        }


# Factory function for dependency injection
def create_msgpack_serializer(
    use_compression: bool = False,
    compression_level: int = 6,
    use_single_float: bool = False,
    **options
) -> MessagePackCacheSerializer:
    """Create MessagePack cache serializer with configuration.
    
    Args:
        use_compression: Enable gzip compression
        compression_level: Gzip compression level (1-9)
        use_single_float: Use single precision for floats
        **options: Additional configuration options
        
    Returns:
        Configured MessagePack cache serializer
        
    Raises:
        ImportError: If msgpack library is not available
    """
    return MessagePackCacheSerializer(
        use_compression=use_compression,
        compression_level=compression_level,
        use_single_float=use_single_float,
        **options
    )