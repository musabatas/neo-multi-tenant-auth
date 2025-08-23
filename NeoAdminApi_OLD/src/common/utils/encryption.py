"""
NeoAdminApi encryption utilities.

This module provides a service-specific wrapper around neo-commons encryption
utilities, handling NeoAdminApi-specific configuration and settings integration.
"""

import os
from neo_commons.utils.encryption import (
    PasswordEncryption as BasePasswordEncryption,
    get_encryption as base_get_encryption,
    encrypt_password as base_encrypt_password,
    decrypt_password as base_decrypt_password,
    is_encrypted as base_is_encrypted,
    reset_encryption_instance as base_reset_encryption_instance,
)

# Re-export the base class for direct usage
PasswordEncryption = BasePasswordEncryption


def get_encryption() -> BasePasswordEncryption:
    """
    Get the singleton encryption instance with NeoAdminApi settings integration.
    
    Returns:
        The PasswordEncryption instance configured for NeoAdminApi
    """
    # Ensure encryption key is available from settings if not in environment
    if not os.environ.get('APP_ENCRYPTION_KEY'):
        from src.common.config.settings import settings
        os.environ['APP_ENCRYPTION_KEY'] = settings.app_encryption_key
    
    return base_get_encryption()


def encrypt_password(password: str) -> str:
    """
    Convenience function to encrypt a password using NeoAdminApi configuration.
    
    Args:
        password: The plaintext password
        
    Returns:
        The encrypted password
    """
    return get_encryption().encrypt_password(password)


def decrypt_password(encrypted_password: str) -> str:
    """
    Convenience function to decrypt a password using NeoAdminApi configuration.
    
    Args:
        encrypted_password: The encrypted password
        
    Returns:
        The plaintext password
    """
    return get_encryption().decrypt_password(encrypted_password)


def is_encrypted(value: str) -> bool:
    """
    Convenience function to check if a value is encrypted.
    
    Args:
        value: The value to check
        
    Returns:
        True if encrypted, False otherwise
    """
    return base_is_encrypted(value)


def reset_encryption_instance() -> None:
    """
    Reset the singleton encryption instance.
    
    This function is primarily useful for testing scenarios.
    """
    return base_reset_encryption_instance()