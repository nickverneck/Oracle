"""Ollama model serving client with configurable URL support."""

import time
from typing import Dict, Any, Optional, List
import httpx
import structlog

from .base import BaseModelClient, ModelResponse
from ..models.errors import ModelClientError

logger = structlog.get_logger(__name__)


class OllamaClient(BaseModelClient):
    """Client for Ollama model serving with configurable URL."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama client.
        
        Args:
            config: Configuration containing:
                - base_url: Ollama server URL (required)
                - model: Model name to use (default: llama2)
                - timeout: Request timeout in seconds (default: 120)
        """
        super().__init__(config)
        self.base_url = config.get("base_url")
        if not self.base_url:
            raise ValueError("Ollama base_url is required in configuration")
        
        self.model = config.get("model", "llama2")
        self.timeout = config.get("timeout", 120)
        
        # Create HTTP client with timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        )
        
        logger.info(
            "Initialized Ollama client",
            base_url=self.base_url,
            model=self.model,
            timeout=self.timeout
        )
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using Ollama API.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate (Ollama uses num_predict)
            temperature: Sampling temperature (default: 0.7)
            **kwargs: Additional Ollama parameters
            
        Returns:
            ModelResponse with generated content
            
        Raises:
            ModelClientError: When generation fails
        """
        start_time = time.time()
        
        try:
            # Prepare request payload for Ollama API
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature or 0.7,
                    **kwargs
                }
            }
            
            # Convert max_tokens to Ollama's num_predict parameter
            if max_tokens:
                payload["options"]["num_predict"] = max_tokens
            
            logger.debug("Sending request to Ollama", payload=payload)
            
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()
            
            data = response.json()
            response_time = time.time() - start_time
            
            # Extract content from Ollama response
            content = data.get("response", "")
            if not content:
                raise ModelClientError("Empty response returned from Ollama")
            
            logger.info(
                "Successfully generated response with Ollama",
                response_time=response_time,
                content_length=len(content)
            )
            
            return ModelResponse(
                content=content,
                model_used=data.get("model", self.model),
                provider="ollama",
                usage={
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count"),
                    "total_duration": data.get("total_duration"),
                },
                finish_reason="stop" if data.get("done") else "length",
                response_time=response_time
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from Ollama",
                status_code=e.response.status_code,
                response_text=e.response.text
            )
            raise ModelClientError(f"Ollama HTTP error: {e.response.status_code}")
        
        except httpx.RequestError as e:
            logger.error("Request error to Ollama", error=str(e))
            raise ModelClientError(f"Ollama request error: {str(e)}")
        
        except Exception as e:
            logger.error("Unexpected error with Ollama", error=str(e))
            raise ModelClientError(f"Ollama unexpected error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if Ollama service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Ollama doesn't have a dedicated health endpoint, so we check /api/tags
            response = await self.client.get("/api/tags", timeout=5.0)
            is_healthy = response.status_code == 200
            
            logger.debug("Ollama health check", healthy=is_healthy)
            return is_healthy
            
        except Exception as e:
            logger.warning("Ollama health check failed", error=str(e))
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get available models from Ollama.
        
        Returns:
            List of available model names
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            
            logger.debug("Retrieved Ollama models", models=models)
            return models
            
        except Exception as e:
            logger.warning("Failed to get Ollama models", error=str(e))
            return [self.model]  # Return configured model as fallback
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()