"""Simple file upload test without pytest fixtures.

This test validates the file upload functionality in a standalone way.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
import uuid

# Neo-commons imports
from neo_commons.platform.files.application.commands.upload_file import (
    UploadFileCommand, 
    UploadFileData, 
    UploadFileResult
)
from neo_commons.platform.files.application.validators.file_type_validator import (
    FileTypeValidator,
    HAS_MAGIC
)
from neo_commons.platform.files.core.value_objects.file_id import FileId
from neo_commons.platform.files.core.value_objects.file_size import FileSize
from neo_commons.platform.files.core.value_objects.mime_type import MimeType


class MockFileRepository:
    """Mock file repository for testing."""
    
    async def create_file(self, file_metadata):
        """Mock create_file method."""
        print(f"📝 Mock Repository: Creating file {file_metadata.original_name}")
        # Return the same metadata (simulating successful creation)
        return file_metadata


class MockStorageProvider:
    """Mock storage provider for testing."""
    
    async def upload_file(self, key, content, content_type, metadata):
        """Mock upload_file method."""
        print(f"☁️  Mock Storage: Uploading {key} ({content_type})")
        # Simulate successful upload
        return True
    
    def __str__(self):
        return "local"


class MockVirusScanner:
    """Mock virus scanner for testing."""
    
    async def scan_content(self, content):
        """Mock scan_content method."""
        print(f"🛡️  Mock Scanner: Scanning {len(content)} bytes")
        
        # Mock scan result
        scan_result = MagicMock()
        scan_result.clean = True
        scan_result.infected = False
        scan_result.threat_name = None
        
        return scan_result


async def test_file_upload_workflow():
    """Test complete file upload workflow."""
    
    print("\\n" + "="*60)
    print("🧪 FILE UPLOAD INTEGRATION TEST")
    print("="*60)
    
    try:
        # Test 1: File Type Validator
        print("\\n1️⃣  Testing File Type Validator...")
        validator = FileTypeValidator()
        
        test_content = b"Hello, World! This is a test file for upload validation."
        result = validator.validate_file("test.txt", test_content, "text/plain")
        
        print(f"   ✅ Magic available: {HAS_MAGIC}")
        print(f"   ✅ Validation result: {result.valid}")
        if not result.valid:
            print(f"   ❌ Validation reason: {result.reason}")
        
        assert result.valid, f"File validation failed: {result.reason}"
        
        # Test 2: MIME Type Detection
        print("\\n2️⃣  Testing MIME Type Detection...")
        if HAS_MAGIC:
            import magic
            detected_mime = magic.from_buffer(test_content, mime=True)
            print(f"   ✅ Detected MIME type: {detected_mime}")
            assert detected_mime == "text/plain"
        else:
            print("   ⚠️  Magic not available, using fallback")
        
        # Test 3: Value Objects
        print("\\n3️⃣  Testing Value Objects...")
        
        # File ID generation
        file_id = FileId.generate()
        print(f"   ✅ Generated File ID: {file_id.value}")
        assert file_id.value is not None
        
        # File size handling
        file_size = FileSize(len(test_content))
        print(f"   ✅ File size: {file_size.value} bytes ({file_size.format_human_readable()})")
        assert file_size.value == len(test_content)
        
        # MIME type handling
        mime_type = MimeType("text/plain")
        print(f"   ✅ MIME type: {mime_type.value}")
        print(f"   ✅ Is text: {mime_type.is_text()}")
        print(f"   ✅ Is image: {mime_type.is_image()}")
        assert mime_type.is_text()
        assert not mime_type.is_image()
        
        # Test 4: Upload Command Execution
        print("\\n4️⃣  Testing Upload Command...")
        
        # Create mock dependencies
        mock_repository = MockFileRepository()
        mock_storage = MockStorageProvider()
        mock_scanner = MockVirusScanner()
        
        # Create upload command
        upload_command = UploadFileCommand(
            file_repository=mock_repository,
            storage_provider=mock_storage,
            virus_scanner=mock_scanner
        )
        
        # Create upload data
        user_uuid = str(uuid.uuid4())
        tenant_uuid = str(uuid.uuid4())
        
        upload_data = UploadFileData(
            filename="test-document.txt",
            content=test_content,
            user_id=user_uuid,
            tenant_id=tenant_uuid,
            content_type="text/plain",
            folder_path="/documents",
            description="Test file for integration testing",
            tags={"category": "test", "project": "file-management"}
        )
        
        print(f"   📋 Upload data prepared:")
        print(f"      - Filename: {upload_data.filename}")
        print(f"      - Size: {len(upload_data.content)} bytes")
        print(f"      - User: {upload_data.user_id}")
        print(f"      - Tenant: {upload_data.tenant_id}")
        
        # Execute upload
        print("   🚀 Executing upload...")
        start_time = datetime.utcnow()
        upload_result = await upload_command.execute(upload_data)
        end_time = datetime.utcnow()
        
        duration = int((end_time - start_time).total_seconds() * 1000)
        
        print(f"   ⏱️  Upload completed in {duration}ms")
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
        else:
            print(f"   ❌ Upload failed:")
            print(f"      - Error code: {upload_result.error_code}")
            print(f"      - Error message: {upload_result.error_message}")
        
        # Validate results
        assert upload_result.success, f"Upload failed: {upload_result.error_message}"
        assert upload_result.file_id is not None, "File ID should be generated"
        assert upload_result.filename == "test-document.txt", "Filename should match"
        assert upload_result.file_size == len(test_content), "File size should match"
        assert upload_result.content_type == "text/plain", "Content type should be correct"
        assert upload_result.virus_scan_status == "clean", "Virus scan should be clean"
        assert upload_result.upload_duration_ms >= 0, "Duration should be measured"
        assert upload_result.checksum, "Checksum should be generated"
        assert upload_result.storage_key, "Storage key should be generated"
        
        # Test 5: Error Handling
        print("\\n5️⃣  Testing Error Handling...")
        
        # Test with invalid file type
        invalid_data = UploadFileData(
            filename="malicious.exe", 
            content=b"MZ\\x90\\x00\\x03",  # Executable header
            user_id=user_uuid,
            tenant_id=tenant_uuid,
            content_type="application/x-executable"
        )
        
        print("   🚫 Testing upload with invalid file type...")
        error_result = await upload_command.execute(invalid_data)
        
        print(f"   ✅ Upload rejected: {not error_result.success}")
        if not error_result.success:
            print(f"      - Error code: {error_result.error_code}")
            print(f"      - Error message: {error_result.error_message}")
        
        assert not error_result.success, "Upload should fail for invalid file type"
        
        print("\\n" + "="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("✅ File type validation: WORKING")
        print("✅ MIME type detection: WORKING") 
        print("✅ Value objects: WORKING")
        print("✅ Upload command: WORKING")
        print("✅ Error handling: WORKING")
        print("✅ File upload workflow: FULLY FUNCTIONAL")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run the test
    result = asyncio.run(test_file_upload_workflow())
    exit(0 if result else 1)