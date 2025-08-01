"""
Unit tests for Oracle data models and validation schemas.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from oracle.models.chat import ChatRequest, ChatResponse, Source, ConversationContext
from oracle.models.ingestion import (
    ProcessingOptions, ProcessedFile, IngestionError, 
    IngestionRequest, IngestionResponse, FileUploadInfo
)
from oracle.models.errors import ErrorResponse, ErrorDetail, ErrorCode
from oracle.models.base import BaseResponse, TimestampedModel


class TestChatModels:
    """Test chat-related models."""
    
    def test_chat_request_valid(self):
        """Test valid chat request creation."""
        request = ChatRequest(
            message="How do I troubleshoot connection issues?",
            context={"user_id": "123"},
            model_preference="vllm",
            include_sources=True,
            max_sources=3
        )
        
        assert request.message == "How do I troubleshoot connection issues?"
        assert request.context == {"user_id": "123"}
        assert request.model_preference == "vllm"
        assert request.include_sources is True
        assert request.max_sources == 3
    
    def test_chat_request_message_validation(self):
        """Test chat request message validation."""
        # Empty message should fail
        with pytest.raises(ValidationError):
            ChatRequest(message="")
        
        # Whitespace-only message should fail
        with pytest.raises(ValidationError):
            ChatRequest(message="   ")
        
        # Too long message should fail
        with pytest.raises(ValidationError):
            ChatRequest(message="x" * 4001)
    
    def test_chat_request_model_preference_validation(self):
        """Test model preference validation."""
        # Valid model preferences
        for model in ["vllm", "ollama", "gemini"]:
            request = ChatRequest(message="test", model_preference=model)
            assert request.model_preference == model
        
        # Invalid model preference should fail
        with pytest.raises(ValidationError):
            ChatRequest(message="test", model_preference="invalid_model")
    
    def test_source_model(self):
        """Test Source model validation."""
        source = Source(
            type="graph",
            content="Connection troubleshooting guide",
            relevance_score=0.85,
            metadata={"document": "troubleshooting.pdf", "page": 5}
        )
        
        assert source.type == "graph"
        assert source.content == "Connection troubleshooting guide"
        assert source.relevance_score == 0.85
        assert source.metadata["document"] == "troubleshooting.pdf"
    
    def test_source_relevance_score_validation(self):
        """Test source relevance score validation."""
        # Valid scores
        Source(type="graph", content="test", relevance_score=0.0)
        Source(type="graph", content="test", relevance_score=1.0)
        Source(type="graph", content="test", relevance_score=0.5)
        
        # Invalid scores should fail
        with pytest.raises(ValidationError):
            Source(type="graph", content="test", relevance_score=-0.1)
        
        with pytest.raises(ValidationError):
            Source(type="graph", content="test", relevance_score=1.1)
    
    def test_chat_response(self):
        """Test ChatResponse model."""
        sources = [
            Source(type="graph", content="Graph content", relevance_score=0.9),
            Source(type="vector", content="Vector content", relevance_score=0.8)
        ]
        
        response = ChatResponse(
            status="success",
            processing_time=1.5,
            response="Here's how to troubleshoot connection issues...",
            confidence=0.92,
            sources=sources,
            model_used="vllm",
            tokens_used=150
        )
        
        assert response.status == "success"
        assert response.processing_time == 1.5
        assert response.response.startswith("Here's how to troubleshoot")
        assert response.confidence == 0.92
        assert len(response.sources) == 2
        assert response.model_used == "vllm"
        assert response.tokens_used == 150
    
    def test_conversation_context(self):
        """Test ConversationContext model."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        context = ConversationContext(
            conversation_id="conv_123",
            messages=messages,
            user_preferences={"language": "en"}
        )
        
        assert context.conversation_id == "conv_123"
        assert len(context.messages) == 2
        assert context.user_preferences["language"] == "en"
    
    def test_conversation_context_message_validation(self):
        """Test conversation context message validation."""
        # Invalid message format should fail
        with pytest.raises(ValidationError):
            ConversationContext(
                conversation_id="conv_123",
                messages=[{"content": "missing role"}]
            )
        
        # Invalid role should fail
        with pytest.raises(ValidationError):
            ConversationContext(
                conversation_id="conv_123",
                messages=[{"role": "invalid", "content": "test"}]
            )


