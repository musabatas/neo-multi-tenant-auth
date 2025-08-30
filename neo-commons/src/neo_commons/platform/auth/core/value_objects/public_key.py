"""Public key value object with cryptographic key validation."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PublicKey:
    """Public key value object for JWT signature validation.
    
    Handles ONLY public key representation and basic validation.
    Does not perform cryptographic operations - that's handled by validators.
    """
    
    key_data: str
    key_id: Optional[str] = None
    algorithm: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate public key format."""
        if not self.key_data:
            raise ValueError("Public key data cannot be empty")
        
        if not isinstance(self.key_data, str):
            raise TypeError("Public key data must be a string")
        
        # Basic PEM format validation
        self._validate_pem_format()
        
        # Validate key_id if provided
        if self.key_id is not None:
            if not isinstance(self.key_id, str):
                raise TypeError("Key ID must be a string")
            if not self.key_id.strip():
                raise ValueError("Key ID cannot be empty")
        
        # Validate algorithm if provided
        if self.algorithm is not None:
            if not isinstance(self.algorithm, str):
                raise TypeError("Algorithm must be a string")
            
            # Validate against supported JWT algorithms
            supported_algorithms = {
                'RS256', 'RS384', 'RS512',  # RSA with SHA
                'ES256', 'ES384', 'ES512',  # ECDSA with SHA
                'PS256', 'PS384', 'PS512',  # RSA-PSS with SHA
            }
            if self.algorithm not in supported_algorithms:
                raise ValueError(f"Unsupported algorithm: {self.algorithm}")
    
    def _validate_pem_format(self) -> None:
        """Validate PEM format structure."""
        lines = self.key_data.strip().split('\n')
        
        if len(lines) < 3:
            raise ValueError("Invalid PEM format: too few lines")
        
        # Check for PEM headers/footers
        first_line = lines[0].strip()
        last_line = lines[-1].strip()
        
        valid_headers = [
            '-----BEGIN PUBLIC KEY-----',
            '-----BEGIN RSA PUBLIC KEY-----',
            '-----BEGIN EC PUBLIC KEY-----',
            '-----BEGIN CERTIFICATE-----'
        ]
        
        valid_footers = [
            '-----END PUBLIC KEY-----',
            '-----END RSA PUBLIC KEY-----', 
            '-----END EC PUBLIC KEY-----',
            '-----END CERTIFICATE-----'
        ]
        
        if not any(first_line == header for header in valid_headers):
            raise ValueError("Invalid PEM format: missing or invalid header")
        
        if not any(last_line == footer for footer in valid_footers):
            raise ValueError("Invalid PEM format: missing or invalid footer")
        
        # Validate base64 content (middle lines)
        import re
        base64_pattern = re.compile(r'^[A-Za-z0-9+/=\s]+$')
        
        for i, line in enumerate(lines[1:-1], 1):
            if line.strip() and not base64_pattern.match(line):
                raise ValueError(f"Invalid PEM format: line {i+1} contains invalid base64 characters")
    
    @property
    def is_rsa_key(self) -> bool:
        """Check if this is an RSA public key."""
        return any(marker in self.key_data for marker in [
            'BEGIN RSA PUBLIC KEY',
            'BEGIN PUBLIC KEY'  # Most common format
        ])
    
    @property
    def is_ec_key(self) -> bool:
        """Check if this is an Elliptic Curve public key."""
        return 'BEGIN EC PUBLIC KEY' in self.key_data
    
    @property
    def is_certificate(self) -> bool:
        """Check if this is a certificate (contains public key)."""
        return 'BEGIN CERTIFICATE' in self.key_data
    
    def fingerprint(self) -> str:
        """Generate a fingerprint for the public key (for identification)."""
        import hashlib
        
        # Use the key data (without whitespace) for fingerprint
        normalized_key = ''.join(self.key_data.split())
        fingerprint_bytes = hashlib.sha256(normalized_key.encode('utf-8')).digest()
        
        # Return as hex string with colons
        hex_fingerprint = fingerprint_bytes.hex()
        return ':'.join(hex_fingerprint[i:i+2] for i in range(0, len(hex_fingerprint), 2))
    
    def mask_for_logging(self) -> str:
        """Return masked key safe for logging."""
        lines = self.key_data.strip().split('\n')
        if len(lines) < 3:
            return "***INVALID_KEY***"
        
        # Show header and footer, mask content
        header = lines[0]
        footer = lines[-1]
        content_lines = len(lines) - 2
        
        return f"{header}\n{'*' * 20} ({content_lines} lines masked)\n{footer}"
    
    def __str__(self) -> str:
        """String representation (masked for security)."""
        key_type = "RSA" if self.is_rsa_key else "EC" if self.is_ec_key else "CERT" if self.is_certificate else "UNKNOWN"
        key_id_str = f", key_id={self.key_id}" if self.key_id else ""
        algorithm_str = f", algorithm={self.algorithm}" if self.algorithm else ""
        return f"PublicKey(type={key_type}{key_id_str}{algorithm_str})"
    
    def __repr__(self) -> str:
        """Debug representation (masked for security)."""
        return f"PublicKey(key_data='{self.mask_for_logging()}', key_id={self.key_id}, algorithm={self.algorithm})"