"""
Error response models and exception handling classes for the Oracle system.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from fastapi import HTTPException
from enum import Enum


class ErrorCode(str, Enum):
    """Enumeration of standardized error codes."""
    
    # General errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMITED = "RATE_LIMITED"
    
    # Model serving errors
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_OVERLOADED = "MODEL_OVERLOADED"
    INVALID_MODEL_RESPONSE = "INVALID_MODEL_RESPONSE"
    
    # Knowledge retrieval errors
    GRAPH_CONNECTION_ERROR = "GRAPH_CONNECTION_ERROR"
    VECTOR_DB_ERROR = "VECTOR_DB_ERROR"
    KNOWLEDGE_RETRIEVAL_FAILED = "KNOWLEDGE_RETRIEVAL_FAILED"
    KNOWLEDGE_RETRIEVAL_ERROR = "KNOWLEDGE_RETRIEVAL_ERROR"
    
    # Ingestion errors
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    PROCESSING_FAILED = "PROCESSING_FAILED"
    DUPLICATE_FILE = "DUPLICATE_FILE"


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    field: Optional[str] = Field(
        default=None,
        description="Field name that caused the error (for validation errors)"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context about the error"
    )


class ErrorResponse(BaseModel):
    """Standard error response model for all API endpoints."""
    
    error: bool = Field(
        default=True,
        description="Indicates this is an error response"
    )
    error_code: ErrorCode = Field(
        ...,
        description="Standardized error code"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Detailed error information"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracking"
    )
    timestamp: str = Field(
        ...,
        description="ISO timestamp when the error occurred"
    )
    path: Optional[str] = Field(
        default=None,
        description="API path where the error occurred"
    )
    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Suggestions for resolving the error"
    )


# Custom Exception Classes

class OracleException(Exception):
    """Base exception class for Oracle-specific errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        details: Optional[List[ErrorDetail]] = None,
        suggestions: Optional[List[str]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or []
        self.suggestions = suggestions or []
        super().__init__(message)


class ModelServingException(OracleException):
    """Exception for model serving related errors."""
    
    def __init__(
        self, 
        message: str, 
        model_name: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.MODEL_UNAVAILABLE,
        **kwargs
    ):
        self.model_name = model_name
        super().__init__(message, error_code, **kwargs)


class KnowledgeRetrievalException(OracleException):
    """Exception for knowledge retrieval related errors."""
    
    def __init__(
        self, 
        message: str, 
        source_type: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.KNOWLEDGE_RETRIEVAL_FAILED,
        **kwargs
    ):
        self.source_type = source_type
        super().__init__(message, error_code, **kwargs)


class IngestionException(OracleException):
    """Exception for document ingestion related errors."""
    
    def __init__(
        self, 
        message: str, 
        filename: Optional[str] = None,
        error_code: ErrorCode = ErrorCode.PROCESSING_FAILED,
        **kwargs
    ):
        self.filename = filename
        super().__init__(message, error_code, **kwargs)


class ValidationException(OracleException):
    """Exception for data validation errors."""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        self.field = field
        self.value = value
        details = []
        if field:
            details.append(ErrorDetail(
                field=field,
                message=message,
                code=ErrorCode.VALIDATION_ERROR
            ))
        super().__init__(message, ErrorCode.VALIDATION_ERROR, details, **kwargs)


class ModelClientError(Exception):
    """Exception for model client errors with fallback support."""
    
    def __init__(self, message: str, provider: Optional[str] = None):
        self.message = message
        self.provider = provider
        super().__init__(message)


# HTTP Exception Helpers

def create_http_exception(
    status_code: int,
    error_code: ErrorCode,
    message: str,
    details: Optional[List[ErrorDetail]] = None,
    suggestions: Optional[List[str]] = None
) -> HTTPException:
    """Create a standardized HTTPException with ErrorResponse format."""
    
    from datetime import datetime
    
    error_response = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        timestamp=datetime.utcnow().isoformat(),
        suggestions=suggestions
    )
    
    return HTTPException(
        status_code=status_code,
        detail=error_response.model_dump()
    )


def validation_error_to_http_exception(validation_errors: List[Dict[str, Any]]) -> HTTPException:
    """Convert Pydantic validation errors to standardized HTTP exception."""
    
    details = []
    for error in validation_errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        details.append(ErrorDetail(
            field=field,
            message=error.get("msg", "Validation error"),
            code=ErrorCode.VALIDATION_ERROR,
            context={"input": error.get("input")}
        ))
    
    return create_http_exception(
        status_code=422,
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details=details,
        suggestions=[
            "Check the request format and field types",
            "Ensure all required fields are provided",
            "Verify field values meet the specified constraints"
        ]
    )