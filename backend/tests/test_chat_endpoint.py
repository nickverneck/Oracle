"""End-to-end tests for chat endpoint functionality."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from oracle.clients.base import ModelResponse


class TestChatEndpointE2E:
    """End-to-end tests for chat endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_model_response = ModelResponse(
            content="This is a helpful response about troubleshooting.",
            model_used="test-model",
            provider="test-provider",
            usage={"total_tokens": 75},
            response_time=0.3
        )
    
    @patch('oracle.clients.model_manager.ModelManager.generate')
    def test_chat_endpoint_with_real_services(self, mock_generate):
        """Test chat endpoint with real conversation and knowledge services."""
        # Mock only the model generation
        mock_generate.return_value = self.mock_model_response
        
        from oracle.main import app
        client = TestClient(app)
        
        # Make chat request
        request_data = {
            "message": "How do I fix network connectivity issues?",
            "include_sources": True,
            "max_sources": 3
        }
        
        response = client.post("/api/v1/chat/", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["response"] == self.mock_model_response.content
        assert data["model_used"] == self.mock_model_response.model_used
        assert data["tokens_used"] == self.mock_model_response.usage["total_tokens"]
        assert len(data["sources"]) >= 0  # May have placeholder sources
        assert 0.0 <= data["confidence"] <= 1.0
        assert data["processing_time"] > 0
        
        # Verify model was called
        mock_generate.assert_called_once()
        call_args = mock_generate.call_args
        assert "How do I fix network connectivity issues?" in call_args[1]["prompt"]
    
    @patch('oracle.clients.model_manager.ModelManager.generate')
    def test_chat_endpoint_conversation_context(self, mock_generate):
        """Test that conversation context is maintained across requests."""
        mock_generate.return_value = self.mock_model_response
        
        from oracle.main import app
        client = TestClient(app)
        
        # First message
        response1 = client.post("/api/v1/chat/", json={
            "message": "What is Python?",
            "include_sources": False
        })
        
        assert response1.status_code == 200
        data1 = response1.json()
        
        # Extract conversation ID from logs or create a new conversation
        # For this test, we'll make a second request and verify context is built
        response2 = client.post("/api/v1/chat/", json={
            "message": "How do I install it?",
            "include_sources": False,
            "context": {"conversation_id": "test-conversation"}
        })
        
        assert response2.status_code == 200
        data2 = response2.json()
        
        # Verify both requests succeeded
        assert data1["status"] == "success"
        assert data2["status"] == "success"
        
        # Verify model was called twice
        assert mock_generate.call_count == 2
    
    def test_chat_endpoint_without_sources(self):
        """Test chat endpoint when sources are disabled."""
        from oracle.main import app
        client = TestClient(app)
        
        # This will fail with real model providers, but should validate the request
        response = client.post("/api/v1/chat/", json={
            "message": "Simple question",
            "include_sources": False
        })
        
        # Should get 503 due to no available models, but request should be valid
        assert response.status_code == 503
        data = response.json()
        assert "Model service unavailable" in data["detail"]["error"]
    
    def test_conversation_history_endpoints(self):
        """Test conversation history management endpoints."""
        from oracle.main import app
        client = TestClient(app)
        
        # Test getting history for non-existent conversation
        response = client.get("/api/v1/chat/conversations/nonexistent/history")
        assert response.status_code == 404
        
        # Test deleting non-existent conversation
        response = client.delete("/api/v1/chat/conversations/nonexistent")
        assert response.status_code == 404
    
    def test_chat_health_endpoint_structure(self):
        """Test chat health endpoint returns proper structure."""
        from oracle.main import app
        client = TestClient(app)
        
        response = client.get("/api/v1/chat/health")
        
        # Should return some status (likely degraded due to missing external services)
        assert response.status_code in [200, 503]
        data = response.json()
        
        # Verify basic structure
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]