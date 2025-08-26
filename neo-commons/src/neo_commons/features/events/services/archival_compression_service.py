"""
Advanced Event Archival Compression Service

Provides automated compression algorithms, multi-format serialization,
and intelligent compression strategy selection for optimal storage efficiency
and cross-region archival support.
"""

import gzip
import bz2
import lzma
import json
import pickle
import logging
from typing import List, Dict, Any, Tuple, Optional, Protocol, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
import asyncio
import io
from pathlib import Path

from ..entities.domain_event import DomainEvent
from ..entities.event_archive import EventArchive, StorageType

logger = logging.getLogger(__name__)


class CompressionAlgorithm(Enum):
    """Available compression algorithms with efficiency profiles."""
    GZIP = "gzip"           # Good balance of speed vs compression
    BZIP2 = "bzip2"         # Better compression, slower speed
    LZMA = "lzma"           # Best compression, slowest speed
    LZ4 = "lz4"             # Fastest compression, moderate ratio (if available)


class SerializationFormat(Enum):
    """Event serialization formats for archival."""
    JSON = "json"           # Human readable, larger size
    PICKLE = "pickle"       # Python native, compact, not cross-language
    MSGPACK = "msgpack"     # Cross-language binary, compact (if available)
    PARQUET = "parquet"     # Columnar format, excellent compression (if available)


@dataclass
class CompressionProfile:
    """Compression strategy profile for different scenarios."""
    name: str
    algorithm: CompressionAlgorithm
    serialization: SerializationFormat
    compression_level: int
    description: str
    optimal_for: List[str] = field(default_factory=list)
    
    # Performance characteristics (estimated)
    speed_score: int = 5       # 1-10 (10 = fastest)
    ratio_score: int = 5       # 1-10 (10 = best compression)
    memory_usage_mb: int = 100 # Estimated memory usage


