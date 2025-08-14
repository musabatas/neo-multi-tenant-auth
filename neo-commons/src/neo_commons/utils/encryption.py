"""
Password encryption/decryption utilities.
Based on NeoInfrastructure encryption approach using PBKDF2 + Fernet.
Enhanced for neo-commons with environment configuration and improved error handling.
"""

import os
import base64
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class PasswordEncryption:
    """Handle encryption and decryption of database passwords and sensitive data."""
    
    def __init__(self, encryption_key: Optional[str] = None, salt: Optional[bytes] = None):
        """
        Initialize encryption with the provided key or from environment.
        
        Args:
            encryption_key: The encryption key to use. If not provided, 
                          uses APP_ENCRYPTION_KEY or NEO_ENCRYPTION_KEY from environment.
            salt: Custom salt for key derivation. If not provided, uses default.
        """
        # Try multiple environment variable names for flexibility
        self.key_string = encryption_key or (
            os.environ.get('APP_ENCRYPTION_KEY') or 
            os.environ.get('NEO_ENCRYPTION_KEY') or 
            os.environ.get('ENCRYPTION_KEY') or
            'dev-encryption-key-change-in-production'
        )
        
        # Use custom salt or default
        self.salt = salt or b'NeoMultiTenantSalt'
        
        # Derive a proper Fernet key from the string key
        self.cipher = self._get_cipher()
    
    def _get_cipher(self) -> Fernet:
        """
        Create a Fernet cipher from the encryption key string.
        Uses PBKDF2 to derive a proper key from the string.
        
        Returns:
            Fernet: Initialized Fernet cipher
        """
        # Derive a 32-byte key from the password string
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,  # OWASP recommended minimum
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
            str: The encrypted password as a base64-encoded string.
            
        Raises:
            ValueError: If password is None or encryption fails
        """
        if password is None:
            raise ValueError("Password cannot be None")
        
        if not password:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(password.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Encryption failed: {str(e)}") from e
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt an encrypted password.
        
        Args:
            encrypted_password: The encrypted password as a base64-encoded string.
            
        Returns:
            str: The decrypted plaintext password.
            
        Raises:
            ValueError: If decryption fails or input is None
        """
        if encrypted_password is None:
            raise ValueError("Encrypted password cannot be None")
        
        if not encrypted_password:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(encrypted_password.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except InvalidToken:
            # If decryption fails, it might be plaintext or corrupted
            raise ValueError("Invalid encrypted password - may be plaintext or corrupted")
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}") from e
    
    def decrypt_password_safe(self, encrypted_password: str) -> str:
        """
        Decrypt an encrypted password with fallback to original value.
        This is a legacy compatibility method - prefer decrypt_password() for new code.
        
        Args:
            encrypted_password: The encrypted password as a base64-encoded string.
            
        Returns:
            str: The decrypted plaintext password, or original value if decryption fails.
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
        """
        Check if a value appears to be encrypted.
        
        Args:
            value: The value to check.
            
        Returns:
            bool: True if the value appears to be encrypted, False otherwise.
        """
        if not value:
            return False
        
        # Fernet tokens start with 'gAAAAA'
        return value.startswith('gAAAAA')
    
    def encrypt_data(self, data: Union[str, bytes]) -> str:
        """
        Encrypt arbitrary data (not just passwords).
        
        Args:
            data: String or bytes to encrypt
            
        Returns:
            str: Encrypted data as base64-encoded string
            
        Raises:
            ValueError: If data is None or encryption fails
        """
        if data is None:
            raise ValueError("Data cannot be None")
        
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        try:
            encrypted_bytes = self.cipher.encrypt(data_bytes)
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            raise ValueError(f"Data encryption failed: {str(e)}") from e
    
    def decrypt_data(self, encrypted_data: str) -> bytes:
        """
        Decrypt arbitrary data and return as bytes.
        
        Args:
            encrypted_data: Encrypted data as base64-encoded string
            
        Returns:
            bytes: Decrypted data as bytes
            
        Raises:
            ValueError: If decryption fails or input is None
        """
        if encrypted_data is None:
            raise ValueError("Encrypted data cannot be None")
        
        try:
            return self.cipher.decrypt(encrypted_data.encode('utf-8'))
        except InvalidToken:
            raise ValueError("Invalid encrypted data - may be corrupted")
        except Exception as e:
            raise ValueError(f"Data decryption failed: {str(e)}") from e
    
    def decrypt_data_to_string(self, encrypted_data: str, encoding: str = 'utf-8') -> str:
        """
        Decrypt arbitrary data and return as string.
        
        Args:
            encrypted_data: Encrypted data as base64-encoded string
            encoding: Text encoding to use for string conversion
            
        Returns:
            str: Decrypted data as string
            
        Raises:
            ValueError: If decryption fails or encoding is invalid
        """
        try:
            decrypted_bytes = self.decrypt_data(encrypted_data)
            return decrypted_bytes.decode(encoding)
        except UnicodeDecodeError as e:
            raise ValueError(f"Failed to decode decrypted data with {encoding}: {str(e)}") from e


# Global encryption instance
_encryption_instance: Optional[PasswordEncryption] = None


def get_encryption() -> PasswordEncryption:
    """
    Get the singleton encryption instance.
    
    Returns:
        PasswordEncryption: The encryption instance.
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = PasswordEncryption()
    return _encryption_instance


