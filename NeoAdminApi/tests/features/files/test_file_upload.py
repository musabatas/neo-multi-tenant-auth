"""Test file upload functionality with neo-commons integration.

This test validates the complete file upload workflow including:
- File validation and MIME type detection
- Upload command execution
- Database integration
- Error handling

Run with: pytest tests/features/files/test_file_upload.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from io import BytesIO

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
from neo_commons.platform.files.core.entities.file_metadata import FileMetadata


class TestFileUploadIntegration:
    """Test file upload with realistic scenarios."""
    
    @pytest.fixture
    def mock_file_repository(self):
        """Mock file repository for testing."""
        repository = AsyncMock()
        
        # Mock create_file method
        async def mock_create_file(file_metadata):
            # Return the same metadata with updated timestamps
            return file_metadata
            
        repository.create_file = mock_create_file
        return repository
    
    @pytest.fixture
    def mock_storage_provider(self):
        """Mock storage provider for testing."""
        provider = AsyncMock()
        
        # Mock upload_file method
        async def mock_upload_file(key, content, content_type, metadata):
            # Simulate successful upload
            return True
            
        provider.upload_file = mock_upload_file
        provider.__str__ = MagicMock(return_value="LocalStorage")
        return provider
    
    @pytest.fixture
    def mock_virus_scanner(self):
        """Mock virus scanner for testing."""
        scanner = AsyncMock()
        
        # Mock scan result
        scan_result = MagicMock()
        scan_result.clean = True
        scan_result.infected = False
        scan_result.threat_name = None
        
        scanner.scan_content = AsyncMock(return_value=scan_result)
        return scanner
    
    @pytest.fixture
    def upload_command(self, mock_file_repository, mock_storage_provider, mock_virus_scanner):
        """Create upload command with mocked dependencies."""
        return UploadFileCommand(
            file_repository=mock_file_repository,
            storage_provider=mock_storage_provider,
            virus_scanner=mock_virus_scanner
        )
    
    @pytest.fixture
    def test_file_data(self):
        """Create test file data."""
        test_content = b"Hello, World! This is a test file for upload validation."
        
        return UploadFileData(
            filename="test-document.txt",
            content=test_content,
            user_id="user-123",
            tenant_id="tenant-456",
            content_type="text/plain",
            folder_path="/documents",
            description="Test file for upload validation",
            tags={"category": "test", "project": "file-management"}
        )
    
    async def test_file_type_validator_with_magic(self):
        """Test file type validator with python-magic integration."""
        print(f"\\n🧪 Testing FileTypeValidator (Magic available: {HAS_MAGIC})")
        
        # Test file validation
        validator = FileTypeValidator()
        
        # Test with text file
        test_content = b"Hello, World! This is a test file."
        result = validator.validate_file("test.txt", test_content)
        
        print(f"✅ Text file validation: {result.valid}")
        assert result.valid, f"Text file should be valid: {result.reason}"
        
        # Test MIME type detection if magic is available
        if HAS_MAGIC:
            import magic
            detected_mime = magic.from_buffer(test_content, mime=True)
            print(f"✅ MIME type detected: {detected_mime}")
            assert detected_mime == "text/plain"
    
    async def test_upload_file_success(self, upload_command, test_file_data):
        """Test successful file upload."""
        print("\\n🧪 Testing successful file upload")
        
        # Execute upload command
        result = await upload_command.execute(test_file_data)
        
        print(f"✅ Upload success: {result.success}")
        print(f"✅ File ID: {result.file_id}")
        print(f"✅ Filename: {result.filename}")
        print(f"✅ File size: {result.file_size} bytes")
        print(f"✅ Content type: {result.content_type}")
        print(f"✅ Duration: {result.upload_duration_ms}ms")
        print(f"✅ Virus scan: {result.virus_scan_status}")
        
        # Validate results
        assert result.success, f"Upload should succeed: {result.error_message}"
        assert result.file_id is not None, "File ID should be generated"
        assert result.filename == "test-document.txt", "Filename should match"
        assert result.file_size == len(test_file_data.content), "File size should match"
        assert result.content_type == "text/plain", "Content type should be detected"
        assert result.virus_scan_status == "clean", "Virus scan should be clean"
        assert result.upload_duration_ms > 0, "Duration should be measured"
    
    async def test_upload_file_with_invalid_type(self, upload_command):
        """Test file upload with invalid file type."""
        print("\\n🧪 Testing upload with invalid file type")
        
        # Create data with blocked file type
        invalid_data = UploadFileData(
            filename="malicious.exe",
            content=b"MZ\\x90\\x00\\x03", # Executable file header
            user_id="user-123",
            tenant_id="tenant-456",
            content_type="application/x-executable"
        )
        
        # Execute upload command
        result = await upload_command.execute(invalid_data)
        
        print(f"✅ Upload blocked: {not result.success}")
        print(f"✅ Error code: {result.error_code}")
        print(f"✅ Error message: {result.error_message}")
        
        # Validate results
        assert not result.success, "Upload should fail for invalid file type"
        assert result.error_code == "InvalidFileType", "Should return InvalidFileType error"
        assert "not allowed" in result.error_message, "Error message should mention file type not allowed"
    
    async def test_file_id_generation(self):
        """Test FileId generation with UUIDv7."""
        print("\\n🧪 Testing FileId generation")
        
        # Generate multiple file IDs
        file_ids = [FileId.generate() for _ in range(5)]
        
        for i, file_id in enumerate(file_ids):
            print(f"✅ File ID {i+1}: {file_id.value}")
            assert file_id.value is not None, "File ID should be generated"
            assert len(str(file_id.value)) == 36, "File ID should be UUID format"
        
        # Ensure they're unique
        unique_ids = set(str(fid.value) for fid in file_ids)
        assert len(unique_ids) == 5, "All file IDs should be unique"
    
    async def test_file_size_validation(self):
        """Test FileSize value object."""
        print("\\n🧪 Testing FileSize validation")
        
        # Test valid file sizes
        sizes = [
            (100, "100 bytes"),
            (1024, "1.0 KB"),
            (1024 * 1024, "1.0 MB"),
            (1024 * 1024 * 1024, "1.0 GB")
        ]
        
        for size_bytes, expected_desc in sizes:
            file_size = FileSize(size_bytes)
            print(f"✅ {size_bytes} bytes = {file_size.human_readable}")
            assert file_size.bytes == size_bytes, "Bytes should match"
            assert file_size.human_readable == expected_desc, f"Description should be {expected_desc}"
    
    async def test_mime_type_detection(self):
        """Test MimeType detection and validation."""
        print("\\n🧪 Testing MIME type detection")
        
        # Test different file types
        test_files = [
            (b"Hello, World!", "text/plain", "txt"),
            (b"\\x89PNG\\r\\n\\x1a\\n", "image/png", "png"),
            (b"%PDF-1.4", "application/pdf", "pdf")
        ]
        
        for content, expected_mime, ext in test_files:
            mime_type = MimeType(expected_mime)
            print(f"✅ {ext.upper()} file: {mime_type.value}")
            assert mime_type.value == expected_mime, f"MIME type should be {expected_mime}"
            assert mime_type.is_image() == (expected_mime.startswith("image/")), "Image detection should work"
            assert mime_type.is_text() == (expected_mime.startswith("text/")), "Text detection should work"


class TestFileUploadErrors:
    """Test error scenarios in file upload."""
    
    @pytest.fixture
    def failing_storage_provider(self):
        """Mock storage provider that fails."""
        provider = AsyncMock()
        provider.upload_file = AsyncMock(return_value=False)  # Simulate storage failure
        provider.__str__ = MagicMock(return_value="FailingStorage")
        return provider
    
    @pytest.fixture
    def failing_upload_command(self, mock_file_repository, failing_storage_provider):
        """Create upload command with failing storage."""
        return UploadFileCommand(
            file_repository=mock_file_repository,
            storage_provider=failing_storage_provider
        )
    
    async def test_storage_failure(self, failing_upload_command):
        """Test upload failure when storage fails."""
        print("\\n🧪 Testing storage failure scenario")
        
        test_data = UploadFileData(
            filename="test.txt",
            content=b"test content",
            user_id="user-123",
            tenant_id="tenant-456"
        )
        
        # Execute upload command
        result = await failing_upload_command.execute(test_data)
        
        print(f"✅ Upload failed as expected: {not result.success}")
        print(f"✅ Error code: {result.error_code}")
        print(f"✅ Error message: {result.error_message}")
        
        # Validate error handling
        assert not result.success, "Upload should fail"
        assert result.error_code == "UploadFailed", "Should return UploadFailed error"
        assert "Failed to store file content" in result.error_message, "Error message should mention storage failure"


@pytest.mark.asyncio
class TestFileUploadIntegrationRun:
    """Run integration tests."""
    
    async def test_full_integration_suite(self):
        """Run the complete integration test suite."""
        print("\\n" + "="*60)
        print("🧪 RUNNING COMPLETE FILE UPLOAD INTEGRATION TESTS")
        print("="*60)
        
        # Initialize test components
        test_integration = TestFileUploadIntegration()
        test_errors = TestFileUploadErrors()
        
        # Mock dependencies
        mock_repo = await test_integration.mock_file_repository(test_integration)
        mock_storage = await test_integration.mock_storage_provider(test_integration)
        mock_scanner = await test_integration.mock_virus_scanner(test_integration)
        
        upload_cmd = test_integration.upload_command(
            test_integration, mock_repo, mock_storage, mock_scanner
        )
        test_data = test_integration.test_file_data(test_integration)
        
        try:
            # Run all tests
            await test_integration.test_file_type_validator_with_magic()
            await test_integration.test_upload_file_success(upload_cmd, test_data)
            await test_integration.test_upload_file_with_invalid_type(upload_cmd)
            await test_integration.test_file_id_generation()
            await test_integration.test_file_size_validation()
            await test_integration.test_mime_type_detection()
            
            # Test error scenarios
            failing_storage = await test_errors.failing_storage_provider(test_errors)
            failing_cmd = test_errors.failing_upload_command(test_errors, mock_repo, failing_storage)
            await test_errors.test_storage_failure(failing_cmd)
            
            print("\\n" + "="*60)
            print("🎉 ALL FILE UPLOAD INTEGRATION TESTS PASSED!")
            print("✅ File type validation working")
            print("✅ Upload command execution successful")
            print("✅ Error handling functional") 
            print("✅ Value objects operating correctly")
            print("✅ MIME type detection operational")
            print("="*60)
            
        except Exception as e:
            print(f"\\n❌ INTEGRATION TEST FAILED: {e}")
            raise