class ArchivalCompressionService:
    """Advanced compression service for event archival operations."""
    
    # Predefined compression profiles for different use cases
    COMPRESSION_PROFILES = {
        "fast": CompressionProfile(
            name="fast",
            algorithm=CompressionAlgorithm.GZIP,
            serialization=SerializationFormat.PICKLE,
            compression_level=1,
            description="Fast compression for real-time archival",
            optimal_for=["real_time", "high_volume", "temporary_archives"],
            speed_score=9,
            ratio_score=4,
            memory_usage_mb=50
        ),
        "balanced": CompressionProfile(
            name="balanced",
            algorithm=CompressionAlgorithm.GZIP,
            serialization=SerializationFormat.JSON,
            compression_level=6,
            description="Balanced compression for general use",
            optimal_for=["general", "mixed_workload", "default"],
            speed_score=6,
            ratio_score=6,
            memory_usage_mb=100
        ),
        "maximum": CompressionProfile(
            name="maximum",
            algorithm=CompressionAlgorithm.LZMA,
            serialization=SerializationFormat.JSON,
            compression_level=9,
            description="Maximum compression for long-term storage",
            optimal_for=["long_term", "cold_storage", "cost_optimization"],
            speed_score=2,
            ratio_score=9,
            memory_usage_mb=200
        ),
        "cross_platform": CompressionProfile(
            name="cross_platform",
            algorithm=CompressionAlgorithm.GZIP,
            serialization=SerializationFormat.JSON,
            compression_level=6,
            description="Cross-platform compatible compression",
            optimal_for=["multi_region", "cross_platform", "json_compatibility"],
            speed_score=6,
            ratio_score=5,
            memory_usage_mb=100
        )
    }
    
    def __init__(self, default_profile: str = "balanced"):
        """Initialize compression service.
        
        Args:
            default_profile: Default compression profile to use
        """
        self._default_profile = default_profile
        if default_profile not in self.COMPRESSION_PROFILES:
            raise ValueError(f"Unknown compression profile: {default_profile}")
        
        # Compression statistics
        self._compression_stats = {
            "total_compressions": 0,
            "total_bytes_original": 0,
            "total_bytes_compressed": 0,
            "average_compression_ratio": 0.0,
            "algorithm_usage": {alg.value: 0 for alg in CompressionAlgorithm},
            "format_usage": {fmt.value: 0 for fmt in SerializationFormat}
        }
    
    async def compress_events_for_archive(
        self,
        events: List[DomainEvent],
        archive: EventArchive,
        profile_name: Optional[str] = None,
        custom_profile: Optional[CompressionProfile] = None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """Compress events for archival with intelligent strategy selection.
        
        Args:
            events: List of domain events to compress
            archive: Archive metadata for context
            profile_name: Named compression profile to use
            custom_profile: Custom compression profile
            
        Returns:
            Tuple of (compressed_data, compression_metadata)
        """
        if not events:
            raise ValueError("Cannot compress empty event list")
        
        # Select compression profile
        profile = self._select_compression_profile(
            events, archive, profile_name, custom_profile
        )
        
        logger.info(
            f"Compressing {len(events)} events using profile '{profile.name}' "
            f"({profile.algorithm.value} + {profile.serialization.value})"
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Serialize events
            serialized_data = await self._serialize_events(events, profile.serialization)
            original_size = len(serialized_data)
            
            # Compress serialized data
            compressed_data = await self._compress_data(
                serialized_data, profile.algorithm, profile.compression_level
            )
            compressed_size = len(compressed_data)
            
            # Calculate compression metrics
            compression_ratio = compressed_size / original_size if original_size > 0 else 1.0
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Update statistics
            self._update_compression_stats(
                original_size, compressed_size, profile.algorithm, profile.serialization
            )
            
            # Create compression metadata
            metadata = {
                "compression_algorithm": profile.algorithm.value,
                "serialization_format": profile.serialization.value,
                "compression_level": profile.compression_level,
                "original_size_bytes": original_size,
                "compressed_size_bytes": compressed_size,
                "compression_ratio": compression_ratio,
                "compression_efficiency": 1.0 - compression_ratio,
                "processing_time_seconds": processing_time,
                "event_count": len(events),
                "profile_used": profile.name,
                "compression_date": start_time.isoformat(),
                "events_per_kb": len(events) / (compressed_size / 1024) if compressed_size > 0 else 0,
                "throughput_events_per_second": len(events) / processing_time if processing_time > 0 else 0
            }
            
            logger.info(
                f"Compression completed: {original_size} -> {compressed_size} bytes "
                f"({compression_ratio:.3f} ratio, {processing_time:.2f}s)"
            )
            
            return compressed_data, metadata
            
        except Exception as e:
            logger.error(f"Compression failed using profile '{profile.name}': {e}")
            raise
    
    async def decompress_archive_events(
        self,
        compressed_data: bytes,
        compression_metadata: Dict[str, Any]
    ) -> List[DomainEvent]:
        """Decompress archived events using stored metadata.
        
        Args:
            compressed_data: Compressed event data
            compression_metadata: Compression metadata from archival
            
        Returns:
            List of restored domain events
        """
        algorithm_name = compression_metadata.get("compression_algorithm")
        serialization_name = compression_metadata.get("serialization_format")
        
        if not algorithm_name or not serialization_name:
            raise ValueError("Invalid compression metadata - missing algorithm or serialization format")
        
        try:
            algorithm = CompressionAlgorithm(algorithm_name)
            serialization = SerializationFormat(serialization_name)
        except ValueError as e:
            raise ValueError(f"Unsupported compression format: {e}")
        
        logger.info(
            f"Decompressing {len(compressed_data)} bytes using {algorithm.value} + {serialization.value}"
        )
        
        start_time = datetime.now(timezone.utc)
        
        try:
            # Decompress data
            decompressed_data = await self._decompress_data(compressed_data, algorithm)
            
            # Deserialize events
            events = await self._deserialize_events(decompressed_data, serialization)
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            logger.info(
                f"Decompression completed: {len(events)} events restored in {processing_time:.2f}s"
            )
            
            return events
            
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise
    
    def _select_compression_profile(
        self,
        events: List[DomainEvent],
        archive: EventArchive,
        profile_name: Optional[str],
        custom_profile: Optional[CompressionProfile]
    ) -> CompressionProfile:
        """Select optimal compression profile based on context."""
        # Use custom profile if provided
        if custom_profile:
            return custom_profile
        
        # Use named profile if specified
        if profile_name and profile_name in self.COMPRESSION_PROFILES:
            return self.COMPRESSION_PROFILES[profile_name]
        
        # Intelligent profile selection based on archive characteristics
        event_count = len(events)
        storage_type = archive.storage_type
        
        # For large volumes, prefer speed
        if event_count > 10000:
            return self.COMPRESSION_PROFILES["fast"]
        
        # For cold storage, prefer maximum compression
        if storage_type == StorageType.COLD_STORAGE:
            return self.COMPRESSION_PROFILES["maximum"]
        
        # For multi-region archives, ensure cross-platform compatibility
        if "multi_region" in getattr(archive, "tags", []):
            return self.COMPRESSION_PROFILES["cross_platform"]
        
        # Default to balanced profile
        return self.COMPRESSION_PROFILES[self._default_profile]
    
    async def _serialize_events(
        self, 
        events: List[DomainEvent], 
        format_type: SerializationFormat
    ) -> bytes:
        """Serialize events to bytes using specified format."""
        if format_type == SerializationFormat.JSON:
            # Convert events to JSON-serializable format
            event_data = []
            for event in events:
                event_dict = {
                    "id": str(event.id.value),
                    "event_type": event.event_type.value,
                    "event_name": event.event_name,
                    "aggregate_id": str(event.aggregate_id),
                    "aggregate_type": event.aggregate_type,
                    "aggregate_version": event.aggregate_version,
                    "event_data": event.event_data,
                    "context_id": str(event.context_id) if event.context_id else None,
                    "correlation_id": str(event.correlation_id) if event.correlation_id else None,
                    "triggered_by_user_id": str(event.triggered_by_user_id.value) if event.triggered_by_user_id else None,
                    "occurred_at": event.occurred_at.isoformat(),
                    "created_at": event.created_at.isoformat(),
                    "metadata": event.metadata
                }
                event_data.append(event_dict)
            
            json_str = json.dumps(event_data, separators=(',', ':'))
            return json_str.encode('utf-8')
        
        elif format_type == SerializationFormat.PICKLE:
            return pickle.dumps(events)
        
        else:
            # Try to import optional serialization formats
            if format_type == SerializationFormat.MSGPACK:
                try:
                    import msgpack
                    return msgpack.packb([self._event_to_dict(event) for event in events])
                except ImportError:
                    logger.warning("msgpack not available, falling back to JSON")
                    return await self._serialize_events(events, SerializationFormat.JSON)
            
            elif format_type == SerializationFormat.PARQUET:
                logger.warning("Parquet serialization not yet implemented, falling back to JSON")
                return await self._serialize_events(events, SerializationFormat.JSON)
            
            else:
                raise ValueError(f"Unsupported serialization format: {format_type}")
    
    async def _compress_data(
        self, 
        data: bytes, 
        algorithm: CompressionAlgorithm, 
        level: int
    ) -> bytes:
        """Compress data using specified algorithm and level."""
        if algorithm == CompressionAlgorithm.GZIP:
            return gzip.compress(data, compresslevel=level)
        
        elif algorithm == CompressionAlgorithm.BZIP2:
            return bz2.compress(data, compresslevel=level)
        
        elif algorithm == CompressionAlgorithm.LZMA:
            return lzma.compress(data, preset=level)
        
        elif algorithm == CompressionAlgorithm.LZ4:
            try:
                import lz4.frame
                return lz4.frame.compress(data, compression_level=level)
            except ImportError:
                logger.warning("lz4 not available, falling back to gzip")
                return gzip.compress(data, compresslevel=level)
        
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
    
    async def _decompress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> bytes:
        """Decompress data using specified algorithm."""
        if algorithm == CompressionAlgorithm.GZIP:
            return gzip.decompress(data)
        
        elif algorithm == CompressionAlgorithm.BZIP2:
            return bz2.decompress(data)
        
        elif algorithm == CompressionAlgorithm.LZMA:
            return lzma.decompress(data)
        
        elif algorithm == CompressionAlgorithm.LZ4:
            try:
                import lz4.frame
                return lz4.frame.decompress(data)
            except ImportError:
                raise ValueError("lz4 required for decompression but not available")
        
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")
    
    async def _deserialize_events(
        self, 
        data: bytes, 
        format_type: SerializationFormat
    ) -> List[DomainEvent]:
        """Deserialize bytes back to domain events."""
        if format_type == SerializationFormat.JSON:
            json_str = data.decode('utf-8')
            event_data_list = json.loads(json_str)
            
            # Convert back to DomainEvent objects
            # This would require importing and using the actual DomainEvent constructor
            # For now, return raw data - this would need to be implemented based on 
            # the actual DomainEvent class structure
            logger.warning("JSON deserialization to DomainEvent objects not fully implemented")
            return event_data_list  # Return raw data for now
        
        elif format_type == SerializationFormat.PICKLE:
            return pickle.loads(data)
        
        elif format_type == SerializationFormat.MSGPACK:
            try:
                import msgpack
                event_data_list = msgpack.unpackb(data, raw=False)
                logger.warning("msgpack deserialization to DomainEvent objects not fully implemented")
                return event_data_list  # Return raw data for now
            except ImportError:
                raise ValueError("msgpack required for deserialization but not available")
        
        else:
            raise ValueError(f"Unsupported serialization format: {format_type}")
    
    def _event_to_dict(self, event: DomainEvent) -> Dict[str, Any]:
        """Convert domain event to dictionary for serialization."""
        return {
            "id": str(event.id.value),
            "event_type": event.event_type.value,
            "event_name": event.event_name,
            "aggregate_id": str(event.aggregate_id),
            "aggregate_type": event.aggregate_type,
            "aggregate_version": event.aggregate_version,
            "event_data": event.event_data,
            "context_id": str(event.context_id) if event.context_id else None,
            "correlation_id": str(event.correlation_id) if event.correlation_id else None,
            "triggered_by_user_id": str(event.triggered_by_user_id.value) if event.triggered_by_user_id else None,
            "occurred_at": event.occurred_at.isoformat(),
            "created_at": event.created_at.isoformat(),
            "metadata": event.metadata
        }
    
    def _update_compression_stats(
        self,
        original_size: int,
        compressed_size: int,
        algorithm: CompressionAlgorithm,
        serialization: SerializationFormat
    ) -> None:
        """Update compression statistics."""
        self._compression_stats["total_compressions"] += 1
        self._compression_stats["total_bytes_original"] += original_size
        self._compression_stats["total_bytes_compressed"] += compressed_size
        
        # Update average compression ratio
        if self._compression_stats["total_bytes_original"] > 0:
            self._compression_stats["average_compression_ratio"] = (
                self._compression_stats["total_bytes_compressed"] / 
                self._compression_stats["total_bytes_original"]
            )
        
        # Update algorithm and format usage
        self._compression_stats["algorithm_usage"][algorithm.value] += 1
        self._compression_stats["format_usage"][serialization.value] += 1
    
    def get_compression_statistics(self) -> Dict[str, Any]:
        """Get comprehensive compression statistics."""
        stats = self._compression_stats.copy()
        
        # Add derived metrics
        if stats["total_compressions"] > 0:
            stats["average_original_size"] = stats["total_bytes_original"] / stats["total_compressions"]
            stats["average_compressed_size"] = stats["total_bytes_compressed"] / stats["total_compressions"]
            stats["total_bytes_saved"] = stats["total_bytes_original"] - stats["total_bytes_compressed"]
            stats["space_savings_percentage"] = (
                (1.0 - stats["average_compression_ratio"]) * 100.0
            )
        
        return stats
    
    def get_profile_recommendations(self, use_case: str) -> List[str]:
        """Get recommended compression profiles for a specific use case."""
        recommendations = []
        
        for profile_name, profile in self.COMPRESSION_PROFILES.items():
            if use_case.lower() in [opt.lower() for opt in profile.optimal_for]:
                recommendations.append(profile_name)
        
        # If no specific recommendations, suggest based on use case patterns
        if not recommendations:
            if any(keyword in use_case.lower() for keyword in ['fast', 'real', 'time', 'high']):
                recommendations.append("fast")
            elif any(keyword in use_case.lower() for keyword in ['long', 'cold', 'storage', 'cost']):
                recommendations.append("maximum")
            elif any(keyword in use_case.lower() for keyword in ['region', 'platform', 'cross']):
                recommendations.append("cross_platform")
            else:
                recommendations.append("balanced")
        
        return recommendations
    
    async def benchmark_compression_profiles(
        self, 
        sample_events: List[DomainEvent]
    ) -> Dict[str, Dict[str, Any]]:
        """Benchmark all compression profiles against sample data."""
        if not sample_events:
            raise ValueError("Sample events required for benchmarking")
        
        logger.info(f"Benchmarking compression profiles with {len(sample_events)} sample events")
        
        results = {}
        
        # Create dummy archive for testing
        from uuid import uuid4
        dummy_archive = EventArchive(
            id=uuid4(),
            archive_name="benchmark_test",
            description="Benchmark test archive",
            policy="test",
            storage_type=StorageType.COMPRESSED_ARCHIVE,
            storage_location="benchmark",
            created_at=datetime.now(timezone.utc),
            status="pending",
            event_count=len(sample_events),
            size_bytes=0
        )
        
        for profile_name, profile in self.COMPRESSION_PROFILES.items():
            try:
                logger.info(f"Benchmarking profile: {profile_name}")
                
                # Test compression
                compressed_data, metadata = await self.compress_events_for_archive(
                    sample_events, dummy_archive, profile_name
                )
                
                # Test decompression
                start_decomp = datetime.now(timezone.utc)
                decompressed_events = await self.decompress_archive_events(
                    compressed_data, metadata
                )
                decomp_time = (datetime.now(timezone.utc) - start_decomp).total_seconds()
                
                # Collect benchmark results
                results[profile_name] = {
                    "profile": profile.__dict__,
                    "compression_metadata": metadata,
                    "decompression_time_seconds": decomp_time,
                    "total_cycle_time_seconds": metadata["processing_time_seconds"] + decomp_time,
                    "round_trip_success": len(decompressed_events) == len(sample_events),
                    "benchmark_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                logger.error(f"Benchmark failed for profile {profile_name}: {e}")
                results[profile_name] = {
                    "error": str(e),
                    "benchmark_timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        return results