#!/usr/bin/env python3
"""
Update database connection passwords with encrypted values.
This script should be run after migrations to set encrypted passwords.
"""

import os
import sys
import asyncio
import asyncpg
from pathlib import Path

# Add the app directory to Python path for encryption module
sys.path.insert(0, '/app')

from orchestrator.encryption import encrypt_password


async def update_passwords():
    """Update all database connections with encrypted passwords."""
    
    # Get database connection parameters
    host = os.getenv('POSTGRES_US_HOST', 'neo-postgres-us-east')
    port = int(os.getenv('POSTGRES_US_PORT', '5432'))
    database = 'neofast_admin'
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    # The password to encrypt for all connections
    db_password = os.getenv('POSTGRES_PASSWORD', 'postgres')
    
    print(f"Encrypting database passwords...")
    print(f"   Using APP_ENCRYPTION_KEY: {os.getenv('APP_ENCRYPTION_KEY', 'not set')[:10]}...")
    
    # Encrypt the password
    encrypted_password = encrypt_password(db_password)
    print(f"   Encrypted password: {encrypted_password[:50]}...")
    
    # Connect to admin database
    conn = await asyncpg.connect(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password
    )
    
    try:
        # Update all database connections with encrypted password
        result = await conn.execute("""
            UPDATE admin.database_connections 
            SET encrypted_password = $1,
                username = COALESCE(username, 'postgres')
            WHERE encrypted_password IS NULL OR encrypted_password = ''
        """, encrypted_password)
        
        # Get count of updated rows
        count = int(result.split()[-1]) if result else 0
        print(f"✅ Updated {count} database connections with encrypted passwords")
        
        # Show which connections were updated
        rows = await conn.fetch("""
            SELECT connection_name, database_name, encrypted_password IS NOT NULL as has_encrypted
            FROM admin.database_connections
            ORDER BY connection_name
        """)
        
        print("\n📊 Database Connections Status:")
        for row in rows:
            status = "✅" if row['has_encrypted'] else "❌"
            print(f"   {status} {row['connection_name']}: {row['database_name']}")
            
    finally:
        await conn.close()
    
    print("\n🎉 Password encryption complete!")
    print("   The migration engine will automatically decrypt these when connecting.")


async def main():
    """Main entry point."""
    # Check if APP_ENCRYPTION_KEY is set
    if not os.getenv('APP_ENCRYPTION_KEY'):
        # Try to load from .env file
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('APP_ENCRYPTION_KEY='):
                        key = line.strip().split('=', 1)[1]
                        os.environ['APP_ENCRYPTION_KEY'] = key
                        break
    
    if not os.getenv('APP_ENCRYPTION_KEY'):
        print("❌ APP_ENCRYPTION_KEY not found in environment")
        print("   Please set it in .env or environment variables")
        sys.exit(1)
    
    await update_passwords()


if __name__ == "__main__":
    asyncio.run(main())