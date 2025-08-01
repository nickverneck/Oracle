"""Example configuration for model serving clients."""

# Example configuration for ModelManager
EXAMPLE_CONFIG = {
    "vllm": {
        "base_url": "http://oracle-vllm:8001",
        "model": "microsoft/DialoGPT-medium",
        "timeout": 60
    },
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "llama2",
        "timeout": 120
    },
    "gemini": {
        "api_key": "your-google-api-key-here",
        "model": "gemini-pro",
        "timeout": 60
    },
    "fallback_order": ["vllm", "ollama", "gemini"]
}

# Example usage:
"""
from oracle.clients import ModelManager

async def main():
    async with ModelManager(EXAMPLE_CONFIG) as manager:
        # Generate response with automatic fallback
        response = await manager.generate(
            prompt="Hello, how can I help you troubleshoot your issue?",
            max_tokens=512,
            temperature=0.7
        )
        
        print(f"Response: {response.content}")
        print(f"Provider used: {response.provider}")
        print(f"Model used: {response.model_used}")
        
        # Check health of all providers
        health_status = await manager.health_check()
        print(f"Health status: {health_status}")
        
        # Get available models
        available_models = await manager.get_available_models()
        print(f"Available models: {available_models}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
"""