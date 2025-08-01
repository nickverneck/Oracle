"""Model manager with fallback logic across multiple providers."""

import asyncio
from typing import Dict, Any, Optional, List, Type
import structlog

from .base import BaseModelClient, ModelResponse
from .vllm_client import VLLMClient
from .ollama_client import OllamaClient
from .gemini_client import GeminiClient
from ..models.errors import ModelClientError

logger = structlog.get_logger(__name__)


class ModelManager:
    """Manages multiple model providers with automatic fallback logic."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize model manager with provider configurations.
        
        Args:
            config: Configuration dictionary containing provider settings:
                - vllm: vLLM configuration
                - ollama: Ollama configuration  
                - gemini: Gemini configuration
                - fallback_order: List of provider names in fallback order
        """
        self.config = config
        self.clients: Dict[str, BaseModelClient] = {}
        self.fallback_order = config.get("fallback_order", ["vllm", "ollama", "gemini"])
        
        # Initialize clients based on configuration
        self._initialize_clients()
        
        logger.info(
            "Initialized model manager",
            providers=list(self.clients.keys()),
            fallback_order=self.fallback_order
        )
    
    def _initialize_clients(self) -> None:
        """Initialize model clients based on configuration."""
        client_classes: Dict[str, Type[BaseModelClient]] = {
            "vllm": VLLMClient,
            "ollama": OllamaClient,
            "gemini": GeminiClient,
        }
        
        for provider_name, client_class in client_classes.items():
            provider_config = self.config.get(provider_name)
            if provider_config:
                try:
                    self.clients[provider_name] = client_class(provider_config)
                    logger.info(f"Initialized {provider_name} client")
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize {provider_name} client",
                        error=str(e)
                    )
    
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        preferred_provider: Optional[str] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate response with automatic fallback across providers.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            preferred_provider: Preferred provider to try first
            **kwargs: Additional generation parameters
            
        Returns:
            ModelResponse from the first successful provider
            
        Raises:
            ModelClientError: When all providers fail
        """
        # Determine provider order
        provider_order = self._get_provider_order(preferred_provider)
        
        last_error = None
        
        for provider_name in provider_order:
            client = self.clients.get(provider_name)
            if not client:
                logger.debug(f"Provider {provider_name} not configured, skipping")
                continue
            
            try:
                logger.info(f"Attempting generation with {provider_name}")
                
                response = await client.generate(
                    prompt=prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                logger.info(
                    f"Successfully generated response with {provider_name}",
                    response_time=response.response_time
                )
                
                return response
                
            except ModelClientError as e:
                last_error = e
                logger.warning(
                    f"Generation failed with {provider_name}, trying next provider",
                    error=str(e)
                )
                continue
            
            except Exception as e:
                last_error = ModelClientError(f"Unexpected error with {provider_name}: {str(e)}")
                logger.error(
                    f"Unexpected error with {provider_name}",
                    error=str(e)
                )
                continue
        
        # All providers failed
        error_msg = f"All model providers failed. Last error: {str(last_error)}"
        logger.error("All model providers failed", last_error=str(last_error))
        raise ModelClientError(error_msg)
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all configured providers.
        
        Returns:
            Dictionary mapping provider names to health status
        """
        health_status = {}
        
        # Run health checks concurrently
        health_tasks = {
            name: client.health_check()
            for name, client in self.clients.items()
        }
        
        if health_tasks:
            results = await asyncio.gather(
                *health_tasks.values(),
                return_exceptions=True
            )
            
            for (name, _), result in zip(health_tasks.items(), results):
                if isinstance(result, Exception):
                    health_status[name] = False
                    logger.warning(f"Health check failed for {name}", error=str(result))
                else:
                    health_status[name] = result
        
        logger.debug("Health check results", health_status=health_status)
        return health_status
    
    async def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models from all providers.
        
        Returns:
            Dictionary mapping provider names to lists of available models
        """
        models_by_provider = {}
        
        # Get models from all providers concurrently
        model_tasks = {
            name: client.get_available_models()
            for name, client in self.clients.items()
        }
        
        if model_tasks:
            results = await asyncio.gather(
                *model_tasks.values(),
                return_exceptions=True
            )
            
            for (name, _), result in zip(model_tasks.items(), results):
                if isinstance(result, Exception):
                    models_by_provider[name] = []
                    logger.warning(f"Failed to get models for {name}", error=str(result))
                else:
                    models_by_provider[name] = result
        
        logger.debug("Available models", models_by_provider=models_by_provider)
        return models_by_provider
    
    def get_configured_providers(self) -> List[str]:
        """Get list of configured provider names.
        
        Returns:
            List of provider names that are configured
        """
        return list(self.clients.keys())
    
    def _get_provider_order(self, preferred_provider: Optional[str] = None) -> List[str]:
        """Get provider order for fallback logic.
        
        Args:
            preferred_provider: Provider to try first
            
        Returns:
            List of provider names in order to try
        """
        if preferred_provider and preferred_provider in self.clients:
            # Put preferred provider first, then follow fallback order
            order = [preferred_provider]
            order.extend([p for p in self.fallback_order if p != preferred_provider and p in self.clients])
            return order
        else:
            # Use default fallback order
            return [p for p in self.fallback_order if p in self.clients]
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Close all client connections
        for client in self.clients.values():
            if hasattr(client, '__aexit__'):
                await client.__aexit__(exc_type, exc_val, exc_tb)