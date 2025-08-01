"""
Oracle Backend Data Models

This module contains all Pydantic models for request/response validation,
data serialization, and type safety across the Oracle chatbot system.
"""

from .chat import ChatRequest, ChatResponse, Source
from .ingestion import (
    IngestionRequest,
    IngestionResponse,
    ProcessedFile,
    ProcessingOptions,
)
from .errors import ErrorResponse
from .ingestion import IngestionError
from .base import BaseResponse, TimestampedModel
from .validation import (
    validate_and_parse,
    serialize_model,
    validate_file_upload,
    validate_chat_message,
    create_validation_error_response,
    sanitize_filename,
    extract_model_errors,
)

__all__ = [
    # Chat models
    "ChatRequest",
    "ChatResponse", 
    "Source",
    # Ingestion models
    "IngestionRequest",
    "IngestionResponse",
    "ProcessedFile",
    "ProcessingOptions",
    # Error models
    "ErrorResponse",
    "IngestionError",
    # Base models
    "BaseResponse",
    "TimestampedModel",
    # Validation utilities
    "validate_and_parse",
    "serialize_model",
    "validate_file_upload",
    "validate_chat_message",
    "create_validation_error_response",
    "sanitize_filename",
    "extract_model_errors",
]