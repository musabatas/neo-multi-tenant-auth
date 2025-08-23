"""Utilities module for neo-commons.

This module provides utility functions and helpers used throughout
the neo-commons library.
"""

from .uuid import *
from .encryption import (
    PasswordEncryption,
    get_encryption,
    encrypt_password,
    decrypt_password,
    is_encrypted,
    reset_encryption_instance,
)

__all__ = [
    # UUID Generation
    "generate_uuid_v7",
    "generate_uuid_v4",
    "extract_timestamp_from_uuid_v7",
    "is_valid_uuid",
    "is_uuid_v7",
    "is_uuid_v4",
    "generate_short_id",
    "generate_tenant_slug",
    "normalize_uuid",
    "uuid_to_base64",
    "base64_to_uuid",
    "UUIDGenerator",
    "default_generator",
    "generate",
    "generate_id",
    # Password Encryption
    "PasswordEncryption",
    "get_encryption",
    "encrypt_password",
    "decrypt_password",
    "is_encrypted",
    "reset_encryption_instance",
]