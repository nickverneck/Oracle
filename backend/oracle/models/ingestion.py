"""
Document ingestion-related Pydantic models for request/response validation.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from fastapi import UploadFile
from .base import BaseResponse, TimestampedModel


class ProcessingOptions(BaseModel):
    """Configuration options for document processing."""
    
    chunk_size: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Size of text chunks for processing"
    )
    chunk_overlap: int = Field(
        default=200,
        ge=0,
        le=1000,
        description="Overlap between consecutive chunks"
    )
    extract_entities: bool = Field(
        default=True,
        description="Whether to extract entities for knowledge graph"
    )
    create_embeddings: bool = Field(
        default=True,
        description="Whether to create vector embeddings"
    )
    language: str = Field(
        default="en",
        min_length=2,
        max_length=5,
        description="Document language code"
    )
    
    @field_validator('chunk_overlap')
    @classmethod
    def validate_chunk_overlap(cls, v, info):
        """Ensure chunk overlap is less than chunk size."""
        if info.data and 'chunk_size' in info.data and v >= info.data['chunk_size']:
            raise ValueError('Chunk overlap must be less than chunk size')
        return v


class ProcessedFile(TimestampedModel):
    """Model representing a successfully processed file."""
    
    filename: str = Field(
        ..., 
        min_length=1,
        description="Original filename"
    )
    file_size: int = Field(
        ..., 
        ge=0,
        description="File size in bytes"
    )
    file_type: str = Field(
        ..., 
        description="Detected file type/format"
    )
    entities_extracted: int = Field(
        ..., 
        ge=0,
        description="Number of entities extracted for knowledge graph"
    )
    chunks_created: int = Field(
        ..., 
        ge=0,
        description="Number of text chunks created"
    )
    graph_nodes_added: int = Field(
        ..., 
        ge=0,
        description="Number of nodes added to knowledge graph"
    )
    graph_relationships_added: int = Field(
        ..., 
        ge=0,
        description="Number of relationships added to knowledge graph"
    )
    vector_embeddings_created: int = Field(
        ..., 
        ge=0,
        description="Number of vector embeddings created"
    )
    processing_time: float = Field(
        ..., 
        ge=0,
        description="Time taken to process the file in seconds"
    )
    checksum: Optional[str] = Field(
        default=None,
        description="File checksum for duplicate detection"
    )


class IngestionError(BaseModel):
    """Model representing an error during file ingestion."""
    
    filename: str = Field(
        ..., 
        description="Name of the file that caused the error"
    )
    error_type: str = Field(
        ..., 
        description="Type/category of the error"
    )
    error_message: str = Field(
        ..., 
        description="Detailed error message"
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code"
    )
    retry_possible: bool = Field(
        default=False,
        description="Whether the operation can be retried"
    )
    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Suggestions for resolving the error"
    )


class IngestionRequest(BaseModel):
    """Model for document ingestion requests."""
    
    processing_options: Optional[ProcessingOptions] = Field(
        default_factory=ProcessingOptions,
        description="Options for processing the uploaded files"
    )
    overwrite_existing: bool = Field(
        default=False,
        description="Whether to overwrite existing documents with same name"
    )
    batch_id: Optional[str] = Field(
        default=None,
        description="Optional batch identifier for grouping uploads"
    )
    
    # Note: files will be handled separately as UploadFile objects in FastAPI


class IngestionResponse(BaseResponse):
    """Model for document ingestion API responses."""
    
    processed_files: List[ProcessedFile] = Field(
        default_factory=list,
        description="List of successfully processed files"
    )
    errors: List[IngestionError] = Field(
        default_factory=list,
        description="List of errors encountered during processing"
    )
    total_files: int = Field(
        ..., 
        ge=0,
        description="Total number of files submitted for processing"
    )
    successful_files: int = Field(
        ..., 
        ge=0,
        description="Number of files processed successfully"
    )
    failed_files: int = Field(
        ..., 
        ge=0,
        description="Number of files that failed processing"
    )
    batch_id: Optional[str] = Field(
        default=None,
        description="Batch identifier if provided in request"
    )
    
    @field_validator('successful_files', 'failed_files')
    @classmethod
    def validate_file_counts(cls, v, info):
        """Validate that file counts are consistent."""
        if info.data and 'total_files' in info.data:
            total = info.data['total_files']
            if 'successful_files' in info.data and 'failed_files' in info.data:
                if info.data['successful_files'] + info.data['failed_files'] != total:
                    raise ValueError('Successful + failed files must equal total files')
        return v


class FileUploadInfo(BaseModel):
    """Model for file upload metadata."""
    
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME content type")
    size: int = Field(..., ge=0, description="File size in bytes")
    
    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v):
        """Validate filename format and allowed extensions."""
        allowed_extensions = {'.pdf', '.txt', '.docx', '.doc', '.md'}
        if not any(v.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError(f'File type not supported. Allowed: {allowed_extensions}')
        return v
    
    @field_validator('size')
    @classmethod
    def validate_file_size(cls, v):
        """Validate file size limits."""
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f'File size exceeds maximum limit of {max_size} bytes')
        return v