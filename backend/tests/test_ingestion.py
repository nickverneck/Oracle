"""
Tests for document ingestion functionality.
"""

import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile
from fastapi.testclient import TestClient

from oracle.main import app
from oracle.services.ingestion import IngestionService, DocumentParser, TextProcessor
from oracle.models.ingestion import ProcessingOptions, FileUploadInfo


class TestDocumentParser:
    """Test document parsing functionality."""
    
    def setup_method(self):
        self.parser = DocumentParser()
    
    @pytest.mark.asyncio
    async def test_parse_text_utf8(self):
        """Test parsing UTF-8 text content."""
        content = "Hello, world! This is a test document.".encode('utf-8')
        result = await self.parser.parse_text(content)
        assert result == "Hello, world! This is a test document."
    
    @pytest.mark.asyncio
    async def test_parse_text_latin1(self):
        """Test parsing Latin-1 encoded text."""
        content = "Café résumé naïve".encode('latin-1')
        result = await self.parser.parse_text(content)
        assert "Café" in result
    
    @pytest.mark.asyncio
    async def test_parse_text_invalid_encoding(self):
        """Test handling of invalid encoding."""
        # Create invalid UTF-8 bytes
        content = b'\xff\xfe\x00\x00invalid'
        result = await self.parser.parse_text(content)
        # Should fallback to alternative encoding
        assert isinstance(result, str)
    
    @pytest.mark.asyncio
    async def test_parse_pdf_mock(self):
        """Test PDF parsing with mocked PyPDF2."""
        with patch('oracle.services.ingestion.pypdf.PdfReader') as mock_reader:
            # Mock PDF reader
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Page content"
            mock_reader.return_value.pages = [mock_page]
            
            content = b"fake pdf content"
            result = await self.parser.parse_pdf(content)
            assert result == "Page content"
    
    @pytest.mark.asyncio
    async def test_parse_docx_mock(self):
        """Test DOCX parsing with mocked python-docx."""
        with patch('oracle.services.ingestion.DocxDocument') as mock_doc:
            # Mock DOCX document
            mock_paragraph = MagicMock()
            mock_paragraph.text = "Document paragraph"
            mock_doc.return_value.paragraphs = [mock_paragraph]
            
            content = b"fake docx content"
            result = await self.parser.parse_docx(content)
            assert result == "Document paragraph"
    
    @pytest.mark.asyncio
    async def test_parse_document_by_extension(self):
        """Test document parsing based on file extension."""
        # Test text file
        content = b"Plain text content"
        result = await self.parser.parse_document("test.txt", content)
        assert result == "Plain text content"
        
        # Test markdown file
        result = await self.parser.parse_document("test.md", content)
        assert result == "Plain text content"
    
    @pytest.mark.asyncio
    async def test_parse_document_unsupported_format(self):
        """Test handling of unsupported file formats."""
        content = b"some content"
        with pytest.raises(ValueError, match="Unsupported file format"):
            await self.parser.parse_document("test.xyz", content)


class TestTextProcessor:
    """Test text processing functionality."""
    
    def setup_method(self):
        self.options = ProcessingOptions(
            chunk_size=100,  # Minimum valid size
            chunk_overlap=20,
            extract_entities=True,
            create_embeddings=True,
        )
        self.processor = TextProcessor(self.options)
    
    def test_create_chunks_small_text(self):
        """Test chunking with text smaller than chunk size."""
        text = "Short text"
        chunks = self.processor.create_chunks(text)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_create_chunks_large_text(self):
        """Test chunking with text larger than chunk size."""
        words = ["word" + str(i) for i in range(200)]  # More words for larger text
        text = " ".join(words)
        chunks = self.processor.create_chunks(text)
        
        assert len(chunks) > 1
        # Check overlap
        first_chunk_words = chunks[0].split()
        second_chunk_words = chunks[1].split()
        assert len(first_chunk_words) == 100  # Updated to match chunk_size
        # Should have overlap
        assert any(word in second_chunk_words for word in first_chunk_words[-20:])
    
    def test_create_chunks_empty_text(self):
        """Test chunking with empty text."""
        chunks = self.processor.create_chunks("")
        assert chunks == []
        
        chunks = self.processor.create_chunks("   ")
        assert chunks == []
    
    def test_extract_entities(self):
        """Test entity extraction."""
        text = "The quick brown fox jumps over the lazy dog. The fox is quick."
        entities = self.processor.extract_entities(text)
        
        assert len(entities) > 0
        # Should extract frequent words
        entity_texts = [e["text"] for e in entities]
        assert "quick" in entity_texts  # Appears twice
        
        # Check entity structure
        for entity in entities:
            assert "text" in entity
            assert "type" in entity
            assert "frequency" in entity
            assert "confidence" in entity


