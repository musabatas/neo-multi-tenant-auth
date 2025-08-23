"""Password encryption utilities for neo-commons.

This module provides encryption/decryption functionality compatible with 
NeoInfrastructure's encryption system. Uses Fernet symmetric encryption.
"""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class PasswordEncryption:
    """Handle encryption and decryption of database passwords."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with the provided key or from environment.
        
        Args:
            encryption_key: The encryption key to use. If not provided, 
                          uses DB_ENCRYPTION_KEY from environment (neo-commons standard).
        """
        # Support both DB_ENCRYPTION_KEY (neo-commons) and APP_ENCRYPTION_KEY (NeoInfrastructure)
        self.key_string = (
            encryption_key or 
            os.environ.get('DB_ENCRYPTION_KEY') or 
            os.environ.get('APP_ENCRYPTION_KEY')
        )
        
        if not self.key_string:
            raise ValueError("DB_ENCRYPTION_KEY or APP_ENCRYPTION_KEY not found in environment variables")
        
        # Derive a proper Fernet key from the string key
        self.cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        """
        Create a Fernet cipher from the encryption key string.
        Uses PBKDF2 to derive a proper key from the string.
        Compatible with NeoInfrastructure encryption.
        """
        # Use the same fixed salt as NeoInfrastructure for compatibility
        salt = b'NeoMultiTenant2024'
        
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
        """
        Encrypt a password string.
        
        Args:
            password: The plaintext password to encrypt.
            
        Returns:
            The encrypted password as a base64-encoded string.
        """
        if not password:
            return ""
        
        encrypted_bytes = self.cipher.encrypt(password.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt an encrypted password.
        
        Args:
            encrypted_password: The encrypted password as a base64-encoded string.
            
        Returns:
            The decrypted plaintext password.
        """
        if not encrypted_password:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_password.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to decrypt password: {e}")
    
    def is_encrypted(self, value: str) -> bool:
        """
        Check if a value appears to be encrypted.
        
        Args:
            value: The value to check.
            
        Returns:
            True if the value appears to be encrypted, False otherwise.
        """
        if not value:
            return False
        
        # Fernet tokens start with 'gAAAAA'
        return value.startswith('gAAAAA')


# Singleton instance for use across the application
_encryption_instance: Optional[PasswordEncryption] = None


def get_encryption() -> PasswordEncryption:
    """
    Get the singleton encryption instance.
    
    Returns:
        The PasswordEncryption instance.
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = PasswordEncryption()
    return _encryption_instance


def encrypt_password(password: str) -> str:
    """
    Convenience function to encrypt a password.
    
    Args:
        password: The plaintext password.
        
    Returns:
        The encrypted password.
    """
    return get_encryption().encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """
    Convenience function to decrypt a password.
    
    Args:
        encrypted_password: The encrypted password.
        
    Returns:
        The plaintext password.
    """
    return get_encryption().decrypt_password(encrypted_password)


def is_encrypted(value: str) -> bool:
    """
    Convenience function to check if a value is encrypted.
    
    Args:
        value: The value to check.
        
    Returns:
        True if encrypted, False otherwise.
    """
    return get_encryption().is_encrypted(value)


def reset_encryption_instance() -> None:
    """
    Reset the singleton encryption instance.
    
    This function is primarily useful for testing scenarios.
    """
    global _encryption_instance
    _encryption_instance = None