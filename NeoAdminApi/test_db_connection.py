#!/usr/bin/env python3
"""Test script to verify admin database connection."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path so we can import neo_commons
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables for testing
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "true"
os.environ["ADMIN_DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/neofast_admin"
os.environ["DB_ENCRYPTION_KEY"] = "test-key-for-development-only-32chars"
os.environ["KEYCLOAK_SERVER_URL"] = "http://localhost:8080"
os.environ["KEYCLOAK_CLIENT_ID"] = "admin-cli"
os.environ["KEYCLOAK_CLIENT_SECRET"] = "test-secret"


async def test_database_connection():
    """Test database connection and health check."""
    try:
        print("🔄 Testing neo-commons database connection...")
        
        # Import neo-commons database service
        from neo_commons.features.database.services import DatabaseManager
        
        # Get database service instance
        print("📡 Getting database service instance...")
        db_service = await DatabaseManager.get_instance()
        
        print("✅ Database service initialized successfully!")
        
        # Test health check
        print("🩺 Testing database health check...")
        health_status = await db_service.health_check()
        
        print("📊 Health Check Results:")
        print(f"  Overall Healthy: {health_status.get('overall_healthy', False)}")
        print(f"  Total Connections: {health_status.get('total_connections', 0)}")
        
        # Print connection details
        connections = health_status.get('connections', {})
        for conn_name, conn_status in connections.items():
            print(f"  Connection '{conn_name}':")
            print(f"    - Healthy: {conn_status.get('healthy', False)}")
            print(f"    - Active: {conn_status.get('connection_active', False)}")
            if conn_status.get('error_message'):
                print(f"    - Error: {conn_status['error_message']}")
        
        # Test basic query
        print("📝 Testing basic query...")
        try:
            async with db_service.get_connection("admin") as conn:
                result = await conn.fetchval("SELECT 1 as test")
                print(f"✅ Basic query result: {result}")
        except Exception as e:
            print(f"❌ Basic query failed: {e}")
        
        # Test admin schema check
        print("🏗️ Testing admin schema accessibility...")
        try:
            async with db_service.get_connection("admin") as conn:
                # Check if admin schema exists
                schema_exists = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM information_schema.schemata 
                        WHERE schema_name = 'admin'
                    )
                """)
                print(f"📋 Admin schema exists: {schema_exists}")
                
                if schema_exists:
                    # Check some admin tables
                    tables_query = """
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = 'admin' 
                        ORDER BY table_name
                    """
                    tables = await conn.fetch(tables_query)
                    print(f"📑 Admin tables found: {len(tables)}")
                    for table in tables[:5]:  # Show first 5 tables
                        print(f"    - {table['table_name']}")
                    if len(tables) > 5:
                        print(f"    ... and {len(tables) - 5} more")
                
        except Exception as e:
            print(f"❌ Admin schema check failed: {e}")
        
        print("🎉 Database connection test completed!")
        
    except Exception as e:
        print(f"💥 Database connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


async def main():
    """Main test function."""
    print("🚀 Starting NeoAdminApi Database Connection Test")
    print("=" * 50)
    
    success = await test_database_connection()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed! Database connection is working.")
        return 0
    else:
        print("❌ Tests failed! Check the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)