def set_encryption_key(key: str) -> None:
    """
    Set a custom encryption key and reset the singleton instance.
    Useful for testing or dynamic configuration.
    
    Args:
        key: The encryption key to use
    """
    global _encryption_instance
    _encryption_instance = PasswordEncryption(encryption_key=key)


def encrypt_password(password: str) -> str:
    """
    Convenience function to encrypt a password.
    
    Args:
        password: The plaintext password.
        
    Returns:
        str: The encrypted password.
    """
    return get_encryption().encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """
    Convenience function to decrypt a password.
    
    Args:
        encrypted_password: The encrypted password.
        
    Returns:
        str: The plaintext password.
        
    Raises:
        ValueError: If decryption fails
    """
    return get_encryption().decrypt_password(encrypted_password)


def decrypt_password_safe(encrypted_password: str) -> str:
    """
    Convenience function to decrypt a password with fallback.
    Legacy compatibility method.
    
    Args:
        encrypted_password: The encrypted password.
        
    Returns:
        str: The plaintext password, or original value if decryption fails.
    """
    return get_encryption().decrypt_password_safe(encrypted_password)


def is_encrypted(value: str) -> bool:
    """
    Convenience function to check if a value is encrypted.
    
    Args:
        value: The value to check.
        
    Returns:
        bool: True if encrypted, False otherwise.
    """
    return get_encryption().is_encrypted(value)


def encrypt_data(data: Union[str, bytes]) -> str:
    """
    Convenience function to encrypt arbitrary data.
    
    Args:
        data: Data to encrypt
        
    Returns:
        str: Encrypted data as base64-encoded string
    """
    return get_encryption().encrypt_data(data)


def decrypt_data_to_string(encrypted_data: str, encoding: str = 'utf-8') -> str:
    """
    Convenience function to decrypt data to string.
    
    Args:
        encrypted_data: Encrypted data
        encoding: Text encoding
        
    Returns:
        str: Decrypted string
    """
    return get_encryption().decrypt_data_to_string(encrypted_data, encoding)


# Utility functions for validation
def validate_encryption_key(key: str) -> bool:
    """
    Validate that an encryption key works correctly.
    
    Args:
        key: The encryption key to test
        
    Returns:
        bool: True if key works, False otherwise
    """
    try:
        test_encryption = PasswordEncryption(encryption_key=key)
        test_data = "test_encryption_validation"
        
        encrypted = test_encryption.encrypt_password(test_data)
        decrypted = test_encryption.decrypt_password(encrypted)
        
        return decrypted == test_data
    except Exception:
        return False


def generate_salt() -> bytes:
    """
    Generate a random salt for key derivation.
    
    Returns:
        bytes: Random 16-byte salt
    """
    return os.urandom(16)


def is_production_key(key: str) -> bool:
    """
    Check if encryption key appears to be a production-ready key.
    
    Args:
        key: The encryption key to check
        
    Returns:
        bool: True if appears to be production-ready
    """
    # Production keys should be longer and not contain common dev patterns
    dev_patterns = ['dev', 'test', 'local', 'demo', 'sample', 'change']
    
    if len(key) < 32:  # Minimum length for good security
        return False
    
    key_lower = key.lower()
    return not any(pattern in key_lower for pattern in dev_patterns)