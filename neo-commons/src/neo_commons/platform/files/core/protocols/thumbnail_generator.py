"""Thumbnail generator protocol.

ONLY thumbnail generation contract - defines interface for thumbnail
generation implementations supporting images, videos, and documents.

Following maximum separation architecture - one file = one purpose.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO, List, Tuple
from typing_extensions import Protocol, runtime_checkable
from enum import Enum

from ..value_objects.file_id import FileId
from ..value_objects.mime_type import MimeType


class ThumbnailSize(Enum):
    """Standard thumbnail sizes."""
    SMALL = "small"      # 150x150
    MEDIUM = "medium"    # 300x300  
    LARGE = "large"      # 600x600
    CUSTOM = "custom"    # Custom dimensions


class ThumbnailFormat(Enum):
    """Supported thumbnail formats."""
    JPEG = "jpeg"
    PNG = "png" 
    WEBP = "webp"


@runtime_checkable
class ThumbnailGenerator(Protocol):
    """Thumbnail generator protocol.
    
    Defines interface for thumbnail generation implementations with support for:
    - Image thumbnail generation with various sizes
    - Video frame extraction and thumbnails
    - Document preview generation (PDF, Office docs)
    - Batch thumbnail generation
    - Format conversion and optimization
    - Quality control and compression
    """
    
    # Single file thumbnail generation
    async def generate_thumbnail(
        self,
        content: BinaryIO,
        source_mime_type: MimeType,
        thumbnail_size: ThumbnailSize = ThumbnailSize.MEDIUM,
        thumbnail_format: ThumbnailFormat = ThumbnailFormat.JPEG,
        quality: int = 85,
        file_id: Optional[FileId] = None,
        custom_dimensions: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        """Generate thumbnail from file content.
        
        Args:
            content: Binary stream of source file
            source_mime_type: MIME type of source file
            thumbnail_size: Standard thumbnail size or custom
            thumbnail_format: Output thumbnail format
            quality: Compression quality (1-100, higher is better)
            file_id: File identifier for tracking/logging
            custom_dimensions: (width, height) for custom size
        
        Returns:
            Dictionary with generation results:
            - thumbnail_data: Binary thumbnail content
            - thumbnail_format: Actual output format used
            - thumbnail_size_bytes: Size of generated thumbnail
            - dimensions: (width, height) of generated thumbnail
            - generation_duration_ms: Time taken to generate
            - source_dimensions: (width, height) of source (if applicable)
            - compression_ratio: Size reduction ratio
        """
        ...
    
    async def generate_thumbnail_from_path(
        self,
        file_path: str,
        thumbnail_size: ThumbnailSize = ThumbnailSize.MEDIUM,
        thumbnail_format: ThumbnailFormat = ThumbnailFormat.JPEG,
        quality: int = 85,
        file_id: Optional[FileId] = None,
        custom_dimensions: Optional[Tuple[int, int]] = None
    ) -> Dict[str, Any]:
        """Generate thumbnail from file path.
        
        Args:
            file_path: Path to source file
            thumbnail_size: Standard thumbnail size or custom
            thumbnail_format: Output thumbnail format
            quality: Compression quality (1-100)
            file_id: File identifier for tracking/logging
            custom_dimensions: (width, height) for custom size
        
        Returns:
            Same format as generate_thumbnail
        """
        ...
    
    # Multiple thumbnail sizes
    async def generate_multiple_sizes(
        self,
        content: BinaryIO,
        source_mime_type: MimeType,
        sizes: List[ThumbnailSize],
        thumbnail_format: ThumbnailFormat = ThumbnailFormat.JPEG,
        quality: int = 85,
        file_id: Optional[FileId] = None
    ) -> Dict[ThumbnailSize, Dict[str, Any]]:
        """Generate multiple thumbnail sizes from single source.
        
        Args:
            content: Binary stream of source file
            source_mime_type: MIME type of source file
            sizes: List of thumbnail sizes to generate
            thumbnail_format: Output thumbnail format
            quality: Compression quality (1-100)
            file_id: File identifier for tracking/logging
        
        Returns:
            Dictionary mapping sizes to generation results
        """
        ...
    
    # Video-specific operations
    async def generate_video_thumbnail(
        self,
        content: BinaryIO,
        time_offset_seconds: float = 0.0,
        thumbnail_size: ThumbnailSize = ThumbnailSize.MEDIUM,
        thumbnail_format: ThumbnailFormat = ThumbnailFormat.JPEG,
        quality: int = 85,
        file_id: Optional[FileId] = None
    ) -> Dict[str, Any]:
        """Generate thumbnail from video frame.
        
        Args:
            content: Binary stream of video file
            time_offset_seconds: Time offset to extract frame from
            thumbnail_size: Thumbnail size
            thumbnail_format: Output thumbnail format
            quality: Compression quality (1-100)
            file_id: File identifier for tracking/logging
        
        Returns:
            Same format as generate_thumbnail plus:
            - video_duration_seconds: Total video duration
            - frame_time_offset: Actual time offset used
            - video_resolution: (width, height) of source video
        """
        ...
    
    async def generate_video_contact_sheet(
        self,
        content: BinaryIO,
        grid_size: Tuple[int, int] = (3, 3),
        thumbnail_format: ThumbnailFormat = ThumbnailFormat.JPEG,
        quality: int = 85,
        file_id: Optional[FileId] = None
    ) -> Dict[str, Any]:
        """Generate contact sheet with multiple video frames.
        
        Args:
            content: Binary stream of video file
            grid_size: (columns, rows) for contact sheet grid
            thumbnail_format: Output thumbnail format
            quality: Compression quality (1-100)
            file_id: File identifier for tracking/logging
        
        Returns:
            Same format as generate_thumbnail plus:
            - grid_dimensions: (columns, rows) used
            - frame_count: Number of frames included
            - video_duration_seconds: Total video duration
        """
        ...
    
    # Document-specific operations
    async def generate_document_preview(
        self,
        content: BinaryIO,
        source_mime_type: MimeType,
        page_number: int = 1,
        thumbnail_size: ThumbnailSize = ThumbnailSize.LARGE,
        thumbnail_format: ThumbnailFormat = ThumbnailFormat.PNG,
        quality: int = 90,
        file_id: Optional[FileId] = None
    ) -> Dict[str, Any]:
        """Generate preview thumbnail from document page.
        
        Args:
            content: Binary stream of document file
            source_mime_type: MIME type of document
            page_number: Page number to generate preview from (1-based)
            thumbnail_size: Thumbnail size
            thumbnail_format: Output thumbnail format
            quality: Compression quality (1-100)
            file_id: File identifier for tracking/logging
        
        Returns:
            Same format as generate_thumbnail plus:
            - page_count: Total number of pages in document
            - page_number_used: Actual page number used
            - document_dimensions: (width, height) of document page
        """
        ...
    
    async def generate_document_multi_page(
        self,
        content: BinaryIO,
        source_mime_type: MimeType,
        max_pages: int = 5,
        thumbnail_size: ThumbnailSize = ThumbnailSize.MEDIUM,
        thumbnail_format: ThumbnailFormat = ThumbnailFormat.PNG,
        quality: int = 90,
        file_id: Optional[FileId] = None
    ) -> List[Dict[str, Any]]:
        """Generate previews for multiple document pages.
        
        Args:
            content: Binary stream of document file
            source_mime_type: MIME type of document
            max_pages: Maximum number of pages to generate
            thumbnail_size: Thumbnail size
            thumbnail_format: Output thumbnail format
            quality: Compression quality (1-100)
            file_id: File identifier for tracking/logging
        
        Returns:
            List of generation results for each page
        """
        ...
    
    # Batch operations
    async def generate_batch_thumbnails(
        self,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Generate thumbnails for multiple files.
        
        Args:
            files: List of file specifications with content and parameters
        
        Returns:
            Dictionary mapping file identifiers to generation results
        """
        ...
    
    # Format and capability detection
    async def is_supported_format(self, mime_type: MimeType) -> bool:
        """Check if MIME type is supported for thumbnail generation.
        
        Args:
            mime_type: MIME type to check
        
        Returns:
            True if format is supported for thumbnail generation
        """
        ...
    
    async def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get all supported file formats by category.
        
        Returns:
            Dictionary with format categories:
            - images: List of supported image MIME types
            - videos: List of supported video MIME types
            - documents: List of supported document MIME types
        """
        ...
    
    async def get_format_capabilities(self, mime_type: MimeType) -> Dict[str, Any]:
        """Get capabilities for specific format.
        
        Args:
            mime_type: MIME type to check capabilities for
        
        Returns:
            Dictionary with format capabilities:
            - max_dimensions: Maximum supported dimensions
            - supported_sizes: List of supported thumbnail sizes
            - supported_formats: List of output formats available
            - special_features: Format-specific features available
        """
        ...
    
    # Generator configuration and info
    async def get_generator_info(self) -> Dict[str, Any]:
        """Get thumbnail generator information.
        
        Returns:
            Dictionary with generator info:
            - generator_name: Name of thumbnail engine
            - generator_version: Engine version
            - supported_input_formats: Total supported input formats
            - supported_output_formats: Available output formats
            - max_input_size_mb: Maximum input file size
            - max_output_dimensions: Maximum output dimensions
        """
        ...
    
    async def optimize_thumbnail(
        self,
        thumbnail_data: BinaryIO,
        target_size_kb: Optional[int] = None,
        maintain_quality: bool = True
    ) -> Dict[str, Any]:
        """Optimize thumbnail for size/quality balance.
        
        Args:
            thumbnail_data: Binary thumbnail data to optimize
            target_size_kb: Target size in KB (None for automatic)
            maintain_quality: Prioritize quality over size reduction
        
        Returns:
            Dictionary with optimization results:
            - optimized_data: Optimized thumbnail binary data
            - original_size_bytes: Original thumbnail size
            - optimized_size_bytes: Optimized thumbnail size
            - size_reduction_percent: Percentage of size reduction
            - quality_retained_percent: Estimated quality retention
        """
        ...
    
    # Health monitoring
    async def ping(self) -> bool:
        """Health check - verify generator is responsive.
        
        Returns:
            True if generator is healthy and responsive
        """
        ...