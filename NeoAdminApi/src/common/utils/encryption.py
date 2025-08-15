"""
Password encryption/decryption utilities.

MIGRATED TO NEO-COMMONS: Now using neo-commons encryption utilities with enhanced security features.
Import compatibility maintained - all existing imports continue to work.
"""

import os
from typing import Optional, Union

# NEO-COMMONS IMPORT: Use neo-commons encryption utilities
from neo_commons.utils.encryption import (
    # Main encryption class
    PasswordEncryption as NeoCommonsPasswordEncryption,
    
    # Core functions
    get_encryption as neo_commons_get_encryption,
    set_encryption_key,
    encrypt_password,
    decrypt_password,
    decrypt_password_safe,
    is_encrypted,
    
    # Enhanced data encryption functions
    encrypt_data,
    decrypt_data_to_string,
    
    # Validation and utility functions
    validate_encryption_key,
    generate_salt,
    is_production_key,
)


class PasswordEncryption(NeoCommonsPasswordEncryption):
    """
    NeoAdminApi password encryption extending neo-commons PasswordEncryption.
    
    Maintains backward compatibility while leveraging enhanced neo-commons features.
    Adds all the enhanced features from neo-commons including:
    - Better error handling with specific exceptions
    - Support for arbitrary data encryption (encrypt_data/decrypt_data)
    - Enhanced security validation (validate_encryption_key, is_production_key)
    - Improved environment variable support (APP_ENCRYPTION_KEY, NEO_ENCRYPTION_KEY)
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption with NeoAdminApi-specific configuration.
        
        Args:
            encryption_key: The encryption key to use. If not provided, 
                          tries APP_ENCRYPTION_KEY first for backward compatibility.
        """
        # Maintain backward compatibility with NeoAdminApi's APP_ENCRYPTION_KEY preference
        if encryption_key is None:
            encryption_key = (
                os.environ.get('APP_ENCRYPTION_KEY') or
                os.environ.get('NEO_ENCRYPTION_KEY') or
                os.environ.get('ENCRYPTION_KEY')
            )
            
            # If still no key found, try loading from settings for backward compatibility
            if not encryption_key:
                try:
                    from src.common.config.settings import settings
                    encryption_key = settings.app_encryption_key
                except Exception:
                    # If settings loading fails, use default
                    pass
        
        # Initialize neo-commons encryption with the resolved key
        super().__init__(encryption_key=encryption_key)


# Singleton instance for backward compatibility
_encryption_instance: Optional[PasswordEncryption] = None


def get_encryption() -> PasswordEncryption:
    """
    Get the singleton encryption instance with NeoAdminApi configuration.
    
    Returns:
        PasswordEncryption: The NeoAdminApi-configured encryption instance.
    """
    global _encryption_instance
    if _encryption_instance is None:
        _encryption_instance = PasswordEncryption()
    return _encryption_instance


# Re-export all neo-commons functions for backward compatibility
__all__ = [
    # Main class
    "PasswordEncryption",
    
    # Core functions
    "get_encryption",
    "set_encryption_key",
    "encrypt_password",
    "decrypt_password",
    "decrypt_password_safe",
    "is_encrypted",
    
    # Enhanced data encryption functions (NEW from neo-commons)
    "encrypt_data",
    "decrypt_data_to_string",
    
    # Validation and utility functions (NEW from neo-commons)
    "validate_encryption_key",
    "generate_salt",
    "is_production_key",
]