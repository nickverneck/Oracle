"""Tests for chat endpoint and related functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from oracle.models.chat import ChatRequest, ChatResponse, Source
from oracle.services.conversation import ConversationManager
from oracle.services.knowledge import KnowledgeRetrievalService
from oracle.clients.model_manager import ModelManager
from oracle.clients.base import ModelResponse
from oracle.models.errors import ModelClientError


class TestChatEndpoint:
    """Test cases for the chat endpoint."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Import app here to avoid circular imports
        from oracle.main import app
        self.client = TestClient(app)
        
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
    
    @patch('oracle.api.endpoints.chat.get_model_manager')
    @patch('oracle.api.endpoints.chat.get_knowledge_service')
    @patch('oracle.api.endpoints.chat.get_conversation_manager')
    def test_chat_endpoint_success(self, mock_conv_mgr, mock_knowledge_svc, mock_model_mgr):
        """Test successful chat request."""
        # Setup mocks
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.create_conversation.return_value = "test-conv-id"
        mock_conversation_manager.add_message.return_value = True
        mock_conversation_manager.build_context_prompt.return_value = "Test prompt"
        mock_conversation_manager.get_conversation_history.return_value = []
        mock_conv_mgr.return_value = mock_conversation_manager
        
        mock_knowledge_service = AsyncMock()
        mock_knowledge_service.retrieve_knowledge.return_value = self.mock_sources
        mock_knowledge_svc.return_value = mock_knowledge_service
        
        mock_model_manager = AsyncMock()
        mock_model_manager.generate.return_value = self.mock_model_response
        mock_model_mgr.return_value = mock_model_manager
        
        # Make request
        request_data = {
            "message": "How do I troubleshoot connection issues?",
            "include_sources": True,
            "max_sources": 5
        }
        
        response = self.client.post("/api/v1/chat/", json=request_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
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
        mock_conversation_manager.add_message.assert_called()
    
    @patch('oracle.api.endpoints.chat.get_model_manager')
    @patch('oracle.api.endpoints.chat.get_knowledge_service')
    @patch('oracle.api.endpoints.chat.get_conversation_manager')
    def test_chat_endpoint_without_sources(self, mock_conv_mgr, mock_knowledge_svc, mock_model_mgr):
        """Test chat request without knowledge sources."""
        # Setup mocks
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.create_conversation.return_value = "test-conv-id"
        mock_conversation_manager.add_message.return_value = True
        mock_conversation_manager.build_context_prompt.return_value = "Test prompt"
        mock_conversation_manager.get_conversation_history.return_value = []
        mock_conv_mgr.return_value = mock_conversation_manager
        
        mock_knowledge_service = AsyncMock()
        mock_knowledge_svc.return_value = mock_knowledge_service
        
        mock_model_manager = AsyncMock()
        mock_model_manager.generate.return_value = self.mock_model_response
        mock_model_mgr.return_value = mock_model_manager
        
        # Make request without sources
        request_data = {
            "message": "Hello, how are you?",
            "include_sources": False
        }
        
        response = self.client.post("/api/v1/chat/", json=request_data)
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert len(data["sources"]) == 0
        
        # Verify knowledge service was not called
        mock_knowledge_service.retrieve_knowledge.assert_not_called()
    
    @patch('oracle.api.endpoints.chat.get_model_manager')
    @patch('oracle.api.endpoints.chat.get_knowledge_service')
    @patch('oracle.api.endpoints.chat.get_conversation_manager')
    def test_chat_endpoint_model_failure(self, mock_conv_mgr, mock_knowledge_svc, mock_model_mgr):
        """Test chat request when all models fail."""
        # Setup mocks
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.create_conversation.return_value = "test-conv-id"
        mock_conversation_manager.add_message.return_value = True
        mock_conversation_manager.build_context_prompt.return_value = "Test prompt"
        mock_conversation_manager.get_conversation_history.return_value = []
        mock_conv_mgr.return_value = mock_conversation_manager
        
        mock_knowledge_service = AsyncMock()
        mock_knowledge_service.retrieve_knowledge.return_value = []
        mock_knowledge_svc.return_value = mock_knowledge_service
        
        mock_model_manager = AsyncMock()
        mock_model_manager.generate.side_effect = ModelClientError("All providers failed")
        mock_model_mgr.return_value = mock_model_manager
        
        # Make request
        request_data = {
            "message": "Test message"
        }
        
        response = self.client.post("/api/v1/chat/", json=request_data)
        
        # Assertions
        assert response.status_code == 503
        data = response.json()
        assert "Model service unavailable" in data["detail"]["error"]
    
    def test_chat_endpoint_validation_errors(self):
        """Test chat request validation errors."""
        # Empty message
        response = self.client.post("/api/v1/chat/", json={"message": ""})
        assert response.status_code == 422
        
        # Message too long
        long_message = "x" * 5000
        response = self.client.post("/api/v1/chat/", json={"message": long_message})
        assert response.status_code == 422
        
        # Invalid model preference
        response = self.client.post("/api/v1/chat/", json={
            "message": "test",
            "model_preference": "invalid_model"
        })
        assert response.status_code == 422
        
        # Invalid max_sources
        response = self.client.post("/api/v1/chat/", json={
            "message": "test",
            "max_sources": 0
        })
        assert response.status_code == 422
    
    @patch('oracle.api.endpoints.chat.get_conversation_manager')
    def test_get_conversation_history(self, mock_conv_mgr):
        """Test getting conversation history."""
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.get_conversation_history.return_value = [
            {"role": "user", "content": "Hello", "timestamp": "2024-01-01T00:00:00Z"},
            {"role": "assistant", "content": "Hi there!", "timestamp": "2024-01-01T00:00:01Z"}
        ]
        mock_conversation_manager.get_conversation.return_value = MagicMock()
        mock_conv_mgr.return_value = mock_conversation_manager
        
        response = self.client.get("/api/v1/chat/conversations/test-conv-id/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "test-conv-id"
        assert len(data["messages"]) == 2
        assert data["message_count"] == 2
    
    @patch('oracle.api.endpoints.chat.get_conversation_manager')
    def test_get_conversation_history_not_found(self, mock_conv_mgr):
        """Test getting history for non-existent conversation."""
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.get_conversation_history.return_value = []
        mock_conversation_manager.get_conversation.return_value = None
        mock_conv_mgr.return_value = mock_conversation_manager
        
        response = self.client.get("/api/v1/chat/conversations/nonexistent/history")
        
        assert response.status_code == 404
    
    @patch('oracle.api.endpoints.chat.get_conversation_manager')
    def test_delete_conversation(self, mock_conv_mgr):
        """Test deleting a conversation."""
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.delete_conversation.return_value = True
        mock_conv_mgr.return_value = mock_conversation_manager
        
        response = self.client.delete("/api/v1/chat/conversations/test-conv-id")
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
    
    @patch('oracle.api.endpoints.chat.get_conversation_manager')
    def test_delete_conversation_not_found(self, mock_conv_mgr):
        """Test deleting non-existent conversation."""
        mock_conversation_manager = MagicMock()
        mock_conversation_manager.delete_conversation.return_value = False
        mock_conv_mgr.return_value = mock_conversation_manager
        
        response = self.client.delete("/api/v1/chat/conversations/nonexistent")
        
        assert response.status_code == 404


class TestConversationManager:
    """Test cases for the ConversationManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = ConversationManager(max_history_length=5)
    
    def test_create_conversation(self):
        """Test creating a new conversation."""
        conv_id = self.manager.create_conversation()
        
        assert conv_id is not None
        assert len(conv_id) > 0
        
        context = self.manager.get_conversation(conv_id)
        assert context is not None
        assert context.conversation_id == conv_id
        assert len(context.messages) == 0
    
    def test_create_conversation_with_custom_id(self):
        """Test creating conversation with custom ID."""
        custom_id = "custom-conv-123"
        conv_id = self.manager.create_conversation(custom_id)
        
        assert conv_id == custom_id
        context = self.manager.get_conversation(custom_id)
        assert context.conversation_id == custom_id
    
    def test_add_message(self):
        """Test adding messages to conversation."""
        conv_id = self.manager.create_conversation()
        
        # Add user message
        success = self.manager.add_message(conv_id, "user", "Hello")
        assert success is True
        
        # Add assistant message
        success = self.manager.add_message(conv_id, "assistant", "Hi there!")
        assert success is True
        
        # Check messages
        history = self.manager.get_conversation_history(conv_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Hi there!"
    
    def test_add_message_nonexistent_conversation(self):
        """Test adding message to non-existent conversation."""
        success = self.manager.add_message("nonexistent", "user", "Hello")
        assert success is False
    
    def test_conversation_history_limit(self):
        """Test conversation history length limit."""
        conv_id = self.manager.create_conversation()
        
        # Add more messages than the limit
        for i in range(10):
            self.manager.add_message(conv_id, "user", f"Message {i}")
        
        history = self.manager.get_conversation_history(conv_id)
        assert len(history) == 5  # Should be limited to max_history_length
        
        # Should contain the most recent messages
        assert history[-1]["content"] == "Message 9"
        assert history[0]["content"] == "Message 5"
    
    def test_update_user_preferences(self):
        """Test updating user preferences."""
        conv_id = self.manager.create_conversation()
        
        preferences = {"model": "gpt-4", "temperature": 0.7}
        success = self.manager.update_user_preferences(conv_id, preferences)
        assert success is True
        
        context = self.manager.get_conversation(conv_id)
        assert context.user_preferences == preferences
        
        # Update with additional preferences
        new_prefs = {"max_tokens": 1000}
        self.manager.update_user_preferences(conv_id, new_prefs)
        
        context = self.manager.get_conversation(conv_id)
        assert context.user_preferences["model"] == "gpt-4"
        assert context.user_preferences["max_tokens"] == 1000
    
    def test_delete_conversation(self):
        """Test deleting a conversation."""
        conv_id = self.manager.create_conversation()
        
        # Verify conversation exists
        assert self.manager.get_conversation(conv_id) is not None
        
        # Delete conversation
        success = self.manager.delete_conversation(conv_id)
        assert success is True
        
        # Verify conversation is gone
        assert self.manager.get_conversation(conv_id) is None
        
        # Try to delete again
        success = self.manager.delete_conversation(conv_id)
        assert success is False
    
    def test_build_context_prompt(self):
        """Test building context-aware prompts."""
        conv_id = self.manager.create_conversation()
        
        # Add some conversation history
        self.manager.add_message(conv_id, "user", "What is Python?")
        self.manager.add_message(conv_id, "assistant", "Python is a programming language.")
        self.manager.add_message(conv_id, "user", "What about Java?")
        
        # Build context prompt
        prompt = self.manager.build_context_prompt(
            conv_id, 
            "How do they compare?",
            include_history=True,
            max_context_messages=2
        )
        
        assert "Previous conversation context:" in prompt
        assert "What about Java?" in prompt
        assert "How do they compare?" in prompt
        
        # Test without history
        prompt_no_history = self.manager.build_context_prompt(
            conv_id,
            "How do they compare?",
            include_history=False
        )
        
        assert prompt_no_history == "How do they compare?"
    
    def test_get_conversation_stats(self):
        """Test getting conversation statistics."""
        # Create some conversations with messages
        conv1 = self.manager.create_conversation()
        conv2 = self.manager.create_conversation()
        
        self.manager.add_message(conv1, "user", "Hello")
        self.manager.add_message(conv1, "assistant", "Hi")
        self.manager.add_message(conv2, "user", "Test")
        
        stats = self.manager.get_conversation_stats()
        
        assert stats["total_conversations"] == 2
        assert stats["total_messages"] == 3
        assert stats["max_history_length"] == 5


class TestKnowledgeRetrievalService:
    """Test cases for the KnowledgeRetrievalService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        config = {
            "neo4j": {"uri": "bolt://localhost:7687"},
            "chromadb": {"host": "localhost", "port": 8000},
            "retrieval": {"max_graph_results": 5}
        }
        self.service = KnowledgeRetrievalService(config)
    
    @pytest.mark.asyncio
    async def test_retrieve_knowledge_placeholder(self):
        """Test knowledge retrieval with placeholder implementations."""
        sources = await self.service.retrieve_knowledge(
            query="test query",
            max_sources=3,
            include_graph=True,
            include_vector=True
        )
        
        assert len(sources) > 0
        assert all(isinstance(source, Source) for source in sources)
        assert all(0.0 <= source.relevance_score <= 1.0 for source in sources)
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test knowledge service health check."""
        health = await self.service.health_check()
        
        assert "neo4j" in health
        assert "chromadb" in health
        assert "knowledge_service" in health
        assert health["knowledge_service"] is True
    
    def test_get_retrieval_stats(self):
        """Test getting retrieval statistics."""
        stats = self.service.get_retrieval_stats()
        
        assert "neo4j_available" in stats
        assert "chromadb_available" in stats
        assert "config" in stats
        assert isinstance(stats["config"], dict)