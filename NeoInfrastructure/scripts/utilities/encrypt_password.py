#!/usr/bin/env python3
"""
Utility script to encrypt passwords for storage in the database.
Usage: ./encrypt_password.py [password]
"""

import os
import sys
import getpass

# Add the migrations/orchestrator directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'migrations'))

from orchestrator.encryption import encrypt_password, decrypt_password


def main():
    """Main function to encrypt a password."""
    
    # Set the encryption key if not already set
    if not os.environ.get('APP_ENCRYPTION_KEY'):
        # Try to load from .env file
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('APP_ENCRYPTION_KEY='):
                        key = line.strip().split('=', 1)[1]
                        os.environ['APP_ENCRYPTION_KEY'] = key
                        break
    
    if not os.environ.get('APP_ENCRYPTION_KEY'):
        print("❌ APP_ENCRYPTION_KEY not found in environment or .env file")
        sys.exit(1)
    
    # Get password from command line or prompt
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass("Enter password to encrypt: ")
    
    # Encrypt the password
    encrypted = encrypt_password(password)
    
    print("\n" + "=" * 60)
    print("Password Encryption")
    print("=" * 60)
    print(f"Original:  {password}")
    print(f"Encrypted: {encrypted}")
    print("=" * 60)
    
    # Verify it can be decrypted
    decrypted = decrypt_password(encrypted)
    if decrypted == password:
        print("✅ Verification successful - password can be decrypted")
    else:
        print("❌ Verification failed - decryption doesn't match original")
    
    print("\n💡 You can now store this encrypted password in the database")
    print("   The migration engine will automatically decrypt it when needed.")


if __name__ == "__main__":
    main()