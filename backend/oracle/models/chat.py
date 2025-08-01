"""
Chat-related Pydantic models for request/response validation.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
from .base import BaseResponse


class Source(BaseModel):
    """Model representing a knowledge source used in generating a response."""
    
    type: Literal["graph", "vector"] = Field(
        ..., 
        description="Type of knowledge source (graph or vector database)"
    )
    content: str = Field(
        ..., 
        min_length=1,
        max_length=2000,
        description="Content from the knowledge source"
    )
    relevance_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Relevance score between 0.0 and 1.0"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the source"
    )


class ChatRequest(BaseModel):
    """Model for incoming chat requests."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        protected_namespaces=()
    )
    
    message: str = Field(
        ..., 
        min_length=1,
        max_length=4000,
        description="User's chat message"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional context for the conversation"
    )
    model_preference: Optional[str] = Field(
        default=None,
        description="Preferred model for response generation"
    )
    include_sources: bool = Field(
        default=True,
        description="Whether to include knowledge sources in response"
    )
    max_sources: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of sources to include"
    )
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        """Validate that message is not just whitespace."""
        if not v.strip():
            raise ValueError('Message cannot be empty or just whitespace')
        return v.strip()
    
    @field_validator('model_preference')
    @classmethod
    def validate_model_preference(cls, v):
        """Validate model preference against allowed values."""
        if v is not None:
            allowed_models = ['vllm', 'ollama', 'gemini']
            if v.lower() not in allowed_models:
                raise ValueError(f'Model preference must be one of: {allowed_models}')
            return v.lower()
        return v


class ChatResponse(BaseResponse):
    """Model for chat API responses."""
    
    model_config = ConfigDict(
        protected_namespaces=()
    )
    
    response: str = Field(
        ..., 
        min_length=1,
        description="Generated response from the AI model"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Confidence score for the response"
    )
    sources: List[Source] = Field(
        default_factory=list,
        description="Knowledge sources used to generate the response"
    )
    model_used: str = Field(
        ..., 
        description="AI model that generated the response"
    )
    tokens_used: Optional[int] = Field(
        default=None,
        ge=0,
        description="Number of tokens used in generation"
    )
    
    @field_validator('sources')
    @classmethod
    def validate_sources_limit(cls, v):
        """Ensure sources list doesn't exceed reasonable limits."""
        if len(v) > 20:
            raise ValueError('Too many sources provided (max 20)')
        return v


class ConversationContext(BaseModel):
    """Model for maintaining conversation context."""
    
    conversation_id: str = Field(
        ..., 
        min_length=1,
        description="Unique identifier for the conversation"
    )
    messages: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous messages in the conversation"
    )
    user_preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="User-specific preferences for the conversation"
    )
    
    @field_validator('messages')
    @classmethod
    def validate_messages_format(cls, v):
        """Validate message format in conversation history."""
        for msg in v:
            if not isinstance(msg, dict):
                raise ValueError('Each message must be a dictionary')
            if 'role' not in msg or 'content' not in msg:
                raise ValueError('Each message must have "role" and "content" fields')
            if msg['role'] not in ['user', 'assistant']:
                raise ValueError('Message role must be "user" or "assistant"')
        return v