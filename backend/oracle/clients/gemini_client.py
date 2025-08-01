"""Google Gemini API client with authentication."""

import time
from typing import Dict, Any, Optional, List
import google.generativeai as genai
import structlog

from .base import BaseModelClient, ModelResponse
from ..models.errors import ModelClientError

logger = structlog.get_logger(__name__)


class GeminiClient(BaseModelClient):
    """Client for Google Gemini API with authentication."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Gemini client.
        
        Args:
            config: Configuration containing:
                - api_key: Google API key (required)
                - model: Model name to use (default: gemini-pro)
                - timeout: Request timeout in seconds (default: 60)
        """
        super().__init__(config)
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Gemini api_key is required in configuration")
        
        self.model_name = config.get("model", "gemini-pro")
        self.timeout = config.get("timeout", 60)
        
        # Configure the Gemini API
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
        logger.info(
            "Initialized Gemini client",
            model=self.model_name,
            timeout=self.timeout
        )
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response using Google Gemini API.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate (Gemini uses max_output_tokens)
            temperature: Sampling temperature (default: 0.7)
            **kwargs: Additional Gemini parameters
            
        Returns:
            ModelResponse with generated content
            
        Raises:
            ModelClientError: When generation fails
        """
        start_time = time.time()
        
        try:
            # Prepare generation config
            generation_config = genai.types.GenerationConfig(
                temperature=temperature or 0.7,
                max_output_tokens=max_tokens or 512,
                **kwargs
            )
            
            logger.debug("Sending request to Gemini", prompt_length=len(prompt))
            
            # Generate response
            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config
            )
            
            response_time = time.time() - start_time
            
            # Check if response was blocked
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                raise ModelClientError(
                    f"Gemini blocked prompt: {response.prompt_feedback.block_reason}"
                )
            
            # Extract content from response
            if not response.candidates or len(response.candidates) == 0:
                raise ModelClientError("No candidates returned from Gemini")
            
            candidate = response.candidates[0]
            
            # Check if candidate was blocked
            if candidate.finish_reason and candidate.finish_reason.name in ["SAFETY", "RECITATION"]:
                raise ModelClientError(
                    f"Gemini blocked response: {candidate.finish_reason.name}"
                )
            
            content = candidate.content.parts[0].text if candidate.content.parts else ""
            if not content:
                raise ModelClientError("Empty content returned from Gemini")
            
            logger.info(
                "Successfully generated response with Gemini",
                response_time=response_time,
                content_length=len(content)
            )
            
            return ModelResponse(
                content=content,
                model_used=self.model_name,
                provider="gemini",
                usage={
                    "prompt_token_count": response.usage_metadata.prompt_token_count if response.usage_metadata else None,
                    "candidates_token_count": response.usage_metadata.candidates_token_count if response.usage_metadata else None,
                    "total_token_count": response.usage_metadata.total_token_count if response.usage_metadata else None,
                },
                finish_reason=candidate.finish_reason.name if candidate.finish_reason else "stop",
                response_time=response_time
            )
            
        except Exception as e:
            logger.error("Error with Gemini", error=str(e))
            raise ModelClientError(f"Gemini error: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check if Gemini API is accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple generation to test API access
            test_response = await self.model.generate_content_async(
                "Hello",
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1,
                    temperature=0.1
                )
            )
            
            is_healthy = (
                test_response.candidates and 
                len(test_response.candidates) > 0 and
                test_response.candidates[0].content.parts
            )
            
            logger.debug("Gemini health check", healthy=is_healthy)
            return is_healthy
            
        except Exception as e:
            logger.warning("Gemini health check failed", error=str(e))
            return False
    
    async def get_available_models(self) -> List[str]:
        """Get available models from Gemini.
        
        Returns:
            List of available model names
        """
        try:
            # List available models
            models = []
            for model in genai.list_models():
                if 'generateContent' in model.supported_generation_methods:
                    models.append(model.name.replace('models/', ''))
            
            logger.debug("Retrieved Gemini models", models=models)
            return models
            
        except Exception as e:
            logger.warning("Failed to get Gemini models", error=str(e))
            return [self.model_name]  # Return configured model as fallback