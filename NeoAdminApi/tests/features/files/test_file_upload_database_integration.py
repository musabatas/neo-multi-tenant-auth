"""Database integration test for file upload functionality.

This test creates minimal infrastructure implementations to test 
the actual database persistence with real connections.
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
import os

# Neo-commons imports
from neo_commons.platform.files.application.commands.upload_file import (
    UploadFileCommand, 
    UploadFileData, 
    UploadFileResult
)
from neo_commons.platform.files.core.protocols.file_repository import FileRepository
from neo_commons.platform.files.core.protocols.storage_provider import StorageProviderProtocol
from neo_commons.platform.files.core.entities.file_metadata import FileMetadata
from neo_commons.core.value_objects.identifiers import TenantId, UserId

# Add NeoAdminApi to Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Database service from NeoAdminApi
from src.common.dependencies import get_database_service


class TestFileRepository(FileRepository):
    """Test file repository that writes to actual admin database."""
    
    def __init__(self, database_service):
        self.database_service = database_service
    
    async def create_file(self, file_metadata: FileMetadata) -> FileMetadata:
        """Create file record in admin.files table."""
        async with self.database_service.get_connection("admin") as connection:
            
            # Insert into admin.files table
            query = """
                INSERT INTO admin.files (
                    id, file_name, original_name, file_path, storage_provider, 
                    storage_key, mime_type, file_size, checksum_sha256, 
                    uploaded_by_user_id, tenant_id, description, tags,
                    virus_scan_status, created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                )
            """
            
            # Extract checksum hash from "algorithm:hash" format
            checksum_hash = file_metadata.checksum.get_digest() if file_metadata.checksum else None
            
            await connection.execute(
                query,
                file_metadata.id.value,                          # $1
                file_metadata.original_name,                     # $2 - file_name
                file_metadata.original_name,                     # $3 - original_name  
                str(file_metadata.path.value),                   # $4 - file_path
                file_metadata.storage_provider.value,            # $5 - storage_provider
                file_metadata.storage_key.value,                 # $6 - storage_key
                file_metadata.mime_type.value,                   # $7 - mime_type
                file_metadata.size.value,                        # $8 - file_size
                checksum_hash,                                    # $9 - checksum_sha256
                file_metadata.created_by.value if file_metadata.created_by else None,  # $10
                file_metadata.tenant_id.value,                   # $11 - tenant_id
                file_metadata.description,                       # $12 - description
                list(file_metadata.tags) if file_metadata.tags else None,  # $13 - tags
                "clean",                                          # $14 - virus_scan_status
                file_metadata.created_at,                        # $15 - created_at
                file_metadata.updated_at                         # $16 - updated_at
            )
            
            print(f"📝 Database: File record created with ID {file_metadata.id.value}")
            return file_metadata


class TestStorageProvider(StorageProviderProtocol):
    """Test storage provider that writes to local filesystem."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    async def upload_file(self, key: str, content, content_type: str, metadata: dict) -> bool:
        """Upload file to local storage."""
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content to file
        if hasattr(content, 'read'):
            content_bytes = content.read()
            content.seek(0)  # Reset for potential reuse
        else:
            content_bytes = content
        
        file_path.write_bytes(content_bytes)
        print(f"☁️  Storage: File uploaded to {file_path}")
        return True
    
    async def delete_file(self, key: str) -> bool:
        """Delete file from local storage."""
        file_path = self.base_path / key
        if file_path.exists():
            file_path.unlink()
            print(f"🗑️  Storage: File deleted from {file_path}")
            return True
        return False
    
    def __str__(self):
        return "local"


