"""Tests for model serving clients and manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from oracle.clients.base import BaseModelClient, ModelResponse
from oracle.clients.vllm_client import VLLMClient
from oracle.clients.ollama_client import OllamaClient
from oracle.clients.gemini_client import GeminiClient
from oracle.clients.model_manager import ModelManager
from oracle.models.errors import ModelClientError


class TestBaseModelClient:
    """Test the base model client interface."""
    
    def test_provider_name_extraction(self):
        """Test that provider name is correctly extracted from class name."""
        
        class TestClient(BaseModelClient):
            async def generate(self, prompt, **kwargs):
                pass
            
            async def health_check(self):
                pass
            
            async def get_available_models(self):
                pass
        
        client = TestClient({})
        assert client.get_provider_name() == "test"


class TestVLLMClient:
    """Test vLLM client implementation."""
    
    @pytest.fixture
    def vllm_config(self):
        return {
            "base_url": "http://test-vllm:8001",
            "model": "test-model",
            "timeout": 30
        }
    
    @pytest.fixture
    def vllm_client(self, vllm_config):
        return VLLMClient(vllm_config)
    
    @pytest.mark.asyncio
    async def test_successful_generation(self, vllm_client):
        """Test successful response generation."""
        mock_response = {
            "choices": [{
                "message": {"content": "Test response"},
                "finish_reason": "stop"
            }],
            "model": "test-model",
            "usage": {"total_tokens": 10}
        }
        
        with patch.object(vllm_client.client, 'post') as mock_post:
            mock_http_response = AsyncMock()
            mock_http_response.json = MagicMock(return_value=mock_response)
            mock_http_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_http_response
            
            response = await vllm_client.generate("Test prompt")
            
            assert isinstance(response, ModelResponse)
            assert response.content == "Test response"
            assert response.provider == "vllm"
            assert response.model_used == "test-model"
            assert response.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_http_error_handling(self, vllm_client):
        """Test HTTP error handling."""
        with patch.object(vllm_client.client, 'post') as mock_post:
            mock_post.side_effect = httpx.HTTPStatusError(
                "Server error", 
                request=MagicMock(), 
                response=MagicMock(status_code=500, text="Internal error")
            )
            
            with pytest.raises(ModelClientError, match="vLLM HTTP error: 500"):
                await vllm_client.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, vllm_client):
        """Test successful health check."""
        with patch.object(vllm_client.client, 'get') as mock_get:
            mock_http_response = AsyncMock()
            mock_http_response.status_code = 200
            mock_get.return_value = mock_http_response
            
            is_healthy = await vllm_client.health_check()
            assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, vllm_client):
        """Test failed health check."""
        with patch.object(vllm_client.client, 'get') as mock_get:
            mock_get.side_effect = httpx.RequestError("Connection failed")
            
            is_healthy = await vllm_client.health_check()
            assert is_healthy is False


class TestOllamaClient:
    """Test Ollama client implementation."""
    
    @pytest.fixture
    def ollama_config(self):
        return {
            "base_url": "http://test-ollama:11434",
            "model": "llama2",
            "timeout": 60
        }
    
    @pytest.fixture
    def ollama_client(self, ollama_config):
        return OllamaClient(ollama_config)
    
    def test_missing_base_url(self):
        """Test that missing base_url raises ValueError."""
        with pytest.raises(ValueError, match="Ollama base_url is required"):
            OllamaClient({})
    
    @pytest.mark.asyncio
    async def test_successful_generation(self, ollama_client):
        """Test successful response generation."""
        mock_response = {
            "response": "Test response from Ollama",
            "model": "llama2",
            "done": True,
            "prompt_eval_count": 5,
            "eval_count": 10,
            "total_duration": 1000000
        }
        
        with patch.object(ollama_client.client, 'post') as mock_post:
            mock_http_response = AsyncMock()
            mock_http_response.json = MagicMock(return_value=mock_response)
            mock_http_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_http_response
            
            response = await ollama_client.generate("Test prompt")
            
            assert isinstance(response, ModelResponse)
            assert response.content == "Test response from Ollama"
            assert response.provider == "ollama"
            assert response.model_used == "llama2"
            assert response.finish_reason == "stop"
    
    @pytest.mark.asyncio
    async def test_get_available_models(self, ollama_client):
        """Test getting available models."""
        mock_response = {
            "models": [
                {"name": "llama2"},
                {"name": "codellama"}
            ]
        }
        
        with patch.object(ollama_client.client, 'get') as mock_get:
            mock_http_response = AsyncMock()
            mock_http_response.json = MagicMock(return_value=mock_response)
            mock_http_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_http_response
            
            models = await ollama_client.get_available_models()
            assert models == ["llama2", "codellama"]


class TestGeminiClient:
    """Test Gemini client implementation."""
    
    @pytest.fixture
    def gemini_config(self):
        return {
            "api_key": "test-api-key",
            "model": "gemini-pro",
            "timeout": 30
        }
    
    def test_missing_api_key(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError, match="Gemini api_key is required"):
            GeminiClient({})
    
    @pytest.mark.asyncio
    async def test_successful_generation(self, gemini_config):
        """Test successful response generation."""
        with patch('oracle.clients.gemini_client.genai') as mock_genai:
            # Mock the model and response
            mock_model = AsyncMock()
            mock_genai.GenerativeModel.return_value = mock_model
            
            # Create mock response
            mock_candidate = MagicMock()
            mock_candidate.content.parts = [MagicMock(text="Test response from Gemini")]
            mock_candidate.finish_reason = None
            
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_response.prompt_feedback = None
            mock_response.usage_metadata = MagicMock()
            mock_response.usage_metadata.total_token_count = 15
            
            mock_model.generate_content_async.return_value = mock_response
            
            client = GeminiClient(gemini_config)
            response = await client.generate("Test prompt")
            
            assert isinstance(response, ModelResponse)
            assert response.content == "Test response from Gemini"
            assert response.provider == "gemini"
            assert response.model_used == "gemini-pro"


class TestModelManager:
    """Test model manager with fallback logic."""
    
    @pytest.fixture
    def manager_config(self):
        return {
            "vllm": {
                "base_url": "http://test-vllm:8001",
                "model": "test-model"
            },
            "ollama": {
                "base_url": "http://test-ollama:11434",
                "model": "llama2"
            },
            "gemini": {
                "api_key": "test-key",
                "model": "gemini-pro"
            },
            "fallback_order": ["vllm", "ollama", "gemini"]
        }
    
    @pytest.fixture
    def model_manager(self, manager_config):
        with patch('oracle.clients.gemini_client.genai'):
            return ModelManager(manager_config)
    
    def test_initialization(self, model_manager):
        """Test that manager initializes with correct providers."""
        providers = model_manager.get_configured_providers()
        assert "vllm" in providers
        assert "ollama" in providers
        assert "gemini" in providers
    
    @pytest.mark.asyncio
    async def test_successful_generation_primary(self, model_manager):
        """Test successful generation with primary provider."""
        mock_response = ModelResponse(
            content="Test response",
            model_used="test-model",
            provider="vllm"
        )
        
        # Mock the vLLM client to succeed
        with patch.object(model_manager.clients["vllm"], 'generate', return_value=mock_response):
            response = await model_manager.generate("Test prompt")
            
            assert response.content == "Test response"
            assert response.provider == "vllm"
    
    @pytest.mark.asyncio
    async def test_fallback_logic(self, model_manager):
        """Test fallback to secondary provider when primary fails."""
        mock_response = ModelResponse(
            content="Fallback response",
            model_used="llama2",
            provider="ollama"
        )
        
        # Mock vLLM to fail, Ollama to succeed
        with patch.object(model_manager.clients["vllm"], 'generate', side_effect=ModelClientError("vLLM failed")):
            with patch.object(model_manager.clients["ollama"], 'generate', return_value=mock_response):
                response = await model_manager.generate("Test prompt")
                
                assert response.content == "Fallback response"
                assert response.provider == "ollama"
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self, model_manager):
        """Test error when all providers fail."""
        # Mock all clients to fail
        for client in model_manager.clients.values():
            with patch.object(client, 'generate', side_effect=ModelClientError("Provider failed")):
                pass
        
        with pytest.raises(ModelClientError, match="All model providers failed"):
            await model_manager.generate("Test prompt")
    
    @pytest.mark.asyncio
    async def test_health_check(self, model_manager):
        """Test health check across all providers."""
        # Mock health checks
        with patch.object(model_manager.clients["vllm"], 'health_check', return_value=True):
            with patch.object(model_manager.clients["ollama"], 'health_check', return_value=False):
                with patch.object(model_manager.clients["gemini"], 'health_check', return_value=True):
                    health_status = await model_manager.health_check()
                    
                    assert health_status["vllm"] is True
                    assert health_status["ollama"] is False
                    assert health_status["gemini"] is True
    
    def test_provider_order_with_preference(self, model_manager):
        """Test provider order with preferred provider."""
        order = model_manager._get_provider_order("gemini")
        assert order[0] == "gemini"
        assert "vllm" in order
        assert "ollama" in order
    
    def test_provider_order_default(self, model_manager):
        """Test default provider order."""
        order = model_manager._get_provider_order()
        assert order == ["vllm", "ollama", "gemini"]