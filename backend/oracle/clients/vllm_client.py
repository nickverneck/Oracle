"""vLLM model serving client with OpenAI-compatible API."""

import time
from typing import Dict, Any, Optional, List
import httpx
import structlog

from .base import BaseModelClient, ModelResponse
from ..models.errors import ModelClientError

logger = structlog.get_logger(__name__)


class VLLMClient(BaseModelClient):
    """Client for vLLM model serving with OpenAI-compatible API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize vLLM client.
        
        Args:
            config: Configuration containing:
                - base_url: vLLM server URL (default: http://oracle-vllm:8001)
                - model: Model name to use
                - timeout: Request timeout in seconds (default: 60)
        """
        super().__init__(config)
        self.base_url = config.get("base_url", "http://oracle-vllm:8001")
        self.model = config.get("model", "default")
        self.timeout = config.get("timeout", 60)
        
        # Create HTTP client with timeout
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout)
        )
        
        logger.info(
            "Initialized vLLM client",
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
        """Generate response using vLLM OpenAI-compatible API.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate (default: 512)
            temperature: Sampling temperature (default: 0.7)
            **kwargs: Additional OpenAI API parameters
            
        Returns:
            ModelResponse with generated content
            
        Raises:
            ModelClientError: When generation fails
        """
        start_time = time.time()
        
        try:
            # Prepare request payload for OpenAI-compatible API
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens or 512,
                "temperature": temperature or 0.7,
                "stream": False,
                **kwargs
            }
            
            logger.debug("Sending request to vLLM", payload=payload)
            
            response = await self.client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            
            data = response.json()
            response_time = time.time() - start_time
            
            # Extract content from OpenAI-compatible response
            if not data.get("choices") or len(data["choices"]) == 0:
                raise ModelClientError("No choices returned from vLLM")
            
            choice = data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            
            if not content:
                raise ModelClientError("Empty content returned from vLLM")
            
            logger.info(
                "Successfully generated response with vLLM",
                response_time=response_time,
                content_length=len(content)
            )
            
            return ModelResponse(
                content=content,
                model_used=data.get("model", self.model),
                provider="vllm",
                usage=data.get("usage"),
                finish_reason=choice.get("finish_reason"),
                response_time=response_time
            )
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from vLLM",
                status_code=e.response.status_code,
                response_text=e.response.text
            )
            raise ModelClientError(f"vLLM HTTP error: {e.response.status_code}")
        
        except httpx.RequestError as e:
            logger.error("Request error to vLLM", error=str(e))
            raise ModelClientError(f"vLLM request error: {str(e)}")
        
        except Exception as e:
            logger.error("Unexpected error with vLLM", error=str(e))
            raise ModelClientError(f"vLLM unexpected error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if vLLM service is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get("/health", timeout=5.0)
            is_healthy = response.status_code == 200
            
            logger.debug("vLLM health check", healthy=is_healthy)
            return is_healthy
            
        except Exception as e:
            logger.warning("vLLM health check failed", error=str(e))
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get available models from vLLM.
        
        Returns:
            List of available model names
        """
        try:
            response = await self.client.get("/v1/models")
            response.raise_for_status()
            
            data = response.json()
            models = [model["id"] for model in data.get("data", [])]
            
            logger.debug("Retrieved vLLM models", models=models)
            return models
            
        except Exception as e:
            logger.warning("Failed to get vLLM models", error=str(e))
            return [self.model]  # Return configured model as fallback
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()