"""
Validation utilities and helpers for Oracle data models.
"""

from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from fastapi import HTTPException

from .errors import (
    ErrorCode, ErrorDetail, ErrorResponse, 
    validation_error_to_http_exception,
    create_http_exception
)

T = TypeVar('T', bound=BaseModel)


def validate_and_parse(
    model_class: Type[T], 
    data: Dict[str, Any],
    raise_on_error: bool = True
) -> Optional[T]:
    """
    Validate and parse data into a Pydantic model.
    
    Args:
        model_class: The Pydantic model class to validate against
        data: Dictionary data to validate
        raise_on_error: Whether to raise HTTPException on validation errors
        
    Returns:
        Validated model instance or None if validation fails and raise_on_error=False
        
    Raises:
        HTTPException: If validation fails and raise_on_error=True
    """
    try:
        return model_class.model_validate(data)
    except ValidationError as e:
        if raise_on_error:
            raise validation_error_to_http_exception(e.errors())
        return None


def serialize_model(
    model: BaseModel,
    exclude_none: bool = True,
    exclude_unset: bool = False,
    by_alias: bool = True
) -> Dict[str, Any]:
    """
    Serialize a Pydantic model to dictionary with consistent options.
    
    Args:
        model: The Pydantic model instance to serialize
        exclude_none: Whether to exclude None values
        exclude_unset: Whether to exclude unset values
        by_alias: Whether to use field aliases
        
    Returns:
        Dictionary representation of the model
    """
    return model.model_dump(
        exclude_none=exclude_none,
        exclude_unset=exclude_unset,
        by_alias=by_alias
    )


def validate_file_upload(
    filename: str,
    content_type: str,
    size: int,
    max_size: int = 50 * 1024 * 1024  # 50MB
) -> Optional[List[ErrorDetail]]:
    """
    Validate file upload parameters.
    
    Args:
        filename: Name of the uploaded file
        content_type: MIME type of the file
        size: Size of the file in bytes
        max_size: Maximum allowed file size in bytes
        
    Returns:
        List of validation errors or None if valid
    """
    errors = []
    
    # Check file extension
    allowed_extensions = {'.pdf', '.txt', '.docx', '.doc', '.md'}
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        errors.append(ErrorDetail(
            field="filename",
            message=f"File type not supported. Allowed extensions: {', '.join(allowed_extensions)}",
            code=ErrorCode.UNSUPPORTED_FILE_TYPE,
            context={"filename": filename, "allowed_extensions": list(allowed_extensions)}
        ))
    
    # Check file size
    if size > max_size:
        errors.append(ErrorDetail(
            field="size",
            message=f"File size ({size} bytes) exceeds maximum limit ({max_size} bytes)",
            code=ErrorCode.FILE_TOO_LARGE,
            context={"size": size, "max_size": max_size}
        ))
    
    # Check for empty files
    if size == 0:
        errors.append(ErrorDetail(
            field="size",
            message="File cannot be empty",
            code=ErrorCode.VALIDATION_ERROR,
            context={"size": size}
        ))
    
    return errors if errors else None


def validate_chat_message(message: str) -> Optional[List[ErrorDetail]]:
    """
    Validate chat message content.
    
    Args:
        message: The chat message to validate
        
    Returns:
        List of validation errors or None if valid
    """
    errors = []
    
    if not message or not message.strip():
        errors.append(ErrorDetail(
            field="message",
            message="Message cannot be empty or contain only whitespace",
            code=ErrorCode.VALIDATION_ERROR
        ))
    
    if len(message) > 4000:
        errors.append(ErrorDetail(
            field="message",
            message=f"Message too long ({len(message)} characters). Maximum allowed: 4000",
            code=ErrorCode.VALIDATION_ERROR,
            context={"length": len(message), "max_length": 4000}
        ))
    
    return errors if errors else None


def create_validation_error_response(
    errors: List[ErrorDetail],
    message: str = "Validation failed"
) -> HTTPException:
    """
    Create a standardized validation error HTTP response.
    
    Args:
        errors: List of validation error details
        message: General error message
        
    Returns:
        HTTPException with standardized error format
    """
    return create_http_exception(
        status_code=422,
        error_code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details=errors,
        suggestions=[
            "Check the request format and field types",
            "Ensure all required fields are provided",
            "Verify field values meet the specified constraints"
        ]
    )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage and processing.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    import os
    
    # Handle special case where filename starts with dot (like .pdf)
    if filename.startswith('.') and '.' not in filename[1:]:
        # This is likely a hidden file or extension-only file
        ext = filename
        name = "unnamed_file"
    else:
        # Get the base name and extension normally
        name, ext = os.path.splitext(filename)
        
        # Remove or replace unsafe characters
        name = re.sub(r'[^\w\-_\.]', '_', name)
        
        # Ensure it doesn't start with a dot or dash
        name = name.lstrip('.-')
        
        # Ensure it's not empty after stripping
        if not name:
            name = "unnamed_file"
    
    # Limit length
    if len(name) > 100:
        name = name[:100]
    
    return f"{name}{ext}"


def extract_model_errors(validation_error: ValidationError) -> List[ErrorDetail]:
    """
    Extract error details from Pydantic ValidationError.
    
    Args:
        validation_error: Pydantic ValidationError instance
        
    Returns:
        List of ErrorDetail objects
    """
    details = []
    
    for error in validation_error.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        details.append(ErrorDetail(
            field=field,
            message=error.get("msg", "Validation error"),
            code=ErrorCode.VALIDATION_ERROR,
            context={
                "input": error.get("input"),
                "type": error.get("type")
            }
        ))
    
    return details