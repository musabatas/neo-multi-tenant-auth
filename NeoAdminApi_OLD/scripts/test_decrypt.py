#!/usr/bin/env python3
"""Test decryption with environment key."""

import os
import sys

# Add src to path
sys.path.insert(0, '/Users/musabatas/Workspaces/NeoMultiTenant/NeoAdminApi')

# Set the key explicitly
os.environ['APP_ENCRYPTION_KEY'] = 'KDEAXgazY0zwe6ZkVsXT980pDADnoX9I'

from src.common.utils.encryption import decrypt_password, is_encrypted

# The encrypted password we just put in the database
encrypted = "gAAAAABol4ATGxSZIbqI00K0du_r2yesIsV_AUgGyZ5oeuI6jhs-6suJ07tkS8HuzEI0fT366Cllhozg5uGOSFSUQ3hI3kY2GA=="

print(f"APP_ENCRYPTION_KEY from env: {os.environ.get('APP_ENCRYPTION_KEY')}")
print(f"Encrypted password: {encrypted}")
print(f"Is encrypted: {is_encrypted(encrypted)}")

try:
    decrypted = decrypt_password(encrypted)
    print(f"Decrypted password: '{decrypted}'")
    print(f"Is 'postgres': {decrypted == 'postgres'}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()