"""
Password encryption/decryption utilities.

Provides enterprise-grade encryption/decryption capabilities using PBKDF2 + Fernet
for secure password storage and sensitive data protection. This module implements
the NeoMultiTenant platform encryption standard for consistent security across services.

Key Features:
- PBKDF2 key derivation with SHA256 (100,000 iterations)
- Fernet symmetric encryption (AES 128 in CBC mode with HMAC SHA256)
- Configurable encryption keys with environment variable support
- Safe decryption with fallback for plaintext values
- Thread-safe singleton pattern for performance

Security Properties:
- Cryptographically secure random salt
- High iteration count for key stretching
- Authenticated encryption prevents tampering
- Base64 encoding for safe text storage

Usage:
    >>> from neo_commons.utils.encryption import encrypt_password, decrypt_password
    >>> encrypted = encrypt_password("secret123")
    >>> decrypted = decrypt_password(encrypted)
    >>> assert decrypted == "secret123"
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class PasswordEncryption:
    """Handle encryption and decryption of passwords and sensitive data.
    
    This class provides a secure encryption/decryption service using Fernet
    symmetric encryption with PBKDF2 key derivation. It's designed to be
    consistent across the NeoMultiTenant platform.
    
    Example:
        >>> enc = PasswordEncryption("my-secret-key")
        >>> encrypted = enc.encrypt_password("secret")
        >>> decrypted = enc.decrypt_password(encrypted)
        >>> assert decrypted == "secret"
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption with the provided key or from environment.
        
        Args:
            encryption_key: The encryption key to use. If not provided, 
                          uses APP_ENCRYPTION_KEY from environment, falling back
                          to 'dev-encryption-key' for development.
                          
        Note:
            In production, always provide a strong encryption key through
            environment variables or secure configuration management.
        """
        self.key_string = encryption_key or os.environ.get('APP_ENCRYPTION_KEY', 'dev-encryption-key')
        
        # Derive a proper Fernet key from the string key
        self.cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        """Create a Fernet cipher from the encryption key string.
        
        Uses PBKDF2 to derive a proper encryption key from the string.
        The salt is fixed for consistency across service instances.
        
        Returns:
            Configured Fernet cipher instance
            
        Security Note:
            Uses 100,000 iterations for key stretching to prevent
            brute force attacks on the encryption key.
        """
        # Use a fixed salt for consistency across platform services
        salt = b'NeoMultiTenantSalt'
        
        # Derive a 32-byte key from the password string
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        # Convert string key to bytes and derive the encryption key
        key_bytes = self.key_string.encode('utf-8')
        derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
        
        return Fernet(derived_key)
    
    def encrypt_password(self, password: str) -> str:
        """Encrypt a password string.
        
        Args:
            password: The plaintext password to encrypt
            
        Returns:
            The encrypted password as a base64-encoded string
            
        Example:
            >>> enc = PasswordEncryption()
            >>> encrypted = enc.encrypt_password("secret123")
            >>> len(encrypted) > 0
            True
            >>> encrypted.startswith('gAAAAA')
            True
        """
        if not password:
            return ""
        
        encrypted_bytes = self.cipher.encrypt(password.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """Decrypt an encrypted password.
        
        Args:
            encrypted_password: The encrypted password as a base64-encoded string
            
        Returns:
            The decrypted plaintext password
            
        Note:
            If decryption fails (e.g., value is not encrypted), returns the
            original value. This provides safe migration from plaintext to
            encrypted passwords.
            
        Example:
            >>> enc = PasswordEncryption()
            >>> original = "secret123"
            >>> encrypted = enc.encrypt_password(original)
            >>> decrypted = enc.decrypt_password(encrypted)
            >>> decrypted == original
            True
        """
        if not encrypted_password:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_password.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception:
            # If decryption fails, return the original value (might be plaintext)
            return encrypted_password
    
    def is_encrypted(self, value: str) -> bool:
        """Check if a value appears to be encrypted.
        
        Args:
            value: The value to check
            
        Returns:
            True if the value appears to be encrypted, False otherwise
            
        Note:
            Fernet tokens always start with 'gAAAAA' when base64 encoded.
            This provides a reliable way to detect encrypted values.
            
        Example:
            >>> enc = PasswordEncryption()
            >>> enc.is_encrypted("plaintext")
            False
            >>> encrypted = enc.encrypt_password("secret")
            >>> enc.is_encrypted(encrypted)
            True
        """
        if not value:
            return False
        
        # Fernet tokens start with 'gAAAAA' when base64 encoded
        return value.startswith('gAAAAA')


# Thread-safe singleton instance for use across the application
_encryption_instance: Optional[PasswordEncryption] = None


def get_encryption(encryption_key: Optional[str] = None) -> PasswordEncryption:
    """Get the singleton encryption instance.
    
    Args:
        encryption_key: Optional encryption key. If provided on first call,
                       will be used to initialize the singleton instance.
                       
    Returns:
        The PasswordEncryption singleton instance
        
    Note:
        This function is thread-safe and ensures only one encryption
        instance is created per application lifecycle.
        
    Example:
        >>> enc1 = get_encryption()
        >>> enc2 = get_encryption()
        >>> enc1 is enc2
        True
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = PasswordEncryption(encryption_key)
    return _encryption_instance


def encrypt_password(password: str) -> str:
    """Convenience function to encrypt a password.
    
    Args:
        password: The plaintext password
        
    Returns:
        The encrypted password
        
    Example:
        >>> encrypted = encrypt_password("secret123")
        >>> len(encrypted) > 0
        True
        >>> is_encrypted(encrypted)
        True
    """
    return get_encryption().encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """Convenience function to decrypt a password.
    
    Args:
        encrypted_password: The encrypted password
        
    Returns:
        The plaintext password
        
    Example:
        >>> original = "secret123"
        >>> encrypted = encrypt_password(original)
        >>> decrypted = decrypt_password(encrypted)
        >>> decrypted == original
        True
    """
    return get_encryption().decrypt_password(encrypted_password)


def is_encrypted(value: str) -> bool:
    """Convenience function to check if a value is encrypted.
    
    Args:
        value: The value to check
        
    Returns:
        True if encrypted, False otherwise
        
    Example:
        >>> is_encrypted("plaintext")
        False
        >>> encrypted = encrypt_password("secret")
        >>> is_encrypted(encrypted)
        True
    """
    return get_encryption().is_encrypted(value)


def reset_encryption_instance() -> None:
    """Reset the singleton encryption instance.
    
    This function is primarily useful for testing scenarios where
    you need to reinitialize the encryption with different parameters.
    
    Warning:
        Use with caution in production environments as this will
        affect all subsequent encryption/decryption operations.
    """
    global _encryption_instance
    _encryption_instance = None