"""
Base Pydantic models for common patterns across the Oracle system.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, ConfigDict


class BaseResponse(BaseModel):
    """Base response model with common fields for all API responses."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        extra="forbid"
    )
    
    status: str = Field(..., description="Response status")
    processing_time: float = Field(..., ge=0, description="Processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Additional metadata for the response"
    )


class TimestampedModel(BaseModel):
    """Base model with automatic timestamp fields."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


class PaginatedResponse(BaseModel):
    """Base model for paginated API responses."""
    
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )
    
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")