class TestIngestionService:
    """Test ingestion service functionality."""
    
    def setup_method(self):
        self.service = IngestionService()
        self.processing_options = ProcessingOptions()
    
    @pytest.mark.asyncio
    async def test_calculate_checksum(self):
        """Test checksum calculation."""
        content = b"test content"
        checksum = await self.service.calculate_checksum(content)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA-256 hex length
        
        # Same content should produce same checksum
        checksum2 = await self.service.calculate_checksum(content)
        assert checksum == checksum2
    
    @pytest.mark.asyncio
    async def test_process_single_file_success(self):
        """Test successful processing of a single file."""
        # Create mock upload file
        content = b"This is test content for processing."
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=content)
        mock_file.seek = AsyncMock()
        
        file_info = FileUploadInfo(
            filename="test.txt",
            content_type="text/plain",
            size=len(content)
        )
        
        processed_file, error = await self.service.process_single_file(
            mock_file, file_info, self.processing_options
        )
        
        assert processed_file is not None
        assert error is None
        assert processed_file.filename == "test.txt"
        assert processed_file.file_size == len(content)
        assert processed_file.chunks_created > 0
        assert processed_file.checksum is not None
    
    @pytest.mark.asyncio
    async def test_process_single_file_parsing_error(self):
        """Test handling of parsing errors."""
        content = b"content"
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=content)
        mock_file.seek = AsyncMock()
        
        # Create file info with valid extension but mock parser to fail
        file_info = FileUploadInfo(
            filename="test.txt",
            content_type="text/plain",
            size=len(content)
        )
        
        # Mock the parser to raise an error
        with patch.object(self.service.parser, 'parse_document', side_effect=ValueError("Parsing failed")):
            processed_file, error = await self.service.process_single_file(
                mock_file, file_info, self.processing_options
            )
        
        assert processed_file is None
        assert error is not None
        assert error.error_type == "parsing_error"
        assert "Parsing failed" in error.error_message
    
    @pytest.mark.asyncio
    async def test_process_single_file_empty_content(self):
        """Test handling of empty content."""
        content = b"   "  # Only whitespace
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=content)
        mock_file.seek = AsyncMock()
        
        file_info = FileUploadInfo(
            filename="empty.txt",
            content_type="text/plain",
            size=len(content)
        )
        
        processed_file, error = await self.service.process_single_file(
            mock_file, file_info, self.processing_options
        )
        
        assert processed_file is None
        assert error is not None
        assert error.error_type == "empty_content"
    
    @pytest.mark.asyncio
    async def test_process_files_multiple(self):
        """Test processing multiple files."""
        # Create mock files
        files = []
        file_infos = []
        
        for i in range(3):
            content = f"Content for file {i}".encode()
            mock_file = MagicMock(spec=UploadFile)
            mock_file.read = AsyncMock(return_value=content)
            mock_file.seek = AsyncMock()
            files.append(mock_file)
            
            file_info = FileUploadInfo(
                filename=f"test{i}.txt",
                content_type="text/plain",
                size=len(content)
            )
            file_infos.append(file_info)
        
        result = await self.service.process_files(
            files, file_infos, self.processing_options, batch_id="test-batch"
        )
        
        assert result.total_files == 3
        assert result.successful_files == 3
        assert result.failed_files == 0
        assert len(result.processed_files) == 3
        assert len(result.errors) == 0
        assert result.batch_id == "test-batch"
    
    @pytest.mark.asyncio
    async def test_get_batch_status(self):
        """Test batch status retrieval."""
        batch_id = "test-batch"
        
        # Should raise error for non-existent batch
        with pytest.raises(ValueError, match="Batch .* not found"):
            await self.service.get_batch_status(batch_id)
        
        # Add batch status
        self.service.batch_status[batch_id] = {
            "status": "completed",
            "total_files": 5,
            "processed_files": 4,
        }
        
        status = await self.service.get_batch_status(batch_id)
        assert status["status"] == "completed"
        assert status["total_files"] == 5


class TestIngestionAPI:
    """Test ingestion API endpoints."""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_get_supported_formats(self):
        """Test getting supported file formats."""
        response = self.client.get("/api/v1/ingest/supported-formats")
        assert response.status_code == 200
        
        data = response.json()
        assert "supported_formats" in data
        assert "max_files_per_batch" in data
        assert "max_file_size_bytes" in data
        
        formats = data["supported_formats"]
        extensions = [fmt["extension"] for fmt in formats]
        assert ".pdf" in extensions
        assert ".txt" in extensions
        assert ".docx" in extensions
    
    def test_ingest_documents_no_files(self):
        """Test ingestion with no files provided."""
        response = self.client.post("/api/v1/ingest/")
        assert response.status_code == 422  # Validation error
    
    def test_ingest_documents_validation_error(self):
        """Test ingestion with invalid parameters."""
        # Create a small test file
        test_content = b"Test content"
        files = [("files", ("test.txt", io.BytesIO(test_content), "text/plain"))]
        
        # Invalid chunk_size (too small)
        response = self.client.post(
            "/api/v1/ingest/",
            files=files,
            data={"chunk_size": 50}  # Below minimum of 100
        )
        assert response.status_code == 422
    
    @patch('oracle.services.ingestion.IngestionService.process_files')
    def test_ingest_documents_success(self, mock_process):
        """Test successful document ingestion."""
        from oracle.models.ingestion import IngestionResponse, ProcessedFile
        
        # Mock successful response
        mock_processed_file = ProcessedFile(
            filename="test.txt",
            file_size=12,
            file_type="text/plain",
            entities_extracted=5,
            chunks_created=1,
            graph_nodes_added=5,
            graph_relationships_added=4,
            vector_embeddings_created=1,
            processing_time=0.1,
            checksum="abc123"
        )
        
        mock_response = IngestionResponse(
            status="success",
            processed_files=[mock_processed_file],
            errors=[],
            total_files=1,
            successful_files=1,
            failed_files=0,
            processing_time=0.1
        )
        
        mock_process.return_value = mock_response
        
        # Create test file
        test_content = b"Test content"
        files = [("files", ("test.txt", io.BytesIO(test_content), "text/plain"))]
        
        response = self.client.post("/api/v1/ingest/", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["total_files"] == 1
        assert data["successful_files"] == 1
        assert len(data["processed_files"]) == 1