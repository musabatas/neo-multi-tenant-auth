"""Virus scanner protocol.

ONLY virus scanning contract - defines interface for virus scanning
implementations with support for various scanning engines.

Following maximum separation architecture - one file = one purpose.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO, List
from typing_extensions import Protocol, runtime_checkable
from datetime import datetime

from ..value_objects.file_id import FileId
from ..value_objects.checksum import Checksum


@runtime_checkable
class VirusScanner(Protocol):
    """Virus scanner protocol.
    
    Defines interface for virus scanning implementations with support for:
    - File content scanning from streams or files
    - Batch scanning for efficiency
    - Real-time scanning integration
    - Scanner health monitoring
    - Signature updates and versioning
    - Quarantine management
    """
    
    # Single file scanning
    async def scan_file_content(
        self,
        content: BinaryIO,
        filename: Optional[str] = None,
        file_id: Optional[FileId] = None
    ) -> Dict[str, Any]:
        """Scan file content for viruses and malware.
        
        Args:
            content: Binary stream of file content to scan
            filename: Original filename (helps with detection)
            file_id: File identifier for tracking/logging
        
        Returns:
            Dictionary with scan results:
            - is_clean: Boolean indicating if file is clean
            - threat_found: Boolean indicating if threats detected
            - threat_names: List of threat names found
            - threat_types: List of threat types (virus, malware, trojan, etc.)
            - scanner_engine: Name of scanning engine used
            - scanner_version: Version of scanner
            - signature_version: Version of virus signatures
            - scan_duration_ms: Time taken for scan
            - quarantine_id: Quarantine identifier if threats found
        """
        ...
    
    async def scan_file_by_path(
        self,
        file_path: str,
        file_id: Optional[FileId] = None
    ) -> Dict[str, Any]:
        """Scan file at specified path.
        
        Args:
            file_path: Path to file to scan
            file_id: File identifier for tracking/logging
        
        Returns:
            Same format as scan_file_content
        """
        ...
    
    async def scan_file_by_checksum(
        self,
        checksum: Checksum,
        file_id: Optional[FileId] = None
    ) -> Dict[str, Any]:
        """Scan file by checksum lookup (if supported).
        
        Args:
            checksum: File checksum for lookup
            file_id: File identifier for tracking/logging
        
        Returns:
            Same format as scan_file_content, or None if checksum not in database
        """
        ...
    
    # Batch scanning operations
    async def scan_multiple_files(
        self,
        files: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Scan multiple files in batch.
        
        Args:
            files: List of file specifications with content/path/checksum
        
        Returns:
            Dictionary mapping file identifiers to scan results
        """
        ...
    
    async def scan_directory(
        self,
        directory_path: str,
        recursive: bool = True,
        file_patterns: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Scan all files in directory.
        
        Args:
            directory_path: Path to directory to scan
            recursive: Whether to scan subdirectories
            file_patterns: Glob patterns for files to include
        
        Returns:
            Dictionary mapping file paths to scan results
        """
        ...
    
    # Real-time scanning
    async def start_real_time_scanning(
        self,
        watch_directories: List[str],
        callback_url: Optional[str] = None
    ) -> str:
        """Start real-time file system monitoring.
        
        Args:
            watch_directories: Directories to monitor
            callback_url: URL to notify of scan results
        
        Returns:
            Session identifier for real-time scanning
        """
        ...
    
    async def stop_real_time_scanning(self, session_id: str) -> bool:
        """Stop real-time file system monitoring.
        
        Args:
            session_id: Real-time scanning session to stop
        
        Returns:
            True if session was stopped successfully
        """
        ...
    
    # Quarantine management
    async def quarantine_file(
        self,
        file_path: str,
        threat_name: str,
        file_id: Optional[FileId] = None
    ) -> str:
        """Move infected file to quarantine.
        
        Args:
            file_path: Path to infected file
            threat_name: Name of detected threat
            file_id: File identifier for tracking
        
        Returns:
            Quarantine identifier for future reference
        """
        ...
    
    async def list_quarantined_files(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """List files currently in quarantine.
        
        Args:
            start_date: Filter quarantined files from this date
            end_date: Filter quarantined files to this date
        
        Returns:
            List of quarantined file information
        """
        ...
    
    async def restore_quarantined_file(self, quarantine_id: str) -> bool:
        """Restore file from quarantine (if confirmed clean).
        
        Args:
            quarantine_id: Quarantine identifier
        
        Returns:
            True if file was restored successfully
        """
        ...
    
    async def delete_quarantined_file(self, quarantine_id: str) -> bool:
        """Permanently delete quarantined file.
        
        Args:
            quarantine_id: Quarantine identifier
        
        Returns:
            True if file was deleted successfully
        """
        ...
    
    # Scanner management and configuration
    async def update_virus_signatures(self) -> Dict[str, Any]:
        """Update virus signature database.
        
        Returns:
            Dictionary with update results:
            - update_successful: Boolean indicating success
            - previous_version: Previous signature version
            - new_version: New signature version
            - signatures_added: Number of new signatures
            - update_duration_ms: Time taken for update
        """
        ...
    
    async def get_scanner_info(self) -> Dict[str, Any]:
        """Get scanner engine information.
        
        Returns:
            Dictionary with scanner info:
            - scanner_name: Name of scanning engine
            - scanner_version: Engine version
            - signature_version: Current signature database version
            - last_signature_update: Last signature update timestamp
            - supported_formats: List of supported file formats
            - max_file_size_mb: Maximum scannable file size
        """
        ...
    
    async def get_scan_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get scanning statistics.
        
        Args:
            start_date: Statistics from this date
            end_date: Statistics to this date
        
        Returns:
            Dictionary with statistics:
            - total_scans: Total number of scans performed
            - clean_files: Number of clean files
            - infected_files: Number of infected files
            - threats_by_type: Breakdown of threats by type
            - average_scan_time_ms: Average scan duration
            - largest_file_scanned_mb: Size of largest file scanned
        """
        ...
    
    # Health monitoring
    async def ping(self) -> bool:
        """Health check - verify scanner is responsive.
        
        Returns:
            True if scanner is healthy and responsive
        """
        ...
    
    async def test_scan(self) -> Dict[str, Any]:
        """Perform test scan with EICAR test file.
        
        Returns:
            Dictionary with test results confirming scanner is working
        """
        ...