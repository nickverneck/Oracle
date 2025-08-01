"""Integration tests for chat functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from oracle.models.chat import Source
from oracle.clients.base import ModelResponse


class TestChatIntegration:
    """Integration tests for chat endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock model response
        self.mock_model_response = ModelResponse(
            content="This is a test response from the AI model.",
            model_used="test-model",
            provider="test-provider",
            usage={"total_tokens": 50},
            response_time=0.5
        )
        
        # Mock knowledge sources
        self.mock_sources = [
            Source(
                type="graph",
                content="Graph-based knowledge about the query",
                relevance_score=0.9,
                metadata={"source": "neo4j", "entities": ["test"]}
            ),
            Source(
                type="vector",
                content="Vector-based semantic match",
                relevance_score=0.8,
                metadata={"source": "chromadb", "similarity": 0.85}
            )
        ]
    
    @patch('oracle.clients.model_manager.ModelManager')
    @patch('oracle.services.knowledge.KnowledgeRetrievalService')
    @patch('oracle.services.conversation.ConversationManager')
    def test_chat_endpoint_success_with_mocked_services(self, mock_conv_class, mock_knowledge_class, mock_model_class):
        """Test successful chat request with mocked services."""
        # Setup service mocks
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.create_conversation.return_value = "test-conv-id"
        mock_conversation_manager.add_message.return_value = True
        mock_conversation_manager.build_context_prompt.return_value = "Test prompt with context"
        mock_conversation_manager.get_conversation_history.return_value = []
        mock_conv_class.return_value = mock_conversation_manager
        
        mock_knowledge_service = AsyncMock()
        mock_knowledge_service.retrieve_knowledge.return_value = self.mock_sources
        mock_knowledge_class.return_value = mock_knowledge_service
        
        mock_model_manager = AsyncMock()
        mock_model_manager.generate.return_value = self.mock_model_response
        mock_model_class.return_value = mock_model_manager
        
        # Import app after mocking to ensure mocks are applied
        from oracle.main import app
        client = TestClient(app)
        
        # Make request
        request_data = {
            "message": "How do I troubleshoot connection issues?",
            "include_sources": True,
            "max_sources": 5
        }
        
        response = client.post("/api/v1/chat/", json=request_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["response"] == self.mock_model_response.content
        assert data["model_used"] == self.mock_model_response.model_used
        assert data["tokens_used"] == self.mock_model_response.usage["total_tokens"]
        assert len(data["sources"]) == 2
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["processing_time"] > 0
        
        # Verify service calls
        mock_knowledge_service.retrieve_knowledge.assert_called_once()
        mock_model_manager.generate.assert_called_once()
        mock_conversation_manager.create_conversation.assert_called_once()
        assert mock_conversation_manager.add_message.call_count >= 1
    
    def test_chat_endpoint_validation_errors(self):
        """Test chat request validation errors."""
        from oracle.main import app
        client = TestClient(app)
        
        # Empty message
        response = client.post("/api/v1/chat/", json={"message": ""})
        assert response.status_code == 422
        
        # Message too long
        long_message = "x" * 5000
        response = client.post("/api/v1/chat/", json={"message": long_message})
        assert response.status_code == 422
        
        # Invalid model preference
        response = client.post("/api/v1/chat/", json={
            "message": "test",
            "model_preference": "invalid_model"
        })
        assert response.status_code == 422
        
        # Invalid max_sources
        response = client.post("/api/v1/chat/", json={
            "message": "test",
            "max_sources": 0
        })
        assert response.status_code == 422
    
    def test_chat_health_endpoint(self):
        """Test chat health check endpoint."""
        from oracle.main import app
        client = TestClient(app)
        
        response = client.get("/api/v1/chat/health")
        
        # Should return some status (may be degraded due to missing services)
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "timestamp" in data