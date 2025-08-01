"""Base model client interface for consistent API across providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class ModelResponse(BaseModel):
    """Standard response model for all model providers."""
    
    model_config = {"protected_namespaces": ()}
    
    content: str
    model_used: str
    provider: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None
    response_time: Optional[float] = None


class BaseModelClient(ABC):
    """Abstract base class for model serving clients."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the model client with configuration.
        
        Args:
            config: Configuration dictionary containing provider-specific settings
        """
        self.config = config
        self.provider_name = self.__class__.__name__.replace("Client", "").lower()
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs
    ) -> ModelResponse:
        """Generate a response from the model.
        
        Args:
            prompt: The input prompt to generate from
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature for generation
            **kwargs: Additional provider-specific parameters
            
        Returns:
            ModelResponse containing the generated content and metadata
            
        Raises:
            ModelClientError: When generation fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the model service is healthy and available.
        
        Returns:
            True if service is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_available_models(self) -> List[str]:
        """Get list of available models from the provider.
        
        Returns:
            List of model names available from this provider
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get the name of this model provider.
        
        Returns:
            Provider name string
        """
        return self.provider_name