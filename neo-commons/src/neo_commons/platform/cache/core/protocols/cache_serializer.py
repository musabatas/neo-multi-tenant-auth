"""Cache serializer protocol.

ONLY serialization contract - defines interface for cache value
serialization with multiple format support.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Optional, Dict
from typing_extensions import Protocol, runtime_checkable


@runtime_checkable
class CacheSerializer(Protocol):
    """Cache serializer protocol.
    
    Defines interface for cache value serialization with support for:
    - Multiple serialization formats (JSON, pickle, msgpack)
    - Type preservation and reconstruction
    - Compression support
    - Metadata handling
    - Performance optimization
    - Error handling and recovery
    """
    
    def serialize(self, value: Any, metadata: Optional[Dict[str, Any]] = None) -> bytes:
        """Serialize value to bytes for cache storage.
        
        Args:
            value: Python object to serialize
            metadata: Optional metadata for serialization hints
            
        Returns:
            Serialized bytes suitable for cache storage
            
        Raises:
            SerializationError: If value cannot be serialized
        """
        ...
    
    def deserialize(self, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> Any:
        """Deserialize bytes back to Python object.
        
        Args:
            data: Serialized bytes from cache storage
            metadata: Optional metadata for deserialization hints
            
        Returns:
            Reconstructed Python object
            
        Raises:
            DeserializationError: If data cannot be deserialized
        """
        ...
    
    def get_format_name(self) -> str:
        """Get serialization format name (e.g., 'json', 'pickle', 'msgpack')."""
        ...
    
    def supports_compression(self) -> bool:
        """Check if serializer supports compression."""
        ...
    
    def get_content_type(self) -> str:
        """Get MIME content type for serialized data."""
        ...
    
    def estimate_serialized_size(self, value: Any) -> int:
        """Estimate serialized size in bytes without actually serializing.
        
        Useful for cache size planning and memory management.
        Returns rough estimate, actual size may vary.
        """
        ...
    
    def can_serialize(self, value: Any) -> bool:
        """Check if value can be serialized by this serializer.
        
        Fast check without actually serializing.
        Useful for serializer selection and validation.
        """
        ...
    
    def get_serialization_metadata(self, value: Any) -> Dict[str, Any]:
        """Get metadata about serialization for the given value.
        
        Returns information like:
        - estimated_size: Estimated serialized size
        - type_info: Type information for deserialization
        - compression_recommended: Whether compression would be beneficial
        - serializer_version: Serializer version for compatibility
        """
        ...
    
    # Optional: Streaming support for large objects
    async def serialize_stream(self, value: Any, chunk_size: int = 8192) -> bytes:
        """Serialize large objects in streaming fashion.
        
        Optional method for handling very large objects.
        Default implementation can fall back to regular serialize().
        """
        ...
    
    async def deserialize_stream(self, data: bytes, chunk_size: int = 8192) -> Any:
        """Deserialize large objects in streaming fashion.
        
        Optional method for handling very large objects.
        Default implementation can fall back to regular deserialize().
        """
        ...
    
    # Configuration and optimization
    def configure(self, **options) -> None:
        """Configure serializer options.
        
        Common options might include:
        - compression_level: Compression level (if supported)
        - ensure_ascii: For JSON serializers
        - protocol_version: For pickle serializers
        - use_single_float: For msgpack serializers
        """
        ...
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current serializer configuration."""
        ...
    
    def reset_configuration(self) -> None:
        """Reset serializer to default configuration."""
        ...
    
    # Performance and monitoring
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics.
        
        Returns metrics like:
        - serialization_count: Number of serializations performed
        - deserialization_count: Number of deserializations performed
        - total_serialization_time: Total time spent serializing
        - total_deserialization_time: Total time spent deserializing
        - average_serialization_time: Average serialization time
        - average_deserialization_time: Average deserialization time
        - total_bytes_serialized: Total bytes produced
        - total_bytes_deserialized: Total bytes consumed
        - compression_ratio: Average compression ratio (if applicable)
        """
        ...
    
    def reset_performance_stats(self) -> None:
        """Reset performance statistics counters."""
        ...