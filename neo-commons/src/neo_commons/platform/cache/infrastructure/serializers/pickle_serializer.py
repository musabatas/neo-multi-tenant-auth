"""Pickle cache serializer.

ONLY pickle serialization - implements pickle serialization for cache values
with protocol version control and compression support.

Following maximum separation architecture - one file = one purpose.
"""

import pickle
import gzip
import time
import sys
from dataclasses import dataclass
from typing import Any, Optional, Dict

from ...core.exceptions.serialization_error import SerializationError
from ...core.exceptions.deserialization_error import DeserializationError


@dataclass
class PickleSerializerStats:
    """Pickle serializer performance statistics."""
    
    serialization_count: int = 0
    deserialization_count: int = 0
    total_serialization_time: float = 0.0
    total_deserialization_time: float = 0.0
    total_bytes_serialized: int = 0
    total_bytes_deserialized: int = 0
    compression_ratio: float = 0.0
    error_count: int = 0


class PickleCacheSerializer:
    """Pickle cache serializer with protocol version control and compression.
    
    Features:
    - Pickle serialization with configurable protocol version
    - Optional gzip compression for large objects
    - Comprehensive Python object support
    - Performance monitoring and statistics
    - Security considerations for trusted data only
    """
    
    def __init__(
        self,
        protocol: int = pickle.HIGHEST_PROTOCOL,
        use_compression: bool = False,
        compression_level: int = 6,
        compression_threshold: int = 1024,  # Compress if > 1KB
        fix_imports: bool = True,
        buffer_callback: Optional[Any] = None
    ):
        """Initialize pickle serializer.
        
        Args:
            protocol: Pickle protocol version (0-5)
            use_compression: Enable gzip compression
            compression_level: Gzip compression level (1-9)
            compression_threshold: Minimum size for compression
            fix_imports: Fix Python 2 vs 3 imports
            buffer_callback: Buffer callback for out-of-band data
        """
        # Validate protocol version
        if protocol < 0 or protocol > pickle.HIGHEST_PROTOCOL:
            protocol = pickle.HIGHEST_PROTOCOL
        
        self._protocol = protocol
        self._use_compression = use_compression
        self._compression_level = max(1, min(9, compression_level))
        self._compression_threshold = max(0, compression_threshold)
        self._fix_imports = fix_imports
        self._buffer_callback = buffer_callback
        self._stats = PickleSerializerStats()
    
    def serialize(self, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bytes:
        """Serialize value to pickle bytes."""
        start_time = time.time()
        
        try:
            # Serialize with pickle
            pickle_bytes = pickle.dumps(
                value,
                protocol=self._protocol,
                fix_imports=self._fix_imports,
                buffer_callback=self._buffer_callback
            )
            
            # Apply compression if enabled and beneficial
            if (self._use_compression and 
                len(pickle_bytes) >= self._compression_threshold):
                compressed = gzip.compress(pickle_bytes, compresslevel=self._compression_level)
                # Only use compression if it actually reduces size
                if len(compressed) < len(pickle_bytes):
                    result_bytes = b'GZIP:' + compressed
                    compression_ratio = len(pickle_bytes) / len(result_bytes)
                    self._stats.compression_ratio = (
                        (self._stats.compression_ratio * self._stats.serialization_count + compression_ratio) /
                        (self._stats.serialization_count + 1)
                    )
                else:
                    result_bytes = pickle_bytes
            else:
                result_bytes = pickle_bytes
            
            # Update statistics
            elapsed = time.time() - start_time
            self._stats.serialization_count += 1
            self._stats.total_serialization_time += elapsed
            self._stats.total_bytes_serialized += len(result_bytes)
            
            return result_bytes
            
        except (pickle.PickleError, TypeError, AttributeError, ValueError) as e:
            self._stats.error_count += 1
            raise SerializationError(
                f"Pickle serialization failed: {str(e)}",
                value=value,
                serializer_type="pickle",
                original_error=e,
                metadata=metadata
            )
        except Exception as e:
            self._stats.error_count += 1
            raise SerializationError(
                f"Unexpected pickle serialization error: {str(e)}",
                value=value,
                serializer_type="pickle",
                original_error=e,
                metadata=metadata
            )
    
    def deserialize(self, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Deserialize pickle bytes back to Python object."""
        start_time = time.time()
        
        try:
            # Check for compression
            if data.startswith(b'GZIP:'):
                pickle_bytes = gzip.decompress(data[5:])  # Remove 'GZIP:' prefix
            else:
                pickle_bytes = data
            
            # Deserialize with pickle
            result = pickle.loads(
                pickle_bytes,
                fix_imports=self._fix_imports,
                encoding='bytes',  # Use bytes encoding for safety
                errors='strict'
            )
            
            # Update statistics
            elapsed = time.time() - start_time
            self._stats.deserialization_count += 1
            self._stats.total_deserialization_time += elapsed
            self._stats.total_bytes_deserialized += len(data)
            
            return result
            
        except (pickle.PickleError, EOFError, AttributeError, ImportError, 
                IndexError, ValueError, gzip.BadGzipFile) as e:
            self._stats.error_count += 1
            raise DeserializationError(
                f"Pickle deserialization failed: {str(e)}",
                data=data,
                serializer_type="pickle",
                original_error=e,
                metadata=metadata
            )
        except Exception as e:
            self._stats.error_count += 1
            raise DeserializationError(
                f"Unexpected pickle deserialization error: {str(e)}",
                data=data,
                serializer_type="pickle",
                original_error=e,
                metadata=metadata
            )
    
    def get_format_name(self) -> str:
        """Get serialization format name."""
        return "pickle"
    
    def supports_compression(self) -> bool:
        """Check if serializer supports compression."""
        return True
    
    def get_content_type(self) -> str:
        """Get MIME content type."""
        return "application/x-pickle"
    
    def estimate_serialized_size(self, value: Any) -> int:
        """Estimate serialized size without actually serializing."""
        try:
            # Use sys.getsizeof as base estimate
            # Pickle typically adds some overhead
            base_size = sys.getsizeof(value)
            
            # Add pickle overhead estimation based on object complexity
            if hasattr(value, '__dict__'):
                # Objects with attributes have more overhead
                overhead_factor = 1.5
            elif isinstance(value, (list, tuple, dict, set)):
                # Collections have moderate overhead
                overhead_factor = 1.3
            else:
                # Simple types have minimal overhead
                overhead_factor = 1.1
            
            estimated_size = int(base_size * overhead_factor)
            
            # Account for compression if enabled
            if self._use_compression and estimated_size >= self._compression_threshold:
                # Pickle data often compresses well, assume 40% reduction
                estimated_size = int(estimated_size * 0.6)
            
            return estimated_size
            
        except Exception:
            # Fallback to very conservative estimate
            return sys.getsizeof(value) * 2
    
    def can_serialize(self, value: Any) -> bool:
        """Check if value can be serialized."""
        try:
            # Quick test serialization with highest protocol
            pickle.dumps(value, protocol=self._protocol)
            return True
        except Exception:
            return False
    
    def get_serialization_metadata(self, value: Any) -> Dict[str, Any]:
        """Get serialization metadata."""
        return {
            "estimated_size": self.estimate_serialized_size(value),
            "type_info": f"{type(value).__module__}.{type(value).__name__}",
            "compression_recommended": (
                self.estimate_serialized_size(value) >= self._compression_threshold
            ),
            "serializer_version": "1.0",
            "protocol_version": self._protocol,
            "format": self.get_format_name(),
            "content_type": self.get_content_type(),
            "security_note": "Pickle data should only come from trusted sources"
        }
    
    async def serialize_stream(self, value: Any, chunk_size: int = 8192) -> bytes:
        """Serialize in streaming fashion (fallback to regular serialize)."""
        return self.serialize(value)
    
    async def deserialize_stream(self, data: bytes, chunk_size: int = 8192) -> Any:
        """Deserialize in streaming fashion (fallback to regular deserialize)."""
        return self.deserialize(data)
    
    def configure(self, **options) -> None:
        """Configure serializer options."""
        if 'protocol' in options:
            protocol = options['protocol']
            if 0 <= protocol <= pickle.HIGHEST_PROTOCOL:
                self._protocol = protocol
        if 'use_compression' in options:
            self._use_compression = options['use_compression']
        if 'compression_level' in options:
            self._compression_level = max(1, min(9, options['compression_level']))
        if 'compression_threshold' in options:
            self._compression_threshold = max(0, options['compression_threshold'])
        if 'fix_imports' in options:
            self._fix_imports = options['fix_imports']
        if 'buffer_callback' in options:
            self._buffer_callback = options['buffer_callback']
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "protocol": self._protocol,
            "use_compression": self._use_compression,
            "compression_level": self._compression_level,
            "compression_threshold": self._compression_threshold,
            "fix_imports": self._fix_imports,
            "buffer_callback": self._buffer_callback is not None,
            "highest_protocol": pickle.HIGHEST_PROTOCOL
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
            "error_count": self._stats.error_count,
            "protocol_version": self._protocol
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
        self._stats = PickleSerializerStats()
    
    def get_security_warnings(self) -> list[str]:
        """Get security warnings for pickle usage."""
        return [
            "Pickle can execute arbitrary code during deserialization",
            "Only deserialize pickle data from trusted sources",
            "Consider using JSON or MessagePack for untrusted data",
            "Validate data source before unpickling",
            "Monitor for suspicious pickle operations"
        ]
    
    def is_safe_for_untrusted_data(self) -> bool:
        """Check if serializer is safe for untrusted data."""
        return False  # Pickle is never safe for untrusted data


# Factory function for dependency injection
def create_pickle_serializer(
    protocol: Optional[int] = None,
    use_compression: bool = False,
    compression_level: int = 6,
    **options
) -> PickleCacheSerializer:
    """Create pickle cache serializer with configuration.
    
    Args:
        protocol: Pickle protocol version (None = highest)
        use_compression: Enable gzip compression
        compression_level: Gzip compression level (1-9)
        **options: Additional configuration options
        
    Returns:
        Configured pickle cache serializer
    """
    if protocol is None:
        protocol = pickle.HIGHEST_PROTOCOL
    
    return PickleCacheSerializer(
        protocol=protocol,
        use_compression=use_compression,
        compression_level=compression_level,
        **options
    )