class TestIngestionModels:
    """Test ingestion-related models."""
    
    def test_processing_options(self):
        """Test ProcessingOptions model."""
        options = ProcessingOptions(
            chunk_size=1500,
            chunk_overlap=300,
            extract_entities=True,
            create_embeddings=True,
            language="en"
        )
        
        assert options.chunk_size == 1500
        assert options.chunk_overlap == 300
        assert options.extract_entities is True
        assert options.create_embeddings is True
        assert options.language == "en"
    
    def test_processing_options_validation(self):
        """Test ProcessingOptions validation."""
        # Chunk overlap >= chunk size should fail
        with pytest.raises(ValidationError):
            ProcessingOptions(chunk_size=1000, chunk_overlap=1000)
        
        with pytest.raises(ValidationError):
            ProcessingOptions(chunk_size=1000, chunk_overlap=1500)
    
    def test_processed_file(self):
        """Test ProcessedFile model."""
        file = ProcessedFile(
            filename="document.pdf",
            file_size=1024000,
            file_type="application/pdf",
            entities_extracted=25,
            chunks_created=10,
            graph_nodes_added=30,
            graph_relationships_added=45,
            vector_embeddings_created=10,
            processing_time=5.2,
            checksum="abc123"
        )
        
        assert file.filename == "document.pdf"
        assert file.file_size == 1024000
        assert file.entities_extracted == 25
        assert file.chunks_created == 10
        assert file.processing_time == 5.2
        assert file.checksum == "abc123"
        assert isinstance(file.created_at, datetime)
    
    def test_ingestion_error(self):
        """Test IngestionError model."""
        error = IngestionError(
            filename="corrupted.pdf",
            error_type="FILE_CORRUPTED",
            error_message="Unable to parse PDF file",
            error_code="PDF_PARSE_ERROR",
            retry_possible=False,
            suggestions=["Try converting to a different format", "Check file integrity"]
        )
        
        assert error.filename == "corrupted.pdf"
        assert error.error_type == "FILE_CORRUPTED"
        assert error.retry_possible is False
        assert len(error.suggestions) == 2
    
    def test_ingestion_response(self):
        """Test IngestionResponse model."""
        processed_files = [
            ProcessedFile(
                filename="doc1.pdf",
                file_size=1000,
                file_type="pdf",
                entities_extracted=10,
                chunks_created=5,
                graph_nodes_added=15,
                graph_relationships_added=20,
                vector_embeddings_created=5,
                processing_time=2.0
            )
        ]
        
        errors = [
            IngestionError(
                filename="doc2.pdf",
                error_type="CORRUPTED",
                error_message="File corrupted"
            )
        ]
        
        response = IngestionResponse(
            status="partial_success",
            processing_time=3.5,
            processed_files=processed_files,
            errors=errors,
            total_files=2,
            successful_files=1,
            failed_files=1,
            batch_id="batch_123"
        )
        
        assert response.status == "partial_success"
        assert response.total_files == 2
        assert response.successful_files == 1
        assert response.failed_files == 1
        assert len(response.processed_files) == 1
        assert len(response.errors) == 1
    
    def test_file_upload_info(self):
        """Test FileUploadInfo model."""
        info = FileUploadInfo(
            filename="document.pdf",
            content_type="application/pdf",
            size=1024000
        )
        
        assert info.filename == "document.pdf"
        assert info.content_type == "application/pdf"
        assert info.size == 1024000
    
    def test_file_upload_info_validation(self):
        """Test FileUploadInfo validation."""
        # Unsupported file type should fail
        with pytest.raises(ValidationError):
            FileUploadInfo(
                filename="document.exe",
                content_type="application/exe",
                size=1000
            )
        
        # File too large should fail
        with pytest.raises(ValidationError):
            FileUploadInfo(
                filename="document.pdf",
                content_type="application/pdf",
                size=100 * 1024 * 1024  # 100MB
            )


class TestErrorModels:
    """Test error-related models."""
    
    def test_error_detail(self):
        """Test ErrorDetail model."""
        detail = ErrorDetail(
            field="message",
            message="Field is required",
            code="REQUIRED_FIELD",
            context={"expected_type": "string"}
        )
        
        assert detail.field == "message"
        assert detail.message == "Field is required"
        assert detail.code == "REQUIRED_FIELD"
        assert detail.context["expected_type"] == "string"
    
    def test_error_response(self):
        """Test ErrorResponse model."""
        details = [
            ErrorDetail(field="message", message="Field is required")
        ]
        
        response = ErrorResponse(
            error_code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            details=details,
            request_id="req_123",
            timestamp="2024-01-01T00:00:00Z",
            path="/api/v1/chat",
            suggestions=["Check required fields"]
        )
        
        assert response.error is True
        assert response.error_code == ErrorCode.VALIDATION_ERROR
        assert response.message == "Request validation failed"
        assert len(response.details) == 1
        assert response.request_id == "req_123"
        assert len(response.suggestions) == 1


