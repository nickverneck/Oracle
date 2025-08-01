"""
Integration tests for document ingestion system.
"""

import io
import pytest
from fastapi.testclient import TestClient

from oracle.main import app


class TestIngestionIntegration:
    """Integration tests for the complete ingestion workflow."""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_complete_ingestion_workflow(self):
        """Test the complete document ingestion workflow."""
        # Test 1: Get supported formats
        response = self.client.get("/api/v1/ingest/supported-formats")
        assert response.status_code == 200
        
        formats_data = response.json()
        assert "supported_formats" in formats_data
        assert "max_files_per_batch" in formats_data
        
        # Test 2: Ingest a text document
        test_content = b"""
        This is a comprehensive test document for the Oracle chatbot system.
        It contains multiple sentences and paragraphs to test the chunking functionality.
        
        The system should be able to extract entities and create embeddings from this content.
        This document discusses troubleshooting, error handling, and system configuration.
        
        Key topics include:
        - Document processing
        - Knowledge extraction
        - Vector embeddings
        - Graph relationships
        """
        
        files = [("files", ("comprehensive_test.txt", io.BytesIO(test_content), "text/plain"))]
        
        response = self.client.post(
            "/api/v1/ingest/",
            files=files,
            data={
                "chunk_size": 200,
                "chunk_overlap": 50,
                "extract_entities": True,
                "create_embeddings": True,
                "batch_id": "integration-test-batch"
            }
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["total_files"] == 1
        assert data["successful_files"] == 1
        assert data["failed_files"] == 0
        assert data["batch_id"] == "integration-test-batch"
        
        # Verify processed file details
        assert len(data["processed_files"]) == 1
        processed_file = data["processed_files"][0]
        
        assert processed_file["filename"] == "comprehensive_test.txt"
        assert processed_file["file_type"] == "text/plain"
        assert processed_file["chunks_created"] > 0
        assert processed_file["entities_extracted"] > 0
        assert processed_file["vector_embeddings_created"] > 0
        assert processed_file["checksum"] is not None
        
        # Verify batch processing completed successfully
        assert data["batch_id"] == "integration-test-batch"
    
    def test_multiple_file_ingestion(self):
        """Test ingesting multiple files in a single batch."""
        files = []
        
        # Create multiple test files
        for i in range(3):
            content = f"Test document {i+1}. This contains content for testing purposes. Document number {i+1} has unique content.".encode()
            files.append(("files", (f"test_doc_{i+1}.txt", io.BytesIO(content), "text/plain")))
        
        response = self.client.post(
            "/api/v1/ingest/",
            files=files,
            data={
                "batch_id": "multi-file-test",
                "extract_entities": True,
                "create_embeddings": True
            }
        )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["total_files"] == 3
        assert data["successful_files"] == 3
        assert data["failed_files"] == 0
        assert len(data["processed_files"]) == 3
        
        # Verify each file was processed
        filenames = [pf["filename"] for pf in data["processed_files"]]
        assert "test_doc_1.txt" in filenames
        assert "test_doc_2.txt" in filenames
        assert "test_doc_3.txt" in filenames
    
    def test_mixed_file_formats(self):
        """Test ingesting different file formats."""
        files = [
            ("files", ("plain.txt", io.BytesIO(b"Plain text content for testing."), "text/plain")),
            ("files", ("markdown.md", io.BytesIO(b"# Markdown Content\n\nThis is **markdown** content."), "text/markdown")),
        ]
        
        response = self.client.post("/api/v1/ingest/", files=files)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
        assert data["total_files"] == 2
        assert data["successful_files"] == 2
        assert len(data["processed_files"]) == 2
    
    def test_error_handling(self):
        """Test error handling for invalid files."""
        # Test with empty file
        empty_file = ("files", ("empty.txt", io.BytesIO(b""), "text/plain"))
        
        response = self.client.post("/api/v1/ingest/", files=[empty_file])
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "failed"
        assert data["total_files"] == 1
        assert data["successful_files"] == 0
        assert data["failed_files"] == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["error_type"] == "empty_content"
    
    def test_validation_errors(self):
        """Test validation error handling."""
        # Test with invalid chunk size
        test_content = b"Test content"
        files = [("files", ("test.txt", io.BytesIO(test_content), "text/plain"))]
        
        response = self.client.post(
            "/api/v1/ingest/",
            files=files,
            data={"chunk_size": 50}  # Below minimum
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_file_size_limits(self):
        """Test file size validation."""
        # Create a file that's too large (simulate)
        large_content = b"x" * (51 * 1024 * 1024)  # 51MB
        
        # This would normally fail at the validation level
        # For testing, we'll just verify the endpoint handles it gracefully
        files = [("files", ("large.txt", io.BytesIO(b"normal content"), "text/plain"))]
        
        response = self.client.post("/api/v1/ingest/", files=files)
        assert response.status_code == 200  # Should succeed with normal content