async def test_file_upload_database_integration():
    """Test complete file upload workflow with real database integration."""
    
    print("\n" + "="*60)
    print("🧪 FILE UPLOAD DATABASE INTEGRATION TEST")
    print("="*60)
    
    try:
        # Step 1: Setup database connection
        print("\n1️⃣  Setting up database connection...")
        database_service = await get_database_service()
        print(f"   ✅ Database service initialized")
        
        # Verify database connection
        connections = await database_service.connection_registry.get_all_connections()
        print(f"   ✅ Available connections: {len(connections)}")
        if isinstance(connections, dict):
            for conn_name in connections.keys():
                print(f"      - {conn_name}")
        else:
            print("      - admin (main connection)")
        
        # Step 2: Setup test file repository
        print("\n2️⃣  Setting up test file repository...")
        file_repository = TestFileRepository(database_service)
        print(f"   ✅ Test file repository initialized")
        
        # Step 3: Setup test storage provider
        print("\n3️⃣  Setting up test storage provider...")
        # Create temp storage directory
        temp_storage_path = Path("/tmp/neo_file_uploads")
        temp_storage_path.mkdir(exist_ok=True)
        
        storage_provider = TestStorageProvider(str(temp_storage_path))
        print(f"   ✅ Test storage provider initialized at {temp_storage_path}")
        
        # Step 4: Create upload command with test implementations
        print("\n4️⃣  Creating upload command with test implementations...")
        upload_command = UploadFileCommand(
            file_repository=file_repository,
            storage_provider=storage_provider,
            virus_scanner=None  # Optional for testing
        )
        print(f"   ✅ Upload command created")
        
        # Step 5: Prepare test data
        print("\n5️⃣  Preparing test data...")
        test_content = b"Hello, World! This is a real database integration test file."
        user_uuid = str(uuid.uuid4())
        tenant_uuid = str(uuid.uuid4())
        
        upload_data = UploadFileData(
            filename="integration-test.txt",
            content=test_content,
            user_id=user_uuid,
            tenant_id=tenant_uuid,
            content_type="text/plain",
            folder_path="/integration-tests",
            description="Database integration test file",
            tags={"category": "integration", "test": "database"}
        )
        
        print(f"   📋 Upload data prepared:")
        print(f"      - Filename: {upload_data.filename}")
        print(f"      - Size: {len(upload_data.content)} bytes")
        print(f"      - User: {upload_data.user_id}")
        print(f"      - Tenant: {upload_data.tenant_id}")
        
        # Step 6: Execute file upload
        print("\n6️⃣  Executing file upload...")
        start_time = datetime.utcnow()
        upload_result = await upload_command.execute(upload_data)
        end_time = datetime.utcnow()
        
        duration = int((end_time - start_time).total_seconds() * 1000)
        print(f"   ⏱️  Upload completed in {duration}ms")
        
        # Step 7: Validate upload results
        print("\n7️⃣  Validating upload results...")
        print(f"   ✅ Upload success: {upload_result.success}")
        
        if upload_result.success:
            print(f"   📄 Results:")
            print(f"      - File ID: {upload_result.file_id}")
            print(f"      - Filename: {upload_result.filename}")
            print(f"      - File path: {upload_result.file_path}")
            print(f"      - File size: {upload_result.file_size} bytes")
            print(f"      - Content type: {upload_result.content_type}")
            print(f"      - Storage key: {upload_result.storage_key}")
            print(f"      - Checksum: {upload_result.checksum[:16]}...")
            print(f"      - Duration: {upload_result.upload_duration_ms}ms")
            print(f"      - Virus scan: {upload_result.virus_scan_status}")
            
            # Step 8: Verify database record
            print("\n8️⃣  Verifying database record...")
            
            # Check admin.files table
            async with database_service.get_connection("admin") as admin_conn:
                result = await admin_conn.fetchrow(
                    "SELECT id, file_name, original_name, file_size, mime_type FROM admin.files WHERE id = $1",
                    uuid.UUID(upload_result.file_id)
                )
            
            if result:
                print(f"   ✅ Database record found:")
                print(f"      - ID: {result['id']}")
                print(f"      - File name: {result['file_name']}")
                print(f"      - Original name: {result['original_name']}")
                print(f"      - File size: {result['file_size']}")
                print(f"      - MIME type: {result['mime_type']}")
            else:
                print(f"   ❌ No database record found!")
                return False
            
            # Step 9: Verify file storage
            print("\n9️⃣  Verifying file storage...")
            storage_file = temp_storage_path / upload_result.storage_key
            if storage_file.exists():
                stored_content = storage_file.read_bytes()
                if stored_content == test_content:
                    print(f"   ✅ File correctly stored at {storage_file}")
                    print(f"   ✅ Content matches original")
                else:
                    print(f"   ❌ Content mismatch!")
                    return False
            else:
                print(f"   ❌ File not found at {storage_file}")
                return False
            
            # Step 10: Cleanup (DISABLED FOR DEBUGGING)
            print("\n🔟  Cleanup disabled - leaving record for verification...")
            print(f"   ℹ️  File ID to check: {upload_result.file_id}")
            print(f"   ℹ️  Storage file: {storage_file}")
            # # Delete file from storage
            # if storage_file.exists():
            #     storage_file.unlink()
            #     print(f"   ✅ Storage file deleted")
            # 
            # # Delete database record
            # async with database_service.get_connection("admin") as admin_conn:
            #     await admin_conn.execute(
            #         "DELETE FROM admin.files WHERE id = $1",
            #         uuid.UUID(upload_result.file_id)
            #     )
            # print(f"   ✅ Database record deleted")
            
        else:
            print(f"   ❌ Upload failed:")
            print(f"      - Error code: {upload_result.error_code}")
            print(f"      - Error message: {upload_result.error_message}")
            return False
        
        print("\n" + "="*60)
        print("🎉 DATABASE INTEGRATION TEST PASSED!")
        print("="*60)
        print("✅ Database connection: WORKING")
        print("✅ File repository: WORKING") 
        print("✅ Storage adapter: WORKING")
        print("✅ Upload command: WORKING")
        print("✅ Database persistence: WORKING")
        print("✅ File storage: WORKING")
        print("✅ End-to-end workflow: FULLY FUNCTIONAL")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ DATABASE INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the database integration test
    result = asyncio.run(test_file_upload_database_integration())
    exit(0 if result else 1)