class TestBaseModels:
    """Test base models."""
    
    def test_base_response(self):
        """Test BaseResponse model."""
        response = BaseResponse(
            status="success",
            processing_time=1.5,
            metadata={"version": "1.0"}
        )
        
        assert response.status == "success"
        assert response.processing_time == 1.5
        assert response.metadata["version"] == "1.0"
    
    def test_timestamped_model(self):
        """Test TimestampedModel."""
        model = TimestampedModel()
        
        assert isinstance(model.created_at, datetime)
        assert model.updated_at is None

class TestValidationUtilities:
    """Test validation utility functions."""
    
    def test_validate_and_parse_success(self):
        """Test successful validation and parsing."""
        from oracle.models.validation import validate_and_parse
        
        data = {
            "message": "Test message",
            "include_sources": True,
            "max_sources": 3
        }
        
        result = validate_and_parse(ChatRequest, data)
        assert isinstance(result, ChatRequest)
        assert result.message == "Test message"
        assert result.include_sources is True
        assert result.max_sources == 3
    
    def test_validate_and_parse_failure(self):
        """Test validation failure handling."""
        from oracle.models.validation import validate_and_parse
        from fastapi import HTTPException
        
        data = {
            "message": "",  # Invalid empty message
            "max_sources": 25  # Invalid max sources (> 20)
        }
        
        # Should raise HTTPException by default
        with pytest.raises(HTTPException):
            validate_and_parse(ChatRequest, data)
        
        # Should return None when raise_on_error=False
        result = validate_and_parse(ChatRequest, data, raise_on_error=False)
        assert result is None
    
    def test_serialize_model(self):
        """Test model serialization."""
        from oracle.models.validation import serialize_model
        
        request = ChatRequest(
            message="Test message",
            context={"user_id": "123"},
            model_preference=None  # This should be excluded
        )
        
        serialized = serialize_model(request, exclude_none=True)
        assert "message" in serialized
        assert "context" in serialized
        assert "model_preference" not in serialized  # Excluded because None
    
    def test_validate_file_upload_valid(self):
        """Test valid file upload validation."""
        from oracle.models.validation import validate_file_upload
        
        errors = validate_file_upload(
            filename="document.pdf",
            content_type="application/pdf",
            size=1024000  # 1MB
        )
        
        assert errors is None
    
    def test_validate_file_upload_invalid(self):
        """Test invalid file upload validation."""
        from oracle.models.validation import validate_file_upload
        
        # Test unsupported file type
        errors = validate_file_upload(
            filename="document.exe",
            content_type="application/exe",
            size=1000
        )
        assert errors is not None
        assert len(errors) == 1
        assert "not supported" in errors[0].message
        
        # Test file too large
        errors = validate_file_upload(
            filename="document.pdf",
            content_type="application/pdf",
            size=100 * 1024 * 1024  # 100MB
        )
        assert errors is not None
        assert len(errors) == 1
        assert "exceeds maximum limit" in errors[0].message
        
        # Test empty file
        errors = validate_file_upload(
            filename="document.pdf",
            content_type="application/pdf",
            size=0
        )
        assert errors is not None
        assert len(errors) == 1
        assert "cannot be empty" in errors[0].message
    
    def test_validate_chat_message_valid(self):
        """Test valid chat message validation."""
        from oracle.models.validation import validate_chat_message
        
        errors = validate_chat_message("This is a valid message")
        assert errors is None
    
    def test_validate_chat_message_invalid(self):
        """Test invalid chat message validation."""
        from oracle.models.validation import validate_chat_message
        
        # Test empty message
        errors = validate_chat_message("")
        assert errors is not None
        assert len(errors) == 1
        assert "cannot be empty" in errors[0].message
        
        # Test whitespace-only message
        errors = validate_chat_message("   ")
        assert errors is not None
        assert len(errors) == 1
        assert "cannot be empty" in errors[0].message
        
        # Test message too long
        long_message = "x" * 4001
        errors = validate_chat_message(long_message)
        assert errors is not None
        assert len(errors) == 1
        assert "too long" in errors[0].message
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from oracle.models.validation import sanitize_filename
        
        # Test normal filename
        result = sanitize_filename("document.pdf")
        assert result == "document.pdf"
        
        # Test filename with unsafe characters
        result = sanitize_filename("my document!@#$%^&*().pdf")
        assert result == "my_document__________.pdf"
        
        # Test filename starting with dot/dash
        result = sanitize_filename(".-document.pdf")
        assert result == "document.pdf"
        
        # Test empty filename
        result = sanitize_filename(".pdf")
        assert result == "unnamed_file.pdf"
        
        # Test very long filename
        long_name = "x" * 150 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 104  # 100 chars + ".pdf"