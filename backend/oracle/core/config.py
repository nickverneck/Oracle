"""Application configuration management."""

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )
    
    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8000, description="API port")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # CORS Configuration
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "oracle-backend"],
        description="Allowed hosts"
    )
    
    # Model Serving Configuration
    VLLM_BASE_URL: str = Field(
        default="http://oracle-vllm:8001",
        description="vLLM service base URL"
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        description="Ollama service base URL"
    )
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key"
    )
    
    # Database Configuration
    NEO4J_URI: str = Field(
        default="bolt://oracle-neo4j:7687",
        description="Neo4j database URI"
    )
    NEO4J_USERNAME: str = Field(
        default="neo4j",
        description="Neo4j username"
    )
    NEO4J_PASSWORD: str = Field(
        default="password",
        description="Neo4j password"
    )
    
    CHROMADB_HOST: str = Field(
        default="oracle-chromadb",
        description="ChromaDB host"
    )
    CHROMADB_PORT: int = Field(
        default=8002,
        description="ChromaDB port"
    )
    
    # Logging Configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json or console)"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()