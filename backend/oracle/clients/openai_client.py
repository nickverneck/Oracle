"""
Client for OpenAI-compatible APIs.
"""

from typing import Any, Dict, Optional
import httpx
import structlog

from .base import BaseModelClient, ModelResponse
from ..models.errors import ModelClientError

logger = structlog.get_logger(__name__)


class OpenAIClient(BaseModelClient):
    """Client for OpenAI-compatible APIs."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize OpenAI client.

        Args:
            config: Configuration dictionary with base_url, api_key, and model.
        """
        self.base_url = config.get("base_url", "")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=60.0)

    async def generate(
        self, prompt: str, max_tokens: Optional[int] = None, temperature: Optional[float] = None, **kwargs
    ) -> ModelResponse:
        """Generate response from an OpenAI-compatible API."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        json_payload = {
            "model": self.model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs,
        }

        try:
            response = await self.client.post("/completions", headers=headers, json=json_payload)
            response.raise_for_status()
            data = response.json()
            return ModelResponse(
                content=data["choices"][0]["text"],
                model_used=self.model,
                response_time=response.elapsed.total_seconds(),
                usage=data.get("usage"),
            )
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error from OpenAI-compatible API", error=e)
            raise ModelClientError(f"HTTP error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            logger.error("Error generating response from OpenAI-compatible API", error=e)
            raise ModelClientError(f"Failed to generate response: {e}")

    async def health_check(self) -> bool:
        """Health check for the OpenAI-compatible API."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
