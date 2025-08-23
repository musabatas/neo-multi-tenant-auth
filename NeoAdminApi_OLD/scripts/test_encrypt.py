#!/usr/bin/env python3
"""Test what the encrypted password should be with our key."""

import os
import sys
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Test with our key
key_string = 'KDEAXgazY0zwe6ZkVsXT980pDADnoX9I'

# Use the same salt as NeoInfrastructure
salt = b'NeoMultiTenant2024'

# Derive a 32-byte key from the password string
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
)

# Convert string key to bytes and derive the encryption key
key_bytes = key_string.encode('utf-8')
derived_key = base64.urlsafe_b64encode(kdf.derive(key_bytes))

cipher = Fernet(derived_key)

# Encrypt 'postgres' password
password = 'postgres'
encrypted = cipher.encrypt(password.encode('utf-8'))
print(f"Key: {key_string}")
print(f"Password: {password}")
print(f"Encrypted: {encrypted.decode('utf-8')}")

# Now decrypt it back to verify
decrypted = cipher.decrypt(encrypted)
print(f"Decrypted: {decrypted.decode('utf-8')}")
print(f"Match: {decrypted.decode('utf-8') == password}")