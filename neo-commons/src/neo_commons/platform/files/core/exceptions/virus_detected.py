"""Virus detected exception for file management platform infrastructure.

ONLY virus detected - represents when virus scanning detects malicious content
in an uploaded file.

Following maximum separation architecture - one file = one purpose.
"""

from typing import Any, Dict, Optional, List

from .....core.exceptions import SecurityError
from ..value_objects import FileId, Checksum


class VirusDetected(SecurityError):
    """Raised when virus scanning detects malicious content in a file.
    
    This exception represents failures when virus scanning systems
    detect potentially malicious content in uploaded files.
    """
    
    def __init__(
        self,
        message: str,
        file_id: Optional[FileId] = None,
        filename: Optional[str] = None,
        checksum: Optional[Checksum] = None,
        virus_name: Optional[str] = None,
        scanner_name: Optional[str] = None,
        scanner_version: Optional[str] = None,
        scan_engine: Optional[str] = None,
        threat_types: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        quarantine_location: Optional[str] = None,
        scan_duration_ms: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize virus detected exception.
        
        Args:
            message: Human-readable error message
            file_id: ID of the infected file
            filename: Original filename of the infected file
            checksum: Checksum of the infected file for tracking
            virus_name: Name/signature of the detected virus
            scanner_name: Name of the virus scanner that detected the threat
            scanner_version: Version of the virus scanner
            scan_engine: Scanning engine used (ClamAV, VirusTotal, etc.)
            threat_types: List of threat types detected (virus, malware, trojan, etc.)
            tenant_id: Tenant context for multi-tenant isolation
            user_id: User who uploaded the infected file
            quarantine_location: Location where file was quarantined
            scan_duration_ms: Time taken for the scan in milliseconds
            error_code: Specific error code for the failure
            details: Additional details about the failure
        """
        # Build enhanced details
        enhanced_details = details or {}
        if file_id:
            enhanced_details["file_id"] = str(file_id)
        if filename:
            enhanced_details["filename"] = filename
        if checksum:
            enhanced_details["checksum"] = str(checksum)
            enhanced_details["checksum_algorithm"] = checksum.get_algorithm_name()
        if virus_name:
            enhanced_details["virus_name"] = virus_name
        if scanner_name:
            enhanced_details["scanner_name"] = scanner_name
        if scanner_version:
            enhanced_details["scanner_version"] = scanner_version
        if scan_engine:
            enhanced_details["scan_engine"] = scan_engine
        if threat_types:
            enhanced_details["threat_types"] = threat_types
        if tenant_id:
            enhanced_details["tenant_id"] = tenant_id
        if user_id:
            enhanced_details["user_id"] = user_id
        if quarantine_location:
            enhanced_details["quarantine_location"] = quarantine_location
        if scan_duration_ms is not None:
            enhanced_details["scan_duration_ms"] = scan_duration_ms
            
        super().__init__(
            message=message,
            error_code=error_code or "VIRUS_DETECTED",
            details=enhanced_details
        )
        
        # Store virus-specific fields
        self.file_id = file_id
        self.filename = filename
        self.checksum = checksum
        self.virus_name = virus_name
        self.scanner_name = scanner_name
        self.scanner_version = scanner_version
        self.scan_engine = scan_engine
        self.threat_types = threat_types
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.quarantine_location = quarantine_location
        self.scan_duration_ms = scan_duration_ms